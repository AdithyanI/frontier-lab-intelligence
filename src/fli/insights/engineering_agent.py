"""Surface-linked AI Engineering analysis over ranked Developments.

One Development, one Responses call. The model decides whether a Development
changes anything for the team that builds and runs BIT's research platform,
and which of the seven Aion surfaces it lands on. There is no tool loop: the
surface map is small enough to send in full, so progressive disclosure buys
nothing here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import openai

from fli import llm_responses
from fli.insights import engineering_agent_runs
from fli.registry import classification as entity_kinds


REPO_ROOT = Path(__file__).resolve().parents[3]
SURFACE_PATH = engineering_agent_runs.SURFACE_PATH
DEFAULT_TRACE_ROOT = (
    REPO_ROOT / "data" / "derived" / "insights" / "engineering-agent-traces"
)
DEFAULT_API_BASE = "http://127.0.0.1:8797"
DEFAULT_DATE = "2026-07-21"
DEFAULT_RANK = 1
DEFAULT_MODEL = "gpt-5.6-sol"
DEFAULT_EFFORT = "high"
DEFAULT_TOP_RANKED = 10
DEFAULT_WORKERS = 9
MAX_RESPONSE_ATTEMPTS = 3
RETRYABLE_RESPONSE_STATUS_CODES = frozenset({408, 409, 429, 499})
PROMPT_VERSION = "engineering-agent-v1"
PROMPT_CACHE_KEY = "fli:engineering-agent:v1"
PROMPT_PATH = (
    REPO_ROOT
    / "src"
    / "fli"
    / "insights"
    / "prompts"
    / "engineering_surface_analysis.txt"
)


def _get_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def _engineering_candidates(
    *,
    day: str,
    limit: int,
    api_base: str,
) -> list[dict[str, Any]]:
    """Return the highest-ranked current AI Engineering-routed Developments."""
    url = (
        f"{api_base}/api/developments?"
        + urllib.parse.urlencode(
            {
                "date": day,
                "routing": "ai_engineering",
                "sort": "rank",
                "limit": limit,
                "include_evidence": "false",
            }
        )
    )
    payload = _get_json(url)
    if not payload.get("available"):
        raise RuntimeError(
            payload.get("reason")
            or f"The Development projection for {day} is unavailable."
        )
    items = list(payload.get("items") or [])
    for item in items:
        route = item.get("audience_routing") or {}
        engineering = route.get("ai_engineering") or {}
        if (
            item.get("routing_state") != "evaluated"
            or engineering.get("relevant") is not True
        ):
            raise RuntimeError(
                "The AI Engineering candidate endpoint returned a Development "
                "without a current positive AI Engineering route."
            )
    return items


def _surface_cards() -> list[dict[str, Any]]:
    """Return the Aion surface map exactly as the model will see it."""
    payload = json.loads(SURFACE_PATH.read_text(encoding="utf-8"))
    cards = [
        {
            "id": str(item["id"]),
            "name": str(item["name"]),
            "what": str(item["what"]),
            "scope": str(item["scope"]),
        }
        for item in payload["surfaces"]
    ]
    if len(cards) != int(payload["surface_count"]):
        raise RuntimeError("the Aion surface map repeats a surface id")
    return cards


def _instructions(cards: list[dict[str, Any]]) -> str:
    surfaces_json = json.dumps(cards, ensure_ascii=False, indent=2)
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace("{{AION_SURFACES_JSON}}", surfaces_json)


def _final_format(surface_ids: list[str]) -> dict[str, Any]:
    landing = {
        "type": "object",
        "properties": {
            "surface_id": {
                "type": "string",
                "enum": surface_ids,
                "description": "The Aion surface this Development lands on.",
            },
            "why": {
                "type": "string",
                "description": (
                    "One or two sentences naming what this Development does "
                    "to that surface for this reader. Specific enough that it "
                    "could not be moved to another surface unchanged."
                ),
            },
        },
        "required": ["surface_id", "why"],
        "additionalProperties": False,
    }
    return {
        "type": "json_schema",
        "name": "engineering_surface_analysis",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "headline": {
                    "type": "string",
                    "description": (
                        "One factual sentence naming what changed and who did "
                        "it, written for an engineer scanning a list."
                    ),
                },
                "what_changed": {
                    "type": "string",
                    "description": (
                        "Two or three sentences of exact technical substance "
                        "from the evidence, with attribution and conditions."
                    ),
                },
                "decision": {"type": "string", "enum": ["surface", "suppress"]},
                "lands": {
                    "type": "array",
                    "maxItems": engineering_agent_runs.MAX_LANDINGS,
                    "items": landing,
                    "description": (
                        "Surfaces this Development lands on, ordered most to "
                        "least relevant. Empty when suppressed."
                    ),
                },
                "no_match_reason": {"type": ["string", "null"]},
            },
            "required": [
                "headline",
                "what_changed",
                "decision",
                "lands",
                "no_match_reason",
            ],
            "additionalProperties": False,
        },
    }


def _usage_value(usage: Any, field: str) -> int:
    if usage is None:
        return 0
    if isinstance(usage, dict):
        return int(usage.get(field) or 0)
    return int(getattr(usage, field, 0) or 0)


def _input_detail(usage: Any, field: str) -> int:
    if usage is None:
        return 0
    details = (
        usage.get("input_tokens_details")
        if isinstance(usage, dict)
        else getattr(usage, "input_tokens_details", None)
    )
    return _usage_value(details, field)


def _response_request(
    *,
    model: str,
    effort: str,
    instructions: str,
    final_format: dict[str, Any],
    input_value: Any,
    tags: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "model": model,
        "reasoning": {"effort": effort},
        "instructions": instructions,
        "input": input_value,
        "text": {"format": final_format},
        "max_output_tokens": 6_000,
        "prompt_cache_key": PROMPT_CACHE_KEY,
        **llm_responses.litellm_prompt_cache_kwargs(model),
        "store": True,
        "extra_body": {"metadata": {"tags": list(tags)}},
        "extra_headers": {"x-litellm-tags": ",".join(tags)},
    }


def _create_response(
    client: Any,
    request: dict[str, Any],
) -> tuple[Any, dict[str, Any], float | None]:
    raw_api = getattr(client.responses, "with_raw_response", None)
    if raw_api is None:
        response = client.responses.create(**request)
        cost = None
    else:
        raw_response = raw_api.create(**request)
        response = raw_response.parse()
        cost = llm_responses.reported_cost(raw_response.headers)
    return response, llm_responses.as_dict(response), cost


def _is_retryable_response_error(exc: Exception) -> bool:
    if isinstance(exc, (openai.APIConnectionError, openai.APITimeoutError)):
        return True
    if isinstance(exc, openai.APIStatusError):
        return (
            exc.status_code in RETRYABLE_RESPONSE_STATUS_CODES
            or exc.status_code >= 500
        )
    return isinstance(exc, (ConnectionError, TimeoutError))


def _retry_delay_seconds(exc: Exception, attempt: int) -> float:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", {}) or {}
    retry_after_ms = headers.get("retry-after-ms")
    retry_after = headers.get("retry-after")
    try:
        if retry_after_ms is not None:
            return min(max(float(retry_after_ms) / 1000.0, 0.0), 30.0)
        if retry_after is not None:
            return min(max(float(retry_after), 0.0), 30.0)
    except (TypeError, ValueError):
        pass
    return min(2.0 ** (attempt - 1), 8.0)


def _error_attempt_trace(
    exc: Exception,
    *,
    attempt: int,
    duration: float,
    request: dict[str, Any],
    retryable: bool,
    retry_delay_seconds: float | None,
) -> dict[str, Any]:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", {}) or {}
    return {
        "attempt": attempt,
        "duration_ms": round(duration * 1000),
        "error_type": type(exc).__name__,
        "message": str(exc),
        "status_code": getattr(exc, "status_code", None),
        "request_id": headers.get("x-request-id"),
        "retryable": retryable,
        "retry_delay_seconds": retry_delay_seconds,
        "request": request,
    }


def _write_trace(path: Path, trace: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(trace, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _trace_path(
    *,
    trace_root: Path,
    day: str,
    rank: int,
    model: str,
    effort: str,
) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    model_slug = model.removeprefix("gpt-").replace(".", "-")
    prompt_slug = PROMPT_VERSION.replace("/", "-")
    day_root = trace_root / day
    day_root.mkdir(parents=True, exist_ok=True)
    return day_root / (
        f"{timestamp}-rank-{rank:03d}-{model_slug}-{effort}-{prompt_slug}.json"
    )


def _create_response_with_retry(
    client: Any,
    *,
    request: dict[str, Any],
    trace: dict[str, Any],
    trace_path: Path,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[Any, dict[str, Any], float | None, float]:
    for attempt in range(1, MAX_RESPONSE_ATTEMPTS + 1):
        started = time.monotonic()
        try:
            response, response_data, cost = _create_response(client, request)
            return response, response_data, cost, time.monotonic() - started
        except Exception as exc:
            duration = time.monotonic() - started
            retryable = _is_retryable_response_error(exc)
            will_retry = retryable and attempt < MAX_RESPONSE_ATTEMPTS
            delay = _retry_delay_seconds(exc, attempt) if will_retry else None
            trace["request_failures"].append(
                _error_attempt_trace(
                    exc,
                    attempt=attempt,
                    duration=duration,
                    request=request,
                    retryable=retryable,
                    retry_delay_seconds=delay,
                )
            )
            _write_trace(trace_path, trace)
            if not will_retry:
                raise
            sleep(delay)
    raise AssertionError("Response retry loop exhausted without returning or raising.")


def _call_trace(
    response: Any,
    response_data: dict[str, Any],
    *,
    request: dict[str, Any],
    cost: float | None,
    duration: float,
) -> dict[str, Any]:
    usage = getattr(response, "usage", None) or response_data.get("usage")
    return {
        "turn": 1,
        "response_id": getattr(response, "id", None) or response_data.get("id"),
        "response_status": response_data.get("status"),
        "response_model": getattr(response, "model", None)
        or response_data.get("model"),
        "duration_ms": round(duration * 1000),
        "input_tokens": _usage_value(usage, "input_tokens"),
        "cached_tokens": _input_detail(usage, "cached_tokens"),
        "cache_write_tokens": _input_detail(usage, "cache_write_tokens"),
        "output_tokens": _usage_value(usage, "output_tokens"),
        "reasoning_tokens": _usage_value(
            (
                usage.get("output_tokens_details")
                if isinstance(usage, dict)
                else getattr(usage, "output_tokens_details", None)
            ),
            "reasoning_tokens",
        ),
        "reported_cost_usd": cost,
        "request": request,
        "response": response_data,
        "output": response_data.get("output") or [],
    }


def _validate_final(
    result: dict[str, Any],
    *,
    surface_ids: set[str],
) -> dict[str, Any]:
    """Reject any result the read model would not be able to render."""
    if set(result) != engineering_agent_runs.RESULT_FIELDS:
        raise ValueError("the Engineering result does not match the v1 schema")
    headline = str(result.get("headline") or "").strip()
    if not headline or "\n" in headline:
        raise ValueError("the Engineering result has an empty headline")
    if len(headline.split()) > 22:
        raise ValueError("the Engineering headline is longer than 22 words")
    if not str(result.get("what_changed") or "").strip():
        raise ValueError("the Engineering result has an empty what_changed")
    decision = result.get("decision")
    if decision not in {"surface", "suppress"}:
        raise ValueError("the Engineering result has an invalid decision")
    landings = result.get("lands")
    if not isinstance(landings, list):
        raise ValueError("the Engineering result has invalid surface landings")
    if decision == "surface" and not landings:
        raise ValueError("a surfaced Engineering result cites no surface")
    if decision == "suppress" and landings:
        raise ValueError("a suppressed Engineering result cites a surface")
    if len(landings) > engineering_agent_runs.MAX_LANDINGS:
        raise ValueError(
            "the Engineering result cites more than "
            f"{engineering_agent_runs.MAX_LANDINGS} surfaces"
        )
    seen: list[str] = []
    for landing in landings:
        if set(landing) != engineering_agent_runs.LANDING_FIELDS:
            raise ValueError("an Engineering landing does not match the v1 schema")
        surface_id = str(landing["surface_id"]).strip()
        if surface_id not in surface_ids:
            raise ValueError(
                f"the Engineering result cites unknown surface {surface_id!r}"
            )
        if not str(landing["why"]).strip():
            raise ValueError("an Engineering landing has an empty why")
        seen.append(surface_id)
    if len(seen) != len(set(seen)):
        raise ValueError("the Engineering result repeats a surface")
    reason = result.get("no_match_reason")
    if decision == "suppress" and not str(reason or "").strip():
        raise ValueError("a suppressed Engineering result has no reason")
    if decision == "surface" and reason is not None:
        result["no_match_reason"] = None
    return result


def run_one(
    *,
    day: str,
    rank: int,
    development_id: str | None = None,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_EFFORT,
    api_base: str = DEFAULT_API_BASE,
    trace_root: Path = DEFAULT_TRACE_ROOT,
    db_path: Path = engineering_agent_runs.DEFAULT_DB,
    client_factory: Any = entity_kinds.create_litellm_client,
) -> dict[str, Any]:
    """Analyse one AI Engineering-routed Development against the Aion surfaces."""
    if development_id is None:
        candidates = _engineering_candidates(day=day, limit=200, api_base=api_base)
        matching = [
            item for item in candidates if int(item["daily_rank"]) == rank
        ]
        if not matching:
            raise RuntimeError(
                f"{day} daily rank {rank} is not a current AI "
                "Engineering-routed Development."
            )
        development_id = str(matching[0]["development_id"])

    developments_url = (
        f"{api_base}/api/developments?"
        + urllib.parse.urlencode(
            {
                "date": day,
                "development_id": development_id,
                "routing": "ai_engineering",
                "limit": 1,
                "include_evidence": "false",
            }
        )
    )
    exact_items = _get_json(developments_url).get("items") or []
    if (
        len(exact_items) != 1
        or str(exact_items[0]["development_id"]) != development_id
        or int(exact_items[0]["daily_rank"]) != rank
    ):
        raise RuntimeError(
            "The exact AI Engineering candidate no longer matches the "
            "selected Development and daily rank."
        )
    packet_url = (
        f"{api_base}/api/developments/analysis-packet?"
        + urllib.parse.urlencode({"date": day, "development_id": development_id})
    )
    packet = _get_json(packet_url)
    if not packet.get("available"):
        raise RuntimeError(packet.get("note") or "Development packet unavailable.")

    cards = _surface_cards()
    surface_ids = [card["id"] for card in cards]
    instructions = _instructions(cards)
    final_format = _final_format(surface_ids)
    model_input = (
        "<development_evidence>\n"
        + packet["model_input"]
        + "\n</development_evidence>"
    )
    tags = (
        "app:frontier-lab-intelligence",
        "pipeline:engineering-agent",
        f"date:{day}",
        f"development:{development_id[:12]}",
        f"model:{model}",
    )
    trace_path = _trace_path(
        trace_root=trace_root,
        day=day,
        rank=rank,
        model=model,
        effort=effort,
    )

    trace: dict[str, Any] = {
        "schema_version": "engineering-agent-trace-v1",
        "prompt_version": PROMPT_VERSION,
        "prompt_cache_key": PROMPT_CACHE_KEY,
        "date": day,
        "daily_rank": rank,
        "development_id": development_id,
        "model": model,
        "reasoning_effort": effort,
        "surface_count": len(cards),
        "surfaces_sha256": hashlib.sha256(
            json.dumps(cards, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest(),
        "evidence_sha256": packet.get("evidence_sha256"),
        "input_sha256": packet.get("input_sha256"),
        "surface_map_policy": {
            "source": str(SURFACE_PATH.relative_to(REPO_ROOT)),
            "inferred_from_public_sources": True,
            "web_search": False,
            "tool_calls": False,
        },
        "request_context": {
            "developments_url": developments_url,
            "analysis_packet_url": packet_url,
            "instructions": instructions,
            "final_format": final_format,
            "model_input": model_input,
        },
        "turns": [],
        "request_failures": [],
        "final_result": None,
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    _write_trace(trace_path, trace)

    client = client_factory()
    request = _response_request(
        model=model,
        effort=effort,
        instructions=instructions,
        final_format=final_format,
        input_value=model_input,
        tags=tags,
    )
    response, response_data, cost, duration = _create_response_with_retry(
        client,
        request=request,
        trace=trace,
        trace_path=trace_path,
    )
    trace["turns"].append(
        _call_trace(
            response,
            response_data,
            request=request,
            cost=cost,
            duration=duration,
        )
    )
    _write_trace(trace_path, trace)

    text = getattr(response, "output_text", None) or llm_responses.output_text(
        response_data
    )
    if not text:
        raise RuntimeError("The Engineering agent returned no final JSON.")
    result = _validate_final(json.loads(text), surface_ids=set(surface_ids))
    trace["final_result"] = result
    trace["completed_at"] = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )
    _write_trace(trace_path, trace)

    stored = engineering_agent_runs.import_trace(trace_path, db_path=db_path)
    turn = trace["turns"][0]
    return {
        "day": day,
        "daily_rank": rank,
        "development_id": development_id,
        "decision": result["decision"],
        "headline": result["headline"],
        "lands": result["lands"],
        "no_match_reason": result["no_match_reason"],
        "surface_count": len(cards),
        "input_tokens": int(turn["input_tokens"]),
        "cached_tokens": int(turn["cached_tokens"]),
        "output_tokens": int(turn["output_tokens"]),
        "reasoning_tokens": int(turn["reasoning_tokens"]),
        "request_retries": len(trace["request_failures"]),
        "reported_cost_usd": float(turn["reported_cost_usd"] or 0.0),
        "run_id": stored["run_id"],
        "trace_path": str(trace_path),
    }


def run_days(
    *,
    through: str = DEFAULT_DATE,
    days: int = 1,
    top_ranked: int = DEFAULT_TOP_RANKED,
    rank: int | None = None,
    dry_run: bool = False,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_EFFORT,
    workers: int = DEFAULT_WORKERS,
    api_base: str = DEFAULT_API_BASE,
    trace_root: Path = DEFAULT_TRACE_ROOT,
    db_path: Path = engineering_agent_runs.DEFAULT_DB,
    client_factory: Any = entity_kinds.create_litellm_client,
) -> dict[str, Any]:
    """Analyse and publish complete AI Engineering cohorts for whole days."""
    if days < 1:
        raise ValueError("days must be positive")
    if top_ranked < 1:
        raise ValueError("top_ranked must be positive")
    if workers < 1:
        raise ValueError("workers must be positive")
    through_day = date.fromisoformat(through)
    requested_days = [
        (through_day - timedelta(days=offset)).isoformat()
        for offset in reversed(range(days))
    ]
    targets: list[tuple[str, int, str]] = []
    for day in requested_days:
        candidates = _engineering_candidates(
            day=day,
            limit=max(top_ranked, 200 if rank is not None else top_ranked),
            api_base=api_base,
        )
        if rank is not None:
            if rank < 1:
                raise ValueError("rank must be positive")
            candidates = [
                item for item in candidates if int(item["daily_rank"]) == rank
            ]
            if not candidates:
                raise ValueError(
                    f"{day} daily rank {rank} is not a current AI "
                    "Engineering-routed Development."
                )
        for item in candidates[:top_ranked]:
            targets.append(
                (day, int(item["daily_rank"]), str(item["development_id"]))
            )
    if not targets:
        raise ValueError("No AI Engineering analysis targets were selected.")

    selection = {
        "audience": "ai_engineering",
        "routing_state": "evaluated",
        "relevant": True,
        "order": "daily_rank",
    }
    if dry_run:
        return {
            "schema_version": "engineering-agent-batch-v1",
            "selection": selection,
            "targets": [
                {
                    "day": day,
                    "daily_rank": daily_rank,
                    "development_id": development_id,
                }
                for day, daily_rank, development_id in targets
            ],
            "through": through,
            "days": requested_days,
            "top_ranked": None if rank is not None else top_ranked,
            "rank": rank,
            "dry_run": True,
            "model": model,
            "reasoning_effort": effort,
            "workers": workers,
            "prompt_version": PROMPT_VERSION,
            "prompt_cache_key": PROMPT_CACHE_KEY,
            "complete": True,
            "counts": {
                "requested": len(targets),
                "complete": 0,
                "failed": 0,
                "surfaced": 0,
                "suppressed": 0,
                "surface_landings": 0,
            },
            "telemetry": {
                "input_tokens": 0,
                "cached_tokens": 0,
                "output_tokens": 0,
                "reasoning_tokens": 0,
                "request_retries": 0,
                "reported_cost_usd": 0.0,
            },
            "items": [],
            "publications": [],
            "failures": [],
            "db": str(db_path.resolve()),
            "trace_root": str(trace_root.resolve()),
        }

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    def execute(target: tuple[str, int, str]) -> dict[str, Any]:
        day, daily_rank, development_id = target
        return run_one(
            day=day,
            rank=daily_rank,
            development_id=development_id,
            model=model,
            effort=effort,
            api_base=api_base,
            trace_root=trace_root,
            db_path=db_path,
            client_factory=client_factory,
        )

    def record_failure(target: tuple[str, int, str], exc: Exception) -> None:
        day, daily_rank, development_id = target
        failures.append(
            {
                "day": day,
                "daily_rank": daily_rank,
                "development_id": development_id,
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
        )

    # Populate the shared stable prompt prefix before the parallel fan-out.
    warm_target = targets[0]
    try:
        results.append(execute(warm_target))
    except Exception as exc:  # noqa: BLE001 - recorded as a run failure
        record_failure(warm_target, exc)

    remaining = targets[1:]
    if remaining:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(execute, item): item for item in remaining}
            for future in as_completed(futures):
                target = futures[future]
                try:
                    results.append(future.result())
                except Exception as exc:  # noqa: BLE001 - recorded as a failure
                    record_failure(target, exc)

    results.sort(key=lambda item: (item["day"], item["daily_rank"]))
    failures.sort(key=lambda item: (item["day"], item["daily_rank"]))

    publications: list[dict[str, Any]] = []
    failed_days = {item["day"] for item in failures}
    for day in requested_days:
        day_results = [item for item in results if item["day"] == day]
        if not day_results or day in failed_days:
            continue
        publications.append(
            engineering_agent_runs.publish_day(
                day=day,
                candidates=[
                    {
                        "development_id": item["development_id"],
                        "daily_rank": item["daily_rank"],
                    }
                    for item in day_results
                ],
                selection_limit=top_ranked if rank is None else 1,
                db_path=db_path,
            )
        )

    return {
        "schema_version": "engineering-agent-batch-v1",
        "selection": selection,
        "through": through,
        "days": requested_days,
        "top_ranked": None if rank is not None else top_ranked,
        "rank": rank,
        "dry_run": False,
        "model": model,
        "reasoning_effort": effort,
        "workers": workers,
        "prompt_version": PROMPT_VERSION,
        "prompt_cache_key": PROMPT_CACHE_KEY,
        "complete": not failures,
        "counts": {
            "requested": len(targets),
            "complete": len(results),
            "failed": len(failures),
            "surfaced": sum(item["decision"] == "surface" for item in results),
            "suppressed": sum(item["decision"] == "suppress" for item in results),
            "surface_landings": sum(len(item["lands"]) for item in results),
        },
        "telemetry": {
            "input_tokens": sum(item["input_tokens"] for item in results),
            "cached_tokens": sum(item["cached_tokens"] for item in results),
            "output_tokens": sum(item["output_tokens"] for item in results),
            "reasoning_tokens": sum(item["reasoning_tokens"] for item in results),
            "request_retries": sum(item["request_retries"] for item in results),
            "reported_cost_usd": round(
                sum(item["reported_cost_usd"] for item in results), 6
            ),
        },
        "items": results,
        "publications": publications,
        "failures": failures,
        "db": str(db_path.resolve()),
        "trace_root": str(trace_root.resolve()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Analyse AI Engineering-routed Developments against the assumed "
            "Aion surface map."
        )
    )
    parser.add_argument("--date", default=DEFAULT_DATE)
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--top-ranked", type=int, default=DEFAULT_TOP_RANKED)
    parser.add_argument("--rank", type=int, default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--effort", default=DEFAULT_EFFORT)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--trace-root", type=Path, default=DEFAULT_TRACE_ROOT)
    parser.add_argument(
        "--db", type=Path, default=engineering_agent_runs.DEFAULT_DB
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    summary = run_days(
        through=args.date,
        days=args.days,
        top_ranked=args.top_ranked,
        rank=args.rank,
        dry_run=args.dry_run,
        model=args.model,
        effort=args.effort,
        workers=args.workers,
        api_base=args.api_base,
        trace_root=args.trace_root,
        db_path=args.db,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
