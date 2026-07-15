"""Machine-first CLI for repeated single-envelope Insight calibration."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
import time
from typing import Any, Callable
from uuid import uuid4

from openai import APIConnectionError, APITimeoutError, AuthenticationError

from fli import (
    audience_routing,
    audience_routing_runs,
    entity_kinds,
    insight_generation,
)


CLI_SCHEMA_VERSION = "1.0"
DEFAULT_MODEL = "gpt-5.6-terra"
DEFAULT_EFFORT = "high"
DEFAULT_TIMEOUT_SECONDS = 180.0
DEFAULT_DUMP_ROOT = audience_routing_runs.REPO_ROOT / "tmp" / "insight-spikes"
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
        return path.resolve().relative_to(audience_routing_runs.REPO_ROOT).as_posix()
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
) -> dict[str, Any]:
    return {
        "schema_version": CLI_SCHEMA_VERSION,
        "command": command,
        "status": "error",
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "hint": hint,
        },
        "meta": _meta(request_id=request_id, started=started),
    }


def contract_payload(audience: str = AUDIENCE_ALL) -> dict[str, Any]:
    selected = (
        tuple(insight_generation.InsightAudience)
        if audience == AUDIENCE_ALL
        else (insight_generation.require_audience(audience),)
    )
    return {
        "schema_version": insight_generation.SCHEMA_VERSION,
        "output_format": insight_generation.OUTPUT_FORMAT,
        "model_view": "root_same_author_continuations_and_artifacts_only",
        "prompts": [
            {
                "audience": value.value,
                "version": insight_generation.contract(value).version,
                "sha256": insight_generation.contract(value).sha256,
                "cache_key": insight_generation.contract(value).cache_key,
                "instruction_tokens": audience_routing.input_token_count(
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


def resolve_envelope(
    *,
    event_id: str,
    day: str | None,
    routing_root: Path,
) -> dict[str, Any]:
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
        if (
            meta is None
            or row is None
            or str(meta["prompt_version"]) != audience_routing.PROMPT_VERSION
            or str(row["status"]) != "complete"
            or (day is not None and str(meta["day"]) != day)
        ):
            continue
        matches.append({"path": path, "meta": dict(meta), "row": dict(row)})
    if not matches:
        suffix = f" on {day}" if day else ""
        raise ValueError(f"no completed current routing envelope found for {event_id}{suffix}")
    selected = max(
        matches,
        key=lambda value: (
            str(value["meta"]["day"]),
            str(value["meta"]["updated_at"]),
            str(value["meta"]["run_id"]),
        ),
    )
    selected["packet"] = audience_routing_runs._packet_from_payload(
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
            f"envelope is not positively routed for requested audience {requested!r}"
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
    routing_root: Path,
    dump_dir: Path,
    dry_run: bool,
    timeout_seconds: float,
    progress: str,
    client_factory: Callable[[], Any] = entity_kinds.create_litellm_client,
) -> dict[str, Any]:
    resolved = resolve_envelope(
        event_id=event_id,
        day=day,
        routing_root=routing_root,
    )
    row = resolved["row"]
    packet = resolved["packet"]
    audiences = _selected_audiences(row, audience)
    dump_dir.mkdir(parents=True, exist_ok=True)
    request_paths: dict[str, str] = {}
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

    base = {
        "run_id": run_id,
        "dry_run": dry_run,
        "will_call_model": not dry_run,
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

    client = client_factory()
    if hasattr(client, "with_options"):
        client = client.with_options(max_retries=0, timeout=timeout_seconds)
    evaluations = []
    for value in audiences:
        if progress == "plain":
            print(
                f"insight-spike: evaluating {value.value} with {model}",
                file=sys.stderr,
                flush=True,
            )
        evaluation = insight_generation.evaluate(
            client,
            candidates[value.value],
            model=model,
            effort=effort,
            run=run_id,
        )
        evaluations.append(evaluation)
        _write_json(dump_dir / f"{value.value}-result.json", evaluation)
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
    }
    result = {**base, "evaluations": evaluations, "telemetry": telemetry}
    _write_json(dump_dir / "result.json", result)
    return result


def _add_output_flags(parser: argparse.ArgumentParser) -> None:
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true", help="Emit stable JSON (default).")
    mode.add_argument("--plain", action="store_true", help="Emit a compact inspection view.")
    parser.add_argument("--no-input", action="store_true", help="Never prompt (always honored).")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fli insight-spike",
        description="Inspect or run one successor Insight envelope without a run store.",
    )
    sub = parser.add_subparsers(dest="action", required=True)
    contract = sub.add_parser("contract", help="Inspect prompts and output schema.")
    contract.add_argument("--audience", choices=AUDIENCE_CHOICES, default=AUDIENCE_ALL)
    _add_output_flags(contract)
    run = sub.add_parser("run", help="Evaluate one positively routed envelope.")
    run.add_argument("--event-id", required=True)
    run.add_argument("--day")
    run.add_argument("--audience", choices=AUDIENCE_CHOICES, default=AUDIENCE_ALL)
    run.add_argument("--model", default=DEFAULT_MODEL)
    run.add_argument("--reasoning-effort", default=DEFAULT_EFFORT)
    run.add_argument("--run-id")
    run.add_argument(
        "--routing-root", type=Path, default=audience_routing_runs.DEFAULT_RUN_ROOT
    )
    run.add_argument("--dump-dir", type=Path)
    run.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    run.add_argument("--progress", choices=("off", "plain"), default="plain")
    run.add_argument("--dry-run", action="store_true")
    _add_output_flags(run)
    return parser


def _plain(payload: dict[str, Any]) -> str:
    if payload["status"] == "error":
        return f"{payload['error']['code']}: {payload['error']['message']}"
    data = payload["data"]
    if payload["command"] == "insight-spike.contract":
        return _canonical_json(data, pretty=True)
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
    command = f"insight-spike.{args.action}"
    exit_code = 0
    try:
        if args.action == "contract":
            data = contract_payload(args.audience)
        else:
            if args.timeout <= 0:
                raise ValueError("timeout must be positive")
            timestamp = _now().strftime("%Y%m%dT%H%M%SZ")
            run_id = args.run_id or f"insight-spike-{args.event_id[:8]}-{timestamp}"
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
    except (AuthenticationError, RuntimeError) as exc:
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
