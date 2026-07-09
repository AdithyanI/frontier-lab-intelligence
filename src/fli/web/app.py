"""FastAPI app: JSON API + built SPA host.

The frontend lives in frontend/ (Vite + React + TS) and builds into
src/fli/web/dist, which this app serves. During frontend development,
`npm run dev` in frontend/ proxies /api to this server.

Endpoints:
- /api/status        pipeline stages with live DB counts (health/ops)
- /api/accounts      compatibility route for X channels, sortable/paginated
- /api/registry      labs (curated entities) + top people candidates
                     (evidence-ranked, not yet promoted — the registry
                     itself, before the auto-curation pass exists)
"""

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from fli import channels

DIST_DIR = Path(__file__).parent / "dist"

app = FastAPI(title="Frontier Lab Intelligence")


def _model_conn():
    conn = channels.connect()
    if conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0] == 0:
        channels.sync_all(conn)
    return conn


def _counts() -> dict:
    conn = _model_conn()
    try:
        def one(sql: str) -> int:
            return conn.execute(sql).fetchone()[0]

        return {
            "channels": one("SELECT COUNT(*) FROM channels"),
            "x_channels": one("SELECT COUNT(*) FROM channels WHERE kind = 'x'"),
            "seed_ranked_channels": one(
                "SELECT COUNT(DISTINCT channel_id) FROM channel_observations"
                " WHERE source = 'digg' AND metric = 'rank'"
            ),
            "edges": one("SELECT COUNT(*) FROM graph_edges"),
            "observations": one("SELECT COUNT(*) FROM channel_observations"),
            "raw_items": one("SELECT COUNT(*) FROM raw_items"),
            "observation_sources": one(
                "SELECT COUNT(DISTINCT source) FROM channel_observations"
            ),
            "entities": one("SELECT COUNT(*) FROM entities"),
        }
    finally:
        conn.close()


@app.get("/api/status")
def status() -> JSONResponse:
    c = _counts()
    stages = [
        {
            "id": "sources",
            "name": "Sources",
            "state": "live",
            "summary": "Frozen X seed graph + raw lab blogs / arXiv / GitHub corpus.",
            "stats": [
                {"label": "graph edges", "value": c["edges"]},
                {"label": "raw items", "value": c["raw_items"]},
                {"label": "observation sources", "value": c["observation_sources"]},
            ],
        },
        {
            "id": "registry",
            "name": "Registry",
            "state": "in-progress",
            "summary": "Entities linked to channels; people candidates awaiting curation.",
            "stats": [
                {"label": "x channels", "value": c["x_channels"]},
                {"label": "seed-ranked channels", "value": c["seed_ranked_channels"]},
                {"label": "confirmed entities", "value": c["entities"]},
            ],
        },
        {
            "id": "ingestion",
            "name": "Ingestion",
            "state": "pending",
            "summary": "Scheduled pulls around the accepted registry; dedup + clustering.",
            "stats": [],
        },
        {
            "id": "extraction",
            "name": "Extraction",
            "state": "pending",
            "summary": "LLM → structured, cited insights tied to people and labs.",
            "stats": [],
        },
        {
            "id": "scoring",
            "name": "Scoring",
            "state": "pending",
            "summary": "Visible dimensions incl. thesis-breaking; validated, not vibes.",
            "stats": [],
        },
        {
            "id": "delivery",
            "name": "Delivery",
            "state": "pending",
            "summary": "Persona digests and alerts for investment and AI teams.",
            "stats": [],
        },
    ]
    return JSONResponse({"stages": stages})


@app.get("/api/accounts")
def accounts(
    limit: int = Query(100, le=500),
    offset: int = 0,
    q: str = "",
) -> JSONResponse:
    conn = _model_conn()
    try:
        where = ""
        params: list = []
        if q:
            where = "AND (c.key LIKE ? OR c.label LIKE ?)"
            params = [f"%{q}%", f"%{q}%"]
        rows = conn.execute(
            f"""
            SELECT c.id, c.key AS handle, c.label AS display_name,
                   (SELECT o.value FROM channel_observations o
                    WHERE o.channel_id = c.id AND o.source = 'x_profile' AND o.metric = 'bio'
                    ORDER BY o.observed_at DESC LIMIT 1) AS bio,
                   CAST((SELECT o.value FROM channel_observations o
                    WHERE o.channel_id = c.id AND o.source = 'x_profile' AND o.metric = 'followers_count'
                    ORDER BY o.observed_at DESC LIMIT 1) AS INTEGER) AS followers_count,
                   CAST((SELECT o.value FROM channel_observations o
                    WHERE o.channel_id = c.id AND o.source = 'digg' AND o.metric = 'rank'
                    ORDER BY o.observed_at DESC LIMIT 1) AS INTEGER) AS seed_rank,
                   (SELECT o.value FROM channel_observations o
                    WHERE o.channel_id = c.id AND o.source = 'digg' AND o.metric = 'role'
                    ORDER BY o.observed_at DESC LIMIT 1) AS role,
                   (SELECT o.value FROM channel_observations o
                    WHERE o.channel_id = c.id AND o.source = 'digg' AND o.metric = 'github_url'
                    ORDER BY o.observed_at DESC LIMIT 1) AS github_url,
                   (SELECT COUNT(*) FROM graph_edges e
                    JOIN accounts a ON a.id = e.to_account_id
                    WHERE a.handle = c.key) AS graph_follows
            FROM channels c
            WHERE c.kind = 'x' {where}
            ORDER BY seed_rank IS NULL, seed_rank, graph_follows DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
        total = conn.execute(
            f"SELECT COUNT(*) FROM channels c WHERE c.kind = 'x' {where}", params
        ).fetchone()[0]
        return JSONResponse(
            {"total": total, "accounts": [dict(r) for r in rows]}
        )
    finally:
        conn.close()


@app.get("/api/registry")
def registry(limit: int = Query(150, le=500)) -> JSONResponse:
    """The registry: curated lab entities + evidence-ranked people candidates.

    Labs are hand-seeded (judgment; ~10 rows). People have no promotion
    mechanism yet — the "candidates" list is every account with a seed rank
    or a PageRank, ordered by whichever rank is best, excluding accounts
    already linked to a lab (an org shouldn't double-count as a person
    candidate). Honest framing: these are candidates, not tracked entities.
    """
    conn = _model_conn()
    try:
        labs = []
        lab_entities = conn.execute(
            """
            SELECT id, slug, name, notes
            FROM entities
            WHERE kind = 'lab'
            ORDER BY name
            """
        ).fetchall()
        for entity in lab_entities:
            entity_channels = conn.execute(
                """
                SELECT c.id, c.kind, c.key, c.label, c.url
                FROM entity_channels ec
                JOIN channels c ON c.id = ec.channel_id
                WHERE ec.entity_id = ?
                ORDER BY c.kind, c.key
                """,
                (entity["id"],),
            ).fetchall()
            by_kind = {row["kind"]: row for row in entity_channels}
            x_channel = by_kind.get("x")
            followers_count = None
            graph_follows = 0
            linked = False
            if x_channel:
                followers = conn.execute(
                    """SELECT value FROM channel_observations
                       WHERE channel_id = ? AND source = 'x_profile'
                         AND metric = 'followers_count'
                       ORDER BY observed_at DESC LIMIT 1""",
                    (x_channel["id"],),
                ).fetchone()
                followers_count = int(followers["value"]) if followers else None
                account = conn.execute(
                    "SELECT id FROM accounts WHERE platform = 'x' AND handle = ?",
                    (x_channel["key"],),
                ).fetchone()
                linked = account is not None
                if account:
                    graph_follows = conn.execute(
                        "SELECT COUNT(*) FROM graph_edges WHERE to_account_id = ?",
                        (account["id"],),
                    ).fetchone()[0]
            labs.append(
                {
                    "id": entity["id"],
                    "slug": entity["slug"],
                    "name": entity["name"],
                    "notes": entity["notes"],
                    "x_handle": x_channel["key"] if x_channel else None,
                    "website": by_kind["website"]["url"] if "website" in by_kind else None,
                    "blog_feed": by_kind["blog"]["url"] if "blog" in by_kind else None,
                    "github_org": by_kind["github"]["key"] if "github" in by_kind else None,
                    "arxiv_query": by_kind["arxiv"]["key"] if "arxiv" in by_kind else None,
                    "followers_count": followers_count,
                    "linked": linked,
                    "graph_follows": graph_follows,
                    "channels": [dict(row) for row in entity_channels],
                }
            )

        candidates = conn.execute(
            """
            WITH x AS (
                SELECT c.id, c.key AS handle, c.label AS display_name,
                       (SELECT o.value FROM channel_observations o
                        WHERE o.channel_id = c.id AND o.source = 'x_profile' AND o.metric = 'bio'
                        ORDER BY o.observed_at DESC LIMIT 1) AS bio,
                       CAST((SELECT o.value FROM channel_observations o
                        WHERE o.channel_id = c.id AND o.source = 'x_profile' AND o.metric = 'followers_count'
                        ORDER BY o.observed_at DESC LIMIT 1) AS INTEGER) AS followers_count,
                       CAST((SELECT o.value FROM channel_observations o
                        WHERE o.channel_id = c.id AND o.source = 'digg' AND o.metric = 'rank'
                        ORDER BY o.observed_at DESC LIMIT 1) AS INTEGER) AS seed_rank,
                       CAST((SELECT o.value FROM channel_observations o
                        WHERE o.channel_id = c.id AND o.source = 'graph' AND o.metric = 'pagerank_rank'
                        ORDER BY o.observed_at DESC LIMIT 1) AS INTEGER) AS pagerank_rank,
                       (SELECT o.value FROM channel_observations o
                        WHERE o.channel_id = c.id AND o.source = 'digg' AND o.metric = 'role'
                        ORDER BY o.observed_at DESC LIMIT 1) AS role,
                       c.id NOT IN (
                         SELECT ec.channel_id
                         FROM entity_channels ec
                         JOIN entities e ON e.id = ec.entity_id
                         WHERE e.kind = 'lab'
                       ) AS not_lab_channel,
                       (SELECT COUNT(*) FROM graph_edges e
                        JOIN accounts a ON a.id = e.to_account_id
                        WHERE a.handle = c.key) AS graph_follows
                FROM channels c
                WHERE c.kind = 'x'
            )
            SELECT id, handle, display_name, bio, followers_count, seed_rank,
                   pagerank_rank, role, graph_follows
            FROM x
            WHERE not_lab_channel
              AND (seed_rank IS NOT NULL OR pagerank_rank IS NOT NULL)
            ORDER BY MIN(COALESCE(seed_rank, 999999),
                         COALESCE(pagerank_rank, 999999)) ASC
            LIMIT ?
            """,
            [limit],
        ).fetchall()

        pool_total = conn.execute(
            """
            WITH x AS (
                SELECT c.id,
                       CAST((SELECT o.value FROM channel_observations o
                        WHERE o.channel_id = c.id AND o.source = 'digg' AND o.metric = 'rank'
                        ORDER BY o.observed_at DESC LIMIT 1) AS INTEGER) AS seed_rank,
                       CAST((SELECT o.value FROM channel_observations o
                        WHERE o.channel_id = c.id AND o.source = 'graph' AND o.metric = 'pagerank_rank'
                        ORDER BY o.observed_at DESC LIMIT 1) AS INTEGER) AS pagerank_rank
                FROM channels c
                WHERE c.kind = 'x'
                  AND c.id NOT IN (
                    SELECT ec.channel_id
                    FROM entity_channels ec
                    JOIN entities e ON e.id = ec.entity_id
                    WHERE e.kind = 'lab'
                  )
            )
            SELECT COUNT(*) FROM x
            WHERE seed_rank IS NOT NULL OR pagerank_rank IS NOT NULL
            """
        ).fetchone()[0]

        candidates_out = []
        for r in candidates:
            row = dict(r)
            row["disagreement"] = (
                row["seed_rank"] - row["pagerank_rank"]
                if row["seed_rank"] is not None and row["pagerank_rank"] is not None
                else None
            )
            candidates_out.append(row)

        return JSONResponse(
            {
                "labs": labs,
                "candidates": candidates_out,
                "candidates_pool_total": pool_total,
            }
        )
    finally:
        conn.close()


if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str) -> FileResponse:
        candidate = DIST_DIR / path
        if path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST_DIR / "index.html")
