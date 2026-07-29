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
STORE_SCHEMA_VERSION = "investment-agent-store-v2"
READ_SCHEMA_VERSION = "investment-agent-read-v8"
CURRENT_PROMPT_VERSION = "investment-agent-v14"
TRACE_SCHEMA_VERSIONS = {"investment-agent-trace-v1"}
STATUSES = {"kept", "suppressed", "all"}
CONNECTION_FIELDS = {"mechanism", "companies"}
COMPANY_FIELDS = {
    "ticker",
    "bet_id",
    "threshold_met",
    "impact",
}

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

CREATE TABLE IF NOT EXISTS investment_agent_day_publication (
    day TEXT PRIMARY KEY,
    audience TEXT NOT NULL CHECK (audience = 'investment'),
    selection_kind TEXT NOT NULL,
    selection_limit INTEGER NOT NULL,
    selection_sha256 TEXT NOT NULL,
    candidate_count INTEGER NOT NULL,
    published_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS investment_agent_day_publication_item (
    day TEXT NOT NULL,
    development_id TEXT NOT NULL,
    daily_rank INTEGER NOT NULL,
    PRIMARY KEY (day, development_id),
    UNIQUE (day, daily_rank),
    FOREIGN KEY (day) REFERENCES investment_agent_day_publication(day)
        ON DELETE CASCADE
);
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
    elif str(row["schema_version"]) == "investment-agent-store-v1":
        conn.execute(
            """UPDATE investment_agent_meta
               SET schema_version = ?
               WHERE singleton = 1""",
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
    if set(final) != {
        "headline",
        "what_changed",
        "decision",
        "connections",
        "no_match_reason",
    }:
        raise ValueError("Investment agent result does not match the v14 schema")
    headline = str(final.get("headline") or "").strip()
    if not headline or "\n" in headline or len(headline.split()) > 18:
        raise ValueError("Investment agent result has an invalid headline")
    decision = final.get("decision")
    if decision not in {"surface", "suppress"}:
        raise ValueError("Investment agent result has an invalid decision")
    connections = final.get("connections")
    if not isinstance(connections, list):
        raise ValueError("Investment agent result has invalid company connections")
    assessed = [
        str(company.get("ticker") or "")
        for item in connections
        if isinstance(item, dict)
        for company in (item.get("companies") or [])
    ]
    cited_bets = [
        (
            str(company.get("ticker") or ""),
            str(company.get("bet_id") or ""),
        )
        for item in connections
        if isinstance(item, dict)
        for company in (item.get("companies") or [])
    ]
    if not assessed and decision == "surface":
        raise ValueError("surfaced Investment result has no company connection")
    if "" in assessed or any(not bet_id for _, bet_id in cited_bets):
        raise ValueError("Investment result omits a company ticker or bet id")
    if len(cited_bets) != len(set(cited_bets)):
        raise ValueError("Investment result repeats a company bet")
    for connection in connections:
        if set(connection) != CONNECTION_FIELDS:
            raise ValueError("Investment connection does not match the v14 schema")
        companies = connection["companies"]
        if not isinstance(companies, list) or not companies:
            raise ValueError("Investment connection has no company")
        if not str(connection["mechanism"]).strip():
            raise ValueError("Investment connection has an empty mechanism")
        for company in companies:
            if set(company) != COMPANY_FIELDS:
                raise ValueError(
                    "Investment company does not match the v14 schema"
                )
            if not isinstance(company["threshold_met"], bool):
                raise ValueError("Investment company threshold_met must be boolean")
            for field in COMPANY_FIELDS - {"threshold_met"}:
                if not str(company[field]).strip():
                    raise ValueError(
                        f"Investment company has empty {field}"
                    )
    memo_calls = trace.get("memo_calls")
    if not isinstance(memo_calls, list):
        raise ValueError("Investment agent trace has no memo-call audit")
    called = [
        str((item.get("arguments") or {}).get("ticker") or "")
        for item in memo_calls
    ]
    if len(called) != len(set(called)) or "" in called:
        raise ValueError("Investment memo audit repeats or omits a ticker")
    if not set(assessed).issubset(set(called)):
        raise ValueError(
            "every retained company must have an opened memo"
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
    assessed = {
        str(company["ticker"])
        for connection in final["connections"]
        for company in connection["companies"]
    }
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
        "assessed_company_count": len(assessed),
        "rejected_company_count": len(trace["memo_calls"])
        - len(assessed),
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
        "company_connections": values["assessed_company_count"],
        "memos_rejected": values["rejected_company_count"],
        "reported_cost_usd": values["reported_cost_usd"],
    }


def publish_day(
    *,
    day: str,
    candidates: list[dict[str, Any]],
    selection_limit: int,
    db_path: Path = DEFAULT_DB,
) -> dict[str, Any]:
    """Atomically publish one complete Investment-routed daily cohort."""
    if not candidates:
        raise ValueError("cannot publish an empty Investment cohort")
    normalized = [
        {
            "development_id": str(item["development_id"]),
            "daily_rank": int(item["daily_rank"]),
        }
        for item in candidates
    ]
    if len({item["development_id"] for item in normalized}) != len(normalized):
        raise ValueError("Investment publication repeats a Development")
    if len({item["daily_rank"] for item in normalized}) != len(normalized):
        raise ValueError("Investment publication repeats a daily rank")
    normalized.sort(key=lambda item: (item["daily_rank"], item["development_id"]))
    selection_sha256 = _sha256(
        {
            "audience": "investment",
            "selection_kind": "top_investment_routed",
            "selection_limit": selection_limit,
            "candidates": normalized,
        }
    )
    conn = connect(db_path)
    try:
        for item in normalized:
            row = conn.execute(
                """SELECT 1
                   FROM investment_agent_run
                   WHERE day = ?
                     AND development_id = ?
                     AND daily_rank = ?
                     AND prompt_version = ?
                   LIMIT 1""",
                (
                    day,
                    item["development_id"],
                    item["daily_rank"],
                    CURRENT_PROMPT_VERSION,
                ),
            ).fetchone()
            if row is None:
                raise ValueError(
                    "cannot publish an Investment candidate without a "
                    "completed imported run"
                )
        now = _now()
        with conn:
            conn.execute(
                "DELETE FROM investment_agent_day_publication_item WHERE day = ?",
                (day,),
            )
            conn.execute(
                "DELETE FROM investment_agent_day_publication WHERE day = ?",
                (day,),
            )
            conn.execute(
                """INSERT INTO investment_agent_day_publication (
                       day, audience, selection_kind, selection_limit,
                       selection_sha256, candidate_count, published_at
                   ) VALUES (?, 'investment', 'top_investment_routed', ?, ?, ?, ?)""",
                (
                    day,
                    selection_limit,
                    selection_sha256,
                    len(normalized),
                    now,
                ),
            )
            conn.executemany(
                """INSERT INTO investment_agent_day_publication_item (
                       day, development_id, daily_rank
                   ) VALUES (?, ?, ?)""",
                [
                    (day, item["development_id"], item["daily_rank"])
                    for item in normalized
                ],
            )
    finally:
        conn.close()
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "day": day,
        "audience": "investment",
        "selection_kind": "top_investment_routed",
        "selection_limit": selection_limit,
        "selection_sha256": selection_sha256,
        "candidate_count": len(normalized),
        "published_at": now,
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
               WHERE run.prompt_version = ?
           )
           SELECT current.*
           FROM current
           JOIN investment_agent_day_publication_item AS publication
             ON publication.day = current.day
            AND publication.development_id = current.development_id
            AND publication.daily_rank = current.daily_rank
           WHERE current.recency_order = 1
           ORDER BY current.day, current.daily_rank, current.development_id""",
        (CURRENT_PROMPT_VERSION,),
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
                "development_count": 0,
                "surfaced_development_count": 0,
                "suppressed_development_count": 0,
            },
        )
        value["development_count"] += 1
        if str(row["decision"]) == "surface":
            value["item_count"] += 1
            value["surfaced_development_count"] += 1
        else:
            value["suppressed_development_count"] += 1
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
        publications = {
            str(row["day"]): dict(row)
            for row in conn.execute(
                "SELECT * FROM investment_agent_day_publication"
            ).fetchall()
        }
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
        "audience": "investment",
        "selection_kind": str(
            publications[selected_day]["selection_kind"]
        ),
        "selection_limit": int(
            publications[selected_day]["selection_limit"]
        ),
        "selection_sha256": str(
            publications[selected_day]["selection_sha256"]
        ),
        "development_count": len(day_rows),
        "surfaced_development_count": sum(
            str(row["decision"]) == "surface" for row in day_rows
        ),
        "suppressed_development_count": sum(
            str(row["decision"]) == "suppress" for row in day_rows
        ),
        "company_connection_count": sum(
            int(row["assessed_company_count"]) for row in day_rows
        ),
        "memo_rejected_count": sum(
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
                "headline": str(final["headline"]),
                "what_changed": str(final["what_changed"]),
                "connections": final["connections"],
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


def summary_payload(path: Path = DEFAULT_DB) -> dict[str, Any]:
    """Aggregate durable run state for operator inspection."""
    conn = _open_readonly(path)
    if conn is None:
        return {
            "schema_version": READ_SCHEMA_VERSION,
            "available": False,
            "reason": "No company-aware Investment run has been stored yet.",
            "run_count": 0,
            "published_days": [],
        }
    try:
        totals = conn.execute(
            """
            SELECT COUNT(*) AS run_count,
                   COUNT(DISTINCT day) AS day_count,
                   COALESCE(SUM(reported_cost_usd), 0) AS cost_usd,
                   COALESCE(SUM(input_tokens), 0) AS input_tokens,
                   COALESCE(SUM(cached_tokens), 0) AS cached_tokens,
                   COALESCE(SUM(output_tokens), 0) AS output_tokens
              FROM investment_agent_run
            """
        ).fetchone()
        versions = [
            {"prompt_version": str(row["prompt_version"]), "run_count": int(row["n"])}
            for row in conn.execute(
                """
                SELECT prompt_version, COUNT(*) AS n
                  FROM investment_agent_run
                 GROUP BY prompt_version
                 ORDER BY prompt_version
                """
            )
        ]
        published = [
            {
                "day": str(row["day"]),
                "candidate_count": int(row["candidate_count"]),
                "published_at": str(row["published_at"]),
            }
            for row in conn.execute(
                """
                SELECT day, candidate_count, published_at
                  FROM investment_agent_day_publication
                 ORDER BY day
                """
            )
        ]
        return {
            "schema_version": READ_SCHEMA_VERSION,
            "available": True,
            "reason": None,
            "run_count": int(totals["run_count"]),
            "day_count": int(totals["day_count"]),
            "reported_cost_usd": round(float(totals["cost_usd"]), 6),
            "input_tokens": int(totals["input_tokens"]),
            "cached_tokens": int(totals["cached_tokens"]),
            "output_tokens": int(totals["output_tokens"]),
            "prompt_versions": versions,
            "published_days": published,
        }
    finally:
        conn.close()
