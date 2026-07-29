"""Durable storage and read projection for surface-linked Engineering Insights."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = (
    REPO_ROOT / "data" / "derived" / "insights" / "engineering-agent.db"
)
SURFACE_PATH = REPO_ROOT / "docs" / "references" / "aion-surfaces.json"
STORE_SCHEMA_VERSION = "engineering-agent-store-v1"
READ_SCHEMA_VERSION = "engineering-agent-read-v1"
CURRENT_PROMPT_VERSION = "engineering-agent-v3"
TRACE_SCHEMA_VERSIONS = {"engineering-agent-trace-v1"}
STATUSES = {"kept", "suppressed", "all"}
RESULT_FIELDS = {
    "headline",
    "what_changed",
    "decision",
    "lands",
    "no_match_reason",
}
LANDING_FIELDS = {"surface_id", "why"}
MAX_LANDINGS = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS engineering_agent_meta (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    schema_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS engineering_agent_run (
    run_id TEXT PRIMARY KEY,
    day TEXT NOT NULL,
    development_id TEXT NOT NULL,
    daily_rank INTEGER NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('surface', 'suppress')),
    prompt_version TEXT NOT NULL,
    prompt_cache_key TEXT NOT NULL,
    model TEXT NOT NULL,
    reasoning_effort TEXT NOT NULL,
    surface_count INTEGER NOT NULL,
    surfaces_sha256 TEXT NOT NULL,
    evidence_sha256 TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    landing_count INTEGER NOT NULL,
    input_tokens INTEGER NOT NULL,
    cached_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    reasoning_tokens INTEGER NOT NULL,
    reported_cost_usd REAL NOT NULL,
    result_sha256 TEXT NOT NULL,
    final_result_json TEXT NOT NULL,
    trace_json TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    UNIQUE (
        day, development_id, input_sha256, prompt_version, model,
        reasoning_effort, result_sha256
    )
);

CREATE INDEX IF NOT EXISTS idx_engineering_agent_run_day_rank
    ON engineering_agent_run(day, daily_rank, development_id);

CREATE TABLE IF NOT EXISTS engineering_agent_day_publication (
    day TEXT PRIMARY KEY,
    audience TEXT NOT NULL CHECK (audience = 'ai_engineering'),
    selection_kind TEXT NOT NULL,
    selection_limit INTEGER NOT NULL,
    selection_sha256 TEXT NOT NULL,
    candidate_count INTEGER NOT NULL,
    published_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS engineering_agent_day_publication_item (
    day TEXT NOT NULL,
    development_id TEXT NOT NULL,
    daily_rank INTEGER NOT NULL,
    PRIMARY KEY (day, development_id),
    UNIQUE (day, daily_rank),
    FOREIGN KEY (day) REFERENCES engineering_agent_day_publication(day)
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


def surface_map() -> dict[str, dict[str, Any]]:
    """Return the canonical Aion surface map keyed by surface id."""
    payload = json.loads(SURFACE_PATH.read_text(encoding="utf-8"))
    surfaces = {str(item["id"]): item for item in payload["surfaces"]}
    if len(surfaces) != int(payload["surface_count"]):
        raise ValueError("the Aion surface map repeats a surface id")
    return surfaces


def connect(path: Path = DEFAULT_DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.executescript(SCHEMA)
    row = conn.execute(
        "SELECT schema_version FROM engineering_agent_meta WHERE singleton = 1"
    ).fetchone()
    if row is None:
        conn.execute(
            """INSERT INTO engineering_agent_meta(singleton, schema_version)
               VALUES (1, ?)""",
            (STORE_SCHEMA_VERSION,),
        )
    elif str(row["schema_version"]) != STORE_SCHEMA_VERSION:
        raise ValueError(
            "unsupported Engineering agent store schema "
            f"{row['schema_version']!r}"
        )
    conn.commit()
    return conn


def _validate_trace(trace: dict[str, Any]) -> None:
    if trace.get("schema_version") not in TRACE_SCHEMA_VERSIONS:
        raise ValueError("unsupported Engineering agent trace schema")
    final = trace.get("final_result")
    if not isinstance(final, dict):
        raise ValueError("Engineering agent trace has no validated final result")
    if set(final) != RESULT_FIELDS:
        raise ValueError("Engineering agent result does not match the v1 schema")
    headline = str(final.get("headline") or "").strip()
    if not headline or "\n" in headline or len(headline.split()) > 18:
        raise ValueError("Engineering agent result has an invalid headline")
    if not str(final.get("what_changed") or "").strip():
        raise ValueError("Engineering agent result has an empty what_changed")
    decision = final.get("decision")
    if decision not in {"surface", "suppress"}:
        raise ValueError("Engineering agent result has an invalid decision")
    landings = final.get("lands")
    if not isinstance(landings, list):
        raise ValueError("Engineering agent result has invalid surface landings")
    if decision == "surface" and not landings:
        raise ValueError("a surfaced Engineering result has no surface landing")
    if decision == "suppress" and landings:
        raise ValueError("a suppressed Engineering result cites a surface")
    if len(landings) > MAX_LANDINGS:
        raise ValueError(
            f"an Engineering result cites more than {MAX_LANDINGS} surfaces"
        )
    known = set(surface_map())
    cited: list[str] = []
    for landing in landings:
        if not isinstance(landing, dict) or set(landing) != LANDING_FIELDS:
            raise ValueError(
                "an Engineering landing does not match the v1 schema"
            )
        surface_id = str(landing["surface_id"]).strip()
        if surface_id not in known:
            raise ValueError(
                f"Engineering result cites unknown surface {surface_id!r}"
            )
        if not str(landing["why"]).strip():
            raise ValueError("an Engineering landing has an empty why")
        cited.append(surface_id)
    if len(cited) != len(set(cited)):
        raise ValueError("an Engineering result repeats a surface")
    reason = final.get("no_match_reason")
    if decision == "suppress" and not str(reason or "").strip():
        raise ValueError("a suppressed Engineering result has no reason")
    if decision == "surface" and reason is not None:
        raise ValueError("a surfaced Engineering result carries a suppression reason")


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
        f"engineering-agent-{trace['date']}-"
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
        "surface_count": int(trace["surface_count"]),
        "surfaces_sha256": str(trace["surfaces_sha256"]),
        "evidence_sha256": str(trace["evidence_sha256"]),
        "input_sha256": str(trace["input_sha256"]),
        "landing_count": len(final["lands"]),
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
        "trace_json": _canonical_json(trace),
        "completed_at": _now(),
    }
    conn = connect(db_path)
    try:
        conn.execute(
            """INSERT OR IGNORE INTO engineering_agent_run (
                   run_id, day, development_id, daily_rank, decision,
                   prompt_version, prompt_cache_key, model, reasoning_effort,
                   surface_count, surfaces_sha256, evidence_sha256,
                   input_sha256, landing_count, input_tokens, cached_tokens,
                   output_tokens, reasoning_tokens, reported_cost_usd,
                   result_sha256, final_result_json, trace_json, completed_at
               ) VALUES (
                   :run_id, :day, :development_id, :daily_rank, :decision,
                   :prompt_version, :prompt_cache_key, :model,
                   :reasoning_effort, :surface_count, :surfaces_sha256,
                   :evidence_sha256, :input_sha256, :landing_count,
                   :input_tokens, :cached_tokens, :output_tokens,
                   :reasoning_tokens, :reported_cost_usd, :result_sha256,
                   :final_result_json, :trace_json, :completed_at
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
        "surface_landings": values["landing_count"],
        "reported_cost_usd": values["reported_cost_usd"],
    }


def publish_day(
    *,
    day: str,
    candidates: list[dict[str, Any]],
    selection_limit: int,
    db_path: Path = DEFAULT_DB,
) -> dict[str, Any]:
    """Atomically publish one complete Engineering-routed daily cohort."""
    return publish_days(
        publications=[
            {
                "day": day,
                "candidates": candidates,
                "selection_limit": selection_limit,
            }
        ],
        db_path=db_path,
    )[0]


def published_development_days(
    *,
    db_path: Path = DEFAULT_DB,
) -> dict[str, str]:
    """Return the canonical published owner day for each Development."""
    conn = _open_readonly(db_path)
    if conn is None:
        return {}
    try:
        rows = conn.execute(
            """SELECT development_id, day
               FROM engineering_agent_day_publication_item
               ORDER BY day, development_id"""
        ).fetchall()
    finally:
        conn.close()
    owners: dict[str, str] = {}
    for row in rows:
        owners.setdefault(str(row["development_id"]), str(row["day"]))
    return owners


def publish_days(
    *,
    publications: list[dict[str, Any]],
    db_path: Path = DEFAULT_DB,
) -> list[dict[str, Any]]:
    """Atomically replace one or more complete Engineering daily cohorts."""
    if not publications:
        raise ValueError("cannot publish an empty Engineering day set")
    normalized_publications: list[dict[str, Any]] = []
    for publication in publications:
        day = str(publication["day"])
        candidates = publication["candidates"]
        selection_limit = int(publication["selection_limit"])
        if not candidates:
            raise ValueError("cannot publish an empty Engineering cohort")
        normalized = [
            {
                "development_id": str(item["development_id"]),
                "daily_rank": int(item["daily_rank"]),
            }
            for item in candidates
        ]
        if len({item["development_id"] for item in normalized}) != len(normalized):
            raise ValueError("Engineering publication repeats a Development")
        if len({item["daily_rank"] for item in normalized}) != len(normalized):
            raise ValueError("Engineering publication repeats a daily rank")
        normalized.sort(
            key=lambda item: (item["daily_rank"], item["development_id"])
        )
        normalized_publications.append(
            {
                "day": day,
                "candidates": normalized,
                "selection_limit": selection_limit,
                "selection_sha256": _sha256(
                    {
                        "audience": "ai_engineering",
                        "selection_kind": "top_engineering_routed",
                        "selection_limit": selection_limit,
                        "candidates": normalized,
                    }
                ),
            }
        )
    days = [item["day"] for item in normalized_publications]
    if len(days) != len(set(days)):
        raise ValueError("Engineering publication repeats a day")
    development_ids = [
        candidate["development_id"]
        for publication in normalized_publications
        for candidate in publication["candidates"]
    ]
    if len(development_ids) != len(set(development_ids)):
        raise ValueError(
            "cannot publish an Engineering Development on more than one day"
        )
    replacement_days = set(days)
    conn = connect(db_path)
    try:
        repeated = conn.execute(
            f"""SELECT development_id, day
                FROM engineering_agent_day_publication_item
                WHERE day NOT IN ({",".join("?" for _ in replacement_days)})
                  AND development_id IN (
                      {",".join("?" for _ in development_ids)}
                  )
                ORDER BY day, development_id
                LIMIT 1""",
            (*sorted(replacement_days), *development_ids),
        ).fetchone()
        if repeated is not None:
            raise ValueError(
                "cannot publish an Engineering Development on more than one "
                f"day: {repeated['development_id']} already belongs to "
                f"{repeated['day']}"
            )
        for publication in normalized_publications:
            for item in publication["candidates"]:
                row = conn.execute(
                    """SELECT 1
                       FROM engineering_agent_run
                       WHERE day = ?
                         AND development_id = ?
                         AND daily_rank = ?
                         AND prompt_version = ?
                       LIMIT 1""",
                    (
                        publication["day"],
                        item["development_id"],
                        item["daily_rank"],
                        CURRENT_PROMPT_VERSION,
                    ),
                ).fetchone()
                if row is None:
                    raise ValueError(
                        "cannot publish an Engineering candidate without a "
                        "completed imported run"
                    )
        now = _now()
        with conn:
            conn.executemany(
                "DELETE FROM engineering_agent_day_publication_item WHERE day = ?",
                [(day,) for day in days],
            )
            conn.executemany(
                "DELETE FROM engineering_agent_day_publication WHERE day = ?",
                [(day,) for day in days],
            )
            conn.executemany(
                """INSERT INTO engineering_agent_day_publication (
                       day, audience, selection_kind, selection_limit,
                       selection_sha256, candidate_count, published_at
                   ) VALUES (
                       ?, 'ai_engineering', 'top_engineering_routed', ?, ?, ?, ?
                   )""",
                [
                    (
                        publication["day"],
                        publication["selection_limit"],
                        publication["selection_sha256"],
                        len(publication["candidates"]),
                        now,
                    )
                    for publication in normalized_publications
                ],
            )
            conn.executemany(
                """INSERT INTO engineering_agent_day_publication_item (
                       day, development_id, daily_rank
                   ) VALUES (?, ?, ?)""",
                [
                    (
                        publication["day"],
                        item["development_id"],
                        item["daily_rank"],
                    )
                    for publication in normalized_publications
                    for item in publication["candidates"]
                ],
            )
    finally:
        conn.close()
    return [
        {
            "schema_version": STORE_SCHEMA_VERSION,
            "day": publication["day"],
            "audience": "ai_engineering",
            "selection_kind": "top_engineering_routed",
            "selection_limit": publication["selection_limit"],
            "selection_sha256": publication["selection_sha256"],
            "candidate_count": len(publication["candidates"]),
            "published_at": now,
        }
        for publication in normalized_publications
    ]


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
               FROM engineering_agent_run AS run
               WHERE run.prompt_version = ?
           ),
           canonical_publication AS (
               SELECT publication.*,
                      ROW_NUMBER() OVER (
                          PARTITION BY development_id
                          ORDER BY day, daily_rank
                      ) AS publication_order
               FROM engineering_agent_day_publication_item AS publication
           )
           SELECT current.*
           FROM current
           JOIN canonical_publication AS publication
             ON publication.day = current.day
            AND publication.development_id = current.development_id
            AND publication.daily_rank = current.daily_rank
           WHERE current.recency_order = 1
             AND publication.publication_order = 1
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
            "reason": "No surface-linked Engineering run has been stored yet.",
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
                "content_kind": "engineering_agent",
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
        "reason": None if ordered else "No surface-linked Engineering run is complete.",
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
    surfaces = surface_map()
    conn = _open_readonly(db_path)
    if conn is None:
        return {
            "schema_version": READ_SCHEMA_VERSION,
            "available": False,
            "reason": "No surface-linked Engineering run has been stored yet.",
            "requested_date": day,
            "date": None,
            "audience": "ai_engineering",
            "status": status,
            "content_kind": "engineering_agent",
            "run": None,
            "surfaces": [],
            "items": [],
        }
    try:
        current = _latest_rows(conn)
        publications = {
            str(row["day"]): dict(row)
            for row in conn.execute(
                "SELECT * FROM engineering_agent_day_publication"
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
    surface_cards = [
        {"id": item["id"], "name": item["name"], "what": item["what"]}
        for item in surfaces.values()
    ]
    if not day_rows:
        return {
            "schema_version": READ_SCHEMA_VERSION,
            "available": False,
            "reason": "No surface-linked Engineering result exists for this date.",
            "requested_date": day,
            "date": selected_day,
            "audience": "ai_engineering",
            "status": status,
            "content_kind": "engineering_agent",
            "run": None,
            "surfaces": surface_cards,
            "items": [],
        }
    run = {
        "date": selected_day,
        "audience": "ai_engineering",
        "selection_kind": str(publications[selected_day]["selection_kind"]),
        "selection_limit": int(publications[selected_day]["selection_limit"]),
        "selection_sha256": str(publications[selected_day]["selection_sha256"]),
        "development_count": len(day_rows),
        "surfaced_development_count": sum(
            str(row["decision"]) == "surface" for row in day_rows
        ),
        "suppressed_development_count": sum(
            str(row["decision"]) == "suppress" for row in day_rows
        ),
        "surface_landing_count": sum(
            int(row["landing_count"]) for row in day_rows
        ),
        "surface_count": int(day_rows[-1]["surface_count"]),
        "model": str(day_rows[-1]["model"]),
        "reasoning_effort": str(day_rows[-1]["reasoning_effort"]),
        "prompt_version": str(day_rows[-1]["prompt_version"]),
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
        lands = [
            {
                "surface_id": str(landing["surface_id"]),
                "surface_name": str(
                    surfaces[str(landing["surface_id"])]["name"]
                ),
                "why": str(landing["why"]),
            }
            for landing in final["lands"]
        ]
        items.append(
            {
                "run_id": str(row["run_id"]),
                "day": str(row["day"]),
                "development_id": str(row["development_id"]),
                "daily_rank": int(row["daily_rank"]),
                "decision": str(row["decision"]),
                "headline": str(final["headline"]),
                "what_changed": str(final["what_changed"]),
                "lands": lands,
                "no_match_reason": final["no_match_reason"],
                "telemetry": {
                    "model": str(row["model"]),
                    "reasoning_effort": str(row["reasoning_effort"]),
                    "prompt_version": str(row["prompt_version"]),
                    "surface_count": int(row["surface_count"]),
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
            "No surface-linked Engineering result was suppressed on this date."
            if status == "suppressed"
            else "No surface-linked Engineering result matches this view."
        )
    return {
        "schema_version": READ_SCHEMA_VERSION,
        "available": True,
        "reason": reason,
        "requested_date": day,
        "date": selected_day,
        "audience": "ai_engineering",
        "status": status,
        "content_kind": "engineering_agent",
        "run": run,
        "surfaces": surface_cards,
        "items": items,
    }


def summary_payload(path: Path = DEFAULT_DB) -> dict[str, Any]:
    """Aggregate durable run state for operator inspection."""
    conn = _open_readonly(path)
    if conn is None:
        return {
            "schema_version": READ_SCHEMA_VERSION,
            "available": False,
            "reason": "No surface-linked Engineering run has been stored yet.",
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
              FROM engineering_agent_run
            """
        ).fetchone()
        surfaced = conn.execute(
            """
            SELECT decision, COUNT(*) AS n
              FROM engineering_agent_run
             GROUP BY decision
            """
        ).fetchall()
        published = [
            {
                "day": str(row["day"]),
                "candidate_count": int(row["candidate_count"]),
                "published_at": str(row["published_at"]),
            }
            for row in conn.execute(
                """SELECT day, candidate_count, published_at
                     FROM engineering_agent_day_publication
                    ORDER BY day"""
            ).fetchall()
        ]
    finally:
        conn.close()
    return {
        "schema_version": READ_SCHEMA_VERSION,
        "available": int(totals["run_count"]) > 0,
        "reason": None,
        "run_count": int(totals["run_count"]),
        "day_count": int(totals["day_count"]),
        "decisions": {str(row["decision"]): int(row["n"]) for row in surfaced},
        "input_tokens": int(totals["input_tokens"]),
        "cached_tokens": int(totals["cached_tokens"]),
        "output_tokens": int(totals["output_tokens"]),
        "reported_cost_usd": round(float(totals["cost_usd"]), 6),
        "published_days": published,
    }
