"""Machine-first CLI for durable, repeated single-Event Insight runs."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import time
from typing import Any, Callable
from uuid import uuid4

from openai import APIConnectionError, APITimeoutError, AuthenticationError

from fli import llm_responses
from fli.evidence import feed as signal_feed
from fli.insights import generation as insight_generation
from fli.insights import runs as insight_runs
from fli.registry import classification as entity_kinds
from fli.routing import model as routing_model
from fli.routing import runs as routing_run_store
from fli.routing import view as routing_view
from fli.scoring import development_attention


CLI_SCHEMA_VERSION = "1.0"
DEFAULT_MODEL = "gpt-5.6-terra"
DEFAULT_EFFORT = "high"
DEFAULT_TIMEOUT_SECONDS = 180.0
DEFAULT_DUMP_ROOT = routing_run_store.REPO_ROOT / "tmp" / "insight-runs"
DEFAULT_REFRESH_DAYS = 1
DEFAULT_REFRESH_LIMIT_PER_DAY = 10
DEFAULT_REFRESH_WORKERS = 8
AUDIENCE_ALL = "all"
AUDIENCE_CHOICES = (
    AUDIENCE_ALL,
    *(value.value for value in insight_generation.InsightAudience),
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _canonical_json(value: Any, *, pretty: bool = False) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2 if pretty else None,
        sort_keys=True,
        separators=None if pretty else (",", ":"),
    )


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(routing_run_store.REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _meta(*, request_id: str, started: float) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "timestamp_utc": _now().isoformat(),
    }


def _success(
    command: str, data: dict[str, Any], *, request_id: str, started: float
) -> dict[str, Any]:
    return {
        "schema_version": CLI_SCHEMA_VERSION,
        "command": command,
        "status": "ok",
        "data": data,
        "error": None,
        "meta": _meta(request_id=request_id, started=started),
    }


def _error(
    command: str,
    *,
    code: str,
    message: str,
    retryable: bool,
    hint: str,
    request_id: str,
    started: float,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": CLI_SCHEMA_VERSION,
        "command": command,
        "status": "error",
        "data": data,
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "hint": hint,
        },
        "meta": _meta(request_id=request_id, started=started),
    }


class InsightRefreshIncomplete(RuntimeError):
    """A batch finished its independent work but one or more requests failed."""

    def __init__(self, result: dict[str, Any]):
        super().__init__("Insight refresh completed with failed requests.")
        self.result = result


def contract_payload(audience: str = AUDIENCE_ALL) -> dict[str, Any]:
    selected = (
        tuple(insight_generation.InsightAudience)
        if audience == AUDIENCE_ALL
        else (insight_generation.require_audience(audience),)
    )
    return {
        "schema_version": insight_generation.SCHEMA_VERSION,
        "output_formats": {
            value.value: insight_generation.output_format(value)
            for value in selected
        },
        "model_view": "first_party_authored_posts_and_artifacts_only",
        "prompts": [
            {
                "audience": value.value,
                "version": insight_generation.contract(value).version,
                "sha256": insight_generation.contract(value).sha256,
                "cache_key": insight_generation.contract(value).cache_key,
                "instruction_tokens": routing_model.input_token_count(
                    insight_generation.contract(value).instructions()
                ),
                "path": _display_path(insight_generation.contract(value).path),
            }
            for value in selected
        ],
    }


def _open_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _enrich_post_dates(
    packet: routing_model.RoutingPacket,
    *,
    feed_run_id: str,
    feed_db: Path = signal_feed.DEFAULT_FEED_DB,
) -> routing_model.RoutingPacket:
    """Add Insight-only post dates without mutating the frozen route packet."""
    source_ids = sorted(
        {
            source.source_id
            for source in packet.sources
            if source.source_type == "x_post" and not source.posted
        }
    )
    if not source_ids or not feed_db.is_file():
        return packet
    placeholders = ",".join("?" for _ in source_ids)
    try:
        conn = _open_readonly(feed_db)
        try:
            rows = conn.execute(
                f"""SELECT post_id, published_at FROM feed_post
                    WHERE run_id = ? AND post_id IN ({placeholders})""",
                (feed_run_id, *source_ids),
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return packet
    posted_by_id = {
        str(row["post_id"]): str(row["published_at"])[:10]
        for row in rows
        if row["published_at"]
    }
    if not posted_by_id:
        return packet
    return routing_model.RoutingPacket(
        event_id=packet.event_id,
        day=packet.day,
        sources=tuple(
            replace(
                source,
                posted=source.posted or posted_by_id.get(source.source_id),
            )
            for source in packet.sources
        ),
    )


def resolve_event(
    *,
    event_id: str,
    day: str | None,
    routing_root: Path,
    source_routing_run_id: str | None = None,
) -> dict[str, Any]:
    from fli.web import developments as development_store

    identities: dict[str, dict[str, str]] = {}
    matches: list[dict[str, Any]] = []
    for path in sorted(routing_root.glob("*/routing.db")):
        try:
            conn = _open_readonly(path)
            meta = conn.execute(
                "SELECT * FROM run_meta WHERE singleton = 1"
            ).fetchone()
            row = conn.execute(
                "SELECT * FROM routing_item WHERE event_id = ?", (event_id,)
            ).fetchone()
            conn.close()
        except sqlite3.Error:
            continue
        route_day = str(meta["day"]) if meta is not None else ""
        try:
            identity = identities.setdefault(
                route_day,
                development_store.current_rank_identity(day=route_day),
            )
        except ValueError:
            continue
        if (
            meta is None
            or row is None
            or dict(meta).get("rank_version")
            != development_attention.DAILY_RANK_VERSION
            or dict(meta).get("source_rank_input_sha256")
            != identity["rank_input_sha256"]
            or str(meta["source_event_run_id"]) != identity["event_run_id"]
            or str(meta["source_feed_run_id"]) != identity["feed_run_id"]
            or str(meta["prompt_version"]) != routing_model.PROMPT_VERSION
            or str(row["status"]) != "complete"
            or (day is not None and str(meta["day"]) != day)
            or (
                source_routing_run_id is not None
                and str(meta["run_id"]) != source_routing_run_id
            )
        ):
            continue
        matches.append({"path": path, "meta": dict(meta), "row": dict(row)})
    if not matches:
        suffix = f" on {day}" if day else ""
        raise ValueError(f"no completed current routed Event found for {event_id}{suffix}")
    selected = min(
        matches,
        key=lambda value: (
            str(value["meta"]["day"]),
            -datetime.fromisoformat(str(value["meta"]["updated_at"])).timestamp(),
            str(value["meta"]["run_id"]),
        ),
    )
    selected["packet"] = routing_run_store._packet_from_payload(
        json.loads(str(selected["row"]["packet_json"]))
    )
    return selected


def _selected_audiences(
    row: dict[str, Any], requested: str
) -> tuple[insight_generation.InsightAudience, ...]:
    candidates = (
        tuple(insight_generation.InsightAudience)
        if requested == AUDIENCE_ALL
        else (insight_generation.require_audience(requested),)
    )
    selected = tuple(
        audience
        for audience in candidates
        if int(row[f"{audience.value}_relevant"] or 0) == 1
    )
    if not selected:
        raise ValueError(
            f"Event is not positively routed for requested audience {requested!r}"
        )
    return selected


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical_json(payload, pretty=True) + "\n", encoding="utf-8")


def run_spike(
    *,
    event_id: str,
    day: str | None,
    audience: str,
    model: str,
    effort: str,
    run_id: str,
    db_path: Path,
    routing_root: Path,
    dump_dir: Path,
    dry_run: bool,
    timeout_seconds: float,
    progress: str,
    source_routing_run_id: str | None = None,
    prepare_only: bool = False,
    client_factory: Callable[[], Any] = entity_kinds.create_litellm_client,
) -> dict[str, Any]:
    resolved = resolve_event(
        event_id=event_id,
        day=day,
        routing_root=routing_root,
        source_routing_run_id=source_routing_run_id,
    )
    row = resolved["row"]
    packet = _enrich_post_dates(
        resolved["packet"],
        feed_run_id=str(resolved["meta"]["source_feed_run_id"]),
    )
    audiences = _selected_audiences(row, audience)
    dump_dir.mkdir(parents=True, exist_ok=True)
    request_paths: dict[str, str] = {}
    requests: dict[str, dict[str, Any]] = {}
    candidates: dict[str, insight_generation.InsightCandidate] = {}
    for value in audiences:
        candidate = insight_generation.InsightCandidate.create(
            audience=value,
            packet=packet,
            feed_rank=int(row["feed_rank"]),
        )
        candidates[value.value] = candidate
        request = insight_generation.build_request(
            candidate,
            model=model,
            effort=effort,
            run=run_id,
        )
        request_path = dump_dir / f"{value.value}-request.json"
        _write_json(request_path, request)
        request_paths[value.value] = _display_path(request_path)
        requests[value.value] = request

    base = {
        "run_id": run_id,
        "db": _display_path(db_path),
        "dry_run": dry_run,
        "prepare_only": prepare_only,
        "will_call_model": not dry_run and not prepare_only,
        "event_id": event_id,
        "day": packet.day,
        "feed_rank": int(row["feed_rank"]),
        "source_routing_run_id": str(resolved["meta"]["run_id"]),
        "source_routing_db": _display_path(resolved["path"]),
        "model": model,
        "reasoning_effort": effort,
        "timeout_seconds": timeout_seconds,
        "audiences": [value.value for value in audiences],
        "contract": contract_payload(audience),
        "dump_dir": _display_path(dump_dir),
        "request_files": request_paths,
    }
    if dry_run:
        _write_json(dump_dir / "result.json", {**base, "evaluations": []})
        return {**base, "evaluations": [], "telemetry": None}

    conn = insight_runs.connect(db_path)
    try:
        insight_runs.prepare_run(
            conn,
            run_id=run_id,
            event_id=event_id,
            day=packet.day,
            feed_rank=int(row["feed_rank"]),
            source_routing_run_id=str(resolved["meta"]["run_id"]),
            source_routing_db=_display_path(resolved["path"]),
            model=model,
            reasoning_effort=effort,
            items=(
                {
                    "audience": value.value,
                    "candidate_id": candidates[value.value].candidate_id,
                    "request": requests[value.value],
                }
                for value in audiences
            ),
        )
        if prepare_only:
            prepared = {
                **base,
                "evaluations": [],
                "telemetry": None,
                "store": insight_runs.run_payload(conn, run_id),
            }
            _write_json(dump_dir / "result.json", prepared)
            return prepared
        client = None
        evaluations = []
        model_requested_audiences: set[str] = set()
        for value in audiences:
            evaluation = insight_runs.completed_evaluation(
                conn, run_id=run_id, audience=value.value
            )
            if evaluation is None:
                if client is None:
                    client = client_factory()
                    if hasattr(client, "with_options"):
                        client = client.with_options(
                            max_retries=0, timeout=timeout_seconds
                        )
                if progress == "plain":
                    print(
                        f"insights: evaluating {value.value} with {model}",
                        file=sys.stderr,
                        flush=True,
                    )
                try:
                    model_requested_audiences.add(value.value)
                    evaluation = insight_generation.evaluate(
                        client,
                        candidates[value.value],
                        model=model,
                        effort=effort,
                        run=run_id,
                    )
                    insight_runs.complete_item(
                        conn, run_id=run_id, evaluation=evaluation
                    )
                except Exception as error:
                    insight_runs.fail_item(
                        conn,
                        run_id=run_id,
                        audience=value.value,
                        error=error,
                    )
                    raise
            elif progress == "plain":
                print(
                    f"insights: reusing completed {value.value} result from {run_id}",
                    file=sys.stderr,
                    flush=True,
                )
            evaluations.append(evaluation)
            _write_json(dump_dir / f"{value.value}-result.json", evaluation)
        stored_run = insight_runs.run_payload(conn, run_id)
    finally:
        conn.close()
    telemetry = {
        "input_tokens": sum(value["input_tokens"] for value in evaluations),
        "cached_tokens": sum(value["cached_tokens"] for value in evaluations),
        "cache_write_tokens": sum(
            value["cache_write_tokens"] for value in evaluations
        ),
        "output_tokens": sum(value["output_tokens"] for value in evaluations),
        "reported_cost_usd": round(
            sum(float(value["reported_cost_usd"] or 0) for value in evaluations),
            8,
        ),
        "cache_hit_requests": sum(
            value["cached_tokens"] > 0 for value in evaluations
        ),
        "request_count": len(evaluations),
        "model_requests": len(model_requested_audiences),
        "reused_results": len(evaluations) - len(model_requested_audiences),
        "incremental_input_tokens": sum(
            value["input_tokens"]
            for value in evaluations
            if value["audience"] in model_requested_audiences
        ),
        "incremental_cached_tokens": sum(
            value["cached_tokens"]
            for value in evaluations
            if value["audience"] in model_requested_audiences
        ),
        "incremental_output_tokens": sum(
            value["output_tokens"]
            for value in evaluations
            if value["audience"] in model_requested_audiences
        ),
        "incremental_reported_cost_usd": round(
            sum(
                float(value["reported_cost_usd"] or 0)
                for value in evaluations
                if value["audience"] in model_requested_audiences
            ),
            8,
        ),
    }
    result = {
        **base,
        "evaluations": evaluations,
        "telemetry": telemetry,
        "store": stored_run,
    }
    _write_json(dump_dir / "result.json", result)
    return result


def _refresh_days(through: str, days: int) -> list[str]:
    if days < 1 or days > 90:
        raise ValueError("days must be between 1 and 90")
    end = date.fromisoformat(through)
    start = end - timedelta(days=days - 1)
    return [(start + timedelta(days=offset)).isoformat() for offset in range(days)]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _stable_run_id(
    *,
    event_id: str,
    audience: insight_generation.InsightAudience,
    source_routing_run_id: str,
    model: str,
    effort: str,
) -> str:
    prompt = insight_generation.contract(audience)
    identity = _canonical_json(
        {
            "event_id": event_id,
            "audience": audience.value,
            "source_routing_run_id": source_routing_run_id,
            "model": model,
            "reasoning_effort": effort,
            "prompt_version": prompt.version,
            "prompt_sha256": prompt.sha256,
            "schema_version": insight_generation.SCHEMA_VERSION,
        }
    )
    digest = hashlib.sha256(identity.encode()).hexdigest()[:12]
    audience_label = (
        "eng"
        if audience is insight_generation.InsightAudience.AI_ENGINEERING
        else "inv"
    )
    return (
        f"insight-{_slug(prompt.version)}-{audience_label}-"
        f"{event_id[:8]}-{digest}"
    )


def _current_routing_runs(
    *,
    days: list[str],
    routing_root: Path,
) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    from fli.web import developments as development_store

    source = routing_run_store._published_event_source()
    selected: dict[str, dict[str, Any]] = {}
    for day in days:
        identity = development_store.current_rank_identity(day=day)
        path = routing_view.latest_complete_run(
            day,
            expected_rank_input_sha256=identity["rank_input_sha256"],
            expected_event_run_id=identity["event_run_id"],
            expected_feed_run_id=identity["feed_run_id"],
            root=routing_root,
        )
        if path is None:
            raise ValueError(
                f"no complete current routing run found for {day}; "
                "rerun audience routing first"
            )
        conn = _open_readonly(path)
        try:
            meta_row = conn.execute(
                "SELECT * FROM run_meta WHERE singleton = 1"
            ).fetchone()
        finally:
            conn.close()
        if meta_row is None:
            raise ValueError(f"routing metadata is missing for {day}")
        selected[day] = {"path": path, "meta": dict(meta_row)}
    return source, selected


def plan_refresh(
    *,
    through: str,
    days: int,
    limit_per_day: int | None,
    audience: str,
    model: str,
    effort: str,
    routing_root: Path,
) -> dict[str, Any]:
    if limit_per_day is not None and limit_per_day < 1:
        raise ValueError("limit_per_day must be positive")
    selected_days = _refresh_days(through, days)
    source, routing_runs = _current_routing_runs(
        days=selected_days,
        routing_root=routing_root,
    )
    requested_audiences = (
        tuple(insight_generation.InsightAudience)
        if audience == AUDIENCE_ALL
        else (insight_generation.require_audience(audience),)
    )
    requests: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    seen_events: dict[str, str] = {}
    sources: list[dict[str, Any]] = []
    for day in selected_days:
        route = routing_runs[day]
        meta = route["meta"]
        conn = _open_readonly(route["path"])
        try:
            rows = conn.execute(
                """SELECT event_id, feed_rank,
                          ai_engineering_relevant, investment_relevant
                   FROM routing_item
                   WHERE status = 'complete'
                     AND (ai_engineering_relevant = 1 OR investment_relevant = 1)
                   ORDER BY feed_rank, event_id"""
            ).fetchall()
        finally:
            conn.close()
        chosen: list[tuple[sqlite3.Row, list[insight_generation.InsightAudience]]] = []
        for row in rows:
            relevant = [
                value
                for value in requested_audiences
                if int(row[f"{value.value}_relevant"] or 0) == 1
            ]
            if not relevant:
                continue
            chosen.append((row, relevant))
            if limit_per_day is not None and len(chosen) >= limit_per_day:
                break
        for row, relevant in chosen:
            event_id = str(row["event_id"])
            previous_day = seen_events.get(event_id)
            if previous_day is not None and previous_day != day:
                raise ValueError(
                    f"Event {event_id} appears on both {previous_day} and {day}; "
                    "repair canonical Event publication before generating Insights"
                )
            seen_events[event_id] = day
            event_requests = []
            for value in relevant:
                run_id = _stable_run_id(
                    event_id=event_id,
                    audience=value,
                    source_routing_run_id=str(meta["run_id"]),
                    model=model,
                    effort=effort,
                )
                request = {
                    "run_id": run_id,
                    "event_id": event_id,
                    "day": day,
                    "feed_rank": int(row["feed_rank"]),
                    "audience": value.value,
                    "source_routing_run_id": str(meta["run_id"]),
                    "source_routing_db": _display_path(route["path"]),
                }
                requests.append(request)
                event_requests.append({"audience": value.value, "run_id": run_id})
            events.append(
                {
                    "event_id": event_id,
                    "day": day,
                    "feed_rank": int(row["feed_rank"]),
                    "requests": event_requests,
                }
            )
        sources.append(
            {
                "day": day,
                "run_id": str(meta["run_id"]),
                "run_db": _display_path(route["path"]),
                "source_event_run_id": str(meta["source_event_run_id"]),
                "source_feed_run_id": str(meta["source_feed_run_id"]),
            }
        )

    cohort_payload = {
        "source_event_run_id": source["event_run_id"],
        "source_feed_run_id": source["feed_run_id"],
        "through": through,
        "days": days,
        "limit_per_day": limit_per_day,
        "audience": audience,
        "model": model,
        "reasoning_effort": effort,
        "requests": requests,
    }
    cohort_sha256 = hashlib.sha256(
        _canonical_json(cohort_payload).encode()
    ).hexdigest()
    return {
        **cohort_payload,
        "refresh_id": f"insight-refresh-{cohort_sha256[:16]}",
        "cohort_sha256": cohort_sha256,
        "routing_runs": sources,
        "event_count": len(events),
        "request_count": len(requests),
        "events": events,
    }


def refresh_insights(
    *,
    through: str,
    days: int = DEFAULT_REFRESH_DAYS,
    limit_per_day: int | None = DEFAULT_REFRESH_LIMIT_PER_DAY,
    audience: str = AUDIENCE_ALL,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_EFFORT,
    workers: int = DEFAULT_REFRESH_WORKERS,
    db_path: Path = insight_runs.DEFAULT_DB,
    routing_root: Path = routing_run_store.DEFAULT_RUN_ROOT,
    dump_root: Path = DEFAULT_DUMP_ROOT / "refreshes",
    dry_run: bool = False,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    progress: str = "plain",
    client_factory: Callable[[], Any] = entity_kinds.create_litellm_client,
) -> dict[str, Any]:
    if workers < 1 or workers > 64:
        raise ValueError("workers must be between 1 and 64")
    if timeout_seconds <= 0:
        raise ValueError("timeout must be positive")
    plan = plan_refresh(
        through=through,
        days=days,
        limit_per_day=limit_per_day,
        audience=audience,
        model=model,
        effort=effort,
        routing_root=routing_root,
    )
    cache_lanes = llm_responses.group_prompt_cache_lanes(
        plan["requests"],
        lambda item: insight_generation.contract(
            str(item["audience"])
        ).cache_key,
    )
    base = {
        **plan,
        "db": _display_path(db_path),
        "requested_workers": workers,
        "workers": min(workers, max(len(cache_lanes), 1)),
        "cache_lanes": len(cache_lanes),
        "cache_execution": "serial_per_key",
        "timeout_seconds": timeout_seconds,
        "dry_run": dry_run,
        "will_call_model": False if dry_run else None,
    }
    if dry_run:
        return {**base, "results": [], "errors": [], "telemetry": None}

    current_source = routing_run_store._published_event_source()
    if current_source != {
        "event_run_id": plan["source_event_run_id"],
        "feed_run_id": plan["source_feed_run_id"],
    }:
        raise RuntimeError(
            "The published Event run changed after the Insight cohort was "
            "planned; retry."
        )

    refresh_dir = dump_root / str(plan["refresh_id"])
    refresh_dir.mkdir(parents=True, exist_ok=True)
    _write_json(refresh_dir / "plan.json", plan)
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    # Freeze every exact request before any model work starts. This turns a
    # cohort into an auditable immutable unit and makes publication drift fail
    # before spend rather than halfway through execution.
    for item in plan["requests"]:
        run_spike(
            event_id=str(item["event_id"]),
            day=str(item["day"]),
            audience=str(item["audience"]),
            model=model,
            effort=effort,
            run_id=str(item["run_id"]),
            db_path=db_path,
            routing_root=routing_root,
            dump_dir=refresh_dir / str(item["run_id"]),
            dry_run=False,
            timeout_seconds=timeout_seconds,
            progress="off",
            source_routing_run_id=str(item["source_routing_run_id"]),
            prepare_only=True,
            client_factory=client_factory,
        )

    if routing_run_store._published_event_source() != current_source:
        raise RuntimeError(
            "The published Event run changed while Insight requests were "
            "frozen; no model calls were started. Retry."
        )

    def execute(item: dict[str, Any]) -> dict[str, Any]:
        return run_spike(
            event_id=str(item["event_id"]),
            day=str(item["day"]),
            audience=str(item["audience"]),
            model=model,
            effort=effort,
            run_id=str(item["run_id"]),
            db_path=db_path,
            routing_root=routing_root,
            dump_dir=refresh_dir / str(item["run_id"]),
            dry_run=False,
            timeout_seconds=timeout_seconds,
            progress="off",
            source_routing_run_id=str(item["source_routing_run_id"]),
            prepare_only=False,
            client_factory=client_factory,
        )

    def execute_lane(
        lane: list[dict[str, Any]],
    ) -> list[tuple[dict[str, Any], dict[str, Any] | None, Exception | None]]:
        outcomes = []
        for item in lane:
            try:
                outcomes.append((item, execute(item), None))
            except Exception as error:
                outcomes.append((item, None, error))
        return outcomes

    if cache_lanes:
        with ThreadPoolExecutor(max_workers=base["workers"]) as executor:
            futures = [
                executor.submit(execute_lane, lane)
                for lane in cache_lanes.values()
            ]
            for future in as_completed(futures):
                for item, completed, error in future.result():
                    if completed is not None:
                        evaluation = completed["evaluations"][0]
                        result = evaluation["result"]
                        results.append(
                            {
                                **item,
                                "decision": result["decision"],
                                "title": result["title"],
                                "model_requests": completed["telemetry"][
                                    "model_requests"
                                ],
                                "reused_results": completed["telemetry"][
                                    "reused_results"
                                ],
                                "input_tokens": completed["telemetry"][
                                    "incremental_input_tokens"
                                ],
                                "cached_tokens": completed["telemetry"][
                                    "incremental_cached_tokens"
                                ],
                                "output_tokens": completed["telemetry"][
                                    "incremental_output_tokens"
                                ],
                                "reported_cost_usd": completed["telemetry"][
                                    "incremental_reported_cost_usd"
                                ],
                            }
                        )
                        if progress == "plain":
                            print(
                                "insights: "
                                f"{len(results) + len(errors)}/"
                                f"{plan['request_count']} "
                                f"{item['day']} rank {item['feed_rank']} "
                                f"{item['audience']} complete",
                                file=sys.stderr,
                                flush=True,
                            )
                        continue
                    assert error is not None
                    errors.append(
                        {
                            **item,
                            "error_type": type(error).__name__,
                            "error_message": str(error),
                        }
                    )
                    if progress == "plain":
                        print(
                            "insights: "
                            f"{len(results) + len(errors)}/"
                            f"{plan['request_count']} "
                            f"{item['day']} rank {item['feed_rank']} "
                            f"{item['audience']} failed",
                            file=sys.stderr,
                            flush=True,
                        )

    results.sort(key=lambda item: (item["day"], item["feed_rank"], item["audience"]))
    errors.sort(key=lambda item: (item["day"], item["feed_rank"], item["audience"]))
    telemetry = {
        "model_requests": sum(int(item["model_requests"]) for item in results),
        "reused_results": sum(int(item["reused_results"]) for item in results),
        "input_tokens": sum(int(item["input_tokens"]) for item in results),
        "cached_tokens": sum(int(item["cached_tokens"]) for item in results),
        "output_tokens": sum(int(item["output_tokens"]) for item in results),
        "reported_cost_usd": round(
            sum(float(item["reported_cost_usd"] or 0) for item in results), 8
        ),
    }
    result = {
        **base,
        "will_call_model": telemetry["model_requests"] > 0,
        "counts": {
            "requests": plan["request_count"],
            "complete": len(results),
            "failed": len(errors),
            "surfaced": sum(item["decision"] == "surface" for item in results),
            "suppressed": sum(item["decision"] == "suppress" for item in results),
        },
        "results": results,
        "errors": errors,
        "telemetry": telemetry,
        "dump_dir": _display_path(refresh_dir),
    }
    _write_json(refresh_dir / "result.json", result)
    if errors:
        raise InsightRefreshIncomplete(result)
    return result


def _add_output_flags(parser: argparse.ArgumentParser) -> None:
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true", help="Emit stable JSON (default).")
    mode.add_argument("--plain", action="store_true", help="Emit a compact inspection view.")
    parser.add_argument("--no-input", action="store_true", help="Never prompt (always honored).")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fli insights",
        description="Inspect, run, resume, and audit successor Insight generation.",
    )
    sub = parser.add_subparsers(dest="action", required=True)
    contract = sub.add_parser("contract", help="Inspect prompts and output schema.")
    contract.add_argument("--audience", choices=AUDIENCE_CHOICES, default=AUDIENCE_ALL)
    _add_output_flags(contract)
    run = sub.add_parser("run", help="Evaluate one positively routed Event.")
    run.add_argument("--event-id", required=True)
    run.add_argument("--day")
    run.add_argument("--audience", choices=AUDIENCE_CHOICES, default=AUDIENCE_ALL)
    run.add_argument("--model", default=DEFAULT_MODEL)
    run.add_argument("--reasoning-effort", default=DEFAULT_EFFORT)
    run.add_argument("--run-id")
    run.add_argument("--db", type=Path, default=insight_runs.DEFAULT_DB)
    run.add_argument(
        "--routing-root", type=Path, default=routing_run_store.DEFAULT_RUN_ROOT
    )
    run.add_argument("--dump-dir", type=Path)
    run.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    run.add_argument("--progress", choices=("off", "plain"), default="plain")
    run.add_argument("--dry-run", action="store_true")
    _add_output_flags(run)
    refresh = sub.add_parser(
        "refresh",
        help="Generate a resumable batch from current positive audience routes.",
    )
    refresh.add_argument("--through", required=True)
    refresh.add_argument("--days", type=int, default=DEFAULT_REFRESH_DAYS)
    selection = refresh.add_mutually_exclusive_group()
    selection.add_argument(
        "--limit-per-day",
        type=int,
        default=DEFAULT_REFRESH_LIMIT_PER_DAY,
        help="Select this many positively routed Events per day (default: 10).",
    )
    selection.add_argument(
        "--all-routed",
        action="store_true",
        help="Select every positively routed Event in each requested day.",
    )
    refresh.add_argument(
        "--audience", choices=AUDIENCE_CHOICES, default=AUDIENCE_ALL
    )
    refresh.add_argument("--model", default=DEFAULT_MODEL)
    refresh.add_argument("--reasoning-effort", default=DEFAULT_EFFORT)
    refresh.add_argument("--workers", type=int, default=DEFAULT_REFRESH_WORKERS)
    refresh.add_argument("--db", type=Path, default=insight_runs.DEFAULT_DB)
    refresh.add_argument(
        "--routing-root", type=Path, default=routing_run_store.DEFAULT_RUN_ROOT
    )
    refresh.add_argument(
        "--dump-dir", type=Path, default=DEFAULT_DUMP_ROOT / "refreshes"
    )
    refresh.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    refresh.add_argument("--progress", choices=("off", "plain"), default="plain")
    refresh.add_argument("--dry-run", action="store_true")
    _add_output_flags(refresh)
    imported = sub.add_parser(
        "import-result", help="Persist an exact completed request dump without a model call."
    )
    imported.add_argument("--result-file", type=Path, required=True)
    imported.add_argument("--db", type=Path, default=insight_runs.DEFAULT_DB)
    _add_output_flags(imported)
    summary = sub.add_parser("summary", help="Inspect aggregate durable run state.")
    summary.add_argument("--db", type=Path, default=insight_runs.DEFAULT_DB)
    _add_output_flags(summary)
    inspect = sub.add_parser("inspect", help="Inspect one durable run.")
    inspect.add_argument("--run-id", required=True)
    inspect.add_argument("--db", type=Path, default=insight_runs.DEFAULT_DB)
    _add_output_flags(inspect)
    return parser


def _plain(payload: dict[str, Any]) -> str:
    if payload["status"] == "error":
        return f"{payload['error']['code']}: {payload['error']['message']}"
    data = payload["data"]
    if payload["command"] == "insights.contract":
        return _canonical_json(data, pretty=True)
    if payload["command"] in {
        "insights.summary",
        "insights.inspect",
        "insights.import-result",
    }:
        return _canonical_json(data, pretty=True)
    if payload["command"] == "insights.refresh":
        if payload["status"] == "error":
            return f"{payload['error']['code']}: {payload['error']['message']}"
        if data["dry_run"]:
            return (
                f"{data['refresh_id']} · {data['event_count']} Events · "
                f"{data['request_count']} requests · no model calls"
            )
        return (
            f"{data['refresh_id']} · {data['counts']['complete']}/"
            f"{data['counts']['requests']} complete · "
            f"{data['telemetry']['model_requests']} model requests · "
            f"${data['telemetry']['reported_cost_usd']:.6f}"
        )
    lines = [
        f"event {data['event_id']} · {data['day']} · Feed rank {data['feed_rank']}",
        f"model {data['model']} · dump {data['dump_dir']}",
    ]
    for evaluation in data["evaluations"]:
        result = evaluation["result"]
        lines.append(
            f"{evaluation['audience']}: {result['decision']} — "
            f"{result['suppression_reason'] or result['summary']}"
        )
    return "\n".join(lines)


def main(
    argv: list[str] | None = None,
    *,
    client_factory: Callable[[], Any] = entity_kinds.create_litellm_client,
) -> int:
    args = _parser().parse_args(argv)
    started = time.monotonic()
    request_id = str(uuid4())
    command = f"insights.{args.action}"
    exit_code = 0
    try:
        if args.action == "contract":
            data = contract_payload(args.audience)
        elif args.action in {"summary", "inspect", "import-result"}:
            if args.action in {"summary", "inspect"} and not args.db.is_file():
                raise FileNotFoundError(args.db)
            conn = insight_runs.connect(args.db)
            try:
                if args.action == "summary":
                    data = {
                        "db": _display_path(args.db),
                        **insight_runs.summary_payload(conn),
                    }
                elif args.action == "inspect":
                    data = {
                        "db": _display_path(args.db),
                        "run": insight_runs.run_payload(conn, args.run_id),
                    }
                else:
                    data = insight_runs.import_result_file(conn, args.result_file)
            finally:
                conn.close()
        elif args.action == "refresh":
            data = refresh_insights(
                through=args.through,
                days=args.days,
                limit_per_day=None if args.all_routed else args.limit_per_day,
                audience=args.audience,
                model=args.model,
                effort=args.reasoning_effort,
                workers=args.workers,
                db_path=args.db,
                routing_root=args.routing_root,
                dump_root=args.dump_dir,
                dry_run=args.dry_run,
                timeout_seconds=args.timeout,
                progress=args.progress,
                client_factory=client_factory,
            )
        else:
            if args.timeout <= 0:
                raise ValueError("timeout must be positive")
            timestamp = _now().strftime("%Y%m%dT%H%M%SZ")
            run_id = args.run_id or f"insight-{args.event_id[:8]}-{timestamp}"
            dump_dir = args.dump_dir or (
                DEFAULT_DUMP_ROOT
                / f"{args.event_id[:8]}-{args.day or 'latest'}-{args.model}-{timestamp}"
            )
            data = run_spike(
                event_id=args.event_id,
                day=args.day,
                audience=args.audience,
                model=args.model,
                effort=args.reasoning_effort,
                run_id=run_id,
                db_path=args.db,
                routing_root=args.routing_root,
                dump_dir=dump_dir,
                dry_run=args.dry_run,
                timeout_seconds=args.timeout,
                progress=args.progress,
                client_factory=client_factory,
            )
        payload = _success(
            command, data, request_id=request_id, started=started
        )
    except InsightRefreshIncomplete as exc:
        exit_code = 1
        payload = _error(
            command,
            code="E_PARTIAL_FAILURE",
            message=str(exc),
            retryable=True,
            hint=(
                "Rerun the identical command; completed requests are reused "
                "and failed requests retry."
            ),
            request_id=request_id,
            started=started,
            data=exc.result,
        )
    except KeyboardInterrupt:
        exit_code = 5
        payload = _error(
            command,
            code="E_INTERRUPTED",
            message="Insight spike was interrupted.",
            retryable=True,
            hint="Run the same command again; each spike uses a new dump directory.",
            request_id=request_id,
            started=started,
        )
    except (FileNotFoundError, sqlite3.Error, ValueError) as exc:
        exit_code = 2
        payload = _error(
            command,
            code="E_INVALID_INPUT",
            message=str(exc),
            retryable=False,
            hint="Check the event ID, optional day, audience route, and routing root.",
            request_id=request_id,
            started=started,
        )
    except AuthenticationError as exc:
        exit_code = 3
        payload = _error(
            command,
            code="E_AUTH",
            message=str(exc),
            retryable=False,
            hint="Repair the shared LiteLLM credential file and retry.",
            request_id=request_id,
            started=started,
        )
    except (APITimeoutError, TimeoutError) as exc:
        exit_code = 5
        payload = _error(
            command,
            code="E_TIMEOUT",
            message=str(exc),
            retryable=True,
            hint="Retry with a larger --timeout value.",
            request_id=request_id,
            started=started,
        )
    except APIConnectionError as exc:
        exit_code = 4
        payload = _error(
            command,
            code="E_DEPENDENCY_UNAVAILABLE",
            message=str(exc),
            retryable=True,
            hint="Check the shared LiteLLM endpoint and retry.",
            request_id=request_id,
            started=started,
        )
    except RuntimeError as exc:
        exit_code = 1
        payload = _error(
            command,
            code="E_EXECUTION",
            message=str(exc),
            retryable=True,
            hint=(
                "Retry the same command after the current Event and routing "
                "publication is stable."
            ),
            request_id=request_id,
            started=started,
        )
    except Exception as exc:
        exit_code = 1
        payload = _error(
            command,
            code="E_EXECUTION",
            message=str(exc),
            retryable=False,
            hint="Inspect the dumped request and retry after correcting the dependency.",
            request_id=request_id,
            started=started,
        )
    print(_plain(payload) if getattr(args, "plain", False) else _canonical_json(payload))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
