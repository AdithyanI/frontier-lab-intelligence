"""Deterministic read-only production reconciliation for Audience Insights v2.

The manifest is the scope boundary: every audience/day, source run, adjacent
audit, expected base selection count, and optional finalization sidecar is
named explicitly.  No directory discovery or recency heuristic participates
in the report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping

from fli import artifact_x_articles
from fli import audience_insight_evaluations
from fli import audience_insight_publication_audit as publication_audit
from fli import audience_insight_recall
from fli import audience_insight_runs
from fli import audience_insights


MANIFEST_SCHEMA_VERSION = "audience-insight-production-reconciliation-manifest-v2"
REPORT_SCHEMA_VERSION = "audience-insight-production-reconciliation-report-v2"
RECONCILIATION_VERSION = "audience-insight-production-reconciliation-v2"
RECONCILIATION_MODES = ("partial", "final")
RELEASE_STATUS_PUBLISHABLE = "publishable"
RELEASE_STATUS_INTERNAL_GATE_QUARANTINE = "internal_gate_quarantine"
RELEASE_STATUSES = (
    RELEASE_STATUS_PUBLISHABLE,
    RELEASE_STATUS_INTERNAL_GATE_QUARANTINE,
)
QUARANTINE_FAILURE_REASONS = ("no_padding",)
QUALITY_GATE_CHECKS = frozenset(
    {
        "selected_ids_valid",
        "selected_ids_unique",
        "selected_count_within_editor_bound",
        "schema_checks_passed",
        "citation_checks_passed",
        "editor_output_valid",
        "reviewer_coverage",
        "day_set_review_valid",
        "claim_fidelity_and_epistemics",
        "quality_threshold",
        "thin_day_honest_and_all_quality",
        "no_duplicate_stories",
        "no_padding",
        "no_unhandled_items",
    }
)
FINAL_DAYS = tuple(f"2026-07-{day:02d}" for day in range(5, 14))
CONTRACT_STAGES = ("extraction", "editor", "item_review", "day_review")
CONTRACT_FIELDS = {
    "model",
    "reasoning_effort",
    "prompt_version",
    "prompt_sha256",
    "schema_version",
}
# These downstream efforts are frozen production routing decisions, not
# provider defaults inferred at reconciliation time. Extraction effort is
# audience-owned by audience_insights.default_extraction_effort so the runner
# and reconciler cannot drift.
FINAL_REASONING_EFFORTS = {
    "investment": {
        "editor": "high",
        "item_review": "high",
        "day_review": "high",
    },
    "ai_engineering": {
        "editor": "high",
        "item_review": "high",
        "day_review": "high",
    },
}
ADJACENT_AUDIT = Path("publication-audit-v1") / "audit.db"
ADJACENT_FINALIZATION = (
    Path(publication_audit.FINALIZATION_DIR)
    / publication_audit.FINALIZATION_FILENAME
)
ADJACENT_EDITORIAL_FINALIZATION = (
    Path(publication_audit.EDITORIAL_FINALIZATION_DIR)
    / publication_audit.FINALIZATION_FILENAME
)
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ARTIFACT_ID = re.compile(r"^[0-9a-f]{64}$")
_RECALL_SAMPLE_ID = re.compile(r"^recall-sample-[0-9a-f]{20}$")
REPO_ROOT = Path(__file__).resolve().parents[2]


class ProductionReconciliationError(ValueError):
    """The manifest or a frozen production input violates the contract."""


def current_expected_contracts() -> dict[str, dict[str, dict[str, str]]]:
    """Return the exact current production contracts bound by a manifest."""
    contracts: dict[str, dict[str, dict[str, str]]] = {}
    for audience in sorted(audience_insights.AUDIENCES):
        efforts = FINAL_REASONING_EFFORTS[audience]
        contracts[audience] = {
            "extraction": {
                "model": audience_insights.DEFAULT_MODEL,
                "reasoning_effort": (
                    audience_insights.default_extraction_effort(audience)
                ),
                "prompt_version": audience_insights.prompt_version(audience),
                "prompt_sha256": audience_insights.prompt_sha256(audience),
                "schema_version": audience_insights.schema_version(audience),
            },
            "editor": {
                "model": audience_insights.DEFAULT_MODEL,
                "reasoning_effort": efforts["editor"],
                "prompt_version": audience_insights.editor_prompt_version(audience),
                "prompt_sha256": audience_insights.editor_prompt_sha256(audience),
                "schema_version": audience_insights.editor_schema_version(audience),
            },
            "item_review": {
                "model": audience_insight_evaluations.DEFAULT_MODEL,
                "reasoning_effort": efforts["item_review"],
                "prompt_version": audience_insight_evaluations.item_prompt_version(
                    audience
                ),
                "prompt_sha256": audience_insight_evaluations.item_prompt_sha256(
                    audience
                ),
                "schema_version": audience_insight_evaluations.ITEM_SCHEMA_VERSION,
            },
            "day_review": {
                "model": audience_insight_evaluations.DEFAULT_MODEL,
                "reasoning_effort": efforts["day_review"],
                "prompt_version": audience_insight_evaluations.DAY_SET_PROMPT_VERSION,
                "prompt_sha256": (
                    audience_insight_evaluations.day_set_prompt_sha256()
                ),
                "schema_version": (
                    audience_insight_evaluations.DAY_SET_SCHEMA_VERSION
                ),
            },
        }
    return contracts


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _database_binding_sha256(
    conn: sqlite3.Connection,
    tables: Iterable[str],
) -> str:
    """Hash complete visible table state, including uncheckpointed WAL rows."""
    payload: dict[str, Any] = {}
    for table in sorted(tables):
        if re.fullmatch(r"[a-z_]+", table) is None:
            raise ValueError(f"unsafe table name: {table!r}")
        columns = [
            str(row["name"])
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        ]
        if not columns:
            raise ProductionReconciliationError(
                f"binding table is missing: {table}"
            )
        rows = [
            [row[column] for column in columns]
            for row in conn.execute(f"SELECT * FROM {table}").fetchall()
        ]
        rows.sort(key=_canonical_json)
        payload[table] = {"columns": columns, "rows": rows}
    return _sha256(_canonical_json(payload))


SOURCE_BINDING_TABLES = (
    "run_meta",
    "candidate_item",
    "candidate_attempt",
    "editor_run",
    "daily_selection",
    "publication_selection",
    "suppressed_duplicate",
    "item_review",
    "day_set_review",
    "selection_reconciliation",
    "reconciled_day_set_review",
    "quality_gate",
)
AUDIT_BINDING_TABLES = ("audit_run", "audit_item", "audit_attempt")
RECALL_ORIGIN_BINDING_TABLES = (
    "recall_run",
    "recall_sample",
    "recall_replacement",
)


def _open_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(path)
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _require_exact_keys(
    value: Mapping[str, Any], expected: set[str], *, label: str
) -> None:
    if set(value) != expected:
        raise ProductionReconciliationError(
            f"{label} keys do not match the schema; "
            f"missing={sorted(expected - set(value))}, "
            f"extra={sorted(set(value) - expected)}"
        )


def _resolve_path(raw: Any, *, manifest_path: Path, label: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ProductionReconciliationError(f"{label} must be a non-empty path")
    path = Path(raw)
    if not path.is_absolute():
        path = manifest_path.parent / path
    return path.resolve()


def load_manifest(path: Path | str) -> tuple[dict[str, Any], str]:
    """Strictly load and normalize one explicit reconciliation manifest."""
    manifest_path = Path(path).resolve()
    payload = json.loads(manifest_path.read_text())
    if not isinstance(payload, dict):
        raise ProductionReconciliationError("manifest must be a JSON object")
    _require_exact_keys(
        payload,
        {
            "schema_version",
            "reconciliation_id",
            "mode",
            "expected_contracts",
            "expected_audience_days",
            "runs",
            "x_article_cohort",
        },
        label="manifest",
    )
    if payload["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise ProductionReconciliationError(
            f"unsupported manifest schema_version: {payload['schema_version']!r}"
        )
    reconciliation_id = payload["reconciliation_id"]
    if not isinstance(reconciliation_id, str) or not reconciliation_id.strip():
        raise ProductionReconciliationError(
            "reconciliation_id must be a non-empty string"
        )
    mode = payload["mode"]
    if mode not in RECONCILIATION_MODES:
        raise ProductionReconciliationError(
            f"mode must be one of {list(RECONCILIATION_MODES)}"
        )

    raw_contracts = payload["expected_contracts"]
    if not isinstance(raw_contracts, dict):
        raise ProductionReconciliationError("expected_contracts must be an object")
    _require_exact_keys(
        raw_contracts,
        set(audience_insights.AUDIENCES),
        label="expected_contracts",
    )
    current_contracts = current_expected_contracts()
    normalized_contracts: dict[str, dict[str, dict[str, str]]] = {}
    for audience in sorted(audience_insights.AUDIENCES):
        raw_audience = raw_contracts[audience]
        if not isinstance(raw_audience, dict):
            raise ProductionReconciliationError(
                f"expected_contracts.{audience} must be an object"
            )
        _require_exact_keys(
            raw_audience,
            set(CONTRACT_STAGES),
            label=f"expected_contracts.{audience}",
        )
        normalized_stages: dict[str, dict[str, str]] = {}
        for stage in CONTRACT_STAGES:
            raw_stage = raw_audience[stage]
            if not isinstance(raw_stage, dict):
                raise ProductionReconciliationError(
                    f"expected_contracts.{audience}.{stage} must be an object"
                )
            _require_exact_keys(
                raw_stage,
                CONTRACT_FIELDS,
                label=f"expected_contracts.{audience}.{stage}",
            )
            if any(
                not isinstance(raw_stage[field], str)
                or not raw_stage[field].strip()
                for field in CONTRACT_FIELDS
            ):
                raise ProductionReconciliationError(
                    f"expected_contracts.{audience}.{stage} values must be "
                    "non-empty strings"
                )
            normalized_stage = {
                field: raw_stage[field].strip() for field in sorted(CONTRACT_FIELDS)
            }
            expected_current = current_contracts[audience][stage]
            if normalized_stage != expected_current:
                raise ProductionReconciliationError(
                    f"expected_contracts.{audience}.{stage} does not match the "
                    f"current production contract; expected={expected_current}, "
                    f"actual={normalized_stage}"
                )
            normalized_stages[stage] = normalized_stage
        normalized_contracts[audience] = normalized_stages

    expected = payload["expected_audience_days"]
    if not isinstance(expected, dict):
        raise ProductionReconciliationError(
            "expected_audience_days must be an object"
        )
    _require_exact_keys(
        expected,
        set(audience_insights.AUDIENCES),
        label="expected_audience_days",
    )
    expected_pairs: set[tuple[str, str]] = set()
    normalized_expected: dict[str, list[str]] = {}
    for audience in audience_insights.AUDIENCES:
        raw_days = expected[audience]
        if not isinstance(raw_days, list) or not raw_days:
            raise ProductionReconciliationError(
                f"expected_audience_days.{audience} must be a non-empty array"
            )
        if any(
            not isinstance(day, str) or _DAY.fullmatch(day) is None
            for day in raw_days
        ):
            raise ProductionReconciliationError(
                f"expected_audience_days.{audience} must use YYYY-MM-DD"
            )
        if len(raw_days) != len(set(raw_days)):
            raise ProductionReconciliationError(
                f"expected_audience_days.{audience} contains duplicates"
            )
        days = sorted(raw_days)
        normalized_expected[audience] = days
        expected_pairs.update((audience, day) for day in days)
    if mode == "final":
        final_days = list(FINAL_DAYS)
        for audience in audience_insights.AUDIENCES:
            if normalized_expected[audience] != final_days:
                raise ProductionReconciliationError(
                    "final mode requires exactly 2026-07-05 through "
                    f"2026-07-13 for {audience}"
                )

    raw_runs = payload["runs"]
    if not isinstance(raw_runs, list) or not raw_runs:
        raise ProductionReconciliationError("runs must be a non-empty array")
    normalized_runs: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    seen_source_paths: set[Path] = set()
    seen_audit_paths: set[Path] = set()
    seen_finalization_paths: set[Path] = set()
    for index, raw in enumerate(raw_runs):
        if not isinstance(raw, dict):
            raise ProductionReconciliationError(f"runs[{index}] must be an object")
        _require_exact_keys(
            raw,
            {
                "audience",
                "day",
                "source_run_db",
                "audit_db",
                "expected_selected_count",
                "finalization_path",
                "release_status",
            },
            label=f"runs[{index}]",
        )
        audience = raw["audience"]
        if audience not in audience_insights.AUDIENCES:
            raise ProductionReconciliationError(
                f"runs[{index}].audience is unsupported"
            )
        day = raw["day"]
        if not isinstance(day, str) or _DAY.fullmatch(day) is None:
            raise ProductionReconciliationError(
                f"runs[{index}].day must use YYYY-MM-DD"
            )
        pair = (audience, day)
        if pair in seen_pairs:
            raise ProductionReconciliationError(
                f"duplicate audience/day run: {audience}/{day}"
            )
        seen_pairs.add(pair)
        source_path = _resolve_path(
            raw["source_run_db"],
            manifest_path=manifest_path,
            label=f"runs[{index}].source_run_db",
        )
        audit_path = _resolve_path(
            raw["audit_db"],
            manifest_path=manifest_path,
            label=f"runs[{index}].audit_db",
        )
        if audit_path != (source_path.parent / ADJACENT_AUDIT).resolve():
            raise ProductionReconciliationError(
                f"runs[{index}].audit_db is not adjacent to source_run_db"
            )
        if source_path in seen_source_paths:
            raise ProductionReconciliationError(f"duplicate source run: {source_path}")
        if audit_path in seen_audit_paths:
            raise ProductionReconciliationError(f"duplicate audit DB: {audit_path}")
        seen_source_paths.add(source_path)
        seen_audit_paths.add(audit_path)
        selected_count = raw["expected_selected_count"]
        if type(selected_count) is not int or selected_count < 0:
            raise ProductionReconciliationError(
                f"runs[{index}].expected_selected_count must be non-negative"
            )
        release_status = raw["release_status"]
        if release_status not in RELEASE_STATUSES:
            raise ProductionReconciliationError(
                f"runs[{index}].release_status must be one of "
                f"{list(RELEASE_STATUSES)}"
            )
        raw_finalization = raw["finalization_path"]
        if raw_finalization is None:
            finalization_path = None
        else:
            finalization_path = _resolve_path(
                raw_finalization,
                manifest_path=manifest_path,
                label=f"runs[{index}].finalization_path",
            )
            allowed_finalization_paths = {
                (source_path.parent / ADJACENT_FINALIZATION).resolve(),
                (source_path.parent / ADJACENT_EDITORIAL_FINALIZATION).resolve(),
            }
            if finalization_path not in allowed_finalization_paths:
                raise ProductionReconciliationError(
                    f"runs[{index}].finalization_path is not adjacent to source_run_db"
                )
            if finalization_path in seen_finalization_paths:
                raise ProductionReconciliationError(
                    f"duplicate finalization sidecar: {finalization_path}"
                )
            seen_finalization_paths.add(finalization_path)
        if (
            release_status == RELEASE_STATUS_INTERNAL_GATE_QUARANTINE
            and finalization_path is not None
        ):
            raise ProductionReconciliationError(
                f"runs[{index}] internal-gate quarantine cannot name a finalization"
            )
        normalized_runs.append(
            {
                "audience": audience,
                "day": day,
                "source_run_db": str(source_path),
                "audit_db": str(audit_path),
                "expected_selected_count": selected_count,
                "release_status": release_status,
                "finalization_path": (
                    str(finalization_path) if finalization_path is not None else None
                ),
            }
        )
    if seen_pairs != expected_pairs:
        raise ProductionReconciliationError(
            "runs do not match expected_audience_days exactly; "
            f"missing={sorted(expected_pairs - seen_pairs)}, "
            f"extra={sorted(seen_pairs - expected_pairs)}"
        )

    raw_x = payload["x_article_cohort"]
    if raw_x is None:
        normalized_x = None
    else:
        if not isinstance(raw_x, dict):
            raise ProductionReconciliationError(
                "x_article_cohort must be null or an object"
            )
        _require_exact_keys(
            raw_x,
            {"artifact_db", "artifact_ids", "frozen_recall_origin"},
            label="x_article_cohort",
        )
        artifact_db = _resolve_path(
            raw_x["artifact_db"],
            manifest_path=manifest_path,
            label="x_article_cohort.artifact_db",
        )
        artifact_ids = raw_x["artifact_ids"]
        if not isinstance(artifact_ids, list) or not artifact_ids:
            raise ProductionReconciliationError(
                "x_article_cohort.artifact_ids must be a non-empty array"
            )
        if any(
            not isinstance(value, str)
            or _ARTIFACT_ID.fullmatch(value) is None
            for value in artifact_ids
        ):
            raise ProductionReconciliationError(
                "x_article_cohort.artifact_ids must be lowercase SHA-256 IDs"
            )
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ProductionReconciliationError(
                "x_article_cohort.artifact_ids contains duplicates"
            )
        raw_recall = raw_x["frozen_recall_origin"]
        if raw_recall is None:
            normalized_recall = None
        else:
            if not isinstance(raw_recall, dict):
                raise ProductionReconciliationError(
                    "x_article_cohort.frozen_recall_origin must be null or an object"
                )
            _require_exact_keys(
                raw_recall,
                {"recall_db", "binding_sha256", "sample_ids"},
                label="x_article_cohort.frozen_recall_origin",
            )
            recall_db = _resolve_path(
                raw_recall["recall_db"],
                manifest_path=manifest_path,
                label="x_article_cohort.frozen_recall_origin.recall_db",
            )
            binding_sha256 = raw_recall["binding_sha256"]
            if (
                not isinstance(binding_sha256, str)
                or _ARTIFACT_ID.fullmatch(binding_sha256) is None
            ):
                raise ProductionReconciliationError(
                    "x_article_cohort.frozen_recall_origin.binding_sha256 "
                    "must be a lowercase SHA-256"
                )
            sample_ids = raw_recall["sample_ids"]
            if not isinstance(sample_ids, list) or not sample_ids:
                raise ProductionReconciliationError(
                    "x_article_cohort.frozen_recall_origin.sample_ids must be "
                    "a non-empty array"
                )
            if any(
                not isinstance(value, str)
                or _RECALL_SAMPLE_ID.fullmatch(value) is None
                for value in sample_ids
            ):
                raise ProductionReconciliationError(
                    "x_article_cohort.frozen_recall_origin.sample_ids must use "
                    "canonical recall-sample IDs"
                )
            if len(sample_ids) != len(set(sample_ids)):
                raise ProductionReconciliationError(
                    "x_article_cohort.frozen_recall_origin.sample_ids contains "
                    "duplicates"
                )
            normalized_recall = {
                "recall_db": str(recall_db),
                "binding_sha256": binding_sha256,
                "sample_ids": sorted(sample_ids),
            }
        normalized_x = {
            "artifact_db": str(artifact_db),
            "artifact_ids": sorted(artifact_ids),
            "frozen_recall_origin": normalized_recall,
        }
    if mode == "final" and normalized_x is None:
        raise ProductionReconciliationError(
            "final mode requires a non-null exact X Article cohort"
        )

    normalized = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "reconciliation_id": reconciliation_id.strip(),
        "mode": mode,
        "expected_contracts": normalized_contracts,
        "expected_audience_days": normalized_expected,
        "runs": sorted(
            normalized_runs, key=lambda row: (row["day"], row["audience"])
        ),
        "x_article_cohort": normalized_x,
    }
    return normalized, _sha256(_canonical_json(normalized))


_TELEMETRY_REQUIRED_FIELDS = (
    "response_id",
    "response_model",
    "input_tokens",
    "cached_tokens",
    "output_tokens",
    "request_tags_json",
)
_TELEMETRY_TOKEN_FIELDS = (
    "input_tokens",
    "cached_tokens",
    "output_tokens",
)


def _validate_telemetry_record(
    row: Mapping[str, Any], *, stage: str, identity: str, source_path: Path
) -> None:
    null_fields = [field for field in _TELEMETRY_REQUIRED_FIELDS if row[field] is None]
    if null_fields:
        raise ProductionReconciliationError(
            f"{stage} telemetry has null required fields {null_fields} for "
            f"{identity}: {source_path}"
        )
    # The proxy-reported response cost is the operational source of truth. A
    # literal numeric zero is a valid provider report; NULL means the cost is
    # unknown and must never be silently backfilled or coerced to zero.
    if row["reported_cost_usd"] is None:
        raise ProductionReconciliationError(
            f"{stage} telemetry is missing proxy-reported cost for {identity}; "
            "unknown cost cannot be coerced to zero and the run must be "
            f"superseded: {source_path}"
        )
    for field in ("response_id", "response_model"):
        if not isinstance(row[field], str) or not str(row[field]).strip():
            raise ProductionReconciliationError(
                f"{stage} telemetry has an empty {field} for {identity}: "
                f"{source_path}"
            )
    for field in _TELEMETRY_TOKEN_FIELDS:
        value = row[field]
        if type(value) is not int or value < 0:
            raise ProductionReconciliationError(
                f"{stage} telemetry has invalid {field} for {identity}: "
                f"{source_path}"
            )
    cache_write_tokens = row["cache_write_tokens"]
    if cache_write_tokens is not None and (
        type(cache_write_tokens) is not int or cache_write_tokens < 0
    ):
        raise ProductionReconciliationError(
            f"{stage} telemetry has invalid cache_write_tokens for {identity}: "
            f"{source_path}"
        )
    cost = row["reported_cost_usd"]
    if (
        type(cost) not in (int, float)
        or not math.isfinite(float(cost))
        or float(cost) < 0.0
    ):
        raise ProductionReconciliationError(
            f"{stage} telemetry has invalid reported_cost_usd for {identity}: "
            f"{source_path}"
        )
    try:
        tags = json.loads(str(row["request_tags_json"]))
    except json.JSONDecodeError as exc:
        raise ProductionReconciliationError(
            f"{stage} telemetry has invalid request_tags_json for {identity}: "
            f"{source_path}"
        ) from exc
    if (
        not isinstance(tags, list)
        or not tags
        or any(not isinstance(tag, str) or not tag.strip() for tag in tags)
    ):
        raise ProductionReconciliationError(
            f"{stage} telemetry request_tags_json must be a non-empty string "
            f"array for {identity}: {source_path}"
        )


def _telemetry_report(
    rows: Iterable[Mapping[str, Any]],
    *,
    expected_attempts: int,
    stage: str,
    source_path: Path,
) -> dict[str, Any]:
    records = list(rows)
    for index, row in enumerate(records):
        identity = str(row["telemetry_identity"])
        _validate_telemetry_record(
            row,
            stage=stage,
            identity=identity or f"row-{index + 1}",
            source_path=source_path,
        )
    input_tokens = sum(int(row["input_tokens"]) for row in records)
    cached_tokens = sum(int(row["cached_tokens"]) for row in records)
    cache_write_tokens = sum(
        int(row["cache_write_tokens"])
        for row in records
        if row["cache_write_tokens"] is not None
    )
    cache_write_reported = sum(
        row["cache_write_tokens"] is not None for row in records
    )
    output_tokens = sum(int(row["output_tokens"]) for row in records)
    cost = sum(float(row["reported_cost_usd"]) for row in records)
    eligible = sum(int(row["input_tokens"]) >= 1024 for row in records)
    hits = sum(int(row["cached_tokens"]) > 0 for row in records)
    recorded = len(records)
    expected = int(expected_attempts)
    return {
        "attempts": expected,
        "recorded_attempts": recorded,
        "telemetry_missing_attempts": max(expected - recorded, 0),
        "telemetry_surplus_attempts": max(recorded - expected, 0),
        "input_tokens": input_tokens,
        "cached_tokens": cached_tokens,
        "cache_write_tokens": cache_write_tokens,
        "cache_write_tokens_reported_records": cache_write_reported,
        "cache_write_tokens_unreported_records": recorded - cache_write_reported,
        "output_tokens": output_tokens,
        "cache_eligible_requests": eligible,
        "cache_hit_requests": hits,
        "cache_hit_request_ratio": round(hits / eligible, 6) if eligible else 0.0,
        "cache_read_ratio": (
            round(cached_tokens / input_tokens, 6) if input_tokens else 0.0
        ),
        "proxy_reported_cost_usd": round(cost, 9),
        "proxy_cost_records": recorded,
    }


def _validate_attempt_sequences(
    rows: Iterable[Mapping[str, Any]],
    *,
    entity_field: str,
    expected_attempts: Mapping[str, int],
    stage: str,
    source_path: Path,
) -> None:
    observed: dict[str, list[int]] = {}
    for row in rows:
        entity = str(row[entity_field])
        observed.setdefault(entity, []).append(int(row["attempt_number"]))
    expected_entities = {
        entity for entity, attempts in expected_attempts.items() if attempts > 0
    }
    if set(observed) != expected_entities:
        raise ProductionReconciliationError(
            f"{stage} telemetry entities do not match expected attempts; "
            f"missing={sorted(expected_entities - set(observed))}, "
            f"extra={sorted(set(observed) - expected_entities)}: {source_path}"
        )
    for entity in sorted(expected_entities):
        actual_numbers = sorted(observed[entity])
        expected_numbers = list(range(1, expected_attempts[entity] + 1))
        if actual_numbers != expected_numbers:
            raise ProductionReconciliationError(
                f"{stage} telemetry attempt numbers are not contiguous for "
                f"{entity}; expected={expected_numbers}, actual={actual_numbers}: "
                f"{source_path}"
            )


def _reject_zero_attempt_telemetry(
    conn: sqlite3.Connection, *, table: str, stage: str, source_path: Path
) -> None:
    telemetry_fields = (
        *_TELEMETRY_REQUIRED_FIELDS,
        "reported_cost_usd",
        "cache_write_tokens",
    )
    predicates = " OR ".join(f"{field} IS NOT NULL" for field in telemetry_fields)
    count = int(
        conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE attempts = 0 AND ({predicates})"
        ).fetchone()[0]
    )
    if count:
        raise ProductionReconciliationError(
            f"{stage} has telemetry on {count} zero-attempt rows: {source_path}"
        )


def _require_exact_request_tags(
    rows: Iterable[Mapping[str, Any]],
    expected: Iterable[str],
    *,
    stage: str,
    source_path: Path,
) -> None:
    expected_json = _canonical_json(list(expected))
    for row in rows:
        # The generic telemetry validator owns the clearer null-field error.
        if row["request_tags_json"] is None:
            continue
        try:
            actual_json = _canonical_json(json.loads(str(row["request_tags_json"])))
        except (TypeError, json.JSONDecodeError) as exc:
            raise ProductionReconciliationError(
                f"{stage} request tags are invalid: {source_path}"
            ) from exc
        if actual_json != expected_json:
            raise ProductionReconciliationError(
                f"{stage} request tags do not match the frozen contract: "
                f"{source_path}"
            )


def _source_telemetry(
    conn: sqlite3.Connection,
    meta: Mapping[str, Any],
    *,
    source_path: Path,
) -> dict[str, dict[str, Any]]:
    extraction_rows = conn.execute(
        """SELECT candidate_id,
                  candidate_id || ':' || attempt_number AS telemetry_identity,
                  attempt_number, response_id, response_model, input_tokens,
                  cached_tokens, cache_write_tokens, output_tokens,
                  reported_cost_usd, request_tags_json
           FROM candidate_attempt
           ORDER BY candidate_id, attempt_number"""
    ).fetchall()
    extraction_expected = {
        str(row["candidate_id"]): int(row["attempts"])
        for row in conn.execute(
            "SELECT candidate_id, attempts FROM candidate_item"
        ).fetchall()
    }
    _validate_attempt_sequences(
        extraction_rows,
        entity_field="candidate_id",
        expected_attempts=extraction_expected,
        stage="extraction",
        source_path=source_path,
    )
    _require_exact_request_tags(
        extraction_rows,
        audience_insights.request_tags(
            audience=str(meta["audience"]),
            job="insight-extraction",
            run=str(meta["run_id"]),
            day=str(meta["day"]),
            version=str(meta["prompt_version"]),
        ),
        stage="extraction",
        source_path=source_path,
    )
    extraction_attempts = sum(extraction_expected.values())
    _reject_zero_attempt_telemetry(
        conn, table="item_review", stage="review", source_path=source_path
    )
    review_rows = conn.execute(
        """SELECT candidate_id AS telemetry_identity, response_id,
                  response_model, input_tokens, cached_tokens,
                  cache_write_tokens, output_tokens, reported_cost_usd,
                  request_tags_json
           FROM item_review WHERE attempts > 0"""
    ).fetchall()
    _require_exact_request_tags(
        review_rows,
        audience_insight_evaluations.request_tags(
            audience=str(meta["audience"]),
            run=str(meta["run_id"]),
            day=str(meta["day"]),
            prompt_version=str(meta["item_review_prompt_version"]),
        ),
        stage="review",
        source_path=source_path,
    )
    review_attempts = int(
        conn.execute("SELECT COALESCE(SUM(attempts), 0) FROM item_review").fetchone()[0]
    )
    _reject_zero_attempt_telemetry(
        conn, table="editor_run", stage="editor", source_path=source_path
    )
    editor_rows = conn.execute(
        """SELECT 'editor' AS telemetry_identity, response_id,
                  response_model, input_tokens, cached_tokens,
                  cache_write_tokens, output_tokens, reported_cost_usd,
                  request_tags_json
           FROM editor_run WHERE attempts > 0"""
    ).fetchall()
    _require_exact_request_tags(
        editor_rows,
        audience_insights.request_tags(
            audience=str(meta["audience"]),
            job="daily-editor",
            run=str(meta["run_id"]),
            day=str(meta["day"]),
            version=str(meta["editor_prompt_version"]),
        ),
        stage="editor",
        source_path=source_path,
    )
    editor_attempts = int(
        conn.execute("SELECT COALESCE(SUM(attempts), 0) FROM editor_run").fetchone()[0]
    )
    _reject_zero_attempt_telemetry(
        conn, table="day_set_review", stage="day", source_path=source_path
    )
    _reject_zero_attempt_telemetry(
        conn,
        table="reconciled_day_set_review",
        stage="day_reconciliation",
        source_path=source_path,
    )
    initial_day_rows = conn.execute(
        """SELECT 'day-initial' AS telemetry_identity, response_id,
                  response_model, input_tokens, cached_tokens,
                  cache_write_tokens, output_tokens, reported_cost_usd,
                  request_tags_json
           FROM day_set_review WHERE attempts > 0"""
    ).fetchall()
    reconciled_day_rows = conn.execute(
        """SELECT 'day-reconciled' AS telemetry_identity, response_id,
                  response_model, input_tokens, cached_tokens,
                  cache_write_tokens, output_tokens, reported_cost_usd,
                  request_tags_json
           FROM reconciled_day_set_review WHERE attempts > 0"""
    ).fetchall()
    _require_exact_request_tags(
        initial_day_rows,
        audience_insight_evaluations.request_tags(
            audience=str(meta["audience"]),
            run=str(meta["run_id"]),
            day=str(meta["day"]),
            prompt_version=str(meta["day_review_prompt_version"]),
        ),
        stage="day",
        source_path=source_path,
    )
    _require_exact_request_tags(
        reconciled_day_rows,
        audience_insight_evaluations.request_tags(
            audience=str(meta["audience"]),
            run=f"{meta['run_id']}:padding-tail-trim",
            day=str(meta["day"]),
            prompt_version=str(meta["day_review_prompt_version"]),
        ),
        stage="reconciled day",
        source_path=source_path,
    )
    day_rows = [*initial_day_rows, *reconciled_day_rows]
    day_attempts = int(
        conn.execute(
            """SELECT
                   COALESCE((SELECT SUM(attempts) FROM day_set_review), 0) +
                   COALESCE((SELECT SUM(attempts)
                             FROM reconciled_day_set_review), 0)"""
        ).fetchone()[0]
    )
    return {
        "extraction": _telemetry_report(
            extraction_rows,
            expected_attempts=extraction_attempts,
            stage="extraction",
            source_path=source_path,
        ),
        "review": _telemetry_report(
            review_rows,
            expected_attempts=review_attempts,
            stage="review",
            source_path=source_path,
        ),
        "editor": _telemetry_report(
            editor_rows,
            expected_attempts=editor_attempts,
            stage="editor",
            source_path=source_path,
        ),
        "day": _telemetry_report(
            day_rows,
            expected_attempts=day_attempts,
            stage="day",
            source_path=source_path,
        ),
    }


def _audit_telemetry(
    conn: sqlite3.Connection, *, source_path: Path
) -> dict[str, Any]:
    rows = conn.execute(
        """SELECT audit_item_id,
                  audit_item_id || ':' || attempt_number AS telemetry_identity,
                  attempt_number, response_id, response_model, input_tokens,
                  cached_tokens, cache_write_tokens, output_tokens,
                  reported_cost_usd, request_tags_json
           FROM audit_attempt ORDER BY audit_item_id, attempt_number"""
    ).fetchall()
    expected_by_item = {
        str(row["audit_item_id"]): int(row["attempts"])
        for row in conn.execute(
            "SELECT audit_item_id, attempts FROM audit_item"
        ).fetchall()
    }
    _validate_attempt_sequences(
        rows,
        entity_field="audit_item_id",
        expected_attempts=expected_by_item,
        stage="audit",
        source_path=source_path,
    )
    return _telemetry_report(
        rows,
        expected_attempts=sum(expected_by_item.values()),
        stage="audit",
        source_path=source_path,
    )


def _validate_telemetry(
    telemetry: Mapping[str, Mapping[str, Any]], *, source_path: Path
) -> None:
    for stage, report in telemetry.items():
        missing = int(report["telemetry_missing_attempts"])
        surplus = int(report["telemetry_surplus_attempts"])
        recorded = int(report["recorded_attempts"])
        cost_records = int(report["proxy_cost_records"])
        if missing or surplus:
            raise ProductionReconciliationError(
                f"{stage} telemetry attempt count is not exact; missing={missing}, "
                f"surplus={surplus}: {source_path}"
            )
        if cost_records != recorded:
            raise ProductionReconciliationError(
                f"{stage} telemetry is missing provider-reported cost for "
                f"{recorded - cost_records} attempts: {source_path}"
            )


_RUN_CONTRACT_COLUMNS = {
    "extraction": {
        "model": "model",
        "reasoning_effort": "reasoning_effort",
        "prompt_version": "prompt_version",
        "prompt_sha256": "prompt_sha256",
        "schema_version": "schema_version",
    },
    "editor": {
        "model": "editor_model",
        "reasoning_effort": "editor_reasoning_effort",
        "prompt_version": "editor_prompt_version",
        "prompt_sha256": "editor_prompt_sha256",
        "schema_version": "editor_schema_version",
    },
    "item_review": {
        "model": "review_model",
        "reasoning_effort": "review_reasoning_effort",
        "prompt_version": "item_review_prompt_version",
        "prompt_sha256": "item_review_prompt_sha256",
        "schema_version": "item_review_schema_version",
    },
    "day_review": {
        "model": "review_model",
        "reasoning_effort": "review_reasoning_effort",
        "prompt_version": "day_review_prompt_version",
        "prompt_sha256": "day_review_prompt_sha256",
        "schema_version": "day_review_schema_version",
    },
}


def _validate_run_contract(
    meta: Mapping[str, Any],
    expected_contract: Mapping[str, Mapping[str, str]],
    *,
    source_path: Path,
) -> dict[str, dict[str, str]]:
    observed: dict[str, dict[str, str]] = {}
    for stage in CONTRACT_STAGES:
        stage_observed = {
            field: str(meta[column])
            for field, column in _RUN_CONTRACT_COLUMNS[stage].items()
        }
        if stage_observed != dict(expected_contract[stage]):
            raise ProductionReconciliationError(
                f"{stage} contract does not match manifest; "
                f"expected={dict(expected_contract[stage])}, "
                f"actual={stage_observed}: {source_path}"
            )
        observed[stage] = stage_observed
    return observed


def _validate_frozen_cohort(
    conn: sqlite3.Connection,
    meta: Mapping[str, Any],
    *,
    source_path: Path,
) -> dict[str, Any]:
    """Rebuild the immutable candidate cohort from its runner-owned fields."""
    audience = str(meta["audience"])
    day = str(meta["day"])
    render_version = audience_insight_runs.declared_input_render_version(conn)
    rows = conn.execute(
        """SELECT candidate_id, event_id, day, feed_rank, packet_json,
                  input_text, input_sha256, prompt_cache_key
           FROM candidate_item
           ORDER BY feed_rank, event_id"""
    ).fetchall()
    event_ids: list[str] = []
    packet_payloads: list[dict[str, Any]] = []
    for row in rows:
        candidate_id = str(row["candidate_id"])
        event_id = str(row["event_id"])
        expected_candidate_id = audience_insight_runs._candidate_id(
            day, audience, event_id
        )
        if candidate_id != expected_candidate_id:
            raise ProductionReconciliationError(
                f"frozen candidate ID drift for {event_id}: {source_path}"
            )
        try:
            raw_packet = json.loads(str(row["packet_json"]))
            packet = audience_insight_runs._packet_from_payload(raw_packet)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProductionReconciliationError(
                f"frozen packet is invalid for {candidate_id}: {source_path}"
            ) from exc
        canonical_packet = audience_insight_runs._packet_payload(packet)
        if str(row["packet_json"]) != _canonical_json(canonical_packet):
            raise ProductionReconciliationError(
                f"frozen packet is not canonical for {candidate_id}: {source_path}"
            )
        if (
            packet.event_id != event_id
            or packet.day != day
            or str(row["day"]) != day
            or packet.feed_rank != int(row["feed_rank"])
        ):
            raise ProductionReconciliationError(
                f"frozen packet identity drift for {candidate_id}: {source_path}"
            )
        expected_input = audience_insights.render_model_input(
            packet,
            version=render_version,
        )
        if (
            str(row["input_text"]) != expected_input
            or str(row["input_sha256"]) != _sha256(expected_input)
        ):
            raise ProductionReconciliationError(
                f"frozen model input drift for {candidate_id}: {source_path}"
            )
        expected_cache_key = audience_insights.prompt_cache_key(audience, event_id)
        if str(row["prompt_cache_key"]) != expected_cache_key:
            raise ProductionReconciliationError(
                f"extraction cache key drift for {candidate_id}: {source_path}"
            )
        event_ids.append(event_id)
        packet_payloads.append(canonical_packet)

    expected_event_ids_json = _canonical_json(event_ids)
    expected_cohort_sha256 = _sha256(_canonical_json(packet_payloads))
    if (
        str(meta["event_ids_json"]) != expected_event_ids_json
        or str(meta["cohort_sha256"]) != expected_cohort_sha256
        or int(meta["expected_count"]) != len(rows)
    ):
        raise ProductionReconciliationError(
            f"frozen cohort binding drift: {source_path}"
        )
    return {
        "input_render_version": render_version,
        "event_ids_sha256": _sha256(expected_event_ids_json),
        "cohort_sha256": expected_cohort_sha256,
        "candidate_count": len(rows),
    }


def _row_sha256(row: Mapping[str, Any]) -> str:
    return _sha256(_canonical_json(dict(row)))


def _review_selected_ids(row: Mapping[str, Any], *, label: str) -> list[str]:
    try:
        payload = json.loads(str(row["input_text"]))
        selected = payload["selected"]
        ids = [str(item["candidate_id"]) for item in selected]
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ProductionReconciliationError(
            f"{label} does not bind an exact selected set"
        ) from exc
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        raise ProductionReconciliationError(
            f"{label} selected IDs are invalid"
        )
    return ids


def _same_exact_ids(actual: list[str], expected: list[str]) -> bool:
    return len(actual) == len(expected) and set(actual) == set(expected)


def _validate_internal_gate_quarantine(
    source: sqlite3.Connection,
    *,
    source_path: Path,
    gate: Mapping[str, Any],
    gate_result: Mapping[str, Any],
    day_review: Mapping[str, Any],
    reconciliation: Mapping[str, Any] | None,
    reconciled_review: Mapping[str, Any] | None,
    base_ids: list[str],
) -> None:
    """Prove one exact no-padding terminal state without publishing it."""
    checks = gate_result.get("checks")
    expected_failures = list(QUARANTINE_FAILURE_REASONS)
    if (
        int(gate["passed"]) != 0
        or gate_result.get("passed") is not False
        or gate_result.get("failure_reasons") != expected_failures
        or not isinstance(checks, dict)
        or set(checks) != QUALITY_GATE_CHECKS
        or checks.get("no_padding") is not False
        or any(
            value is not True
            for key, value in checks.items()
            if key != "no_padding"
        )
        or gate_result.get("thin_day") is not True
    ):
        raise ProductionReconciliationError(
            f"internal-gate quarantine is not an exact no-padding-only failure: "
            f"{source_path}"
        )
    if reconciliation is None or reconciled_review is None:
        raise ProductionReconciliationError(
            f"internal-gate quarantine requires completed padding reconciliation: "
            f"{source_path}"
        )
    daily_rows = source.execute(
        "SELECT * FROM daily_selection ORDER BY editorial_rank"
    ).fetchall()
    publication_rows = source.execute(
        "SELECT * FROM publication_selection ORDER BY publication_rank"
    ).fetchall()
    daily_ids = [str(row["candidate_id"]) for row in daily_rows]
    if (
        not base_ids
        or len(daily_ids) != len(base_ids) + 1
        or [int(row["editorial_rank"]) for row in daily_rows]
        != list(range(1, len(daily_rows) + 1))
        or [int(row["publication_rank"]) for row in publication_rows]
        != list(range(1, len(publication_rows) + 1))
        or [int(row["original_editorial_rank"]) for row in publication_rows]
        != list(range(1, len(publication_rows) + 1))
        or not _same_exact_ids(
            _review_selected_ids(day_review, label="original day review"),
            daily_ids,
        )
        or str(day_review["status"]) != "complete"
        or int(day_review["padding_detected"] or 0) != 1
    ):
        raise ProductionReconciliationError(
            f"internal-gate quarantine original padding state drift: {source_path}"
        )
    try:
        original_ids = json.loads(str(reconciliation["original_selected_ids_json"]))
        active_ids = json.loads(str(reconciliation["active_selected_ids_json"]))
    except json.JSONDecodeError as exc:
        raise ProductionReconciliationError(
            f"internal-gate quarantine reconciliation IDs are invalid: {source_path}"
        ) from exc
    if (
        str(reconciliation["status"]) != "complete"
        or str(reconciliation["reason_code"]) != "padding_tail_trim"
        or original_ids != daily_ids
        or active_ids != base_ids
        or str(reconciliation["removed_candidate_id"]) != daily_ids[-1]
        or int(reconciliation["removed_editorial_rank"]) != len(daily_ids)
        or str(reconciliation["source_review_input_sha256"])
        != str(day_review["input_sha256"])
        or str(reconciliation["source_review_response_id"])
        != str(day_review["response_id"])
        or str(reconciled_review["status"]) != "complete"
        or str(reconciled_review["reconciliation_reason"])
        != "padding_tail_trim"
        or str(reconciled_review["source_review_input_sha256"])
        != str(day_review["input_sha256"])
        or not _same_exact_ids(
            _review_selected_ids(
                reconciled_review, label="reconciled day review"
            ),
            base_ids,
        )
        or int(reconciled_review["padding_detected"] or 0) != 1
        or int(reconciled_review["thin_day_honest"] or 0) != 1
    ):
        raise ProductionReconciliationError(
            f"internal-gate quarantine reconciled padding state drift: "
            f"{source_path}"
        )


def _inspect_run(
    entry: Mapping[str, Any],
    *,
    expected_contract: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    source_path = Path(str(entry["source_run_db"]))
    audit_path = Path(str(entry["audit_db"]))
    expected_selected = int(entry["expected_selected_count"])
    release_status = str(entry["release_status"])
    finalization_path = (
        Path(str(entry["finalization_path"]))
        if entry["finalization_path"] is not None
        else None
    )
    source = _open_readonly(source_path)
    audit = _open_readonly(audit_path)
    try:
        meta = source.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
        editor = source.execute(
            "SELECT * FROM editor_run WHERE singleton = 1"
        ).fetchone()
        gate = source.execute(
            "SELECT * FROM quality_gate WHERE singleton = 1"
        ).fetchone()
        day_review = source.execute(
            "SELECT * FROM day_set_review WHERE singleton = 1"
        ).fetchone()
        if meta is None or editor is None or gate is None or day_review is None:
            raise ProductionReconciliationError(
                f"source run is incomplete: {source_path}"
            )
        if str(meta["audience"]) != entry["audience"] or str(meta["day"]) != entry["day"]:
            raise ProductionReconciliationError(
                f"manifest audience/day does not match source: {source_path}"
            )
        observed_contract = _validate_run_contract(
            meta, expected_contract, source_path=source_path
        )
        frozen_cohort = _validate_frozen_cohort(
            source,
            meta,
            source_path=source_path,
        )
        if str(editor["status"]) != "complete" or str(day_review["status"]) != "complete":
            raise ProductionReconciliationError(
                f"editor/day review is incomplete: {source_path}"
            )
        counts = dict(
            source.execute(
                """SELECT COUNT(*) AS candidates,
                          SUM(status = 'pending') AS pending,
                          SUM(status = 'complete') AS complete,
                          SUM(status = 'rejected') AS rejected,
                          SUM(status = 'failed') AS failed,
                          SUM(status = 'complete' AND outcome = 'insight') AS insights
                   FROM candidate_item"""
            ).fetchone()
        )
        counts = {key: int(value or 0) for key, value in counts.items()}
        if counts["candidates"] != int(meta["expected_count"]):
            raise ProductionReconciliationError(
                f"candidate count drift in source run: {source_path}"
            )
        if counts["pending"]:
            raise ProductionReconciliationError(
                f"source run still has pending candidates: {source_path}"
            )
        if counts["failed"]:
            raise ProductionReconciliationError(
                f"source run still has retryable failed candidates: {source_path}"
            )
        base_ids = [
            str(row[0])
            for row in source.execute(
                "SELECT candidate_id FROM publication_selection ORDER BY publication_rank"
            ).fetchall()
        ]
        if len(base_ids) != expected_selected:
            raise ProductionReconciliationError(
                f"base publication count does not match manifest: {source_path}"
            )
        gate_result = json.loads(str(gate["result_json"]))
        gate_checks = gate_result.get("checks")
        if (
            gate_result.get("audience") != entry["audience"]
            or gate_result.get("day") != entry["day"]
            or int(gate_result.get("selected_count", -1)) != expected_selected
        ):
            raise ProductionReconciliationError(
                f"internal quality gate result is incomplete or inconsistent: "
                f"{source_path}"
            )
        reconciliation_row = source.execute(
            "SELECT * FROM selection_reconciliation WHERE singleton = 1"
        ).fetchone()
        reconciled_review = source.execute(
            "SELECT * FROM reconciled_day_set_review WHERE singleton = 1"
        ).fetchone()
        gate_reconciliation = gate_result.get("reconciliation")
        if gate_reconciliation is None:
            if reconciliation_row is not None or reconciled_review is not None:
                raise ProductionReconciliationError(
                    f"quality gate omitted an existing padding reconciliation: "
                    f"{source_path}"
                )
        else:
            if (
                not isinstance(gate_reconciliation, dict)
                or reconciliation_row is None
                or str(reconciliation_row["status"]) != "complete"
                or reconciled_review is None
                or str(reconciled_review["status"]) != "complete"
            ):
                raise ProductionReconciliationError(
                    f"padding reconciliation is incomplete: {source_path}"
                )
            expected_reconciliation = {
                "reason_code": str(reconciliation_row["reason_code"]),
                "removed_candidate_id": str(
                    reconciliation_row["removed_candidate_id"]
                ),
                "removed_editorial_rank": int(
                    reconciliation_row["removed_editorial_rank"]
                ),
                "original_selected_count": len(
                    json.loads(str(reconciliation_row["original_selected_ids_json"]))
                ),
                "active_selected_count": len(
                    json.loads(str(reconciliation_row["active_selected_ids_json"]))
                ),
            }
            if gate_reconciliation != expected_reconciliation:
                raise ProductionReconciliationError(
                    f"quality gate padding reconciliation drift: {source_path}"
                )

        if release_status == RELEASE_STATUS_PUBLISHABLE:
            if (
                int(gate["passed"]) != 1
                or gate_result.get("passed") is not True
                or not isinstance(gate_checks, dict)
                or not gate_checks
                or any(value is not True for value in gate_checks.values())
                or gate_result.get("failure_reasons") != []
            ):
                raise ProductionReconciliationError(
                    "internal quality gate result is incomplete or inconsistent: "
                    f"{source_path}"
                )
        elif release_status == RELEASE_STATUS_INTERNAL_GATE_QUARANTINE:
            _validate_internal_gate_quarantine(
                source,
                source_path=source_path,
                gate=gate,
                gate_result=gate_result,
                day_review=day_review,
                reconciliation=reconciliation_row,
                reconciled_review=reconciled_review,
                base_ids=base_ids,
            )
        else:  # load_manifest owns the user-facing enum error.
            raise AssertionError(f"unsupported release status: {release_status}")

        default_editorial_finalization = (
            publication_audit.default_editorial_finalization_path(source_path)
        )
        terminal_finalization = publication_audit.terminal_finalization_path(
            source_path
        )
        if release_status == RELEASE_STATUS_INTERNAL_GATE_QUARANTINE:
            if finalization_path is not None or terminal_finalization.exists():
                raise ProductionReconciliationError(
                    f"internal-gate quarantine cannot have a finalization: "
                    f"{source_path}"
                )
            try:
                audit_report = (
                    publication_audit.validate_readonly_completed_publication_audit(
                        source_run_db=source_path,
                        audit_db=audit_path,
                        expected_selected_count=expected_selected,
                    )
                )
            except (
                FileNotFoundError,
                IndexError,
                KeyError,
                OSError,
                TypeError,
                ValueError,
                sqlite3.Error,
            ) as exc:
                raise ProductionReconciliationError(
                    f"quarantine characterization audit validation failed: "
                    f"{source_path}: {exc}"
                ) from exc
            projection = {
                "base_selected_ids": base_ids,
                "post_audit_selected_ids": [],
                "effective_selected_ids": [],
                "history_selected_ids": [],
                "audit": audit_report,
                "finalization": None,
            }
        elif finalization_path is None:
            if terminal_finalization.exists():
                raise ProductionReconciliationError(
                    f"manifest omitted existing finalization: {terminal_finalization}"
                )
            projection = publication_audit.validated_publication_projection(
                source_run_db=source_path,
                audit_db=audit_path,
            )
        else:
            if (
                default_editorial_finalization.exists()
                and finalization_path != default_editorial_finalization
            ):
                raise ProductionReconciliationError(
                    f"manifest finalization is not the terminal editorial layer: "
                    f"{source_path}"
                )
            try:
                projection = publication_audit.validated_publication_projection(
                    source_run_db=source_path,
                    audit_db=audit_path,
                    finalization_path=finalization_path,
                )
            except (
                FileNotFoundError,
                IndexError,
                KeyError,
                OSError,
                TypeError,
                ValueError,
                sqlite3.Error,
            ) as exc:
                raise ProductionReconciliationError(
                    f"finalization validation failed: {source_path}: {exc}"
                ) from exc
        if projection["base_selected_ids"] != base_ids:
            raise ProductionReconciliationError(
                f"finalization base selection drift: {source_path}"
            )
        audit_report = projection["audit"]
        finalization_report = projection["finalization"]
        post_audit_ids = list(projection["post_audit_selected_ids"])
        effective_ids = list(projection["effective_selected_ids"])
        history_ids = list(projection["history_selected_ids"])
        for label, ids in (
            ("post-audit", post_audit_ids),
            ("effective", effective_ids),
            ("history", history_ids),
        ):
            if len(ids) != len(set(ids)) or any(value not in base_ids for value in ids):
                raise ProductionReconciliationError(
                    f"{label} publication projection is invalid: {source_path}"
                )

        audit_meta = audit.execute(
            "SELECT selected_count, reject_sample_count FROM audit_run WHERE singleton = 1"
        ).fetchone()
        if audit_meta is None or int(audit_meta["selected_count"]) != expected_selected:
            raise ProductionReconciliationError(
                f"audit selected count drift: {audit_path}"
            )
        source_telemetry = _source_telemetry(
            source,
            meta,
            source_path=source_path,
        )
        source_telemetry["audit"] = _audit_telemetry(
            audit, source_path=audit_path
        )
        _validate_telemetry(source_telemetry, source_path=source_path)
        editor_selected = int(
            source.execute("SELECT COUNT(*) FROM daily_selection").fetchone()[0]
        )
        try:
            event_ids = json.loads(str(meta["event_ids_json"]))
        except json.JSONDecodeError as exc:
            raise ProductionReconciliationError(
                f"source event_ids_json is invalid: {source_path}"
            ) from exc
        if (
            not isinstance(event_ids, list)
            or any(not isinstance(event_id, str) or not event_id for event_id in event_ids)
            or len(event_ids) != len(set(event_ids))
        ):
            raise ProductionReconciliationError(
                f"source event_ids_json is not an exact unique ID list: {source_path}"
            )
        prerequisite_report = (
            finalization_report.get("prerequisite_finalization")
            if finalization_report is not None
            else None
        )
        audit_status = "passed"
        if release_status == RELEASE_STATUS_INTERNAL_GATE_QUARANTINE:
            audit_status = "completed_characterization_quarantined"
        elif prerequisite_report is not None:
            audit_status = "failed_selected_audit_and_editorial_finalized"
        elif finalization_report is not None:
            audit_status = (
                "passed_selected_editorial_finalized"
                if finalization_report["reason_code"]
                == publication_audit.EDITORIAL_FINALIZATION_REASON_CODE
                else "failed_selected_finalized"
            )
        return {
            "audience": str(meta["audience"]),
            "day": str(meta["day"]),
            "release_status": release_status,
            "release": {
                "status": release_status,
                "internal_quality_gate_passed": bool(gate_result["passed"]),
                "failure_reasons": list(gate_result["failure_reasons"]),
                "quality_gate_sha256": _row_sha256(gate),
            },
            "source_run_id": str(meta["run_id"]),
            "source_run_db": str(source_path),
            "source_run_db_sha256": _file_sha256(source_path),
            "source_binding_sha256": _database_binding_sha256(
                source,
                SOURCE_BINDING_TABLES,
            ),
            "audit_db": str(audit_path),
            "audit_db_sha256": _file_sha256(audit_path),
            "audit_binding_sha256": _database_binding_sha256(
                audit,
                AUDIT_BINDING_TABLES,
            ),
            "rank_limit": int(meta["rank_limit"]),
            "contracts": observed_contract,
            "frozen_cohort": frozen_cohort,
            "counts": {
                "expected_candidates": int(meta["expected_count"]),
                **counts,
                "editor_selected": editor_selected,
                "base_publication": len(base_ids),
                "effective_publication": len(effective_ids),
            },
            "selection": {
                "base_ids": base_ids,
                "base_ids_sha256": _sha256(_canonical_json(base_ids)),
                "post_audit_ids": post_audit_ids,
                "post_audit_ids_sha256": _sha256(
                    _canonical_json(post_audit_ids)
                ),
                "effective_ids": effective_ids,
                "effective_ids_sha256": _sha256(_canonical_json(effective_ids)),
                "history_ids": history_ids,
                "history_ids_sha256": _sha256(_canonical_json(history_ids)),
            },
            "telemetry": source_telemetry,
            "audit": {
                "status": audit_status,
                "passed": bool(audit_report["passed"]),
                "audit_id": str(audit_report["audit_id"]),
                "selected_count": int(audit_meta["selected_count"]),
                "reject_sample_count": int(audit_meta["reject_sample_count"]),
                "cohort_sha256": str(audit_report["audit_cohort_sha256"]),
                "result_sha256": str(audit_report["audit_result_sha256"]),
                "source_contract_sha256": str(
                    audit_report["source_contract_sha256"]
                ),
                "false_negative_adjudication": audit_report[
                    "false_negative_adjudication"
                ],
            },
            "finalization": (
                {
                    "status": "validated",
                    "path": str(finalization_path),
                    "reason_code": str(finalization_report["reason_code"]),
                    "sha256": str(finalization_report["finalization_sha256"]),
                    "removed_candidate_ids": list(
                        finalization_report["removed_candidate_ids"]
                    ),
                    "prerequisite": (
                        {
                            "path": str(prerequisite_report["path"]),
                            "reason_code": str(prerequisite_report["reason_code"]),
                            "sha256": str(
                                prerequisite_report["finalization_sha256"]
                            ),
                            "effective_selected_ids": list(
                                prerequisite_report["effective_selected_ids"]
                            ),
                        }
                        if prerequisite_report is not None
                        else None
                    ),
                }
                if finalization_report is not None
                else {
                    "status": "not_present",
                    "path": None,
                    "reason_code": None,
                    "sha256": None,
                    "removed_candidate_ids": [],
                    "prerequisite": None,
                }
            ),
            "_event_ids": event_ids,
            "_effective_selected_ids": effective_ids,
            "_history_selected_ids": history_ids,
        }
    finally:
        audit.close()
        source.close()


def _validate_chronological_history(runs: list[dict[str, Any]]) -> None:
    """Prove each editor consumed earlier effective publication projections."""
    for audience in audience_insights.AUDIENCES:
        prior_history: list[dict[str, Any]] = []
        audience_runs = sorted(
            (row for row in runs if row["audience"] == audience),
            key=lambda row: (row["day"], row["source_run_id"]),
        )
        for row in audience_runs:
            source_path = Path(str(row["source_run_db"]))
            source = _open_readonly(source_path)
            try:
                editor = source.execute(
                    "SELECT prior_selected_json, history_sha256 "
                    "FROM editor_run WHERE singleton = 1"
                ).fetchone()
                if editor is None:
                    raise ProductionReconciliationError(
                        f"source editor is missing: {source_path}"
                    )
                expected_json = _canonical_json(prior_history)
                expected_sha256 = _sha256(expected_json)
                if (
                    str(editor["prior_selected_json"]) != expected_json
                    or str(editor["history_sha256"]) != expected_sha256
                ):
                    raise ProductionReconciliationError(
                        "editor history does not match earlier manifest runs' "
                        f"effective selections: {source_path}"
                    )
                row["history"] = {
                    "status": "validated",
                    "prior_item_count": len(prior_history),
                    "prior_history_sha256": expected_sha256,
                }
                prior_history.extend(
                    audience_insight_runs.selected_history_row(
                        source,
                        candidate_ids=row["_history_selected_ids"],
                    )
                )
            finally:
                source.close()


_TELEMETRY_SUM_FIELDS = (
    "attempts",
    "recorded_attempts",
    "telemetry_missing_attempts",
    "telemetry_surplus_attempts",
    "input_tokens",
    "cached_tokens",
    "cache_write_tokens",
    "cache_write_tokens_reported_records",
    "cache_write_tokens_unreported_records",
    "output_tokens",
    "cache_eligible_requests",
    "cache_hit_requests",
    "proxy_cost_records",
)


def _sum_telemetry(reports: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(reports)
    result = {
        field: sum(int(row[field]) for row in rows)
        for field in _TELEMETRY_SUM_FIELDS
    }
    input_tokens = result["input_tokens"]
    eligible = result["cache_eligible_requests"]
    result["cache_hit_request_ratio"] = (
        round(result["cache_hit_requests"] / eligible, 6) if eligible else 0.0
    )
    result["cache_read_ratio"] = (
        round(result["cached_tokens"] / input_tokens, 6) if input_tokens else 0.0
    )
    result["proxy_reported_cost_usd"] = round(
        sum(float(row["proxy_reported_cost_usd"]) for row in rows), 9
    )
    return result


def _run_totals(runs: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(runs)
    count_fields = (
        "expected_candidates",
        "candidates",
        "pending",
        "complete",
        "rejected",
        "failed",
        "insights",
        "editor_selected",
        "base_publication",
        "effective_publication",
    )
    stages = ("extraction", "review", "editor", "day", "audit")
    telemetry = {
        stage: _sum_telemetry(row["telemetry"][stage] for row in rows)
        for stage in stages
    }
    return {
        "run_count": len(rows),
        "counts": {
            field: sum(int(row["counts"][field]) for row in rows)
            for field in count_fields
        },
        "telemetry": telemetry,
        "telemetry_all_stages": _sum_telemetry(telemetry.values()),
    }


def _snapshot_path(raw: Any, *, label: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ProductionReconciliationError(f"{label} is missing")
    path = Path(raw)
    if not path.is_absolute():
        path = REPO_ROOT / path
    path = path.resolve()
    if not path.is_file():
        raise ProductionReconciliationError(f"{label} does not exist: {path}")
    return path


def frozen_recall_origin_binding_sha256(path: Path | str) -> str:
    """Hash the complete frozen recall-origin ledger visible to SQLite."""
    source_path = Path(path).resolve()
    conn = _open_readonly(source_path)
    try:
        return _database_binding_sha256(conn, RECALL_ORIGIN_BINDING_TABLES)
    finally:
        conn.close()


def _resolved_recorded_path(raw: Any, *, label: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ProductionReconciliationError(f"{label} is missing")
    path = Path(raw)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def _inspect_frozen_recall_origin(
    config: Mapping[str, Any] | None,
    *,
    artifact_conn: sqlite3.Connection,
    artifact_db: Path,
    source_event_ids: set[str],
) -> tuple[set[str], dict[str, Any] | None]:
    """Validate exact lower-rank X Articles against one frozen recall ledger."""
    if config is None:
        return set(), None
    recall_path = Path(str(config["recall_db"]))
    conn = _open_readonly(recall_path)
    try:
        binding_sha256 = _database_binding_sha256(
            conn, RECALL_ORIGIN_BINDING_TABLES
        )
        if binding_sha256 != str(config["binding_sha256"]):
            raise ProductionReconciliationError(
                "frozen recall origin binding does not match the manifest: "
                f"{recall_path}"
            )
        meta = conn.execute(
            "SELECT * FROM recall_run WHERE singleton = 1"
        ).fetchone()
        if meta is None:
            raise ProductionReconciliationError(
                f"frozen recall origin is missing recall_run: {recall_path}"
            )
        if str(meta["protocol_version"]) != audience_insight_recall.PROTOCOL_VERSION:
            raise ProductionReconciliationError(
                f"frozen recall origin uses an unsupported protocol: {recall_path}"
            )
        sample_count = int(
            conn.execute("SELECT COUNT(*) FROM recall_sample").fetchone()[0]
        )
        if sample_count != int(meta["expected_sample_count"]):
            raise ProductionReconciliationError(
                f"frozen recall origin sample count drift: {recall_path}"
            )
        recorded_artifact_db = _resolved_recorded_path(
            meta["source_artifact_db"],
            label="frozen recall origin source_artifact_db",
        )
        if recorded_artifact_db != artifact_db.resolve():
            raise ProductionReconciliationError(
                "frozen recall origin was built from a different artifact DB: "
                f"{recall_path}"
            )

        sample_ids = list(config["sample_ids"])
        placeholders = ",".join("?" for _ in sample_ids)
        rows = conn.execute(
            f"""SELECT sample_id, day, event_id, band, sample_kind,
                       triage_decision, feed_rank, selection_sha256,
                       article_artifact_ids_json, packet_json
                FROM recall_sample
                WHERE sample_id IN ({placeholders})
                ORDER BY sample_id""",
            tuple(sample_ids),
        ).fetchall()
        observed_ids = {str(row["sample_id"]) for row in rows}
        if observed_ids != set(sample_ids):
            raise ProductionReconciliationError(
                "frozen recall origin sample IDs do not match the manifest; "
                f"missing={sorted(set(sample_ids) - observed_ids)}, "
                f"extra={sorted(observed_ids - set(sample_ids))}: {recall_path}"
            )

        artifact_ids: set[str] = set()
        items: list[dict[str, Any]] = []
        for row in rows:
            sample_id = str(row["sample_id"])
            day = str(row["day"])
            event_id = str(row["event_id"])
            band = str(row["band"])
            if (
                str(row["sample_kind"]) != "x_article_census"
                or str(row["triage_decision"]) != "keep"
                or band != audience_insight_recall.X_ARTICLE_51_100
            ):
                raise ProductionReconciliationError(
                    "frozen recall origin is not an accepted X Article census "
                    f"sample: {sample_id}"
                )
            if event_id in source_event_ids:
                raise ProductionReconciliationError(
                    "frozen recall origin overlaps a declared production-run "
                    f"event: {sample_id}"
                )
            if sample_id != audience_insight_recall._sample_id(day, event_id):
                raise ProductionReconciliationError(
                    f"frozen recall sample identity drift: {sample_id}"
                )
            expected_selection_sha256 = audience_insight_recall.selection_sha256(
                day=day,
                band=band,
                event_id=event_id,
            )
            if str(row["selection_sha256"]) != expected_selection_sha256:
                raise ProductionReconciliationError(
                    f"frozen recall sample selection drift: {sample_id}"
                )
            try:
                article_ids = json.loads(str(row["article_artifact_ids_json"]))
                packet = json.loads(str(row["packet_json"]))
            except json.JSONDecodeError as exc:
                raise ProductionReconciliationError(
                    f"frozen recall sample JSON is invalid: {sample_id}"
                ) from exc
            if (
                not isinstance(article_ids, list)
                or not article_ids
                or any(
                    not isinstance(value, str)
                    or _ARTIFACT_ID.fullmatch(value) is None
                    for value in article_ids
                )
                or len(article_ids) != len(set(article_ids))
                or str(row["article_artifact_ids_json"])
                != _canonical_json(article_ids)
            ):
                raise ProductionReconciliationError(
                    f"frozen recall article IDs are invalid: {sample_id}"
                )
            if (
                not isinstance(packet, dict)
                or packet.get("event_id") != event_id
                or packet.get("day") != day
            ):
                raise ProductionReconciliationError(
                    f"frozen recall packet identity drift: {sample_id}"
                )
            for artifact_id in article_ids:
                linked = artifact_conn.execute(
                    """SELECT COUNT(*)
                       FROM artifact_import_candidate
                       WHERE event_id = ? AND artifact_id = ?
                         AND decision = 'accepted'""",
                    (event_id, artifact_id),
                ).fetchone()[0]
                if int(linked) < 1:
                    raise ProductionReconciliationError(
                        "frozen recall article is not linked to its exact event: "
                        f"{sample_id}/{artifact_id}"
                    )
            artifact_ids.update(article_ids)
            items.append(
                {
                    "sample_id": sample_id,
                    "day": day,
                    "event_id": event_id,
                    "feed_rank": int(row["feed_rank"]),
                    "selection_sha256": expected_selection_sha256,
                    "artifact_ids": article_ids,
                }
            )
        return artifact_ids, {
            "recall_db": str(recall_path),
            "run_id": str(meta["run_id"]),
            "protocol_version": str(meta["protocol_version"]),
            "sample_set_sha256": str(meta["sample_set_sha256"]),
            "binding_sha256": binding_sha256,
            "sample_count": len(items),
            "artifact_count": len(artifact_ids),
            "items": items,
        }
    finally:
        conn.close()


def _inspect_x_article_cohort(
    config: Mapping[str, Any] | None, *, source_event_ids: set[str]
) -> dict[str, Any]:
    if config is None:
        return {
            "status": "not_bound",
            "reason": (
                "manifest did not provide an explicit artifact_db and exact "
                "artifact_ids; no heuristic X Article cohort was inferred"
            ),
            "artifact_db": None,
            "binding": None,
            "artifact_count": 0,
            "terminal_count": 0,
            "terminal_complete": None,
            "status_counts": {},
            "provider_request_count": 0,
            "estimated_provider_credits": 0,
            "items": [],
        }
    path = Path(str(config["artifact_db"]))
    conn = _open_readonly(path)
    try:
        placeholders = ",".join("?" for _ in source_event_ids)
        derived_ids = {
            str(row[0])
            for row in conn.execute(
                f"""SELECT DISTINCT artifact.artifact_id
                    FROM artifact_import_candidate AS candidate
                    JOIN artifact USING (artifact_id)
                    WHERE candidate.event_id IN ({placeholders})
                      AND candidate.decision = 'accepted'
                      AND lower(artifact.canonical_url) LIKE '%/i/article/%'""",
                tuple(sorted(source_event_ids)),
            ).fetchall()
        }
        recall_ids, recall_origin = _inspect_frozen_recall_origin(
            config["frozen_recall_origin"],
            artifact_conn=conn,
            artifact_db=path,
            source_event_ids=source_event_ids,
        )
        overlap = derived_ids & recall_ids
        if overlap:
            raise ProductionReconciliationError(
                "frozen recall X Articles overlap the production-run-derived "
                f"origin: {sorted(overlap)}"
            )
        required_ids = derived_ids | recall_ids
        configured_ids = set(config["artifact_ids"])
        if configured_ids != required_ids:
            raise ProductionReconciliationError(
                "manifest X Article cohort does not match the exact origin union; "
                f"missing={sorted(required_ids - configured_ids)}, "
                f"extra={sorted(configured_ids - required_ids)}"
            )
        try:
            provider_provenance = artifact_x_articles.validate_x_article_provenance(
                db_path=path,
                artifact_ids=sorted(configured_ids),
            )
        except (FileNotFoundError, sqlite3.Error, TypeError, ValueError) as exc:
            raise ProductionReconciliationError(
                f"X Article provider provenance is invalid: {exc}"
            ) from exc
        items = []
        for artifact_id in config["artifact_ids"]:
            artifact = conn.execute(
                "SELECT artifact_id, canonical_url FROM artifact WHERE artifact_id = ?",
                (artifact_id,),
            ).fetchone()
            if artifact is None:
                raise ProductionReconciliationError(
                    f"manifest X Article is not catalogued: {artifact_id}"
                )
            canonical_url = str(artifact["canonical_url"])
            if "/i/article/" not in canonical_url.lower():
                raise ProductionReconciliationError(
                    f"manifest artifact is not an X Article: {artifact_id}"
                )
            attempts = conn.execute(
                """SELECT fetch_id, status, attempt_number, raw_sha256,
                          raw_snapshot_ref, text_sha256, text_snapshot_ref,
                          error_code, error_message
                   FROM artifact_fetch
                   WHERE artifact_id = ? AND fetch_policy = ?
                   ORDER BY attempt_number, fetch_id""",
                (artifact_id, artifact_x_articles.FETCH_POLICY),
            ).fetchall()
            statuses = [str(row["status"]) for row in attempts]
            if "success" in statuses:
                effective_status = "success"
                effective_fetch = [
                    row for row in attempts if str(row["status"]) == "success"
                ][-1]
            elif "failed_terminal" in statuses:
                effective_status = "failed_terminal"
                effective_fetch = [
                    row
                    for row in attempts
                    if str(row["status"]) == "failed_terminal"
                ][-1]
            elif statuses:
                effective_status = statuses[-1]
                effective_fetch = attempts[-1]
            else:
                effective_status = "missing"
                effective_fetch = None
            provider_row = (
                conn.execute(
                    "SELECT * FROM artifact_x_article_fetch WHERE fetch_id = ?",
                    (effective_fetch["fetch_id"],),
                ).fetchone()
                if effective_fetch is not None
                else None
            )
            raw_sha256 = None
            text_sha256 = None
            terminal_error_code = None
            if effective_status == "success":
                if provider_row is None or int(provider_row["request_made"]) != 1:
                    raise ProductionReconciliationError(
                        f"successful X Article lacks provider request proof: {artifact_id}"
                    )
                raw_sha256 = str(effective_fetch["raw_sha256"] or "")
                text_sha256 = str(effective_fetch["text_sha256"] or "")
                if (
                    _ARTIFACT_ID.fullmatch(raw_sha256) is None
                    or _ARTIFACT_ID.fullmatch(text_sha256) is None
                ):
                    raise ProductionReconciliationError(
                        f"successful X Article lacks raw/text hashes: {artifact_id}"
                    )
                raw_snapshot = _snapshot_path(
                    effective_fetch["raw_snapshot_ref"],
                    label=f"X Article {artifact_id} raw snapshot",
                )
                text_snapshot = _snapshot_path(
                    effective_fetch["text_snapshot_ref"],
                    label=f"X Article {artifact_id} text snapshot",
                )
                if (
                    _file_sha256(raw_snapshot) != raw_sha256
                    or _file_sha256(text_snapshot) != text_sha256
                ):
                    raise ProductionReconciliationError(
                        f"X Article snapshot hash drift: {artifact_id}"
                    )
            elif effective_status == "failed_terminal":
                if provider_row is None:
                    raise ProductionReconciliationError(
                        f"terminal X Article lacks provider attempt proof: {artifact_id}"
                    )
                terminal_error_code = str(effective_fetch["error_code"] or "")
                error_message = str(effective_fetch["error_message"] or "")
                if not terminal_error_code or not error_message:
                    raise ProductionReconciliationError(
                        f"terminal X Article lacks explicit error metadata: {artifact_id}"
                    )
            provider = conn.execute(
                """SELECT COUNT(*) AS requests,
                          COALESCE(SUM(estimated_provider_credits), 0) AS credits
                   FROM artifact_x_article_fetch
                   WHERE artifact_id = ? AND request_made = 1""",
                (artifact_id,),
            ).fetchone()
            items.append(
                {
                    "artifact_id": artifact_id,
                    "origin": (
                        "production_run_event"
                        if artifact_id in derived_ids
                        else "frozen_recall_x_article_census"
                    ),
                    "canonical_url": canonical_url,
                    "status": effective_status,
                    "attempt_count": len(attempts),
                    "provider_request_count": int(provider["requests"] or 0),
                    "estimated_provider_credits": int(provider["credits"] or 0),
                    "raw_sha256": raw_sha256,
                    "text_sha256": text_sha256,
                    "terminal_error_code": terminal_error_code,
                }
            )
        status_counts: dict[str, int] = {}
        for item in items:
            status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
        terminal = sum(
            item["status"] in {"success", "failed_terminal"} for item in items
        )
        return {
            "status": "validated",
            "reason": None,
            "artifact_db": str(path),
            "binding": {
                "source_event_count": len(source_event_ids),
                "derived_artifact_count": len(derived_ids),
                "frozen_recall_artifact_count": len(recall_ids),
                "artifact_ids_sha256": _sha256(
                    _canonical_json(sorted(required_ids))
                ),
                "provider_provenance_sha256": provider_provenance[
                    "binding_sha256"
                ],
                "frozen_recall_origin": recall_origin,
            },
            "artifact_count": len(items),
            "terminal_count": terminal,
            "terminal_complete": terminal == len(items),
            "status_counts": dict(sorted(status_counts.items())),
            "provider_request_count": sum(
                item["provider_request_count"] for item in items
            ),
            "estimated_provider_credits": sum(
                item["estimated_provider_credits"] for item in items
            ),
            "items": items,
        }
    finally:
        conn.close()


def evaluate_manifest(path: Path | str) -> dict[str, Any]:
    """Validate every frozen input and return a deterministic report."""
    manifest, manifest_sha256 = load_manifest(path)
    runs = [
        _inspect_run(
            entry,
            expected_contract=manifest["expected_contracts"][entry["audience"]],
        )
        for entry in manifest["runs"]
    ]
    runs.sort(key=lambda row: (row["day"], row["audience"], row["source_run_id"]))
    _validate_chronological_history(runs)
    source_event_ids = {
        event_id for row in runs for event_id in row["_event_ids"]
    }
    x_articles = _inspect_x_article_cohort(
        manifest["x_article_cohort"], source_event_ids=source_event_ids
    )
    for row in runs:
        del row["_event_ids"]
        del row["_effective_selected_ids"]
        del row["_history_selected_ids"]
    totals = _run_totals(runs)
    by_audience = {
        audience: _run_totals(
            row for row in runs if row["audience"] == audience
        )
        for audience in audience_insights.AUDIENCES
    }
    x_article_requirement_satisfied = bool(x_articles["terminal_complete"])
    if manifest["mode"] == "partial" and x_articles["status"] == "not_bound":
        x_article_requirement_satisfied = True
    checks = {
        "all_manifest_runs_validated": True,
        "mode_scope_validated": True,
        "x_article_cohort_requirement_satisfied": x_article_requirement_satisfied,
    }
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "reconciliation_version": RECONCILIATION_VERSION,
        "reconciliation_id": manifest["reconciliation_id"],
        "mode": manifest["mode"],
        "manifest_sha256": manifest_sha256,
        "expected_contracts": manifest["expected_contracts"],
        "expected_audience_days": manifest["expected_audience_days"],
        "runs": runs,
        "totals": {"all": totals, "by_audience": by_audience},
        "x_article_cohort": x_articles,
        "checks": checks,
        "passed": all(checks.values()),
    }


def write_report(report: Mapping[str, Any], path: Path | str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output.parent,
        prefix=f".{output.name}.",
        suffix=".tmp",
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(canonical_report_text(report))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def canonical_report_text(report: Mapping[str, Any]) -> str:
    """Return the one byte-stable JSON representation accepted for publication."""
    return _canonical_json(report) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fli audience-insight-production-reconciliation"
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    command = "audience-insight-production-reconciliation.evaluate"
    try:
        report = evaluate_manifest(args.manifest)
        write_report(report, args.output)
    except (
        FileNotFoundError,
        json.JSONDecodeError,
        ProductionReconciliationError,
        sqlite3.Error,
        TypeError,
        ValueError,
    ) as exc:
        print(
            _canonical_json(
                {
                    "schema_version": "1.0",
                    "command": command,
                    "status": "error",
                    "data": None,
                    "error": {"code": "E_INVALID_INPUT", "message": str(exc)},
                }
            )
        )
        return 2
    print(
        _canonical_json(
            {
                "schema_version": "1.0",
                "command": command,
                "status": "ok",
                "data": {
                    "output": str(args.output.resolve()),
                    "passed": report["passed"],
                    "run_count": len(report["runs"]),
                },
                "error": None,
            }
        )
    )
    return 0 if report["passed"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
