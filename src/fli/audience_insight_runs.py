"""Resumable per-day, per-audience execution for Audience Insights v2.

The run database is the publication boundary.  Frozen evidence packets are
immutable, extraction writes only mechanically verified candidates, and the
daily editor may select runner-owned candidate IDs without rewriting their
content.  Investment and AI Engineering runs intentionally live in separate
databases even when they consume the same evidence cohort.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import sqlite3
import sys
import time
from collections import deque
from collections.abc import Mapping
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from fli import (
    artifacts,
    audience_insight_evaluations,
    audience_insight_publication_audit,
    audience_insights,
    entity_kinds,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_ROOT = REPO_ROOT / "data" / "derived" / "audience-insights-v2"
DEFAULT_TRIAGE_ROOT = (
    REPO_ROOT / "data" / "derived" / "cited-insights" / "triage"
)
DEFAULT_ARTIFACT_DB = artifacts.DEFAULT_DB
DEFAULT_RANK_LIMIT = 50
DEFAULT_WORKERS = 16
DEFAULT_REVIEW_WORKERS = 5
DEFAULT_PROGRESS_EVERY = 10
MAX_EXTRACTION_ATTEMPTS = 2
CANONICAL_TRIAGE_PREFIX = "triage-v2.2-canonical-v8"
ADJACENT_PUBLICATION_AUDIT = Path("publication-audit-v1") / "audit.db"
HISTORY_MODES = ("auto", "explicit", "none")


SCHEMA = """
CREATE TABLE IF NOT EXISTS run_meta (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    run_id TEXT NOT NULL,
    audience TEXT NOT NULL CHECK (audience IN ('investment', 'ai_engineering')),
    day TEXT NOT NULL,
    model TEXT NOT NULL,
    reasoning_effort TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    prompt_sha256 TEXT NOT NULL,
    input_render_version TEXT NOT NULL CHECK (
        input_render_version IN (
            'verbatim-v1',
            'provider-safe-v2',
            'citation-safe-v3'
        )
    ),
    schema_version TEXT NOT NULL,
    editor_model TEXT NOT NULL,
    editor_reasoning_effort TEXT NOT NULL,
    editor_prompt_version TEXT NOT NULL,
    editor_prompt_sha256 TEXT NOT NULL,
    editor_schema_version TEXT NOT NULL,
    review_model TEXT NOT NULL,
    review_reasoning_effort TEXT NOT NULL,
    item_review_prompt_version TEXT NOT NULL,
    item_review_prompt_sha256 TEXT NOT NULL,
    item_review_schema_version TEXT NOT NULL,
    day_review_prompt_version TEXT NOT NULL,
    day_review_prompt_sha256 TEXT NOT NULL,
    day_review_schema_version TEXT NOT NULL,
    source_triage_db TEXT NOT NULL,
    source_artifact_db TEXT NOT NULL,
    rank_limit INTEGER NOT NULL,
    event_ids_json TEXT NOT NULL,
    cohort_sha256 TEXT NOT NULL,
    expected_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidate_item (
    candidate_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    day TEXT NOT NULL,
    feed_rank INTEGER NOT NULL,
    packet_json TEXT NOT NULL,
    input_text TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    prompt_cache_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'complete', 'failed', 'rejected')),
    attempts INTEGER NOT NULL DEFAULT 0,
    outcome TEXT CHECK (
        outcome IS NULL OR outcome IN ('insight', 'no_extractable_insight')
    ),
    no_insight_reason TEXT,
    claim TEXT,
    claim_posture TEXT,
    why_it_matters TEXT,
    audience_fields_json TEXT,
    supporting_quote TEXT,
    citation_block_index INTEGER,
    citation_source_type TEXT,
    citation_source_id TEXT,
    citation_source_url TEXT,
    citation_source_author TEXT,
    citation_source_title TEXT,
    citation_source_sha256 TEXT,
    citation_section_ordinal INTEGER,
    citation_char_start INTEGER,
    citation_char_end INTEGER,
    citation_global_matching_block_count INTEGER,
    response_id TEXT,
    response_model TEXT,
    input_tokens INTEGER,
    cached_tokens INTEGER,
    cache_write_tokens INTEGER,
    output_tokens INTEGER,
    reported_cost_usd REAL,
    request_tags_json TEXT,
    raw_output_text TEXT,
    error_type TEXT,
    error_message TEXT,
    terminal_reason TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audience_candidate_status_rank
    ON candidate_item(status, feed_rank, event_id);
CREATE INDEX IF NOT EXISTS idx_audience_candidate_outcome_rank
    ON candidate_item(outcome, feed_rank, event_id);
CREATE INDEX IF NOT EXISTS idx_audience_candidate_cache_key
    ON candidate_item(prompt_cache_key, status, feed_rank, event_id);

CREATE TABLE IF NOT EXISTS candidate_attempt (
    candidate_id TEXT NOT NULL
        REFERENCES candidate_item(candidate_id) ON DELETE RESTRICT,
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
    PRIMARY KEY (candidate_id, attempt_number)
);

CREATE TABLE IF NOT EXISTS editor_run (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'complete', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    candidate_set_sha256 TEXT NOT NULL,
    history_sha256 TEXT NOT NULL,
    prior_selected_json TEXT NOT NULL,
    input_text TEXT NOT NULL,
    prompt_cache_key TEXT NOT NULL,
    selected_count INTEGER,
    thin_day_reason TEXT,
    response_id TEXT,
    response_model TEXT,
    input_tokens INTEGER,
    cached_tokens INTEGER,
    cache_write_tokens INTEGER,
    output_tokens INTEGER,
    reported_cost_usd REAL,
    request_tags_json TEXT,
    raw_output_text TEXT,
    error_type TEXT,
    error_message TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_selection (
    editorial_rank INTEGER PRIMARY KEY CHECK (editorial_rank BETWEEN 1 AND 5),
    candidate_id TEXT NOT NULL UNIQUE
        REFERENCES candidate_item(candidate_id) ON DELETE RESTRICT,
    decision_value TEXT NOT NULL,
    audit_reason TEXT NOT NULL,
    updates_prior_id TEXT
);

-- The editor's ordered shortlist above is immutable provenance.  Publication
-- normally mirrors it, but a single structured padding reconciliation may
-- remove only its lowest-ranked item without rewriting the editor result.
CREATE TABLE IF NOT EXISTS publication_selection (
    publication_rank INTEGER PRIMARY KEY CHECK (publication_rank BETWEEN 1 AND 5),
    original_editorial_rank INTEGER NOT NULL UNIQUE
        CHECK (original_editorial_rank BETWEEN 1 AND 5),
    candidate_id TEXT NOT NULL UNIQUE
        REFERENCES candidate_item(candidate_id) ON DELETE RESTRICT,
    activated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS suppressed_duplicate (
    candidate_id TEXT PRIMARY KEY
        REFERENCES candidate_item(candidate_id) ON DELETE RESTRICT,
    duplicate_of_id TEXT NOT NULL,
    duplicate_scope TEXT NOT NULL CHECK (
        duplicate_scope IN ('same_day', 'cross_day')
    ),
    audit_reason TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS item_review (
    candidate_id TEXT PRIMARY KEY
        REFERENCES candidate_item(candidate_id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'complete', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    input_text TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    prompt_cache_key TEXT NOT NULL,
    claim_fidelity TEXT,
    epistemic_discipline TEXT,
    audience_usefulness TEXT,
    actionability TEXT,
    specificity TEXT,
    failure_codes_json TEXT,
    rationale TEXT,
    response_id TEXT,
    response_model TEXT,
    input_tokens INTEGER,
    cached_tokens INTEGER,
    cache_write_tokens INTEGER,
    output_tokens INTEGER,
    reported_cost_usd REAL,
    request_tags_json TEXT,
    raw_output_text TEXT,
    error_type TEXT,
    error_message TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS day_set_review (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'complete', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    input_text TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    prompt_cache_key TEXT NOT NULL,
    duplicate_pairs_json TEXT,
    padding_detected INTEGER,
    thin_day_honest INTEGER,
    set_rationale TEXT,
    response_id TEXT,
    response_model TEXT,
    input_tokens INTEGER,
    cached_tokens INTEGER,
    cache_write_tokens INTEGER,
    output_tokens INTEGER,
    reported_cost_usd REAL,
    request_tags_json TEXT,
    raw_output_text TEXT,
    error_type TEXT,
    error_message TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS selection_reconciliation (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    status TEXT NOT NULL CHECK (status IN ('pending', 'complete', 'failed')),
    reason_code TEXT NOT NULL CHECK (reason_code = 'padding_tail_trim'),
    source_review_input_sha256 TEXT NOT NULL,
    source_review_response_id TEXT,
    original_selected_ids_json TEXT NOT NULL,
    active_selected_ids_json TEXT NOT NULL,
    removed_candidate_id TEXT NOT NULL
        REFERENCES candidate_item(candidate_id) ON DELETE RESTRICT,
    removed_editorial_rank INTEGER NOT NULL
        CHECK (removed_editorial_rank BETWEEN 1 AND 5),
    error_type TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reconciled_day_set_review (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'complete', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    reconciliation_reason TEXT NOT NULL
        CHECK (reconciliation_reason = 'padding_tail_trim'),
    source_review_input_sha256 TEXT NOT NULL,
    input_text TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    prompt_cache_key TEXT NOT NULL,
    duplicate_pairs_json TEXT,
    padding_detected INTEGER,
    thin_day_honest INTEGER,
    set_rationale TEXT,
    response_id TEXT,
    response_model TEXT,
    input_tokens INTEGER,
    cached_tokens INTEGER,
    cache_write_tokens INTEGER,
    output_tokens INTEGER,
    reported_cost_usd REAL,
    request_tags_json TEXT,
    raw_output_text TEXT,
    error_type TEXT,
    error_message TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quality_gate (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    passed INTEGER NOT NULL,
    result_json TEXT NOT NULL,
    computed_at TEXT NOT NULL
);

-- Clean migration for pre-reconciliation run stores: seed the active set once
-- from the immutable editor selection.  Once reconciliation exists, reopening
-- the database can never restore the trimmed tail.
INSERT INTO publication_selection
    (publication_rank, original_editorial_rank, candidate_id, activated_at)
SELECT editorial_rank, editorial_rank, candidate_id,
       COALESCE(
           (SELECT completed_at FROM editor_run WHERE singleton = 1),
           CURRENT_TIMESTAMP
       )
FROM daily_selection
WHERE NOT EXISTS (SELECT 1 FROM publication_selection)
  AND NOT EXISTS (SELECT 1 FROM selection_reconciliation)
ORDER BY editorial_rank;
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def _safe_slug(value: str, *, name: str) -> str:
    if not value or any(
        character
        not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        for character in value
    ):
        raise ValueError(
            f"{name} may contain only letters, numbers, '-', '_', and '.'"
        )
    return value


def default_run_db(*, day: str, audience: str, run_id: str) -> Path:
    audience_insights.require_audience(audience)
    _safe_slug(day, name="day")
    _safe_slug(run_id, name="run_id")
    return DEFAULT_RUN_ROOT / day / audience / run_id / "insights.db"


def canonical_triage_db(day: str) -> Path:
    return (
        DEFAULT_TRIAGE_ROOT
        / f"{CANONICAL_TRIAGE_PREFIX}-{day}-top1000"
        / "triage.db"
    )


def connect_run(path: Path | str) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.executescript(SCHEMA)
    return conn


def declared_input_render_version(conn: sqlite3.Connection) -> str:
    """Return the declared model-input renderer, classifying pre-column runs."""
    columns = {
        str(row[1]) for row in conn.execute("PRAGMA table_info(run_meta)").fetchall()
    }
    if "input_render_version" not in columns:
        return audience_insights.INPUT_RENDER_VERBATIM_V1
    row = conn.execute(
        "SELECT input_render_version FROM run_meta WHERE singleton = 1"
    ).fetchone()
    if row is None:
        return audience_insights.DEFAULT_INPUT_RENDER_VERSION
    return audience_insights.require_input_render_version(
        str(row["input_render_version"])
    )


def _open_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(path)
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _x_url(author: str | None, post_id: str) -> str:
    handle = (author or "i").removeprefix("@")
    return f"https://x.com/{handle}/status/{post_id}"


def _source_payload(source: audience_insights.EvidenceSource) -> dict[str, Any]:
    return asdict(source)


def _source_from_payload(payload: dict[str, Any]) -> audience_insights.EvidenceSource:
    return audience_insights.EvidenceSource(**payload)


def _packet_payload(packet: audience_insights.EvidencePacket) -> dict[str, Any]:
    return {
        "event_id": packet.event_id,
        "day": packet.day,
        "feed_rank": packet.feed_rank,
        "sources": [_source_payload(source) for source in packet.sources],
    }


def _packet_from_payload(payload: dict[str, Any]) -> audience_insights.EvidencePacket:
    return audience_insights.EvidencePacket(
        event_id=str(payload["event_id"]),
        day=str(payload["day"]),
        feed_rank=int(payload["feed_rank"]),
        sources=tuple(_source_from_payload(source) for source in payload["sources"]),
    )


def _x_source(post: dict[str, Any], *, relation: str) -> audience_insights.EvidenceSource:
    post_id = str(post["post_id"])
    author = str(post.get("author") or "") or None
    return audience_insights.EvidenceSource(
        source_type="x_post",
        source_id=post_id,
        url=_x_url(author, post_id),
        text=str(post.get("text") or ""),
        author=author,
        relation=relation,
    )


def _section_text(
    text: str,
    *,
    max_chars: int = 60_000,
) -> list[tuple[int, int, str]]:
    """Return deterministic verbatim sections without inventing source text."""
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    if len(text) <= max_chars:
        return [(0, len(text), text)]
    sections: list[tuple[int, int, str]] = []
    start = 0
    while start < len(text):
        target = min(start + max_chars, len(text))
        end = target
        if target < len(text):
            boundary = text.rfind("\n\n", start + max_chars // 2, target)
            if boundary > start:
                end = boundary
        if end <= start:
            end = target
        sections.append((start, end, text[start:end]))
        start = end
        while start < len(text) and text[start] == "\n":
            start += 1
    return sections


def _artifact_sources(
    artifact_conn: sqlite3.Connection,
    *,
    event_id: str,
    max_total_chars: int = 600_000,
) -> list[audience_insights.EvidenceSource]:
    artifact_ids = {
        str(row["artifact_id"])
        for row in artifact_conn.execute(
            """SELECT DISTINCT artifact_id
               FROM artifact_import_candidate
               WHERE event_id = ? AND decision = 'accepted'
                 AND artifact_id IS NOT NULL""",
            (event_id,),
        ).fetchall()
    }
    has_supplements = artifact_conn.execute(
        """SELECT 1 FROM sqlite_master
           WHERE type = 'table' AND name = 'artifact_event_supplement'"""
    ).fetchone()
    if has_supplements is not None:
        artifact_ids.update(
            str(row["artifact_id"])
            for row in artifact_conn.execute(
                """SELECT DISTINCT artifact_id
                   FROM artifact_event_supplement WHERE event_id = ?""",
                (event_id,),
            ).fetchall()
        )
    if not artifact_ids:
        return []
    placeholders = ",".join("?" for _ in artifact_ids)
    rows = artifact_conn.execute(
        f"""SELECT DISTINCT a.artifact_id, a.canonical_url, a.title,
                          latest.text_snapshot_ref, latest.text_sha256
           FROM artifact AS a
           JOIN artifact_fetch AS latest ON latest.fetch_id = (
               SELECT fetch.fetch_id
               FROM artifact_fetch AS fetch
               WHERE fetch.artifact_id = a.artifact_id
                 AND fetch.status = 'success'
                 AND fetch.text_snapshot_ref IS NOT NULL
               ORDER BY fetch.completed_at DESC, fetch.fetch_id DESC
               LIMIT 1
           )
           WHERE a.artifact_id IN ({placeholders})
           ORDER BY a.artifact_id""",
        tuple(sorted(artifact_ids)),
    ).fetchall()
    sources: list[audience_insights.EvidenceSource] = []
    included = 0
    for row in rows:
        snapshot_path = REPO_ROOT / str(row["text_snapshot_ref"])
        if not snapshot_path.is_file():
            continue
        text = snapshot_path.read_text()
        source_sha256 = str(row["text_sha256"] or _sha256(text))
        sections = _section_text(text)
        for ordinal, (start, end, section) in enumerate(sections, start=1):
            if included and included + len(section) > max_total_chars:
                return sources
            sources.append(
                audience_insights.EvidenceSource(
                    source_type="artifact",
                    source_id=str(row["artifact_id"]),
                    url=str(row["canonical_url"]),
                    title=str(row["title"] or "") or None,
                    text=section,
                    relation=(
                        "optional_strengthening"
                        if len(sections) == 1
                        else "article_section"
                    ),
                    source_sha256=source_sha256,
                    section_ordinal=ordinal if len(sections) > 1 else None,
                    source_char_start=start,
                    source_char_end=end,
                )
            )
            included += len(section)
    return sources


def _packet_from_row(
    row: sqlite3.Row,
    *,
    artifact_conn: sqlite3.Connection,
) -> audience_insights.EvidencePacket:
    envelope = json.loads(row["envelope_json"])
    root = dict(envelope["root"])
    sources = [_x_source(root, relation="root")]
    for related in envelope.get("related_posts") or []:
        item = dict(related)
        sources.append(
            _x_source(item, relation=str(item.get("relation") or "related"))
        )
    sources.extend(_artifact_sources(artifact_conn, event_id=str(row["event_id"])))
    return audience_insights.EvidencePacket(
        event_id=str(row["event_id"]),
        day=str(envelope["day"]),
        feed_rank=int(row["current_rank"]),
        sources=tuple(sources),
    )


def _candidate_id(day: str, audience: str, event_id: str) -> str:
    digest = _sha256(f"{day}:{audience}:{event_id}")[:20]
    return f"candidate-{digest}"


def freeze_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    audience: str,
    day: str,
    rank_limit: int = DEFAULT_RANK_LIMIT,
    event_ids: Iterable[str] | None = None,
    triage_db: Path | None = None,
    artifact_db: Path = DEFAULT_ARTIFACT_DB,
    model: str = audience_insights.DEFAULT_MODEL,
    effort: str | None = None,
    editor_model: str = audience_insights.DEFAULT_MODEL,
    editor_effort: str = audience_insights.DEFAULT_EDITOR_EFFORT,
    review_model: str = audience_insight_evaluations.DEFAULT_MODEL,
    review_effort: str = audience_insight_evaluations.DEFAULT_REASONING_EFFORT,
    input_render_version: str | None = None,
) -> int:
    audience = audience_insights.require_audience(audience)
    effort = (
        audience_insights.default_extraction_effort(audience)
        if effort is None
        else effort
    )
    if rank_limit < 1:
        raise ValueError("rank_limit must be positive")
    triage_path = triage_db or canonical_triage_db(day)
    frozen_ids = tuple(dict.fromkeys(event_ids or ()))
    triage_conn = _open_readonly(triage_path)
    artifact_conn = _open_readonly(artifact_db)
    try:
        parameters: list[Any] = [rank_limit]
        where = (
            "status = 'complete' AND decision = 'keep' AND current_rank <= ?"
        )
        if frozen_ids:
            where += " AND event_id IN (" + ",".join("?" for _ in frozen_ids) + ")"
            parameters.extend(frozen_ids)
        rows = triage_conn.execute(
            f"""SELECT event_id, current_rank, envelope_json
                FROM triage_item
                WHERE {where}
                ORDER BY current_rank, event_id""",
            parameters,
        ).fetchall()
        if frozen_ids:
            found = {str(row["event_id"]) for row in rows}
            missing = sorted(set(frozen_ids) - found)
            if missing:
                raise ValueError(
                    "requested events are not completed kept rows within rank limit: "
                    + ", ".join(missing)
                )
        if not rows:
            raise ValueError("no completed kept candidates matched the frozen cohort")
        packets = [
            _packet_from_row(row, artifact_conn=artifact_conn) for row in rows
        ]
    finally:
        triage_conn.close()
        artifact_conn.close()

    cohort = [_packet_payload(packet) for packet in packets]
    event_ids_json = _canonical_json([packet.event_id for packet in packets])
    cohort_sha256 = _sha256(_canonical_json(cohort))
    contract = audience_insights.contract(audience)
    existing = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    requested_render_version = (
        audience_insights.require_input_render_version(input_render_version)
        if input_render_version is not None
        else None
    )
    if existing is None:
        resolved_render_version = (
            requested_render_version
            or audience_insights.DEFAULT_INPUT_RENDER_VERSION
        )
    else:
        resolved_render_version = declared_input_render_version(conn)
        if (
            requested_render_version is not None
            and requested_render_version != resolved_render_version
        ):
            raise ValueError(
                "run database does not match the frozen request: "
                "input_render_version"
            )
    expected = {
        "run_id": run_id,
        "audience": audience,
        "day": day,
        "model": model,
        "reasoning_effort": effort,
        "prompt_version": contract.prompt_version,
        "prompt_sha256": audience_insights.prompt_sha256(audience),
        "schema_version": contract.schema_version,
        "editor_model": editor_model,
        "editor_reasoning_effort": editor_effort,
        "editor_prompt_version": contract.editor_prompt_version,
        "editor_prompt_sha256": audience_insights.editor_prompt_sha256(audience),
        "editor_schema_version": audience_insights.EDITOR_SCHEMA_VERSION,
        "review_model": review_model,
        "review_reasoning_effort": review_effort,
        "item_review_prompt_version": (
            audience_insight_evaluations.item_prompt_version(audience)
        ),
        "item_review_prompt_sha256": (
            audience_insight_evaluations.item_prompt_sha256(audience)
        ),
        "item_review_schema_version": (
            audience_insight_evaluations.ITEM_SCHEMA_VERSION
        ),
        "day_review_prompt_version": (
            audience_insight_evaluations.DAY_SET_PROMPT_VERSION
        ),
        "day_review_prompt_sha256": (
            audience_insight_evaluations.day_set_prompt_sha256()
        ),
        "day_review_schema_version": (
            audience_insight_evaluations.DAY_SET_SCHEMA_VERSION
        ),
        "rank_limit": rank_limit,
        "event_ids_json": event_ids_json,
        "cohort_sha256": cohort_sha256,
        "expected_count": len(packets),
    }
    if existing is not None:
        mismatches = [key for key, value in expected.items() if existing[key] != value]
        if mismatches:
            raise ValueError(
                "run database does not match the frozen request: "
                + ", ".join(mismatches)
            )
        return int(existing["expected_count"])

    now = _now()
    rendered_packets = [
        (
            packet,
            audience_insights.render_model_input(
                packet,
                version=resolved_render_version,
            ),
        )
        for packet in packets
    ]
    with conn:
        conn.execute(
            """INSERT INTO run_meta
               (singleton, run_id, audience, day, model, reasoning_effort,
                prompt_version, prompt_sha256, input_render_version,
                schema_version,
                editor_model, editor_reasoning_effort, editor_prompt_version,
                editor_prompt_sha256, editor_schema_version,
                review_model, review_reasoning_effort,
                item_review_prompt_version, item_review_prompt_sha256,
                item_review_schema_version, day_review_prompt_version,
                day_review_prompt_sha256, day_review_schema_version,
                source_triage_db, source_artifact_db, rank_limit,
                event_ids_json, cohort_sha256, expected_count,
                created_at, updated_at)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                audience,
                day,
                model,
                effort,
                contract.prompt_version,
                audience_insights.prompt_sha256(audience),
                resolved_render_version,
                contract.schema_version,
                editor_model,
                editor_effort,
                contract.editor_prompt_version,
                audience_insights.editor_prompt_sha256(audience),
                audience_insights.EDITOR_SCHEMA_VERSION,
                review_model,
                review_effort,
                audience_insight_evaluations.item_prompt_version(audience),
                audience_insight_evaluations.item_prompt_sha256(audience),
                audience_insight_evaluations.ITEM_SCHEMA_VERSION,
                audience_insight_evaluations.DAY_SET_PROMPT_VERSION,
                audience_insight_evaluations.day_set_prompt_sha256(),
                audience_insight_evaluations.DAY_SET_SCHEMA_VERSION,
                _display_path(triage_path),
                _display_path(artifact_db),
                rank_limit,
                event_ids_json,
                cohort_sha256,
                len(packets),
                now,
                now,
            ),
        )
        conn.executemany(
            """INSERT INTO candidate_item
               (candidate_id, event_id, day, feed_rank, packet_json, input_text,
                input_sha256, prompt_cache_key, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    _candidate_id(day, audience, packet.event_id),
                    packet.event_id,
                    packet.day,
                    packet.feed_rank,
                    _canonical_json(_packet_payload(packet)),
                    input_text,
                    _sha256(input_text),
                    audience_insights.prompt_cache_key(audience, packet.event_id),
                    now,
                )
                for packet, input_text in rendered_packets
            ],
        )
    return len(packets)


def _store_success(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    result: dict[str, Any],
) -> None:
    citation = result.get("citation") or {}
    analysis = result.get("audience_fields") or {}
    now = _now()
    with conn:
        conn.execute(
            """INSERT INTO candidate_attempt
               (candidate_id, attempt_number, status, result_json,
                raw_output_text, response_id, response_model, input_tokens,
                cached_tokens, cache_write_tokens, output_tokens,
                reported_cost_usd, request_tags_json, created_at)
               VALUES (?, ?, 'complete', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row["candidate_id"],
                int(row["attempts"]) + 1,
                _canonical_json(result),
                result.get("raw_output_text"),
                result.get("response_id"),
                result.get("response_model"),
                result.get("input_tokens"),
                result.get("cached_tokens"),
                result.get("cache_write_tokens"),
                result.get("output_tokens"),
                result.get("reported_cost_usd"),
                _canonical_json(result.get("request_tags") or []),
                now,
            ),
        )
        conn.execute(
            """UPDATE candidate_item
               SET status = 'complete', attempts = attempts + 1,
                   outcome = ?, no_insight_reason = ?, claim = ?,
                   claim_posture = ?, why_it_matters = ?,
                   audience_fields_json = ?, supporting_quote = ?,
                   citation_block_index = ?, citation_source_type = ?,
                   citation_source_id = ?, citation_source_url = ?,
                   citation_source_author = ?, citation_source_title = ?,
                   citation_source_sha256 = ?, citation_section_ordinal = ?,
                   citation_char_start = ?, citation_char_end = ?,
                   citation_global_matching_block_count = ?, response_id = ?,
                   response_model = ?, input_tokens = ?, cached_tokens = ?,
                   cache_write_tokens = ?, output_tokens = ?,
                   reported_cost_usd = ?, request_tags_json = ?,
                   raw_output_text = ?, error_type = NULL, error_message = NULL,
                   completed_at = ?, updated_at = ?
               WHERE candidate_id = ?""",
            (
                result["outcome"],
                result.get("no_insight_reason"),
                result.get("claim"),
                result.get("claim_posture"),
                result.get("why_it_matters"),
                _canonical_json(analysis) if analysis else None,
                result.get("supporting_quote"),
                result.get("citation_block_index"),
                citation.get("source_type"),
                citation.get("source_id"),
                citation.get("source_url"),
                citation.get("source_author"),
                citation.get("source_title"),
                citation.get("source_sha256"),
                citation.get("section_ordinal"),
                citation.get("char_start"),
                citation.get("char_end"),
                citation.get("global_matching_block_count"),
                result.get("response_id"),
                result.get("response_model"),
                result.get("input_tokens"),
                result.get("cached_tokens"),
                result.get("cache_write_tokens"),
                result.get("output_tokens"),
                result.get("reported_cost_usd"),
                _canonical_json(result.get("request_tags") or []),
                result.get("raw_output_text"),
                now,
                now,
                row["candidate_id"],
            ),
        )


def _store_failure(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    error: Exception,
) -> str:
    now = _now()
    deterministic_failure_reasons = {
        audience_insights.CitationVerificationError:
            "citation_verification_failed",
        audience_insights.ExtractionValidationError:
            "schema_validation_failed",
    }
    terminal_reason = next(
        (
            reason
            for error_type, reason in deterministic_failure_reasons.items()
            if isinstance(error, error_type)
        ),
        None,
    )
    audit_result = error.result if terminal_reason is not None else None
    attempt_number = int(row["attempts"]) + 1
    prior_matching_failures = int(
        conn.execute(
            """SELECT COUNT(*)
               FROM candidate_attempt
               WHERE candidate_id = ?
                 AND error_type = ?""",
            (
                row["candidate_id"],
                type(error).__name__,
            ),
        ).fetchone()[0]
    )
    terminal_rejection = (
        audit_result is not None
        and prior_matching_failures + 1 >= MAX_EXTRACTION_ATTEMPTS
    )
    status = "rejected" if terminal_rejection else "failed"
    terminal_reason = terminal_reason if terminal_rejection else None
    with conn:
        conn.execute(
            """INSERT INTO candidate_attempt
               (candidate_id, attempt_number, status, result_json,
                raw_output_text, error_type, error_message, response_id,
                response_model, input_tokens, cached_tokens,
                cache_write_tokens, output_tokens, reported_cost_usd,
                request_tags_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row["candidate_id"],
                attempt_number,
                status,
                _canonical_json(audit_result) if audit_result is not None else None,
                (audit_result or {}).get("raw_output_text"),
                type(error).__name__,
                str(error),
                (audit_result or {}).get("response_id"),
                (audit_result or {}).get("response_model"),
                (audit_result or {}).get("input_tokens"),
                (audit_result or {}).get("cached_tokens"),
                (audit_result or {}).get("cache_write_tokens"),
                (audit_result or {}).get("output_tokens"),
                (audit_result or {}).get("reported_cost_usd"),
                _canonical_json((audit_result or {}).get("request_tags") or []),
                now,
            ),
        )
        conn.execute(
            """UPDATE candidate_item
               SET status = ?, attempts = attempts + 1,
                   outcome = ?, no_insight_reason = ?, claim = ?,
                   claim_posture = ?, why_it_matters = ?,
                   audience_fields_json = ?, supporting_quote = ?,
                   citation_block_index = ?, response_id = ?,
                   response_model = ?, input_tokens = ?, cached_tokens = ?,
                   cache_write_tokens = ?, output_tokens = ?,
                   reported_cost_usd = ?, request_tags_json = ?,
                   raw_output_text = ?, error_type = ?, error_message = ?,
                   terminal_reason = ?, completed_at = ?, updated_at = ?
               WHERE candidate_id = ?""",
            (
                status,
                (audit_result or {}).get("outcome"),
                (audit_result or {}).get("no_insight_reason"),
                (audit_result or {}).get("claim"),
                (audit_result or {}).get("claim_posture"),
                (audit_result or {}).get("why_it_matters"),
                _canonical_json((audit_result or {}).get("audience_fields") or {})
                if (audit_result or {}).get("audience_fields")
                else None,
                (audit_result or {}).get("supporting_quote"),
                (audit_result or {}).get("citation_block_index"),
                (audit_result or {}).get("response_id"),
                (audit_result or {}).get("response_model"),
                (audit_result or {}).get("input_tokens"),
                (audit_result or {}).get("cached_tokens"),
                (audit_result or {}).get("cache_write_tokens"),
                (audit_result or {}).get("output_tokens"),
                (audit_result or {}).get("reported_cost_usd"),
                _canonical_json((audit_result or {}).get("request_tags") or []),
                (audit_result or {}).get("raw_output_text"),
                type(error).__name__,
                str(error),
                terminal_reason,
                now if terminal_rejection else None,
                now,
                row["candidate_id"],
            ),
        )
    return status


def run_pending(
    conn: sqlite3.Connection,
    *,
    client: Any,
    workers: int = DEFAULT_WORKERS,
    retry_failed: bool = False,
    progress_every: int = DEFAULT_PROGRESS_EVERY,
) -> dict[str, Any]:
    if workers < 1:
        raise ValueError("workers must be at least 1")
    if progress_every < 1:
        raise ValueError("progress_every must be at least 1")
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("run database has not been prepared")
    statuses = ("pending", "failed") if retry_failed else ("pending",)
    rows = conn.execute(
        """SELECT * FROM candidate_item
           WHERE status IN (SELECT value FROM json_each(?))
           ORDER BY feed_rank, event_id""",
        (_canonical_json(statuses),),
    ).fetchall()
    if not rows:
        return summary(conn)
    for row in rows:
        input_text = str(row["input_text"])
        if _sha256(input_text) != str(row["input_sha256"]):
            raise ValueError(
                f"frozen candidate input hash drift: {row['candidate_id']}"
            )

    def evaluate(
        row: sqlite3.Row,
    ) -> tuple[sqlite3.Row, dict[str, Any] | None, Exception | None]:
        packet = _packet_from_payload(json.loads(row["packet_json"]))
        try:
            result = audience_insights.evaluate_one(
                client,
                packet,
                audience=str(meta["audience"]),
                run=str(meta["run_id"]),
                model=str(meta["model"]),
                effort=str(meta["reasoning_effort"]),
                frozen_input_text=str(row["input_text"]),
            )
            return row, result, None
        except Exception as exc:
            return row, None, exc

    lanes: dict[str, deque[sqlite3.Row]] = {}
    for row in rows:
        lanes.setdefault(str(row["prompt_cache_key"]), deque()).append(row)
    waiting_lanes = deque(lanes)
    active: dict[concurrent.futures.Future, str] = {}
    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=min(workers, len(lanes))
    )

    def start_next(cache_key: str) -> None:
        active[executor.submit(evaluate, lanes[cache_key].popleft())] = cache_key

    while waiting_lanes and len(active) < workers:
        start_next(waiting_lanes.popleft())

    try:
        processed = 0
        while active:
            done, _ = concurrent.futures.wait(
                active,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            for future in done:
                cache_key = active.pop(future)
                row, result, error = future.result()
                if result is not None:
                    _store_success(conn, row, result)
                    status = "complete"
                else:
                    assert error is not None
                    status = _store_failure(conn, row, error)
                processed += 1
                if (
                    processed == 1
                    or processed % progress_every == 0
                    or processed == len(rows)
                ):
                    print(
                        _canonical_json(
                            {
                                "audience": meta["audience"],
                                "day": meta["day"],
                                "candidate_id": row["candidate_id"],
                                "feed_rank": row["feed_rank"],
                                "status": status,
                                "processed": processed,
                                "pending_batch": len(rows),
                            }
                        ),
                        file=sys.stderr,
                        flush=True,
                    )
                if lanes[cache_key]:
                    start_next(cache_key)
                elif waiting_lanes:
                    start_next(waiting_lanes.popleft())
    finally:
        executor.shutdown(wait=True, cancel_futures=False)
    return summary(conn)


def _reviewable_candidate_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return every extracted insight with mechanically bound provenance."""
    return conn.execute(
        """SELECT item.*, meta.audience
           FROM candidate_item AS item
           CROSS JOIN run_meta AS meta
           WHERE meta.singleton = 1
             AND item.status = 'complete'
             AND item.outcome = 'insight'
             AND item.citation_source_url IS NOT NULL
             AND item.citation_source_sha256 IS NOT NULL
             AND item.citation_char_start IS NOT NULL
             AND item.citation_char_end IS NOT NULL
           ORDER BY item.candidate_id"""
    ).fetchall()


def _candidate_editor_payload(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "candidate_id": str(row["candidate_id"]),
        "claim": str(row["claim"]),
        "claim_posture": str(row["claim_posture"]),
        "why_it_matters": str(row["why_it_matters"]),
        "audience_fields": json.loads(row["audience_fields_json"]),
        "source_type": str(row["citation_source_type"]),
        "source_author": row["citation_source_author"],
        "source_title": row["citation_source_title"],
    }


def _editor_candidates(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return only independently reviewed candidates that pass every dimension.

    The join is a publication filter. Reviewer judgments and rationale are
    deliberately absent from the selected columns, so they cannot steer the
    daily editor after deciding eligibility.
    """
    rows = conn.execute(
        """SELECT item.candidate_id, item.claim, item.claim_posture,
                  item.why_it_matters, item.audience_fields_json,
                  item.citation_source_type, item.citation_source_author,
                  item.citation_source_title
           FROM candidate_item AS item
           JOIN item_review AS review USING (candidate_id)
           WHERE item.status = 'complete' AND item.outcome = 'insight'
             AND item.citation_source_url IS NOT NULL
             AND item.citation_source_sha256 IS NOT NULL
             AND item.citation_char_start IS NOT NULL
             AND item.citation_char_end IS NOT NULL
             AND review.status = 'complete'
             AND review.claim_fidelity = 'pass'
             AND review.epistemic_discipline = 'pass'
             AND review.audience_usefulness = 'pass'
             AND review.actionability = 'pass'
             AND review.specificity = 'pass'
           ORDER BY item.candidate_id"""
    ).fetchall()
    return [_candidate_editor_payload(row) for row in rows]


def prepare_editor(
    conn: sqlite3.Connection,
    *,
    prior_selected: Iterable[dict[str, Any]] = (),
) -> int:
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("run database has not been prepared")
    counts = conn.execute(
        """SELECT SUM(status = 'pending') AS pending,
                  SUM(status = 'failed') AS failed
           FROM candidate_item"""
    ).fetchone()
    if int(counts["pending"] or 0) or int(counts["failed"] or 0):
        raise ValueError(
            "editor requires every frozen candidate to be handled "
            "(complete or terminally rejected)"
        )
    uncovered = conn.execute(
        """SELECT COUNT(*)
           FROM candidate_item AS item
           LEFT JOIN item_review AS review USING (candidate_id)
           WHERE item.status = 'complete' AND item.outcome = 'insight'
             AND item.citation_source_url IS NOT NULL
             AND item.citation_source_sha256 IS NOT NULL
             AND item.citation_char_start IS NOT NULL
             AND item.citation_char_end IS NOT NULL
             AND (review.candidate_id IS NULL OR review.status != 'complete')"""
    ).fetchone()[0]
    if int(uncovered):
        raise ValueError(
            "editor requires a complete independent item quality review for "
            "every citation-verified insight candidate"
        )
    candidates = _editor_candidates(conn)
    history = list(prior_selected)
    candidate_set_sha256 = _sha256(_canonical_json(candidates))
    history_sha256 = _sha256(_canonical_json(history))
    editor_input = audience_insights.EditorInput(
        audience=str(meta["audience"]),
        day=str(meta["day"]),
        candidates=tuple(candidates),
        prior_selected=tuple(history),
    )
    input_text = audience_insights.render_editor_input(editor_input)
    cache_key = audience_insights.editor_prompt_cache_key(
        str(meta["audience"]), str(meta["day"])
    )
    existing = conn.execute("SELECT * FROM editor_run WHERE singleton = 1").fetchone()
    if existing is not None:
        mismatches = []
        for key, value in (
            ("candidate_set_sha256", candidate_set_sha256),
            ("history_sha256", history_sha256),
            ("input_text", input_text),
            ("prompt_cache_key", cache_key),
        ):
            if existing[key] != value:
                mismatches.append(key)
        if mismatches:
            raise ValueError(
                "editor input no longer matches the frozen run: "
                + ", ".join(mismatches)
            )
        return len(candidates)
    now = _now()
    with conn:
        conn.execute(
            """INSERT INTO editor_run
               (singleton, candidate_set_sha256, history_sha256,
                prior_selected_json, input_text, prompt_cache_key, updated_at)
               VALUES (1, ?, ?, ?, ?, ?, ?)""",
            (
                candidate_set_sha256,
                history_sha256,
                _canonical_json(history),
                input_text,
                cache_key,
                now,
            ),
        )
    return len(candidates)


def run_editor(conn: sqlite3.Connection, *, client: Any) -> dict[str, Any]:
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    editor = conn.execute("SELECT * FROM editor_run WHERE singleton = 1").fetchone()
    if meta is None or editor is None:
        raise ValueError("editor input has not been prepared")
    if editor["status"] == "complete":
        return summary(conn)
    candidates = _editor_candidates(conn)
    prior_selected = json.loads(editor["prior_selected_json"])
    editor_input = audience_insights.EditorInput(
        audience=str(meta["audience"]),
        day=str(meta["day"]),
        candidates=tuple(candidates),
        prior_selected=tuple(prior_selected),
    )
    try:
        result = audience_insights.evaluate_editor(
            client,
            editor_input,
            run=str(meta["run_id"]),
            model=str(meta["editor_model"]),
            effort=str(meta["editor_reasoning_effort"]),
        )
        now = _now()
        with conn:
            conn.execute("DELETE FROM daily_selection")
            conn.execute("DELETE FROM publication_selection")
            conn.execute("DELETE FROM selection_reconciliation")
            conn.execute("DELETE FROM reconciled_day_set_review")
            conn.execute("DELETE FROM quality_gate")
            conn.execute("DELETE FROM suppressed_duplicate")
            conn.executemany(
                """INSERT INTO daily_selection
                   (editorial_rank, candidate_id, decision_value,
                    audit_reason, updates_prior_id)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    (
                        rank,
                        item["candidate_id"],
                        item["decision_value"],
                        item["audit_reason"],
                        item["updates_prior_id"],
                    )
                    for rank, item in enumerate(result["selected"], start=1)
                ],
            )
            conn.executemany(
                """INSERT INTO publication_selection
                   (publication_rank, original_editorial_rank,
                    candidate_id, activated_at)
                   VALUES (?, ?, ?, ?)""",
                [
                    (rank, rank, item["candidate_id"], now)
                    for rank, item in enumerate(result["selected"], start=1)
                ],
            )
            conn.executemany(
                """INSERT INTO suppressed_duplicate
                   (candidate_id, duplicate_of_id, duplicate_scope, audit_reason)
                   VALUES (?, ?, ?, ?)""",
                [
                    (
                        item["candidate_id"],
                        item["duplicate_of_id"],
                        item["duplicate_scope"],
                        item["audit_reason"],
                    )
                    for item in result["suppressed_duplicates"]
                ],
            )
            conn.execute(
                """UPDATE editor_run
                   SET status = 'complete', attempts = attempts + 1,
                       selected_count = ?, thin_day_reason = ?, response_id = ?,
                       response_model = ?, input_tokens = ?, cached_tokens = ?,
                       cache_write_tokens = ?, output_tokens = ?,
                       reported_cost_usd = ?, request_tags_json = ?,
                       raw_output_text = ?, error_type = NULL,
                       error_message = NULL, completed_at = ?, updated_at = ?
                   WHERE singleton = 1""",
                (
                    len(result["selected"]),
                    result["thin_day_reason"],
                    result["response_id"],
                    result["response_model"],
                    result["input_tokens"],
                    result["cached_tokens"],
                    result["cache_write_tokens"],
                    result["output_tokens"],
                    result["reported_cost_usd"],
                    _canonical_json(result["request_tags"]),
                    result["raw_output_text"],
                    now,
                    now,
                ),
            )
    except Exception as exc:
        now = _now()
        with conn:
            conn.execute(
                """UPDATE editor_run
                   SET status = 'failed', attempts = attempts + 1,
                       error_type = ?, error_message = ?, updated_at = ?
                   WHERE singleton = 1""",
                (type(exc).__name__, str(exc), now),
            )
        raise
    return summary(conn)


def selected_history_row(
    conn: sqlite3.Connection,
    *,
    candidate_ids: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    run = conn.execute("SELECT audience, day FROM run_meta WHERE singleton = 1").fetchone()
    if run is None:
        return []
    rows = conn.execute(
        """SELECT selection.publication_rank, item.candidate_id, item.claim,
                  item.audience_fields_json, item.citation_source_author,
                  item.citation_source_title
           FROM publication_selection AS selection
           JOIN candidate_item AS item USING (candidate_id)
           ORDER BY selection.publication_rank"""
    ).fetchall()
    allowed_ids = set(candidate_ids) if candidate_ids is not None else None
    return [
        {
            "selected_item_id": str(row["candidate_id"]),
            "day": str(run["day"]),
            "claim": str(row["claim"]),
            "audience_fields": json.loads(row["audience_fields_json"]),
            "source_author": row["citation_source_author"],
            "source_title": row["citation_source_title"],
        }
        for row in rows
        if allowed_ids is None or str(row["candidate_id"]) in allowed_ids
    ]


def _history_projection_ids(projection: Mapping[str, Any]) -> list[str]:
    """Project one audited run into duplicate-suppression history.

    Independent-audit disqualifications disappear from both publication and
    history. A senior editorial veto disappears only from publication: the
    mechanically valid framing remains in history so a later editor cannot
    rediscover it as a fresh story.
    """
    history_ids = projection.get("history_selected_ids")
    if not isinstance(history_ids, list) or any(
        not isinstance(value, str) or not value for value in history_ids
    ):
        raise ValueError("publication projection is missing explicit history IDs")
    if len(history_ids) != len(set(history_ids)):
        raise ValueError("publication projection history IDs are not unique")
    return list(history_ids)


def _quality_item_payload(
    row: sqlite3.Row,
) -> tuple[
    audience_insight_evaluations.ItemReviewInput,
    audience_insights.EvidencePacket,
]:
    packet = _packet_from_payload(json.loads(row["packet_json"]))
    audience_fields = json.loads(row["audience_fields_json"])
    extracted = {
        "claim": row["claim"],
        "claim_posture": row["claim_posture"],
        "why_it_matters": row["why_it_matters"],
        "supporting_quote": row["supporting_quote"],
        "citation_block_index": row["citation_block_index"],
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
    review = audience_insight_evaluations.ItemReviewInput(
        candidate_id=str(row["candidate_id"]),
        audience=str(row["audience"]),
        day=str(row["day"]),
        evidence_blocks=blocks,
        extracted_item=extracted,
    )
    return review, packet


def prepare_item_reviews(conn: sqlite3.Connection) -> int:
    """Freeze an independent review input for every reviewable extraction."""
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("run database has not been prepared")
    reviewable_rows = _reviewable_candidate_rows(conn)
    now = _now()
    for row in reviewable_rows:
        candidate_id = str(row["candidate_id"])
        review, _ = _quality_item_payload(row)
        input_text = audience_insight_evaluations.render_item_input(review)
        cache_key = audience_insight_evaluations.item_prompt_cache_key(
            str(meta["audience"]), candidate_id
        )
        existing = conn.execute(
            "SELECT * FROM item_review WHERE candidate_id = ?", (candidate_id,)
        ).fetchone()
        if existing is not None:
            if (
                existing["input_sha256"] != review.input_sha256
                or existing["input_text"] != input_text
                or existing["prompt_cache_key"] != cache_key
            ):
                raise ValueError(
                    f"quality item input changed for frozen candidate {candidate_id}"
                )
            continue
        with conn:
            conn.execute(
                """INSERT INTO item_review
                   (candidate_id, input_text, input_sha256,
                    prompt_cache_key, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (candidate_id, input_text, review.input_sha256, cache_key, now),
            )
    return len(reviewable_rows)


def run_item_reviews(
    conn: sqlite3.Connection,
    *,
    client: Any,
    workers: int = DEFAULT_REVIEW_WORKERS,
) -> dict[str, Any]:
    """Review all extracted insights in parallel before daily editing."""
    if workers < 1:
        raise ValueError("review workers must be at least 1")
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("run database has not been prepared")
    prepare_item_reviews(conn)
    rows = conn.execute(
        """SELECT review.*, item.packet_json, item.day,
                  item.claim, item.claim_posture, item.why_it_matters,
                  item.audience_fields_json, item.supporting_quote,
                  item.citation_block_index, meta.audience
           FROM item_review AS review
           JOIN candidate_item AS item USING (candidate_id)
           CROSS JOIN run_meta AS meta
           WHERE review.status != 'complete' AND meta.singleton = 1
           ORDER BY review.candidate_id"""
    ).fetchall()

    def evaluate_item(
        row: sqlite3.Row,
    ) -> tuple[sqlite3.Row, dict[str, Any] | None, Exception | None]:
        review, _ = _quality_item_payload(row)
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

    errors: list[Exception] = []
    if rows:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(workers, len(rows))
        ) as executor:
            futures = [executor.submit(evaluate_item, row) for row in rows]
            for future in concurrent.futures.as_completed(futures):
                row, result, error = future.result()
                if result is not None:
                    _store_item_review_success(conn, result)
                    continue
                assert error is not None
                errors.append(error)
                with conn:
                    conn.execute(
                        """UPDATE item_review
                           SET status = 'failed', attempts = attempts + 1,
                               error_type = ?, error_message = ?, updated_at = ?
                           WHERE candidate_id = ?""",
                        (
                            type(error).__name__,
                            str(error),
                            _now(),
                            row["candidate_id"],
                        ),
                    )
    if errors:
        # Preserve every concurrently completed result before surfacing the
        # first failure. A resumed run evaluates only the remaining rows.
        raise errors[0]
    return summary(conn)


def prepare_day_set_review(conn: sqlite3.Connection) -> int:
    """Freeze the post-editor set review over quality-eligible candidates."""
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    editor = conn.execute("SELECT * FROM editor_run WHERE singleton = 1").fetchone()
    if meta is None or editor is None or editor["status"] != "complete":
        raise ValueError("day-set quality review requires a complete daily editor")
    incomplete_reviews = conn.execute(
        """SELECT COUNT(*)
           FROM candidate_item AS item
           LEFT JOIN item_review AS review USING (candidate_id)
           WHERE item.status = 'complete' AND item.outcome = 'insight'
             AND item.citation_source_url IS NOT NULL
             AND item.citation_source_sha256 IS NOT NULL
             AND item.citation_char_start IS NOT NULL
             AND item.citation_char_end IS NOT NULL
             AND (review.candidate_id IS NULL OR review.status != 'complete')"""
    ).fetchone()[0]
    if int(incomplete_reviews):
        raise ValueError(
            "day-set quality review requires complete item-review coverage"
        )
    eligible_items = _editor_candidates(conn)
    eligible_by_id = {item["candidate_id"]: item for item in eligible_items}
    selected_ids = [
        str(row[0])
        for row in conn.execute(
            "SELECT candidate_id FROM daily_selection ORDER BY editorial_rank"
        )
    ]
    if any(candidate_id not in eligible_by_id for candidate_id in selected_ids):
        raise ValueError("editor selected a candidate that is not quality eligible")

    now = _now()
    prior_selected = json.loads(editor["prior_selected_json"])
    selected = tuple(eligible_by_id[candidate_id] for candidate_id in selected_ids)
    selected_set = set(selected_ids)
    unselected = tuple(
        item for item in eligible_items if item["candidate_id"] not in selected_set
    )
    day_input = audience_insight_evaluations.DaySetReviewInput(
        audience=str(meta["audience"]),
        day=str(meta["day"]),
        selected=selected,
        unselected=unselected,
        prior_selected=tuple(prior_selected),
    )
    day_input_text = audience_insight_evaluations.render_day_set_input(day_input)
    day_cache_key = audience_insight_evaluations.day_set_prompt_cache_key(
        str(meta["audience"]), day_input.input_sha256
    )
    existing_day = conn.execute(
        "SELECT * FROM day_set_review WHERE singleton = 1"
    ).fetchone()
    if existing_day is not None:
        if (
            existing_day["input_sha256"] != day_input.input_sha256
            or existing_day["input_text"] != day_input_text
            or existing_day["prompt_cache_key"] != day_cache_key
        ):
            raise ValueError("quality day-set input changed for the frozen run")
    else:
        with conn:
            conn.execute(
                """INSERT INTO day_set_review
                   (singleton, input_text, input_sha256,
                    prompt_cache_key, updated_at)
                   VALUES (1, ?, ?, ?, ?)""",
                (day_input_text, day_input.input_sha256, day_cache_key, now),
            )
    return len(eligible_items)


def prepare_quality_reviews(conn: sqlite3.Connection) -> int:
    """Compatibility wrapper for the post-editor day-set review stage."""
    return prepare_day_set_review(conn)


def _store_item_review_success(
    conn: sqlite3.Connection,
    result: dict[str, Any],
) -> None:
    now = _now()
    with conn:
        conn.execute(
            """UPDATE item_review
               SET status = 'complete', attempts = attempts + 1,
                   claim_fidelity = ?, epistemic_discipline = ?,
                   audience_usefulness = ?, actionability = ?, specificity = ?,
                   failure_codes_json = ?, rationale = ?, response_id = ?,
                   response_model = ?, input_tokens = ?, cached_tokens = ?,
                   cache_write_tokens = ?, output_tokens = ?,
                   reported_cost_usd = ?, request_tags_json = ?,
                   raw_output_text = ?, error_type = NULL, error_message = NULL,
                   completed_at = ?, updated_at = ?
               WHERE candidate_id = ?""",
            (
                result["claim_fidelity"],
                result["epistemic_discipline"],
                result["audience_usefulness"],
                result["actionability"],
                result["specificity"],
                _canonical_json(result["failure_codes"]),
                result["rationale"],
                result["response_id"],
                result["response_model"],
                result["input_tokens"],
                result["cached_tokens"],
                result["cache_write_tokens"],
                result["output_tokens"],
                result["reported_cost_usd"],
                _canonical_json(result["request_tags"]),
                result["raw_output_text"],
                now,
                now,
                result["candidate_id"],
            ),
        )


def _selection_rows(
    conn: sqlite3.Connection,
    *,
    publication: bool,
) -> list[sqlite3.Row]:
    if publication:
        return conn.execute(
            """SELECT published.publication_rank AS active_rank,
                      published.original_editorial_rank,
                      published.candidate_id
               FROM publication_selection AS published
               ORDER BY published.publication_rank"""
        ).fetchall()
    return conn.execute(
        """SELECT selected.editorial_rank AS active_rank,
                  selected.editorial_rank AS original_editorial_rank,
                  selected.candidate_id
           FROM daily_selection AS selected
           ORDER BY selected.editorial_rank"""
    ).fetchall()


def _quality_day_input_for_ids(
    conn: sqlite3.Connection,
    selected_ids: Iterable[str],
) -> audience_insight_evaluations.DaySetReviewInput:
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    editor = conn.execute("SELECT * FROM editor_run WHERE singleton = 1").fetchone()
    assert meta is not None and editor is not None
    current_items = _editor_candidates(conn)
    current_by_id = {item["candidate_id"]: item for item in current_items}
    ordered_ids = tuple(str(candidate_id) for candidate_id in selected_ids)
    if len(ordered_ids) != len(set(ordered_ids)):
        raise ValueError("day-set review selection contains duplicate candidate IDs")
    missing = [candidate_id for candidate_id in ordered_ids if candidate_id not in current_by_id]
    if missing:
        raise ValueError(
            "day-set review selection contains ineligible candidates: "
            + ", ".join(missing)
        )
    selected = tuple(current_by_id[candidate_id] for candidate_id in ordered_ids)
    selected_set = set(ordered_ids)
    unselected = tuple(
        item for item in current_items if item["candidate_id"] not in selected_set
    )
    return audience_insight_evaluations.DaySetReviewInput(
        audience=str(meta["audience"]),
        day=str(meta["day"]),
        selected=selected,
        unselected=unselected,
        prior_selected=tuple(json.loads(editor["prior_selected_json"])),
    )


def _quality_day_input(
    conn: sqlite3.Connection,
    *,
    publication: bool = False,
) -> audience_insight_evaluations.DaySetReviewInput:
    rows = _selection_rows(conn, publication=publication)
    return _quality_day_input_for_ids(
        conn,
        (str(row["candidate_id"]) for row in rows),
    )


def prepare_padding_tail_reconciliation(conn: sqlite3.Connection) -> bool:
    """Freeze one deterministic tail trim after a structured padding veto.

    The original editor shortlist and first day-set review remain untouched.
    Reconciliation can remove only the final editorial rank and can be prepared
    only once.  Its fresh review input uses the same prompt version but a new
    input hash, and therefore a distinct cache scope.
    """
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    first_review = conn.execute(
        "SELECT * FROM day_set_review WHERE singleton = 1 AND status = 'complete'"
    ).fetchone()
    if meta is None or first_review is None:
        raise ValueError("padding reconciliation requires a complete first day-set review")
    original_rows = _selection_rows(conn, publication=False)
    original_ids = tuple(str(row["candidate_id"]) for row in original_rows)
    # A thin day is allowed to publish one or two genuinely strong items.  If
    # the independent reviewer identifies the editor's final item as padding,
    # preserve the stronger prefix even when the original shortlist was below
    # the nominal target of three.  Never reconcile 1 -> 0: at that point there
    # is no stronger retained prefix, so the padding veto must fail closed.
    if not bool(first_review["padding_detected"]) or len(original_rows) <= 1:
        return False

    removed = original_rows[-1]
    active_rows = original_rows[:-1]
    active_ids = tuple(str(row["candidate_id"]) for row in active_rows)
    expected = {
        "reason_code": "padding_tail_trim",
        "source_review_input_sha256": str(first_review["input_sha256"]),
        "original_selected_ids_json": _canonical_json(original_ids),
        "active_selected_ids_json": _canonical_json(active_ids),
        "removed_candidate_id": str(removed["candidate_id"]),
        "removed_editorial_rank": int(removed["original_editorial_rank"]),
    }
    second_input = _quality_day_input_for_ids(conn, active_ids)
    second_text = audience_insight_evaluations.render_day_set_input(second_input)
    second_cache_key = audience_insight_evaluations.day_set_prompt_cache_key(
        str(meta["audience"]),
        second_input.input_sha256,
        cache_scope="padding_tail_trim",
    )
    if second_cache_key == str(first_review["prompt_cache_key"]):
        raise ValueError("padding reconciliation did not create a distinct cache scope")

    existing = conn.execute(
        "SELECT * FROM selection_reconciliation WHERE singleton = 1"
    ).fetchone()
    if existing is not None:
        mismatches = [
            key for key, value in expected.items() if existing[key] != value
        ]
        publication_ids = tuple(
            str(row["candidate_id"])
            for row in _selection_rows(conn, publication=True)
        )
        if publication_ids != active_ids:
            mismatches.append("publication_selection")
        second = conn.execute(
            "SELECT * FROM reconciled_day_set_review WHERE singleton = 1"
        ).fetchone()
        if second is None:
            mismatches.append("reconciled_day_set_review")
        elif (
            second["source_review_input_sha256"] != first_review["input_sha256"]
            or second["input_sha256"] != second_input.input_sha256
            or second["input_text"] != second_text
            or second["prompt_cache_key"] != second_cache_key
        ):
            mismatches.append("reconciled_day_set_review_input")
        if mismatches:
            raise ValueError(
                "padding reconciliation no longer matches the frozen run: "
                + ", ".join(mismatches)
            )
        return True

    publication_ids = tuple(
        str(row["candidate_id"])
        for row in _selection_rows(conn, publication=True)
    )
    if publication_ids != original_ids:
        raise ValueError(
            "active publication selection no longer matches the original editor set"
        )
    now = _now()
    with conn:
        conn.execute("DELETE FROM quality_gate")
        conn.execute("DELETE FROM publication_selection")
        conn.executemany(
            """INSERT INTO publication_selection
               (publication_rank, original_editorial_rank,
                candidate_id, activated_at)
               VALUES (?, ?, ?, ?)""",
            [
                (
                    publication_rank,
                    int(row["original_editorial_rank"]),
                    str(row["candidate_id"]),
                    now,
                )
                for publication_rank, row in enumerate(active_rows, start=1)
            ],
        )
        conn.execute(
            """INSERT INTO selection_reconciliation
               (singleton, status, reason_code, source_review_input_sha256,
                source_review_response_id, original_selected_ids_json,
                active_selected_ids_json, removed_candidate_id,
                removed_editorial_rank, created_at, updated_at)
               VALUES (1, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                expected["reason_code"],
                expected["source_review_input_sha256"],
                first_review["response_id"],
                expected["original_selected_ids_json"],
                expected["active_selected_ids_json"],
                expected["removed_candidate_id"],
                expected["removed_editorial_rank"],
                now,
                now,
            ),
        )
        conn.execute(
            """INSERT INTO reconciled_day_set_review
               (singleton, reconciliation_reason,
                source_review_input_sha256, input_text, input_sha256,
                prompt_cache_key, updated_at)
               VALUES (1, 'padding_tail_trim', ?, ?, ?, ?, ?)""",
            (
                first_review["input_sha256"],
                second_text,
                second_input.input_sha256,
                second_cache_key,
                now,
            ),
        )
    return True


def _gate_day_review_row(conn: sqlite3.Connection) -> sqlite3.Row:
    reconciliation = conn.execute(
        "SELECT * FROM selection_reconciliation WHERE singleton = 1"
    ).fetchone()
    table = "reconciled_day_set_review" if reconciliation is not None else "day_set_review"
    row = conn.execute(
        f"SELECT * FROM {table} WHERE singleton = 1 AND status = 'complete'"
    ).fetchone()
    if row is None:
        raise ValueError("final day-set review has not completed")
    return row


def compute_and_store_quality_gate(conn: sqlite3.Connection) -> dict[str, Any]:
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("run database has not been prepared")
    selected_ids = tuple(
        str(row["candidate_id"])
        for row in _selection_rows(conn, publication=True)
    )
    if selected_ids:
        placeholders = ",".join("?" for _ in selected_ids)
        item_rows = conn.execute(
            f"""SELECT * FROM item_review
                WHERE status = 'complete'
                  AND candidate_id IN ({placeholders})
                ORDER BY candidate_id""",
            selected_ids,
        ).fetchall()
    else:
        item_rows = []
    item_reviews = tuple(
        {
            "candidate_id": str(row["candidate_id"]),
            "claim_fidelity": str(row["claim_fidelity"]),
            "epistemic_discipline": str(row["epistemic_discipline"]),
            "audience_usefulness": str(row["audience_usefulness"]),
            "actionability": str(row["actionability"]),
            "specificity": str(row["specificity"]),
            "failure_codes": json.loads(row["failure_codes_json"]),
            "rationale": str(row["rationale"]),
        }
        for row in item_rows
    )
    day_row = _gate_day_review_row(conn)
    day_review = {
        "duplicate_pairs": json.loads(day_row["duplicate_pairs_json"]),
        "padding_detected": bool(day_row["padding_detected"]),
        "thin_day_honest": bool(day_row["thin_day_honest"]),
        "set_rationale": str(day_row["set_rationale"]),
    }
    counts = conn.execute(
        """SELECT SUM(status = 'pending') AS pending,
                  SUM(status = 'failed') AS failed
           FROM candidate_item"""
    ).fetchone()
    citation_checks_passed = conn.execute(
        """SELECT COUNT(*) = 0
           FROM publication_selection AS selected
           JOIN candidate_item AS item USING (candidate_id)
           WHERE item.status != 'complete' OR item.outcome != 'insight'
              OR item.citation_source_url IS NULL
              OR item.citation_source_sha256 IS NULL
              OR item.citation_char_start IS NULL
              OR item.citation_char_end IS NULL"""
    ).fetchone()[0]
    result = audience_insight_evaluations.compute_day_gate(
        audience_insight_evaluations.DayGateInput(
            audience=str(meta["audience"]),
            day=str(meta["day"]),
            selected_candidate_ids=selected_ids,
            item_reviews=item_reviews,
            day_set_review=day_review,
            schema_checks_passed=True,
            citation_checks_passed=bool(citation_checks_passed),
            editor_output_valid=True,
            pending_count=int(counts["pending"] or 0),
            failed_count=int(counts["failed"] or 0),
        )
    )
    reconciliation = conn.execute(
        "SELECT * FROM selection_reconciliation WHERE singleton = 1"
    ).fetchone()
    result["reconciliation"] = (
        {
            "reason_code": str(reconciliation["reason_code"]),
            "removed_candidate_id": str(reconciliation["removed_candidate_id"]),
            "removed_editorial_rank": int(reconciliation["removed_editorial_rank"]),
            "original_selected_count": len(
                json.loads(reconciliation["original_selected_ids_json"])
            ),
            "active_selected_count": len(
                json.loads(reconciliation["active_selected_ids_json"])
            ),
        }
        if reconciliation is not None
        else None
    )
    with conn:
        conn.execute(
            """INSERT INTO quality_gate
               (singleton, passed, result_json, computed_at)
               VALUES (1, ?, ?, ?)
               ON CONFLICT(singleton) DO UPDATE SET
                   passed = excluded.passed,
                   result_json = excluded.result_json,
                   computed_at = excluded.computed_at""",
            (int(result["passed"]), _canonical_json(result), _now()),
        )
    return result


def run_quality_reviews(
    conn: sqlite3.Connection,
    *,
    client: Any,
    workers: int = DEFAULT_REVIEW_WORKERS,
) -> dict[str, Any]:
    if workers < 1:
        raise ValueError("review workers must be at least 1")
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("run database has not been prepared")
    prepare_quality_reviews(conn)
    first_row = conn.execute(
        "SELECT * FROM day_set_review WHERE singleton = 1"
    ).fetchone()
    assert first_row is not None
    if first_row["status"] != "complete":
        day_input = _quality_day_input(conn, publication=False)
        try:
            result = audience_insight_evaluations.review_day_set(
                client,
                day_input,
                run=str(meta["run_id"]),
                model=str(meta["review_model"]),
                effort=str(meta["review_reasoning_effort"]),
            )
            now = _now()
            with conn:
                conn.execute(
                    """UPDATE day_set_review
                       SET status = 'complete', attempts = attempts + 1,
                           duplicate_pairs_json = ?, padding_detected = ?,
                           thin_day_honest = ?, set_rationale = ?,
                           response_id = ?, response_model = ?, input_tokens = ?,
                           cached_tokens = ?, cache_write_tokens = ?,
                           output_tokens = ?, reported_cost_usd = ?,
                           request_tags_json = ?, raw_output_text = ?,
                           error_type = NULL, error_message = NULL,
                           completed_at = ?, updated_at = ?
                       WHERE singleton = 1""",
                    (
                        _canonical_json(result["duplicate_pairs"]),
                        int(result["padding_detected"]),
                        int(result["thin_day_honest"]),
                        result["set_rationale"],
                        result["response_id"],
                        result["response_model"],
                        result["input_tokens"],
                        result["cached_tokens"],
                        result["cache_write_tokens"],
                        result["output_tokens"],
                        result["reported_cost_usd"],
                        _canonical_json(result["request_tags"]),
                        result["raw_output_text"],
                        now,
                        now,
                    ),
                )
        except Exception as exc:
            with conn:
                conn.execute(
                    """UPDATE day_set_review
                       SET status = 'failed', attempts = attempts + 1,
                           error_type = ?, error_message = ?, updated_at = ?
                       WHERE singleton = 1""",
                    (type(exc).__name__, str(exc), _now()),
                )
            raise

    first_row = conn.execute(
        "SELECT * FROM day_set_review WHERE singleton = 1 AND status = 'complete'"
    ).fetchone()
    assert first_row is not None
    if prepare_padding_tail_reconciliation(conn):
        second_row = conn.execute(
            "SELECT * FROM reconciled_day_set_review WHERE singleton = 1"
        ).fetchone()
        assert second_row is not None
        if second_row["status"] != "complete":
            second_input = _quality_day_input(conn, publication=True)
            with conn:
                conn.execute(
                    """UPDATE selection_reconciliation
                       SET status = 'pending', error_type = NULL,
                           error_message = NULL, updated_at = ?
                       WHERE singleton = 1""",
                    (_now(),),
                )
            try:
                result = audience_insight_evaluations.review_day_set(
                    client,
                    second_input,
                    run=f"{meta['run_id']}:padding-tail-trim",
                    model=str(meta["review_model"]),
                    effort=str(meta["review_reasoning_effort"]),
                    cache_scope="padding_tail_trim",
                )
                if result["input_sha256"] != second_row["input_sha256"]:
                    raise ValueError(
                        "reconciled day-set response does not match its frozen input"
                    )
                if result["prompt_cache_key"] != second_row["prompt_cache_key"]:
                    raise ValueError(
                        "reconciled day-set response used an unexpected cache scope"
                    )
                now = _now()
                with conn:
                    conn.execute(
                        """UPDATE reconciled_day_set_review
                           SET status = 'complete', attempts = attempts + 1,
                               duplicate_pairs_json = ?, padding_detected = ?,
                               thin_day_honest = ?, set_rationale = ?,
                               response_id = ?, response_model = ?, input_tokens = ?,
                               cached_tokens = ?, cache_write_tokens = ?,
                               output_tokens = ?, reported_cost_usd = ?,
                               request_tags_json = ?, raw_output_text = ?,
                               error_type = NULL, error_message = NULL,
                               completed_at = ?, updated_at = ?
                           WHERE singleton = 1""",
                        (
                            _canonical_json(result["duplicate_pairs"]),
                            int(result["padding_detected"]),
                            int(result["thin_day_honest"]),
                            result["set_rationale"],
                            result["response_id"],
                            result["response_model"],
                            result["input_tokens"],
                            result["cached_tokens"],
                            result["cache_write_tokens"],
                            result["output_tokens"],
                            result["reported_cost_usd"],
                            _canonical_json(result["request_tags"]),
                            result["raw_output_text"],
                            now,
                            now,
                        ),
                    )
                    conn.execute(
                        """UPDATE selection_reconciliation
                           SET status = 'complete', error_type = NULL,
                               error_message = NULL, completed_at = ?, updated_at = ?
                           WHERE singleton = 1""",
                        (now, now),
                    )
            except Exception as exc:
                now = _now()
                with conn:
                    conn.execute(
                        """UPDATE reconciled_day_set_review
                           SET status = 'failed', attempts = attempts + 1,
                               error_type = ?, error_message = ?, updated_at = ?
                           WHERE singleton = 1""",
                        (type(exc).__name__, str(exc), now),
                    )
                    conn.execute(
                        """UPDATE selection_reconciliation
                           SET status = 'failed', error_type = ?,
                               error_message = ?, updated_at = ?
                           WHERE singleton = 1""",
                        (type(exc).__name__, str(exc), now),
                    )
                    conn.execute("DELETE FROM quality_gate")
                raise
    compute_and_store_quality_gate(conn)
    return summary(conn)


def summary(conn: sqlite3.Connection) -> dict[str, Any]:
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("run database has not been prepared")
    run = dict(meta)
    run.setdefault(
        "input_render_version",
        declared_input_render_version(conn),
    )
    counts = dict(
        conn.execute(
            """SELECT COUNT(*) AS total,
                      SUM(status = 'pending') AS pending,
                      SUM(status = 'complete') AS complete,
                      SUM(status = 'failed') AS failed,
                      SUM(status = 'rejected') AS rejected,
                      SUM(status = 'complete' AND outcome = 'insight') AS insights,
                      SUM(status = 'complete' AND
                          outcome = 'no_extractable_insight') AS no_extractable,
                      SUM(citation_source_url IS NOT NULL) AS verified_citations,
                      SUM(attempts) AS expected_attempts
               FROM candidate_item"""
        ).fetchone()
    )
    telemetry = dict(
        conn.execute(
            """WITH extraction_request AS (
                   SELECT attempt.input_tokens, attempt.cached_tokens,
                          attempt.cache_write_tokens, attempt.output_tokens,
                          attempt.reported_cost_usd, item.prompt_cache_key
                   FROM candidate_attempt AS attempt
                   JOIN candidate_item AS item USING (candidate_id)
                   UNION ALL
                   SELECT item.input_tokens, item.cached_tokens,
                          item.cache_write_tokens, item.output_tokens,
                          item.reported_cost_usd, item.prompt_cache_key
                   FROM candidate_item AS item
                   WHERE item.attempts > 0
                     AND NOT EXISTS (
                         SELECT 1 FROM candidate_attempt AS attempt
                         WHERE attempt.candidate_id = item.candidate_id
                     )
               )
               SELECT COUNT(*) AS recorded_attempts,
                      SUM(COALESCE(input_tokens, 0)) AS input_tokens,
                      SUM(COALESCE(cached_tokens, 0)) AS cached_tokens,
                      SUM(COALESCE(cache_write_tokens, 0)) AS cache_write_tokens,
                      SUM(COALESCE(output_tokens, 0)) AS output_tokens,
                      SUM(COALESCE(reported_cost_usd, 0)) AS reported_cost_usd,
                      SUM(reported_cost_usd IS NOT NULL) AS reported_cost_count,
                      COUNT(DISTINCT prompt_cache_key) AS prompt_cache_keys,
                      SUM(COALESCE(input_tokens, 0) >= 1024)
                          AS cache_eligible_requests,
                      SUM(COALESCE(cached_tokens, 0) > 0) AS cache_hit_requests
               FROM extraction_request"""
        ).fetchone()
    )
    counts.update(telemetry)
    counts["telemetry_missing_attempts"] = max(
        int(counts["expected_attempts"] or 0)
        - int(counts["recorded_attempts"] or 0),
        0,
    )
    editor = conn.execute("SELECT * FROM editor_run WHERE singleton = 1").fetchone()
    item_review_counts = dict(
        conn.execute(
            """SELECT COUNT(*) AS total,
                      SUM(status = 'pending') AS pending,
                      SUM(status = 'complete') AS complete,
                      SUM(status = 'failed') AS failed,
                      SUM(COALESCE(input_tokens, 0)) AS input_tokens,
                      SUM(COALESCE(cached_tokens, 0)) AS cached_tokens,
                      SUM(COALESCE(output_tokens, 0)) AS output_tokens,
                      SUM(COALESCE(reported_cost_usd, 0)) AS reported_cost_usd
               FROM item_review"""
        ).fetchone()
    )
    day_review = conn.execute(
        "SELECT * FROM day_set_review WHERE singleton = 1"
    ).fetchone()
    reconciled_day_review = conn.execute(
        "SELECT * FROM reconciled_day_set_review WHERE singleton = 1"
    ).fetchone()
    reconciliation = conn.execute(
        "SELECT * FROM selection_reconciliation WHERE singleton = 1"
    ).fetchone()
    day_review_counts = dict(
        conn.execute(
            """WITH review_request AS (
                   SELECT attempts, status, input_tokens, cached_tokens,
                          cache_write_tokens, output_tokens, reported_cost_usd,
                          prompt_cache_key
                   FROM day_set_review
                   UNION ALL
                   SELECT attempts, status, input_tokens, cached_tokens,
                          cache_write_tokens, output_tokens, reported_cost_usd,
                          prompt_cache_key
                   FROM reconciled_day_set_review
               )
               SELECT COUNT(*) AS total,
                      SUM(attempts) AS attempts,
                      SUM(status = 'complete') AS complete,
                      SUM(status = 'failed') AS failed,
                      SUM(COALESCE(input_tokens, 0)) AS input_tokens,
                      SUM(COALESCE(cached_tokens, 0)) AS cached_tokens,
                      SUM(COALESCE(cache_write_tokens, 0)) AS cache_write_tokens,
                      SUM(COALESCE(output_tokens, 0)) AS output_tokens,
                      SUM(COALESCE(reported_cost_usd, 0)) AS reported_cost_usd,
                      COUNT(DISTINCT prompt_cache_key) AS prompt_cache_keys
               FROM review_request"""
        ).fetchone()
    )
    gate_row = conn.execute(
        "SELECT * FROM quality_gate WHERE singleton = 1"
    ).fetchone()
    counts["selected"] = int(
        conn.execute("SELECT COUNT(*) FROM publication_selection").fetchone()[0]
    )
    counts["editor_selected"] = int(
        conn.execute("SELECT COUNT(*) FROM daily_selection").fetchone()[0]
    )
    counts["suppressed_duplicates"] = int(
        conn.execute("SELECT COUNT(*) FROM suppressed_duplicate").fetchone()[0]
    )
    input_tokens = int(counts["input_tokens"] or 0)
    counts["cache_read_ratio"] = (
        round(int(counts["cached_tokens"] or 0) / input_tokens, 6)
        if input_tokens
        else 0.0
    )
    return {
        "run": run,
        "counts": counts,
        "editor": dict(editor) if editor is not None else None,
        "item_reviews": item_review_counts,
        "day_reviews": day_review_counts,
        "day_set_review": dict(day_review) if day_review is not None else None,
        "reconciled_day_set_review": (
            dict(reconciled_day_review)
            if reconciled_day_review is not None
            else None
        ),
        "selection_reconciliation": (
            dict(reconciliation) if reconciliation is not None else None
        ),
        "quality_gate": (
            json.loads(gate_row["result_json"]) if gate_row is not None else None
        ),
    }


def _prior_history(
    *,
    root: Path,
    audience: str,
    day: str,
) -> list[dict[str, Any]]:
    passed_by_day: dict[
        str, tuple[tuple[str, str, str, str], list[dict[str, Any]]]
    ] = {}
    for path in sorted(root.glob(f"*/{audience}/*/insights.db")):
        conn: sqlite3.Connection | None = None
        try:
            conn = _open_readonly(path)
            run = conn.execute(
                """SELECT meta.day, meta.run_id, meta.created_at,
                          gate.computed_at
                   FROM run_meta AS meta
                   JOIN editor_run AS editor ON editor.singleton = 1
                   JOIN quality_gate AS gate ON gate.singleton = 1
                   WHERE meta.singleton = 1
                     AND editor.status = 'complete'
                     AND gate.passed = 1"""
            ).fetchone()
            if run is None or str(run["day"]) >= day:
                continue
            audit_db = path.parent / "publication-audit-v1" / "audit.db"
            try:
                projection = audience_insight_publication_audit.validated_publication_projection(
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
                # Internal quality is necessary but not sufficient history.
                # Missing, stale, failing, or unadjudicated publication audits
                # must not steer a later day's editorial suppression.
                continue
            run_day = str(run["day"])
            recency_key = (
                str(run["computed_at"]),
                str(run["created_at"]),
                str(run["run_id"]),
                str(path),
            )
            current = passed_by_day.get(run_day)
            if current is None or recency_key > current[0]:
                history_ids = _history_projection_ids(projection)
                passed_by_day[run_day] = (
                    recency_key,
                    selected_history_row(
                        conn,
                        candidate_ids=history_ids,
                    ),
                )
        except sqlite3.Error:
            continue
        finally:
            if conn is not None:
                conn.close()
    return [
        item
        for run_day in sorted(passed_by_day)
        for item in passed_by_day[run_day][1]
    ]


def _explicit_prior_history(
    *,
    prior_run_dbs: Iterable[Path],
    audience: str,
    day: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Resolve an exact ordered history chain before any model request.

    Every source must be an earlier, internally passed run for the requested
    audience. Its exact adjacent publication audit and optional adjacent
    finalization are revalidated; no directory discovery or recency choice is
    involved.
    """
    audience_insights.require_audience(audience)
    try:
        target_day = date.fromisoformat(day)
    except ValueError as exc:
        raise ValueError(f"invalid run day: {day}") from exc
    paths = [Path(value).resolve() for value in prior_run_dbs]
    if not paths:
        raise ValueError("explicit history requires at least one --prior-run-db")
    if len(paths) != len(set(paths)):
        raise ValueError("explicit history contains a duplicate prior run database")

    chain: list[dict[str, Any]] = []
    seen_days: set[str] = set()
    previous_day: date | None = None
    for path in paths:
        conn = _open_readonly(path)
        try:
            run = conn.execute(
                "SELECT audience, day, run_id FROM run_meta WHERE singleton = 1"
            ).fetchone()
            editor = conn.execute(
                "SELECT status FROM editor_run WHERE singleton = 1"
            ).fetchone()
            gate = conn.execute(
                "SELECT passed FROM quality_gate WHERE singleton = 1"
            ).fetchone()
            if run is None:
                raise ValueError(f"prior run is missing run_meta: {path}")
            run_audience = str(run["audience"])
            run_day_text = str(run["day"])
            if run_audience != audience:
                raise ValueError(
                    "prior run audience does not match target audience: "
                    f"{path} ({run_audience} != {audience})"
                )
            try:
                run_day = date.fromisoformat(run_day_text)
            except ValueError as exc:
                raise ValueError(
                    f"prior run has an invalid day: {path} ({run_day_text})"
                ) from exc
            if run_day >= target_day:
                raise ValueError(
                    "prior run day must be earlier than target day: "
                    f"{path} ({run_day_text} >= {day})"
                )
            if run_day_text in seen_days:
                raise ValueError(
                    f"explicit history contains duplicate day {run_day_text}"
                )
            if previous_day is not None and run_day <= previous_day:
                raise ValueError(
                    "--prior-run-db values must be in strictly increasing day order"
                )
            if editor is None or str(editor["status"]) != "complete":
                raise ValueError(f"prior run editor is not complete: {path}")
            if gate is None or int(gate["passed"] or 0) != 1:
                raise ValueError(f"prior run quality gate did not pass: {path}")
            chain.append(
                {
                    "path": path,
                    "run_id": str(run["run_id"]),
                    "day": run_day_text,
                }
            )
            seen_days.add(run_day_text)
            previous_day = run_day
        finally:
            conn.close()

    # Validate publication provenance only after the complete command-level
    # chain has passed audience/day/ordering checks. A malformed chain should
    # fail for its own deterministic input error, not whichever sidecar happens
    # to be inspected first.
    history: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for entry in chain:
        path = entry["path"]
        audit_db = path.parent / ADJACENT_PUBLICATION_AUDIT
        finalization_path = (
            audience_insight_publication_audit.terminal_finalization_path(path)
        )
        try:
            projection = (
                audience_insight_publication_audit.validated_publication_projection(
                    source_run_db=path,
                    audit_db=audit_db,
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
            raise ValueError(
                "prior run has a missing or stale adjacent audit/finalization: "
                f"{path}: {exc}"
            ) from exc
        conn = _open_readonly(path)
        try:
            history_ids = _history_projection_ids(projection)
            selected = selected_history_row(conn, candidate_ids=history_ids)
            if [str(item["selected_item_id"]) for item in selected] != history_ids:
                raise ValueError(
                    f"prior run history projection order is stale: {path}"
                )
            history.extend(selected)
            sources.append(
                {
                    "run_db": _display_path(path),
                    "run_id": entry["run_id"],
                    "day": entry["day"],
                    "audit_db": _display_path(audit_db),
                    "finalization": (
                        _display_path(finalization_path)
                        if finalization_path.is_file()
                        else None
                    ),
                    "projection_mode": str(projection["mode"]),
                    "history_item_count": len(selected),
                }
            )
        finally:
            conn.close()
    return history, {
        "mode": "explicit",
        "sources": sources,
        "prior_item_count": len(history),
        "history_sha256": _sha256(_canonical_json(history)),
    }


def _resolve_history_input(
    *,
    mode: str,
    prior_run_dbs: Iterable[Path],
    audience: str,
    day: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paths = list(prior_run_dbs)
    if mode == "explicit":
        return _explicit_prior_history(
            prior_run_dbs=paths,
            audience=audience,
            day=day,
        )
    if paths:
        raise ValueError("--prior-run-db may be used only with explicit history")
    if mode == "none":
        history: list[dict[str, Any]] = []
    elif mode == "auto":
        history = _prior_history(
            root=DEFAULT_RUN_ROOT,
            audience=audience,
            day=day,
        )
    else:
        raise ValueError(f"unsupported history mode: {mode}")
    return history, {
        "mode": mode,
        "sources": [],
        "prior_item_count": len(history),
        "history_sha256": _sha256(_canonical_json(history)),
    }


def _result(command: str, data: Any) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "command": command,
        "status": "ok",
        "data": data,
        "error": None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fli audience-insights")
    sub = parser.add_subparsers(dest="action", required=True)

    run_parser = sub.add_parser(
        "run", help="Freeze, extract, and edit one audience/day run."
    )
    run_parser.add_argument("--run-id", required=True)
    run_parser.add_argument("--run-db", type=Path)
    run_parser.add_argument("--audience", choices=audience_insights.AUDIENCES, required=True)
    run_parser.add_argument("--day", required=True)
    run_parser.add_argument("--rank-limit", type=int, default=DEFAULT_RANK_LIMIT)
    run_parser.add_argument("--triage-db", type=Path)
    run_parser.add_argument("--artifact-db", type=Path, default=DEFAULT_ARTIFACT_DB)
    run_parser.add_argument("--model", default=audience_insights.DEFAULT_MODEL)
    run_parser.add_argument(
        "--input-render-version",
        choices=audience_insights.INPUT_RENDER_VERSIONS,
        help=(
            "Persist the model-input rendering contract for a new run. "
            "Existing pre-column runs remain verbatim-v1."
        ),
    )
    run_parser.add_argument(
        "--reasoning-effort",
        help=(
            "Override the audience default (Investment: high; "
            "AI Engineering: medium)."
        ),
    )
    run_parser.add_argument("--editor-model", default=audience_insights.DEFAULT_MODEL)
    run_parser.add_argument(
        "--editor-reasoning-effort", default=audience_insights.DEFAULT_EDITOR_EFFORT
    )
    run_parser.add_argument(
        "--review-model", default=audience_insight_evaluations.DEFAULT_MODEL
    )
    run_parser.add_argument(
        "--review-reasoning-effort",
        default=audience_insight_evaluations.DEFAULT_REASONING_EFFORT,
    )
    run_parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    run_parser.add_argument(
        "--review-workers", type=int, default=DEFAULT_REVIEW_WORKERS
    )
    run_parser.add_argument("--retry-failed", action="store_true")
    run_parser.add_argument("--skip-editor", action="store_true")
    run_parser.add_argument("--skip-quality", action="store_true")
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument(
        "--history-mode",
        choices=HISTORY_MODES,
        help=(
            "Required unless --prior-run-db infers explicit mode. Use explicit "
            "for production, none only at a history origin, and auto only for "
            "non-production discovery."
        ),
    )
    run_parser.add_argument(
        "--prior-run-db",
        type=Path,
        action="append",
        default=[],
        help=(
            "Exact earlier audience run DB, repeated in strictly increasing day "
            "order. Its adjacent audit/finalization is revalidated before model calls."
        ),
    )

    summary_parser = sub.add_parser("summary", help="Inspect one immutable run.")
    summary_parser.add_argument("--run-db", type=Path, required=True)

    args = parser.parse_args(argv)
    started = time.monotonic()
    command = f"audience-insights.{args.action}"
    try:
        if args.action == "summary":
            conn = connect_run(args.run_db)
            data = summary(conn)
            conn.close()
        else:
            history_mode = args.history_mode
            if args.prior_run_db and history_mode is None:
                history_mode = "explicit"
            if history_mode is None:
                raise ValueError(
                    "run requires --history-mode or at least one --prior-run-db; "
                    "production chronology must not use implicit directory recency"
                )
            history, history_input = _resolve_history_input(
                mode=history_mode,
                prior_run_dbs=args.prior_run_db,
                audience=args.audience,
                day=args.day,
            )
            run_db = args.run_db or default_run_db(
                day=args.day,
                audience=args.audience,
                run_id=args.run_id,
            )
            conn = connect_run(run_db)
            freeze_run(
                conn,
                run_id=args.run_id,
                audience=args.audience,
                day=args.day,
                rank_limit=args.rank_limit,
                triage_db=args.triage_db,
                artifact_db=args.artifact_db,
                model=args.model,
                effort=args.reasoning_effort,
                editor_model=args.editor_model,
                editor_effort=args.editor_reasoning_effort,
                review_model=args.review_model,
                review_effort=args.review_reasoning_effort,
                input_render_version=args.input_render_version,
            )
            existing_editor = conn.execute(
                "SELECT history_sha256, prior_selected_json "
                "FROM editor_run WHERE singleton = 1"
            ).fetchone()
            if existing_editor is not None and (
                str(existing_editor["history_sha256"])
                != str(history_input["history_sha256"])
                or str(existing_editor["prior_selected_json"])
                != _canonical_json(history)
            ):
                raise ValueError(
                    "resolved history does not match the existing frozen editor input"
                )
            if args.dry_run:
                data = summary(conn)
                data["will_call_model"] = False
            else:
                client = entity_kinds.create_litellm_client()
                if hasattr(client, "with_options"):
                    client = client.with_options(max_retries=0, timeout=300.0)
                extraction = run_pending(
                    conn,
                    client=client,
                    workers=args.workers,
                    retry_failed=args.retry_failed,
                )
                if (
                    not args.retry_failed
                    and int(extraction["counts"]["failed"] or 0) > 0
                ):
                    run_pending(
                        conn,
                        client=client,
                        workers=args.workers,
                        retry_failed=True,
                    )
                if not args.skip_editor:
                    run_item_reviews(
                        conn,
                        client=client,
                        workers=args.review_workers,
                    )
                    prepare_editor(conn, prior_selected=history)
                    run_editor(conn, client=client)
                    if not args.skip_quality:
                        run_quality_reviews(
                            conn,
                            client=client,
                            workers=args.review_workers,
                        )
                data = summary(conn)
            data["history_input"] = history_input
            data["run_db"] = _display_path(run_db)
            conn.close()
    except (FileNotFoundError, RuntimeError, sqlite3.Error, ValueError) as exc:
        print(
            _canonical_json(
                {
                    "schema_version": "2.0",
                    "command": command,
                    "status": "error",
                    "data": None,
                    "error": {"code": "E_INVALID_INPUT", "message": str(exc)},
                }
            )
        )
        return 2
    data["duration_ms"] = round((time.monotonic() - started) * 1000)
    print(_canonical_json(_result(command, data)))
    if args.action == "run" and int(data["counts"]["failed"] or 0):
        return 3
    if (
        args.action == "run"
        and not args.dry_run
        and not args.skip_editor
        and not args.skip_quality
        and not bool((data.get("quality_gate") or {}).get("passed"))
    ):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
