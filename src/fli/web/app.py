"""FastAPI app: JSON API + built SPA host.

The frontend lives in frontend/ (Vite + React + TS) and builds into
src/fli/web/dist, which this app serves. During frontend development,
`npm run dev` in frontend/ proxies /api to this server.

Endpoints:
- /api/registry                  paged/searchable typed entity universe
- /api/rankings                  derived cohort-trust ranking (read-only)
- /api/rankings/followers/{id}   which cohort sources follow one account
- /api/feed/dates                materialized complete X evidence dates
- /api/feed                      Registry-aware deterministic signal Feed
- /api/events/dates              exact structural event counts by date
- /api/events                    Registry-aware exact structural event groups
- /api/artifacts/dates           source-evidence dates with artifact counts
- /api/artifacts                 canonical primary-artifact library
- /api/artifacts/{id}/text       normalized readable artifact snapshot
- /api/insights/dates            successor audience Insight dates
- /api/insights                  successor audience Insights
- /api/insights/report.pdf       cached daily editorial PDF workbook
"""

from contextlib import asynccontextmanager
from datetime import date as calendar_date
from pathlib import Path
from threading import Thread
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from fli.ingestion import sources
from fli.insights import editorial_runs as editorial_store
from fli.insights import pdf_report
from fli.insights import view as insight_store
from fli.network import view as rankings_store
from fli.registry import channels
from fli.registry import classification as entity_kinds
from fli.registry import intake as registry_intake
from fli.registry import store as entity_registry
from fli.registry import view as entity_registry_view
from fli.web import artifact_library as artifact_store
from fli.web import events as event_store, feed as feed_store

DIST_DIR = Path(__file__).parent / "dist"


@asynccontextmanager
async def _lifespan(_: FastAPI):
    # The always-on local production service starts at login. Warm the one
    # expensive immutable summary before a person opens Feed, without delaying
    # health/static responses while it is being built.
    Thread(
        target=event_store.dates_payload,
        name="fli-feed-date-warmup",
        daemon=True,
    ).start()
    yield


app = FastAPI(title="Frontier Lab Intelligence", lifespan=_lifespan)


class RegistryIntakeRequest(BaseModel):
    profile: str = Field(min_length=1, max_length=500)
    mode: Literal["screen", "direct"]
    reason: str | None = Field(default=None, max_length=500)


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
        counts = entity_registry_view.kind_counts(conn)
        filtered_total = entity_registry_view.count_entities(
            conn, group=group, query=q
        )
        if sort == "network" and filtered_total:
            entities = entity_registry_view.read_entities(
                conn,
                limit=filtered_total,
                offset=0,
                group=group,
                query=q,
                direction="desc",
            )
        else:
            follower_direction = "desc" if direction == "asc" else "asc"
            entities = entity_registry_view.read_entities(
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
        entities = entity_registry_view.read_entities(
            conn, limit=1, entity_id=entity_id
        )
        if not entities:
            return JSONResponse({"detail": "entity not found"}, status_code=404)
        _add_registry_ranks(conn, entities)
        return JSONResponse({"entity": entities[0]})
    finally:
        conn.close()


@app.post("/api/registry/intake")
def registry_profile_intake(request: RegistryIntakeRequest) -> JSONResponse:
    """Screen or directly admit one X profile from the operator UI."""
    conn = _model_conn()
    try:
        try:
            result = registry_intake.run_intake(
                conn,
                profile=request.profile,
                mode=request.mode,
                reason=request.reason,
                llm_client=entity_kinds.create_litellm_client,
                post_client=sources.create_twitterapi_io_client,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except sources.SourceCliError as error:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": error.code,
                    "message": error.message,
                    "hint": error.hint,
                    "retryable": error.retryable,
                },
            ) from error
        entity = None
        if result["entity_id"] is not None:
            entities = entity_registry_view.read_entities(
                conn, limit=1, entity_id=int(result["entity_id"])
            )
            if entities:
                _add_registry_ranks(conn, entities)
                entity = entities[0]
        return JSONResponse({**result, "entity": entity})
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
    routing: str = Query(
        "all",
        pattern="^(all|relevant|not_relevant|not_evaluated)$",
    ),
    projection: str = Query("day", pattern="^(day|week)$"),
    include_evidence: bool = Query(True),
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
            routing_filter=routing,
            projection=projection,
            include_evidence=include_evidence,
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


@app.get("/api/artifacts/{artifact_id}/text")
def artifact_text(artifact_id: str) -> PlainTextResponse:
    """Readable normalized text for one successfully retrieved artifact."""
    payload = artifact_store.artifact_text_payload(artifact_id)
    if not payload["available"]:
        raise HTTPException(status_code=404, detail=payload["reason"])
    return PlainTextResponse(
        payload["text"],
        headers={
            "Cache-Control": "private, max-age=31536000, immutable",
            "X-Artifact-Extractor": str(payload["extractor_contract"] or "unknown"),
            "X-Artifact-Format": str(payload["format"]),
        },
    )


@app.get("/api/insights/dates")
def insight_dates(
    audience: Literal["investment", "ai_engineering"] = "investment",
) -> JSONResponse:
    """Available successor Insight dates for one audience."""
    payload = insight_store.insight_dates_payload(audience=audience)
    editorial = editorial_store.editorial_insight_dates_payload(audience=audience)
    candidate_dates = {
        str(item["day"]): {
            "day": str(item["day"]),
            "content_kind": "candidate_decisions",
            "item_count": int(item["item_count"]),
            "candidate_count": int(item["evaluated_count"]),
            "included_candidate_count": int(item["item_count"]),
            "not_selected_candidate_count": int(item["suppressed_count"]),
        }
        for item in payload.get("dates", [])
    }
    if not editorial["available"]:
        return JSONResponse({**payload, "dates": list(candidate_dates.values())})
    dates = candidate_dates
    for item in editorial["dates"]:
        day = str(item["day"])
        dates[day] = {
            "day": day,
            "content_kind": "daily_editorial",
            "item_count": int(item["item_count"]),
            "candidate_count": int(item["candidate_count"]),
            "included_candidate_count": int(item["included_candidate_count"]),
            "not_selected_candidate_count": int(item["not_selected_candidate_count"]),
        }
    ordered = [dates[day] for day in sorted(dates)]
    return JSONResponse(
        {
            **payload,
            "available": True,
            "reason": None,
            "latest_date": ordered[-1]["day"],
            "dates": ordered,
        }
    )


@app.get("/api/insights")
def insights(
    insight_date: calendar_date | None = Query(None, alias="date"),
    audience: Literal["investment", "ai_engineering"] = "investment",
    status: Literal["kept", "suppressed", "all"] = "kept",
) -> JSONResponse:
    """Successor audience Insights ordered by application-owned Feed rank."""
    day = insight_date.isoformat() if insight_date else None
    if status == "kept":
        editorial = editorial_store.editorial_insights_payload(
            audience=audience,
            day=day,
        )
        if editorial["available"]:
            return JSONResponse(editorial)
    payload = insight_store.insights_payload(
        audience=audience,
        day=day,
        status=status,
    )
    payload["content_kind"] = "candidate_decisions"
    return JSONResponse(payload)


@app.get("/api/insights/report.pdf")
def insight_report_pdf(
    request: Request,
    insight_date: calendar_date | None = Query(None, alias="date"),
    audience: Literal["investment", "ai_engineering"] = "investment",
) -> Response:
    """Download one cached PDF from the canonical complete daily editorial run."""
    day = insight_date.isoformat() if insight_date else None
    payload = editorial_store.editorial_insights_payload(
        audience=audience,
        day=day,
    )
    try:
        artifact = pdf_report.get_or_create_report(
            payload,
            cache_root=pdf_report.DEFAULT_CACHE_ROOT,
        )
    except pdf_report.ReportUnavailable as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    etag = f'"{artifact.etag}"'
    headers = {
        "Cache-Control": "private, no-cache",
        "Content-Language": "en",
        "ETag": etag,
        "X-FLI-PDF-Cache": "hit" if artifact.cache_hit else "miss",
        "X-FLI-Report-Version": artifact.report_version,
    }
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return FileResponse(
        artifact.path,
        media_type="application/pdf",
        filename=artifact.filename,
        headers=headers,
    )


if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        candidate = DIST_DIR / path
        if path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST_DIR / "index.html")
