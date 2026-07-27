"""Resumable bulk execution for the read-only Registry evaluator."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from fli import llm_responses, store
from fli.ingestion import sources
from fli.ingestion.x import content as x_content
from fli.registry import classification as entity_kinds
from fli.registry import evaluation as registry_evaluation
from fli.registry import identity_contexts

DEFAULT_MODEL = registry_evaluation.DEFAULT_MODEL
DEFAULT_EFFORT = registry_evaluation.DEFAULT_REASONING_EFFORT
DEFAULT_FETCH_WORKERS = 20
DEFAULT_FETCH_QPS = 9.0
DEFAULT_MODEL_WORKERS = registry_evaluation.PROMPT_CACHE_SHARDS
DEFAULT_IDENTITY_WORKERS = identity_contexts.PROMPT_CACHE_SHARDS
DEFAULT_POST_LIMIT = 20

RUN_SCHEMA = """
CREATE TABLE IF NOT EXISTS run_meta (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    run_id TEXT NOT NULL,
    model TEXT NOT NULL,
    reasoning_effort TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    prompt_sha256 TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    cohort_sha256 TEXT NOT NULL,
    expected_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evaluation_item (
    entity_id INTEGER PRIMARY KEY,
    handle TEXT NOT NULL,
    display_name TEXT NOT NULL,
    bio TEXT,
    profile_url TEXT NOT NULL,
    prompt_cache_key TEXT NOT NULL,
    evidence_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (evidence_status IN ('pending', 'complete', 'failed')),
    evidence_json TEXT,
    evidence_sha256 TEXT,
    evidence_bundle_id TEXT,
    evidence_fetched_at TEXT,
    evidence_error_type TEXT,
    evidence_error TEXT,
    evaluation_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (evaluation_status IN ('pending', 'complete', 'failed')),
    evaluation_attempts INTEGER NOT NULL DEFAULT 0,
    input_sha256 TEXT,
    kind TEXT,
    kind_reason TEXT,
    registry_decision TEXT,
    registry_decision_reason TEXT,
    response_id TEXT,
    response_model TEXT,
    input_tokens INTEGER,
    cached_tokens INTEGER,
    cache_write_tokens INTEGER,
    output_tokens INTEGER,
    reported_cost_usd REAL,
    web_action_count INTEGER,
    source_count INTEGER,
    result_json TEXT,
    evaluation_error_type TEXT,
    evaluation_error TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_evaluation_item_evidence
    ON evaluation_item (evidence_status, entity_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_item_status
    ON evaluation_item (evaluation_status, entity_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_item_cache_key
    ON evaluation_item (prompt_cache_key, entity_id);

CREATE TABLE IF NOT EXISTS identity_context (
    entity_id INTEGER PRIMARY KEY REFERENCES evaluation_item (entity_id)
        ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'complete', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    input_sha256 TEXT,
    context_json TEXT,
    identity_status TEXT,
    canonical_name TEXT,
    current_role TEXT,
    current_organization TEXT,
    known_for_json TEXT,
    frontier_ai_relevance TEXT,
    research_summary TEXT,
    response_id TEXT,
    response_model TEXT,
    input_tokens INTEGER,
    cached_tokens INTEGER,
    cache_write_tokens INTEGER,
    output_tokens INTEGER,
    reported_cost_usd REAL,
    web_action_count INTEGER,
    source_count INTEGER,
    result_json TEXT,
    error_type TEXT,
    error TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_identity_context_status
    ON identity_context (status, entity_id);
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


def connect_run(path: Path | str, *, check_same_thread: bool = True) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60.0, check_same_thread=check_same_thread)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.executescript(RUN_SCHEMA)
    return conn


def read_active_inputs(conn: sqlite3.Connection) -> list[registry_evaluation.EvaluationInput]:
    """Choose one deterministic representative X channel per active entity."""
    rows = conn.execute(
        """WITH candidates AS (
               SELECT e.id AS entity_id,
                      e.name AS entity_name,
                      e.slug,
                      c.key AS handle,
                      COALESCE(a.display_name, c.label, e.name) AS display_name,
                      a.bio,
                      COALESCE(c.url, 'https://x.com/' || c.key) AS profile_url,
                      COALESCE(a.followers_count, 0) AS followers_count,
                      ROW_NUMBER() OVER (
                          PARTITION BY e.id
                          ORDER BY
                              CASE
                                  WHEN lower(c.key) = lower(e.slug) THEN 0
                                  WHEN lower(COALESCE(a.display_name, c.label, ''))
                                       = lower(e.name) THEN 1
                                  ELSE 2
                              END,
                              COALESCE(a.followers_count, 0) DESC,
                              c.key
                      ) AS choice_rank
               FROM entities e
               JOIN entity_channels ec ON ec.entity_id = e.id
               JOIN channels c ON c.id = ec.channel_id AND c.kind = 'x'
               LEFT JOIN accounts a
                 ON a.platform = 'x' AND lower(a.handle) = lower(c.key)
               WHERE e.kind IN ('person', 'organization')
                 AND NOT EXISTS (
                     SELECT 1 FROM entity_registry_rejections r
                     WHERE r.entity_id = e.id
                 )
           )
           SELECT entity_id, handle, display_name, bio, profile_url
           FROM candidates
           WHERE choice_rank = 1
           ORDER BY entity_id"""
    ).fetchall()
    return [
        registry_evaluation.EvaluationInput(
            entity_id=row["entity_id"],
            handle=row["handle"],
            display_name=row["display_name"],
            bio=row["bio"] or None,
            profile_url=row["profile_url"],
        )
        for row in rows
    ]


def freeze_run(
    registry_conn: sqlite3.Connection,
    run_conn: sqlite3.Connection,
    *,
    run_id: str,
    model: str,
    effort: str,
) -> int:
    inputs = read_active_inputs(registry_conn)
    cohort_payload = [
        {
            "entity_id": item.entity_id,
            "handle": item.handle,
            "display_name": item.display_name,
            "bio": item.bio,
            "profile_url": item.profile_url,
        }
        for item in inputs
    ]
    cohort_sha256 = _sha256(_canonical_json(cohort_payload))
    expected = {
        "run_id": run_id,
        "model": model,
        "reasoning_effort": effort,
        "prompt_version": registry_evaluation.PROMPT_VERSION,
        "prompt_sha256": registry_evaluation.prompt_sha256(),
        "schema_version": registry_evaluation.SCHEMA_VERSION,
        "cohort_sha256": cohort_sha256,
        "expected_count": len(inputs),
    }
    existing = run_conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if existing is not None:
        mismatches = [key for key, value in expected.items() if existing[key] != value]
        if mismatches:
            raise ValueError(
                "run database does not match current request: " + ", ".join(mismatches)
            )
        return len(inputs)

    now = _now()
    with run_conn:
        run_conn.execute(
            """INSERT INTO run_meta
               (singleton, run_id, model, reasoning_effort, prompt_version,
                prompt_sha256, schema_version, cohort_sha256, expected_count,
                created_at, updated_at)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                model,
                effort,
                registry_evaluation.PROMPT_VERSION,
                registry_evaluation.prompt_sha256(),
                registry_evaluation.SCHEMA_VERSION,
                cohort_sha256,
                len(inputs),
                now,
                now,
            ),
        )
        run_conn.executemany(
            """INSERT INTO evaluation_item
               (entity_id, handle, display_name, bio, profile_url,
                prompt_cache_key, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    item.entity_id,
                    item.handle,
                    item.display_name,
                    item.bio,
                    item.profile_url,
                    registry_evaluation.prompt_cache_key(item.entity_id),
                    now,
                )
                for item in inputs
            ],
        )
    return len(inputs)


def freeze_run_from_results(
    source_conn: sqlite3.Connection,
    run_conn: sqlite3.Connection,
    *,
    run_id: str,
    model: str,
    effort: str,
    source_kind: str,
    source_decision: str,
) -> int:
    """Freeze a filtered comparison cohort with the source run's exact evidence."""
    source_meta = source_conn.execute(
        "SELECT * FROM run_meta WHERE singleton = 1"
    ).fetchone()
    if source_meta is None:
        raise ValueError("source run has no metadata")
    rows = source_conn.execute(
        """SELECT entity_id, handle, display_name, bio, profile_url,
                  prompt_cache_key, evidence_json, evidence_sha256,
                  evidence_bundle_id, evidence_fetched_at
           FROM evaluation_item
           WHERE evidence_status = 'complete'
             AND evaluation_status = 'complete'
             AND kind = ?
             AND registry_decision = ?
           ORDER BY entity_id""",
        (source_kind, source_decision),
    ).fetchall()
    if not rows:
        raise ValueError("source filter selected no completed results")

    cohort_payload = [
        {
            "entity_id": row["entity_id"],
            "handle": row["handle"],
            "evidence_sha256": row["evidence_sha256"],
        }
        for row in rows
    ]
    cohort_sha256 = _sha256(_canonical_json(cohort_payload))
    expected = {
        "run_id": run_id,
        "model": model,
        "reasoning_effort": effort,
        "prompt_version": registry_evaluation.PROMPT_VERSION,
        "prompt_sha256": registry_evaluation.prompt_sha256(),
        "schema_version": registry_evaluation.SCHEMA_VERSION,
        "cohort_sha256": cohort_sha256,
        "expected_count": len(rows),
    }
    existing = run_conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if existing is not None:
        mismatches = [key for key, value in expected.items() if existing[key] != value]
        if mismatches:
            raise ValueError(
                "run database does not match current request: " + ", ".join(mismatches)
            )
        return len(rows)

    now = _now()
    with run_conn:
        run_conn.execute(
            """INSERT INTO run_meta
               (singleton, run_id, model, reasoning_effort, prompt_version,
                prompt_sha256, schema_version, cohort_sha256, expected_count,
                created_at, updated_at)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                model,
                effort,
                registry_evaluation.PROMPT_VERSION,
                registry_evaluation.prompt_sha256(),
                registry_evaluation.SCHEMA_VERSION,
                cohort_sha256,
                len(rows),
                now,
                now,
            ),
        )
        run_conn.executemany(
            """INSERT INTO evaluation_item
               (entity_id, handle, display_name, bio, profile_url,
                prompt_cache_key, evidence_status, evidence_json,
                evidence_sha256, evidence_bundle_id, evidence_fetched_at,
                updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'complete', ?, ?, ?, ?, ?)""",
            [
                (
                    row["entity_id"],
                    row["handle"],
                    row["display_name"],
                    row["bio"],
                    row["profile_url"],
                    registry_evaluation.prompt_cache_key(row["entity_id"]),
                    row["evidence_json"],
                    row["evidence_sha256"],
                    row["evidence_bundle_id"],
                    row["evidence_fetched_at"],
                    now,
                )
                for row in rows
            ],
        )
    return len(rows)


class RequestStartLimiter:
    def __init__(self, requests_per_second: float) -> None:
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        self.interval = 1.0 / requests_per_second
        self.next_start = 0.0
        self.lock = threading.Lock()

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            start_at = max(now, self.next_start)
            self.next_start = start_at + self.interval
        if start_at > now:
            time.sleep(start_at - now)


def collect_evidence(
    run_conn: sqlite3.Connection,
    *,
    post_client: Any,
    workers: int = DEFAULT_FETCH_WORKERS,
    requests_per_second: float = DEFAULT_FETCH_QPS,
    post_limit: int = DEFAULT_POST_LIMIT,
) -> dict[str, int]:
    pending = run_conn.execute(
        """SELECT entity_id, handle
           FROM evaluation_item
           WHERE evidence_status != 'complete'
           ORDER BY entity_id"""
    ).fetchall()
    limiter = RequestStartLimiter(requests_per_second)

    def fetch(row: sqlite3.Row) -> tuple[sqlite3.Row, tuple[dict[str, Any], ...]]:
        limiter.wait()
        posts = post_client.fetch_recent_authored_posts(
            username=row["handle"],
            limit=post_limit,
            profile={"isProtected": False},
        )
        return row, posts

    complete = 0
    failed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch, row): row for row in pending}
        for processed, future in enumerate(
            concurrent.futures.as_completed(futures), start=1
        ):
            row = futures[future]
            now = _now()
            try:
                _, posts = future.result()
                evidence_json = _canonical_json(list(posts))
                bundle_id = (
                    post_client.store_post_bundle(
                        username=row["handle"],
                        posts=posts,
                        requested_limit=post_limit,
                    )
                    if hasattr(post_client, "store_post_bundle")
                    else None
                )
                with run_conn:
                    run_conn.execute(
                        """UPDATE evaluation_item
                           SET evidence_status = 'complete', evidence_json = ?,
                               evidence_sha256 = ?, evidence_bundle_id = ?,
                               evidence_fetched_at = ?,
                               evidence_error_type = NULL, evidence_error = NULL,
                               updated_at = ?
                           WHERE entity_id = ?""",
                        (
                            evidence_json,
                            _sha256(evidence_json),
                            bundle_id,
                            now,
                            now,
                            row["entity_id"],
                        ),
                    )
                complete += 1
            except Exception as exc:
                with run_conn:
                    run_conn.execute(
                        """UPDATE evaluation_item
                           SET evidence_status = 'failed', evidence_error_type = ?,
                               evidence_error = ?, updated_at = ?
                           WHERE entity_id = ?""",
                        (type(exc).__name__, str(exc), now, row["entity_id"]),
                    )
                failed += 1
            if processed % 100 == 0 or processed == len(pending):
                print(
                    _canonical_json(
                        {
                            "stage": "evidence",
                            "processed": processed,
                            "pending_at_start": len(pending),
                            "complete_this_run": complete,
                            "failed_this_run": failed,
                        }
                    ),
                    flush=True,
                )
    return {"pending_at_start": len(pending), "complete": complete, "failed": failed}


def collect_identity_contexts(
    run_conn: sqlite3.Connection,
    *,
    model: str,
    effort: str,
    run_id: str,
    workers: int = DEFAULT_IDENTITY_WORKERS,
    client_factory: Callable[[], Any] = entity_kinds.create_litellm_client,
    enricher: Callable[..., dict[str, Any]] = identity_contexts.enrich_one,
) -> dict[str, int]:
    """Ground missing biographies before their pending Registry evaluation."""
    rows = run_conn.execute(
        """SELECT item.*
           FROM evaluation_item item
           LEFT JOIN identity_context context
             ON context.entity_id = item.entity_id
           WHERE item.evidence_status = 'complete'
             AND item.evaluation_status != 'complete'
             AND (item.bio IS NULL OR trim(item.bio) = '')
             AND (context.status IS NULL OR context.status != 'complete')
           ORDER BY item.entity_id"""
    ).fetchall()
    by_key = llm_responses.group_prompt_cache_lanes(
        rows,
        lambda row: identity_contexts.prompt_cache_key(row["entity_id"]),
    )

    write_lock = threading.Lock()
    progress_lock = threading.Lock()
    progress = {"processed": 0, "complete": 0, "failed": 0}

    def persist_success(row: sqlite3.Row, result: dict[str, Any]) -> None:
        now = _now()
        context = {
            field: result[field]
            for field in identity_contexts.OUTPUT_FORMAT["schema"]["required"]
        }
        context["consulted_sources"] = result["consulted_sources"]
        with write_lock, run_conn:
            run_conn.execute(
                """INSERT INTO identity_context
                   (entity_id, status, attempts, input_sha256, context_json,
                    identity_status, canonical_name, current_role,
                    current_organization, known_for_json,
                    frontier_ai_relevance, research_summary, response_id,
                    response_model, input_tokens, cached_tokens,
                    cache_write_tokens, output_tokens, reported_cost_usd,
                    web_action_count, source_count, result_json, error_type,
                    error, completed_at, updated_at)
                   VALUES (?, 'complete', 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                           ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
                   ON CONFLICT(entity_id) DO UPDATE SET
                       status = 'complete', attempts = identity_context.attempts + 1,
                       input_sha256 = excluded.input_sha256,
                       context_json = excluded.context_json,
                       identity_status = excluded.identity_status,
                       canonical_name = excluded.canonical_name,
                       current_role = excluded.current_role,
                       current_organization = excluded.current_organization,
                       known_for_json = excluded.known_for_json,
                       frontier_ai_relevance = excluded.frontier_ai_relevance,
                       research_summary = excluded.research_summary,
                       response_id = excluded.response_id,
                       response_model = excluded.response_model,
                       input_tokens = excluded.input_tokens,
                       cached_tokens = excluded.cached_tokens,
                       cache_write_tokens = excluded.cache_write_tokens,
                       output_tokens = excluded.output_tokens,
                       reported_cost_usd = excluded.reported_cost_usd,
                       web_action_count = excluded.web_action_count,
                       source_count = excluded.source_count,
                       result_json = excluded.result_json,
                       error_type = NULL, error = NULL,
                       completed_at = excluded.completed_at,
                       updated_at = excluded.updated_at""",
                (
                    row["entity_id"],
                    result["input_sha256"],
                    _canonical_json(context),
                    result["identity_status"],
                    result["canonical_name"],
                    result["current_role"],
                    result["current_organization"],
                    _canonical_json(result["known_for"]),
                    result["frontier_ai_relevance"],
                    result["research_summary"],
                    result["response_id"],
                    result["response_model"],
                    result["input_tokens"],
                    result["cached_tokens"],
                    result["cache_write_tokens"],
                    result["output_tokens"],
                    result["reported_cost_usd"],
                    len(result["web_actions"]),
                    len(result["consulted_sources"]),
                    _canonical_json(result),
                    now,
                    now,
                ),
            )

    def persist_error(row: sqlite3.Row, exc: Exception) -> None:
        now = _now()
        with write_lock, run_conn:
            run_conn.execute(
                """INSERT INTO identity_context
                   (entity_id, status, attempts, error_type, error, updated_at)
                   VALUES (?, 'failed', 1, ?, ?, ?)
                   ON CONFLICT(entity_id) DO UPDATE SET
                       status = 'failed',
                       attempts = identity_context.attempts + 1,
                       error_type = excluded.error_type,
                       error = excluded.error,
                       updated_at = excluded.updated_at""",
                (row["entity_id"], type(exc).__name__, str(exc), now),
            )

    def note(success: bool) -> None:
        with progress_lock:
            progress["processed"] += 1
            progress["complete" if success else "failed"] += 1
            if progress["processed"] % 50 == 0 or progress["processed"] == len(rows):
                print(
                    _canonical_json(
                        {
                            "stage": "identity-context",
                            "processed": progress["processed"],
                            "pending_at_start": len(rows),
                            "complete_this_run": progress["complete"],
                            "failed_this_run": progress["failed"],
                        }
                    ),
                    flush=True,
                )

    def run_lane(lane: list[sqlite3.Row]) -> None:
        client = client_factory()
        if hasattr(client, "with_options"):
            client = client.with_options(max_retries=0)
        for row in lane:
            entity = identity_contexts.IdentityInput(
                entity_id=row["entity_id"],
                handle=row["handle"],
                display_name=row["display_name"],
                profile_url=row["profile_url"],
                recent_posts=tuple(json.loads(row["evidence_json"])),
            )
            try:
                result = enricher(
                    client,
                    entity,
                    run=run_id,
                    model=model,
                    effort=effort,
                )
                persist_success(row, result)
                note(True)
            except Exception as exc:
                persist_error(row, exc)
                note(False)

    if rows:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(workers, len(by_key))
        ) as executor:
            futures = [executor.submit(run_lane, lane) for lane in by_key.values()]
            for future in concurrent.futures.as_completed(futures):
                future.result()
    return {
        "pending_at_start": len(rows),
        "complete": progress["complete"],
        "failed": progress["failed"],
    }


def evaluate_pending(
    run_conn: sqlite3.Connection,
    *,
    model: str,
    effort: str,
    run_id: str,
    workers: int = DEFAULT_MODEL_WORKERS,
    client_factory: Callable[[], Any] = entity_kinds.create_litellm_client,
    evaluator: Callable[..., dict[str, Any]] = registry_evaluation.evaluate_one,
) -> dict[str, int]:
    rows = run_conn.execute(
        """SELECT item.*, context.context_json AS identity_context_json
           FROM evaluation_item item
           LEFT JOIN identity_context context
             ON context.entity_id = item.entity_id
           WHERE item.evidence_status = 'complete'
             AND item.evaluation_status != 'complete'
             AND (
                 (item.bio IS NOT NULL AND trim(item.bio) != '')
                 OR context.status = 'complete'
             )
           ORDER BY item.prompt_cache_key, item.entity_id"""
    ).fetchall()
    by_key = llm_responses.group_prompt_cache_lanes(
        rows,
        lambda row: str(row["prompt_cache_key"]),
    )

    write_lock = threading.Lock()
    progress_lock = threading.Lock()
    progress = {"processed": 0, "complete": 0, "failed": 0}

    def persist_success(row: sqlite3.Row, result: dict[str, Any]) -> None:
        now = _now()
        with write_lock, run_conn:
            run_conn.execute(
                """UPDATE evaluation_item
                   SET evaluation_status = 'complete',
                       evaluation_attempts = evaluation_attempts + 1,
                       input_sha256 = ?, kind = ?, kind_reason = ?,
                       registry_decision = ?, registry_decision_reason = ?,
                       response_id = ?, response_model = ?, input_tokens = ?,
                       cached_tokens = ?, cache_write_tokens = ?, output_tokens = ?,
                       reported_cost_usd = ?, web_action_count = ?, source_count = ?,
                       result_json = ?, evaluation_error_type = NULL,
                       evaluation_error = NULL, completed_at = ?, updated_at = ?
                   WHERE entity_id = ?""",
                (
                    result["input_sha256"],
                    result["kind"],
                    result["kind_reason"],
                    result["registry_decision"],
                    result["registry_decision_reason"],
                    result["response_id"],
                    result["response_model"],
                    result["input_tokens"],
                    result["cached_tokens"],
                    result["cache_write_tokens"],
                    result["output_tokens"],
                    result["reported_cost_usd"],
                    len(result["web_actions"]),
                    len(result["consulted_sources"]),
                    _canonical_json(result),
                    now,
                    now,
                    row["entity_id"],
                ),
            )

    def persist_error(row: sqlite3.Row, exc: Exception) -> None:
        with write_lock, run_conn:
            run_conn.execute(
                """UPDATE evaluation_item
                   SET evaluation_status = 'failed',
                       evaluation_attempts = evaluation_attempts + 1,
                       evaluation_error_type = ?, evaluation_error = ?, updated_at = ?
                   WHERE entity_id = ?""",
                (type(exc).__name__, str(exc), _now(), row["entity_id"]),
            )

    def note(success: bool) -> None:
        with progress_lock:
            progress["processed"] += 1
            progress["complete" if success else "failed"] += 1
            if progress["processed"] % 100 == 0 or progress["processed"] == len(rows):
                print(
                    _canonical_json(
                        {
                            "stage": "evaluation",
                            "processed": progress["processed"],
                            "pending_at_start": len(rows),
                            "complete_this_run": progress["complete"],
                            "failed_this_run": progress["failed"],
                        }
                    ),
                    flush=True,
                )

    def run_lane(lane: list[sqlite3.Row]) -> None:
        client = client_factory()
        if hasattr(client, "with_options"):
            client = client.with_options(max_retries=0)
        for row in lane:
            posts = tuple(json.loads(row["evidence_json"]))
            entity = registry_evaluation.EvaluationInput(
                entity_id=row["entity_id"],
                handle=row["handle"],
                display_name=row["display_name"],
                bio=row["bio"],
                profile_url=row["profile_url"],
                recent_posts=posts,
                identity_context=(
                    json.loads(row["identity_context_json"])
                    if row["identity_context_json"]
                    else None
                ),
            )
            try:
                result = evaluator(
                    client,
                    entity,
                    run=run_id,
                    model=model,
                    effort=effort,
                )
                persist_success(row, result)
                note(True)
            except Exception as exc:
                persist_error(row, exc)
                note(False)

    if rows:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(workers, len(by_key))
        ) as executor:
            futures = [executor.submit(run_lane, lane) for lane in by_key.values()]
            for future in concurrent.futures.as_completed(futures):
                future.result()
    return {
        "pending_at_start": len(rows),
        "complete": progress["complete"],
        "failed": progress["failed"],
    }


def status(run_conn: sqlite3.Connection) -> dict[str, Any]:
    meta = run_conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("run database has not been initialized")
    counts = run_conn.execute(
        """SELECT COUNT(*) AS total,
                  SUM(evidence_status = 'complete') AS evidence_complete,
                  SUM(evidence_status = 'failed') AS evidence_failed,
                  SUM(evaluation_status = 'complete') AS evaluation_complete,
                  SUM(evaluation_status = 'failed') AS evaluation_failed,
                  SUM(CASE WHEN evaluation_status = 'complete'
                           THEN COALESCE(reported_cost_usd, 0) ELSE 0 END) AS cost,
                  SUM(CASE WHEN evaluation_status = 'complete'
                           THEN COALESCE(input_tokens, 0) ELSE 0 END) AS input_tokens,
                  SUM(CASE WHEN evaluation_status = 'complete'
                           THEN COALESCE(cached_tokens, 0) ELSE 0 END) AS cached_tokens,
                  SUM(CASE WHEN evaluation_status = 'complete'
                           THEN COALESCE(output_tokens, 0) ELSE 0 END) AS output_tokens,
                  SUM(CASE WHEN evaluation_status = 'complete'
                           THEN COALESCE(web_action_count, 0) ELSE 0 END) AS web_actions
           FROM evaluation_item"""
    ).fetchone()
    decisions = {
        row["registry_decision"]: row["n"]
        for row in run_conn.execute(
            """SELECT registry_decision, COUNT(*) AS n
               FROM evaluation_item
               WHERE evaluation_status = 'complete'
               GROUP BY registry_decision
               ORDER BY registry_decision"""
        )
    }
    kinds = {
        row["kind"]: row["n"]
        for row in run_conn.execute(
            """SELECT kind, COUNT(*) AS n
               FROM evaluation_item
               WHERE evaluation_status = 'complete'
               GROUP BY kind
               ORDER BY kind"""
        )
    }
    identity = run_conn.execute(
        """SELECT COUNT(*) AS requested,
                  SUM(status = 'complete') AS complete,
                  SUM(status = 'failed') AS failed,
                  SUM(CASE WHEN status = 'complete'
                           THEN COALESCE(reported_cost_usd, 0) ELSE 0 END) AS cost,
                  SUM(CASE WHEN status = 'complete'
                           THEN COALESCE(input_tokens, 0) ELSE 0 END) AS input_tokens,
                  SUM(CASE WHEN status = 'complete'
                           THEN COALESCE(cached_tokens, 0) ELSE 0 END) AS cached_tokens,
                  SUM(CASE WHEN status = 'complete'
                           THEN COALESCE(output_tokens, 0) ELSE 0 END) AS output_tokens,
                  SUM(CASE WHEN status = 'complete'
                           THEN COALESCE(web_action_count, 0) ELSE 0 END) AS web_actions
           FROM identity_context"""
    ).fetchone()
    return {
        "run_id": meta["run_id"],
        "model": meta["model"],
        "reasoning_effort": meta["reasoning_effort"],
        "prompt_version": meta["prompt_version"],
        "cohort_sha256": meta["cohort_sha256"],
        "total": counts["total"],
        "evidence_complete": counts["evidence_complete"] or 0,
        "evidence_failed": counts["evidence_failed"] or 0,
        "evaluation_complete": counts["evaluation_complete"] or 0,
        "evaluation_failed": counts["evaluation_failed"] or 0,
        "reported_cost_usd": counts["cost"] or 0,
        "input_tokens": counts["input_tokens"] or 0,
        "cached_tokens": counts["cached_tokens"] or 0,
        "output_tokens": counts["output_tokens"] or 0,
        "web_actions": counts["web_actions"] or 0,
        "identity_context_requested": identity["requested"] or 0,
        "identity_context_complete": identity["complete"] or 0,
        "identity_context_failed": identity["failed"] or 0,
        "identity_context_reported_cost_usd": identity["cost"] or 0,
        "identity_context_input_tokens": identity["input_tokens"] or 0,
        "identity_context_cached_tokens": identity["cached_tokens"] or 0,
        "identity_context_output_tokens": identity["output_tokens"] or 0,
        "identity_context_web_actions": identity["web_actions"] or 0,
        "decisions": decisions,
        "kinds": kinds,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fli registry-evaluation")
    sub = parser.add_subparsers(dest="action", required=True)
    run_p = sub.add_parser("run", help="Run or resume a cached active-Registry audit.")
    run_p.add_argument("--registry-db", type=Path, default=store.DEFAULT_DB_PATH)
    run_p.add_argument("--run-db", type=Path, required=True)
    run_p.add_argument("--run-id", required=True)
    run_p.add_argument("--all", action="store_true")
    run_p.add_argument(
        "--source-run-db",
        type=Path,
        help="Reuse exact evidence from a completed filtered comparison cohort.",
    )
    run_p.add_argument("--source-kind", choices=("person", "organization", "unsure"))
    run_p.add_argument("--source-decision", choices=("keep", "remove", "review"))
    run_p.add_argument("--model", default=DEFAULT_MODEL)
    run_p.add_argument("--reasoning-effort", default=DEFAULT_EFFORT)
    run_p.add_argument(
        "--identity-model",
        help="Optional model override for missing-bio identity research.",
    )
    run_p.add_argument("--fetch-workers", type=int, default=DEFAULT_FETCH_WORKERS)
    run_p.add_argument("--fetch-qps", type=float, default=DEFAULT_FETCH_QPS)
    run_p.add_argument("--model-workers", type=int, default=DEFAULT_MODEL_WORKERS)
    run_p.add_argument(
        "--identity-workers", type=int, default=DEFAULT_IDENTITY_WORKERS
    )
    run_p.add_argument(
        "--x-content-db",
        type=Path,
        default=x_content.DEFAULT_DB_PATH,
    )
    run_p.add_argument("--x-content-max-age-hours", type=float, default=24.0)
    run_p.add_argument("--refresh-x-content", action="store_true")
    status_p = sub.add_parser("status", help="Inspect a cached evaluation run.")
    status_p.add_argument("--run-db", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.action == "status":
        print(json.dumps(status(connect_run(args.run_db)), sort_keys=True))
        return 0
    if not args.all:
        parser.error("paid bulk execution requires explicit --all")
    for name in (
        "fetch_workers",
        "fetch_qps",
        "model_workers",
        "identity_workers",
        "x_content_max_age_hours",
    ):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} must be positive")

    run_conn = connect_run(args.run_db, check_same_thread=False)
    if args.source_run_db is not None:
        if args.source_kind is None or args.source_decision is None:
            parser.error(
                "--source-run-db requires --source-kind and --source-decision"
            )
        if args.source_run_db.resolve() == args.run_db.resolve():
            parser.error("--source-run-db and --run-db must be different files")
        source_conn = sqlite3.connect(
            f"file:{args.source_run_db.resolve()}?mode=ro", uri=True
        )
        source_conn.row_factory = sqlite3.Row
        frozen = freeze_run_from_results(
            source_conn,
            run_conn,
            run_id=args.run_id,
            model=args.model,
            effort=args.reasoning_effort,
            source_kind=args.source_kind,
            source_decision=args.source_decision,
        )
    else:
        if args.source_kind is not None or args.source_decision is not None:
            parser.error("source filters require --source-run-db")
        registry_conn = sqlite3.connect(
            f"file:{args.registry_db.resolve()}?mode=ro", uri=True
        )
        registry_conn.row_factory = sqlite3.Row
        frozen = freeze_run(
            registry_conn,
            run_conn,
            run_id=args.run_id,
            model=args.model,
            effort=args.reasoning_effort,
        )
    print(_canonical_json({"stage": "freeze", "entities": frozen}), flush=True)
    if args.source_run_db is None:
        limiter = RequestStartLimiter(args.fetch_qps)
        post_client = x_content.create_client(
            db_path=args.x_content_db,
            max_age=timedelta(hours=args.x_content_max_age_hours),
            refresh=args.refresh_x_content,
            before_upstream_request=limiter.wait,
            page_sleep_seconds=0.0,
        )
        collect_evidence(
            run_conn,
            post_client=post_client,
            workers=args.fetch_workers,
            requests_per_second=1_000_000,
        )
        print(
            _canonical_json({"stage": "x-content", **post_client.stats()}),
            flush=True,
        )
    else:
        print(
            _canonical_json(
                {"stage": "x-content", "cache_hits": frozen, "provider_requests": 0}
            ),
            flush=True,
        )
    collect_identity_contexts(
        run_conn,
        model=args.identity_model or args.model,
        effort=args.reasoning_effort,
        run_id=args.run_id,
        workers=args.identity_workers,
    )
    evaluate_pending(
        run_conn,
        model=args.model,
        effort=args.reasoning_effort,
        run_id=args.run_id,
        workers=args.model_workers,
    )
    summary = status(run_conn)
    print(json.dumps(summary, sort_keys=True))
    return 0 if (
        summary["evidence_complete"] == summary["total"]
        and summary["identity_context_failed"] == 0
        and summary["identity_context_complete"]
        == summary["identity_context_requested"]
        and summary["evaluation_complete"] == summary["total"]
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
