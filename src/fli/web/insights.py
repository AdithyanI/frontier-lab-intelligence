"""Read-only publication model for Audience Insights v2."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from fli import (
    audience_insight_production_reconciliation,
    audience_insight_publication_audit,
    audience_insight_runs,
    audience_insights,
)


DEFAULT_INSIGHTS_ROOT = audience_insight_runs.DEFAULT_RUN_ROOT
DEFAULT_AUDIENCE = "investment"
PUBLICATION_AUDIT_DIR = "publication-audit-v1"
PRODUCTION_RECONCILIATION_DIR = "production-reconciliation-v2"
PRODUCTION_RECONCILIATION_REPORT = "report.json"
PRODUCTION_RECONCILIATION_MANIFEST = "manifest.json"
PRODUCTION_RECONCILIATION_SCHEMA = (
    audience_insight_production_reconciliation.REPORT_SCHEMA_VERSION
)


def _missing(reason: str, *, audience: str) -> dict[str, Any]:
    return {
        "available": False,
        "reason": reason,
        "audience": audience,
        "run": None,
        "items": [],
    }


def _publication_audit_report(
    path: Path,
) -> dict[str, Any] | None:
    """Return the exact publishable projection without mutating provenance."""
    audit_db = path.parent / PUBLICATION_AUDIT_DIR / "audit.db"
    try:
        return audience_insight_publication_audit.validated_publication_projection(
            source_run_db=path,
            audit_db=audit_db,
        )
    except (
        IndexError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
        sqlite3.Error,
    ):
        return None


def _run_summary(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        run = conn.execute(
            """SELECT run_id, audience, day, updated_at
               FROM run_meta WHERE singleton = 1"""
        ).fetchone()
        editor = conn.execute(
            "SELECT status, selected_count FROM editor_run WHERE singleton = 1"
        ).fetchone()
        gate = conn.execute(
            "SELECT passed, result_json FROM quality_gate WHERE singleton = 1"
        ).fetchone()
        if (
            run is None
            or editor is None
            or editor["status"] != "complete"
            or gate is None
            or int(gate["passed"]) != 1
        ):
            return None
        selected_count = conn.execute(
            """SELECT COUNT(*)
               FROM publication_selection AS selected
               JOIN candidate_item AS item USING (candidate_id)
               WHERE item.status = 'complete' AND item.outcome = 'insight'
                 AND item.citation_source_url IS NOT NULL
                 AND item.citation_source_sha256 IS NOT NULL"""
        ).fetchone()[0]
        gate_result = json.loads(str(gate["result_json"]))
        if int(selected_count) != int(gate_result.get("selected_count", -1)):
            return None
        projection = _publication_audit_report(path)
        if projection is None:
            return None
        return {
            "path": path,
            "run_id": str(run["run_id"]),
            "audience": str(run["audience"]),
            "day": str(run["day"]),
            "updated_at": str(run["updated_at"]),
            "selected_count": int(projection["selected_count"]),
        }
    except (sqlite3.Error, ValueError):
        return None
    finally:
        if conn is not None:
            conn.close()


def _reconciled_run_entries(root: Path) -> list[dict[str, str]]:
    """Return only runs proven by the exact manifest/report pair.

    Production never guesses by recency.  The stored report must equal a fresh
    deterministic evaluation of its adjacent manifest, which revalidates every
    run, audit, finalization, contract, telemetry ledger, chronological history,
    and bound X Article.  Explicit ``run_root`` callers bypass this function so
    isolated fixtures can still exercise discovery behavior.
    """
    publication_dir = root / PRODUCTION_RECONCILIATION_DIR
    report_path = publication_dir / PRODUCTION_RECONCILIATION_REPORT
    manifest_path = publication_dir / PRODUCTION_RECONCILIATION_MANIFEST
    if not report_path.is_file() or not manifest_path.is_file():
        return []
    try:
        stored_report_text = report_path.read_text()
        report = audience_insight_production_reconciliation.evaluate_manifest(
            manifest_path
        )
        if (
            stored_report_text
            != audience_insight_production_reconciliation.canonical_report_text(
                report
            )
            or not isinstance(report, dict)
            or report.get("schema_version") != PRODUCTION_RECONCILIATION_SCHEMA
            or report.get("mode") not in {"partial", "final"}
            or report.get("passed") is not True
        ):
            return []
        runs = report.get("runs")
        if not isinstance(runs, list) or not runs:
            return []
        normalized: list[dict[str, str]] = []
        resolved_root = root.resolve()
        for row in runs:
            path = Path(str(row["source_run_db"])).resolve()
            if not path.is_relative_to(resolved_root):
                return []
            normalized.append(
                {
                    "audience": str(row["audience"]),
                    "day": str(row["day"]),
                    "run_id": str(row["source_run_id"]),
                    "path": str(path),
                }
            )
        return sorted(normalized, key=lambda row: (row["day"], row["audience"]))
    except (
        FileNotFoundError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        sqlite3.Error,
    ):
        return []


def _available_runs(
    *,
    audience: str,
    run_root: Path | str | None = None,
) -> list[dict[str, Any]]:
    audience = audience_insights.require_audience(audience)
    root = Path(run_root or DEFAULT_INSIGHTS_ROOT)
    if run_root is None:
        reconciled_entries = _reconciled_run_entries(root)
        summaries: list[dict[str, Any]] = []
        for entry in reconciled_entries:
            summary = _run_summary(Path(entry["path"]))
            if (
                summary is None
                or summary["audience"] != entry["audience"]
                or summary["day"] != entry["day"]
                or summary["run_id"] != entry["run_id"]
            ):
                return []
            if summary["audience"] == audience:
                summaries.append(summary)
        return sorted(summaries, key=lambda value: value["day"])
    paths = set(root.glob("**/insights.db")) if root.is_dir() else set()
    latest_by_day: dict[str, dict[str, Any]] = {}
    for path in paths:
        summary = _run_summary(path)
        if summary is None or summary["audience"] != audience:
            continue
        current = latest_by_day.get(summary["day"])
        if current is None or (summary["updated_at"], summary["run_id"]) > (
            current["updated_at"],
            current["run_id"],
        ):
            latest_by_day[summary["day"]] = summary
    return sorted(latest_by_day.values(), key=lambda value: value["day"])


def insight_dates_payload(
    *,
    audience: str = DEFAULT_AUDIENCE,
    run_root: Path | str | None = None,
) -> dict[str, Any]:
    """Return complete editor-backed days for exactly one audience."""
    audience = audience_insights.require_audience(audience)
    runs = _available_runs(audience=audience, run_root=run_root)
    if not runs:
        return {
            "available": False,
            "reason": f"No completed {audience.replace('_', ' ')} insight days exist yet.",
            "audience": audience,
            "latest_date": None,
            "dates": [],
        }
    return {
        "available": True,
        "reason": None,
        "audience": audience,
        "latest_date": runs[-1]["day"],
        "dates": [
            {"day": run["day"], "item_count": run["selected_count"]}
            for run in runs
        ],
    }


def insights_payload(
    *,
    audience: str = DEFAULT_AUDIENCE,
    day: str | None = None,
    db_path: Path | str | None = None,
    run_root: Path | str | None = None,
) -> dict[str, Any]:
    """Return only editor-selected, application-verified audience insights."""
    audience = audience_insights.require_audience(audience)
    if db_path is not None:
        path = Path(db_path)
    else:
        runs = _available_runs(audience=audience, run_root=run_root)
        if not runs:
            return _missing(
                f"No completed {audience.replace('_', ' ')} insight days exist yet.",
                audience=audience,
            )
        selected_run = (
            next((run for run in runs if run["day"] == day), None)
            if day is not None
            else runs[-1]
        )
        if selected_run is None:
            return _missing(
                f"No completed {audience.replace('_', ' ')} insights exist for {day}.",
                audience=audience,
            )
        path = Path(selected_run["path"])
    if not path.is_file():
        return _missing("The requested audience insight run does not exist.", audience=audience)

    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        run = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
        editor = conn.execute(
            "SELECT * FROM editor_run WHERE singleton = 1"
        ).fetchone()
        gate = conn.execute(
            "SELECT * FROM quality_gate WHERE singleton = 1"
        ).fetchone()
        if run is None or str(run["audience"]) != audience:
            return _missing(
                "The requested run belongs to a different audience.", audience=audience
            )
        if editor is None or editor["status"] != "complete":
            return _missing(
                "The daily audience editor has not completed.", audience=audience
            )
        if gate is None or int(gate["passed"]) != 1:
            return _missing(
                "The independent audience quality gate has not passed.",
                audience=audience,
            )

        counts = conn.execute(
            """SELECT COUNT(*) AS candidate_count,
                      SUM(status = 'complete') AS complete_count,
                      SUM(status = 'failed') AS failed_count,
                      SUM(outcome = 'insight') AS extracted_count,
                      SUM(outcome = 'no_extractable_insight') AS no_insight_count,
                      SUM(CASE WHEN input_tokens >= 1024 THEN 1 ELSE 0 END)
                          AS cache_eligible_requests,
                      SUM(CASE WHEN cached_tokens > 0 THEN 1 ELSE 0 END)
                          AS cache_hit_requests,
                      COALESCE(SUM(reported_cost_usd), 0.0)
                          AS extraction_cost_usd
               FROM candidate_item"""
        ).fetchone()
        rows = conn.execute(
            """SELECT published.publication_rank AS editorial_rank,
                      published.original_editorial_rank,
                      selected.decision_value,
                      item.candidate_id, item.event_id, item.day,
                      item.feed_rank, item.claim, item.claim_posture,
                      item.why_it_matters, item.audience_fields_json,
                      item.supporting_quote, item.citation_block_index,
                      item.citation_source_type, item.citation_source_id,
                      item.citation_source_url, item.citation_source_author,
                      item.citation_source_title, item.citation_source_sha256,
                      item.citation_section_ordinal,
                      item.citation_char_start, item.citation_char_end
               FROM publication_selection AS published
               JOIN daily_selection AS selected USING (candidate_id)
               JOIN candidate_item AS item USING (candidate_id)
               WHERE item.status = 'complete' AND item.outcome = 'insight'
                 AND item.citation_source_url IS NOT NULL
                 AND item.citation_source_sha256 IS NOT NULL
               ORDER BY published.publication_rank"""
        ).fetchall()
        base_items = [
            {
                "candidate_id": str(row["candidate_id"]),
                "event_id": str(row["event_id"]),
                "day": str(row["day"]),
                "editorial_rank": int(row["editorial_rank"]),
                "original_editorial_rank": int(row["original_editorial_rank"]),
                "feed_rank": int(row["feed_rank"]),
                "decision_value": str(row["decision_value"]),
                "claim": str(row["claim"]),
                "claim_posture": str(row["claim_posture"]),
                "why_it_matters": str(row["why_it_matters"]),
                "audience_fields": json.loads(row["audience_fields_json"]),
                "citation": {
                    "quote": str(row["supporting_quote"]),
                    "url": str(row["citation_source_url"]),
                    "source_type": str(row["citation_source_type"]),
                    "source_id": str(row["citation_source_id"]),
                    "author": row["citation_source_author"],
                    "title": row["citation_source_title"],
                    "source_sha256": str(row["citation_source_sha256"]),
                    "block_index": int(row["citation_block_index"]),
                    "section_ordinal": row["citation_section_ordinal"],
                    "char_start": int(row["citation_char_start"]),
                    "char_end": int(row["citation_char_end"]),
                },
            }
            for row in rows
        ]
        gate_result = json.loads(str(gate["result_json"]))
        base_selected_count = int(gate_result.get("selected_count", -1))
        if base_selected_count != len(base_items):
            return _missing(
                "The selected set failed publication reconciliation.", audience=audience
            )
        projection = _publication_audit_report(path)
        if projection is None:
            return _missing(
                "The independent publication audit has not passed.",
                audience=audience,
            )
        effective_ids = set(projection["effective_selected_ids"])
        items = [item for item in base_items if item["candidate_id"] in effective_ids]
        selected_count = int(projection["selected_count"])
        if selected_count != len(items):
            return _missing(
                "The publication finalization projection is inconsistent.",
                audience=audience,
            )
        review_cost = conn.execute(
            """SELECT
                   COALESCE((SELECT SUM(reported_cost_usd) FROM item_review), 0) +
                   COALESCE((SELECT SUM(reported_cost_usd) FROM day_set_review), 0) +
                   COALESCE((SELECT SUM(reported_cost_usd)
                             FROM reconciled_day_set_review), 0)"""
        ).fetchone()[0]
        total_cost = (
            float(counts["extraction_cost_usd"] or 0)
            + float(editor["reported_cost_usd"] or 0)
            + float(review_cost or 0)
        )
        reconciliation_row = conn.execute(
            "SELECT * FROM selection_reconciliation WHERE singleton = 1"
        ).fetchone()
        reconciliation = (
            {
                "reason_code": str(reconciliation_row["reason_code"]),
                "status": str(reconciliation_row["status"]),
                "removed_candidate_id": str(
                    reconciliation_row["removed_candidate_id"]
                ),
                "removed_editorial_rank": int(
                    reconciliation_row["removed_editorial_rank"]
                ),
                "original_selected_count": len(
                    json.loads(reconciliation_row["original_selected_ids_json"])
                ),
                "active_selected_count": len(
                    json.loads(reconciliation_row["active_selected_ids_json"])
                ),
            }
            if reconciliation_row is not None
            else None
        )
        return {
            "available": bool(items),
            "reason": (
                None
                if items
                else (
                    "No candidate cleared this audience's publication quality "
                    "bar for this day."
                )
            ),
            "audience": audience,
            "run": {
                "run_id": str(run["run_id"]),
                "day": str(run["day"]),
                "audience": audience,
                "prompt_version": str(run["prompt_version"]),
                "editor_prompt_version": str(run["editor_prompt_version"]),
                "model": str(run["model"]),
                "candidate_count": int(counts["candidate_count"] or 0),
                "extracted_count": int(counts["extracted_count"] or 0),
                "selected_count": selected_count,
                "editor_selected_count": int(editor["selected_count"] or 0),
                "selection_reconciliation": reconciliation,
                "publication_finalization": (
                    {
                        "reason_code": projection["finalization"]["reason_code"],
                        "removed_candidate_ids": projection["finalization"][
                            "removed_candidate_ids"
                        ],
                        "finalization_sha256": projection["finalization"][
                            "finalization_sha256"
                        ],
                    }
                    if projection["finalization"] is not None
                    else None
                ),
                "failed_count": int(counts["failed_count"] or 0),
                "reported_cost_usd": round(total_cost, 6),
                "cache_hit_requests": int(counts["cache_hit_requests"] or 0),
                "cache_eligible_requests": int(
                    counts["cache_eligible_requests"] or 0
                ),
            },
            "items": items,
        }
    finally:
        conn.close()
