"""Read-only UI projection over durable successor Insight runs."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import sqlite3
from typing import Any, Literal

from fli.insights import generation as insight_generation
from fli.insights import runs as insight_runs
from fli.routing import model as routing_model
from fli.scoring import attention


DEFAULT_AUDIENCE = insight_generation.InsightAudience.INVESTMENT.value
InsightStatus = Literal["kept", "suppressed", "all"]


def _audience(value: str) -> str:
    return insight_generation.require_audience(value).value


def _status(value: str) -> InsightStatus:
    if value not in {"kept", "suppressed", "all"}:
        raise ValueError(f"unsupported Insight status: {value!r}")
    return value  # type: ignore[return-value]


def _path(value: object | None) -> Path:
    return Path(value) if value is not None else insight_runs.DEFAULT_DB


def _reason(audience: str) -> str:
    label = audience.replace("_", " ")
    return f"No successor {label} Insight run has been generated yet."


def _open(path: Path) -> sqlite3.Connection | None:
    if not path.is_file():
        return None
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _db_version(path: Path) -> tuple[str, int, int, int, int]:
    """Return a cache token that notices replacement and WAL writes."""
    try:
        stat = path.stat()
        main_mtime, main_size = stat.st_mtime_ns, stat.st_size
    except FileNotFoundError:
        main_mtime, main_size = 0, 0
    wal = Path(f"{path}-wal")
    try:
        wal_stat = wal.stat()
        wal_mtime, wal_size = wal_stat.st_mtime_ns, wal_stat.st_size
    except FileNotFoundError:
        wal_mtime, wal_size = 0, 0
    return str(path.resolve()), main_mtime, main_size, wal_mtime, wal_size


@lru_cache(maxsize=64)
def _routing_source_cached(
    version: tuple[str, int, int, int, int],
) -> dict[str, Any]:
    path = Path(version[0])
    conn = _open(path)
    if conn is None:
        return {"current": False, "packets": {}}
    try:
        meta = conn.execute(
            """SELECT run_id, prompt_version, prompt_sha256, schema_version,
                      rank_version
               FROM run_meta WHERE singleton = 1"""
        ).fetchone()
        if meta is None or (
            str(meta["prompt_version"]) != routing_model.PROMPT_VERSION
            or str(meta["prompt_sha256"]) != routing_model.prompt_sha256()
            or str(meta["schema_version"]) != routing_model.SCHEMA_VERSION
            or str(meta["rank_version"]) != attention.DAILY_RANK_VERSION
        ):
            return {"current": False, "packets": {}}
        rows = conn.execute(
            """SELECT event_id, packet_json FROM routing_item
               WHERE status = 'complete'"""
        ).fetchall()
    except sqlite3.DatabaseError:
        return {"current": False, "packets": {}}
    finally:
        conn.close()
    packets: dict[str, dict[str, Any]] = {}
    for row in rows:
        try:
            packet = json.loads(str(row["packet_json"]))
        except (TypeError, ValueError):
            continue
        if isinstance(packet, dict):
            packets[str(row["event_id"])] = packet
    return {"current": True, "run_id": str(meta["run_id"]), "packets": packets}


def _routing_source(source_db: str) -> dict[str, Any]:
    path = Path(source_db)
    if not path.is_absolute():
        path = insight_runs.REPO_ROOT / path
    return _routing_source_cached(_db_version(path))


def _source_payload(row: dict[str, Any]) -> dict[str, Any]:
    source = _routing_source(str(row["source_routing_db"]))
    packet = source["packets"].get(str(row["event_id"]), {})
    sources = packet.get("sources", [])
    if not isinstance(sources, list):
        sources = []
    root_source_url = None
    artifacts: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            continue
        url = str(source.get("url") or "").strip()
        if not url:
            continue
        if source.get("relation") == "root" and root_source_url is None:
            root_source_url = url
        if source.get("source_type") != "artifact" or url in seen_urls:
            continue
        seen_urls.add(url)
        artifacts.append(
            {
                "title": str(source.get("title") or "Primary artifact"),
                "url": url,
            }
        )
    return {"root_source_url": root_source_url, "artifacts": artifacts}


def _current_rows(
    conn: sqlite3.Connection, *, audience: str
) -> list[dict[str, Any]]:
    prompt = insight_generation.contract(audience)
    rows = conn.execute(
        """WITH ranked AS (
                 SELECT item.*, run.source_routing_run_id, run.source_routing_db,
                        ROW_NUMBER() OVER (
                            PARTITION BY item.event_id, item.audience
                            ORDER BY item.completed_at DESC, item.run_id DESC
                        ) AS recency_order
                 FROM insight_item AS item
                 JOIN insight_run AS run ON run.run_id = item.run_id
                 WHERE item.status = 'complete'
                   AND item.audience = ?
                   AND item.prompt_version = ?
                   AND item.prompt_sha256 = ?
                   AND item.schema_version = ?
                   AND item.title IS NOT NULL
             )
             SELECT * FROM ranked WHERE recency_order = 1
             ORDER BY feed_rank, event_id""",
        (
            audience,
            prompt.version,
            prompt.sha256,
            insight_generation.SCHEMA_VERSION,
        ),
    ).fetchall()
    projected: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        source = _routing_source(str(row["source_routing_db"]))
        if (
            not source["current"]
            or str(row["source_routing_run_id"]) != source.get("run_id")
            or str(row["event_id"]) not in source["packets"]
        ):
            continue
        projected.append(item)
    projected.sort(key=lambda item: (int(item["feed_rank"]), str(item["event_id"])))
    return projected


def _dates_payload(audience: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_day: dict[str, dict[str, int | str]] = {}
    for row in rows:
        day = str(row["day"])
        counts = by_day.setdefault(
            day,
            {"day": day, "item_count": 0, "suppressed_count": 0, "evaluated_count": 0},
        )
        counts["evaluated_count"] = int(counts["evaluated_count"]) + 1
        field = "item_count" if row["decision"] == "surface" else "suppressed_count"
        counts[field] = int(counts[field]) + 1
    dates = [by_day[day] for day in sorted(by_day)]
    return {
        "available": bool(dates),
        "reason": None if dates else _reason(audience),
        "audience": audience,
        "latest_date": str(dates[-1]["day"]) if dates else None,
        "dates": dates,
    }


def insight_dates_payload(
    *,
    audience: str = DEFAULT_AUDIENCE,
    db_path: object | None = None,
    run_root: object | None = None,
) -> dict[str, Any]:
    """Return every evaluated day; the pill count is the number kept."""
    del run_root
    selected = _audience(audience)
    conn = _open(_path(db_path))
    if conn is None:
        return _dates_payload(selected, [])
    try:
        return _dates_payload(selected, _current_rows(conn, audience=selected))
    finally:
        conn.close()


def _item_payload(row: dict[str, Any]) -> dict[str, Any]:
    decision = str(row["decision"])
    why_it_matters = row["why_it_matters"]
    audience = insight_generation.require_audience(str(row["audience"]))
    return {
        "candidate_id": str(row["candidate_id"]),
        "event_id": str(row["event_id"]),
        "day": str(row["day"]),
        "feed_rank": int(row["feed_rank"]),
        "audience": str(row["audience"]),
        "decision": decision,
        "decision_reason": (
            str(row["suppression_reason"])
            if decision == "suppress"
            else str(why_it_matters)
        ),
        "title": str(row["title"]),
        "summary": str(row["summary"]) if row["summary"] is not None else None,
        "why_it_matters": (
            str(why_it_matters) if why_it_matters is not None else None
        ),
        "action": str(row["action"]) if row["action"] is not None else None,
        "action_label": insight_generation.ACTION_LABELS[audience],
        "model": str(row["model"]),
        "reasoning_effort": str(row["reasoning_effort"]),
        "prompt_version": str(row["prompt_version"]),
        "source_routing_run_id": str(row["source_routing_run_id"]),
        **_source_payload(row),
    }


def insights_payload(
    *,
    audience: str = DEFAULT_AUDIENCE,
    day: str | None = None,
    status: str = "kept",
    db_path: object | None = None,
    run_root: object | None = None,
) -> dict[str, Any]:
    """Return latest decisions by Event, ordered only by frozen Feed rank."""
    del run_root
    selected_audience = _audience(audience)
    selected_status = _status(status)
    conn = _open(_path(db_path))
    if conn is None:
        return {
            "available": False,
            "reason": _reason(selected_audience),
            "audience": selected_audience,
            "status": selected_status,
            "run": None,
            "items": [],
        }
    try:
        current_rows = _current_rows(conn, audience=selected_audience)
        selected_day = day or max(
            (str(row["day"]) for row in current_rows), default=None
        )
        all_rows = [
            row for row in current_rows if str(row["day"]) == selected_day
        ]
    finally:
        conn.close()
    if not all_rows:
        return {
            "available": False,
            "reason": _reason(selected_audience),
            "audience": selected_audience,
            "status": selected_status,
            "run": None,
            "items": [],
        }
    counts = {
        "all": len(all_rows),
        "kept": sum(row["decision"] == "surface" for row in all_rows),
        "suppressed": sum(row["decision"] == "suppress" for row in all_rows),
    }
    decision = {"kept": "surface", "suppressed": "suppress"}.get(selected_status)
    rows = [row for row in all_rows if decision is None or row["decision"] == decision]
    newest = max(all_rows, key=lambda row: (str(row["completed_at"]), str(row["run_id"])))
    run = {
        "run_id": str(newest["run_id"]),
        "day": str(selected_day),
        "audience": selected_audience,
        "candidate_count": len(all_rows),
        "complete_count": len(all_rows),
        "surfaced_count": counts["kept"],
        "suppressed_count": counts["suppressed"],
        "model": str(newest["model"]),
        "prompt_version": str(newest["prompt_version"]),
        "input_tokens": sum(int(row["input_tokens"] or 0) for row in all_rows),
        "cached_tokens": sum(int(row["cached_tokens"] or 0) for row in all_rows),
        "reported_cost_usd": round(
            sum(float(row["reported_cost_usd"] or 0) for row in all_rows), 8
        ),
        "counts": counts,
    }
    reason = None
    if not rows:
        reason = (
            "No kept Insight cleared the final editorial gate for this day."
            if selected_status == "kept"
            else "No Insight was suppressed for this day."
        )
    return {
        "available": True,
        "reason": reason,
        "audience": selected_audience,
        "status": selected_status,
        "run": run,
        "items": [_item_payload(row) for row in rows],
    }
