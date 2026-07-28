"""Durable storage and read projection for company-aware Investment Insights."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = (
    REPO_ROOT / "data" / "derived" / "insights" / "investment-agent.db"
)
STORE_SCHEMA_VERSION = "investment-agent-store-v1"
READ_SCHEMA_VERSION = "investment-agent-read-v4"
TRACE_SCHEMA_VERSIONS = {"investment-agent-trace-v1"}
STATUSES = {"kept", "suppressed", "all"}
ASSESSMENT_FIELDS = {
    "ticker",
    "bottom_line",
    "mechanism",
    "affected_driver",
    "direction",
    "main_uncertainty",
    "next_check",
}
DIRECTIONS = {"positive", "negative", "mixed", "unclear"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS investment_agent_meta (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    schema_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS investment_agent_run (
    run_id TEXT PRIMARY KEY,
    day TEXT NOT NULL,
    development_id TEXT NOT NULL,
    daily_rank INTEGER NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('surface', 'suppress')),
    prompt_version TEXT NOT NULL,
    prompt_cache_key TEXT NOT NULL,
    model TEXT NOT NULL,
    reasoning_effort TEXT NOT NULL,
    company_universe_count INTEGER NOT NULL,
    company_cards_sha256 TEXT NOT NULL,
    evidence_sha256 TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    memo_count INTEGER NOT NULL,
    assessed_company_count INTEGER NOT NULL,
    rejected_company_count INTEGER NOT NULL,
    turn_count INTEGER NOT NULL,
    input_tokens INTEGER NOT NULL,
    cached_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    reasoning_tokens INTEGER NOT NULL,
    reported_cost_usd REAL NOT NULL,
    result_sha256 TEXT NOT NULL,
    final_result_json TEXT NOT NULL,
    memo_calls_json TEXT NOT NULL,
    citation_repairs_json TEXT NOT NULL,
    trace_json TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    UNIQUE (
        day, development_id, input_sha256, prompt_version, model,
        reasoning_effort, result_sha256
    )
);

CREATE INDEX IF NOT EXISTS idx_investment_agent_run_day_rank
    ON investment_agent_run(day, daily_rank, development_id);
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


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


def connect(path: Path = DEFAULT_DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.executescript(SCHEMA)
    row = conn.execute(
        "SELECT schema_version FROM investment_agent_meta WHERE singleton = 1"
    ).fetchone()
    if row is None:
        conn.execute(
            """INSERT INTO investment_agent_meta(singleton, schema_version)
               VALUES (1, ?)""",
            (STORE_SCHEMA_VERSION,),
        )
    elif str(row["schema_version"]) != STORE_SCHEMA_VERSION:
        raise ValueError(
            "unsupported Investment agent store schema "
            f"{row['schema_version']!r}"
        )
    conn.commit()
    return conn


def _validate_trace(trace: dict[str, Any]) -> None:
    if trace.get("schema_version") not in TRACE_SCHEMA_VERSIONS:
        raise ValueError("unsupported Investment agent trace schema")
    final = trace.get("final_result")
    if not isinstance(final, dict):
        raise ValueError("Investment agent trace has no validated final result")
    headline = str(final.get("investment_headline") or "").strip()
    if not headline or "\n" in headline or len(headline.split()) > 18:
        raise ValueError("Investment agent result has an invalid headline")
    decision = final.get("decision")
    if decision not in {"surface", "suppress"}:
        raise ValueError("Investment agent result has an invalid decision")
    assessments = final.get("company_assessments")
    rejections = final.get("rejected_after_memo")
    if not isinstance(assessments, list) or not isinstance(rejections, list):
        raise ValueError("Investment agent result has invalid company decisions")
    assessed = [str(item.get("ticker") or "") for item in assessments]
    rejected = [str(item.get("ticker") or "") for item in rejections]
    represented = assessed + rejected
    if not represented and decision == "surface":
        raise ValueError("surfaced Investment result has no company assessment")
    if len(represented) != len(set(represented)) or "" in represented:
        raise ValueError("Investment result repeats or omits a company ticker")
    for assessment in assessments:
        if set(assessment) != ASSESSMENT_FIELDS:
            raise ValueError(
                "Investment company assessment does not match the minimal schema"
            )
        if str(assessment["direction"]) not in DIRECTIONS:
            raise ValueError("Investment company assessment has invalid direction")
        for field in ASSESSMENT_FIELDS - {"direction"}:
            if not str(assessment[field]).strip():
                raise ValueError(
                    f"Investment company assessment has empty {field}"
                )
    memo_calls = trace.get("memo_calls")
    if not isinstance(memo_calls, list):
        raise ValueError("Investment agent trace has no memo-call audit")
    called = [
        str((item.get("arguments") or {}).get("ticker") or "")
        for item in memo_calls
    ]
    if set(called) != set(represented):
        raise ValueError(
            "every opened memo must be assessed or rejected exactly once"
        )


def import_trace(
    path: Path,
    *,
    db_path: Path = DEFAULT_DB,
) -> dict[str, Any]:
    trace = json.loads(path.read_text(encoding="utf-8"))
    _validate_trace(trace)
    final = trace["final_result"]
    turns = trace.get("turns") or []
    result_sha256 = _sha256(final)
    run_identity_sha256 = _sha256(
        {
            "prompt_version": trace["prompt_version"],
            "model": trace["model"],
            "reasoning_effort": trace["reasoning_effort"],
            "result_sha256": result_sha256,
        }
    )
    run_id = (
        f"investment-agent-{trace['date']}-"
        f"{str(trace['development_id'])[:12]}-{run_identity_sha256[:12]}"
    )
    values = {
        "run_id": run_id,
        "day": str(trace["date"]),
        "development_id": str(trace["development_id"]),
        "daily_rank": int(trace["daily_rank"]),
        "decision": str(final["decision"]),
        "prompt_version": str(trace["prompt_version"]),
        "prompt_cache_key": str(trace["prompt_cache_key"]),
        "model": str(trace["model"]),
        "reasoning_effort": str(trace["reasoning_effort"]),
        "company_universe_count": int(trace["company_count"]),
        "company_cards_sha256": str(trace["company_cards_sha256"]),
        "evidence_sha256": str(trace["evidence_sha256"]),
        "input_sha256": str(trace["input_sha256"]),
        "memo_count": len(trace["memo_calls"]),
        "assessed_company_count": len(final["company_assessments"]),
        "rejected_company_count": len(final["rejected_after_memo"]),
        "turn_count": len(turns),
        "input_tokens": sum(int(item.get("input_tokens") or 0) for item in turns),
        "cached_tokens": sum(int(item.get("cached_tokens") or 0) for item in turns),
        "output_tokens": sum(
            int(item.get("output_tokens") or 0) for item in turns
        ),
        "reasoning_tokens": sum(
            int(item.get("reasoning_tokens") or 0) for item in turns
        ),
        "reported_cost_usd": round(
            sum(float(item.get("reported_cost_usd") or 0) for item in turns),
            8,
        ),
        "result_sha256": result_sha256,
        "final_result_json": _canonical_json(final),
        "memo_calls_json": _canonical_json(trace["memo_calls"]),
        "citation_repairs_json": _canonical_json(
            trace.get("citation_repairs") or []
        ),
        "trace_json": _canonical_json(trace),
        "completed_at": _now(),
    }
    conn = connect(db_path)
    try:
        conn.execute(
            """INSERT OR IGNORE INTO investment_agent_run (
                   run_id, day, development_id, daily_rank, decision,
                   prompt_version, prompt_cache_key, model, reasoning_effort,
                   company_universe_count, company_cards_sha256,
                   evidence_sha256, input_sha256, memo_count,
                   assessed_company_count, rejected_company_count, turn_count,
                   input_tokens, cached_tokens, output_tokens,
                   reasoning_tokens, reported_cost_usd, result_sha256,
                   final_result_json, memo_calls_json, citation_repairs_json,
                   trace_json, completed_at
               ) VALUES (
                   :run_id, :day, :development_id, :daily_rank, :decision,
                   :prompt_version, :prompt_cache_key, :model,
                   :reasoning_effort, :company_universe_count,
                   :company_cards_sha256, :evidence_sha256, :input_sha256,
                   :memo_count, :assessed_company_count,
                   :rejected_company_count, :turn_count, :input_tokens,
                   :cached_tokens, :output_tokens, :reasoning_tokens,
                   :reported_cost_usd, :result_sha256, :final_result_json,
                   :memo_calls_json, :citation_repairs_json, :trace_json,
                   :completed_at
               )""",
            values,
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "run_id": run_id,
        "db": str(db_path),
        "day": values["day"],
        "development_id": values["development_id"],
        "decision": values["decision"],
        "company_assessments": values["assessed_company_count"],
        "rejected_after_memo": values["rejected_company_count"],
        "reported_cost_usd": values["reported_cost_usd"],
    }


def _open_readonly(path: Path) -> sqlite3.Connection | None:
    if not path.is_file():
        return None
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _latest_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """WITH current AS (
               SELECT run.*,
                      ROW_NUMBER() OVER (
                          PARTITION BY day, development_id
                          ORDER BY completed_at DESC, run_id DESC
                      ) AS recency_order
               FROM investment_agent_run AS run
           )
           SELECT * FROM current
           WHERE recency_order = 1
           ORDER BY day, daily_rank, development_id"""
    ).fetchall()


def dates_payload(
    *,
    db_path: Path | None = None,
) -> dict[str, Any]:
    db_path = db_path or DEFAULT_DB
    conn = _open_readonly(db_path)
    if conn is None:
        return {
            "available": False,
            "reason": "No company-aware Investment run has been stored yet.",
            "latest_date": None,
            "dates": [],
        }
    try:
        rows = _latest_rows(conn)
    finally:
        conn.close()
    dates: dict[str, dict[str, Any]] = {}
    for row in rows:
        day = str(row["day"])
        value = dates.setdefault(
            day,
            {
                "day": day,
                "content_kind": "investment_agent",
                "item_count": 0,
                "candidate_count": 0,
                "included_candidate_count": 0,
                "not_selected_candidate_count": 0,
            },
        )
        value["candidate_count"] += 1
        if str(row["decision"]) == "surface":
            value["item_count"] += 1
            value["included_candidate_count"] += 1
        else:
            value["not_selected_candidate_count"] += 1
    ordered = [dates[day] for day in sorted(dates)]
    return {
        "available": bool(ordered),
        "reason": None if ordered else "No company-aware Investment run is complete.",
        "latest_date": ordered[-1]["day"] if ordered else None,
        "dates": ordered,
    }


def insights_payload(
    *,
    day: str | None = None,
    status: str = "kept",
    db_path: Path | None = None,
) -> dict[str, Any]:
    db_path = db_path or DEFAULT_DB
    if status not in STATUSES:
        raise ValueError(f"unsupported Insight status {status!r}")
    conn = _open_readonly(db_path)
    if conn is None:
        return {
            "schema_version": READ_SCHEMA_VERSION,
            "available": False,
            "reason": "No company-aware Investment run has been stored yet.",
            "requested_date": day,
            "date": None,
            "audience": "investment",
            "status": status,
            "content_kind": "investment_agent",
            "run": None,
            "items": [],
        }
    try:
        current = _latest_rows(conn)
    finally:
        conn.close()
    selected_day = day or max((str(row["day"]) for row in current), default=None)
    day_rows = [row for row in current if str(row["day"]) == selected_day]
    wanted_decision = {
        "kept": "surface",
        "suppressed": "suppress",
    }.get(status)
    visible = [
        row
        for row in day_rows
        if wanted_decision is None or str(row["decision"]) == wanted_decision
    ]
    if not day_rows:
        return {
            "schema_version": READ_SCHEMA_VERSION,
            "available": False,
            "reason": "No company-aware Investment result exists for this date.",
            "requested_date": day,
            "date": selected_day,
            "audience": "investment",
            "status": status,
            "content_kind": "investment_agent",
            "run": None,
            "items": [],
        }
    run = {
        "date": selected_day,
        "development_count": len(day_rows),
        "surfaced_development_count": sum(
            str(row["decision"]) == "surface" for row in day_rows
        ),
        "suppressed_development_count": sum(
            str(row["decision"]) == "suppress" for row in day_rows
        ),
        "company_assessment_count": sum(
            int(row["assessed_company_count"]) for row in day_rows
        ),
        "rejected_company_count": sum(
            int(row["rejected_company_count"]) for row in day_rows
        ),
        "model": str(day_rows[-1]["model"]),
        "reasoning_effort": str(day_rows[-1]["reasoning_effort"]),
        "prompt_version": str(day_rows[-1]["prompt_version"]),
        "turn_count": sum(int(row["turn_count"]) for row in day_rows),
        "input_tokens": sum(int(row["input_tokens"]) for row in day_rows),
        "cached_tokens": sum(int(row["cached_tokens"]) for row in day_rows),
        "output_tokens": sum(int(row["output_tokens"]) for row in day_rows),
        "reasoning_tokens": sum(
            int(row["reasoning_tokens"]) for row in day_rows
        ),
        "reported_cost_usd": round(
            sum(float(row["reported_cost_usd"]) for row in day_rows), 8
        ),
    }
    items = []
    for row in visible:
        final = json.loads(str(row["final_result_json"]))
        trace = json.loads(str(row["trace_json"]))
        company_names = {
            str(ticker): str(
                ((packet.get("company") or {}).get("name"))
                or ticker
            )
            for ticker, packet in (trace.get("memo_packets") or {}).items()
        }
        items.append(
            {
                "run_id": str(row["run_id"]),
                "day": str(row["day"]),
                "development_id": str(row["development_id"]),
                "daily_rank": int(row["daily_rank"]),
                "decision": str(row["decision"]),
                "investment_headline": str(final["investment_headline"]),
                "development_summary": str(final["development_summary"]),
                "portfolio_readthrough": str(final["portfolio_readthrough"]),
                "company_assessments": final["company_assessments"],
                "rejected_after_memo": final["rejected_after_memo"],
                "no_match_reason": final["no_match_reason"],
                "company_names": company_names,
                "memo_calls": json.loads(str(row["memo_calls_json"])),
                "citation_repairs": json.loads(
                    str(row["citation_repairs_json"])
                ),
                "telemetry": {
                    "model": str(row["model"]),
                    "reasoning_effort": str(row["reasoning_effort"]),
                    "prompt_version": str(row["prompt_version"]),
                    "company_universe_count": int(
                        row["company_universe_count"]
                    ),
                    "memo_count": int(row["memo_count"]),
                    "turn_count": int(row["turn_count"]),
                    "input_tokens": int(row["input_tokens"]),
                    "cached_tokens": int(row["cached_tokens"]),
                    "output_tokens": int(row["output_tokens"]),
                    "reasoning_tokens": int(row["reasoning_tokens"]),
                    "reported_cost_usd": float(row["reported_cost_usd"]),
                    "completed_at": str(row["completed_at"]),
                },
            }
        )
    reason = None
    if not items:
        reason = (
            "No company-aware Investment result was suppressed on this date."
            if status == "suppressed"
            else "No company-aware Investment result matches this view."
        )
    return {
        "schema_version": READ_SCHEMA_VERSION,
        "available": True,
        "reason": reason,
        "requested_date": day,
        "date": selected_day,
        "audience": "investment",
        "status": status,
        "content_kind": "investment_agent",
        "run": run,
        "items": items,
    }
