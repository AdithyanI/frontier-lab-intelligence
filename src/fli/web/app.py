"""FastAPI app: JSON API + built SPA host.

The frontend lives in frontend/ (Vite + React + TS) and builds into
src/fli/web/dist, which this app serves. During frontend development,
`npm run dev` in frontend/ proxies /api to this server.

Endpoints:
- /api/status        pipeline stages with live DB counts (the system map)
- /api/accounts      modeled accounts with Digg facts, sortable/paginated
"""

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from fli import graph

DIST_DIR = Path(__file__).parent / "dist"

app = FastAPI(title="Frontier Lab Intelligence")


def _counts() -> dict:
    conn = graph.connect()
    try:
        def one(sql: str) -> int:
            return conn.execute(sql).fetchone()[0]

        return {
            "accounts": one("SELECT COUNT(*) FROM accounts"),
            "ranked_accounts": one(
                "SELECT COUNT(*) FROM account_source_facts"
                " WHERE source = 'digg' AND fact = 'rank'"
            ),
            "edges": one("SELECT COUNT(*) FROM graph_edges"),
            "facts": one("SELECT COUNT(*) FROM account_source_facts"),
            "raw_items": one("SELECT COUNT(*) FROM raw_items"),
            "fact_sources": one(
                "SELECT COUNT(DISTINCT source) FROM account_source_facts"
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
            "summary": "Digg X-graph pull + raw lab blogs / arXiv / GitHub corpus.",
            "stats": [
                {"label": "graph edges", "value": c["edges"]},
                {"label": "raw items", "value": c["raw_items"]},
                {"label": "fact sources", "value": c["fact_sources"]},
            ],
        },
        {
            "id": "registry",
            "name": "Registry",
            "state": "in-progress",
            "summary": "Graph-derived candidates awaiting weights, triangulation, review.",
            "stats": [
                {"label": "candidate accounts", "value": c["accounts"]},
                {"label": "ranked by Digg", "value": c["ranked_accounts"]},
                {"label": "confirmed entities", "value": 0},
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
    conn = graph.connect()
    try:
        where = ""
        params: list = []
        if q:
            where = "WHERE a.handle LIKE ? OR a.display_name LIKE ?"
            params = [f"%{q}%", f"%{q}%"]
        rows = conn.execute(
            f"""
            SELECT a.id, a.handle, a.display_name, a.bio, a.followers_count,
                   CAST(rank.value AS INTEGER) AS digg_rank,
                   role.value AS role,
                   gh.value AS github_url,
                   (SELECT COUNT(*) FROM graph_edges e
                    WHERE e.to_account_id = a.id) AS tracked_followers
            FROM accounts a
            LEFT JOIN account_source_facts rank
              ON rank.account_id = a.id AND rank.source = 'digg' AND rank.fact = 'rank'
            LEFT JOIN account_source_facts role
              ON role.account_id = a.id AND role.source = 'digg' AND role.fact = 'role'
            LEFT JOIN account_source_facts gh
              ON gh.account_id = a.id AND gh.source = 'digg' AND gh.fact = 'github_url'
            {where}
            ORDER BY digg_rank IS NULL, digg_rank, tracked_followers DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
        total = conn.execute(
            f"SELECT COUNT(*) FROM accounts a {where}", params
        ).fetchone()[0]
        return JSONResponse(
            {"total": total, "accounts": [dict(r) for r in rows]}
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
