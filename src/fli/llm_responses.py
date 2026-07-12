"""Shared normalization for OpenAI-compatible Responses API payloads."""

from __future__ import annotations

import hashlib
import json
from typing import Any


DEFAULT_PROMPT_CACHE_SHARDS = 64


def sharded_prompt_cache_key(
    *,
    namespace: str,
    prompt_version: str,
    scope_key: str | int,
    shards: int = DEFAULT_PROMPT_CACHE_SHARDS,
) -> str:
    """Return one stable cache-routing key from the shared repo convention."""
    if shards < 1:
        raise ValueError("prompt cache shards must be at least 1")
    digest = hashlib.sha256(str(scope_key).encode()).digest()
    shard = int.from_bytes(digest[:8], "big") % shards
    return f"fli:{namespace}:{prompt_version}:shard-{shard:02d}"


def reported_cost(headers: Any) -> float | None:
    """Read LiteLLM's operational response-cost header when present."""
    if headers is None:
        return None
    raw_cost = headers.get("x-litellm-response-cost")
    if raw_cost in (None, ""):
        return None
    try:
        return float(raw_cost)
    except (TypeError, ValueError):
        return None


def required_web_search_tool_choice(model: str) -> str:
    """Let Claude finish after native searches; callers still verify search evidence."""
    return "auto" if model.startswith("claude-") else "required"


def as_dict(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        return response
    if hasattr(response, "model_dump"):
        return response.model_dump(warnings=False)
    return {}


def output_text(response_data: dict[str, Any]) -> str:
    """Extract response text without joining nullable translated blocks."""
    direct = response_data.get("output_text")
    if isinstance(direct, str) and direct:
        return direct
    texts: list[str] = []
    for item in response_data.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if not isinstance(content, dict) or content.get("type") != "output_text":
                continue
            text = content.get("text")
            if isinstance(text, str):
                texts.append(text)
    return "".join(texts)


def web_evidence(
    response_data: dict[str, Any],
    *,
    cited_urls: list[str] | None = None,
    require_search_action: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return hosted-search actions and unique consulted sources."""
    actions: list[dict[str, Any]] = []
    sources: dict[str, dict[str, Any]] = {}
    for item in response_data.get("output") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "web_search_call":
            action = item.get("action") or {}
            actions.append(action)
            for source in action.get("sources") or []:
                if isinstance(source, dict) and source.get("url"):
                    sources[source["url"]] = source
        elif item.get("type") == "function_call" and item.get("name") == "web_search":
            try:
                arguments = json.loads(item.get("arguments") or "{}")
            except json.JSONDecodeError:
                arguments = {}
            actions.append(
                {
                    "type": "search",
                    "query": arguments.get("query"),
                    "translated_from": "function_call",
                }
            )
    if require_search_action and not actions:
        raise ValueError("response completed without required web search")
    if not sources:
        for url in cited_urls or []:
            sources[url] = {"url": url, "type": "model_citation"}
    return actions, list(sources.values())
