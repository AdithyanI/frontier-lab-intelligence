"""Read-only UI projection over durable successor Insight runs."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import sqlite3
from typing import Any, Literal

from fli import insight_generation, insight_runs
from fli.web import events as event_store


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


@lru_cache(maxsize=32)
def _routing_packets(source_db: str) -> dict[str, dict[str, Any]]:
    path = Path(source_db)
    if not path.is_absolute():
        path = insight_runs.REPO_ROOT / path
    conn = _open(path)
    if conn is None:
        return {}
    try:
        rows = conn.execute("SELECT event_id, packet_json FROM routing_item").fetchall()
    except sqlite3.DatabaseError:
        return {}
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
    return packets


def _source_payload(row: dict[str, Any]) -> dict[str, Any]:
    packet = _routing_packets(str(row["source_routing_db"])).get(
        str(row["event_id"]), {}
    )
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
    rows = conn.execute(
        """WITH ranked AS (
                 SELECT item.*, run.source_routing_run_id, run.source_routing_db,
                        ROW_NUMBER() OVER (
                            PARTITION BY item.event_id, item.audience
                            ORDER BY item.completed_at DESC, item.run_id DESC
                        ) AS revision
                 FROM insight_item AS item
                 JOIN insight_run AS run ON run.run_id = item.run_id
                 WHERE item.status = 'complete' AND item.audience = ?
             )
             SELECT * FROM ranked WHERE revision = 1
             ORDER BY feed_rank, event_id""",
        (audience,),
    ).fetchall()
    projected: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        location = event_store.canonical_event_location(str(row["event_id"]))
        if location is not None:
            item.update(location)
            item["candidate_id"] = insight_generation.candidate_id(
                str(row["audience"]), str(row["event_id"])
            )
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
    implication = row["implication"]
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
            else str(implication)
        ),
        "title": str(row["title"]) if row["title"] is not None else None,
        "summary": str(row["summary"]) if row["summary"] is not None else None,
        "implication": str(implication) if implication is not None else None,
        "next_step": str(row["next_step"]) if row["next_step"] is not None else None,
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
    """Return latest decisions by envelope, ordered only by frozen Feed rank."""
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


def extraction_dates_payload(
    *,
    audience: str = DEFAULT_AUDIENCE,
    db_path: object | None = None,
    run_root: object | None = None,
) -> dict[str, Any]:
    return insight_dates_payload(
        audience=audience, db_path=db_path, run_root=run_root
    )


def extraction_insights_payload(
    *,
    audience: str = DEFAULT_AUDIENCE,
    day: str | None = None,
    status: str = "kept",
    db_path: object | None = None,
    run_root: object | None = None,
) -> dict[str, Any]:
    return insights_payload(
        audience=audience,
        day=day,
        status=status,
        db_path=db_path,
        run_root=run_root,
    )
