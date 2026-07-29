"""Company-aware Investment analysis over ranked Developments."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import openai

from fli import llm_responses
from fli.insights import investment_agent_runs
from fli.registry import classification as entity_kinds


REPO_ROOT = Path(__file__).resolve().parents[3]
MEMO_PATH = REPO_ROOT / "docs" / "references" / "company-memos.json"
DEFAULT_TRACE_ROOT = (
    REPO_ROOT / "data" / "derived" / "insights" / "investment-agent-traces"
)
DEFAULT_API_BASE = "http://127.0.0.1:8797"
DEFAULT_DATE = "2026-07-21"
DEFAULT_RANK = 1
DEFAULT_MODEL = "gpt-5.6-sol"
DEFAULT_EFFORT = "xhigh"
DEFAULT_TOP_RANKED = 10
DEFAULT_WORKERS = 9
MAX_UNIQUE_MEMOS = 8
MAX_MODEL_TURNS = 4
MAX_RESPONSE_ATTEMPTS = 3
RETRYABLE_RESPONSE_STATUS_CODES = frozenset({408, 409, 429, 499})
PROMPT_VERSION = "investment-agent-v15"
PROMPT_CACHE_KEY = "fli:investment-agent:v15"
PROMPT_PATH = (
    REPO_ROOT
    / "src"
    / "fli"
    / "insights"
    / "prompts"
    / "investment_company_analysis.txt"
)


def _get_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def _investment_candidates(
    *,
    day: str,
    limit: int,
    api_base: str,
) -> list[dict[str, Any]]:
    """Return the highest-ranked current Investment-routed Developments."""
    url = (
        f"{api_base}/api/developments?"
        + urllib.parse.urlencode(
            {
                "date": day,
                "routing": "investment",
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
        investment = route.get("investment") or {}
        if (
            item.get("routing_state") != "evaluated"
            or investment.get("relevant") is not True
        ):
            raise RuntimeError(
                "The Investment candidate endpoint returned a Development "
                "without a current positive Investment route."
            )
    return items


def _company_cards(payload: dict[str, Any]) -> list[dict[str, Any]]:
    memos = _all_memos()
    cards: list[dict[str, Any]] = []
    for company in payload["companies"]:
        ticker = company["ticker"]
        memo = memos.get(ticker)
        if memo is None:
            raise RuntimeError(f"No research memo for candidate {ticker}.")
        cards.append(
            {
                "ticker": ticker,
                "name": company["name"],
                "summary": memo["summary"],
                "bets": [
                    {"id": bet["id"], "if": bet["if"]} for bet in memo["bets"]
                ],
            }
        )
    return cards


def _bet_ids(ticker: str) -> list[str]:
    return [bet["id"] for bet in _all_memos()[ticker]["bets"]]



def _all_memos() -> dict[str, Any]:
    payload = json.loads(MEMO_PATH.read_text(encoding="utf-8"))
    return payload["companies"]


def _memo_packet(ticker: str) -> dict[str, Any]:
    memo = copy.deepcopy(_all_memos()[ticker])
    memo.pop("source_ledger", None)
    return {
        "schema_version": "investment-agent-company-memo-v4",
        "company": {"name": memo["name"], "ticker": memo["ticker"]},
        "research_date": memo.get("researched_at"),
        "packet_policy": {
            "included": (
                "What the company does and its standing bets. Each bet is a "
                "hypothesis fixed before this daily analysis: if the "
                "world-side condition holds, the named exposure moves the "
                "named financial line. Its binary direction is fixed in the "
                "memo, and its threshold states when the consequence is "
                "important enough to review the thesis."
            ),
            "excluded": (
                "Ecosystem relationships, committed strategy actions, "
                "research-workflow triggers, the source ledger, and all "
                "model-generation provenance."
            ),
            "bet_usage": (
                "Decide which standing bet this Development instantiates and "
                "cite its id. Do not invent a new transmission path when an "
                "existing bet already covers it."
            ),
        },
        "memo": memo,
    }


def _memo_tool(tickers: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "name": "get_company_memo",
        "description": (
            "Open the complete research memo for one candidate company only "
            "after the Development establishes a concrete causal connection. "
            "Use the smallest set needed to test the strongest connections. "
            "Multiple independent memo calls may be emitted together."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "enum": tickers},
                "connection_type": {
                    "type": "string",
                    "enum": ["direct", "indirect"],
                },
                "mechanism": {"type": "string"},
                "candidate_bet_id": {
                    "type": "string",
                    "description": (
                        "The id of the standing bet on this company's card "
                        "that the Development appears to instantiate."
                    ),
                },
                "why_memo_is_needed": {"type": "string"},
            },
            "required": [
                "ticker",
                "connection_type",
                "mechanism",
                "candidate_bet_id",
                "why_memo_is_needed",
            ],
            "additionalProperties": False,
        },
    }


def _final_format(tickers: list[str]) -> dict[str, Any]:
    company = {
        "type": "object",
        "properties": {
            "ticker": {"type": "string", "enum": tickers},
            "bet_id": {
                "type": "string",
                "description": (
                    "The id of the standing bet from this company's memo that "
                    "this Development instantiates, exactly as written in the "
                    "memo. Cite an existing bet; never invent an id."
                ),
            },
            "threshold_met": {
                "type": "boolean",
                "description": (
                    "True only when this Development's supplied evidence "
                    "establishes the cited bet's exact threshold now. A "
                    "plausible path, product launch, forecast, or early signal "
                    "is false."
                ),
            },
            "impact": {
                "type": "string",
                "description": (
                    "Two to three sentences on what this Development means "
                    "for this company specifically. Name the product, segment "
                    "or contract that carries the effect, and say what would "
                    "have to happen for it to show up in results. Do not "
                    "state the company's rank; the ordering already shows it."
                ),
            },
        },
        "required": [
            "ticker",
            "bet_id",
            "threshold_met",
            "impact",
        ],
        "additionalProperties": False,
    }
    connection = {
        "type": "object",
        "properties": {
            "mechanism": {
                "type": "string",
                "description": (
                    "No more than two sentences tracing the complete causal "
                    "link from the Development to the companies below. Written "
                    "once for the whole path, not per company."
                ),
            },
            "companies": {
                "type": "array",
                "minItems": 1,
                "maxItems": MAX_UNIQUE_MEMOS,
                "items": company,
                "description": (
                    "Every company on this mechanism, ordered most to least "
                    "exposed."
                ),
            },
        },
        "required": [
            "mechanism",
            "companies",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "json_schema",
        "name": PROMPT_VERSION.replace("-", "_"),
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "decision": {
                    "type": "string",
                    "enum": ["surface", "suppress"],
                },
                "headline": {
                    "type": "string",
                    "description": (
                        "A 6-14 word plain-English headline stating the most "
                        "important supported investment implication."
                    ),
                },
                "what_changed": {"type": "string"},
                "connections": {
                    "type": "array",
                    "maxItems": MAX_UNIQUE_MEMOS,
                    "items": connection,
                    "description": (
                        "Causal mechanisms, ordered most to least "
                        "decision-relevant."
                    ),
                },
                "no_match_reason": {"type": ["string", "null"]},
            },
            "required": [
                "decision",
                "headline",
                "what_changed",
                "connections",
                "no_match_reason",
            ],
            "additionalProperties": False,
        },
    }


def _instructions(cards: list[dict[str, Any]]) -> str:
    company_json = json.dumps(cards, ensure_ascii=False, sort_keys=True)
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace("{{COMPANY_UNIVERSE_JSON}}", company_json)


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
    tools: list[dict[str, Any]],
    final_format: dict[str, Any],
    input_value: Any,
    previous_response_id: str | None,
    tags: tuple[str, ...],
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "model": model,
        "reasoning": {"effort": effort},
        "instructions": instructions,
        "tools": tools,
        "input": input_value,
        "text": {"format": final_format},
        "max_output_tokens": 10_000,
        "prompt_cache_key": PROMPT_CACHE_KEY,
        **llm_responses.litellm_prompt_cache_kwargs(model),
        "store": True,
        "extra_body": {"metadata": {"tags": list(tags)}},
        "extra_headers": {"x-litellm-tags": ",".join(tags)},
    }
    if previous_response_id is not None:
        request["previous_response_id"] = previous_response_id
    return request


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
    turn: int,
    attempt: int,
    duration: float,
    request: dict[str, Any],
    retryable: bool,
    retry_delay_seconds: float | None,
) -> dict[str, Any]:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", {}) or {}
    return {
        "turn": turn,
        "attempt": attempt,
        "error_type": type(exc).__name__,
        "status_code": getattr(exc, "status_code", None),
        "message": str(exc),
        "response_body": getattr(exc, "body", None),
        "request_id": getattr(exc, "request_id", None),
        "duration_ms": round(duration * 1000),
        "retryable": retryable,
        "retry_delay_seconds": retry_delay_seconds,
        "response_headers": {
            key: headers[key]
            for key in (
                "retry-after",
                "retry-after-ms",
                "x-request-id",
                "x-litellm-call-id",
            )
            if key in headers
        },
        "request": request,
    }


def _create_response_with_retry(
    client: Any,
    *,
    request: dict[str, Any],
    trace: dict[str, Any],
    trace_path: Path,
    turn: int,
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
                    turn=turn,
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
    turn: int,
    cost: float | None,
    duration: float,
) -> dict[str, Any]:
    usage = getattr(response, "usage", None) or response_data.get("usage")
    output = response_data.get("output") or []
    return {
        "turn": turn,
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
        "output": output,
    }


def _function_calls(response: Any) -> list[Any]:
    return [
        item
        for item in (getattr(response, "output", None) or [])
        if getattr(item, "type", None) == "function_call"
    ]


def _validate_final(
    result: dict[str, Any],
    *,
    fetched_tickers: set[str],
) -> None:
    headline = str(result["headline"]).strip()
    if not headline or "\n" in headline or len(headline.split()) > 18:
        raise ValueError(
            "Investment headline must be one concise non-empty line."
        )
    assessed = [
        company["ticker"]
        for connection in result["connections"]
        for company in connection["companies"]
    ]
    cited_bets = [
        (company["ticker"], company["bet_id"])
        for connection in result["connections"]
        for company in connection["companies"]
    ]
    if len(cited_bets) != len(set(cited_bets)):
        raise ValueError(
            "A company bet appears more than once in the final result."
        )
    if not set(assessed).issubset(fetched_tickers):
        raise ValueError(
            "A company was assessed without opening its memo."
        )
    for connection in result["connections"]:
        for company in connection["companies"]:
            valid = _bet_ids(company["ticker"])
            if company["bet_id"] not in valid:
                raise ValueError(
                    f"{company['ticker']} cites unknown bet "
                    f"{company['bet_id']!r}. Valid ids: {', '.join(valid)}"
                )
    if result["decision"] == "surface":
        if not assessed or result["no_match_reason"] is not None:
            raise ValueError(
                "A surfaced result needs company connections and a null reason."
            )
    else:
        if assessed or not str(result["no_match_reason"] or "").strip():
            raise ValueError(
                "A suppressed result needs no company connections and a reason."
            )
    serialized = json.dumps(result, ensure_ascii=False).lower()
    if "http://" in serialized or "https://" in serialized or "](" in serialized:
        raise ValueError("Final model prose must not contain links or citations.")


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


def run_one(
    *,
    day: str,
    rank: int,
    development_id: str | None = None,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_EFFORT,
    api_base: str = DEFAULT_API_BASE,
    trace_root: Path = DEFAULT_TRACE_ROOT,
    db_path: Path = investment_agent_runs.DEFAULT_DB,
    client_factory: Any = entity_kinds.create_litellm_client,
) -> dict[str, Any]:
    if rank < 1:
        raise ValueError("rank must be positive")
    date.fromisoformat(day)
    candidates = _investment_candidates(day=day, limit=200, api_base=api_base)
    development = next(
        (
            item
            for item in candidates
            if int(item["daily_rank"]) == rank
            and (
                development_id is None
                or str(item["development_id"]) == development_id
            )
        ),
        None,
    )
    if development is None:
        raise ValueError(
            f"{day} daily rank {rank} is not a current Investment-routed "
            "Development."
        )
    development_id = str(development["development_id"])
    developments_url = (
        f"{api_base}/api/developments?"
        + urllib.parse.urlencode(
            {
                "date": day,
                "development_id": development_id,
                "routing": "investment",
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
            "The exact Investment candidate no longer matches the selected "
            "Development and daily rank."
        )
    development = exact_items[0]
    packet_url = (
        f"{api_base}/api/developments/analysis-packet?"
        + urllib.parse.urlencode(
            {
                "date": day,
                "development_id": development_id,
            }
        )
    )
    packet = _get_json(packet_url)
    if not packet.get("available"):
        raise RuntimeError(packet.get("note") or "Development packet unavailable.")

    universe_url = f"{api_base}/api/bit-lens/companies"
    universe = _get_json(universe_url)
    cards = _company_cards(universe)
    tickers = [card["ticker"] for card in cards]
    instructions = _instructions(cards)
    tools = [_memo_tool(tickers)]
    final_format = _final_format(tickers)
    model_input = (
        "<development_evidence>\n"
        + packet["model_input"]
        + "\n</development_evidence>"
    )
    tags = (
        "app:frontier-lab-intelligence",
        "pipeline:investment-agent",
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
        "schema_version": "investment-agent-trace-v1",
        "prompt_version": PROMPT_VERSION,
        "prompt_cache_key": PROMPT_CACHE_KEY,
        "date": day,
        "daily_rank": rank,
        "development_id": development_id,
        "model": model,
        "reasoning_effort": effort,
        "company_count": len(cards),
        "company_cards_sha256": hashlib.sha256(
            json.dumps(cards, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest(),
        "evidence_sha256": packet.get("evidence_sha256"),
        "input_sha256": packet.get("input_sha256"),
        "memo_packet_policy": {
            "includes": (
                "All analytical sections, inline source URLs/dates, research "
                "date, uncertainties, and next-research triggers."
            ),
            "excludes": "Standalone source ledger and generation provenance.",
            "web_search": False,
            "compaction": False,
        },
        "request_context": {
            "developments_url": developments_url,
            "analysis_packet_url": packet_url,
            "company_universe_url": universe_url,
            "instructions": instructions,
            "tools": tools,
            "final_format": final_format,
            "model_input": model_input,
            "max_output_tokens": 10_000,
            "store": True,
        },
        "turns": [],
        "request_failures": [],
        "memo_calls": [],
        "memo_packets": {},
        "citation_repairs": [],
        "final_result": None,
    }
    _write_trace(trace_path, trace)

    client = client_factory()
    if hasattr(client, "with_options"):
        client = client.with_options(max_retries=0)
    previous_response_id: str | None = None
    input_value: Any = model_input
    fetched_tickers: set[str] = set()

    for turn in range(1, MAX_MODEL_TURNS + 1):
        request = _response_request(
            model=model,
            effort=effort,
            instructions=instructions,
            tools=tools,
            final_format=final_format,
            input_value=input_value,
            previous_response_id=previous_response_id,
            tags=tags,
        )
        response, response_data, cost, duration = _create_response_with_retry(
            client,
            request=request,
            trace=trace,
            trace_path=trace_path,
            turn=turn,
        )
        trace["turns"].append(
            _call_trace(
                response,
                response_data,
                request=request,
                turn=turn,
                cost=cost,
                duration=duration,
            )
        )
        _write_trace(trace_path, trace)

        calls = _function_calls(response)
        if not calls:
            output_text = getattr(response, "output_text", None)
            if not output_text:
                raise RuntimeError("Model returned neither tool calls nor final text.")
            result = json.loads(output_text)
            trace["citation_repairs"] = []
            _validate_final(
                result,
                fetched_tickers=fetched_tickers,
            )
            trace["final_result"] = result
            _write_trace(trace_path, trace)
            break

        parsed_calls: list[tuple[Any, dict[str, Any]]] = []
        tickers_this_turn: set[str] = set()
        for call in calls:
            if call.name != "get_company_memo":
                raise RuntimeError(f"Unexpected tool call: {call.name}")
            arguments = json.loads(call.arguments)
            ticker = arguments["ticker"]
            if ticker in fetched_tickers or ticker in tickers_this_turn:
                raise RuntimeError(f"Duplicate memo call for {ticker}.")
            tickers_this_turn.add(ticker)
            parsed_calls.append((call, arguments))
        if len(fetched_tickers | tickers_this_turn) > MAX_UNIQUE_MEMOS:
            raise RuntimeError(
                f"Model requested more than {MAX_UNIQUE_MEMOS} unique memos."
            )

        with ThreadPoolExecutor(max_workers=len(parsed_calls)) as executor:
            packets = list(
                executor.map(
                    _memo_packet,
                    [arguments["ticker"] for _, arguments in parsed_calls],
                )
            )
        outputs: list[dict[str, Any]] = []
        for (call, arguments), memo_packet in zip(
            parsed_calls, packets, strict=True
        ):
            ticker = arguments["ticker"]
            fetched_tickers.add(ticker)
            trace["memo_calls"].append(
                {
                    "turn": turn,
                    "call_id": call.call_id,
                    "arguments": arguments,
                }
            )
            trace["memo_packets"][ticker] = memo_packet
            outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(
                        memo_packet, ensure_ascii=False, sort_keys=True
                    ),
                }
            )
        _write_trace(trace_path, trace)
        previous_response_id = getattr(response, "id", None)
        if not previous_response_id:
            raise RuntimeError("Cannot continue without a response ID.")
        input_value = outputs
    else:
        raise RuntimeError("Model exceeded the maximum number of loop turns.")

    imported = investment_agent_runs.import_trace(trace_path, db_path=db_path)
    summary = {
        "trace_path": str(trace_path),
        "development_id": development_id,
        "daily_rank": rank,
        "memo_tickers": sorted(fetched_tickers),
        "turns": [
            {
                key: turn[key]
                for key in (
                    "turn",
                    "response_id",
                    "duration_ms",
                    "input_tokens",
                    "cached_tokens",
                    "output_tokens",
                    "reasoning_tokens",
                    "reported_cost_usd",
                )
            }
            for turn in trace["turns"]
        ],
        "request_failures": trace["request_failures"],
        "final_result": trace["final_result"],
        "imported": imported,
    }
    return summary


def _compact_result(result: dict[str, Any]) -> dict[str, Any]:
    turns = result["turns"]
    final = result["final_result"]
    return {
        "day": result["imported"]["day"],
        "daily_rank": result["daily_rank"],
        "development_id": result["development_id"],
        "decision": final["decision"],
        "headline": final["headline"],
        "memo_tickers": result["memo_tickers"],
        "companies": len(
            {
                company["ticker"]
                for connection in final["connections"]
                for company in connection["companies"]
            }
        ),
        "connections": len(final["connections"]),
        "memos_rejected": len(result["memo_tickers"])
        - len(
            {
                company["ticker"]
                for connection in final["connections"]
                for company in connection["companies"]
            }
        ),
        "turns": len(turns),
        "request_retries": len(result.get("request_failures") or []),
        "input_tokens": sum(int(turn["input_tokens"]) for turn in turns),
        "cached_tokens": sum(int(turn["cached_tokens"]) for turn in turns),
        "output_tokens": sum(int(turn["output_tokens"]) for turn in turns),
        "reasoning_tokens": sum(int(turn["reasoning_tokens"]) for turn in turns),
        "reported_cost_usd": round(
            sum(float(turn["reported_cost_usd"] or 0.0) for turn in turns),
            9,
        ),
        "trace_path": result["trace_path"],
        "run_id": result["imported"]["run_id"],
    }


def run_range(
    *,
    through: str,
    days: int = 1,
    top_ranked: int = DEFAULT_TOP_RANKED,
    rank: int | None = None,
    dry_run: bool = False,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_EFFORT,
    workers: int = DEFAULT_WORKERS,
    api_base: str = DEFAULT_API_BASE,
    trace_root: Path = DEFAULT_TRACE_ROOT,
    db_path: Path = investment_agent_runs.DEFAULT_DB,
    client_factory: Any = entity_kinds.create_litellm_client,
) -> dict[str, Any]:
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
        candidates = _investment_candidates(
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
                    f"{day} daily rank {rank} is not a current "
                    "Investment-routed Development."
                )
        for item in candidates[:top_ranked]:
            targets.append(
                (
                    day,
                    int(item["daily_rank"]),
                    str(item["development_id"]),
                )
            )
    if not targets:
        raise ValueError("No Investment analysis targets were selected.")

    if dry_run:
        return {
            "schema_version": "investment-agent-batch-v2",
            "selection": {
                "audience": "investment",
                "routing_state": "evaluated",
                "relevant": True,
                "order": "daily_rank",
            },
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
                "memo_calls": 0,
                "companies": 0,
                "memos_rejected": 0,
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

    # Populate the shared stable prompt prefix before the parallel fan-out.
    warm_target = targets[0]
    try:
        results.append(execute(warm_target))
    except Exception as exc:
        failures.append(
            {
                "day": warm_target[0],
                "daily_rank": warm_target[1],
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
        )

    remaining = targets[1:]
    if remaining:
        with ThreadPoolExecutor(max_workers=min(workers, len(remaining))) as executor:
            future_targets = {
                executor.submit(execute, target): target for target in remaining
            }
            for future in as_completed(future_targets):
                target = future_targets[future]
                try:
                    results.append(future.result())
                except Exception as exc:
                    failures.append(
                        {
                            "day": target[0],
                            "daily_rank": target[1],
                            "error_type": type(exc).__name__,
                            "message": str(exc),
                        }
                    )

    compact = sorted(
        (_compact_result(result) for result in results),
        key=lambda item: (item["day"], item["daily_rank"]),
    )
    publications = []
    if rank is None:
        failed_days = {item["day"] for item in failures}
        compact_by_day = {
            day: [item for item in compact if item["day"] == day]
            for day in requested_days
        }
        targets_by_day = {
            day: [
                {
                    "development_id": development_id,
                    "daily_rank": daily_rank,
                }
                for target_day, daily_rank, development_id in targets
                if target_day == day
            ]
            for day in requested_days
        }
        publishable = [
            {
                "day": day,
                "candidates": targets_by_day[day],
                "selection_limit": top_ranked,
            }
            for day in requested_days
            if day not in failed_days
            and len(compact_by_day[day]) == len(targets_by_day[day])
        ]
        if publishable:
            publications = investment_agent_runs.publish_days(
                publications=publishable,
                db_path=db_path,
            )
    return {
        "schema_version": "investment-agent-batch-v2",
        "selection": {
            "audience": "investment",
            "routing_state": "evaluated",
            "relevant": True,
            "order": "daily_rank",
        },
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
        "dry_run": False,
        "model": model,
        "reasoning_effort": effort,
        "workers": workers,
        "prompt_version": PROMPT_VERSION,
        "prompt_cache_key": PROMPT_CACHE_KEY,
        "complete": not failures,
        "counts": {
            "requested": len(targets),
            "complete": len(compact),
            "failed": len(failures),
            "surfaced": sum(item["decision"] == "surface" for item in compact),
            "suppressed": sum(item["decision"] == "suppress" for item in compact),
            "memo_calls": sum(len(item["memo_tickers"]) for item in compact),
            "companies": sum(
                int(item["companies"]) for item in compact
            ),
            "memos_rejected": sum(
                int(item["memos_rejected"]) for item in compact
            ),
        },
        "telemetry": {
            "input_tokens": sum(int(item["input_tokens"]) for item in compact),
            "cached_tokens": sum(int(item["cached_tokens"]) for item in compact),
            "output_tokens": sum(int(item["output_tokens"]) for item in compact),
            "reasoning_tokens": sum(
                int(item["reasoning_tokens"]) for item in compact
            ),
            "request_retries": sum(
                int(item["request_retries"]) for item in compact
            ),
            "reported_cost_usd": round(
                sum(float(item["reported_cost_usd"]) for item in compact),
                9,
            ),
        },
        "items": compact,
        "publications": publications,
        "failures": sorted(
            failures,
            key=lambda item: (item["day"], item["daily_rank"]),
        ),
        "db": str(db_path.resolve()),
        "trace_root": str(trace_root.resolve()),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--through", default=DEFAULT_DATE)
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--top-ranked", type=int, default=DEFAULT_TOP_RANKED)
    parser.add_argument("--rank", type=int)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--effort", default=DEFAULT_EFFORT)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--trace-root", type=Path, default=DEFAULT_TRACE_ROOT)
    parser.add_argument("--db", type=Path, default=investment_agent_runs.DEFAULT_DB)
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = run_range(
        through=args.through,
        days=args.days,
        top_ranked=args.top_ranked,
        rank=args.rank,
        model=args.model,
        effort=args.effort,
        workers=args.workers,
        api_base=args.api_base,
        trace_root=args.trace_root,
        db_path=args.db,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
