"""Deterministic offline replay diagnostics for the layered daily Event rank."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Iterable
from uuid import uuid4

from fli.routing import runs as routing_runs
from fli.scoring.attention import DAILY_RANK_VERSION, LAYER_NAMES
from fli.web import events as event_store


SCHEMA_VERSION = "2.0"
TOP_K = 100
VOTE_BUCKETS = ("0", "1", "2", "3-4", "5+")
ROUTING_PROMPT_VERSION = "audience-routing-v9"


@dataclass(frozen=True)
class RoutingLabel:
    event_id: str
    baseline_rank: int
    relevant: bool


@dataclass(frozen=True)
class ReplayedEvent:
    day: str
    event_id: str
    daily_rank: int
    trusted_votes: int
    decided_at_layer: int
    relevant: bool | None
    baseline_rank: int | None


@dataclass(frozen=True)
class ReplayedDay:
    day: str
    events: tuple[ReplayedEvent, ...]
    routing_label_count: int
    unmatched_label_count: int


def _canonical_json(value: Any, *, pretty: bool = False) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2 if pretty else None,
        sort_keys=True,
        separators=None if pretty else (",", ":"),
    )


def _routing_sources(root: Path) -> list[tuple[str, Path]]:
    """Return the newest complete compatible routing store for each day."""
    selected: dict[str, tuple[str, Path]] = {}
    for path in sorted(root.glob("*/routing.db")):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            meta = conn.execute(
                "SELECT * FROM run_meta WHERE singleton = 1"
            ).fetchone()
            if (
                meta is None
                or str(meta["prompt_version"]) != ROUTING_PROMPT_VERSION
                or "rank_version" not in meta.keys()
                or str(meta["rank_version"]) != DAILY_RANK_VERSION
            ):
                continue
            incomplete = int(
                conn.execute(
                    "SELECT COUNT(*) FROM routing_item WHERE status != 'complete'"
                ).fetchone()[0]
            )
            if incomplete:
                continue
            day = str(meta["day"])
            updated_at = str(meta["updated_at"])
            if day not in selected or updated_at > selected[day][0]:
                selected[day] = (updated_at, path)
        finally:
            conn.close()
    return [(day, selected[day][1]) for day in sorted(selected)]


def load_routing_labels(
    *,
    routing_root: Path = routing_runs.DEFAULT_RUN_ROOT,
    from_day: str | None = None,
    through: str | None = None,
) -> dict[str, dict[str, RoutingLabel]]:
    """Load current-rank audience judgments as optional, censored labels."""
    days: dict[str, dict[str, RoutingLabel]] = {}
    for day, path in _routing_sources(routing_root):
        if from_day and day < from_day:
            continue
        if through and day > through:
            continue
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """SELECT event_id, feed_rank, ai_engineering_relevant,
                          investment_relevant
                   FROM routing_item
                   WHERE status = 'complete'
                   ORDER BY feed_rank, event_id"""
            ).fetchall()
        finally:
            conn.close()
        days[day] = {
            str(row["event_id"]): RoutingLabel(
                event_id=str(row["event_id"]),
                baseline_rank=int(row["feed_rank"]),
                relevant=bool(
                    row["ai_engineering_relevant"]
                    or row["investment_relevant"]
                ),
            )
            for row in rows
        }
    return days


def _validated_day(value: str | None, *, flag: str) -> str | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError(f"{flag} must be an ISO date (YYYY-MM-DD)") from exc


def load_saved_days(
    *,
    routing_root: Path = routing_runs.DEFAULT_RUN_ROOT,
    from_day: str | None = None,
    through: str | None = None,
) -> dict[str, ReplayedDay]:
    """Replay every Event in each selected day of the current published run."""
    from_day = _validated_day(from_day, flag="--from-day")
    through = _validated_day(through, flag="--through")
    if from_day and through and from_day > through:
        raise ValueError("--from-day cannot be after --through")

    summary = event_store.dates_payload()
    if not summary.get("available"):
        raise FileNotFoundError(
            "Current Event dates are unavailable: "
            f"{summary.get('reason', 'unknown reason')}"
        )
    effective_from = from_day or (
        str(summary["date_from"]) if summary.get("date_from") else None
    )
    effective_through = through or (
        str(summary["date_to"]) if summary.get("date_to") else None
    )
    selected_days = [
        str(row["day"])
        for row in summary.get("dates") or []
        if (not effective_from or str(row["day"]) >= effective_from)
        and (not effective_through or str(row["day"]) <= effective_through)
    ]
    if not selected_days:
        raise FileNotFoundError("No saved Event days matched the requested range")

    labels_by_day = load_routing_labels(
        routing_root=routing_root,
        from_day=from_day,
        through=through,
    )
    replayed: dict[str, ReplayedDay] = {}
    for day in selected_days:
        projection = event_store.events_payload(
            day=day,
            lane="all",
            sort="score",
            query="",
            limit=2**31 - 1,
            offset=0,
            include_evidence=False,
        )
        if not projection.get("available"):
            raise RuntimeError(
                f"Event projection is unavailable for {day}: "
                f"{projection.get('reason', 'unknown reason')}"
            )
        items = sorted(
            projection.get("items") or [],
            key=lambda item: (int(item["daily_rank"]), str(item["event_id"])),
        )
        expected_ranks = list(range(1, len(items) + 1))
        actual_ranks = [int(item["daily_rank"]) for item in items]
        if actual_ranks != expected_ranks:
            raise RuntimeError(f"{day} does not contain one contiguous daily rank")

        labels = labels_by_day.get(day, {})
        projected_ids = {str(item["event_id"]) for item in items}
        events: list[ReplayedEvent] = []
        for item in items:
            event_id = str(item["event_id"])
            components = item.get("rank_components") or {}
            if str(components.get("version")) != DAILY_RANK_VERSION:
                raise RuntimeError(
                    f"{day} Event {event_id} does not use {DAILY_RANK_VERSION}"
                )
            trusted_votes = int(components["trusted_votes"])
            decided_at_layer = int(components["decided_at_layer"])
            if trusted_votes < 0:
                raise RuntimeError(
                    f"{day} Event {event_id} has negative trusted votes"
                )
            if decided_at_layer not in range(1, len(LAYER_NAMES) + 1):
                raise RuntimeError(
                    f"{day} Event {event_id} has invalid layer attribution"
                )
            label = labels.get(event_id)
            events.append(
                ReplayedEvent(
                    day=day,
                    event_id=event_id,
                    daily_rank=int(item["daily_rank"]),
                    trusted_votes=trusted_votes,
                    decided_at_layer=decided_at_layer,
                    relevant=label.relevant if label else None,
                    baseline_rank=label.baseline_rank if label else None,
                )
            )
        replayed[day] = ReplayedDay(
            day=day,
            events=tuple(events),
            routing_label_count=len(labels),
            unmatched_label_count=len(set(labels) - projected_ids),
        )
    return replayed


def _vote_bucket(votes: int) -> str:
    if votes <= 0:
        return "0"
    if votes == 1:
        return "1"
    if votes == 2:
        return "2"
    if votes <= 4:
        return "3-4"
    return "5+"


def _vote_bucket_stats(events: Iterable[ReplayedEvent]) -> dict[str, dict[str, Any]]:
    rows = list(events)
    total = len(rows)
    output: dict[str, dict[str, Any]] = {}
    for bucket in VOTE_BUCKETS:
        selected = [event for event in rows if _vote_bucket(event.trusted_votes) == bucket]
        labeled = [event for event in selected if event.relevant is not None]
        relevant_count = sum(bool(event.relevant) for event in labeled)
        output[bucket] = {
            "event_count": len(selected),
            "share": round(len(selected) / total, 6) if total else 0.0,
            "labeled_count": len(labeled),
            "relevant_count": relevant_count,
            "hit_rate": (
                round(relevant_count / len(labeled), 6) if labeled else None
            ),
        }
    return output


def _layer_attribution(
    events: Iterable[ReplayedEvent],
) -> dict[str, dict[str, Any]]:
    rows = list(events)
    total = len(rows)
    output: dict[str, dict[str, Any]] = {}
    for layer, name in enumerate(LAYER_NAMES, start=1):
        count = sum(event.decided_at_layer == layer for event in rows)
        output[str(layer)] = {
            "name": name,
            "event_count": count,
            "share": round(count / total, 6) if total else 0.0,
        }
    return output


def _day_diagnostics(day: ReplayedDay) -> dict[str, Any]:
    events = list(day.events)
    top = events[:TOP_K]
    labeled = [event for event in events if event.relevant is not None]
    return {
        "day": day.day,
        "event_count": len(events),
        "top_100_count": len(top),
        "routing_label_count": day.routing_label_count,
        "matched_label_count": len(labeled),
        "unmatched_label_count": day.unmatched_label_count,
        "relevant_label_count": sum(bool(event.relevant) for event in labeled),
        "vote_buckets": _vote_bucket_stats(events),
        "top_100_vote_buckets": _vote_bucket_stats(top),
        "top_100_layer_attribution": _layer_attribution(top),
    }


def evaluation_payload(
    *,
    routing_root: Path = routing_runs.DEFAULT_RUN_ROOT,
    from_day: str | None = None,
    through: str | None = None,
) -> dict[str, Any]:
    days = load_saved_days(
        routing_root=routing_root,
        from_day=from_day,
        through=through,
    )
    per_day = [_day_diagnostics(day) for day in days.values()]
    all_events = [event for day in days.values() for event in day.events]
    all_top = [event for day in days.values() for event in day.events[:TOP_K]]
    matched_labels = [event for event in all_events if event.relevant is not None]
    aggregate = {
        "day_count": len(days),
        "event_count": len(all_events),
        "top_100_event_count": len(all_top),
        "routing_label_count": sum(day.routing_label_count for day in days.values()),
        "matched_label_count": len(matched_labels),
        "unmatched_label_count": sum(
            day.unmatched_label_count for day in days.values()
        ),
        "relevant_label_count": sum(
            bool(event.relevant) for event in matched_labels
        ),
        "vote_buckets": _vote_bucket_stats(all_events),
        "top_100_vote_buckets": _vote_bucket_stats(all_top),
        "top_100_layer_attribution": _layer_attribution(all_top),
    }
    return {
        "rank_contract": {
            "version": DAILY_RANK_VERSION,
            "type": "lexicographic",
            "layers": [
                {"layer": index, "name": name}
                for index, name in enumerate(LAYER_NAMES, start=1)
            ],
            "top_k": TOP_K,
        },
        "routing_root": str(routing_root),
        "days": sorted(days),
        "per_day": per_day,
        "aggregate": aggregate,
        "limitations": [
            "Routing labels are model judgments, not human ground truth.",
            (
                "Routing labels were selected under the historical top-100 gate; "
                "their hit rates do not measure recall below that gate."
            ),
            (
                "Layer attribution names the first layer separating each top-100 "
                "Event from its adjacent lower-ranked Event."
            ),
        ],
    }


def _result(
    *,
    command: str,
    status: str,
    data: Any,
    error: dict[str, Any] | None,
    request_id: str,
    started: float,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "status": status,
        "data": data,
        "error": error,
        "meta": {
            "request_id": request_id,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fli daily-rank")
    sub = parser.add_subparsers(dest="action", required=True)
    evaluate = sub.add_parser(
        "evaluate", help=f"Replay {DAILY_RANK_VERSION} over current saved Event days."
    )
    evaluate.add_argument(
        "--routing-root", type=Path, default=routing_runs.DEFAULT_RUN_ROOT
    )
    evaluate.add_argument("--from-day")
    evaluate.add_argument("--through")
    evaluate.add_argument("--json", action="store_true")
    evaluate.add_argument("--plain", action="store_true")
    evaluate.add_argument("--no-input", action="store_true")
    return parser


def _plain(payload: dict[str, Any]) -> str:
    if payload["status"] == "error":
        return f"{payload['error']['code']}: {payload['error']['message']}"
    data = payload["data"]
    aggregate = data["aggregate"]
    votes = aggregate["top_100_vote_buckets"]
    layers = aggregate["top_100_layer_attribution"]
    vote_summary = " · ".join(
        f"{bucket} votes {votes[bucket]['event_count']}" for bucket in VOTE_BUCKETS
    )
    layer_summary = " · ".join(
        f"L{layer} {layers[layer]['share']:.1%}" for layer in layers
    )
    return (
        f"{DAILY_RANK_VERSION}: {aggregate['event_count']} Events across "
        f"{aggregate['day_count']} days\n"
        f"top-100 vote buckets: {vote_summary}\n"
        f"top-100 deciding layers: {layer_summary}"
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    started = time.monotonic()
    request_id = str(uuid4())
    command = f"daily-rank.{args.action}"
    try:
        data = evaluation_payload(
            routing_root=args.routing_root,
            from_day=args.from_day,
            through=args.through,
        )
        payload = _result(
            command=command,
            status="ok",
            data=data,
            error=None,
            request_id=request_id,
            started=started,
        )
        exit_code = 0
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        payload = _result(
            command=command,
            status="error",
            data=None,
            error={
                "code": "E_EVALUATION_INPUT",
                "message": str(exc),
                "retryable": False,
                "hint": "Verify the current Event publication and routing root.",
            },
            request_id=request_id,
            started=started,
        )
        exit_code = 2
    print(_plain(payload) if args.plain else _canonical_json(payload))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
