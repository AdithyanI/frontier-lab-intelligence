"""Read model for the canonical primary-artifact library."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fli import artifacts


DEFAULT_ARTIFACT_DB = artifacts.DEFAULT_DB


def _fetch_state(status: str | None) -> str:
    if status == "success":
        return "ready"
    if status == "failed_retryable":
        return "retryable"
    if status == "failed_terminal":
        return "unavailable"
    if status == "in_progress":
        return "fetching"
    return "catalogued"


def _fetch_method(fetch_policy: str | None) -> str | None:
    if fetch_policy == "jina-reader-v1":
        return "Jina Reader"
    if fetch_policy == "bounded-public-v1":
        return "Direct fetch"
    return fetch_policy


def _missing_catalog(
    reason: str, *, limit: int = 60, offset: int = 0
) -> dict[str, Any]:
    return {
        "available": False,
        "reason": reason,
        "items": [],
        "total": 0,
        "matching_total": 0,
        "limit": limit,
        "offset": offset,
    }


def _like_pattern(query: str) -> str:
    escaped = (
        query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )
    return f"%{escaped}%"


def artifact_dates_payload(
    *, db_path: Path | str | None = None
) -> dict[str, Any]:
    """Return source-evidence dates with distinct artifact counts."""
    path = Path(db_path or DEFAULT_ARTIFACT_DB)
    if not path.is_file():
        return {
            "available": False,
            "reason": "No artifact catalog has been materialized yet.",
            "dates": [],
        }

    conn = artifacts.connect(path)
    try:
        rows = conn.execute(
            """SELECT substr(source_published_at, 1, 10) AS day,
                      COUNT(DISTINCT artifact_id) AS item_count
               FROM artifact_observation
               GROUP BY substr(source_published_at, 1, 10)
               ORDER BY day"""
        ).fetchall()
        dates = [
            {"day": str(row["day"]), "item_count": int(row["item_count"])}
            for row in rows
        ]
        if not dates:
            return {
                "available": False,
                "reason": "The artifact catalog has no dated source evidence yet.",
                "dates": [],
            }
        return {
            "available": True,
            "latest_date": dates[-1]["day"],
            "date_from": dates[0]["day"],
            "date_to": dates[-1]["day"],
            "dates": dates,
        }
    finally:
        conn.close()


def artifacts_payload(
    *,
    day: str | None = None,
    query: str = "",
    limit: int = 60,
    offset: int = 0,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Return artifacts observed on one source-evidence day, newest-first."""
    path = Path(db_path or DEFAULT_ARTIFACT_DB)
    if not path.is_file():
        return _missing_catalog(
            "No artifact catalog has been materialized yet.",
            limit=limit,
            offset=offset,
        )

    conn = artifacts.connect(path)
    try:
        selected_day = day or conn.execute(
            "SELECT MAX(substr(source_published_at, 1, 10)) "
            "FROM artifact_observation"
        ).fetchone()[0]
        if selected_day is None:
            return _missing_catalog(
                "The artifact catalog has no dated source evidence yet.",
                limit=limit,
                offset=offset,
            )

        total = int(conn.execute("SELECT COUNT(*) FROM artifact").fetchone()[0])
        counts = {
            "catalogued": total,
            "ready": 0,
            "retryable": 0,
            "unavailable": 0,
            "fetching": 0,
        }
        status_rows = conn.execute(
            """WITH ranked_fetch AS (
                   SELECT artifact_id, status,
                          ROW_NUMBER() OVER (
                              PARTITION BY artifact_id
                              ORDER BY CASE status
                                  WHEN 'success' THEN 0
                                  WHEN 'in_progress' THEN 1
                                  WHEN 'failed_retryable' THEN 2
                                  ELSE 3 END,
                                  COALESCE(completed_at, started_at) DESC,
                                  attempt_number DESC,
                                  fetch_id DESC
                          ) AS ordinal
                   FROM artifact_fetch
               )
               SELECT status, COUNT(*) AS count
               FROM ranked_fetch
               WHERE ordinal = 1
               GROUP BY status"""
        ).fetchall()
        fetched = 0
        for row in status_rows:
            state = _fetch_state(str(row["status"]))
            count = int(row["count"])
            counts[state] += count
            fetched += count
        counts["catalogued"] = total - fetched

        clean_query = query.strip()
        search_sql = ""
        search_params: tuple[str, ...] = ()
        if clean_query:
            pattern = _like_pattern(clean_query)
            search_sql = """AND (
                    lower(COALESCE(artifact.title, '')) LIKE lower(?) ESCAPE '\\'
                 OR lower(artifact.host) LIKE lower(?) ESCAPE '\\'
                 OR lower(artifact.canonical_url) LIKE lower(?) ESCAPE '\\'
                 OR lower(observation.source_url) LIKE lower(?) ESCAPE '\\'
               )"""
            search_params = (pattern, pattern, pattern, pattern)

        observation_cte = """WITH ranked_observation AS (
                   SELECT observation.*,
                          COUNT(*) OVER (
                              PARTITION BY observation.artifact_id
                          ) AS observation_count,
                          MIN(observation.source_published_at) OVER (
                              PARTITION BY observation.artifact_id
                          ) AS first_source_published_at,
                          MAX(observation.source_published_at) OVER (
                              PARTITION BY observation.artifact_id
                          ) AS last_source_published_at,
                          ROW_NUMBER() OVER (
                              PARTITION BY observation.artifact_id
                              ORDER BY observation.source_published_at DESC,
                                       observation.best_source_rank,
                                       observation.observation_id
                          ) AS ordinal
                   FROM artifact_observation observation
                   WHERE substr(observation.source_published_at, 1, 10) = ?
               )"""

        matching_total = int(
            conn.execute(
                f"""{observation_cte}
                SELECT COUNT(*)
                FROM ranked_observation observation
                JOIN artifact ON artifact.artifact_id = observation.artifact_id
                WHERE observation.ordinal = 1
                  {search_sql}""",
                (selected_day, *search_params),
            ).fetchone()[0]
        )

        rows = conn.execute(
            f"""{observation_cte},
               ranked_fetch AS (
                   SELECT fetch.*,
                          ROW_NUMBER() OVER (
                              PARTITION BY fetch.artifact_id
                              ORDER BY CASE fetch.status
                                  WHEN 'success' THEN 0
                                  WHEN 'in_progress' THEN 1
                                  WHEN 'failed_retryable' THEN 2
                                  ELSE 3 END,
                                  COALESCE(fetch.completed_at, fetch.started_at) DESC,
                                  fetch.attempt_number DESC,
                                  fetch.fetch_id DESC
                          ) AS ordinal
                   FROM artifact_fetch fetch
               )
               SELECT artifact.artifact_id, artifact.canonical_url,
                      artifact.host, artifact.artifact_kind, artifact.title,
                      artifact.first_seen_at, artifact.last_seen_at,
                      observation.observation_count,
                      observation.first_source_published_at,
                      observation.last_source_published_at,
                      observation.source_kind, observation.source_provider,
                      observation.source_url,
                      fetch.status AS fetch_status,
                      fetch.fetch_policy, fetch.completed_at AS fetched_at,
                      fetch.extractor_contract, fetch.text_char_count,
                      fetch.error_code
               FROM ranked_observation observation
               JOIN artifact ON artifact.artifact_id = observation.artifact_id
               LEFT JOIN ranked_fetch fetch
                 ON fetch.artifact_id = artifact.artifact_id
                AND fetch.ordinal = 1
               WHERE observation.ordinal = 1
                 {search_sql}
               ORDER BY observation.source_published_at DESC,
                        artifact.artifact_id
               LIMIT ? OFFSET ?""",
            (selected_day, *search_params, limit, offset),
        ).fetchall()

        items = []
        for row in rows:
            item = dict(row)
            item["observation_count"] = int(item["observation_count"] or 0)
            item["fetch_state"] = _fetch_state(item.pop("fetch_status"))
            item["fetch_method"] = _fetch_method(item.pop("fetch_policy"))
            items.append(item)
        return {
            "available": True,
            "items": items,
            "total": total,
            "matching_total": matching_total,
            "counts": counts,
            "date": selected_day,
            "query": clean_query,
            "limit": limit,
            "offset": offset,
        }
    finally:
        conn.close()
