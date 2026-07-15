"""Deterministic combined quality gate for Audience Insights v2.

The daily source gate and the blinded publication audit answer different
questions.  This module joins their immutable results across a frozen
multi-day evaluation window without making another model call.  A manifest
names source ``insights.db`` files and one post-freeze holdout day; each audit
is required to live beside its source at ``publication-audit-v1/audit.db``.

The emitted report contains no wall-clock fields, so the same frozen inputs
produce byte-identical JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from fli import audience_insight_publication_audit as publication_audit
from fli import audience_insights


MANIFEST_SCHEMA_VERSION = "audience-insight-combined-gate-manifest-v2"
REPORT_SCHEMA_VERSION = "audience-insight-combined-gate-report-v2"
GATE_VERSION = "audience-insight-combined-gate-v1.1"
ADJACENT_AUDIT_PATH = Path("publication-audit-v1") / "audit.db"
ADJACENT_ADJUDICATION_PATH = (
    Path("publication-audit-v1") / publication_audit.ADJUDICATION_FILENAME
)
ADJUDICATION_SCHEMA_VERSION = publication_audit.ADJUDICATION_SCHEMA_VERSION
MIN_SELECTED_PER_AUDIENCE = 3
MIN_SELECTION_DAYS_PER_AUDIENCE = 2
MIN_JOINT_QUALITY_RATIO = 0.8
STANDARD_POLICY = "standard"
AUDITED_SPARSE_POLICY = "audited_sparse"
AUDIENCE_POLICIES = (STANDARD_POLICY, AUDITED_SPARSE_POLICY)
MIN_SPARSE_EVALUATION_DAYS = 5
MIN_SPARSE_SELECTED_PER_AUDIENCE = 1
MIN_SPARSE_HOLDOUT_REJECT_AUDITS = 5
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SOURCE_CONTRACT_VERSION_FIELDS = (
    "model",
    "reasoning_effort",
    "prompt_version",
    "prompt_sha256",
    "schema_version",
    "editor_model",
    "editor_reasoning_effort",
    "editor_prompt_version",
    "editor_prompt_sha256",
    "editor_schema_version",
    "review_model",
    "review_reasoning_effort",
    "item_review_prompt_version",
    "item_review_prompt_sha256",
    "item_review_schema_version",
    "day_review_prompt_version",
    "day_review_prompt_sha256",
    "day_review_schema_version",
)


class CombinedGateError(ValueError):
    """The manifest or frozen evaluation inputs violate the gate contract."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


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
        missing = sorted(expected - set(value))
        extra = sorted(set(value) - expected)
        raise CombinedGateError(
            f"{label} keys do not match the schema; missing={missing}, extra={extra}"
        )


def load_manifest(path: Path | str) -> tuple[dict[str, Any], str]:
    """Load and strictly validate one frozen evaluation manifest."""
    path = Path(path)
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise CombinedGateError("combined-gate manifest must be a JSON object")
    _require_exact_keys(
        payload,
        {"schema_version", "evaluation_id", "audiences", "runs"},
        label="manifest",
    )
    if payload["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise CombinedGateError(
            f"unsupported manifest schema_version: {payload['schema_version']!r}"
        )
    if not isinstance(payload["evaluation_id"], str) or not payload[
        "evaluation_id"
    ].strip():
        raise CombinedGateError("evaluation_id must be a non-empty string")
    audience_configs = payload["audiences"]
    if not isinstance(audience_configs, dict):
        raise CombinedGateError("audiences must be an object")
    expected_audiences = set(audience_insights.AUDIENCES)
    _require_exact_keys(
        audience_configs,
        expected_audiences,
        label="audiences",
    )
    normalized_audiences: dict[str, dict[str, Any]] = {}
    for audience in audience_insights.AUDIENCES:
        config = audience_configs[audience]
        if not isinstance(config, dict):
            raise CombinedGateError(f"audiences.{audience} must be an object")
        _require_exact_keys(
            config,
            {"policy", "holdout_day", "evaluation_days"},
            label=f"audiences.{audience}",
        )
        policy = config["policy"]
        if policy not in AUDIENCE_POLICIES:
            raise CombinedGateError(
                f"audiences.{audience}.policy must be one of "
                f"{list(AUDIENCE_POLICIES)}"
            )
        holdout_day = config["holdout_day"]
        if not isinstance(holdout_day, str) or not _DAY.fullmatch(holdout_day):
            raise CombinedGateError(
                f"audiences.{audience}.holdout_day must use YYYY-MM-DD"
            )
        raw_days = config["evaluation_days"]
        if not isinstance(raw_days, list) or not raw_days:
            raise CombinedGateError(
                f"audiences.{audience}.evaluation_days must be a non-empty array"
            )
        if any(not isinstance(day, str) or not _DAY.fullmatch(day) for day in raw_days):
            raise CombinedGateError(
                f"audiences.{audience}.evaluation_days must use YYYY-MM-DD"
            )
        if len(raw_days) != len(set(raw_days)):
            raise CombinedGateError(
                f"audiences.{audience}.evaluation_days contains duplicates"
            )
        evaluation_days = sorted(raw_days)
        if holdout_day not in evaluation_days:
            raise CombinedGateError(
                f"audiences.{audience}.holdout_day must be in evaluation_days"
            )
        normalized_audiences[audience] = {
            "policy": policy,
            "holdout_day": holdout_day,
            "evaluation_days": evaluation_days,
        }
    runs = payload["runs"]
    if not isinstance(runs, list) or not runs:
        raise CombinedGateError("runs must be a non-empty array")
    normalized_runs: list[dict[str, str]] = []
    seen_paths: set[Path] = set()
    for index, entry in enumerate(runs):
        if not isinstance(entry, dict):
            raise CombinedGateError(f"runs[{index}] must be an object")
        _require_exact_keys(entry, {"source_run_db"}, label=f"runs[{index}]")
        raw_path = entry["source_run_db"]
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise CombinedGateError(
                f"runs[{index}].source_run_db must be a non-empty string"
            )
        resolved = Path(raw_path)
        if not resolved.is_absolute():
            resolved = path.parent / resolved
        resolved = resolved.resolve()
        if resolved in seen_paths:
            raise CombinedGateError(f"duplicate source run: {resolved}")
        seen_paths.add(resolved)
        normalized_runs.append({"source_run_db": str(resolved)})
    normalized = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "evaluation_id": payload["evaluation_id"].strip(),
        "audiences": normalized_audiences,
        "runs": normalized_runs,
    }
    return normalized, _sha256(_canonical_json(normalized))


def _source_snapshot(
    source: sqlite3.Connection,
    *,
    audit_items: Mapping[str, sqlite3.Row],
    audit_meta: sqlite3.Row,
) -> tuple[sqlite3.Row, str, str, list[str]]:
    """Rebuild the publication audit's immutable source contract."""
    source_meta, rows = publication_audit._source_rows(  # noqa: SLF001
        source,
        reject_sample_limit=int(audit_meta["reject_sample_limit"]),
    )
    source_ids = {str(row["candidate_id"]) for _, row in rows}
    if set(audit_items) != source_ids:
        return source_meta, "", "", ["audit_candidate_set_matches_source"]

    mismatches: list[str] = []
    frozen: list[dict[str, Any]] = []
    for sample_kind, row in rows:
        candidate_id = str(row["candidate_id"])
        stored = audit_items[candidate_id]
        blocks = publication_audit._evidence_blocks(str(row["packet_json"]))  # noqa: SLF001
        item = publication_audit._audience_item(  # noqa: SLF001
            str(source_meta["audience"]), row
        )
        audit_item_id = str(stored["audit_item_id"])
        input_text = publication_audit.render_input(
            audit_item_id=audit_item_id,
            audience=str(source_meta["audience"]),
            evidence_blocks=blocks,
            item=item,
        )
        expected = {
            "source_event_id": str(row["event_id"]),
            "sample_kind": sample_kind,
            "source_feed_rank": int(row["feed_rank"]),
            "frozen_evidence_json": _canonical_json(blocks),
            "frozen_item_json": _canonical_json(item),
            "source_item_sha256": _sha256(
                _canonical_json({"blocks": blocks, "item": item})
            ),
            "input_text": input_text,
            "input_sha256": _sha256(input_text),
            "prompt_cache_key": publication_audit.prompt_cache_key(
                str(source_meta["audience"]), audit_item_id
            ),
            "mechanical_citation_valid": int(
                publication_audit._mechanical_citation_valid(item, blocks)  # noqa: SLF001
            ),
        }
        for field, expected_value in expected.items():
            if stored[field] != expected_value:
                mismatches.append(f"audit_item.{candidate_id}.{field}")
        frozen.append(
            {
                "audit_item_id": audit_item_id,
                "sample_kind": sample_kind,
                "source_feed_rank": int(row["feed_rank"]),
                "source_item_sha256": expected["source_item_sha256"],
            }
        )

    frozen.sort(key=lambda value: value["audit_item_id"])
    cohort_sha256 = _sha256(_canonical_json(frozen))
    source_contract_sha256 = _sha256(
        _canonical_json(
            {
                "source_run_id": source_meta["run_id"],
                "audience": source_meta["audience"],
                "day": source_meta["day"],
                "prompt_version": source_meta["prompt_version"],
                "schema_version": source_meta["schema_version"],
                "editor_prompt_version": source_meta["editor_prompt_version"],
                "cohort_sha256": cohort_sha256,
            }
        )
    )
    return source_meta, cohort_sha256, source_contract_sha256, mismatches


def _adjudication_report(
    path: Path,
    *,
    source_run_id: str,
    source_contract_sha256: str,
    audit_meta: sqlite3.Row,
    audit_result_sha256: str,
    false_negatives: Mapping[str, Any],
) -> dict[str, Any]:
    expected_pairs = set(
        zip(
            false_negatives["audit_item_ids"],
            false_negatives["source_candidate_ids"],
            strict=True,
        )
    )
    base = {
        "path": str(path.resolve()),
        "required_count": len(expected_pairs),
        "audit_result_sha256": audit_result_sha256,
        "adjudications": [],
        "unresolved": [],
        "would_enter": [],
        "errors": [],
    }
    if not expected_pairs and not path.exists():
        return {**base, "status": "not_required", "cleared": True}
    if not path.is_file():
        return {
            **base,
            "status": "required_missing",
            "unresolved": [
                {"audit_item_id": audit_id, "source_candidate_id": candidate_id}
                for audit_id, candidate_id in sorted(expected_pairs)
            ],
            "cleared": False,
        }
    try:
        payload = json.loads(path.read_text())
        if not isinstance(payload, dict):
            raise CombinedGateError("adjudication file must be a JSON object")
        _require_exact_keys(
            payload,
            {
                "schema_version",
                "source_run_id",
                "source_contract_sha256",
                "audit_id",
                "audit_cohort_sha256",
                "audit_result_sha256",
                "adjudications",
            },
            label="adjudication file",
        )
        binding_checks = {
            "schema_version_matches": payload["schema_version"]
            == ADJUDICATION_SCHEMA_VERSION,
            "source_run_id_matches": payload["source_run_id"] == source_run_id,
            "source_contract_sha256_matches": payload["source_contract_sha256"]
            == source_contract_sha256,
            "audit_id_matches": payload["audit_id"] == audit_meta["audit_id"],
            "audit_cohort_sha256_matches": payload["audit_cohort_sha256"]
            == audit_meta["cohort_sha256"],
            "audit_result_sha256_matches": payload["audit_result_sha256"]
            == audit_result_sha256,
        }
        entries = payload["adjudications"]
        if not isinstance(entries, list):
            raise CombinedGateError("adjudications must be an array")
        parsed: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        errors: list[str] = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                errors.append(f"adjudications[{index}] is not an object")
                continue
            try:
                _require_exact_keys(
                    entry,
                    {"audit_item_id", "source_candidate_id", "verdict", "rationale"},
                    label=f"adjudications[{index}]",
                )
            except CombinedGateError as exc:
                errors.append(str(exc))
                continue
            pair = (entry["audit_item_id"], entry["source_candidate_id"])
            if not all(isinstance(value, str) and value for value in pair):
                errors.append(f"adjudications[{index}] has invalid bound IDs")
                continue
            if pair in seen:
                errors.append(f"duplicate adjudication binding: {pair[0]}/{pair[1]}")
            seen.add(pair)
            if entry["verdict"] not in {"would_enter", "would_not_enter"}:
                errors.append(f"adjudications[{index}] has invalid verdict")
            if not isinstance(entry["rationale"], str) or not entry[
                "rationale"
            ].strip():
                errors.append(f"adjudications[{index}] has empty rationale")
            parsed.append(
                {
                    "audit_item_id": pair[0],
                    "source_candidate_id": pair[1],
                    "verdict": entry["verdict"],
                    "rationale": (
                        entry["rationale"].strip()
                        if isinstance(entry["rationale"], str)
                        else ""
                    ),
                }
            )
        actual_pairs = {
            (entry["audit_item_id"], entry["source_candidate_id"])
            for entry in parsed
        }
        if actual_pairs - expected_pairs:
            errors.append("adjudication file contains non-current audit findings")
        unresolved_pairs = expected_pairs - actual_pairs
        would_enter = [
            entry for entry in parsed if entry["verdict"] == "would_enter"
        ]
        cleared = bool(
            all(binding_checks.values())
            and not errors
            and not unresolved_pairs
            and not would_enter
            and actual_pairs == expected_pairs
        )
        return {
            **base,
            "status": "cleared" if cleared else "blocked",
            "binding_checks": binding_checks,
            "adjudications": sorted(
                parsed, key=lambda item: (item["audit_item_id"], item["source_candidate_id"])
            ),
            "unresolved": [
                {"audit_item_id": audit_id, "source_candidate_id": candidate_id}
                for audit_id, candidate_id in sorted(unresolved_pairs)
            ],
            "would_enter": would_enter,
            "errors": errors,
            "cleared": cleared,
        }
    except (CombinedGateError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return {
            **base,
            "status": "invalid",
            "errors": [str(exc)],
            "cleared": False,
        }


def _inspect_run(source_path: Path) -> dict[str, Any]:
    audit_path = source_path.parent / ADJACENT_AUDIT_PATH
    adjudication_path = source_path.parent / ADJACENT_ADJUDICATION_PATH
    source = _open_readonly(source_path)
    audit = _open_readonly(audit_path)
    try:
        source_meta = source.execute(
            "SELECT * FROM run_meta WHERE singleton = 1"
        ).fetchone()
        if source_meta is None:
            raise CombinedGateError(f"source run is not frozen: {source_path}")
        audit_meta = audit.execute(
            "SELECT * FROM audit_run WHERE singleton = 1"
        ).fetchone()
        if audit_meta is None:
            raise CombinedGateError(f"publication audit is not frozen: {audit_path}")
        audit_items = {
            str(row["source_candidate_id"]): row
            for row in audit.execute("SELECT * FROM audit_item").fetchall()
        }
        (
            rebuilt_meta,
            cohort_sha256,
            source_contract_sha256,
            item_mismatches,
        ) = _source_snapshot(
            source,
            audit_items=audit_items,
            audit_meta=audit_meta,
        )
        source_gate = source.execute(
            "SELECT * FROM quality_gate WHERE singleton = 1"
        ).fetchone()
        source_gate_result = (
            json.loads(str(source_gate["result_json"]))
            if source_gate is not None
            else None
        )
        source_internal_gate_passed = bool(
            source_gate is not None
            and int(source_gate["passed"]) == 1
            and isinstance(source_gate_result, dict)
            and source_gate_result.get("passed") is True
            and source_gate_result.get("audience") == source_meta["audience"]
            and source_gate_result.get("day") == source_meta["day"]
            and isinstance(source_gate_result.get("checks"), dict)
            and bool(source_gate_result["checks"])
            and all(source_gate_result["checks"].values())
        )
        selected_count = int(
            source.execute("SELECT COUNT(*) FROM publication_selection").fetchone()[0]
        )
        source_gate_selected_count_matches = bool(
            isinstance(source_gate_result, dict)
            and source_gate_result.get("selected_count") == selected_count
        )

        audit_summary = publication_audit.summary(audit)
        audit_result_sha256 = publication_audit.audit_result_sha256(audit)
        selected = audit_summary["selected_metrics"]
        false_negatives = audit_summary["false_negative_review_rejects"]
        reject_counts = next(
            (
                row
                for row in audit_summary["counts"]
                if row["sample_kind"] == "review_reject"
            ),
            {"complete": 0, "total": 0},
        )
        adjudication = _adjudication_report(
            adjudication_path,
            source_run_id=str(source_meta["run_id"]),
            source_contract_sha256=source_contract_sha256,
            audit_meta=audit_meta,
            audit_result_sha256=audit_result_sha256,
            false_negatives=false_negatives,
        )
        all_audit_items_complete = all(
            int(row["complete"] or 0) == int(row["total"] or 0)
            for row in audit_summary["counts"]
        )
        zero_item_day_honest = bool(
            selected_count > 0
            or (
                isinstance(source_gate_result, dict)
                and source_gate_result.get("thin_day") is True
                and isinstance(source_gate_result.get("checks"), dict)
                and source_gate_result["checks"].get(
                    "thin_day_honest_and_all_quality"
                )
                is True
            )
        )
        source_binding_checks = {
            "source_run_path_matches": Path(str(audit_meta["source_run_db"])).resolve()
            == source_path.resolve(),
            "source_run_id_matches": audit_meta["source_run_id"]
            == rebuilt_meta["run_id"],
            "audience_matches": audit_meta["audience"] == rebuilt_meta["audience"],
            "day_matches": audit_meta["day"] == rebuilt_meta["day"],
            "audit_prompt_version_matches": audit_meta["prompt_version"]
            == publication_audit.PROMPT_VERSION,
            "audit_prompt_sha256_matches": audit_meta["prompt_sha256"]
            == publication_audit.prompt_sha256(),
            "audit_schema_version_matches": audit_meta["schema_version"]
            == publication_audit.SCHEMA_VERSION,
            "selected_count_matches": int(audit_meta["selected_count"])
            == selected_count,
            "cohort_sha256_matches": audit_meta["cohort_sha256"] == cohort_sha256,
            "source_contract_sha256_matches": audit_meta["source_contract_sha256"]
            == source_contract_sha256,
            "frozen_items_match": not item_mismatches,
        }
        checks = {
            "source_internal_gate_passed": source_internal_gate_passed,
            "source_gate_selected_count_matches": source_gate_selected_count_matches,
            "audit_source_binding_valid": all(source_binding_checks.values()),
            "all_audit_items_complete": all_audit_items_complete,
            "publication_audit_passed": audit_summary["passed"] is True,
            "false_negative_review_rejects_adjudicated": adjudication["cleared"],
            "zero_citation_failures": int(selected["mechanical_citation_failures"])
            + int(selected["citation_fidelity_failures"])
            == 0,
            "zero_attribution_failures": int(selected["attribution_failures"]) == 0,
            "zero_epistemic_failures": int(selected["epistemic_failures"]) == 0,
            "zero_item_day_is_explicitly_honest": zero_item_day_honest,
        }
        return {
            "source_run_db": str(source_path.resolve()),
            "publication_audit_db": str(audit_path.resolve()),
            "source_run_id": str(source_meta["run_id"]),
            "audit_id": str(audit_meta["audit_id"]),
            "audience": str(source_meta["audience"]),
            "day": str(source_meta["day"]),
            "selected_count": selected_count,
            "zero_item_day_honest": zero_item_day_honest,
            "audit_review_rejects": {
                "complete": int(reject_counts["complete"] or 0),
                "total": int(reject_counts["total"] or 0),
            },
            "source_contract_versions": {
                field: source_meta[field] for field in SOURCE_CONTRACT_VERSION_FIELDS
            },
            "source_contract_sha256": source_contract_sha256,
            "audit_cohort_sha256": str(audit_meta["cohort_sha256"]),
            "audit_result_sha256": audit_result_sha256,
            "audit_selected_metrics": {
                "total": int(selected["total"]),
                "full_quality_passes": int(selected["full_quality_passes"]),
                "mechanical_citation_failures": int(
                    selected["mechanical_citation_failures"]
                ),
                "citation_fidelity_failures": int(
                    selected["citation_fidelity_failures"]
                ),
                "attribution_failures": int(selected["attribution_failures"]),
                "epistemic_failures": int(selected["epistemic_failures"]),
            },
            "false_negative_review_rejects": false_negatives,
            "false_negative_adjudication": adjudication,
            "source_binding_checks": source_binding_checks,
            "source_binding_mismatches": sorted(item_mismatches),
            "checks": checks,
            "passed": all(checks.values()),
        }
    finally:
        source.close()
        audit.close()


def evaluate_manifest(path: Path | str) -> dict[str, Any]:
    """Evaluate all frozen pairs and return a deterministic gate report."""
    manifest, manifest_sha256 = load_manifest(path)
    runs = [
        _inspect_run(Path(entry["source_run_db"])) for entry in manifest["runs"]
    ]
    runs.sort(key=lambda row: (row["audience"], row["day"], row["source_run_id"]))
    audience_days = [(row["audience"], row["day"]) for row in runs]
    if len(audience_days) != len(set(audience_days)):
        raise CombinedGateError("manifest contains duplicate audience/day runs")
    audiences_present = {row["audience"] for row in runs}
    expected_audiences = set(audience_insights.AUDIENCES)
    unknown = audiences_present - expected_audiences
    if unknown:
        raise CombinedGateError(f"source runs contain unknown audiences: {sorted(unknown)}")

    audience_reports: dict[str, Any] = {}
    for audience in audience_insights.AUDIENCES:
        config = manifest["audiences"][audience]
        policy = config["policy"]
        holdout_day = config["holdout_day"]
        expected_day_set = set(config["evaluation_days"])
        audience_runs = [row for row in runs if row["audience"] == audience]
        audience_day_set = {row["day"] for row in audience_runs}
        contract_payloads = sorted(
            {
                _canonical_json(row["source_contract_versions"])
                for row in audience_runs
            }
        )
        selected_count = sum(row["selected_count"] for row in audience_runs)
        selected_days = sorted(
            row["day"] for row in audience_runs if row["selected_count"] > 0
        )
        holdout_selected_count = sum(
            row["selected_count"]
            for row in audience_runs
            if row["day"] == holdout_day
        )
        holdout_runs = [row for row in audience_runs if row["day"] == holdout_day]
        holdout_reject_audit_total = sum(
            row["audit_review_rejects"]["total"] for row in holdout_runs
        )
        holdout_reject_audit_complete = sum(
            row["audit_review_rejects"]["complete"] for row in holdout_runs
        )
        audit_selected_count = sum(
            row["audit_selected_metrics"]["total"] for row in audience_runs
        )
        quality_pass_count = sum(
            row["audit_selected_metrics"]["full_quality_passes"]
            for row in audience_runs
        )
        required_quality_passes = math.ceil(
            MIN_JOINT_QUALITY_RATIO * audit_selected_count
        )
        quality_ratio = (
            round(quality_pass_count / audit_selected_count, 6)
            if audit_selected_count
            else 0.0
        )
        common_checks = {
            "audience_has_runs": bool(audience_runs),
            "all_runs_pass": bool(audience_runs)
            and all(row["passed"] for row in audience_runs),
            "holdout_day_present": any(
                row["day"] == holdout_day for row in audience_runs
            ),
            "exact_manifest_day_set_present": audience_day_set
            == expected_day_set,
            "uniform_source_contract": len(contract_payloads) == 1,
            "audit_selected_count_matches_source": audit_selected_count
            == selected_count,
            "joint_quality_at_least_80_percent": bool(audit_selected_count)
            and quality_pass_count >= required_quality_passes,
            "zero_item_days_are_explicitly_honest": all(
                row["zero_item_day_honest"] for row in audience_runs
            ),
        }
        standard_yield_checks = {
            "selected_count_at_least_three": selected_count
            >= MIN_SELECTED_PER_AUDIENCE,
            "selections_span_at_least_two_days": len(selected_days)
            >= MIN_SELECTION_DAYS_PER_AUDIENCE,
            "holdout_has_selection": holdout_selected_count >= 1,
        }
        if policy == STANDARD_POLICY:
            active_policy_checks = standard_yield_checks
            outcome = "standard_pass"
        else:
            active_policy_checks = {
                "standard_gate_failed_on_yield_only": not all(
                    standard_yield_checks.values()
                ),
                "evaluation_spans_at_least_five_days": len(audience_runs)
                >= MIN_SPARSE_EVALUATION_DAYS,
                "selected_count_at_least_one": selected_count
                >= MIN_SPARSE_SELECTED_PER_AUDIENCE,
                "selections_span_at_least_one_day": bool(selected_days),
                "holdout_is_honest_zero_item_day": bool(
                    len(holdout_runs) == 1
                    and holdout_selected_count == 0
                    and holdout_runs[0]["zero_item_day_honest"]
                ),
                "holdout_has_full_reject_audit": bool(
                    holdout_reject_audit_total
                    >= MIN_SPARSE_HOLDOUT_REJECT_AUDITS
                    and holdout_reject_audit_complete
                    == holdout_reject_audit_total
                ),
            }
            outcome = "audited_sparse"
        checks = {**common_checks, **active_policy_checks}
        passed = all(checks.values())
        audience_reports[audience] = {
            "policy": policy,
            "outcome": outcome if passed else "failed",
            "holdout_day": holdout_day,
            "evaluation_days": config["evaluation_days"],
            "run_count": len(audience_runs),
            "thin_zero_item_days": sorted(
                row["day"] for row in audience_runs if row["selected_count"] == 0
            ),
            "selected_count": selected_count,
            "selected_days": selected_days,
            "holdout_selected_count": holdout_selected_count,
            "holdout_reject_audit_complete": holdout_reject_audit_complete,
            "holdout_reject_audit_total": holdout_reject_audit_total,
            "audit_selected_count": audit_selected_count,
            "joint_quality_pass_count": quality_pass_count,
            "required_joint_quality_passes": required_quality_passes,
            "joint_quality_ratio": quality_ratio,
            "source_contract_sha256s": [
                _sha256(payload) for payload in contract_payloads
            ],
            "standard_yield_checks": standard_yield_checks,
            "checks": checks,
            "passed": passed,
        }

    checks = {
        "exact_audience_set_present": audiences_present == expected_audiences,
        "exact_evaluation_day_set_present_for_each_audience": all(
            report["checks"]["exact_manifest_day_set_present"]
            for report in audience_reports.values()
        ),
        "uniform_source_contract_per_audience": all(
            report["checks"]["uniform_source_contract"]
            for report in audience_reports.values()
        ),
        "all_source_and_audit_runs_pass": all(row["passed"] for row in runs),
        "all_audiences_pass": all(
            report["passed"] for report in audience_reports.values()
        ),
    }
    blocking_reasons = sorted(
        [
            f"run:{row['audience']}:{row['day']}:{name}"
            for row in runs
            for name, passed in row["checks"].items()
            if not passed
        ]
        + [
            f"audience:{audience}:{name}"
            for audience, report in audience_reports.items()
            for name, passed in report["checks"].items()
            if not passed
        ]
        + [f"combined:{name}" for name, passed in checks.items() if not passed]
    )
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "gate_version": GATE_VERSION,
        "evaluation_id": manifest["evaluation_id"],
        "manifest_sha256": manifest_sha256,
        "audience_policies": manifest["audiences"],
        "requirements": {
            "standard": {
                "minimum_selected_per_audience": MIN_SELECTED_PER_AUDIENCE,
                "minimum_selection_days_per_audience": (
                    MIN_SELECTION_DAYS_PER_AUDIENCE
                ),
                "minimum_holdout_selections_per_audience": 1,
            },
            "audited_sparse": {
                "minimum_evaluation_days": MIN_SPARSE_EVALUATION_DAYS,
                "minimum_selected_per_audience": (
                    MIN_SPARSE_SELECTED_PER_AUDIENCE
                ),
                "minimum_holdout_reject_audits": (
                    MIN_SPARSE_HOLDOUT_REJECT_AUDITS
                ),
                "holdout_must_be_honest_zero_item_day": True,
                "standard_gate_must_fail_on_yield_only": True,
            },
            "minimum_joint_quality_ratio": MIN_JOINT_QUALITY_RATIO,
            "false_negative_review_rejects_must_be_adjudicated_to_zero": True,
        },
        "runs": runs,
        "audiences": audience_reports,
        "checks": checks,
        "blocking_reasons": blocking_reasons,
        "passed": all(checks.values()),
    }


def write_report(report: Mapping[str, Any], path: Path | str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical_json(report) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fli audience-insight-combined-gate")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    command = "audience-insight-combined-gate.evaluate"
    try:
        report = evaluate_manifest(args.manifest)
        write_report(report, args.output)
    except (CombinedGateError, FileNotFoundError, json.JSONDecodeError, sqlite3.Error) as exc:
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
                    "blocking_reasons": report["blocking_reasons"],
                },
                "error": None,
            }
        )
    )
    return 0 if report["passed"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
