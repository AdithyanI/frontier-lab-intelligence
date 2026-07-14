"""FastAPI app: JSON API + built SPA host.

The frontend lives in frontend/ (Vite + React + TS) and builds into
src/fli/web/dist, which this app serves. During frontend development,
`npm run dev` in frontend/ proxies /api to this server.

Endpoints:
- /api/status                    pipeline stages with live DB counts (health/ops)
- /api/registry                  paged/searchable typed entity universe
- /api/rankings                  derived cohort-trust ranking (read-only)
- /api/rankings/followers/{id}   which cohort sources follow one account
- /api/feed/dates                materialized complete X evidence dates
- /api/feed                      Registry-aware deterministic signal Feed
- /api/events/dates              exact structural event counts by date
- /api/events                    Registry-aware exact structural event groups
- /api/artifacts/dates           source-evidence dates with artifact counts
- /api/artifacts                 canonical primary-artifact library
- /api/insights/dates            materialized citation-verified insight dates
- /api/insights                  citation-verified insight proof
"""

from datetime import date as calendar_date
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from fli import channels, registry as entity_registry
from fli.web import artifact_library as artifact_store
from fli.web import events as event_store, feed as feed_store, rankings as rankings_store
from fli.web import insights as insight_store

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
    entity_registry.ensure_schema(conn)
    return conn


def _counts() -> dict:
    conn = _model_conn()
    try:
        def one(sql: str) -> int:
            return conn.execute(sql).fetchone()[0]

        return {
            "channels": one("SELECT COUNT(*) FROM channels"),
            "x_channels": one("SELECT COUNT(*) FROM channels WHERE kind = 'x'"),
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
                """SELECT COUNT(*) FROM entities e
                   WHERE e.kind = 'unsure'
                     AND NOT EXISTS (
                         SELECT 1 FROM entity_registry_rejections rejected
                         WHERE rejected.entity_id = e.id
                     )"""
            ),
            "rejected_entities": one(
                "SELECT COUNT(*) FROM entity_registry_rejections"
            ),
        }
    finally:
        conn.close()


def _registry_reach_ranks(conn) -> tuple[dict[int, int], int]:
    """Stable public-reach position across all active Registry entities."""
    rows = conn.execute(
        """WITH reach AS (
               SELECT e.id, e.name, SUM(a.followers_count) AS followers_count
               FROM entities e
               LEFT JOIN entity_registry_rejections rejected
                 ON rejected.entity_id = e.id
               LEFT JOIN entity_channels ec ON ec.entity_id = e.id
               LEFT JOIN channels c ON c.id = ec.channel_id AND c.kind = 'x'
               LEFT JOIN accounts a
                 ON a.platform = 'x' AND a.handle = c.key
               WHERE rejected.entity_id IS NULL
               GROUP BY e.id, e.name
           ), ranked AS (
               SELECT id, followers_count,
                      ROW_NUMBER() OVER (
                          ORDER BY (followers_count IS NULL),
                                   followers_count DESC,
                                   name COLLATE NOCASE,
                                   id
                      ) AS reach_rank,
                      COUNT(*) OVER () AS reach_rank_total
               FROM reach
           )
           SELECT id,
                  CASE WHEN followers_count IS NOT NULL
                       THEN reach_rank END AS reach_rank,
                  reach_rank_total
           FROM ranked"""
    ).fetchall()
    if not rows:
        return {}, 0
    return (
        {
            int(row["id"]): int(row["reach_rank"])
            for row in rows
            if row["reach_rank"] is not None
        },
        int(rows[0]["reach_rank_total"]),
    )


def _add_registry_ranks(conn, entities: list[dict]) -> int:
    """Attach stable Network and X-reach positions to Registry rows."""
    network_ranks = rankings_store.entity_network_ranks()
    reach_ranks, reach_rank_total = _registry_reach_ranks(conn)
    for entity in entities:
        rank = network_ranks.get(entity["id"])
        entity.update(
            {
                "reach_rank": reach_ranks.get(entity["id"]),
                "network_rank": rank["network_rank"] if rank else None,
                "network_follow_count": (
                    rank["cohort_follow_count"] if rank else None
                ),
                "network_follow_share": (
                    rank["cohort_follow_share"] if rank else None
                ),
                "network_source_total": (
                    rank["network_source_total"] if rank else None
                ),
                "network_rank_total": (
                    rank["network_rank_total"] if rank else None
                ),
                "network_channel_count": (
                    rank["channel_count"] if rank else None
                ),
            }
        )
    return reach_rank_total


@app.get("/api/status")
def status() -> JSONResponse:
    c = _counts()
    stages = [
        {
            "id": "sources",
            "name": "Sources",
            "state": "live",
            "summary": "Curated public source lists + raw public-output corpus; trusted-follow graph starts empty.",
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
                {"label": "rejected", "value": c["rejected_entities"]},
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


@app.get("/api/registry")
def registry(
    limit: int = Query(40, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    group: str = Query(
        "all", pattern="^(all|person|organization|unsure|unknown|rejected)$"
    ),
    q: str = Query("", max_length=200),
    sort: str = Query("reach", pattern="^(reach|network)$"),
    direction: str = Query("asc", pattern="^(asc|desc)$"),
) -> JSONResponse:
    """One server-filtered page of the entity universe."""
    conn = _model_conn()
    try:
        counts = entity_registry.kind_counts(conn)
        filtered_total = entity_registry.count_entities(
            conn, group=group, query=q
        )
        if sort == "network" and filtered_total:
            entities = entity_registry.read_entities(
                conn,
                limit=filtered_total,
                offset=0,
                group=group,
                query=q,
                direction="desc",
            )
        else:
            follower_direction = "desc" if direction == "asc" else "asc"
            entities = entity_registry.read_entities(
                conn,
                limit=limit,
                offset=offset,
                group=group,
                query=q,
                direction=follower_direction,
            )
        reach_rank_total = _add_registry_ranks(conn, entities)
        if sort == "network":
            sign = 1 if direction == "asc" else -1
            entities.sort(
                key=lambda entity: (
                    entity["network_rank"] is None,
                    sign * (entity["network_rank"] or 0),
                    entity["name"].casefold(),
                )
            )
            entities = entities[offset : offset + limit]
        return JSONResponse(
            {
                "entities": entities,
                "total": sum(counts.values()),
                "filtered_total": filtered_total,
                "counts": counts,
                "reach_rank_total": reach_rank_total,
                "network_context": rankings_store.entity_network_context(),
                "limit": limit,
                "offset": offset,
                "sort": sort,
                "direction": direction,
            }
        )
    finally:
        conn.close()


@app.get("/api/registry/entity/{entity_id}")
def registry_entity(entity_id: int) -> JSONResponse:
    """One resolved entity with channels, for the shared identity card."""
    conn = _model_conn()
    try:
        entities = entity_registry.read_entities(
            conn, limit=1, entity_id=entity_id
        )
        if not entities:
            return JSONResponse({"detail": "entity not found"}, status_code=404)
        _add_registry_ranks(conn, entities)
        return JSONResponse({"entity": entities[0]})
    finally:
        conn.close()


@app.get("/api/rankings")
def rankings(
    limit: int = Query(160, ge=1, le=2000),
    state: str = Query("all", pattern="^(all|active|unknown)$"),
    q: str = Query("", max_length=200),
) -> JSONResponse:
    """Top of the accepted entity-overlap network ranking."""
    return JSONResponse(rankings_store.rankings_payload(limit, state, q))


@app.get("/api/rankings/followers/{x_id}")
def ranking_followers(
    x_id: str, limit: int = Query(2000, ge=1, le=5000)
) -> JSONResponse:
    """Screened Registry sources following one account, best-ranked first."""
    return JSONResponse(rankings_store.followers_payload(x_id, limit))


@app.get("/api/feed/dates")
def feed_dates() -> JSONResponse:
    """Available complete dates in the latest materialized Feed run."""
    return JSONResponse(feed_store.dates_payload())


@app.get("/api/feed")
def feed(
    feed_date: calendar_date = Query(..., alias="date"),
    lane: str = Query("all", pattern="^(all|network|firsthand)$"),
    sort: str = Query("attention", pattern="^(attention|recent|engagement)$"),
    q: str = Query("", max_length=200),
    limit: int = Query(40, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    """One date of deduplicated evidence, joined to current Registry state."""
    return JSONResponse(
        feed_store.feed_payload(
            day=feed_date.isoformat(),
            lane=lane,
            sort=sort,
            query=q,
            limit=limit,
            offset=offset,
        )
    )


@app.get("/api/events/dates")
def event_dates() -> JSONResponse:
    """Exact structural Event groups available for each Feed date."""
    return JSONResponse(event_store.dates_payload())


@app.get("/api/events")
def events(
    event_date: calendar_date = Query(..., alias="date"),
    lane: str = Query("all", pattern="^(all|network|firsthand)$"),
    sort: str = Query("attention", pattern="^(attention|recent|engagement)$"),
    q: str = Query("", max_length=200),
    event_id: str = Query("", max_length=128),
    triage: str = Query("all", pattern="^(all|keep|drop|not_evaluated)$"),
    projection: str = Query("day", pattern="^(day|week)$"),
    limit: int = Query(40, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    """One date of groups connected only by exact provider relationships."""
    return JSONResponse(
        event_store.events_payload(
            day=event_date.isoformat(),
            lane=lane,
            sort=sort,
            query=q,
            event_id=event_id,
            triage_filter=triage,
            projection=projection,
            limit=limit,
            offset=offset,
        )
    )


@app.get("/api/artifacts")
def artifact_library(
    artifact_date: calendar_date | None = Query(None, alias="date"),
    q: str = Query("", max_length=200),
    limit: int = Query(60, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    """Canonical artifacts observed on an exact source-evidence date."""
    return JSONResponse(
        artifact_store.artifacts_payload(
            day=artifact_date.isoformat() if artifact_date else None,
            query=q,
            limit=limit,
            offset=offset,
        )
    )


@app.get("/api/artifacts/dates")
def artifact_dates() -> JSONResponse:
    """Available source-evidence dates with distinct artifact counts."""
    return JSONResponse(artifact_store.artifact_dates_payload())


@app.get("/api/insights/dates")
def insight_dates() -> JSONResponse:
    """Materialized cited-insight days and verified insight counts."""
    return JSONResponse(insight_store.insight_dates_payload())


@app.get("/api/insights")
def insights(
    insight_date: calendar_date | None = Query(None, alias="date"),
) -> JSONResponse:
    """Publishable insights whose citation spans were verified in application code."""
    return JSONResponse(
        insight_store.insights_payload(
            day=insight_date.isoformat() if insight_date else None
        )
    )


if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str) -> FileResponse:
        candidate = DIST_DIR / path
        if path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST_DIR / "index.html")
