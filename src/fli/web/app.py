"""FastAPI app: JSON API + built SPA host.

The frontend lives in frontend/ (Vite + React + TS) and builds into
src/fli/web/dist, which this app serves. During frontend development,
`npm run dev` in frontend/ proxies /api to this server.

Endpoints:
- /api/status        pipeline stages with live DB counts (health/ops)
- /api/accounts      compatibility route for X channels, sortable/paginated
- /api/registry      complete typed entity universe
"""

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from fli import channels, registry as entity_registry

DIST_DIR = Path(__file__).parent / "dist"

app = FastAPI(title="Frontier Lab Intelligence")


def _model_conn():
    conn = channels.connect()
    unlinked = conn.execute(
        """SELECT 1 FROM channels c
           WHERE NOT EXISTS (
               SELECT 1 FROM entity_channels ec WHERE ec.channel_id = c.id
           )
           LIMIT 1"""
    ).fetchone()
    if conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0] == 0 or unlinked:
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
            "classified_entities": one(
                "SELECT COUNT(*) FROM entities WHERE kind <> 'unknown'"
            ),
            "unknown_entities": one(
                "SELECT COUNT(*) FROM entities WHERE kind = 'unknown'"
            ),
            "unsure_entities": one(
                "SELECT COUNT(*) FROM entities WHERE kind = 'unsure'"
            ),
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
            "state": "live",
            "summary": "Every observed channel resolves to a structurally typed entity; unsure identities remain explicit.",
            "stats": [
                {"label": "entity universe", "value": c["entities"]},
                {"label": "classified", "value": c["classified_entities"]},
                {"label": "unsure", "value": c["unsure_entities"]},
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
def registry(limit: int = Query(150, le=5000)) -> JSONResponse:
    """The complete entity universe with only identity-bearing fields."""
    conn = _model_conn()
    try:
        counts = entity_registry.kind_counts(conn)
        return JSONResponse(
            {
                "entities": entity_registry.read_entities(conn, limit=limit),
                "total": sum(counts.values()),
                "counts": counts,
                "lab_count": entity_registry.lab_count(conn),
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
