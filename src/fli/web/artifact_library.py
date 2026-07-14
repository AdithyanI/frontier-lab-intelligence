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


def artifacts_payload(
    *,
    limit: int = 60,
    offset: int = 0,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Return canonical artifacts newest-first with compact provenance."""
    path = Path(db_path or DEFAULT_ARTIFACT_DB)
    if not path.is_file():
        return {
            "available": False,
            "reason": "No artifact catalog has been materialized yet.",
            "items": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
        }

    conn = artifacts.connect(path)
    try:
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

        rows = conn.execute(
            """WITH observation_rollup AS (
                   SELECT artifact_id,
                          COUNT(*) AS observation_count,
                          MIN(source_published_at) AS first_source_published_at,
                          MAX(source_published_at) AS last_source_published_at
                   FROM artifact_observation
                   GROUP BY artifact_id
               ),
               ranked_observation AS (
                   SELECT observation.*,
                          ROW_NUMBER() OVER (
                              PARTITION BY observation.artifact_id
                              ORDER BY observation.best_source_rank,
                                       observation.source_published_at,
                                       observation.observation_id
                          ) AS ordinal
                   FROM artifact_observation observation
               ),
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
                      rollup.observation_count,
                      rollup.first_source_published_at,
                      rollup.last_source_published_at,
                      observation.source_kind, observation.source_provider,
                      observation.source_url,
                      fetch.status AS fetch_status,
                      fetch.fetch_policy, fetch.completed_at AS fetched_at,
                      fetch.extractor_contract, fetch.text_char_count,
                      fetch.error_code
               FROM artifact
               LEFT JOIN observation_rollup rollup
                 ON rollup.artifact_id = artifact.artifact_id
               LEFT JOIN ranked_observation observation
                 ON observation.artifact_id = artifact.artifact_id
                AND observation.ordinal = 1
               LEFT JOIN ranked_fetch fetch
                 ON fetch.artifact_id = artifact.artifact_id
                AND fetch.ordinal = 1
               ORDER BY COALESCE(
                            rollup.last_source_published_at,
                            artifact.last_seen_at
                        ) DESC,
                        artifact.artifact_id
               LIMIT ? OFFSET ?""",
            (limit, offset),
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
            "counts": counts,
            "limit": limit,
            "offset": offset,
        }
    finally:
        conn.close()
