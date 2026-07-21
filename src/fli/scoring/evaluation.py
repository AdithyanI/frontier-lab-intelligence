"""Reproducible offline evaluation of attention-score candidates."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Iterable
from uuid import uuid4

from fli.routing import runs as routing_runs
from fli.scoring.attention import (
    ATTENTION_V1_1,
    ATTENTION_V2_CANDIDATE,
    AttentionFormula,
    score_components,
)
from fli.web import events as event_store


SCHEMA_VERSION = "1.0"
DEFAULT_TOP_MOVERS = 10
GRID_AMPLIFIER_CAPS = (8, 16, 32)
GRID_SUPPORT_KNEES = (100, 150, 300)
GRID_WEIGHTS = ((0.55, 0.25, 0.20), (0.55, 0.20, 0.25))


@dataclass(frozen=True)
class LabeledEvent:
    day: str
    event_id: str
    baseline_rank: int
    relevant: bool
    attention_score: float
    score_components: dict[str, Any]
    day_member_count: int
    published_at: str


def _canonical_json(value: Any, *, pretty: bool = False) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2 if pretty else None,
        sort_keys=True,
        separators=None if pretty else (",", ":"),
    )


def _routing_sources(root: Path) -> list[tuple[str, Path]]:
    selected: dict[str, tuple[str, Path]] = {}
    for path in sorted(root.glob("*/routing.db")):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            meta = conn.execute(
                "SELECT * FROM run_meta WHERE singleton = 1"
            ).fetchone()
            if meta is None or str(meta["prompt_version"]) != "audience-routing-v9":
                continue
            incomplete = int(
                conn.execute(
                    "SELECT COUNT(*) FROM routing_item WHERE status != 'complete'"
                ).fetchone()[0]
            )
            if incomplete:
                continue
            day = str(meta["day"])
            key = str(meta["updated_at"])
            if day not in selected or key > selected[day][0]:
                selected[day] = (key, path)
        finally:
            conn.close()
    return [(day, selected[day][1]) for day in sorted(selected)]


def load_labeled_days(
    *,
    routing_root: Path = routing_runs.DEFAULT_RUN_ROOT,
    from_day: str | None = None,
    through: str | None = None,
) -> dict[str, list[LabeledEvent]]:
    days: dict[str, list[LabeledEvent]] = {}
    for day, path in _routing_sources(routing_root):
        if from_day and day < from_day:
            continue
        if through and day > through:
            continue
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            meta = conn.execute(
                "SELECT source_event_run_id FROM run_meta WHERE singleton = 1"
            ).fetchone()
            if meta is None:
                raise RuntimeError(f"Routing run has no metadata: {path}")
            labels = conn.execute(
                """SELECT event_id, feed_rank, ai_engineering_relevant,
                          investment_relevant
                   FROM routing_item
                   WHERE status = 'complete'
                   ORDER BY feed_rank, event_id"""
            ).fetchall()
        finally:
            conn.close()
        projection = event_store.events_payload(
            day=day,
            lane="all",
            sort="score",
            query="",
            limit=100_000,
            offset=0,
            include_evidence=False,
            event_run_id=str(meta["source_event_run_id"]),
        )
        if not projection.get("available"):
            raise RuntimeError(
                f"Event projection is unavailable for {day}: "
                f"{projection.get('reason', 'unknown reason')}"
            )
        by_event_id = {str(item["event_id"]): item for item in projection["items"]}
        missing = [
            str(row["event_id"])
            for row in labels
            if str(row["event_id"]) not in by_event_id
        ]
        if missing:
            raise RuntimeError(
                f"{day} is missing {len(missing)} routed Events from its source projection"
            )
        days[day] = []
        for row in labels:
            item = by_event_id[str(row["event_id"])]
            basis = item["daily_score_basis"]
            days[day].append(
                LabeledEvent(
                    day=day,
                    event_id=str(row["event_id"]),
                    baseline_rank=int(row["feed_rank"]),
                    relevant=bool(
                        row["ai_engineering_relevant"]
                        or row["investment_relevant"]
                    ),
                    attention_score=float(basis["attention_score"]),
                    score_components=dict(basis["score_components"]),
                    day_member_count=int(item["day_member_count"]),
                    published_at=str(basis["published_at"]),
                )
            )
    if not days:
        raise FileNotFoundError(
            f"No complete audience-routing-v9 runs found under {routing_root}"
        )
    return days


def _precision(rows: list[dict[str, Any]], k: int) -> float:
    selected = rows[: min(k, len(rows))]
    return sum(bool(row["relevant"]) for row in selected) / len(selected)


def _kendall_tau(baseline_ids: list[str], candidate_ids: list[str]) -> float:
    candidate_position = {
        event_id: index for index, event_id in enumerate(candidate_ids)
    }
    concordant = 0
    discordant = 0
    for left_index, left in enumerate(baseline_ids):
        for right in baseline_ids[left_index + 1 :]:
            if candidate_position[left] < candidate_position[right]:
                concordant += 1
            else:
                discordant += 1
    pairs = concordant + discordant
    return (concordant - discordant) / pairs if pairs else 1.0


def _candidate_rows(
    labels: Iterable[LabeledEvent], formula: AttentionFormula
) -> list[dict[str, Any]]:
    rows = []
    for item in labels:
        score, factors = score_components(item.score_components, formula)
        rows.append(
            {
                "event_id": item.event_id,
                "relevant": item.relevant,
                "baseline_rank": item.baseline_rank,
                "baseline_score": item.attention_score,
                "candidate_score": score,
                "registry_amplifiers": int(
                    item.score_components["registry_amplifiers"]
                ),
                "day_member_count": item.day_member_count,
                "published_at": item.published_at,
                "factors": factors,
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            row["candidate_score"],
            row["registry_amplifiers"],
            row["day_member_count"],
            row["published_at"],
            row["event_id"],
        ),
        reverse=True,
    )


def evaluate_formula(
    days: dict[str, list[LabeledEvent]], formula: AttentionFormula
) -> dict[str, Any]:
    per_day = []
    all_movers = []
    for day, labels in sorted(days.items()):
        baseline = sorted(labels, key=lambda item: item.baseline_rank)
        candidate = _candidate_rows(labels, formula)
        candidate_rank = {
            row["event_id"]: rank for rank, row in enumerate(candidate, start=1)
        }
        per_day.append(
            {
                "day": day,
                "labeled_count": len(labels),
                "relevant_count": sum(item.relevant for item in labels),
                "precision_at_20": round(_precision(candidate, 20), 6),
                "precision_at_50": round(_precision(candidate, 50), 6),
                "precision_at_100": round(_precision(candidate, 100), 6),
                "kendall_tau": round(
                    _kendall_tau(
                        [item.event_id for item in baseline],
                        [row["event_id"] for row in candidate],
                    ),
                    6,
                ),
            }
        )
        for item in baseline:
            new_rank = candidate_rank[item.event_id]
            all_movers.append(
                {
                    "day": day,
                    "event_id": item.event_id,
                    "relevant": item.relevant,
                    "baseline_rank": item.baseline_rank,
                    "candidate_rank": new_rank,
                    "rank_change": item.baseline_rank - new_rank,
                    "candidate_score": next(
                        row["candidate_score"]
                        for row in candidate
                        if row["event_id"] == item.event_id
                    ),
                    "score_components": item.score_components,
                }
            )
    mean = {
        key: round(sum(float(row[key]) for row in per_day) / len(per_day), 6)
        for key in (
            "precision_at_20",
            "precision_at_50",
            "precision_at_100",
            "kendall_tau",
        )
    }
    return {
        "formula": formula.payload(),
        "mean": mean,
        "per_day": per_day,
        "movers": all_movers,
    }


def _baseline_metrics(days: dict[str, list[LabeledEvent]]) -> dict[str, Any]:
    per_day = []
    for day, labels in sorted(days.items()):
        baseline = [
            {"relevant": item.relevant}
            for item in sorted(labels, key=lambda item: item.baseline_rank)
        ]
        per_day.append(
            {
                "day": day,
                "labeled_count": len(labels),
                "relevant_count": sum(item.relevant for item in labels),
                "precision_at_20": round(_precision(baseline, 20), 6),
                "precision_at_50": round(_precision(baseline, 50), 6),
                "precision_at_100": round(_precision(baseline, 100), 6),
            }
        )
    mean = {
        key: round(sum(float(row[key]) for row in per_day) / len(per_day), 6)
        for key in ("precision_at_20", "precision_at_50", "precision_at_100")
    }
    return {"formula": ATTENTION_V1_1.payload(), "mean": mean, "per_day": per_day}


def candidate_grid() -> list[AttentionFormula]:
    return [
        AttentionFormula(
            version=(
                f"attention-v2-candidate-a{cap}-s{knee}-"
                f"w{int(network * 100)}-{int(support * 100)}-{int(engagement * 100)}"
            ),
            network_attention_weight=network,
            originator_support_weight=support,
            public_engagement_weight=engagement,
            amplifier_cap=cap,
            support_knee=knee,
        )
        for cap in GRID_AMPLIFIER_CAPS
        for knee in GRID_SUPPORT_KNEES
        for network, support, engagement in GRID_WEIGHTS
    ]


def evaluation_payload(
    *,
    routing_root: Path = routing_runs.DEFAULT_RUN_ROOT,
    from_day: str | None = None,
    through: str | None = None,
    top_movers: int = DEFAULT_TOP_MOVERS,
) -> dict[str, Any]:
    if top_movers < 1:
        raise ValueError("top_movers must be positive")
    days = load_labeled_days(
        routing_root=routing_root, from_day=from_day, through=through
    )
    baseline = _baseline_metrics(days)
    evaluated = [evaluate_formula(days, formula) for formula in candidate_grid()]
    evaluated.sort(
        key=lambda result: (
            result["mean"]["precision_at_20"],
            result["mean"]["precision_at_50"],
            result["mean"]["kendall_tau"],
        ),
        reverse=True,
    )
    initial = evaluate_formula(days, ATTENTION_V2_CANDIDATE)
    best = evaluated[0]
    biggest = sorted(
        best.pop("movers"), key=lambda row: abs(row["rank_change"]), reverse=True
    )[:top_movers]
    for result in evaluated[1:]:
        result.pop("movers")
    initial.pop("movers")
    return {
        "routing_root": str(routing_root),
        "days": sorted(days),
        "labeled_count": sum(len(rows) for rows in days.values()),
        "label_source": "audience-routing-v9 ai_engineering OR investment",
        "baseline": baseline,
        "initial_candidate": initial,
        "best_candidate": {**best, "largest_movers": biggest},
        "grid": evaluated,
        "limitations": [
            "Labels are model judgments, not human ground truth.",
            "The labeled cohort is censored to the current top 100 per day.",
            "Precision@100 is invariant because every labeled row remains selected.",
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
    parser = argparse.ArgumentParser(prog="fli attention-score")
    sub = parser.add_subparsers(dest="action", required=True)
    evaluate = sub.add_parser(
        "evaluate", help="Replay attention-v1.1 and the v2 candidate grid."
    )
    evaluate.add_argument(
        "--routing-root", type=Path, default=routing_runs.DEFAULT_RUN_ROOT
    )
    evaluate.add_argument("--from-day")
    evaluate.add_argument("--through")
    evaluate.add_argument("--top-movers", type=int, default=DEFAULT_TOP_MOVERS)
    evaluate.add_argument("--json", action="store_true")
    evaluate.add_argument("--plain", action="store_true")
    evaluate.add_argument("--no-input", action="store_true")
    return parser


def _plain(payload: dict[str, Any]) -> str:
    if payload["status"] == "error":
        return f"{payload['error']['code']}: {payload['error']['message']}"
    data = payload["data"]
    baseline = data["baseline"]["mean"]
    best = data["best_candidate"]
    return (
        f"{data['labeled_count']} labels across {len(data['days'])} days\n"
        f"v1.1 P@20 {baseline['precision_at_20']:.3f} · "
        f"P@50 {baseline['precision_at_50']:.3f}\n"
        f"best {best['formula']['version']} · "
        f"P@20 {best['mean']['precision_at_20']:.3f} · "
        f"P@50 {best['mean']['precision_at_50']:.3f} · "
        f"tau {best['mean']['kendall_tau']:.3f}"
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    started = time.monotonic()
    request_id = str(uuid4())
    command = f"attention-score.{args.action}"
    try:
        data = evaluation_payload(
            routing_root=args.routing_root,
            from_day=args.from_day,
            through=args.through,
            top_movers=args.top_movers,
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
                "hint": "Verify the routing root and current Event publication.",
            },
            request_id=request_id,
            started=started,
        )
        exit_code = 2
    print(_plain(payload) if args.plain else _canonical_json(payload))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
