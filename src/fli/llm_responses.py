"""Shared normalization for OpenAI-compatible Responses API payloads."""

from __future__ import annotations

from typing import Any


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
        if not isinstance(item, dict):
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
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return hosted-search actions and unique consulted sources."""
    actions: list[dict[str, Any]] = []
    sources: dict[str, dict[str, Any]] = {}
    for item in response_data.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "web_search_call":
            continue
        action = item.get("action") or {}
        actions.append(action)
        for source in action.get("sources") or []:
            if isinstance(source, dict) and source.get("url"):
                sources[source["url"]] = source
    if not actions:
        raise ValueError("response completed without required web search")
    return actions, list(sources.values())
