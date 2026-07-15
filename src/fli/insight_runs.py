"""Durable, immutable run storage for audience Insight generation."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable

from fli import insight_generation


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "data" / "derived" / "insights" / "insights.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS insight_run (
    run_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    day TEXT NOT NULL,
    feed_rank INTEGER NOT NULL,
    source_routing_run_id TEXT NOT NULL,
    source_routing_db TEXT NOT NULL,
    model TEXT NOT NULL,
    reasoning_effort TEXT NOT NULL,
    expected_audiences_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'complete', 'failed')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS insight_item (
    run_id TEXT NOT NULL REFERENCES insight_run(run_id) ON DELETE CASCADE,
    audience TEXT NOT NULL CHECK (audience IN ('investment', 'ai_engineering')),
    candidate_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    day TEXT NOT NULL,
    feed_rank INTEGER NOT NULL,
    input_text TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    prompt_sha256 TEXT NOT NULL,
    prompt_cache_key TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    model TEXT NOT NULL,
    reasoning_effort TEXT NOT NULL,
    request_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'complete', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    decision TEXT CHECK (decision IN ('surface', 'suppress')),
    suppression_reason TEXT,
    title TEXT,
    summary TEXT,
    implication TEXT,
    next_step TEXT,
    raw_output_text TEXT,
    published_json TEXT,
    evaluation_json TEXT,
    response_id TEXT,
    response_model TEXT,
    input_tokens INTEGER,
    cached_tokens INTEGER,
    cache_write_tokens INTEGER,
    output_tokens INTEGER,
    reported_cost_usd REAL,
    request_tags_json TEXT,
    error_type TEXT,
    error_message TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (run_id, audience)
);

CREATE INDEX IF NOT EXISTS idx_insight_item_day_audience_decision
    ON insight_item(day, audience, decision, feed_rank, event_id);
CREATE INDEX IF NOT EXISTS idx_insight_item_event_audience_complete
    ON insight_item(event_id, audience, status, completed_at);
CREATE INDEX IF NOT EXISTS idx_insight_run_day_status
    ON insight_run(day, status, updated_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def connect(path: Path = DEFAULT_DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.executescript(SCHEMA)
    return conn


def _request_contract(
    request: dict[str, Any],
    audience: str,
    recorded: dict[str, str] | None = None,
) -> dict[str, str]:
    prompt = insight_generation.contract(audience)
    input_text = request.get("input")
    if not isinstance(input_text, str) or not input_text:
        raise ValueError(f"{audience} request has no input text")
    instructions = request.get("instructions")
    if not isinstance(instructions, str) or not instructions:
        raise ValueError(f"{audience} request has no instructions")
    if request.get("text", {}).get("format") != insight_generation.OUTPUT_FORMAT:
        raise ValueError(f"{audience} request does not match the current output schema")
    if recorded is None:
        if instructions != prompt.instructions():
            raise ValueError(f"{audience} request does not match the current prompt")
        if request.get("prompt_cache_key") != prompt.cache_key:
            raise ValueError(f"{audience} request has the wrong prompt cache key")
        prompt_version = prompt.version
        prompt_sha256 = prompt.sha256
        schema_version = insight_generation.SCHEMA_VERSION
    else:
        prompt_version = recorded["prompt_version"]
        prompt_sha256 = recorded["prompt_sha256"]
        schema_version = recorded["schema_version"]
        if _sha256(instructions) != prompt_sha256:
            raise ValueError(f"{audience} imported prompt hash does not match")
        if _sha256(input_text) != recorded["input_sha256"]:
            raise ValueError(f"{audience} imported input hash does not match")
    cache_key = request.get("prompt_cache_key")
    if not isinstance(cache_key, str) or not cache_key:
        raise ValueError(f"{audience} request has no prompt cache key")
    return {
        "input_text": input_text,
        "input_sha256": _sha256(input_text),
        "prompt_version": prompt_version,
        "prompt_sha256": prompt_sha256,
        "prompt_cache_key": cache_key,
        "schema_version": schema_version,
    }


def prepare_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    event_id: str,
    day: str,
    feed_rank: int,
    source_routing_run_id: str,
    source_routing_db: str,
    model: str,
    reasoning_effort: str,
    items: Iterable[dict[str, Any]],
) -> None:
    """Freeze one run before model execution and reject contract drift on resume."""
    frozen_items = list(items)
    if not frozen_items:
        raise ValueError("an Insight run must contain at least one audience")
    audiences = [str(item["audience"]) for item in frozen_items]
    if len(audiences) != len(set(audiences)):
        raise ValueError("an Insight run cannot repeat an audience")
    now = _now()
    run_values = {
        "run_id": run_id,
        "event_id": event_id,
        "day": day,
        "feed_rank": feed_rank,
        "source_routing_run_id": source_routing_run_id,
        "source_routing_db": source_routing_db,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "expected_audiences_json": _canonical_json(sorted(audiences)),
    }
    existing = conn.execute(
        "SELECT * FROM insight_run WHERE run_id = ?", (run_id,)
    ).fetchone()
    if existing is not None:
        mismatched = [
            key for key, value in run_values.items() if str(existing[key]) != str(value)
        ]
        if mismatched:
            raise ValueError(
                f"run_id {run_id!r} is already frozen with different "
                + ", ".join(mismatched)
            )
    else:
        conn.execute(
            """INSERT INTO insight_run (
                   run_id, event_id, day, feed_rank, source_routing_run_id,
                   source_routing_db, model, reasoning_effort,
                   expected_audiences_json, status, created_at, updated_at
               ) VALUES (
                   :run_id, :event_id, :day, :feed_rank, :source_routing_run_id,
                   :source_routing_db, :model, :reasoning_effort,
                   :expected_audiences_json, 'pending', :created_at, :updated_at
               )""",
            {**run_values, "created_at": now, "updated_at": now},
        )

    for item in frozen_items:
        audience = insight_generation.require_audience(str(item["audience"])).value
        request = item["request"]
        if not isinstance(request, dict):
            raise ValueError(f"{audience} request must be an object")
        recorded_contract = (
            {
                "prompt_version": str(item["prompt_version"]),
                "prompt_sha256": str(item["prompt_sha256"]),
                "schema_version": str(item["schema_version"]),
                "input_sha256": str(item["input_sha256"]),
            }
            if "prompt_version" in item
            else None
        )
        contract = _request_contract(request, audience, recorded_contract)
        if request.get("model") != model:
            raise ValueError(f"{audience} request model does not match the run")
        if request.get("reasoning", {}).get("effort") != reasoning_effort:
            raise ValueError(f"{audience} request effort does not match the run")
        item_values = {
            "run_id": run_id,
            "audience": audience,
            "candidate_id": str(item["candidate_id"]),
            "event_id": event_id,
            "day": day,
            "feed_rank": feed_rank,
            **contract,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "request_json": _canonical_json(request),
        }
        existing_item = conn.execute(
            "SELECT * FROM insight_item WHERE run_id = ? AND audience = ?",
            (run_id, audience),
        ).fetchone()
        if existing_item is not None:
            mismatched = [
                key
                for key, value in item_values.items()
                if str(existing_item[key]) != str(value)
            ]
            if mismatched:
                raise ValueError(
                    f"{run_id}/{audience} is already frozen with different "
                    + ", ".join(mismatched)
                )
            continue
        conn.execute(
            """INSERT INTO insight_item (
                   run_id, audience, candidate_id, event_id, day, feed_rank,
                   input_text, input_sha256, prompt_version, prompt_sha256,
                   prompt_cache_key, schema_version, model, reasoning_effort,
                   request_json, status, updated_at
               ) VALUES (
                   :run_id, :audience, :candidate_id, :event_id, :day, :feed_rank,
                   :input_text, :input_sha256, :prompt_version, :prompt_sha256,
                   :prompt_cache_key, :schema_version, :model, :reasoning_effort,
                   :request_json, 'pending', :updated_at
               )""",
            {**item_values, "updated_at": now},
        )
    conn.commit()


def _refresh_run_status(conn: sqlite3.Connection, run_id: str) -> str:
    counts = conn.execute(
        """SELECT COUNT(*) AS total,
                  SUM(status = 'complete') AS complete,
                  SUM(status = 'failed') AS failed
           FROM insight_item WHERE run_id = ?""",
        (run_id,),
    ).fetchone()
    assert counts is not None
    total = int(counts["total"] or 0)
    complete = int(counts["complete"] or 0)
    failed = int(counts["failed"] or 0)
    status = "complete" if total > 0 and complete == total else "failed" if failed else "pending"
    conn.execute(
        "UPDATE insight_run SET status = ?, updated_at = ? WHERE run_id = ?",
        (status, _now(), run_id),
    )
    return status


def complete_item(
    conn: sqlite3.Connection, *, run_id: str, evaluation: dict[str, Any]
) -> None:
    audience = insight_generation.require_audience(str(evaluation["audience"])).value
    row = conn.execute(
        "SELECT * FROM insight_item WHERE run_id = ? AND audience = ?",
        (run_id, audience),
    ).fetchone()
    if row is None:
        raise ValueError(f"{run_id}/{audience} was not prepared")
    if str(row["candidate_id"]) != str(evaluation["candidate_id"]):
        raise ValueError(f"{run_id}/{audience} candidate changed after freeze")
    if str(row["input_sha256"]) != str(evaluation["input_sha256"]):
        raise ValueError(f"{run_id}/{audience} input changed after freeze")
    if str(row["prompt_sha256"]) != str(evaluation["prompt_sha256"]):
        raise ValueError(f"{run_id}/{audience} prompt changed after freeze")
    result = insight_generation.validate_output(evaluation["result"])
    canonical_evaluation = _canonical_json(evaluation)
    if row["status"] == "complete":
        if str(row["evaluation_json"]) != canonical_evaluation:
            raise ValueError(f"{run_id}/{audience} already has a different result")
        return
    now = _now()
    conn.execute(
        """UPDATE insight_item
           SET status = 'complete', attempts = attempts + 1,
               decision = ?, suppression_reason = ?, title = ?, summary = ?, implication = ?,
               next_step = ?, raw_output_text = ?, published_json = ?,
               evaluation_json = ?, response_id = ?, response_model = ?,
               input_tokens = ?, cached_tokens = ?, cache_write_tokens = ?,
               output_tokens = ?, reported_cost_usd = ?, request_tags_json = ?,
               error_type = NULL, error_message = NULL, completed_at = ?, updated_at = ?
           WHERE run_id = ? AND audience = ?""",
        (
            result.decision.value,
            result.suppression_reason,
            result.title,
            result.summary,
            result.implication,
            result.next_step,
            evaluation.get("raw_output_text"),
            _canonical_json(evaluation.get("published")),
            canonical_evaluation,
            evaluation.get("response_id"),
            evaluation.get("response_model"),
            int(evaluation.get("input_tokens") or 0),
            int(evaluation.get("cached_tokens") or 0),
            int(evaluation.get("cache_write_tokens") or 0),
            int(evaluation.get("output_tokens") or 0),
            evaluation.get("reported_cost_usd"),
            _canonical_json(evaluation.get("request_tags") or []),
            now,
            now,
            run_id,
            audience,
        ),
    )
    _refresh_run_status(conn, run_id)
    conn.commit()


def fail_item(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    audience: str,
    error: BaseException,
) -> None:
    audience = insight_generation.require_audience(audience).value
    now = _now()
    conn.execute(
        """UPDATE insight_item
           SET status = 'failed', attempts = attempts + 1,
               error_type = ?, error_message = ?, updated_at = ?
           WHERE run_id = ? AND audience = ?""",
        (type(error).__name__, str(error), now, run_id, audience),
    )
    _refresh_run_status(conn, run_id)
    conn.commit()


def completed_evaluation(
    conn: sqlite3.Connection, *, run_id: str, audience: str
) -> dict[str, Any] | None:
    row = conn.execute(
        """SELECT evaluation_json FROM insight_item
           WHERE run_id = ? AND audience = ? AND status = 'complete'""",
        (run_id, insight_generation.require_audience(audience).value),
    ).fetchone()
    return json.loads(str(row["evaluation_json"])) if row is not None else None


def run_payload(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    run = conn.execute(
        "SELECT * FROM insight_run WHERE run_id = ?", (run_id,)
    ).fetchone()
    if run is None:
        raise ValueError(f"Insight run {run_id!r} does not exist")
    items = conn.execute(
        """SELECT audience, candidate_id, status, decision, suppression_reason,
                  title, summary, implication, next_step, attempts, prompt_version,
                  input_sha256, response_id, response_model, input_tokens,
                  cached_tokens, cache_write_tokens, output_tokens,
                  reported_cost_usd, error_type, error_message, completed_at
           FROM insight_item WHERE run_id = ? ORDER BY audience""",
        (run_id,),
    ).fetchall()
    return {
        **dict(run),
        "expected_audiences": json.loads(str(run["expected_audiences_json"])),
        "items": [dict(item) for item in items],
    }


def summary_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute(
        """SELECT COUNT(DISTINCT run_id) AS runs,
                  COUNT(*) AS items,
                  SUM(status = 'complete') AS complete,
                  SUM(status = 'failed') AS failed,
                  SUM(decision = 'surface') AS surfaced,
                  SUM(decision = 'suppress') AS suppressed,
                  COALESCE(SUM(input_tokens), 0) AS input_tokens,
                  COALESCE(SUM(cached_tokens), 0) AS cached_tokens,
                  COALESCE(SUM(cache_write_tokens), 0) AS cache_write_tokens,
                  COALESCE(SUM(output_tokens), 0) AS output_tokens,
                  COALESCE(SUM(reported_cost_usd), 0) AS reported_cost_usd
           FROM insight_item"""
    ).fetchone()
    assert row is not None
    latest = conn.execute(
        "SELECT MAX(day) FROM insight_item WHERE status = 'complete'"
    ).fetchone()[0]
    return {**dict(row), "latest_day": latest}


def import_result_file(
    conn: sqlite3.Connection, result_path: Path
) -> dict[str, Any]:
    """Import an exact completed CLI dump without making another model call."""
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    if payload.get("dry_run") or payload.get("will_call_model") is not True:
        raise ValueError("result file is not a completed model run")
    evaluations = payload.get("evaluations")
    if not isinstance(evaluations, list) or not evaluations:
        raise ValueError("result file has no evaluations")
    request_files = payload.get("request_files")
    if not isinstance(request_files, dict):
        raise ValueError("result file has no request file map")
    items = []
    for evaluation in evaluations:
        audience = insight_generation.require_audience(evaluation["audience"]).value
        request_path = Path(str(request_files[audience]))
        if not request_path.is_absolute():
            request_path = REPO_ROOT / request_path
        request = json.loads(request_path.read_text(encoding="utf-8"))
        items.append(
            {
                "audience": audience,
                "candidate_id": evaluation["candidate_id"],
                "request": request,
                "prompt_version": evaluation["prompt_version"],
                "prompt_sha256": evaluation["prompt_sha256"],
                "schema_version": evaluation["schema_version"],
                "input_sha256": evaluation["input_sha256"],
            }
        )
    prepare_run(
        conn,
        run_id=str(payload["run_id"]),
        event_id=str(payload["event_id"]),
        day=str(payload["day"]),
        feed_rank=int(payload["feed_rank"]),
        source_routing_run_id=str(payload["source_routing_run_id"]),
        source_routing_db=str(payload["source_routing_db"]),
        model=str(payload["model"]),
        reasoning_effort=str(payload["reasoning_effort"]),
        items=items,
    )
    for evaluation in evaluations:
        complete_item(conn, run_id=str(payload["run_id"]), evaluation=evaluation)
    return {
        "db": _display_path(Path(conn.execute("PRAGMA database_list").fetchone()[2])),
        "imported_from": _display_path(result_path),
        "run": run_payload(conn, str(payload["run_id"])),
        "summary": summary_payload(conn),
        "will_call_model": False,
    }
