"""Independent post-publication calibration audit for Audience Insights v2.

This audit is deliberately separate from the item-review filter that controls
editor eligibility.  It copies a blinded, immutable cohort from one audience
run into its own database, uses its own prompt/cache namespace, and never gives
the auditor selection state, Feed rank, prior review judgments, or editor audit
metadata.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import sqlite3
import time
import unicodedata
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from fli import audience_insights, entity_kinds, llm_responses


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUDIT_ROOT = REPO_ROOT / "data" / "derived" / "audience-insights-v2-audits"
DEFAULT_MODEL = llm_responses.DEFAULT_EFFICIENT_MODEL
DEFAULT_REASONING_EFFORT = "high"
DEFAULT_WORKERS = 5
DEFAULT_REJECT_SAMPLE_LIMIT = 5
MAX_ATTEMPTS = 2
PROMPT_CACHE_SHARDS = 4

PROMPT_VERSION = "audience-insight-publication-audit-v1.0"
SCHEMA_VERSION = "audience-insight-publication-audit-output-v1"
ADJUDICATION_SCHEMA_VERSION = "audience-insight-publication-audit-adjudications-v1"
ADJUDICATION_FILENAME = "adjudications.json"
FINALIZATION_SCHEMA_VERSION = "audience-insight-publication-finalization-v1"
FINALIZATION_REASON_CODE = "publication_audit_disqualification"
EDITORIAL_FINALIZATION_SCHEMA_VERSION = (
    "audience-insight-editorial-finalization-v1"
)
COMPOSED_EDITORIAL_FINALIZATION_SCHEMA_VERSION = (
    "audience-insight-composed-editorial-finalization-v1"
)
EDITORIAL_FINALIZATION_REASON_CODE = "senior_editorial_disqualification"
EDITORIAL_REVIEW_SCHEMA_VERSION = "audience-insight-editorial-review-v1"
EDITORIAL_REMOVAL_REASON_CODES = (
    "analytical_overstatement",
    "insufficient_decision_value",
    "promotional_or_testimonial_evidence",
    "duplicate_or_redundant",
    "audience_mismatch",
    "other",
)
FINALIZATION_DIR = "publication-finalization-v1"
EDITORIAL_FINALIZATION_DIR = "publication-editorial-finalization-v1"
FINALIZATION_FILENAME = "finalization.json"
PROMPT_PATH = Path(__file__).with_name("prompts") / "audience_insight_publication_auditor_v1.txt"

JUDGMENT_FIELDS = (
    "citation_fidelity",
    "attribution_fidelity",
    "epistemic_discipline",
    "audience_usefulness",
    "actionability",
    "specificity",
)
OUTPUT_FIELDS = ("audit_item_id", *JUDGMENT_FIELDS, "failure_codes", "rationale")
SUCCESS_TELEMETRY_FIELDS = (
    "raw_output_text",
    "response_id",
    "response_model",
    "input_tokens",
    "cached_tokens",
    "cache_write_tokens",
    "output_tokens",
    "reported_cost_usd",
    "request_tags",
)
SUCCESS_RESULT_FIELDS = (*OUTPUT_FIELDS, *SUCCESS_TELEMETRY_FIELDS)
PASS_FAIL = ("pass", "fail")
FAILURE_CODES = (
    "quote_not_contiguous",
    "wrong_citation_block",
    "claim_not_supported",
    "wrong_attribution",
    "attribution_upgrade",
    "scope_or_modality_loss",
    "unsupported_analysis_fact",
    "generic_investment_implication",
    "generic_investment_watchpoint",
    "generic_engineering_action",
    "missing_validation_boundary",
    "audience_mismatch",
    "not_decision_relevant",
    "vague_or_promotional",
    "other",
)

OUTPUT_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "name": "audience_insight_publication_audit_v1",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "audit_item_id": {"type": "string"},
            **{
                field: {"type": "string", "enum": list(PASS_FAIL)}
                for field in JUDGMENT_FIELDS
            },
            "failure_codes": {
                "type": "array",
                "items": {"type": "string", "enum": list(FAILURE_CODES)},
            },
            "rationale": {"type": "string"},
        },
        "required": list(OUTPUT_FIELDS),
        "additionalProperties": False,
    },
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_run (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    audit_id TEXT NOT NULL,
    source_run_db TEXT NOT NULL,
    source_run_id TEXT NOT NULL,
    audience TEXT NOT NULL CHECK (audience IN ('investment', 'ai_engineering')),
    day TEXT NOT NULL,
    model TEXT NOT NULL,
    reasoning_effort TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    prompt_sha256 TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    reject_sample_limit INTEGER NOT NULL,
    selected_count INTEGER NOT NULL,
    reject_sample_count INTEGER NOT NULL,
    cohort_sha256 TEXT NOT NULL,
    source_contract_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_item (
    audit_item_id TEXT PRIMARY KEY,
    source_candidate_id TEXT NOT NULL UNIQUE,
    source_event_id TEXT NOT NULL,
    sample_kind TEXT NOT NULL CHECK (sample_kind IN ('selected', 'review_reject')),
    source_feed_rank INTEGER NOT NULL,
    frozen_evidence_json TEXT NOT NULL,
    frozen_item_json TEXT NOT NULL,
    source_item_sha256 TEXT NOT NULL,
    input_text TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    prompt_cache_key TEXT NOT NULL,
    mechanical_citation_valid INTEGER NOT NULL CHECK (mechanical_citation_valid IN (0, 1)),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'complete', 'failed', 'rejected')),
    attempts INTEGER NOT NULL DEFAULT 0,
    citation_fidelity TEXT CHECK (citation_fidelity IS NULL OR citation_fidelity IN ('pass', 'fail')),
    attribution_fidelity TEXT CHECK (attribution_fidelity IS NULL OR attribution_fidelity IN ('pass', 'fail')),
    epistemic_discipline TEXT CHECK (epistemic_discipline IS NULL OR epistemic_discipline IN ('pass', 'fail')),
    audience_usefulness TEXT CHECK (audience_usefulness IS NULL OR audience_usefulness IN ('pass', 'fail')),
    actionability TEXT CHECK (actionability IS NULL OR actionability IN ('pass', 'fail')),
    specificity TEXT CHECK (specificity IS NULL OR specificity IN ('pass', 'fail')),
    failure_codes_json TEXT,
    rationale TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_publication_audit_status_cache
    ON audit_item(status, prompt_cache_key, audit_item_id);
CREATE INDEX IF NOT EXISTS idx_publication_audit_kind
    ON audit_item(sample_kind, status, audit_item_id);

CREATE TABLE IF NOT EXISTS audit_attempt (
    audit_item_id TEXT NOT NULL REFERENCES audit_item(audit_item_id) ON DELETE RESTRICT,
    attempt_number INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('complete', 'failed', 'rejected')),
    model TEXT NOT NULL,
    reasoning_effort TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    prompt_sha256 TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    prompt_cache_key TEXT NOT NULL,
    result_json TEXT,
    raw_output_text TEXT,
    error_type TEXT,
    error_message TEXT,
    response_id TEXT,
    response_model TEXT,
    input_tokens INTEGER,
    cached_tokens INTEGER,
    cache_write_tokens INTEGER,
    output_tokens INTEGER,
    reported_cost_usd REAL,
    request_tags_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (audit_item_id, attempt_number)
);
"""


class AuditValidationError(ValueError):
    """A model response that completed but violated the audit output contract."""

    def __init__(self, message: str, *, result: Mapping[str, Any]):
        super().__init__(message)
        self.result = dict(result)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _safe_slug(value: str, *, label: str) -> str:
    if not value or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for character in value):
        raise ValueError(f"{label} may contain only letters, numbers, '-', '_', and '.'")
    return value


def default_audit_db(*, audit_id: str) -> Path:
    return DEFAULT_AUDIT_ROOT / _safe_slug(audit_id, label="audit_id") / "audit.db"


def connect(path: Path | str) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.executescript(SCHEMA)
    return conn


def _open_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(path)
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def instructions() -> str:
    return PROMPT_PATH.read_text().strip()


def prompt_sha256() -> str:
    return _sha256(instructions())


def _audience_label(audience: str) -> str:
    audience_insights.require_audience(audience)
    return "engineering" if audience == audience_insights.AI_ENGINEERING else "investment"


def prompt_cache_key(audience: str, audit_item_id: str) -> str:
    return llm_responses.sharded_prompt_cache_key(
        namespace=f"audience-insights-v2-{_audience_label(audience)}-publication-audit",
        prompt_version=PROMPT_VERSION,
        scope_key=audit_item_id,
        shards=PROMPT_CACHE_SHARDS,
    )


def request_tags(*, audience: str, audit_id: str, day: str) -> tuple[str, ...]:
    return (
        "app:frontier-lab-intelligence",
        "pipeline:audience-insights",
        f"audience:{'ai-engineering' if audience == 'ai_engineering' else audience}",
        "job:publication-calibration-audit",
        f"scope:day-{day}",
        f"prompt:{PROMPT_VERSION}",
        f"run:{audit_id}",
    )


def _legacy_audit_item_id(audience: str, source_candidate_id: str) -> str:
    """Return the v1.0 digest ID retained by already-frozen audit databases."""
    return "audit-" + _sha256(f"{audience}:{source_candidate_id}")[:20]


def _new_audit_item_ids(
    *, audit_id: str, audience: str, source_candidate_ids: Iterable[str]
) -> dict[str, str]:
    """Bind compact opaque IDs without encoding rank or selection state.

    A blinded hash determines sequence order, so neither the number nor its
    lexical order carries source rank, sample kind, or editorial state.  The
    mapping is persisted in ``audit_item`` and reused verbatim on every resume.
    """
    candidate_ids = list(source_candidate_ids)
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("publication audit source candidate IDs must be unique")
    ordered = sorted(
        candidate_ids,
        key=lambda candidate_id: _sha256(
            f"{audit_id}:{audience}:{candidate_id}"
        ),
    )
    width = max(2, len(str(len(ordered))))
    return {
        candidate_id: f"audit-{ordinal:0{width}d}"
        for ordinal, candidate_id in enumerate(ordered, start=1)
    }


def _output_format(audit_item_id: str) -> dict[str, Any]:
    """Constrain structured output to the exact frozen model-facing ID."""
    output_format = json.loads(json.dumps(OUTPUT_FORMAT))
    output_format["schema"]["properties"]["audit_item_id"] = {
        "type": "string",
        "enum": [audit_item_id],
    }
    return output_format


def _audience_item(audience: str, row: Mapping[str, Any]) -> dict[str, Any]:
    fields = json.loads(str(row["audience_fields_json"]))
    expected = (
        ("investment_implication", "what_to_watch")
        if audience == audience_insights.INVESTMENT
        else ("action_type", "engineering_action", "validation_boundary")
    )
    if set(fields) != set(expected):
        raise ValueError(f"candidate {row['candidate_id']} has invalid audience fields")
    return {
        "claim": row["claim"],
        "claim_posture": row["claim_posture"],
        "why_it_matters": row["why_it_matters"],
        **{field: fields[field] for field in expected},
        "supporting_quote": row["supporting_quote"],
        "citation_block_index": row["citation_block_index"],
    }


def _evidence_blocks(packet_json: str) -> list[dict[str, Any]]:
    packet = json.loads(packet_json)
    sources = packet.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("source packet has no evidence blocks")
    blocks = []
    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict) or not isinstance(source.get("text"), str):
            raise ValueError("source packet contains an invalid evidence block")
        blocks.append(
            {
                "block_index": index,
                "source_type": source.get("source_type"),
                "source_author": source.get("author"),
                "source_title": source.get("title"),
                "relation": source.get("relation"),
                "verbatim_text": unicodedata.normalize("NFC", source["text"]),
            }
        )
    return blocks


def _mechanical_citation_valid(item: Mapping[str, Any], blocks: Iterable[Mapping[str, Any]]) -> bool:
    index = item.get("citation_block_index")
    quote = item.get("supporting_quote")
    block_list = list(blocks)
    if type(index) is not int or index < 1 or index > len(block_list):
        return False
    if not isinstance(quote, str) or not quote:
        return False
    normalized_quote = unicodedata.normalize("NFC", quote)
    text = str(block_list[index - 1]["verbatim_text"])
    return text.count(normalized_quote) == 1


def render_input(*, audit_item_id: str, audience: str, evidence_blocks: list[dict[str, Any]], item: Mapping[str, Any]) -> str:
    audience_insights.require_audience(audience)
    if not audit_item_id.startswith("audit-"):
        raise ValueError("audit_item_id must be an opaque audit ID")
    payload = {
        "audit_item_id": audit_item_id,
        "audience": audience,
        "evidence_blocks": evidence_blocks,
        "item": dict(item),
    }
    rendered = _canonical_json(payload)
    forbidden = (
        "feed_rank",
        "editorial_rank",
        "sample_kind",
        "decision_value",
        "audit_reason",
        "failure_codes_json",
        "rationale",
    )
    if any(f'"{field}"' in rendered for field in forbidden):
        raise ValueError("publication audit input leaked source decision metadata")
    return rendered


def _source_rows(source: sqlite3.Connection, *, reject_sample_limit: int) -> tuple[sqlite3.Row, list[tuple[str, sqlite3.Row]]]:
    meta = source.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("source audience run is not frozen")
    selected = source.execute(
        """SELECT item.*
           FROM publication_selection AS selection
           JOIN candidate_item AS item USING (candidate_id)
           ORDER BY item.candidate_id"""
    ).fetchall()
    rejects = source.execute(
        """SELECT item.*
           FROM candidate_item AS item
           JOIN item_review AS review USING (candidate_id)
           LEFT JOIN publication_selection AS selected USING (candidate_id)
           WHERE item.status = 'complete' AND item.outcome = 'insight'
             AND review.status = 'complete'
             AND selected.candidate_id IS NULL
             AND (review.claim_fidelity = 'fail'
                  OR review.epistemic_discipline = 'fail'
                  OR review.audience_usefulness = 'fail'
                  OR review.actionability = 'fail'
                  OR review.specificity = 'fail')
           ORDER BY item.feed_rank, item.candidate_id
           LIMIT ?""",
        (reject_sample_limit,),
    ).fetchall()
    return meta, [("selected", row) for row in selected] + [("review_reject", row) for row in rejects]


def freeze_audit(
    conn: sqlite3.Connection,
    *,
    audit_id: str,
    source_run_db: Path,
    reject_sample_limit: int = DEFAULT_REJECT_SAMPLE_LIMIT,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
) -> int:
    _safe_slug(audit_id, label="audit_id")
    if reject_sample_limit < 0:
        raise ValueError("reject_sample_limit must be non-negative")
    existing = conn.execute("SELECT * FROM audit_run WHERE singleton = 1").fetchone()
    bound_ids = {
        str(row["source_candidate_id"]): str(row["audit_item_id"])
        for row in conn.execute(
            "SELECT source_candidate_id, audit_item_id FROM audit_item"
        ).fetchall()
    }
    source = _open_readonly(source_run_db)
    try:
        meta, rows = _source_rows(source, reject_sample_limit=reject_sample_limit)
        audience = audience_insights.require_audience(str(meta["audience"]))
        source_candidate_ids = [str(row["candidate_id"]) for _, row in rows]
        if existing is not None:
            if set(bound_ids) != set(source_candidate_ids):
                raise ValueError(
                    "audit no longer matches frozen source: source_candidate_ids"
                )
        else:
            bound_ids = _new_audit_item_ids(
                audit_id=audit_id,
                audience=audience,
                source_candidate_ids=source_candidate_ids,
            )
        frozen: list[dict[str, Any]] = []
        for sample_kind, row in rows:
            blocks = _evidence_blocks(str(row["packet_json"]))
            item = _audience_item(audience, row)
            audit_item_id = bound_ids[str(row["candidate_id"])]
            input_text = render_input(
                audit_item_id=audit_item_id,
                audience=audience,
                evidence_blocks=blocks,
                item=item,
            )
            frozen.append(
                {
                    "audit_item_id": audit_item_id,
                    "source_candidate_id": str(row["candidate_id"]),
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
                    "prompt_cache_key": prompt_cache_key(audience, audit_item_id),
                    "mechanical_citation_valid": int(
                        _mechanical_citation_valid(item, blocks)
                    ),
                }
            )
        frozen.sort(key=lambda item: item["audit_item_id"])
        cohort_sha256 = _sha256(
            _canonical_json(
                [
                    {
                        "audit_item_id": item["audit_item_id"],
                        "sample_kind": item["sample_kind"],
                        "source_feed_rank": item["source_feed_rank"],
                        "source_item_sha256": item["source_item_sha256"],
                    }
                    for item in frozen
                ]
            )
        )
        source_contract_sha256 = _sha256(
            _canonical_json(
                {
                    "source_run_id": meta["run_id"],
                    "audience": audience,
                    "day": meta["day"],
                    "prompt_version": meta["prompt_version"],
                    "schema_version": meta["schema_version"],
                    "editor_prompt_version": meta["editor_prompt_version"],
                    "cohort_sha256": cohort_sha256,
                }
            )
        )
    finally:
        source.close()

    if existing is not None:
        expected = {
            "audit_id": audit_id,
            "source_run_db": str(source_run_db.resolve()),
            "source_run_id": str(meta["run_id"]),
            "audience": audience,
            "day": str(meta["day"]),
            "model": model,
            "reasoning_effort": reasoning_effort,
            "prompt_version": PROMPT_VERSION,
            "prompt_sha256": prompt_sha256(),
            "schema_version": SCHEMA_VERSION,
            "reject_sample_limit": reject_sample_limit,
            "selected_count": sum(item["sample_kind"] == "selected" for item in frozen),
            "reject_sample_count": sum(item["sample_kind"] == "review_reject" for item in frozen),
            "cohort_sha256": cohort_sha256,
            "source_contract_sha256": source_contract_sha256,
        }
        mismatches = [key for key, value in expected.items() if existing[key] != value]
        stored_items = {
            str(row["source_candidate_id"]): row
            for row in conn.execute("SELECT * FROM audit_item").fetchall()
        }
        immutable_fields = (
            "audit_item_id",
            "source_event_id",
            "sample_kind",
            "source_feed_rank",
            "frozen_evidence_json",
            "frozen_item_json",
            "source_item_sha256",
            "input_text",
            "input_sha256",
            "prompt_cache_key",
            "mechanical_citation_valid",
        )
        for item in frozen:
            stored = stored_items[item["source_candidate_id"]]
            mismatches.extend(
                f"audit_item.{item['source_candidate_id']}.{field}"
                for field in immutable_fields
                if stored[field] != item[field]
            )
        if mismatches:
            raise ValueError("audit no longer matches frozen source: " + ", ".join(mismatches))
        return len(frozen)

    now = _now()
    selected_count = sum(item["sample_kind"] == "selected" for item in frozen)
    reject_count = len(frozen) - selected_count
    with conn:
        conn.execute(
            """INSERT INTO audit_run
               (singleton, audit_id, source_run_db, source_run_id, audience, day,
                model, reasoning_effort, prompt_version, prompt_sha256,
                schema_version, reject_sample_limit, selected_count,
                reject_sample_count, cohort_sha256, source_contract_sha256,
                created_at, updated_at)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                audit_id,
                str(source_run_db.resolve()),
                str(meta["run_id"]),
                audience,
                str(meta["day"]),
                model,
                reasoning_effort,
                PROMPT_VERSION,
                prompt_sha256(),
                SCHEMA_VERSION,
                reject_sample_limit,
                selected_count,
                reject_count,
                cohort_sha256,
                source_contract_sha256,
                now,
                now,
            ),
        )
        conn.executemany(
            """INSERT INTO audit_item
               (audit_item_id, source_candidate_id, source_event_id,
                sample_kind, source_feed_rank, frozen_evidence_json,
                frozen_item_json, source_item_sha256, input_text, input_sha256,
                prompt_cache_key, mechanical_citation_valid, updated_at)
               VALUES (:audit_item_id, :source_candidate_id, :source_event_id,
                       :sample_kind, :source_feed_rank, :frozen_evidence_json,
                       :frozen_item_json, :source_item_sha256, :input_text,
                       :input_sha256, :prompt_cache_key,
                       :mechanical_citation_valid, :updated_at)""",
            [{**item, "updated_at": now} for item in frozen],
        )
    return len(frozen)


def validate_output(output_text: str, *, expected_audit_item_id: str) -> dict[str, Any]:
    payload = json.loads(output_text)
    if not isinstance(payload, dict) or set(payload) != set(OUTPUT_FIELDS):
        raise ValueError("response does not match the exact publication-audit schema")
    if payload["audit_item_id"] != expected_audit_item_id:
        raise ValueError("auditor returned the wrong audit_item_id")
    for field in JUDGMENT_FIELDS:
        if payload[field] not in PASS_FAIL:
            raise ValueError(f"invalid {field}: {payload[field]!r}")
    codes = payload["failure_codes"]
    if not isinstance(codes, list) or any(code not in FAILURE_CODES for code in codes):
        raise ValueError("auditor returned invalid failure_codes")
    if len(codes) != len(set(codes)):
        raise ValueError("failure_codes must be unique")
    has_failure = any(payload[field] == "fail" for field in JUDGMENT_FIELDS)
    if has_failure != bool(codes):
        raise ValueError("failure_codes must be present exactly when a judgment fails")
    rationale = payload["rationale"]
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("rationale must be a non-empty string")
    return {**payload, "failure_codes": list(codes), "rationale": rationale.strip()}


def _usage_value(usage: Any, field: str) -> int | None:
    value = usage.get(field) if isinstance(usage, dict) else getattr(usage, field, None)
    return int(value) if value is not None else None


def _input_detail(usage: Any, field: str) -> int | None:
    details = usage.get("input_tokens_details") if isinstance(usage, dict) else getattr(usage, "input_tokens_details", None)
    return _usage_value(details, field)


def evaluate_item(client: Any, row: Mapping[str, Any], *, meta: Mapping[str, Any]) -> dict[str, Any]:
    tags = request_tags(
        audience=str(meta["audience"]),
        audit_id=str(meta["audit_id"]),
        day=str(meta["day"]),
    )
    request = {
        "model": str(meta["model"]),
        "instructions": instructions(),
        "input": str(row["input_text"]),
        "prompt_cache_key": str(row["prompt_cache_key"]),
        **llm_responses.litellm_prompt_cache_kwargs(str(meta["model"])),
        "reasoning": {"effort": str(meta["reasoning_effort"])},
        "text": {"format": _output_format(str(row["audit_item_id"]))},
        "store": False,
        "extra_body": {"metadata": {"tags": list(tags)}},
        "extra_headers": {"x-litellm-tags": ",".join(tags)},
    }
    raw_api = getattr(client.responses, "with_raw_response", None)
    if raw_api is None:
        response = client.responses.create(**request)
        reported_cost = None
    else:
        raw_response = raw_api.create(**request)
        response = raw_response.parse()
        reported_cost = llm_responses.reported_cost(raw_response.headers)
    response_data = llm_responses.as_dict(response)
    if response_data.get("status") not in (None, "completed"):
        raise ValueError(f"response status was {response_data.get('status')!r}")
    raw_output_text = llm_responses.output_text(dict(response_data))
    usage = getattr(response, "usage", None) or response_data.get("usage")
    telemetry = {
        "raw_output_text": raw_output_text,
        "response_id": getattr(response, "id", None) or response_data.get("id"),
        "response_model": getattr(response, "model", None) or response_data.get("model"),
        "input_tokens": _usage_value(usage, "input_tokens"),
        "cached_tokens": _input_detail(usage, "cached_tokens"),
        "cache_write_tokens": _input_detail(usage, "cache_write_tokens"),
        "output_tokens": _usage_value(usage, "output_tokens"),
        "reported_cost_usd": reported_cost,
        "request_tags": list(tags),
    }
    try:
        result = validate_output(
            raw_output_text,
            expected_audit_item_id=str(row["audit_item_id"]),
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise AuditValidationError(str(exc), result=telemetry) from exc
    return {**result, **telemetry}


def _error_provenance(error: Exception) -> Mapping[str, Any]:
    return error.result if isinstance(error, AuditValidationError) else {}


def _store_attempt(
    conn: sqlite3.Connection,
    *,
    row: sqlite3.Row,
    meta: sqlite3.Row,
    status: str,
    result: Mapping[str, Any] | None = None,
    error: Exception | None = None,
) -> None:
    attempt = int(row["attempts"]) + 1
    provenance = dict(result or _error_provenance(error or ValueError()))
    tags = provenance.get("request_tags") or request_tags(
        audience=str(meta["audience"]), audit_id=str(meta["audit_id"]), day=str(meta["day"])
    )
    conn.execute(
        """INSERT INTO audit_attempt
           (audit_item_id, attempt_number, status, model, reasoning_effort,
            prompt_version, prompt_sha256, schema_version, input_sha256,
            prompt_cache_key, result_json, raw_output_text, error_type,
            error_message, response_id, response_model, input_tokens,
            cached_tokens, cache_write_tokens, output_tokens, reported_cost_usd,
            request_tags_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            row["audit_item_id"], attempt, status, meta["model"],
            meta["reasoning_effort"], PROMPT_VERSION, prompt_sha256(),
            SCHEMA_VERSION, row["input_sha256"], row["prompt_cache_key"],
            _canonical_json(result) if result is not None else None,
            provenance.get("raw_output_text"),
            type(error).__name__ if error is not None else None,
            str(error) if error is not None else None,
            provenance.get("response_id"), provenance.get("response_model"),
            provenance.get("input_tokens"), provenance.get("cached_tokens"),
            provenance.get("cache_write_tokens"), provenance.get("output_tokens"),
            provenance.get("reported_cost_usd"), _canonical_json(list(tags)), _now(),
        ),
    )


def _store_success(conn: sqlite3.Connection, row: sqlite3.Row, meta: sqlite3.Row, result: Mapping[str, Any]) -> None:
    now = _now()
    with conn:
        _store_attempt(conn, row=row, meta=meta, status="complete", result=result)
        conn.execute(
            """UPDATE audit_item
               SET status = 'complete', attempts = attempts + 1,
                   citation_fidelity = ?, attribution_fidelity = ?,
                   epistemic_discipline = ?, audience_usefulness = ?,
                   actionability = ?, specificity = ?, failure_codes_json = ?,
                   rationale = ?, completed_at = ?, updated_at = ?
               WHERE audit_item_id = ?""",
            (
                result["citation_fidelity"], result["attribution_fidelity"],
                result["epistemic_discipline"], result["audience_usefulness"],
                result["actionability"], result["specificity"],
                _canonical_json(result["failure_codes"]), result["rationale"],
                now, now, row["audit_item_id"],
            ),
        )


def _store_failure(conn: sqlite3.Connection, row: sqlite3.Row, meta: sqlite3.Row, error: Exception) -> str:
    attempt = int(row["attempts"]) + 1
    terminal = isinstance(error, AuditValidationError) and attempt >= MAX_ATTEMPTS
    status = "rejected" if terminal else "failed"
    with conn:
        _store_attempt(conn, row=row, meta=meta, status=status, error=error)
        conn.execute(
            """UPDATE audit_item
               SET status = ?, attempts = attempts + 1, updated_at = ?
               WHERE audit_item_id = ?""",
            (status, _now(), row["audit_item_id"]),
        )
    return status


def run_pending(
    conn: sqlite3.Connection,
    *,
    client: Any,
    workers: int = DEFAULT_WORKERS,
    retry_failed: bool = False,
) -> dict[str, Any]:
    if workers < 1:
        raise ValueError("workers must be positive")
    meta = conn.execute("SELECT * FROM audit_run WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("publication audit has not been frozen")
    if retry_failed:
        rows = conn.execute(
            """SELECT item.* FROM audit_item AS item
               WHERE item.status IN ('pending', 'failed')
                  OR (
                      item.status = 'rejected'
                      AND item.attempts = ?
                      AND length(item.audit_item_id) = 26
                      AND EXISTS (
                          SELECT 1 FROM audit_attempt AS attempt
                          WHERE attempt.audit_item_id = item.audit_item_id
                            AND attempt.attempt_number = item.attempts
                            AND attempt.error_message =
                                'auditor returned the wrong audit_item_id'
                      )
                  )
               ORDER BY item.prompt_cache_key, item.audit_item_id""",
            (MAX_ATTEMPTS,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM audit_item
               WHERE status = 'pending'
               ORDER BY prompt_cache_key, audit_item_id"""
        ).fetchall()
    lanes: dict[str, deque[sqlite3.Row]] = {}
    for row in rows:
        lanes.setdefault(str(row["prompt_cache_key"]), deque()).append(row)

    def evaluate(row: sqlite3.Row) -> tuple[sqlite3.Row, Mapping[str, Any] | None, Exception | None]:
        try:
            return row, evaluate_item(client, row, meta=meta), None
        except Exception as exc:  # stored with bounded provenance for unattended resumption
            return row, None, exc

    waiting = deque(lanes)
    active: dict[concurrent.futures.Future, str] = {}
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=min(workers, len(lanes)) or 1)

    def start(cache_key: str) -> None:
        active[executor.submit(evaluate, lanes[cache_key].popleft())] = cache_key

    while waiting and len(active) < workers:
        start(waiting.popleft())
    try:
        while active:
            done, _ = concurrent.futures.wait(active, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                cache_key = active.pop(future)
                row, result, error = future.result()
                if result is not None:
                    _store_success(conn, row, meta, result)
                else:
                    assert error is not None
                    _store_failure(conn, row, meta, error)
                if lanes[cache_key]:
                    start(cache_key)
                elif waiting:
                    start(waiting.popleft())
    finally:
        executor.shutdown(wait=True, cancel_futures=False)
    return summary(conn)


def summary(conn: sqlite3.Connection) -> dict[str, Any]:
    meta = conn.execute("SELECT * FROM audit_run WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("publication audit has not been frozen")
    counts = [
        dict(row)
        for row in conn.execute(
            """SELECT sample_kind, COUNT(*) AS total,
                      SUM(status = 'pending') AS pending,
                      SUM(status = 'complete') AS complete,
                      SUM(status = 'failed') AS failed,
                      SUM(status = 'rejected') AS rejected
               FROM audit_item GROUP BY sample_kind ORDER BY sample_kind"""
        )
    ]
    selected = dict(
        conn.execute(
            """SELECT COUNT(*) AS total,
                      SUM(status = 'complete') AS complete,
                      SUM(mechanical_citation_valid = 0) AS mechanical_citation_failures,
                      SUM(status = 'complete' AND citation_fidelity = 'fail') AS citation_fidelity_failures,
                      SUM(status = 'complete' AND attribution_fidelity = 'fail') AS attribution_failures,
                      SUM(status = 'complete' AND epistemic_discipline = 'fail') AS epistemic_failures,
                      SUM(status = 'complete' AND audience_usefulness = 'pass') AS usefulness_passes,
                      SUM(status = 'complete' AND actionability = 'pass') AS actionability_passes,
                      SUM(status = 'complete' AND specificity = 'pass') AS specificity_passes,
                      SUM(status = 'complete' AND audience_usefulness = 'pass'
                          AND actionability = 'pass' AND specificity = 'pass') AS full_quality_passes
               FROM audit_item WHERE sample_kind = 'selected'"""
        ).fetchone()
    )
    for key, value in tuple(selected.items()):
        selected[key] = int(value or 0)
    required_quality = math.ceil(0.8 * selected["total"])
    selected["required_quality_passes"] = required_quality
    selected["usefulness_ratio"] = round(selected["usefulness_passes"] / selected["total"], 6) if selected["total"] else 1.0
    selected["actionability_ratio"] = round(selected["actionability_passes"] / selected["total"], 6) if selected["total"] else 1.0
    selected["specificity_ratio"] = round(selected["specificity_passes"] / selected["total"], 6) if selected["total"] else 1.0
    selected["full_quality_ratio"] = round(selected["full_quality_passes"] / selected["total"], 6) if selected["total"] else 1.0
    false_negative_rows = conn.execute(
        """SELECT audit_item_id, source_candidate_id
           FROM audit_item
           WHERE sample_kind = 'review_reject' AND status = 'complete'
             AND mechanical_citation_valid = 1
             AND citation_fidelity = 'pass' AND attribution_fidelity = 'pass'
             AND epistemic_discipline = 'pass' AND audience_usefulness = 'pass'
             AND actionability = 'pass' AND specificity = 'pass'
           ORDER BY audit_item_id"""
    ).fetchall()
    false_negatives = {
        "count": len(false_negative_rows),
        "audit_item_ids": [str(row["audit_item_id"]) for row in false_negative_rows],
        "source_candidate_ids": [str(row["source_candidate_id"]) for row in false_negative_rows],
    }
    checks = {
        "audit_cohort_complete": all(
            int(row["complete"] or 0) == int(row["total"] or 0) for row in counts
        ),
        "selected_audit_complete": selected["complete"] == selected["total"],
        "zero_selected_mechanical_citation_failures": selected["mechanical_citation_failures"] == 0,
        "zero_selected_citation_fidelity_failures": selected["citation_fidelity_failures"] == 0,
        "zero_selected_attribution_failures": selected["attribution_failures"] == 0,
        "zero_selected_epistemic_failures": selected["epistemic_failures"] == 0,
        "selected_quality_at_least_80_percent": selected["full_quality_passes"] >= required_quality,
    }
    attempts = dict(
        conn.execute(
            """SELECT COUNT(*) AS count,
                      SUM(COALESCE(input_tokens, 0)) AS input_tokens,
                      SUM(COALESCE(cached_tokens, 0)) AS cached_tokens,
                      SUM(COALESCE(cache_write_tokens, 0)) AS cache_write_tokens,
                      SUM(COALESCE(output_tokens, 0)) AS output_tokens,
                      SUM(COALESCE(reported_cost_usd, 0)) AS reported_cost_usd
               FROM audit_attempt"""
        ).fetchone()
    )
    return {
        "run": dict(meta),
        "counts": counts,
        "selected_metrics": selected,
        "false_negative_review_rejects": false_negatives,
        "checks": checks,
        "passed": all(checks.values()),
        "duplicate_and_padding_scope": "evaluated separately by the source day-set gate",
        "attempts": attempts,
    }


def audit_result_sha256(conn: sqlite3.Connection) -> str:
    """Digest every blinded audit judgment in deterministic item order."""
    item_fields = (
        "audit_item_id",
        "source_candidate_id",
        "sample_kind",
        "source_item_sha256",
        "mechanical_citation_valid",
        "status",
        *JUDGMENT_FIELDS,
    )
    items = []
    for row in conn.execute(
        "SELECT * FROM audit_item ORDER BY audit_item_id"
    ).fetchall():
        failure_codes = (
            json.loads(str(row["failure_codes_json"]))
            if row["failure_codes_json"] is not None
            else None
        )
        items.append(
            {
                **{field: row[field] for field in item_fields},
                "failure_codes_json": failure_codes,
            }
        )
    return _sha256(_canonical_json(items))


def _validate_audit_attempt_provenance(
    audit: sqlite3.Connection,
    *,
    audit_meta: sqlite3.Row,
    stored_items: Mapping[str, sqlite3.Row],
) -> None:
    """Bind every authorized judgment to its exact stored request attempt.

    ``audit_item`` is a query projection; ``audit_attempt`` is the immutable
    request/result ledger.  Publication may therefore trust an item only when
    the ledger is contiguous, has no surplus or missing rows, and its final
    successful result agrees with both the raw provider output and every
    projected judgment/telemetry field.
    """
    expected_tags = list(
        request_tags(
            audience=str(audit_meta["audience"]),
            audit_id=str(audit_meta["audit_id"]),
            day=str(audit_meta["day"]),
        )
    )
    immutable_attempt_fields = {
        "model": str(audit_meta["model"]),
        "reasoning_effort": str(audit_meta["reasoning_effort"]),
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": prompt_sha256(),
        "schema_version": SCHEMA_VERSION,
    }

    for candidate_id, item in sorted(stored_items.items()):
        audit_item_id = str(item["audit_item_id"])
        attempts = audit.execute(
            "SELECT * FROM audit_attempt WHERE audit_item_id = ? "
            "ORDER BY attempt_number",
            (audit_item_id,),
        ).fetchall()
        expected_attempt_count = int(item["attempts"])
        if expected_attempt_count < 1 or len(attempts) != expected_attempt_count:
            raise ValueError(
                f"publication audit item {candidate_id} attempt count does not match"
            )
        if [int(row["attempt_number"]) for row in attempts] != list(
            range(1, expected_attempt_count + 1)
        ):
            raise ValueError(
                f"publication audit item {candidate_id} attempts are not contiguous"
            )

        for index, attempt in enumerate(attempts):
            expected_fields = {
                **immutable_attempt_fields,
                "input_sha256": str(item["input_sha256"]),
                "prompt_cache_key": str(item["prompt_cache_key"]),
            }
            drift = [
                field
                for field, expected in expected_fields.items()
                if attempt[field] != expected
            ]
            if drift:
                raise ValueError(
                    f"publication audit item {candidate_id} attempt metadata drift: "
                    + ", ".join(drift)
                )
            try:
                attempt_tags = json.loads(str(attempt["request_tags_json"]))
            except (TypeError, json.JSONDecodeError) as exc:
                raise ValueError(
                    f"publication audit item {candidate_id} has invalid attempt tags"
                ) from exc
            if attempt_tags != expected_tags:
                raise ValueError(
                    f"publication audit item {candidate_id} attempt tags drifted"
                )

            is_final = index == len(attempts) - 1
            if not is_final:
                if (
                    str(attempt["status"]) != "failed"
                    or attempt["result_json"] is not None
                    or attempt["error_type"] is None
                    or attempt["error_message"] is None
                ):
                    raise ValueError(
                        f"publication audit item {candidate_id} has an invalid prior attempt"
                    )
                continue

            if (
                str(attempt["status"]) != "complete"
                or attempt["result_json"] is None
                or attempt["error_type"] is not None
                or attempt["error_message"] is not None
            ):
                raise ValueError(
                    f"publication audit item {candidate_id} lacks a final successful attempt"
                )
            try:
                result = json.loads(str(attempt["result_json"]))
            except (TypeError, json.JSONDecodeError) as exc:
                raise ValueError(
                    f"publication audit item {candidate_id} has invalid final result JSON"
                ) from exc
            if not isinstance(result, dict) or set(result) != set(
                SUCCESS_RESULT_FIELDS
            ):
                raise ValueError(
                    f"publication audit item {candidate_id} final result schema drifted"
                )

            output = validate_output(
                _canonical_json({field: result[field] for field in OUTPUT_FIELDS}),
                expected_audit_item_id=audit_item_id,
            )
            raw_output = result["raw_output_text"]
            if not isinstance(raw_output, str) or not raw_output:
                raise ValueError(
                    f"publication audit item {candidate_id} lacks raw provider output"
                )
            try:
                raw_result = validate_output(
                    raw_output,
                    expected_audit_item_id=audit_item_id,
                )
            except (json.JSONDecodeError, ValueError) as exc:
                raise ValueError(
                    f"publication audit item {candidate_id} raw provider output is invalid"
                ) from exc
            if raw_result != output:
                raise ValueError(
                    f"publication audit item {candidate_id} final result diverges from raw output"
                )

            item_projection = {
                "audit_item_id": audit_item_id,
                **{field: item[field] for field in JUDGMENT_FIELDS},
                "failure_codes": json.loads(str(item["failure_codes_json"])),
                "rationale": str(item["rationale"]),
            }
            if item_projection != output:
                raise ValueError(
                    f"publication audit item {candidate_id} judgments do not match "
                    "the final audit attempt"
                )

            telemetry_columns = {
                field: attempt[field]
                for field in SUCCESS_TELEMETRY_FIELDS
                if field != "request_tags"
            }
            telemetry_result = {
                field: result[field]
                for field in SUCCESS_TELEMETRY_FIELDS
                if field != "request_tags"
            }
            if telemetry_result != telemetry_columns or result["request_tags"] != expected_tags:
                raise ValueError(
                    f"publication audit item {candidate_id} response telemetry drifted"
                )
            if (
                not isinstance(result["response_id"], str)
                or not result["response_id"]
                or not isinstance(result["response_model"], str)
                or not result["response_model"]
                or type(result["input_tokens"]) is not int
                or result["input_tokens"] < 0
                or type(result["output_tokens"]) is not int
                or result["output_tokens"] < 0
                or any(
                    value is not None
                    and (type(value) is not int or value < 0)
                    for value in (
                        result["cached_tokens"],
                        result["cache_write_tokens"],
                    )
                )
                or isinstance(result["reported_cost_usd"], bool)
                or not isinstance(result["reported_cost_usd"], (int, float))
                or result["reported_cost_usd"] < 0
            ):
                raise ValueError(
                    f"publication audit item {candidate_id} response telemetry is incomplete"
                )


def _validate_false_negative_adjudication(
    *,
    path: Path,
    audit_meta: sqlite3.Row,
    audit_result_digest: str,
    false_negative_rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    false_negatives = {
        (str(row["audit_item_id"]), str(row["source_candidate_id"]))
        for row in false_negative_rows
    }
    if not false_negatives:
        return {
            "required": False,
            "passed": True,
            "path": None,
            "decision_count": 0,
        }
    if not path.is_file():
        raise ValueError("publication audit false negatives have not been adjudicated")
    payload = json.loads(path.read_text())
    expected_fields = {
        "schema_version",
        "audit_id",
        "source_run_id",
        "audit_cohort_sha256",
        "audit_result_sha256",
        "source_contract_sha256",
        "adjudications",
    }
    if not isinstance(payload, dict) or set(payload) != expected_fields:
        raise ValueError("publication audit adjudication has an invalid schema")
    expected_header = {
        "schema_version": ADJUDICATION_SCHEMA_VERSION,
        "audit_id": str(audit_meta["audit_id"]),
        "source_run_id": str(audit_meta["source_run_id"]),
        "audit_cohort_sha256": str(audit_meta["cohort_sha256"]),
        "audit_result_sha256": audit_result_digest,
        "source_contract_sha256": str(audit_meta["source_contract_sha256"]),
    }
    if any(payload[field] != value for field, value in expected_header.items()):
        raise ValueError("publication audit adjudication does not match this audit")
    adjudications = payload["adjudications"]
    if not isinstance(adjudications, list):
        raise ValueError("publication audit adjudications must be a list")
    by_item: dict[tuple[str, str], Mapping[str, Any]] = {}
    for adjudication in adjudications:
        if not isinstance(adjudication, dict) or set(adjudication) != {
            "audit_item_id",
            "source_candidate_id",
            "verdict",
            "rationale",
        }:
            raise ValueError("publication audit adjudication is malformed")
        key = (
            adjudication["audit_item_id"],
            adjudication["source_candidate_id"],
        )
        if not all(isinstance(value, str) for value in key) or key in by_item:
            raise ValueError("publication audit adjudication targets must be unique")
        by_item[key] = adjudication
    if set(by_item) != false_negatives:
        raise ValueError("publication audit adjudication does not cover exact false negatives")
    for adjudication in by_item.values():
        if adjudication["verdict"] != "would_not_enter":
            raise ValueError("a publication audit false negative remains blocking")
        rationale = adjudication["rationale"]
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError("publication audit adjudication requires a rationale")
    return {
        "required": True,
        "passed": True,
        "path": str(path),
        "decision_count": len(by_item),
        "sha256": _sha256(path.read_text()),
    }


def _validate_readonly_publication_audit(
    *,
    source_run_db: Path | str,
    audit_db: Path | str,
    expected_selected_count: int,
    require_passed: bool,
) -> dict[str, Any]:
    """Validate one completed audit against its exact, current source run.

    This is the publication-side counterpart to :func:`freeze_audit`.  It
    deliberately opens both databases read-only and reconstructs the frozen
    cohort from the source run, so callers cannot accidentally repair, resume,
    or otherwise mutate an audit while deciding whether a run is publishable.
    A successful return means that the audit still describes the exact active
    publication selection and reject sample it originally evaluated.
    """
    if expected_selected_count < 0:
        raise ValueError("expected_selected_count must be non-negative")
    source_path = Path(source_run_db).resolve()
    audit_path = Path(audit_db).resolve()
    source = _open_readonly(source_path)
    audit = _open_readonly(audit_path)
    try:
        audit_meta = audit.execute(
            "SELECT * FROM audit_run WHERE singleton = 1"
        ).fetchone()
        if audit_meta is None:
            raise ValueError("publication audit has not been frozen")
        if Path(str(audit_meta["source_run_db"])).resolve() != source_path:
            raise ValueError("publication audit points at a different source database")
        if str(audit_meta["prompt_version"]) != PROMPT_VERSION:
            raise ValueError("publication audit uses a different prompt version")
        if str(audit_meta["prompt_sha256"]) != prompt_sha256():
            raise ValueError("publication audit prompt digest does not match")
        if str(audit_meta["schema_version"]) != SCHEMA_VERSION:
            raise ValueError("publication audit uses a different schema version")

        reject_sample_limit = int(audit_meta["reject_sample_limit"])
        source_meta, source_rows = _source_rows(
            source,
            reject_sample_limit=reject_sample_limit,
        )
        audience = audience_insights.require_audience(str(source_meta["audience"]))
        source_identity = {
            "source_run_id": str(source_meta["run_id"]),
            "audience": audience,
            "day": str(source_meta["day"]),
        }
        for field, expected in source_identity.items():
            if str(audit_meta[field]) != expected:
                raise ValueError(f"publication audit {field} does not match source")

        stored_items = {
            str(row["source_candidate_id"]): row
            for row in audit.execute("SELECT * FROM audit_item").fetchall()
        }
        source_candidate_ids = [
            str(row["candidate_id"]) for _, row in source_rows
        ]
        if len(source_candidate_ids) != len(set(source_candidate_ids)):
            raise ValueError("publication audit source candidate IDs are not unique")
        if set(stored_items) != set(source_candidate_ids):
            raise ValueError("publication audit cohort no longer matches source")

        frozen: list[dict[str, Any]] = []
        for sample_kind, source_row in source_rows:
            candidate_id = str(source_row["candidate_id"])
            stored = stored_items[candidate_id]
            audit_item_id = str(stored["audit_item_id"])
            blocks = _evidence_blocks(str(source_row["packet_json"]))
            item = _audience_item(audience, source_row)
            input_text = render_input(
                audit_item_id=audit_item_id,
                audience=audience,
                evidence_blocks=blocks,
                item=item,
            )
            expected_item = {
                "source_event_id": str(source_row["event_id"]),
                "sample_kind": sample_kind,
                "source_feed_rank": int(source_row["feed_rank"]),
                "frozen_evidence_json": _canonical_json(blocks),
                "frozen_item_json": _canonical_json(item),
                "source_item_sha256": _sha256(
                    _canonical_json({"blocks": blocks, "item": item})
                ),
                "input_text": input_text,
                "input_sha256": _sha256(input_text),
                "prompt_cache_key": prompt_cache_key(audience, audit_item_id),
                "mechanical_citation_valid": int(
                    _mechanical_citation_valid(item, blocks)
                ),
            }
            mismatches = [
                field
                for field, expected in expected_item.items()
                if stored[field] != expected
            ]
            if mismatches:
                raise ValueError(
                    f"publication audit item {candidate_id} no longer matches source: "
                    + ", ".join(mismatches)
                )
            frozen.append(
                {
                    "audit_item_id": audit_item_id,
                    "sample_kind": sample_kind,
                    "source_feed_rank": int(source_row["feed_rank"]),
                    "source_item_sha256": expected_item["source_item_sha256"],
                }
            )

        frozen.sort(key=lambda item: item["audit_item_id"])
        cohort_sha256 = _sha256(_canonical_json(frozen))
        source_contract_sha256 = _sha256(
            _canonical_json(
                {
                    "source_run_id": source_meta["run_id"],
                    "audience": audience,
                    "day": source_meta["day"],
                    "prompt_version": source_meta["prompt_version"],
                    "schema_version": source_meta["schema_version"],
                    "editor_prompt_version": source_meta["editor_prompt_version"],
                    "cohort_sha256": cohort_sha256,
                }
            )
        )
        selected_count = sum(
            item["sample_kind"] == "selected" for item in frozen
        )
        reject_count = len(frozen) - selected_count
        expected_meta = {
            "selected_count": selected_count,
            "reject_sample_count": reject_count,
            "cohort_sha256": cohort_sha256,
            "source_contract_sha256": source_contract_sha256,
        }
        mismatches = [
            field
            for field, expected in expected_meta.items()
            if audit_meta[field] != expected
        ]
        if mismatches:
            raise ValueError(
                "publication audit metadata no longer matches source: "
                + ", ".join(mismatches)
            )
        if selected_count != expected_selected_count:
            raise ValueError(
                "publication audit selected count does not match active publication set"
            )

        total_items, incomplete_items = audit.execute(
            """SELECT COUNT(*),
                      SUM(status != 'complete')
               FROM audit_item"""
        ).fetchone()
        if int(total_items or 0) != len(frozen) or int(incomplete_items or 0):
            raise ValueError("publication audit is incomplete")
        _validate_audit_attempt_provenance(
            audit,
            audit_meta=audit_meta,
            stored_items=stored_items,
        )

        report = summary(audit)
        if require_passed and not bool(report["passed"]):
            raise ValueError("publication audit summary did not pass")
        if int(report["selected_metrics"]["total"]) != expected_selected_count:
            raise ValueError("publication audit summary selected count does not match")
        adjudication = _validate_false_negative_adjudication(
            path=audit_path.parent / ADJUDICATION_FILENAME,
            audit_meta=audit_meta,
            audit_result_digest=audit_result_sha256(audit),
            false_negative_rows=audit.execute(
                """SELECT audit_item_id, source_candidate_id
                   FROM audit_item
                   WHERE sample_kind = 'review_reject' AND status = 'complete'
                     AND mechanical_citation_valid = 1
                     AND citation_fidelity = 'pass'
                     AND attribution_fidelity = 'pass'
                     AND epistemic_discipline = 'pass'
                     AND audience_usefulness = 'pass'
                     AND actionability = 'pass' AND specificity = 'pass'
                   ORDER BY audit_item_id"""
            ).fetchall(),
        )
        return {
            **report,
            "audit_id": str(audit_meta["audit_id"]),
            "audit_cohort_sha256": str(audit_meta["cohort_sha256"]),
            "audit_result_sha256": audit_result_sha256(audit),
            "source_contract_sha256": str(audit_meta["source_contract_sha256"]),
            "false_negative_adjudication": adjudication,
        }
    finally:
        audit.close()
        source.close()


def validate_readonly_publication_audit(
    *,
    source_run_db: Path | str,
    audit_db: Path | str,
    expected_selected_count: int,
) -> dict[str, Any]:
    """Fail closed unless an exact, completed adjacent audit passes."""
    return _validate_readonly_publication_audit(
        source_run_db=source_run_db,
        audit_db=audit_db,
        expected_selected_count=expected_selected_count,
        require_passed=True,
    )


def default_finalization_path(source_run_db: Path | str) -> Path:
    """Return the immutable publication-finalization sidecar for one run."""
    return Path(source_run_db).resolve().parent / FINALIZATION_DIR / FINALIZATION_FILENAME


def default_editorial_finalization_path(source_run_db: Path | str) -> Path:
    """Return the immutable terminal editorial layer for one finalized run."""
    return (
        Path(source_run_db).resolve().parent
        / EDITORIAL_FINALIZATION_DIR
        / FINALIZATION_FILENAME
    )


def terminal_finalization_path(source_run_db: Path | str) -> Path:
    """Return the terminal adjacent sidecar, preferring a composed editorial layer."""
    editorial = default_editorial_finalization_path(source_run_db)
    if editorial.is_file():
        return editorial
    return default_finalization_path(source_run_db)


def _row_sha256(row: sqlite3.Row) -> str:
    return _sha256(_canonical_json(dict(row)))


def _required_singleton(
    conn: sqlite3.Connection, table: str
) -> sqlite3.Row:
    row = conn.execute(f"SELECT * FROM {table} WHERE singleton = 1").fetchone()
    if row is None:
        raise ValueError(f"publication finalization requires {table}")
    return row


def _review_selected_ids(row: sqlite3.Row, *, label: str) -> list[str]:
    try:
        payload = json.loads(str(row["input_text"]))
        selected = payload["selected"]
        ids = [str(item["candidate_id"]) for item in selected]
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} does not bind an exact selected set") from exc
    if len(ids) != len(set(ids)):
        raise ValueError(f"{label} selected IDs are not unique")
    return ids


def _finalization_evidence(
    *,
    source_path: Path,
    audit_path: Path,
    audit_report: Mapping[str, Any],
) -> dict[str, Any]:
    """Reconstruct an immutable failed-item removal from one published set.

    The projection may only remove selected items that independently failed the
    publication audit.  It never promotes a review reject, substitutes another
    candidate, changes source rows, or reorders the surviving selection.
    """
    source = _open_readonly(source_path)
    audit = _open_readonly(audit_path)
    try:
        run = _required_singleton(source, "run_meta")
        editor = _required_singleton(source, "editor_run")
        gate = _required_singleton(source, "quality_gate")
        day_review = _required_singleton(source, "day_set_review")
        reconciliation = source.execute(
            "SELECT * FROM selection_reconciliation WHERE singleton = 1"
        ).fetchone()
        reconciled_review = source.execute(
            "SELECT * FROM reconciled_day_set_review WHERE singleton = 1"
        ).fetchone()
        base_selection = source.execute(
            "SELECT * FROM publication_selection ORDER BY publication_rank"
        ).fetchall()
        daily_selection = source.execute(
            "SELECT * FROM daily_selection ORDER BY editorial_rank"
        ).fetchall()
        if not base_selection:
            raise ValueError("publication finalization requires an active item")
        base_ids = [str(row["candidate_id"]) for row in base_selection]
        original_ids = [str(row["candidate_id"]) for row in daily_selection]
        if [int(row["publication_rank"]) for row in base_selection] != list(
            range(1, len(base_selection) + 1)
        ):
            raise ValueError("publication finalization requires contiguous publication ranks")
        if str(editor["status"]) != "complete" or int(
            editor["selected_count"] or -1
        ) != len(daily_selection):
            raise ValueError("publication finalization requires the completed editor set")
        if int(gate["passed"]) != 1:
            raise ValueError("publication finalization requires the internal gate to pass")
        gate_result = json.loads(str(gate["result_json"]))
        if not bool(gate_result.get("passed")) or int(
            gate_result.get("selected_count", -1)
        ) != len(base_ids):
            raise ValueError(
                "publication finalization requires a gate bound to the active items"
            )
        original_review_ids = _review_selected_ids(
            day_review, label="original day review"
        )
        if len(original_review_ids) != len(original_ids) or set(
            original_review_ids
        ) != set(original_ids):
            raise ValueError("original day review no longer matches the editor selection")
        if len(daily_selection) == len(base_selection):
            if original_ids != base_ids:
                raise ValueError(
                    "publication finalization direct selection no longer matches the editor"
                )
            if [
                int(row["original_editorial_rank"]) for row in base_selection
            ] != [int(row["editorial_rank"]) for row in daily_selection]:
                raise ValueError(
                    "publication finalization direct selection changed editorial ranks"
                )
            if str(day_review["status"]) != "complete" or int(
                day_review["padding_detected"] or 0
            ) != 0:
                raise ValueError(
                    "publication finalization requires the direct set to pass padding review"
                )
            if reconciliation is not None or reconciled_review is not None:
                raise ValueError(
                    "publication finalization direct path has unexpected reconciliation state"
                )
            reconciliation_sha256 = None
            reconciled_review_sha256 = None
        elif len(daily_selection) == len(base_selection) + 1:
            if [
                int(row["original_editorial_rank"]) for row in base_selection
            ] != list(range(1, len(base_selection) + 1)):
                raise ValueError(
                    "publication finalization requires the editor's leading survivors"
                )
            if str(day_review["status"]) != "complete" or int(
                day_review["padding_detected"] or 0
            ) != 1:
                raise ValueError(
                    "publication finalization requires the original padding finding"
                )
            if reconciliation is None or reconciled_review is None:
                raise ValueError(
                    "publication finalization requires completed padding reconciliation"
                )
            if (
                str(reconciliation["status"]) != "complete"
                or str(reconciliation["reason_code"]) != "padding_tail_trim"
            ):
                raise ValueError(
                    "publication finalization requires completed padding reconciliation"
                )
            reconciled_original = json.loads(
                str(reconciliation["original_selected_ids_json"])
            )
            reconciled_active = json.loads(
                str(reconciliation["active_selected_ids_json"])
            )
            if reconciled_original != original_ids or reconciled_active != base_ids:
                raise ValueError(
                    "padding reconciliation no longer matches the source selections"
                )
            if (
                str(reconciliation["removed_candidate_id"]) != original_ids[-1]
                or int(reconciliation["removed_editorial_rank"])
                != len(original_ids)
                or str(reconciliation["source_review_input_sha256"])
                != str(day_review["input_sha256"])
            ):
                raise ValueError(
                    "padding reconciliation does not identify the exact editor tail"
                )
            if (
                str(reconciled_review["status"]) != "complete"
                or str(reconciled_review["reconciliation_reason"])
                != "padding_tail_trim"
                or int(reconciled_review["padding_detected"] or 0) != 0
                or int(reconciled_review["thin_day_honest"] or 0) != 1
                or str(reconciled_review["source_review_input_sha256"])
                != str(day_review["input_sha256"])
            ):
                raise ValueError(
                    "publication finalization requires the reconciled honest, unpadded thin day"
                )
            reconciled_review_ids = _review_selected_ids(
                reconciled_review, label="reconciled day review"
            )
            if len(reconciled_review_ids) != len(base_ids) or set(
                reconciled_review_ids
            ) != set(base_ids):
                raise ValueError(
                    "reconciled day review no longer matches the active selection"
                )
            reconciliation_sha256 = _row_sha256(reconciliation)
            reconciled_review_sha256 = _row_sha256(reconciled_review)
        else:
            raise ValueError(
                "publication finalization requires a direct set or exact padding-tail trim"
            )

        selected_audit = audit.execute(
            "SELECT * FROM audit_item WHERE sample_kind = 'selected'"
        ).fetchall()
        if len(selected_audit) != len(base_ids):
            raise ValueError(
                "publication finalization audit does not cover the active selection"
            )
        selected_by_id = {
            str(row["source_candidate_id"]): row for row in selected_audit
        }
        if set(selected_by_id) != set(base_ids) or any(
            str(row["status"]) != "complete" for row in selected_audit
        ):
            raise ValueError("publication audit items do not match the active selection")
        failed_dimensions: dict[str, list[str]] = {}
        for candidate_id in base_ids:
            selected_audit_row = selected_by_id[candidate_id]
            dimensions = [
                field
                for field in JUDGMENT_FIELDS
                if str(selected_audit_row[field]) == "fail"
            ]
            if int(selected_audit_row["mechanical_citation_valid"]) != 1:
                dimensions.insert(0, "mechanical_citation_valid")
            if dimensions:
                failed_dimensions[candidate_id] = dimensions
        removed_ids = [
            candidate_id for candidate_id in base_ids if candidate_id in failed_dimensions
        ]
        effective_ids = [
            candidate_id for candidate_id in base_ids if candidate_id not in failed_dimensions
        ]
        if not removed_ids or bool(audit_report["passed"]):
            raise ValueError(
                "publication finalization requires an externally failed selected item"
            )
        if int(audit_report["selected_metrics"]["total"]) != len(base_ids):
            raise ValueError("failed publication audit selected count does not match")

        adjudication = audit_report["false_negative_adjudication"]
        return {
            "schema_version": FINALIZATION_SCHEMA_VERSION,
            "reason_code": FINALIZATION_REASON_CODE,
            "source_run_db": str(source_path),
            "source_run_id": str(run["run_id"]),
            "audience": str(run["audience"]),
            "day": str(run["day"]),
            "source_gate_sha256": _row_sha256(gate),
            "source_day_review_sha256": _row_sha256(day_review),
            "source_padding_reconciliation_sha256": reconciliation_sha256,
            "source_reconciled_day_review_sha256": reconciled_review_sha256,
            "source_editor_selection_sha256": _sha256(
                _canonical_json([dict(row) for row in daily_selection])
            ),
            "base_selection_sha256": _sha256(
                _canonical_json([dict(row) for row in base_selection])
            ),
            "base_selected_ids": base_ids,
            "removed_candidate_ids": removed_ids,
            "effective_selected_ids": effective_ids,
            "failed_dimensions": failed_dimensions,
            "audit_db": str(audit_path),
            "audit_id": str(audit_report["audit_id"]),
            "audit_cohort_sha256": str(audit_report["audit_cohort_sha256"]),
            "audit_result_sha256": str(audit_report["audit_result_sha256"]),
            "source_contract_sha256": str(audit_report["source_contract_sha256"]),
            "false_negative_adjudication_sha256": adjudication.get("sha256"),
        }
    finally:
        audit.close()
        source.close()


def create_publication_finalization(
    *,
    source_run_db: Path | str,
    audit_db: Path | str,
    finalization_path: Path | str | None = None,
) -> dict[str, Any]:
    """Write one immutable sidecar that removes exact audit-failed items.

    A passing audit is an explicit no-op. A failing audit may remove only exact
    audit-failed selected IDs from either a directly reviewed publication set
    or an already-reviewed padding-tail-trim chain; no candidate can be
    supplied, substituted, reordered, or promoted by the caller.
    """
    source_path = Path(source_run_db).resolve()
    audit_path = Path(audit_db).resolve()
    path = Path(finalization_path or default_finalization_path(source_path)).resolve()
    if path.exists():
        raise ValueError("publication finalization already exists for this run")
    source = _open_readonly(source_path)
    try:
        base_ids = [
            str(row[0])
            for row in source.execute(
                "SELECT candidate_id FROM publication_selection "
                "ORDER BY publication_rank"
            ).fetchall()
        ]
    finally:
        source.close()
    if not base_ids:
        raise ValueError("publication finalization requires an active item")
    audit_report = _validate_readonly_publication_audit(
        source_run_db=source_path,
        audit_db=audit_path,
        expected_selected_count=len(base_ids),
        require_passed=False,
    )
    if bool(audit_report["passed"]):
        return {
            "created": False,
            "reason_code": "publication_audit_passed",
            "path": str(path),
            "effective_selected_ids": base_ids,
        }
    evidence = _finalization_evidence(
        source_path=source_path,
        audit_path=audit_path,
        audit_report=audit_report,
    )
    payload = {**evidence, "created_at": _now()}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write(_canonical_json(payload) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "created": True,
        "reason_code": FINALIZATION_REASON_CODE,
        "path": str(path),
        "effective_selected_ids": list(evidence["effective_selected_ids"]),
        "finalization_sha256": _sha256(path.read_text()),
    }


def _normalize_editorial_review(
    review: Mapping[str, Any], *, base_ids: list[str]
) -> dict[str, Any]:
    """Validate and canonically order one human-owned release decision."""
    expected_fields = {"schema_version", "review_id", "reviewer", "removals"}
    if not isinstance(review, Mapping) or set(review) != expected_fields:
        raise ValueError("editorial review has an invalid schema")
    if review["schema_version"] != EDITORIAL_REVIEW_SCHEMA_VERSION:
        raise ValueError("editorial review has an unsupported schema version")
    review_id = review["review_id"]
    reviewer = review["reviewer"]
    if not isinstance(review_id, str) or not review_id.strip():
        raise ValueError("editorial review requires review_id")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("editorial review requires reviewer")
    removals = review["removals"]
    if not isinstance(removals, list) or not removals:
        raise ValueError("editorial review requires at least one removal")
    by_id: dict[str, dict[str, str]] = {}
    for removal in removals:
        if not isinstance(removal, Mapping) or set(removal) != {
            "candidate_id",
            "reason_code",
            "rationale",
        }:
            raise ValueError("editorial review removal is malformed")
        candidate_id = removal["candidate_id"]
        reason_code = removal["reason_code"]
        rationale = removal["rationale"]
        if not isinstance(candidate_id, str) or not candidate_id:
            raise ValueError("editorial review removal requires candidate_id")
        if candidate_id in by_id:
            raise ValueError("editorial review removal IDs must be unique")
        if candidate_id not in base_ids:
            raise ValueError(
                "editorial review may remove only an active selected candidate"
            )
        if reason_code not in EDITORIAL_REMOVAL_REASON_CODES:
            raise ValueError("editorial review removal has an invalid reason_code")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError("editorial review removal requires a rationale")
        by_id[candidate_id] = {
            "candidate_id": candidate_id,
            "reason_code": str(reason_code),
            "rationale": rationale.strip(),
        }
    return {
        "schema_version": EDITORIAL_REVIEW_SCHEMA_VERSION,
        "review_id": review_id.strip(),
        "reviewer": reviewer.strip(),
        "removals": [by_id[candidate_id] for candidate_id in base_ids if candidate_id in by_id],
    }


def _editorial_finalization_evidence(
    *,
    source_path: Path,
    audit_path: Path,
    audit_report: Mapping[str, Any],
    editorial_review: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind a stricter editorial removal to an exact passing publication set."""
    if not bool(audit_report["passed"]):
        raise ValueError(
            "senior editorial finalization requires the independent audit to pass"
        )
    source = _open_readonly(source_path)
    try:
        run = _required_singleton(source, "run_meta")
        gate = _required_singleton(source, "quality_gate")
        base_selection = source.execute(
            "SELECT * FROM publication_selection ORDER BY publication_rank"
        ).fetchall()
        daily_selection = source.execute(
            "SELECT * FROM daily_selection ORDER BY editorial_rank"
        ).fetchall()
        if not base_selection:
            raise ValueError("senior editorial finalization requires an active item")
        base_ids = [str(row["candidate_id"]) for row in base_selection]
        if [int(row["publication_rank"]) for row in base_selection] != list(
            range(1, len(base_selection) + 1)
        ):
            raise ValueError(
                "senior editorial finalization requires contiguous publication ranks"
            )
        review = _normalize_editorial_review(editorial_review, base_ids=base_ids)
        removed_ids = [item["candidate_id"] for item in review["removals"]]
        effective_ids = [
            candidate_id for candidate_id in base_ids if candidate_id not in removed_ids
        ]
        adjudication = audit_report["false_negative_adjudication"]
        return {
            "schema_version": EDITORIAL_FINALIZATION_SCHEMA_VERSION,
            "reason_code": EDITORIAL_FINALIZATION_REASON_CODE,
            "source_run_db": str(source_path),
            "source_run_id": str(run["run_id"]),
            "audience": str(run["audience"]),
            "day": str(run["day"]),
            "source_gate_sha256": _row_sha256(gate),
            "source_editor_selection_sha256": _sha256(
                _canonical_json([dict(row) for row in daily_selection])
            ),
            "base_selection_sha256": _sha256(
                _canonical_json([dict(row) for row in base_selection])
            ),
            "base_selected_ids": base_ids,
            "removed_candidate_ids": removed_ids,
            "effective_selected_ids": effective_ids,
            "editorial_review": review,
            "editorial_review_sha256": _sha256(_canonical_json(review)),
            "audit_db": str(audit_path),
            "audit_id": str(audit_report["audit_id"]),
            "audit_cohort_sha256": str(audit_report["audit_cohort_sha256"]),
            "audit_result_sha256": str(audit_report["audit_result_sha256"]),
            "source_contract_sha256": str(audit_report["source_contract_sha256"]),
            "false_negative_adjudication_sha256": adjudication.get("sha256"),
        }
    finally:
        source.close()


def _composed_editorial_finalization_evidence(
    *,
    source_path: Path,
    audit_path: Path,
    prerequisite_path: Path,
    prerequisite: Mapping[str, Any],
    editorial_review: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind an editorial veto after an immutable audit-disqualification layer."""
    if prerequisite.get("reason_code") != FINALIZATION_REASON_CODE:
        raise ValueError(
            "composed editorial finalization requires an audit-disqualification prerequisite"
        )
    expected_prerequisite = default_finalization_path(source_path).resolve()
    if prerequisite_path.resolve() != expected_prerequisite:
        raise ValueError(
            "composed editorial finalization prerequisite is not the adjacent audit layer"
        )
    post_audit_ids = [
        str(value) for value in prerequisite["effective_selected_ids"]
    ]
    base_ids = [str(value) for value in prerequisite["base_selected_ids"]]
    if not post_audit_ids:
        raise ValueError(
            "composed editorial finalization requires a remaining audit-cleared item"
        )
    review = _normalize_editorial_review(
        editorial_review,
        base_ids=post_audit_ids,
    )
    removed_ids = [item["candidate_id"] for item in review["removals"]]
    effective_ids = [
        candidate_id
        for candidate_id in post_audit_ids
        if candidate_id not in removed_ids
    ]
    audit_report = prerequisite["audit"]
    source = _open_readonly(source_path)
    try:
        run = _required_singleton(source, "run_meta")
    finally:
        source.close()
    adjudication = audit_report["false_negative_adjudication"]
    return {
        "schema_version": COMPOSED_EDITORIAL_FINALIZATION_SCHEMA_VERSION,
        "reason_code": EDITORIAL_FINALIZATION_REASON_CODE,
        "source_run_db": str(source_path),
        "source_run_id": str(run["run_id"]),
        "audience": str(run["audience"]),
        "day": str(run["day"]),
        "audit_db": str(audit_path),
        "audit_id": str(audit_report["audit_id"]),
        "audit_cohort_sha256": str(audit_report["audit_cohort_sha256"]),
        "audit_result_sha256": str(audit_report["audit_result_sha256"]),
        "source_contract_sha256": str(audit_report["source_contract_sha256"]),
        "false_negative_adjudication_sha256": adjudication.get("sha256"),
        "prerequisite_finalization_path": str(prerequisite_path),
        "prerequisite_finalization_sha256": str(
            prerequisite["finalization_sha256"]
        ),
        "prerequisite_reason_code": str(prerequisite["reason_code"]),
        "prerequisite_effective_selected_ids": post_audit_ids,
        "base_selected_ids": base_ids,
        "post_audit_selected_ids": post_audit_ids,
        "removed_candidate_ids": removed_ids,
        "effective_selected_ids": effective_ids,
        # Audit-disqualified candidates never enter history. Editorially vetoed
        # audit survivors do, so later editors cannot rediscover the framing.
        "history_selected_ids": post_audit_ids,
        "editorial_review": review,
        "editorial_review_sha256": _sha256(_canonical_json(review)),
    }


def create_editorial_publication_finalization(
    *,
    source_run_db: Path | str,
    audit_db: Path | str,
    editorial_review: Mapping[str, Any],
    finalization_path: Path | str | None = None,
) -> dict[str, Any]:
    """Write one immutable, source-bound senior editorial release decision.

    This is a stricter gate after the independent publication audit. It may
    remove exact active selected IDs, but cannot alter the audit or source run,
    promote a rejected candidate, substitute an item, or reorder survivors.
    """
    source_path = Path(source_run_db).resolve()
    audit_path = Path(audit_db).resolve()
    prerequisite_path = default_finalization_path(source_path).resolve()
    if prerequisite_path.is_file():
        prerequisite = validate_readonly_publication_finalization(
            source_run_db=source_path,
            audit_db=audit_path,
            finalization_path=prerequisite_path,
        )
        if prerequisite["reason_code"] != FINALIZATION_REASON_CODE:
            raise ValueError(
                "composed editorial finalization prerequisite must be an "
                "audit-disqualification finalization"
            )
        path = Path(
            finalization_path or default_editorial_finalization_path(source_path)
        ).resolve()
        if path != default_editorial_finalization_path(source_path).resolve():
            raise ValueError(
                "composed editorial finalization must use the adjacent editorial layer"
            )
        if path.exists():
            raise ValueError("editorial finalization already exists for this run")
        evidence = _composed_editorial_finalization_evidence(
            source_path=source_path,
            audit_path=audit_path,
            prerequisite_path=prerequisite_path,
            prerequisite=prerequisite,
            editorial_review=editorial_review,
        )
        payload = {**evidence, "created_at": _now()}
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            with temporary.open("x", encoding="utf-8") as handle:
                handle.write(_canonical_json(payload) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        return {
            "created": True,
            "reason_code": EDITORIAL_FINALIZATION_REASON_CODE,
            "path": str(path),
            "prerequisite_finalization_path": str(prerequisite_path),
            "prerequisite_finalization_sha256": prerequisite[
                "finalization_sha256"
            ],
            "effective_selected_ids": list(evidence["effective_selected_ids"]),
            "history_selected_ids": list(evidence["history_selected_ids"]),
            "finalization_sha256": _sha256(path.read_text()),
        }

    path = Path(finalization_path or prerequisite_path).resolve()
    if path.exists():
        raise ValueError("publication finalization already exists for this run")
    source = _open_readonly(source_path)
    try:
        base_ids = [
            str(row[0])
            for row in source.execute(
                "SELECT candidate_id FROM publication_selection "
                "ORDER BY publication_rank"
            ).fetchall()
        ]
    finally:
        source.close()
    audit_report = validate_readonly_publication_audit(
        source_run_db=source_path,
        audit_db=audit_path,
        expected_selected_count=len(base_ids),
    )
    evidence = _editorial_finalization_evidence(
        source_path=source_path,
        audit_path=audit_path,
        audit_report=audit_report,
        editorial_review=editorial_review,
    )
    payload = {**evidence, "created_at": _now()}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write(_canonical_json(payload) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "created": True,
        "reason_code": EDITORIAL_FINALIZATION_REASON_CODE,
        "path": str(path),
        "effective_selected_ids": list(evidence["effective_selected_ids"]),
        "finalization_sha256": _sha256(path.read_text()),
    }


def _validate_readonly_editorial_publication_finalization(
    *,
    source_path: Path,
    audit_path: Path,
    path: Path,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    expected_fields = {
        "schema_version",
        "reason_code",
        "source_run_db",
        "source_run_id",
        "audience",
        "day",
        "source_gate_sha256",
        "source_editor_selection_sha256",
        "base_selection_sha256",
        "base_selected_ids",
        "removed_candidate_ids",
        "effective_selected_ids",
        "editorial_review",
        "editorial_review_sha256",
        "audit_db",
        "audit_id",
        "audit_cohort_sha256",
        "audit_result_sha256",
        "source_contract_sha256",
        "false_negative_adjudication_sha256",
        "created_at",
    }
    if set(payload) != expected_fields:
        raise ValueError("publication finalization has an invalid schema")
    if not isinstance(payload["created_at"], str) or not payload["created_at"].strip():
        raise ValueError("publication finalization requires created_at")
    source = _open_readonly(source_path)
    try:
        base_ids = [
            str(row[0])
            for row in source.execute(
                "SELECT candidate_id FROM publication_selection "
                "ORDER BY publication_rank"
            ).fetchall()
        ]
    finally:
        source.close()
    audit_report = validate_readonly_publication_audit(
        source_run_db=source_path,
        audit_db=audit_path,
        expected_selected_count=len(base_ids),
    )
    expected = _editorial_finalization_evidence(
        source_path=source_path,
        audit_path=audit_path,
        audit_report=audit_report,
        editorial_review=payload["editorial_review"],
    )
    mismatches = [field for field, value in expected.items() if payload[field] != value]
    if mismatches:
        raise ValueError(
            "publication finalization no longer matches its evidence: "
            + ", ".join(mismatches)
        )
    return {
        "passed": True,
        "reason_code": EDITORIAL_FINALIZATION_REASON_CODE,
        "path": str(path),
        "finalization_sha256": _sha256(path.read_text()),
        "base_selected_ids": list(payload["base_selected_ids"]),
        "post_audit_selected_ids": list(payload["base_selected_ids"]),
        "removed_candidate_ids": list(payload["removed_candidate_ids"]),
        "effective_selected_ids": list(payload["effective_selected_ids"]),
        "history_selected_ids": list(payload["base_selected_ids"]),
        "failed_dimensions": {},
        "editorial_review": dict(payload["editorial_review"]),
        "audit": audit_report,
    }


def _validate_readonly_composed_editorial_publication_finalization(
    *,
    source_path: Path,
    audit_path: Path,
    path: Path,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    expected_fields = {
        "schema_version",
        "reason_code",
        "source_run_db",
        "source_run_id",
        "audience",
        "day",
        "audit_db",
        "audit_id",
        "audit_cohort_sha256",
        "audit_result_sha256",
        "source_contract_sha256",
        "false_negative_adjudication_sha256",
        "prerequisite_finalization_path",
        "prerequisite_finalization_sha256",
        "prerequisite_reason_code",
        "prerequisite_effective_selected_ids",
        "base_selected_ids",
        "post_audit_selected_ids",
        "removed_candidate_ids",
        "effective_selected_ids",
        "history_selected_ids",
        "editorial_review",
        "editorial_review_sha256",
        "created_at",
    }
    if set(payload) != expected_fields:
        raise ValueError("publication finalization has an invalid schema")
    if not isinstance(payload["created_at"], str) or not payload["created_at"].strip():
        raise ValueError("publication finalization requires created_at")
    expected_path = default_editorial_finalization_path(source_path).resolve()
    if path.resolve() != expected_path:
        raise ValueError(
            "composed editorial finalization is not the adjacent terminal layer"
        )
    prerequisite_path = default_finalization_path(source_path).resolve()
    stored_prerequisite_path = Path(
        str(payload["prerequisite_finalization_path"])
    ).resolve()
    if stored_prerequisite_path != prerequisite_path:
        raise ValueError("editorial prerequisite finalization path drift")
    prerequisite = validate_readonly_publication_finalization(
        source_run_db=source_path,
        audit_db=audit_path,
        finalization_path=prerequisite_path,
    )
    if prerequisite["reason_code"] != FINALIZATION_REASON_CODE:
        raise ValueError(
            "composed editorial finalization prerequisite must be an "
            "audit-disqualification finalization"
        )
    expected = _composed_editorial_finalization_evidence(
        source_path=source_path,
        audit_path=audit_path,
        prerequisite_path=prerequisite_path,
        prerequisite=prerequisite,
        editorial_review=payload["editorial_review"],
    )
    mismatches = [field for field, value in expected.items() if payload[field] != value]
    if mismatches:
        raise ValueError(
            "publication finalization no longer matches its evidence: "
            + ", ".join(mismatches)
        )
    return {
        "passed": True,
        "reason_code": EDITORIAL_FINALIZATION_REASON_CODE,
        "path": str(path),
        "finalization_sha256": _sha256(path.read_text()),
        "base_selected_ids": list(payload["base_selected_ids"]),
        "post_audit_selected_ids": list(payload["post_audit_selected_ids"]),
        "removed_candidate_ids": list(payload["removed_candidate_ids"]),
        "effective_selected_ids": list(payload["effective_selected_ids"]),
        "history_selected_ids": list(payload["history_selected_ids"]),
        "failed_dimensions": {},
        "editorial_review": dict(payload["editorial_review"]),
        "prerequisite_finalization": prerequisite,
        "audit": prerequisite["audit"],
    }


def validate_readonly_publication_finalization(
    *,
    source_run_db: Path | str,
    audit_db: Path | str,
    finalization_path: Path | str | None = None,
) -> dict[str, Any]:
    """Recompute every sidecar binding and return the effective selected set."""
    source_path = Path(source_run_db).resolve()
    audit_path = Path(audit_db).resolve()
    path = Path(finalization_path or terminal_finalization_path(source_path)).resolve()
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError("publication finalization has an invalid schema")
    if payload.get("schema_version") == EDITORIAL_FINALIZATION_SCHEMA_VERSION:
        return _validate_readonly_editorial_publication_finalization(
            source_path=source_path,
            audit_path=audit_path,
            path=path,
            payload=payload,
        )
    if payload.get("schema_version") == COMPOSED_EDITORIAL_FINALIZATION_SCHEMA_VERSION:
        return _validate_readonly_composed_editorial_publication_finalization(
            source_path=source_path,
            audit_path=audit_path,
            path=path,
            payload=payload,
        )
    expected_fields = {
        "schema_version",
        "reason_code",
        "source_run_db",
        "source_run_id",
        "audience",
        "day",
        "source_gate_sha256",
        "source_day_review_sha256",
        "source_padding_reconciliation_sha256",
        "source_reconciled_day_review_sha256",
        "source_editor_selection_sha256",
        "base_selection_sha256",
        "base_selected_ids",
        "removed_candidate_ids",
        "effective_selected_ids",
        "failed_dimensions",
        "audit_db",
        "audit_id",
        "audit_cohort_sha256",
        "audit_result_sha256",
        "source_contract_sha256",
        "false_negative_adjudication_sha256",
        "created_at",
    }
    if not isinstance(payload, dict) or set(payload) != expected_fields:
        raise ValueError("publication finalization has an invalid schema")
    if not isinstance(payload["created_at"], str) or not payload["created_at"].strip():
        raise ValueError("publication finalization requires created_at")
    source = _open_readonly(source_path)
    try:
        base_ids = [
            str(row[0])
            for row in source.execute(
                "SELECT candidate_id FROM publication_selection "
                "ORDER BY publication_rank"
            ).fetchall()
        ]
    finally:
        source.close()
    audit_report = _validate_readonly_publication_audit(
        source_run_db=source_path,
        audit_db=audit_path,
        expected_selected_count=len(base_ids),
        require_passed=False,
    )
    expected = _finalization_evidence(
        source_path=source_path,
        audit_path=audit_path,
        audit_report=audit_report,
    )
    mismatches = [field for field, value in expected.items() if payload[field] != value]
    if mismatches:
        raise ValueError(
            "publication finalization no longer matches its evidence: "
            + ", ".join(mismatches)
        )
    return {
        "passed": True,
        "reason_code": FINALIZATION_REASON_CODE,
        "path": str(path),
        "finalization_sha256": _sha256(path.read_text()),
        "base_selected_ids": list(payload["base_selected_ids"]),
        "post_audit_selected_ids": list(payload["effective_selected_ids"]),
        "removed_candidate_ids": list(payload["removed_candidate_ids"]),
        "effective_selected_ids": list(payload["effective_selected_ids"]),
        "history_selected_ids": list(payload["effective_selected_ids"]),
        "failed_dimensions": dict(payload["failed_dimensions"]),
        "audit": audit_report,
    }


def validated_publication_projection(
    *,
    source_run_db: Path | str,
    audit_db: Path | str,
    finalization_path: Path | str | None = None,
) -> dict[str, Any]:
    """Return the only publishable ID projection, validating all provenance."""
    source_path = Path(source_run_db).resolve()
    audit_path = Path(audit_db).resolve()
    path = Path(finalization_path or terminal_finalization_path(source_path)).resolve()
    source = _open_readonly(source_path)
    try:
        base_ids = [
            str(row[0])
            for row in source.execute(
                "SELECT candidate_id FROM publication_selection ORDER BY publication_rank"
            ).fetchall()
        ]
    finally:
        source.close()
    if finalization_path is not None and not path.is_file():
        raise FileNotFoundError(path)
    if path.is_file():
        finalization = validate_readonly_publication_finalization(
            source_run_db=source_path,
            audit_db=audit_path,
            finalization_path=path,
        )
        if finalization["base_selected_ids"] != base_ids:
            raise ValueError("publication finalization base selection is stale")
        editorial = finalization["reason_code"] == EDITORIAL_FINALIZATION_REASON_CODE
        composed = "prerequisite_finalization" in finalization
        return {
            "mode": (
                "audit_then_editorial_disqualified_zero"
                if composed and not finalization["effective_selected_ids"]
                else "audit_then_editorial_disqualified_trim"
                if composed
                else "editorial_disqualified_zero"
                if editorial and not finalization["effective_selected_ids"]
                else "editorial_disqualified_trim"
                if editorial
                else "audit_disqualified_zero"
                if not finalization["effective_selected_ids"]
                else "audit_disqualified_trim"
            ),
            "base_selected_ids": base_ids,
            "post_audit_selected_ids": list(
                finalization["post_audit_selected_ids"]
            ),
            "effective_selected_ids": list(
                finalization["effective_selected_ids"]
            ),
            "history_selected_ids": list(finalization["history_selected_ids"]),
            "selected_count": len(finalization["effective_selected_ids"]),
            "audit": finalization["audit"],
            "finalization": finalization,
        }
    audit_report = validate_readonly_publication_audit(
        source_run_db=source_path,
        audit_db=audit_path,
        expected_selected_count=len(base_ids),
    )
    return {
        "mode": "audit_pass",
        "base_selected_ids": base_ids,
        "post_audit_selected_ids": base_ids,
        "effective_selected_ids": base_ids,
        "history_selected_ids": base_ids,
        "selected_count": len(base_ids),
        "audit": audit_report,
        "finalization": None,
    }


def _result(command: str, data: Any) -> dict[str, Any]:
    return {"schema_version": "1.0", "command": command, "status": "ok", "data": data, "error": None}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fli audience-insight-audit")
    sub = parser.add_subparsers(dest="action", required=True)
    freeze = sub.add_parser("freeze", help="Freeze a blinded audit cohort from one audience run.")
    freeze.add_argument("--audit-id", required=True)
    freeze.add_argument("--audit-db", type=Path)
    freeze.add_argument("--source-run-db", type=Path, required=True)
    freeze.add_argument("--reject-sample-limit", type=int, default=DEFAULT_REJECT_SAMPLE_LIMIT)
    freeze.add_argument("--model", default=DEFAULT_MODEL)
    freeze.add_argument("--reasoning-effort", default=DEFAULT_REASONING_EFFORT)
    run = sub.add_parser("run", help="Run or resume the independent auditor.")
    run.add_argument("--audit-db", type=Path, required=True)
    run.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    run.add_argument("--retry-failed", action="store_true")
    report = sub.add_parser("summary", help="Report independent publication-audit metrics.")
    report.add_argument("--audit-db", type=Path, required=True)
    validate = sub.add_parser(
        "validate",
        help=(
            "Fail closed unless an adjacent audit and every required "
            "false-negative adjudication exactly match the source run."
        ),
    )
    validate.add_argument("--audit-db", type=Path, required=True)
    validate.add_argument("--source-run-db", type=Path, required=True)
    validate.add_argument("--expected-selected-count", type=int, required=True)
    finalize = sub.add_parser(
        "finalize",
        help="Write an immutable sidecar removing exact audit-failed selected items.",
    )
    finalize.add_argument("--audit-db", type=Path, required=True)
    finalize.add_argument("--source-run-db", type=Path, required=True)
    finalize.add_argument("--finalization-path", type=Path)
    finalize_editorial = sub.add_parser(
        "finalize-editorial",
        help=(
            "Write an immutable stricter editorial release decision after a "
            "passing independent audit."
        ),
    )
    finalize_editorial.add_argument("--audit-db", type=Path, required=True)
    finalize_editorial.add_argument("--source-run-db", type=Path, required=True)
    finalize_editorial.add_argument("--editorial-review", type=Path, required=True)
    finalize_editorial.add_argument("--finalization-path", type=Path)
    validate_finalization = sub.add_parser(
        "validate-finalization",
        help="Fail closed unless a finalization exactly matches source and audit evidence.",
    )
    validate_finalization.add_argument("--audit-db", type=Path, required=True)
    validate_finalization.add_argument("--source-run-db", type=Path, required=True)
    validate_finalization.add_argument("--finalization-path", type=Path)
    args = parser.parse_args(argv)
    started = time.monotonic()
    command = f"audience-insight-audit.{args.action}"
    conn: sqlite3.Connection | None = None
    try:
        if args.action == "freeze":
            audit_db = args.audit_db or default_audit_db(audit_id=args.audit_id)
            conn = connect(audit_db)
            freeze_audit(
                conn,
                audit_id=args.audit_id,
                source_run_db=args.source_run_db,
                reject_sample_limit=args.reject_sample_limit,
                model=args.model,
                reasoning_effort=args.reasoning_effort,
            )
            data = summary(conn)
            data["audit_db"] = str(audit_db.resolve())
            data["will_call_model"] = False
        elif args.action == "summary":
            conn = connect(args.audit_db)
            data = summary(conn)
        elif args.action == "validate":
            data = validate_readonly_publication_audit(
                source_run_db=args.source_run_db,
                audit_db=args.audit_db,
                expected_selected_count=args.expected_selected_count,
            )
        elif args.action == "finalize":
            data = create_publication_finalization(
                source_run_db=args.source_run_db,
                audit_db=args.audit_db,
                finalization_path=args.finalization_path,
            )
        elif args.action == "finalize-editorial":
            editorial_review = json.loads(args.editorial_review.read_text())
            data = create_editorial_publication_finalization(
                source_run_db=args.source_run_db,
                audit_db=args.audit_db,
                editorial_review=editorial_review,
                finalization_path=args.finalization_path,
            )
        elif args.action == "validate-finalization":
            data = validate_readonly_publication_finalization(
                source_run_db=args.source_run_db,
                audit_db=args.audit_db,
                finalization_path=args.finalization_path,
            )
        else:
            conn = connect(args.audit_db)
            client = entity_kinds.create_litellm_client()
            if hasattr(client, "with_options"):
                client = client.with_options(max_retries=0, timeout=300.0)
            data = run_pending(
                conn,
                client=client,
                workers=args.workers,
                retry_failed=args.retry_failed,
            )
    except (FileNotFoundError, json.JSONDecodeError, sqlite3.Error, ValueError) as exc:
        print(_canonical_json({"schema_version": "1.0", "command": command, "status": "error", "data": None, "error": {"code": "E_INVALID_INPUT", "message": str(exc)}}))
        return 2
    finally:
        if conn is not None:
            conn.close()
    data["duration_ms"] = round((time.monotonic() - started) * 1000)
    print(_canonical_json(_result(command, data)))
    if args.action == "run" and not data["passed"]:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
