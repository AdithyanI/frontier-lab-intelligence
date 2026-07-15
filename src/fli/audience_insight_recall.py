"""Deterministic recall audit for the Audience Insights v2 cutoff.

The recall store is deliberately separate from the publication run store.  It
freezes the predeclared lower-rank and dropped samples, renders the same
rank-blind evidence packet used by the audience extractors, and preserves
independent extraction, item-review, and final-set adjudication fields.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import sqlite3
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from fli import (
    audience_insight_evaluations,
    audience_insight_runs,
    audience_insights,
    entity_kinds,
)


PROTOCOL_VERSION = "audience-insights-v2-recall-v1"
ADJUDICATION_SCHEMA_VERSION = "audience-insights-v2-recall-adjudication-v1"
DAYS = tuple(f"2026-07-{day:02d}" for day in range(5, 14))
AUDIENCES = (audience_insights.INVESTMENT, audience_insights.AI_ENGINEERING)
DEFAULT_ARTIFACT_DB = audience_insight_runs.DEFAULT_ARTIFACT_DB
DEFAULT_MODEL = audience_insights.DEFAULT_MODEL
DEFAULT_EXTRACTION_EFFORT = audience_insights.DEFAULT_EXTRACTION_EFFORT
DEFAULT_REVIEW_MODEL = audience_insight_evaluations.DEFAULT_MODEL
DEFAULT_REVIEW_EFFORT = audience_insight_evaluations.DEFAULT_REASONING_EFFORT
DEFAULT_WORKERS = 12
MAX_DETERMINISTIC_FAILURE_ATTEMPTS = 2

KEPT_51_75 = "kept-51-75"
KEPT_76_100 = "kept-76-100"
X_ARTICLE_51_100 = "kept-x-article-51-100"
DROPPED_1_25 = "dropped-1-25"
DROPPED_26_50 = "dropped-26-50"
DROPPED_51_100 = "dropped-51-100"

QUOTA_BANDS = (
    (KEPT_51_75, "keep", 51, 75, 2, "lower_kept"),
    (KEPT_76_100, "keep", 76, 100, 2, "lower_kept"),
)
DROP_BANDS = (
    (DROPPED_1_25, "drop", 1, 25, 1, "dropped"),
    (DROPPED_26_50, "drop", 26, 50, 1, "dropped"),
    (DROPPED_51_100, "drop", 51, 100, 1, "dropped"),
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS recall_run (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    run_id TEXT NOT NULL,
    protocol_version TEXT NOT NULL,
    days_json TEXT NOT NULL,
    source_triage_dbs_json TEXT NOT NULL,
    source_artifact_db TEXT NOT NULL,
    extraction_model TEXT NOT NULL,
    extraction_reasoning_effort TEXT NOT NULL,
    review_model TEXT NOT NULL,
    review_reasoning_effort TEXT NOT NULL,
    contract_sha256 TEXT NOT NULL,
    sample_set_sha256 TEXT NOT NULL,
    expected_sample_count INTEGER NOT NULL,
    expected_evaluation_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recall_sample (
    sample_id TEXT PRIMARY KEY,
    selection_order INTEGER NOT NULL UNIQUE,
    day TEXT NOT NULL,
    event_id TEXT NOT NULL UNIQUE,
    band TEXT NOT NULL,
    sample_kind TEXT NOT NULL CHECK (
        sample_kind IN ('lower_kept', 'x_article_census', 'dropped')
    ),
    triage_decision TEXT NOT NULL CHECK (triage_decision IN ('keep', 'drop')),
    feed_rank INTEGER NOT NULL,
    selection_sha256 TEXT NOT NULL,
    article_artifact_ids_json TEXT NOT NULL,
    packet_json TEXT NOT NULL,
    evidence_sha256 TEXT NOT NULL,
    extraction_input_text TEXT NOT NULL,
    extraction_input_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_recall_sample_day_band
    ON recall_sample(day, band, selection_order);

CREATE TABLE IF NOT EXISTS recall_replacement (
    replacement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL,
    band TEXT NOT NULL,
    skipped_event_id TEXT NOT NULL,
    skipped_selection_sha256 TEXT NOT NULL,
    replacement_event_id TEXT,
    reason TEXT NOT NULL CHECK (
        reason IN ('repeated_event', 'article_event_already_selected')
    )
);

CREATE TABLE IF NOT EXISTS recall_audience_evaluation (
    sample_id TEXT NOT NULL REFERENCES recall_sample(sample_id)
        ON DELETE RESTRICT,
    audience TEXT NOT NULL CHECK (audience IN ('investment', 'ai_engineering')),
    candidate_id TEXT NOT NULL UNIQUE,
    extraction_input_text TEXT NOT NULL,
    extraction_input_sha256 TEXT NOT NULL,
    extraction_prompt_version TEXT NOT NULL,
    extraction_prompt_sha256 TEXT NOT NULL,
    extraction_schema_version TEXT NOT NULL,
    extraction_prompt_cache_key TEXT NOT NULL,
    extraction_status TEXT NOT NULL DEFAULT 'pending' CHECK (
        extraction_status IN ('pending', 'complete', 'failed', 'rejected')
    ),
    extraction_attempts INTEGER NOT NULL DEFAULT 0,
    outcome TEXT CHECK (
        outcome IS NULL OR outcome IN ('insight', 'no_extractable_insight')
    ),
    no_insight INTEGER NOT NULL DEFAULT 0 CHECK (no_insight IN (0, 1)),
    no_insight_reason TEXT,
    citation_valid INTEGER CHECK (citation_valid IN (0, 1)),
    citation_failure_attempts INTEGER NOT NULL DEFAULT 0,
    citation_terminal_failure INTEGER NOT NULL DEFAULT 0 CHECK (
        citation_terminal_failure IN (0, 1)
    ),
    schema_failure_attempts INTEGER NOT NULL DEFAULT 0,
    schema_terminal_failure INTEGER NOT NULL DEFAULT 0 CHECK (
        schema_terminal_failure IN (0, 1)
    ),
    extraction_result_json TEXT,
    extraction_raw_output_text TEXT,
    extraction_error_type TEXT,
    extraction_error_message TEXT,
    extraction_completed_at TEXT,
    review_status TEXT NOT NULL DEFAULT 'pending' CHECK (
        review_status IN ('pending', 'not_applicable', 'complete', 'failed')
    ),
    review_attempts INTEGER NOT NULL DEFAULT 0,
    review_input_text TEXT,
    review_input_sha256 TEXT,
    review_prompt_cache_key TEXT,
    claim_fidelity INTEGER CHECK (claim_fidelity IN (0, 1)),
    epistemic_discipline INTEGER CHECK (epistemic_discipline IN (0, 1)),
    audience_useful INTEGER CHECK (audience_useful IN (0, 1)),
    actionable INTEGER CHECK (actionable IN (0, 1)),
    specific INTEGER CHECK (specific IN (0, 1)),
    review_failure_codes_json TEXT,
    review_rationale TEXT,
    review_result_json TEXT,
    review_raw_output_text TEXT,
    review_error_type TEXT,
    review_error_message TEXT,
    review_completed_at TEXT,
    redundant INTEGER CHECK (redundant IN (0, 1)),
    final_set_worthy INTEGER CHECK (final_set_worthy IN (0, 1)),
    high_consequence INTEGER CHECK (high_consequence IN (0, 1)),
    adjudication_comparison_json TEXT,
    adjudication_note TEXT,
    adjudicated_at TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (sample_id, audience)
);
CREATE INDEX IF NOT EXISTS idx_recall_evaluation_extraction
    ON recall_audience_evaluation(
        extraction_status, extraction_prompt_cache_key, audience, candidate_id
    );
CREATE INDEX IF NOT EXISTS idx_recall_evaluation_review
    ON recall_audience_evaluation(review_status, audience, candidate_id);

CREATE TABLE IF NOT EXISTS recall_attempt (
    sample_id TEXT NOT NULL,
    audience TEXT NOT NULL,
    stage TEXT NOT NULL CHECK (stage IN ('extraction', 'review')),
    attempt_number INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('complete', 'failed', 'rejected')),
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
    request_tags_json TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (sample_id, audience, stage, attempt_number),
    FOREIGN KEY (sample_id, audience)
        REFERENCES recall_audience_evaluation(sample_id, audience)
        ON DELETE RESTRICT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def selection_sha256(*, day: str, band: str, event_id: str) -> str:
    """Return the exact predeclared sample-order digest."""
    return _sha256(f"{PROTOCOL_VERSION}|{day}|{band}|{event_id}")


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(audience_insight_runs.REPO_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


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


def _sample_id(day: str, event_id: str) -> str:
    return f"recall-sample-{_sha256(f'{day}:{event_id}')[:20]}"


def _candidate_id(day: str, audience: str, event_id: str) -> str:
    value = f"{PROTOCOL_VERSION}|{day}|{audience}|{event_id}"
    return f"recall-candidate-{_sha256(value)[:20]}"


def _packet_payload(packet: audience_insights.EvidencePacket) -> dict[str, Any]:
    return audience_insight_runs._packet_payload(packet)


def _packet_from_payload(payload: Mapping[str, Any]) -> audience_insights.EvidencePacket:
    return audience_insight_runs._packet_from_payload(dict(payload))


def _article_edges(artifact_db: Path) -> dict[tuple[str, str], tuple[str, ...]]:
    conn = _open_readonly(artifact_db)
    try:
        rows = conn.execute(
            """SELECT candidate.envelope_day, candidate.event_id,
                      artifact.artifact_id
               FROM artifact_import_candidate AS candidate
               JOIN artifact USING (artifact_id)
               WHERE candidate.decision = 'accepted'
                 AND artifact.host = 'x.com'
                 AND instr(artifact.canonical_url, '/i/article/') > 0
               ORDER BY candidate.envelope_day, candidate.event_id,
                        artifact.artifact_id"""
        ).fetchall()
    finally:
        conn.close()
    grouped: dict[tuple[str, str], list[str]] = {}
    for row in rows:
        grouped.setdefault(
            (str(row["envelope_day"]), str(row["event_id"])), []
        ).append(str(row["artifact_id"]))
    return {
        key: tuple(dict.fromkeys(artifact_ids))
        for key, artifact_ids in grouped.items()
    }


def _triage_rows(path: Path) -> list[sqlite3.Row]:
    conn = _open_readonly(path)
    try:
        return conn.execute(
            """SELECT event_id, current_rank, envelope_json, decision, status
               FROM triage_item
               WHERE status = 'complete' AND decision IN ('keep', 'drop')
               ORDER BY current_rank, event_id"""
        ).fetchall()
    finally:
        conn.close()


def _contract_payload() -> dict[str, Any]:
    return {
        "extraction": {
            audience: {
                "prompt_version": audience_insights.prompt_version(audience),
                "prompt_sha256": audience_insights.prompt_sha256(audience),
                "schema_version": audience_insights.schema_version(audience),
            }
            for audience in AUDIENCES
        },
        "review": {
            audience: {
                "prompt_version": (
                    audience_insight_evaluations.item_prompt_version(audience)
                ),
                "prompt_sha256": (
                    audience_insight_evaluations.item_prompt_sha256(audience)
                ),
                "schema_version": audience_insight_evaluations.ITEM_SCHEMA_VERSION,
            }
            for audience in AUDIENCES
        },
    }


def _require_runtime_contract(conn: sqlite3.Connection) -> sqlite3.Row:
    """Fail closed when a frozen audit no longer matches the live contracts."""
    meta = conn.execute("SELECT * FROM recall_run WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("recall audit has not been frozen")
    if str(meta["protocol_version"]) != PROTOCOL_VERSION:
        raise ValueError(
            "recall protocol drift: frozen "
            f"{meta['protocol_version']!s}, runtime {PROTOCOL_VERSION}"
        )
    runtime_contract_sha256 = _sha256(_canonical_json(_contract_payload()))
    if str(meta["contract_sha256"]) != runtime_contract_sha256:
        raise ValueError(
            "recall contract drift: frozen prompt/schema hash does not match runtime"
        )

    rows = conn.execute(
        """SELECT audience, extraction_prompt_version,
                  extraction_prompt_sha256, extraction_schema_version,
                  COUNT(*) AS count
           FROM recall_audience_evaluation
           GROUP BY audience, extraction_prompt_version,
                    extraction_prompt_sha256, extraction_schema_version
           ORDER BY audience"""
    ).fetchall()
    observed = {
        str(row["audience"]): (
            str(row["extraction_prompt_version"]),
            str(row["extraction_prompt_sha256"]),
            str(row["extraction_schema_version"]),
        )
        for row in rows
    }
    if len(rows) != len(observed):
        raise ValueError("recall extraction contract is inconsistent within an audience")
    expected = {
        audience: (
            audience_insights.prompt_version(audience),
            audience_insights.prompt_sha256(audience),
            audience_insights.schema_version(audience),
        )
        for audience in AUDIENCES
    }
    if observed != expected:
        raise ValueError(
            "recall extraction contract drift: frozen evaluation metadata does not "
            "match runtime"
        )
    return meta


def _require_frozen_adjudication_contract(
    conn: sqlite3.Connection,
) -> sqlite3.Row:
    """Validate a preserved recall freeze without comparing it to live prompts.

    Extraction and review execution must remain blocked when runtime prompt or
    schema contracts drift.  Adjudication export/import is different: it is a
    read/write decision over already-frozen model results and binds every row
    back to the stored run, contract, sample, candidate, and review-input
    hashes.  Requiring today's prompt hashes here would make an immutable audit
    impossible to finish after a legitimate prompt version advance.
    """
    meta = conn.execute("SELECT * FROM recall_run WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("recall audit has not been frozen")
    if str(meta["protocol_version"]) != PROTOCOL_VERSION:
        raise ValueError(
            "recall protocol drift: frozen "
            f"{meta['protocol_version']!s}, runtime {PROTOCOL_VERSION}"
        )
    if not str(meta["contract_sha256"]).strip():
        raise ValueError("frozen recall contract hash is missing")

    rows = conn.execute(
        """SELECT audience, extraction_prompt_version,
                  extraction_prompt_sha256, extraction_schema_version,
                  COUNT(*) AS count
           FROM recall_audience_evaluation
           GROUP BY audience, extraction_prompt_version,
                    extraction_prompt_sha256, extraction_schema_version
           ORDER BY audience"""
    ).fetchall()
    observed_audiences = {str(row["audience"]) for row in rows}
    if len(rows) != len(observed_audiences) or observed_audiences != set(AUDIENCES):
        raise ValueError(
            "frozen recall extraction contract is inconsistent within an audience"
        )
    for row in rows:
        if not all(
            str(row[field]).strip()
            for field in (
                "extraction_prompt_version",
                "extraction_prompt_sha256",
                "extraction_schema_version",
            )
        ):
            raise ValueError("frozen recall extraction contract metadata is missing")
    return meta


def _ranked_candidates(
    rows: Sequence[sqlite3.Row],
    *,
    day: str,
    band: str,
    decision: str,
    low: int,
    high: int,
) -> list[sqlite3.Row]:
    candidates = [
        row
        for row in rows
        if str(row["decision"]) == decision
        and low <= int(row["current_rank"]) <= high
    ]
    return sorted(
        candidates,
        key=lambda row: (
            selection_sha256(
                day=day,
                band=band,
                event_id=str(row["event_id"]),
            ),
            str(row["event_id"]),
        ),
    )


def _select_quota(
    rows: Sequence[sqlite3.Row],
    *,
    day: str,
    band: str,
    decision: str,
    low: int,
    high: int,
    quota: int,
    seen_event_ids: set[str],
) -> tuple[list[sqlite3.Row], list[dict[str, Any]]]:
    selected: list[sqlite3.Row] = []
    skipped: list[tuple[str, str]] = []
    replacements: list[dict[str, Any]] = []
    for row in _ranked_candidates(
        rows,
        day=day,
        band=band,
        decision=decision,
        low=low,
        high=high,
    ):
        event_id = str(row["event_id"])
        digest = selection_sha256(day=day, band=band, event_id=event_id)
        if event_id in seen_event_ids:
            skipped.append((event_id, digest))
            continue
        seen_event_ids.add(event_id)
        selected.append(row)
        for skipped_event_id, skipped_digest in skipped:
            replacements.append(
                {
                    "day": day,
                    "band": band,
                    "skipped_event_id": skipped_event_id,
                    "skipped_selection_sha256": skipped_digest,
                    "replacement_event_id": event_id,
                    "reason": "repeated_event",
                }
            )
        skipped.clear()
        if len(selected) == quota:
            return selected, replacements
    raise ValueError(
        f"{day} {band} has fewer than {quota} globally unique candidates"
    )


def _build_frozen_sample(
    *,
    days: Sequence[str],
    triage_dbs: Mapping[str, Path],
    artifact_db: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows_by_day = {day: _triage_rows(triage_dbs[day]) for day in days}
    articles = _article_edges(artifact_db)
    selected: list[tuple[str, str, sqlite3.Row]] = []
    replacements: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()

    # Stage 1 follows the document order: both lower-kept bands for every day.
    for day in days:
        for band, decision, low, high, quota, sample_kind in QUOTA_BANDS:
            chosen, band_replacements = _select_quota(
                rows_by_day[day],
                day=day,
                band=band,
                decision=decision,
                low=low,
                high=high,
                quota=quota,
                seen_event_ids=seen_event_ids,
            )
            selected.extend((band, sample_kind, row) for row in chosen)
            replacements.extend(band_replacements)

    # Stage 2 is a census rather than a quota.  An edge whose event is already
    # present is recorded, then omitted exactly as the predeclared protocol says.
    for day in days:
        candidates = [
            row
            for row in _ranked_candidates(
                rows_by_day[day],
                day=day,
                band=X_ARTICLE_51_100,
                decision="keep",
                low=51,
                high=100,
            )
            if (day, str(row["event_id"])) in articles
        ]
        for row in candidates:
            event_id = str(row["event_id"])
            digest = selection_sha256(
                day=day, band=X_ARTICLE_51_100, event_id=event_id
            )
            if event_id in seen_event_ids:
                replacements.append(
                    {
                        "day": day,
                        "band": X_ARTICLE_51_100,
                        "skipped_event_id": event_id,
                        "skipped_selection_sha256": digest,
                        "replacement_event_id": None,
                        "reason": "article_event_already_selected",
                    }
                )
                continue
            seen_event_ids.add(event_id)
            selected.append((X_ARTICLE_51_100, "x_article_census", row))

    # Stage 3 probes upstream triage after the cutoff sample is fixed.
    for day in days:
        for band, decision, low, high, quota, sample_kind in DROP_BANDS:
            chosen, band_replacements = _select_quota(
                rows_by_day[day],
                day=day,
                band=band,
                decision=decision,
                low=low,
                high=high,
                quota=quota,
                seen_event_ids=seen_event_ids,
            )
            selected.extend((band, sample_kind, row) for row in chosen)
            replacements.extend(band_replacements)

    artifact_conn = _open_readonly(artifact_db)
    try:
        samples: list[dict[str, Any]] = []
        for order, (band, sample_kind, row) in enumerate(selected, start=1):
            day = str(json.loads(row["envelope_json"])["day"])
            event_id = str(row["event_id"])
            packet = audience_insight_runs._packet_from_row(
                row, artifact_conn=artifact_conn
            )
            input_text = audience_insights.render_input(packet)
            # This is the critical separation: audit metadata remains in the
            # sample row, while the model input is the shared blind renderer.
            if "feed_rank" in input_text or "triage_decision" in input_text:
                raise ValueError("rank-blind extraction input leaked audit metadata")
            samples.append(
                {
                    "sample_id": _sample_id(day, event_id),
                    "selection_order": order,
                    "day": day,
                    "event_id": event_id,
                    "band": band,
                    "sample_kind": sample_kind,
                    "triage_decision": str(row["decision"]),
                    "feed_rank": int(row["current_rank"]),
                    "selection_sha256": selection_sha256(
                        day=day, band=band, event_id=event_id
                    ),
                    "article_artifact_ids": list(articles.get((day, event_id), ())),
                    "packet": _packet_payload(packet),
                    "evidence_sha256": packet.evidence_sha256,
                    "extraction_input_text": input_text,
                    "extraction_input_sha256": packet.input_sha256,
                }
            )
    finally:
        artifact_conn.close()
    return samples, replacements


def freeze_audit(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    days: Sequence[str] = DAYS,
    triage_dbs: Mapping[str, Path] | None = None,
    artifact_db: Path = DEFAULT_ARTIFACT_DB,
    extraction_model: str = DEFAULT_MODEL,
    extraction_effort: str = DEFAULT_EXTRACTION_EFFORT,
    review_model: str = DEFAULT_REVIEW_MODEL,
    review_effort: str = DEFAULT_REVIEW_EFFORT,
) -> int:
    if not run_id.strip():
        raise ValueError("run_id must be non-empty")
    frozen_days = tuple(dict.fromkeys(days))
    if not frozen_days or any(day not in DAYS for day in frozen_days):
        raise ValueError("days must be a non-empty subset of 2026-07-05..13")
    source_dbs = {
        day: Path((triage_dbs or {}).get(day) or audience_insight_runs.canonical_triage_db(day))
        for day in frozen_days
    }
    samples, replacements = _build_frozen_sample(
        days=frozen_days,
        triage_dbs=source_dbs,
        artifact_db=artifact_db,
    )
    contract = _contract_payload()
    sample_set_sha256 = _sha256(
        _canonical_json(
            {
                "samples": samples,
                "replacements": replacements,
            }
        )
    )
    source_json = _canonical_json(
        {day: _display_path(source_dbs[day]) for day in frozen_days}
    )
    expected = {
        "run_id": run_id,
        "protocol_version": PROTOCOL_VERSION,
        "days_json": _canonical_json(frozen_days),
        "source_triage_dbs_json": source_json,
        "source_artifact_db": _display_path(artifact_db),
        "extraction_model": extraction_model,
        "extraction_reasoning_effort": extraction_effort,
        "review_model": review_model,
        "review_reasoning_effort": review_effort,
        "contract_sha256": _sha256(_canonical_json(contract)),
        "sample_set_sha256": sample_set_sha256,
        "expected_sample_count": len(samples),
        "expected_evaluation_count": len(samples) * len(AUDIENCES),
    }
    existing = conn.execute(
        "SELECT * FROM recall_run WHERE singleton = 1"
    ).fetchone()
    if existing is not None:
        mismatches = [key for key, value in expected.items() if existing[key] != value]
        if mismatches:
            raise ValueError(
                "recall database does not match frozen request: "
                + ", ".join(mismatches)
            )
        return int(existing["expected_sample_count"])

    now = _now()
    with conn:
        conn.execute(
            """INSERT INTO recall_run
               (singleton, run_id, protocol_version, days_json,
                source_triage_dbs_json, source_artifact_db,
                extraction_model, extraction_reasoning_effort,
                review_model, review_reasoning_effort, contract_sha256,
                sample_set_sha256, expected_sample_count,
                expected_evaluation_count, created_at, updated_at)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                PROTOCOL_VERSION,
                expected["days_json"],
                source_json,
                expected["source_artifact_db"],
                extraction_model,
                extraction_effort,
                review_model,
                review_effort,
                expected["contract_sha256"],
                sample_set_sha256,
                len(samples),
                len(samples) * len(AUDIENCES),
                now,
                now,
            ),
        )
        conn.executemany(
            """INSERT INTO recall_sample
               (sample_id, selection_order, day, event_id, band, sample_kind,
                triage_decision, feed_rank, selection_sha256,
                article_artifact_ids_json, packet_json, evidence_sha256,
                extraction_input_text, extraction_input_sha256, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    sample["sample_id"],
                    sample["selection_order"],
                    sample["day"],
                    sample["event_id"],
                    sample["band"],
                    sample["sample_kind"],
                    sample["triage_decision"],
                    sample["feed_rank"],
                    sample["selection_sha256"],
                    _canonical_json(sample["article_artifact_ids"]),
                    _canonical_json(sample["packet"]),
                    sample["evidence_sha256"],
                    sample["extraction_input_text"],
                    sample["extraction_input_sha256"],
                    now,
                )
                for sample in samples
            ],
        )
        conn.executemany(
            """INSERT INTO recall_replacement
               (day, band, skipped_event_id, skipped_selection_sha256,
                replacement_event_id, reason)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (
                    item["day"],
                    item["band"],
                    item["skipped_event_id"],
                    item["skipped_selection_sha256"],
                    item["replacement_event_id"],
                    item["reason"],
                )
                for item in replacements
            ],
        )
        evaluations = []
        for sample in samples:
            for audience in AUDIENCES:
                candidate_id = _candidate_id(
                    sample["day"], audience, sample["event_id"]
                )
                evaluations.append(
                    (
                        sample["sample_id"],
                        audience,
                        candidate_id,
                        sample["extraction_input_text"],
                        sample["extraction_input_sha256"],
                        audience_insights.prompt_version(audience),
                        audience_insights.prompt_sha256(audience),
                        audience_insights.schema_version(audience),
                        audience_insights.prompt_cache_key(audience, sample["event_id"]),
                        now,
                    )
                )
        conn.executemany(
            """INSERT INTO recall_audience_evaluation
               (sample_id, audience, candidate_id, extraction_input_text,
                extraction_input_sha256, extraction_prompt_version,
                extraction_prompt_sha256, extraction_schema_version,
                extraction_prompt_cache_key, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            evaluations,
        )
    return len(samples)


def _telemetry_values(result: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        result.get("response_id"),
        result.get("response_model"),
        result.get("input_tokens"),
        result.get("cached_tokens"),
        result.get("cache_write_tokens"),
        result.get("output_tokens"),
        result.get("reported_cost_usd"),
        _canonical_json(result.get("request_tags") or []),
    )


def _insert_attempt(
    conn: sqlite3.Connection,
    *,
    row: sqlite3.Row,
    stage: str,
    status: str,
    result: Mapping[str, Any] | None = None,
    error: Exception | None = None,
) -> None:
    payload = result or {}
    attempt_column = "extraction_attempts" if stage == "extraction" else "review_attempts"
    conn.execute(
        """INSERT INTO recall_attempt
           (sample_id, audience, stage, attempt_number, status, result_json,
            raw_output_text, error_type, error_message, response_id,
            response_model, input_tokens, cached_tokens, cache_write_tokens,
            output_tokens, reported_cost_usd, request_tags_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            row["sample_id"],
            row["audience"],
            stage,
            int(row[attempt_column]) + 1,
            status,
            _canonical_json(payload) if payload else None,
            payload.get("raw_output_text"),
            type(error).__name__ if error is not None else None,
            str(error) if error is not None else None,
            *_telemetry_values(payload),
            _now(),
        ),
    )


def _store_extraction_success(
    conn: sqlite3.Connection, row: sqlite3.Row, result: Mapping[str, Any]
) -> None:
    outcome = str(result["outcome"])
    no_insight = outcome == "no_extractable_insight"
    now = _now()
    with conn:
        _insert_attempt(
            conn, row=row, stage="extraction", status="complete", result=result
        )
        conn.execute(
            """UPDATE recall_audience_evaluation
               SET extraction_status = 'complete',
                   extraction_attempts = extraction_attempts + 1,
                   outcome = ?, no_insight = ?, no_insight_reason = ?,
                   citation_valid = ?, extraction_result_json = ?,
                   extraction_raw_output_text = ?, extraction_error_type = NULL,
                   extraction_error_message = NULL, extraction_completed_at = ?,
                   review_status = ?, updated_at = ?
               WHERE sample_id = ? AND audience = ?""",
            (
                outcome,
                int(no_insight),
                result.get("no_insight_reason"),
                None if no_insight else int(result.get("citation") is not None),
                _canonical_json(result),
                result.get("raw_output_text"),
                now,
                "not_applicable" if no_insight else "pending",
                now,
                row["sample_id"],
                row["audience"],
            ),
        )


def _store_extraction_failure(
    conn: sqlite3.Connection, row: sqlite3.Row, error: Exception
) -> str:
    result: Mapping[str, Any] = getattr(error, "result", {}) or {}
    citation = isinstance(error, audience_insights.CitationVerificationError)
    schema = isinstance(error, audience_insights.ExtractionValidationError)
    deterministic = citation or schema
    prior_failures = int(
        row["citation_failure_attempts"] if citation else row["schema_failure_attempts"]
    )
    terminal = deterministic and prior_failures + 1 >= MAX_DETERMINISTIC_FAILURE_ATTEMPTS
    status = "rejected" if terminal else "failed"
    now = _now()
    with conn:
        _insert_attempt(
            conn,
            row=row,
            stage="extraction",
            status=status,
            result=result,
            error=error,
        )
        conn.execute(
            """UPDATE recall_audience_evaluation
               SET extraction_status = ?,
                   extraction_attempts = extraction_attempts + 1,
                   citation_failure_attempts = citation_failure_attempts + ?,
                   citation_terminal_failure = ?,
                   schema_failure_attempts = schema_failure_attempts + ?,
                   schema_terminal_failure = ?,
                   extraction_result_json = ?, extraction_raw_output_text = ?,
                   extraction_error_type = ?, extraction_error_message = ?,
                   extraction_completed_at = ?, review_status = ?, updated_at = ?
               WHERE sample_id = ? AND audience = ?""",
            (
                status,
                int(citation),
                int(terminal and citation),
                int(schema),
                int(terminal and schema),
                _canonical_json(result) if result else None,
                result.get("raw_output_text"),
                type(error).__name__,
                str(error),
                now if terminal else None,
                "not_applicable" if terminal else str(row["review_status"]),
                now,
                row["sample_id"],
                row["audience"],
            ),
        )
    return status


def _run_cache_lanes(
    rows: Sequence[sqlite3.Row],
    *,
    workers: int,
    cache_key_field: str,
    evaluate: Any,
    store: Any,
) -> None:
    if not rows:
        return
    lanes: dict[str, deque[sqlite3.Row]] = {}
    for row in rows:
        lanes.setdefault(str(row[cache_key_field]), deque()).append(row)
    waiting = deque(lanes)
    active: dict[concurrent.futures.Future[Any], str] = {}
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(workers, len(lanes))
    ) as executor:
        def start(cache_key: str) -> None:
            row = lanes[cache_key].popleft()
            active[executor.submit(evaluate, row)] = cache_key

        while waiting and len(active) < workers:
            start(waiting.popleft())
        while active:
            done, _ = concurrent.futures.wait(
                active, return_when=concurrent.futures.FIRST_COMPLETED
            )
            for future in done:
                cache_key = active.pop(future)
                store(future.result())
                if lanes[cache_key]:
                    start(cache_key)
                elif waiting:
                    start(waiting.popleft())


def run_extractions(
    conn: sqlite3.Connection,
    *,
    client: Any,
    audiences: Iterable[str] = AUDIENCES,
    workers: int = DEFAULT_WORKERS,
    retry_failed: bool = False,
) -> dict[str, Any]:
    if workers < 1:
        raise ValueError("workers must be positive")
    requested = tuple(
        dict.fromkeys(audience_insights.require_audience(a) for a in audiences)
    )
    if not requested:
        raise ValueError("at least one audience is required")
    meta = _require_runtime_contract(conn)
    statuses = ("pending", "failed") if retry_failed else ("pending",)
    rows = conn.execute(
        f"""SELECT evaluation.*, sample.packet_json, sample.day,
                   sample.event_id
            FROM recall_audience_evaluation AS evaluation
            JOIN recall_sample AS sample USING (sample_id)
            WHERE evaluation.audience IN ({','.join('?' for _ in requested)})
              AND evaluation.extraction_status IN ({','.join('?' for _ in statuses)})
            ORDER BY evaluation.extraction_prompt_cache_key,
                     sample.day, evaluation.candidate_id""",
        (*requested, *statuses),
    ).fetchall()

    def evaluate(row: sqlite3.Row) -> tuple[sqlite3.Row, Any, Exception | None]:
        packet = _packet_from_payload(json.loads(row["packet_json"]))
        try:
            result = audience_insights.evaluate_one(
                client,
                packet,
                audience=str(row["audience"]),
                run=str(meta["run_id"]),
                model=str(meta["extraction_model"]),
                effort=str(meta["extraction_reasoning_effort"]),
            )
            return row, result, None
        except Exception as exc:
            return row, None, exc

    def store(outcome: tuple[sqlite3.Row, Any, Exception | None]) -> None:
        row, result, error = outcome
        if error is None:
            _store_extraction_success(conn, row, result)
        else:
            _store_extraction_failure(conn, row, error)

    _run_cache_lanes(
        rows,
        workers=workers,
        cache_key_field="extraction_prompt_cache_key",
        evaluate=evaluate,
        store=store,
    )
    return summary(conn)


def _review_input(row: sqlite3.Row) -> audience_insight_evaluations.ItemReviewInput:
    packet = _packet_from_payload(json.loads(row["packet_json"]))
    result = json.loads(row["extraction_result_json"])
    audience_fields = result.get("audience_fields") or {}
    extracted = {
        "claim": result["claim"],
        "claim_posture": result["claim_posture"],
        "why_it_matters": result["why_it_matters"],
        "supporting_quote": result["supporting_quote"],
        "citation_block_index": result["citation_block_index"],
        **audience_fields,
    }
    blocks = tuple(
        audience_insight_evaluations.ReviewerEvidenceBlock(
            block_index=index,
            source_type=source.source_type,
            source_author=source.author,
            source_title=source.title,
            relation=source.relation,
            verbatim_text=source.normalized_text(),
        )
        for index, source in enumerate(packet.sources, start=1)
    )
    return audience_insight_evaluations.ItemReviewInput(
        candidate_id=str(row["candidate_id"]),
        audience=str(row["audience"]),
        day=str(row["day"]),
        evidence_blocks=blocks,
        extracted_item=extracted,
    )


def prepare_reviews(conn: sqlite3.Connection) -> int:
    rows = conn.execute(
        """SELECT evaluation.*, sample.packet_json, sample.day
           FROM recall_audience_evaluation AS evaluation
           JOIN recall_sample AS sample USING (sample_id)
           WHERE evaluation.extraction_status = 'complete'
             AND evaluation.outcome = 'insight'
           ORDER BY evaluation.candidate_id"""
    ).fetchall()
    prepared = 0
    now = _now()
    for row in rows:
        review = _review_input(row)
        input_text = audience_insight_evaluations.render_item_input(review)
        if "feed_rank" in input_text or str(row["sample_id"]) in input_text:
            raise ValueError("rank-blind reviewer input leaked audit metadata")
        cache_key = audience_insight_evaluations.item_prompt_cache_key(
            str(row["audience"]), str(row["candidate_id"])
        )
        existing_text = row["review_input_text"]
        if existing_text is not None:
            if (
                str(existing_text) != input_text
                or str(row["review_input_sha256"]) != review.input_sha256
                or str(row["review_prompt_cache_key"]) != cache_key
            ):
                raise ValueError(
                    f"review input changed for frozen candidate {row['candidate_id']}"
                )
            continue
        with conn:
            conn.execute(
                """UPDATE recall_audience_evaluation
                   SET review_input_text = ?, review_input_sha256 = ?,
                       review_prompt_cache_key = ?, updated_at = ?
                   WHERE sample_id = ? AND audience = ?""",
                (
                    input_text,
                    review.input_sha256,
                    cache_key,
                    now,
                    row["sample_id"],
                    row["audience"],
                ),
            )
        prepared += 1
    return prepared


def _store_review_success(
    conn: sqlite3.Connection, row: sqlite3.Row, result: Mapping[str, Any]
) -> None:
    now = _now()
    with conn:
        _insert_attempt(conn, row=row, stage="review", status="complete", result=result)
        conn.execute(
            """UPDATE recall_audience_evaluation
               SET review_status = 'complete', review_attempts = review_attempts + 1,
                   claim_fidelity = ?, epistemic_discipline = ?,
                   audience_useful = ?, actionable = ?, specific = ?,
                   review_failure_codes_json = ?, review_rationale = ?,
                   review_result_json = ?, review_raw_output_text = ?,
                   review_error_type = NULL, review_error_message = NULL,
                   review_completed_at = ?, updated_at = ?
               WHERE sample_id = ? AND audience = ?""",
            (
                int(result["claim_fidelity"] == "pass"),
                int(result["epistemic_discipline"] == "pass"),
                int(result["audience_usefulness"] == "pass"),
                int(result["actionability"] == "pass"),
                int(result["specificity"] == "pass"),
                _canonical_json(result["failure_codes"]),
                result["rationale"],
                _canonical_json(result),
                result.get("raw_output_text"),
                now,
                now,
                row["sample_id"],
                row["audience"],
            ),
        )


def _store_review_failure(
    conn: sqlite3.Connection, row: sqlite3.Row, error: Exception
) -> None:
    now = _now()
    with conn:
        _insert_attempt(conn, row=row, stage="review", status="failed", error=error)
        conn.execute(
            """UPDATE recall_audience_evaluation
               SET review_status = 'failed', review_attempts = review_attempts + 1,
                   review_error_type = ?, review_error_message = ?, updated_at = ?
               WHERE sample_id = ? AND audience = ?""",
            (
                type(error).__name__,
                str(error),
                now,
                row["sample_id"],
                row["audience"],
            ),
        )


def run_reviews(
    conn: sqlite3.Connection,
    *,
    client: Any,
    audiences: Iterable[str] = AUDIENCES,
    workers: int = DEFAULT_WORKERS,
    retry_failed: bool = False,
) -> dict[str, Any]:
    if workers < 1:
        raise ValueError("workers must be positive")
    requested = tuple(
        dict.fromkeys(audience_insights.require_audience(a) for a in audiences)
    )
    if not requested:
        raise ValueError("at least one audience is required")
    meta = _require_runtime_contract(conn)
    prepare_reviews(conn)
    statuses = ("pending", "failed") if retry_failed else ("pending",)
    rows = conn.execute(
        f"""SELECT evaluation.*, sample.packet_json, sample.day
            FROM recall_audience_evaluation AS evaluation
            JOIN recall_sample AS sample USING (sample_id)
            WHERE evaluation.audience IN ({','.join('?' for _ in requested)})
              AND evaluation.extraction_status = 'complete'
              AND evaluation.outcome = 'insight'
              AND evaluation.review_status IN ({','.join('?' for _ in statuses)})
            ORDER BY evaluation.review_prompt_cache_key,
                     sample.day, evaluation.candidate_id""",
        (*requested, *statuses),
    ).fetchall()

    def evaluate(row: sqlite3.Row) -> tuple[sqlite3.Row, Any, Exception | None]:
        review = _review_input(row)
        try:
            result = audience_insight_evaluations.review_item(
                client,
                review,
                run=str(meta["run_id"]),
                model=str(meta["review_model"]),
                effort=str(meta["review_reasoning_effort"]),
            )
            return row, result, None
        except Exception as exc:
            return row, None, exc

    def store(outcome: tuple[sqlite3.Row, Any, Exception | None]) -> None:
        row, result, error = outcome
        if error is None:
            _store_review_success(conn, row, result)
        else:
            _store_review_failure(conn, row, error)

    _run_cache_lanes(
        rows,
        workers=workers,
        cache_key_field="review_prompt_cache_key",
        evaluate=evaluate,
        store=store,
    )
    return summary(conn)


def record_adjudication(
    conn: sqlite3.Connection,
    *,
    sample_id: str,
    audience: str,
    redundant: bool,
    final_set_worthy: bool,
    high_consequence: bool = False,
    note: str,
    comparison: Mapping[str, Any],
) -> None:
    _require_runtime_contract(conn)
    audience = audience_insights.require_audience(audience)
    row = conn.execute(
        """SELECT * FROM recall_audience_evaluation
           WHERE sample_id = ? AND audience = ?""",
        (sample_id, audience),
    ).fetchone()
    if row is None:
        raise ValueError("unknown recall evaluation")
    comparison_payload = _validate_adjudication(
        row,
        redundant=redundant,
        final_set_worthy=final_set_worthy,
        high_consequence=high_consequence,
        note=note,
        comparison=comparison,
    )
    now = _now()
    with conn:
        conn.execute(
            """UPDATE recall_audience_evaluation
               SET redundant = ?, final_set_worthy = ?, high_consequence = ?,
                   adjudication_comparison_json = ?, adjudication_note = ?,
                   adjudicated_at = ?, updated_at = ?
               WHERE sample_id = ? AND audience = ?""",
            (
                int(redundant),
                int(final_set_worthy),
                int(high_consequence),
                _canonical_json(comparison_payload),
                note.strip(),
                now,
                now,
                sample_id,
                audience,
            ),
        )


_COMPARISON_OUTCOMES = {
    "would_enter",
    "materially_diversifies",
    "would_not_enter",
}
_REVIEW_DIMENSIONS = (
    "claim_fidelity",
    "epistemic_discipline",
    "audience_useful",
    "actionable",
    "specific",
)


def _validate_comparison(comparison: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(comparison, Mapping):
        raise ValueError("comparison metadata must be an object")
    required = {
        "reference_set_id",
        "reference_candidate_ids",
        "outcome",
        "note",
    }
    if set(comparison) != required:
        raise ValueError(
            "comparison metadata must contain exactly: "
            + ", ".join(sorted(required))
        )
    reference_set_id = comparison["reference_set_id"]
    candidate_ids = comparison["reference_candidate_ids"]
    outcome = comparison["outcome"]
    comparison_note = comparison["note"]
    if not isinstance(reference_set_id, str) or not reference_set_id.strip():
        raise ValueError("comparison reference_set_id must be non-empty")
    if not isinstance(candidate_ids, list) or any(
        not isinstance(item, str) or not item.strip() for item in candidate_ids
    ):
        raise ValueError("comparison reference_candidate_ids must be a string list")
    normalized_ids = [item.strip() for item in candidate_ids]
    if len(normalized_ids) != len(set(normalized_ids)):
        raise ValueError("comparison reference_candidate_ids must be unique")
    if outcome not in _COMPARISON_OUTCOMES:
        raise ValueError(
            "comparison outcome must be would_enter, materially_diversifies, "
            "or would_not_enter"
        )
    if not isinstance(comparison_note, str) or not comparison_note.strip():
        raise ValueError("comparison note must be non-empty")
    return {
        "reference_set_id": reference_set_id.strip(),
        "reference_candidate_ids": normalized_ids,
        "outcome": outcome,
        "note": comparison_note.strip(),
    }


def _validate_adjudication(
    row: sqlite3.Row,
    *,
    redundant: bool,
    final_set_worthy: bool,
    high_consequence: bool,
    note: str,
    comparison: Mapping[str, Any],
) -> dict[str, Any]:
    if row["review_status"] != "complete":
        raise ValueError("final-set adjudication requires a complete item review")
    for field, value in (
        ("redundant", redundant),
        ("final_set_worthy", final_set_worthy),
        ("high_consequence", high_consequence),
    ):
        if type(value) is not bool:
            raise ValueError(f"{field} must be a boolean")
    if not isinstance(note, str) or not note.strip():
        raise ValueError("adjudication note must be non-empty")
    comparison_payload = _validate_comparison(comparison)
    all_five_pass = all(int(row[field] or 0) == 1 for field in _REVIEW_DIMENSIONS)
    if final_set_worthy and (
        int(row["citation_valid"] or 0) != 1 or not all_five_pass or redundant
    ):
        raise ValueError(
            "final-set-worthy requires a valid citation, all five review dimensions, "
            "and non-redundant evidence"
        )
    comparison_worthy = comparison_payload["outcome"] in {
        "would_enter",
        "materially_diversifies",
    }
    if comparison_worthy != final_set_worthy:
        raise ValueError(
            "final_set_worthy must agree with the explicit comparison outcome"
        )
    if high_consequence and not final_set_worthy:
        raise ValueError("high_consequence requires final_set_worthy")
    return comparison_payload


def _adjudication_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT evaluation.*, sample.day, sample.event_id, sample.band,
                  sample.sample_kind, sample.triage_decision, sample.feed_rank,
                  sample.selection_order, sample.evidence_sha256
           FROM recall_audience_evaluation AS evaluation
           JOIN recall_sample AS sample USING (sample_id)
           WHERE evaluation.extraction_status = 'complete'
             AND evaluation.outcome = 'insight'
             AND evaluation.review_status = 'complete'
           ORDER BY sample.day, sample.selection_order, evaluation.audience"""
    ).fetchall()


def _adjudication_identity(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "sample_id": str(row["sample_id"]),
        "audience": str(row["audience"]),
        "candidate_id": str(row["candidate_id"]),
        "review_input_sha256": str(row["review_input_sha256"]),
    }


def _evaluation_set_sha256(rows: Sequence[Mapping[str, Any]]) -> str:
    return _sha256(_canonical_json([_adjudication_identity(row) for row in rows]))


def export_adjudication_batch(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return the complete deterministic adjudication batch for this freeze."""
    meta = _require_frozen_adjudication_contract(conn)
    rows = _adjudication_rows(conn)
    exported: list[dict[str, Any]] = []
    for row in rows:
        result = json.loads(row["extraction_result_json"])
        comparison = (
            json.loads(row["adjudication_comparison_json"])
            if row["adjudication_comparison_json"]
            else {
                "reference_set_id": "",
                "reference_candidate_ids": [],
                "outcome": None,
                "note": "",
            }
        )
        exported.append(
            {
                **_adjudication_identity(row),
                "day": str(row["day"]),
                "event_id": str(row["event_id"]),
                "band": str(row["band"]),
                "sample_kind": str(row["sample_kind"]),
                "triage_decision": str(row["triage_decision"]),
                "feed_rank": int(row["feed_rank"]),
                "evidence_sha256": str(row["evidence_sha256"]),
                "extracted_item": {
                    key: result.get(key)
                    for key in (
                        "claim",
                        "claim_posture",
                        "why_it_matters",
                        "supporting_quote",
                        "citation_block_index",
                        "audience_fields",
                    )
                },
                "review": {
                    field: bool(row[field]) for field in _REVIEW_DIMENSIONS
                }
                | {
                    "failure_codes": json.loads(
                        row["review_failure_codes_json"] or "[]"
                    ),
                    "rationale": row["review_rationale"],
                },
                "comparison": comparison,
                "adjudication": {
                    "redundant": (
                        None if row["redundant"] is None else bool(row["redundant"])
                    ),
                    "final_set_worthy": (
                        None
                        if row["final_set_worthy"] is None
                        else bool(row["final_set_worthy"])
                    ),
                    "high_consequence": (
                        None
                        if row["high_consequence"] is None
                        else bool(row["high_consequence"])
                    ),
                    "note": row["adjudication_note"] or "",
                },
            }
        )
    return {
        "schema_version": ADJUDICATION_SCHEMA_VERSION,
        "run_id": str(meta["run_id"]),
        "protocol_version": str(meta["protocol_version"]),
        "contract_sha256": str(meta["contract_sha256"]),
        "sample_set_sha256": str(meta["sample_set_sha256"]),
        "evaluation_set_sha256": _evaluation_set_sha256(rows),
        "expected_row_count": len(rows),
        "criteria": {
            "final_set_worthy": (
                "citation valid; all five review dimensions pass; non-redundant; "
                "and comparison outcome is would_enter or materially_diversifies"
            ),
            "comparison_outcomes": sorted(_COMPARISON_OUTCOMES),
        },
        "rows": exported,
    }


def import_adjudication_batch(
    conn: sqlite3.Connection, payload: Mapping[str, Any]
) -> int:
    """Validate an exact exported batch, then apply every adjudication atomically."""
    meta = _require_frozen_adjudication_contract(conn)
    if not isinstance(payload, Mapping):
        raise ValueError("adjudication import must be a JSON object")
    for field, expected in (
        ("schema_version", ADJUDICATION_SCHEMA_VERSION),
        ("run_id", str(meta["run_id"])),
        ("protocol_version", str(meta["protocol_version"])),
        ("contract_sha256", str(meta["contract_sha256"])),
        ("sample_set_sha256", str(meta["sample_set_sha256"])),
    ):
        if payload.get(field) != expected:
            raise ValueError(f"adjudication import {field} does not match freeze")
    incoming = payload.get("rows")
    if not isinstance(incoming, list):
        raise ValueError("adjudication import rows must be a list")
    frozen_rows = _adjudication_rows(conn)
    frozen_by_key = {
        (str(row["sample_id"]), str(row["audience"])): row for row in frozen_rows
    }
    if payload.get("expected_row_count") != len(frozen_rows) or len(incoming) != len(
        frozen_rows
    ):
        raise ValueError("adjudication import must cover the complete exported batch")
    incoming_identities = []
    prepared: list[tuple[sqlite3.Row, dict[str, Any], dict[str, Any]]] = []
    seen: set[tuple[str, str]] = set()
    for item in incoming:
        if not isinstance(item, Mapping):
            raise ValueError("each adjudication row must be an object")
        identity_fields = {
            "sample_id",
            "audience",
            "candidate_id",
            "review_input_sha256",
        }
        if not identity_fields.issubset(item):
            raise ValueError(
                "adjudication row is missing evaluation identity metadata"
            )
        key = (str(item.get("sample_id", "")), str(item.get("audience", "")))
        if key in seen:
            raise ValueError("adjudication import contains duplicate evaluation rows")
        seen.add(key)
        row = frozen_by_key.get(key)
        if row is None:
            raise ValueError("adjudication import contains an unknown evaluation")
        identity = _adjudication_identity(item)
        if identity != _adjudication_identity(row):
            raise ValueError("adjudication import evaluation identity changed")
        incoming_identities.append(identity)
        adjudication = item.get("adjudication")
        if not isinstance(adjudication, Mapping):
            raise ValueError("adjudication row must contain an adjudication object")
        required = {"redundant", "final_set_worthy", "high_consequence", "note"}
        if set(adjudication) != required:
            raise ValueError(
                "adjudication object must contain exactly: "
                + ", ".join(sorted(required))
            )
        comparison_payload = _validate_adjudication(
            row,
            redundant=adjudication["redundant"],
            final_set_worthy=adjudication["final_set_worthy"],
            high_consequence=adjudication["high_consequence"],
            note=adjudication["note"],
            comparison=item.get("comparison"),
        )
        prepared.append((row, comparison_payload, dict(adjudication)))
    incoming_digest = _sha256(_canonical_json(incoming_identities))
    if (
        payload.get("evaluation_set_sha256") != incoming_digest
        or incoming_digest != _evaluation_set_sha256(frozen_rows)
    ):
        raise ValueError("adjudication import evaluation set changed after export")

    now = _now()
    with conn:
        for row, comparison, adjudication in prepared:
            conn.execute(
                """UPDATE recall_audience_evaluation
                   SET redundant = ?, final_set_worthy = ?, high_consequence = ?,
                       adjudication_comparison_json = ?, adjudication_note = ?,
                       adjudicated_at = ?, updated_at = ?
                   WHERE sample_id = ? AND audience = ?""",
                (
                    int(adjudication["redundant"]),
                    int(adjudication["final_set_worthy"]),
                    int(adjudication["high_consequence"]),
                    _canonical_json(comparison),
                    str(adjudication["note"]).strip(),
                    now,
                    now,
                    row["sample_id"],
                    row["audience"],
                ),
            )
    return len(prepared)


def _is_final_set_miss(row: Mapping[str, Any]) -> bool:
    return (
        int(row["final_set_worthy"] or 0) == 1
        and int(row["citation_valid"] or 0) == 1
        and int(row["redundant"] if row["redundant"] is not None else 1) == 0
        and all(int(row[field] or 0) == 1 for field in _REVIEW_DIMENSIONS)
    )


def _recall_analysis(
    conn: sqlite3.Connection, *, days: Sequence[str]
) -> dict[str, Any]:
    rows = conn.execute(
        """SELECT sample.day, sample.band, sample.sample_kind,
                  evaluation.audience, evaluation.extraction_status,
                  evaluation.outcome, evaluation.no_insight,
                  evaluation.citation_terminal_failure,
                  evaluation.schema_terminal_failure,
                  evaluation.review_status, evaluation.citation_valid,
                  evaluation.claim_fidelity,
                  evaluation.epistemic_discipline,
                  evaluation.audience_useful, evaluation.actionable,
                  evaluation.specific, evaluation.redundant,
                  evaluation.final_set_worthy,
                  evaluation.high_consequence
           FROM recall_audience_evaluation AS evaluation
           JOIN recall_sample AS sample USING (sample_id)
           ORDER BY sample.day, sample.band, evaluation.audience,
                    evaluation.candidate_id"""
    ).fetchall()
    strata: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    day_counts = {
        (day, audience): {
            "kept_51_75_misses": 0,
            "kept_76_100_misses": 0,
            "x_article_51_100_misses": 0,
            "awaiting_adjudication": 0,
            "incomplete_evaluations": 0,
        }
        for day in days
        for audience in AUDIENCES
    }
    systemic_days: dict[tuple[str, str], set[str]] = {}
    triage_counts = {
        audience: {
            "false_negatives": 0,
            "high_consequence_false_negatives": 0,
            "awaiting_adjudication": 0,
            "incomplete_evaluations": 0,
        }
        for audience in AUDIENCES
    }
    for row in rows:
        key = (
            str(row["day"]),
            str(row["band"]),
            str(row["sample_kind"]),
            str(row["audience"]),
        )
        aggregate = strata.setdefault(
            key,
            {
                "day": key[0],
                "band": key[1],
                "sample_kind": key[2],
                "audience": key[3],
                "total": 0,
                "no_insight": 0,
                "citation_terminal": 0,
                "schema_terminal": 0,
                "review_complete": 0,
                "all_five_pass": 0,
                "awaiting_adjudication": 0,
                "incomplete_evaluations": 0,
                "final_set_worthy_misses": 0,
                "high_consequence_misses": 0,
            },
        )
        aggregate["total"] += 1
        aggregate["no_insight"] += int(row["no_insight"] or 0)
        aggregate["citation_terminal"] += int(
            row["citation_terminal_failure"] or 0
        )
        aggregate["schema_terminal"] += int(row["schema_terminal_failure"] or 0)
        review_complete = row["review_status"] == "complete"
        all_five = review_complete and all(
            int(row[field] or 0) == 1 for field in _REVIEW_DIMENSIONS
        )
        incomplete = row["extraction_status"] != "complete" or (
            row["outcome"] == "insight" and not review_complete
        )
        awaiting_adjudication = all_five and row["final_set_worthy"] is None
        aggregate["review_complete"] += int(review_complete)
        aggregate["all_five_pass"] += int(all_five)
        aggregate["awaiting_adjudication"] += int(awaiting_adjudication)
        aggregate["incomplete_evaluations"] += int(incomplete)
        day = str(row["day"])
        audience = str(row["audience"])
        sample_kind = str(row["sample_kind"])
        diagnosis_counts = (
            triage_counts[audience]
            if sample_kind == "dropped"
            else day_counts[(day, audience)]
        )
        diagnosis_counts["awaiting_adjudication"] += int(awaiting_adjudication)
        diagnosis_counts["incomplete_evaluations"] += int(incomplete)
        miss = _is_final_set_miss(row)
        if not miss:
            continue
        aggregate["final_set_worthy_misses"] += 1
        high_consequence = int(row["high_consequence"] or 0) == 1
        aggregate["high_consequence_misses"] += int(high_consequence)
        band = str(row["band"])
        if sample_kind == "dropped":
            triage_counts[audience]["false_negatives"] += 1
            triage_counts[audience]["high_consequence_false_negatives"] += int(
                high_consequence
            )
            continue
        if band == KEPT_51_75:
            field = "kept_51_75_misses"
            pattern = "kept_51_75"
        elif band == KEPT_76_100:
            field = "kept_76_100_misses"
            pattern = "kept_76_100_or_x_article"
        elif band == X_ARTICLE_51_100:
            field = "x_article_51_100_misses"
            pattern = "kept_76_100_or_x_article"
        else:
            continue
        day_counts[(day, audience)][field] += 1
        systemic_days.setdefault((audience, pattern), set()).add(day)

    def diagnosis_status(counts: Mapping[str, Any]) -> str:
        if int(counts["incomplete_evaluations"]) > 0:
            return "unknown_incomplete_evaluation"
        if int(counts["awaiting_adjudication"]) > 0:
            return "pending_adjudication"
        return "complete"

    for aggregate in strata.values():
        status = diagnosis_status(aggregate)
        aggregate["diagnosis_status"] = status
        if status != "complete":
            aggregate["final_set_worthy_misses"] = None
            aggregate["high_consequence_misses"] = None

    by_day_audience = []
    for (day, audience), counts in sorted(day_counts.items()):
        status = diagnosis_status(counts)
        if status != "complete":
            rank_limit = None
            published_counts = {
                "kept_51_75_misses": None,
                "kept_76_100_misses": None,
                "x_article_51_100_misses": None,
            }
        elif counts["kept_76_100_misses"] or counts["x_article_51_100_misses"]:
            rank_limit = 100
            published_counts = {
                field: counts[field]
                for field in (
                    "kept_51_75_misses",
                    "kept_76_100_misses",
                    "x_article_51_100_misses",
                )
            }
        elif counts["kept_51_75_misses"]:
            rank_limit = 75
            published_counts = {
                field: counts[field]
                for field in (
                    "kept_51_75_misses",
                    "kept_76_100_misses",
                    "x_article_51_100_misses",
                )
            }
        else:
            rank_limit = 50
            published_counts = {
                field: counts[field]
                for field in (
                    "kept_51_75_misses",
                    "kept_76_100_misses",
                    "x_article_51_100_misses",
                )
            }
        by_day_audience.append(
            {
                "day": day,
                "audience": audience,
                **published_counts,
                "awaiting_adjudication": counts["awaiting_adjudication"],
                "incomplete_evaluations": counts["incomplete_evaluations"],
                "diagnosis_status": status,
                "recommended_rank_limit": rank_limit,
            }
        )
    audience_widening_status = {
        audience: (
            "unknown_incomplete_evaluation"
            if any(
                row["diagnosis_status"] == "unknown_incomplete_evaluation"
                for row in by_day_audience
                if row["audience"] == audience
            )
            else "pending_adjudication"
            if any(
                row["diagnosis_status"] == "pending_adjudication"
                for row in by_day_audience
                if row["audience"] == audience
            )
            else "complete"
        )
        for audience in AUDIENCES
    }
    systemic = []
    for (audience, pattern), failure_days in sorted(systemic_days.items()):
        if audience_widening_status[audience] != "complete" or len(failure_days) < 3:
            continue
        systemic.append(
            {
                "audience": audience,
                "pattern": pattern,
                "failure_days": sorted(failure_days),
                "failure_day_count": len(failure_days),
                "recommended_rank_limit_all_days": (
                    75 if pattern == "kept_51_75" else 100
                ),
            }
        )
    triage = []
    for audience, counts in sorted(triage_counts.items()):
        status = diagnosis_status(counts)
        if status != "complete":
            triage.append(
                {
                    "audience": audience,
                    "false_negatives": None,
                    "high_consequence_false_negatives": None,
                    "ordinary_false_negatives": None,
                    "awaiting_adjudication": counts["awaiting_adjudication"],
                    "incomplete_evaluations": counts["incomplete_evaluations"],
                    "diagnosis_status": status,
                    "second_frozen_sample_required": None,
                    "trigger": None,
                }
            )
            continue
        high = counts["high_consequence_false_negatives"]
        ordinary = counts["false_negatives"] - high
        triggered = high >= 1 or ordinary >= 2
        triage.append(
            {
                "audience": audience,
                **counts,
                "ordinary_false_negatives": ordinary,
                "diagnosis_status": status,
                "second_frozen_sample_required": triggered,
                "trigger": (
                    "high_consequence_false_negative"
                    if high >= 1
                    else "two_ordinary_false_negatives"
                    if ordinary >= 2
                    else None
                ),
            }
        )
    return {
        "strata": list(strata.values()),
        "widening": {
            "diagnosis_status_by_audience": [
                {
                    "audience": audience,
                    "diagnosis_status": audience_widening_status[audience],
                }
                for audience in sorted(AUDIENCES)
            ],
            "thresholds": {
                "kept_51_75_misses_for_top_75": 1,
                "kept_76_100_or_article_misses_for_top_100": 1,
                "same_pattern_days_for_all_days": 3,
            },
            "by_day_audience": by_day_audience,
            "systemic": systemic,
        },
        "triage_diagnosis": triage,
    }


def summary(conn: sqlite3.Connection) -> dict[str, Any]:
    meta = conn.execute("SELECT * FROM recall_run WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("recall audit has not been frozen")
    sample_counts = [
        dict(row)
        for row in conn.execute(
            """SELECT band, sample_kind, COUNT(*) AS count
               FROM recall_sample GROUP BY band, sample_kind ORDER BY band"""
        )
    ]
    evaluation_counts = [
        dict(row)
        for row in conn.execute(
            """SELECT evaluation.audience,
                      COUNT(*) AS total,
                      SUM(extraction_status = 'pending') AS extraction_pending,
                      SUM(extraction_status = 'complete') AS extraction_complete,
                      SUM(extraction_status = 'failed') AS extraction_failed,
                      SUM(extraction_status = 'rejected') AS extraction_rejected,
                      SUM(no_insight = 1) AS no_insight,
                      SUM(citation_terminal_failure = 1) AS citation_terminal,
                      SUM(schema_terminal_failure = 1) AS schema_terminal,
                      SUM(review_status = 'pending' AND
                          extraction_status = 'complete' AND
                          outcome = 'insight') AS review_pending,
                      SUM(review_status = 'complete') AS review_complete,
                      SUM(review_status = 'failed') AS review_failed,
                      SUM(claim_fidelity = 1) AS claim_fidelity,
                      SUM(epistemic_discipline = 1) AS epistemic_discipline,
                      SUM(audience_useful = 1) AS useful,
                      SUM(actionable = 1) AS actionable,
                      SUM(specific = 1) AS specific,
                      CASE WHEN SUM(review_status = 'complete' AND
                                         claim_fidelity = 1 AND
                                         epistemic_discipline = 1 AND
                                         audience_useful = 1 AND actionable = 1 AND
                                         specific = 1 AND final_set_worthy IS NULL) > 0
                           THEN NULL
                           ELSE SUM(CASE WHEN final_set_worthy = 1 THEN 1 ELSE 0 END)
                      END AS final_set_worthy,
                      SUM(final_set_worthy IS NULL AND review_status = 'complete'
                          AND claim_fidelity = 1 AND epistemic_discipline = 1
                          AND audience_useful = 1 AND actionable = 1
                          AND specific = 1) AS awaiting_adjudication,
                      CASE WHEN SUM(sample.sample_kind != 'dropped' AND
                                         (extraction_status != 'complete' OR
                                          (outcome = 'insight' AND
                                           review_status != 'complete') OR
                                          (review_status = 'complete' AND
                                           claim_fidelity = 1 AND
                                           epistemic_discipline = 1 AND
                                           audience_useful = 1 AND actionable = 1 AND
                                           specific = 1 AND
                                           final_set_worthy IS NULL))) > 0
                           THEN NULL
                           ELSE SUM(final_set_worthy = 1 AND
                                    sample.sample_kind != 'dropped' AND
                                    citation_valid = 1 AND audience_useful = 1 AND
                                    claim_fidelity = 1 AND
                                    epistemic_discipline = 1 AND actionable = 1 AND
                                    specific = 1 AND redundant = 0)
                      END AS useful_misses,
                      CASE WHEN SUM(sample.sample_kind = 'dropped' AND
                                         (extraction_status != 'complete' OR
                                          (outcome = 'insight' AND
                                           review_status != 'complete') OR
                                          (review_status = 'complete' AND
                                           claim_fidelity = 1 AND
                                           epistemic_discipline = 1 AND
                                           audience_useful = 1 AND actionable = 1 AND
                                           specific = 1 AND
                                           final_set_worthy IS NULL))) > 0
                           THEN NULL
                           ELSE SUM(final_set_worthy = 1 AND
                                    sample.sample_kind = 'dropped' AND
                                    citation_valid = 1 AND audience_useful = 1 AND
                                    claim_fidelity = 1 AND
                                    epistemic_discipline = 1 AND actionable = 1 AND
                                    specific = 1 AND redundant = 0)
                      END AS triage_false_negatives
               FROM recall_audience_evaluation AS evaluation
               JOIN recall_sample AS sample USING (sample_id)
               GROUP BY evaluation.audience ORDER BY evaluation.audience"""
        )
    ]
    attempts = dict(
        conn.execute(
            """SELECT COUNT(*) AS count,
                      SUM(COALESCE(input_tokens, 0)) AS input_tokens,
                      SUM(COALESCE(cached_tokens, 0)) AS cached_tokens,
                      SUM(COALESCE(output_tokens, 0)) AS output_tokens,
                      SUM(COALESCE(reported_cost_usd, 0)) AS reported_cost_usd
               FROM recall_attempt"""
        ).fetchone()
    )
    analysis = _recall_analysis(conn, days=tuple(json.loads(meta["days_json"])))
    return {
        "run": dict(meta),
        "samples": sample_counts,
        "evaluations": evaluation_counts,
        "replacements": int(
            conn.execute("SELECT COUNT(*) FROM recall_replacement").fetchone()[0]
        ),
        "attempts": attempts,
        **analysis,
    }


def _result(command: str, data: Any) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "command": command,
        "status": "ok",
        "data": data,
        "error": None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m fli.audience_insight_recall")
    sub = parser.add_subparsers(dest="action", required=True)
    freeze_parser = sub.add_parser("freeze")
    freeze_parser.add_argument("--run-db", type=Path, required=True)
    freeze_parser.add_argument("--run-id", required=True)
    freeze_parser.add_argument("--day", action="append", choices=DAYS)
    freeze_parser.add_argument("--artifact-db", type=Path, default=DEFAULT_ARTIFACT_DB)
    summary_parser = sub.add_parser("summary")
    summary_parser.add_argument("--run-db", type=Path, required=True)
    export_parser = sub.add_parser("adjudication-export")
    export_parser.add_argument("--run-db", type=Path, required=True)
    export_parser.add_argument("--output", type=Path, required=True)
    import_parser = sub.add_parser("adjudication-import")
    import_parser.add_argument("--run-db", type=Path, required=True)
    import_parser.add_argument("--input", type=Path, required=True)
    for action in ("extract", "review"):
        action_parser = sub.add_parser(action)
        action_parser.add_argument("--run-db", type=Path, required=True)
        action_parser.add_argument("--audience", action="append", choices=AUDIENCES)
        action_parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
        action_parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args(argv)
    started = time.monotonic()
    command = f"audience-insight-recall.{args.action}"
    conn: sqlite3.Connection | None = None
    try:
        conn = connect(args.run_db)
        if args.action == "freeze":
            freeze_audit(
                conn,
                run_id=args.run_id,
                days=tuple(args.day or DAYS),
                artifact_db=args.artifact_db,
            )
            data = summary(conn)
            data["will_call_model"] = False
        elif args.action == "summary":
            data = summary(conn)
        elif args.action == "adjudication-export":
            payload = export_adjudication_batch(conn)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(_canonical_json(payload) + "\n")
            data = {
                "output": args.output.resolve().as_posix(),
                "row_count": payload["expected_row_count"],
                "evaluation_set_sha256": payload["evaluation_set_sha256"],
                "will_call_model": False,
            }
        elif args.action == "adjudication-import":
            payload = json.loads(args.input.read_text())
            imported = import_adjudication_batch(conn, payload)
            data = summary(conn)
            data["imported_adjudications"] = imported
            data["will_call_model"] = False
        else:
            client = entity_kinds.create_litellm_client()
            if hasattr(client, "with_options"):
                client = client.with_options(max_retries=0, timeout=300.0)
            audiences = tuple(args.audience or AUDIENCES)
            if args.action == "extract":
                data = run_extractions(
                    conn,
                    client=client,
                    audiences=audiences,
                    workers=args.workers,
                    retry_failed=args.retry_failed,
                )
            else:
                data = run_reviews(
                    conn,
                    client=client,
                    audiences=audiences,
                    workers=args.workers,
                    retry_failed=args.retry_failed,
                )
        data["duration_ms"] = round((time.monotonic() - started) * 1000)
        print(_canonical_json(_result(command, data)))
        return 0
    except (FileNotFoundError, RuntimeError, sqlite3.Error, ValueError) as exc:
        print(
            _canonical_json(
                {
                    "schema_version": "1.0",
                    "command": command,
                    "status": "error",
                    "data": None,
                    "error": {
                        "code": "E_INVALID_INPUT",
                        "message": str(exc),
                    },
                }
            )
        )
        return 2
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
