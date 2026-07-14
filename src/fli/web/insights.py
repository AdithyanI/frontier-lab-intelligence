"""Read model for citation-verified insight extraction runs."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from fli import cited_insight_runs


DEFAULT_INSIGHTS_DB = cited_insight_runs.default_run_db(
    cited_insight_runs.DEFAULT_RUN_ID
)
DEFAULT_INSIGHTS_ROOT = cited_insight_runs.DEFAULT_RUN_ROOT


def _missing(reason: str) -> dict[str, Any]:
    return {"available": False, "reason": reason, "run": None, "items": []}


def _run_summary(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        run = conn.execute(
            "SELECT run_id, day, updated_at FROM run_meta WHERE singleton = 1"
        ).fetchone()
        if run is None:
            return None
        verified_count = conn.execute(
            """SELECT COUNT(*)
               FROM insight_item
               WHERE status = 'complete' AND outcome = 'insight'
                 AND citation_source_url IS NOT NULL"""
        ).fetchone()[0]
        return {
            "path": path,
            "run_id": str(run["run_id"]),
            "day": str(run["day"]),
            "updated_at": str(run["updated_at"]),
            "verified_count": int(verified_count),
        }
    except sqlite3.Error:
        return None
    finally:
        if "conn" in locals():
            conn.close()


def _available_runs(
    *, run_root: Path | str | None = None, default_db: Path | str | None = None
) -> list[dict[str, Any]]:
    root = Path(run_root or DEFAULT_INSIGHTS_ROOT)
    paths = set(root.glob("*/insights.db")) if root.is_dir() else set()
    fallback = Path(default_db or DEFAULT_INSIGHTS_DB)
    if (run_root is None or default_db is not None) and fallback.is_file():
        paths.add(fallback)

    latest_by_day: dict[str, dict[str, Any]] = {}
    for path in paths:
        summary = _run_summary(path)
        if summary is None:
            continue
        current = latest_by_day.get(summary["day"])
        if current is None or (summary["updated_at"], summary["run_id"]) > (
            current["updated_at"],
            current["run_id"],
        ):
            latest_by_day[summary["day"]] = summary
    return sorted(latest_by_day.values(), key=lambda value: value["day"])


def insight_dates_payload(
    *, run_root: Path | str | None = None, default_db: Path | str | None = None
) -> dict[str, Any]:
    """Return materialized insight days and their verified insight counts."""
    runs = _available_runs(run_root=run_root, default_db=default_db)
    if not runs:
        return {
            "available": False,
            "reason": "No cited-insight extraction run has been materialized yet.",
            "latest_date": None,
            "dates": [],
        }
    return {
        "available": True,
        "reason": None,
        "latest_date": runs[-1]["day"],
        "dates": [
            {"day": run["day"], "item_count": run["verified_count"]}
            for run in runs
        ],
    }


def insights_payload(
    *,
    day: str | None = None,
    db_path: Path | str | None = None,
    run_root: Path | str | None = None,
) -> dict[str, Any]:
    """Return only publishable insights with application-verified citations."""
    if db_path is not None:
        path = Path(db_path)
    elif day is not None:
        run = next(
            (
                value
                for value in _available_runs(run_root=run_root)
                if value["day"] == day
            ),
            None,
        )
        if run is None:
            return _missing(f"No citation-verified insight run exists for {day}.")
        path = Path(run["path"])
    else:
        path = Path(DEFAULT_INSIGHTS_DB)
    if not path.is_file():
        return _missing("No cited-insight extraction run has been materialized yet.")

    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        run = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
        if run is None:
            return _missing("The cited-insight run has no metadata.")

        counts = conn.execute(
            """SELECT
                   SUM(CASE WHEN status = 'complete' AND outcome = 'insight'
                            AND citation_source_url IS NOT NULL THEN 1 ELSE 0 END)
                       AS verified_count,
                   SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END)
                       AS failed_count,
                   SUM(CASE WHEN input_tokens >= 1024 THEN 1 ELSE 0 END)
                       AS cache_eligible_requests,
                   SUM(CASE WHEN cached_tokens > 0 THEN 1 ELSE 0 END)
                       AS cache_hit_requests,
                   COALESCE(SUM(reported_cost_usd), 0.0) AS reported_cost_usd
               FROM insight_item"""
        ).fetchone()
        rows = conn.execute(
            """SELECT event_id, day, current_rank, claim, why_it_matters,
                      investment_implication, engineering_implication,
                      supporting_quote, citation_source_type,
                      citation_source_id, citation_source_url,
                      citation_source_author, citation_source_title
               FROM insight_item
               WHERE status = 'complete' AND outcome = 'insight'
                 AND citation_source_url IS NOT NULL
               ORDER BY current_rank, event_id"""
        ).fetchall()
        items = [
            {
                "event_id": str(row["event_id"]),
                "day": str(row["day"]),
                "current_rank": int(row["current_rank"]),
                "claim": str(row["claim"]),
                "why_it_matters": str(row["why_it_matters"]),
                "investment_implication": str(row["investment_implication"]),
                "engineering_implication": str(row["engineering_implication"]),
                "citation": {
                    "quote": str(row["supporting_quote"]),
                    "url": str(row["citation_source_url"]),
                    "source_type": str(row["citation_source_type"]),
                    "source_id": str(row["citation_source_id"]),
                    "author": row["citation_source_author"],
                    "title": row["citation_source_title"],
                },
            }
            for row in rows
        ]
        return {
            "available": bool(items),
            "reason": None if items else "The run has no citation-verified insights.",
            "run": {
                "run_id": str(run["run_id"]),
                "day": str(run["day"]),
                "prompt_version": str(run["prompt_version"]),
                "model": str(run["model"]),
                "verified_count": int(counts["verified_count"] or 0),
                "failed_count": int(counts["failed_count"] or 0),
                "reported_cost_usd": round(float(counts["reported_cost_usd"]), 6),
                "cache_hit_requests": int(counts["cache_hit_requests"] or 0),
                "cache_eligible_requests": int(
                    counts["cache_eligible_requests"] or 0
                ),
            },
            "items": items,
        }
    finally:
        conn.close()
