"""Machine-readable prompt-cache canary for the Azure-backed LiteLLM route."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from openai import APIConnectionError, APITimeoutError, AuthenticationError

from fli import llm_responses
from fli.registry import classification as entity_kinds
from fli.routing import model as routing_model


CLI_SCHEMA_VERSION = "1.0"
COMMAND = "prompt-cache-canary"
DEFAULT_MODELS = ("gpt-5.6-luna", "gpt-5.6-terra")
DEFAULT_ATTEMPTS = 5
DEFAULT_REASONING_EFFORT = "high"
DEFAULT_MAX_OUTPUT_TOKENS = 64
DEFAULT_TIMEOUT_SECONDS = 180.0


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _usage_value(usage: Any, field: str) -> int:
    if usage is None:
        return 0
    if isinstance(usage, dict):
        return int(usage.get(field) or 0)
    return int(getattr(usage, field, 0) or 0)


def _input_token_detail(usage: Any, field: str) -> int:
    if usage is None:
        return 0
    details = (
        usage.get("input_tokens_details")
        if isinstance(usage, dict)
        else getattr(usage, "input_tokens_details", None)
    )
    return _usage_value(details, field)


def _create_response(
    client: Any, request: dict[str, Any]
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


def run_canary(
    client: Any,
    *,
    models: tuple[str, ...] = DEFAULT_MODELS,
    attempts: int = DEFAULT_ATTEMPTS,
    effort: str = DEFAULT_REASONING_EFFORT,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    request_id: str,
    progress: str = "off",
) -> dict[str, Any]:
    """Run different-input repeats so proxy full-response caching cannot pass."""
    if attempts < 2:
        raise ValueError("attempts must be at least 2")
    if max_output_tokens < 1:
        raise ValueError("max_output_tokens must be positive")
    if not models or any(not model.strip() for model in models):
        raise ValueError("at least one non-empty model is required")

    model_results = []
    for model in models:
        cache_key = llm_responses.sharded_prompt_cache_key(
            namespace=f"cache-canary-{request_id[:8]}",
            prompt_version=model,
            scope_key=model,
            shards=1,
        )
        calls = []
        for attempt in range(1, attempts + 1):
            nonce = uuid4().hex
            tags = (
                "app:frontier-lab-intelligence",
                "pipeline:diagnostics",
                "job:prompt-cache-canary",
                f"model:{model}",
                f"request:{request_id}",
            )
            request = {
                "model": model,
                "instructions": routing_model.instructions(),
                "input": (
                    "Prompt-cache canary variable suffix. "
                    f"Attempt: {attempt}. Nonce: {nonce}."
                ),
                "prompt_cache_key": cache_key,
                **llm_responses.litellm_prompt_cache_kwargs(model),
                "reasoning": {"effort": effort},
                "max_output_tokens": max_output_tokens,
                "text": {"format": routing_model.OUTPUT_FORMAT},
                "store": False,
                "extra_body": {"metadata": {"tags": list(tags)}},
                "extra_headers": {"x-litellm-tags": ",".join(tags)},
            }
            started = time.monotonic()
            response, response_data, reported_cost = _create_response(client, request)
            usage = getattr(response, "usage", None) or response_data.get("usage")
            call = {
                "attempt": attempt,
                "response_id": (
                    getattr(response, "id", None) or response_data.get("id")
                ),
                "response_model": (
                    getattr(response, "model", None) or response_data.get("model")
                ),
                "response_status": response_data.get("status"),
                "duration_ms": round((time.monotonic() - started) * 1000),
                "input_tokens": _usage_value(usage, "input_tokens"),
                "cached_tokens": _input_token_detail(usage, "cached_tokens"),
                "cache_write_tokens": _input_token_detail(
                    usage, "cache_write_tokens"
                ),
                "output_tokens": _usage_value(usage, "output_tokens"),
                "reported_cost_usd": reported_cost,
            }
            calls.append(call)
            if progress == "plain":
                print(
                    f"{model} attempt {attempt}/{attempts}: "
                    f"{call['cached_tokens']} cached tokens",
                    file=sys.stderr,
                    flush=True,
                )
        warm_calls = calls[1:]
        warm_hits = sum(call["cached_tokens"] > 0 for call in warm_calls)
        model_results.append(
            {
                "model": model,
                "prompt_cache_key": cache_key,
                "prompt_cache_key_length": len(cache_key),
                "attempts": attempts,
                "warm_requests": len(warm_calls),
                "warm_hit_requests": warm_hits,
                "cache_observed": warm_hits > 0,
                "calls": calls,
            }
        )
    return {
        "prompt_version": routing_model.PROMPT_VERSION,
        "reasoning_effort": effort,
        "max_output_tokens": max_output_tokens,
        "models": model_results,
        "cache_observed_for_all_models": all(
            result["cache_observed"] for result in model_results
        ),
    }


def _meta(*, request_id: str, started: float) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "timestamp_utc": _now(),
    }


def _envelope(
    *,
    status: str,
    data: dict[str, Any] | None,
    error: dict[str, Any] | None,
    request_id: str,
    started: float,
) -> dict[str, Any]:
    return {
        "schema_version": CLI_SCHEMA_VERSION,
        "command": COMMAND,
        "status": status,
        "data": data,
        "error": error,
        "meta": _meta(request_id=request_id, started=started),
    }


def _error_payload(exc: Exception) -> tuple[int, dict[str, Any]]:
    if isinstance(exc, AuthenticationError):
        return 3, {
            "code": "E_AUTH",
            "message": "LiteLLM authentication failed.",
            "retryable": False,
            "hint": "Repair the shared machine-secret configuration.",
        }
    if isinstance(exc, APITimeoutError):
        return 5, {
            "code": "E_TIMEOUT",
            "message": "The prompt-cache canary timed out.",
            "retryable": True,
            "hint": "Retry or increase --timeout.",
        }
    if isinstance(exc, APIConnectionError):
        return 4, {
            "code": "E_NETWORK",
            "message": "The LiteLLM endpoint could not be reached.",
            "retryable": True,
            "hint": "Check endpoint availability and retry.",
        }
    if isinstance(exc, (ValueError, TypeError)):
        return 2, {
            "code": "E_USAGE",
            "message": str(exc),
            "retryable": False,
            "hint": "Run with --help and correct the arguments.",
        }
    return 1, {
        "code": "E_CANARY",
        "message": f"{type(exc).__name__}: {exc}",
        "retryable": True,
        "hint": "Inspect endpoint health and retry the canary.",
    }


def _emit(payload: dict[str, Any], *, plain: bool) -> None:
    if not plain:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    data = payload.get("data") or {}
    for result in data.get("models") or []:
        print(
            f"{result['model']}: {result['warm_hit_requests']}/"
            f"{result['warm_requests']} warm requests hit"
        )
    if payload["error"]:
        print(f"{payload['error']['code']}: {payload['error']['message']}")


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="fli prompt-cache-canary")
    parser.add_argument(
        "--model",
        action="append",
        dest="models",
        help="Model alias to probe; repeat for multiple models.",
    )
    parser.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS)
    parser.add_argument(
        "--reasoning-effort", default=DEFAULT_REASONING_EFFORT
    )
    parser.add_argument(
        "--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--progress", choices=("off", "plain"), default="off")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="Stable JSON (default).")
    output.add_argument("--plain", action="store_true", help="Compact human output.")
    parser.add_argument(
        "--no-input", action="store_true", help="Never prompt (always honored)."
    )
    return parser


def main(
    argv: list[str] | None = None,
    *,
    client_factory: Callable[[], Any] = entity_kinds.create_litellm_client,
) -> int:
    raw_args = list(argv) if argv is not None else sys.argv[1:]
    request_id = uuid4().hex
    started = time.monotonic()
    plain = "--plain" in raw_args
    try:
        args = _parser().parse_args(raw_args)
        if args.timeout <= 0:
            raise ValueError("timeout must be positive")
        client = client_factory()
        if hasattr(client, "with_options"):
            client = client.with_options(timeout=args.timeout, max_retries=0)
        data = run_canary(
            client,
            models=tuple(args.models or DEFAULT_MODELS),
            attempts=args.attempts,
            effort=args.reasoning_effort,
            max_output_tokens=args.max_output_tokens,
            request_id=request_id,
            progress=args.progress,
        )
        if data["cache_observed_for_all_models"]:
            payload = _envelope(
                status="ok",
                data=data,
                error=None,
                request_id=request_id,
                started=started,
            )
            _emit(payload, plain=args.plain)
            return 0
        payload = _envelope(
            status="error",
            data=data,
            error={
                "code": "E_CACHE_NOT_OBSERVED",
                "message": "At least one model had no warm prompt-cache read.",
                "retryable": True,
                "hint": "Prompt caching is best-effort; retry before escalating.",
            },
            request_id=request_id,
            started=started,
        )
        _emit(payload, plain=args.plain)
        return 1
    except KeyboardInterrupt:
        payload = _envelope(
            status="error",
            data=None,
            error={
                "code": "E_INTERRUPTED",
                "message": "The prompt-cache canary was interrupted.",
                "retryable": True,
                "hint": "Retry when ready.",
            },
            request_id=request_id,
            started=started,
        )
        _emit(payload, plain=plain)
        return 5
    except Exception as exc:
        exit_code, error = _error_payload(exc)
        payload = _envelope(
            status="error",
            data=None,
            error=error,
            request_id=request_id,
            started=started,
        )
        _emit(payload, plain=plain)
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
