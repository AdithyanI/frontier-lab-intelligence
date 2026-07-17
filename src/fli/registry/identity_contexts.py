"""Grounded identity context for accounts whose source bio is missing."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fli import llm_responses

PROMPT_VERSION = "identity-context-v1"
SCHEMA_VERSION = "identity-context-output-v1"
DEFAULT_MODEL = llm_responses.DEFAULT_EFFICIENT_MODEL
DEFAULT_REASONING_EFFORT = "high"
PROMPT_CACHE_SHARDS = 16
PROMPT_PATH = Path(__file__).with_name("prompts") / "identity_context.txt"
PARENTHESIZED_CITATION_RE = re.compile(
    r"\s*\(\s*\[[^\]]+\]\(https?://[^)]+\)\s*\)"
)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(https?://[^)]+\)")

OUTPUT_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "name": "identity_context",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "identity_status": {
                "type": "string",
                "enum": ["resolved", "unresolved"],
            },
            "canonical_name": {"type": "string"},
            "current_role": {"type": "string"},
            "current_organization": {"type": "string"},
            "known_for": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 5,
            },
            "frontier_ai_relevance": {"type": "string"},
            "research_summary": {"type": "string"},
        },
        "required": [
            "identity_status",
            "canonical_name",
            "current_role",
            "current_organization",
            "known_for",
            "frontier_ai_relevance",
            "research_summary",
        ],
        "additionalProperties": False,
    },
}


@dataclass(frozen=True)
class IdentityInput:
    entity_id: int
    handle: str
    display_name: str
    profile_url: str
    recent_posts: tuple[dict[str, Any], ...] = ()

    @property
    def input_sha256(self) -> str:
        return hashlib.sha256(
            json.dumps(
                {
                    "entity_id": self.entity_id,
                    "handle": self.handle,
                    "display_name": self.display_name,
                    "profile_url": self.profile_url,
                    "recent_posts": self.recent_posts,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()


def instructions() -> str:
    return PROMPT_PATH.read_text().strip()


def prompt_sha256() -> str:
    return hashlib.sha256(instructions().encode()).hexdigest()


def prompt_cache_key(entity_id: int) -> str:
    return llm_responses.sharded_prompt_cache_key(
        namespace="identity-context",
        prompt_version=PROMPT_VERSION,
        scope_key=entity_id,
        shards=PROMPT_CACHE_SHARDS,
    )


def request_tags(*, run: str) -> tuple[str, ...]:
    return (
        "app:frontier-lab-intelligence",
        "pipeline:registry-evaluation",
        "job:missing-bio-identity-context",
        "scope:single-entity",
        f"prompt:{PROMPT_VERSION}",
        f"run:{run}",
    )


def render_input(entity: IdentityInput) -> str:
    blocks = [
        "Research the exact person behind this X account.",
        "The source profile has no observed biography.",
        "",
        f"Handle: @{entity.handle}",
        f"Display name: {entity.display_name}",
        f"Profile: {entity.profile_url}",
        "",
        "Recent authored posts supplied only as identity-disambiguation clues:",
    ]
    if not entity.recent_posts:
        blocks.append("No recent authored posts were supplied.")
    for index, post in enumerate(entity.recent_posts, start=1):
        blocks.extend(
            (
                "",
                f"Post {index} ({post.get('created_at') or 'date unavailable'}):",
                str(post.get("text") or ""),
            )
        )
    return "\n".join(blocks)


def _normalize_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    value = PARENTHESIZED_CITATION_RE.sub("", value)
    value = MARKDOWN_LINK_RE.sub(r"\1", value)
    return " ".join(value.split())


def _validate_output(output_text: str) -> dict[str, Any]:
    payload = json.loads(output_text)
    required = set(OUTPUT_FORMAT["schema"]["required"])
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("response does not match the exact identity-context schema")
    if payload["identity_status"] not in {"resolved", "unresolved"}:
        raise ValueError("invalid identity status")
    for field in (
        "canonical_name",
        "current_role",
        "current_organization",
        "frontier_ai_relevance",
        "research_summary",
    ):
        payload[field] = _normalize_text(payload[field], field)
    known_for = payload["known_for"]
    if not isinstance(known_for, list) or len(known_for) > 5:
        raise ValueError("known_for must be an array of at most five strings")
    payload["known_for"] = [
        _normalize_text(value, "known_for item") for value in known_for
    ]
    return payload


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


def enrich_one(
    client: Any,
    entity: IdentityInput,
    *,
    run: str,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_REASONING_EFFORT,
) -> dict[str, Any]:
    """Research one missing-bio identity without changing the source profile."""
    tags = request_tags(run=run)
    request = {
        "model": model,
        "instructions": instructions(),
        "input": render_input(entity),
        "prompt_cache_key": prompt_cache_key(entity.entity_id),
        **llm_responses.litellm_prompt_cache_kwargs(model),
        "tools": [{"type": "web_search", "search_context_size": "medium"}],
        "tool_choice": llm_responses.required_web_search_tool_choice(model),
        "include": ["web_search_call.action.sources"],
        "reasoning": {"effort": effort},
        "text": {"format": OUTPUT_FORMAT},
        "store": False,
        "extra_body": {"metadata": {"tags": list(tags)}},
        "extra_headers": {"x-litellm-tags": ",".join(tags)},
    }
    raw_api = getattr(client.responses, "with_raw_response", None)
    if raw_api is None:
        response = client.responses.create(**request)
        reported_cost = None
    else:
        raw_response = raw_api.create(**request)
        response = raw_response.parse()
        reported_cost = llm_responses.reported_cost(raw_response.headers)

    response_data = llm_responses.as_dict(response)
    if response_data.get("status") not in (None, "completed"):
        raise ValueError(
            f"response status was {response_data.get('status')!r}: "
            f"{response_data.get('incomplete_details')!r}"
        )
    payload = _validate_output(llm_responses.output_text(response_data))
    actions, sources = llm_responses.web_evidence(
        response_data, require_search_action=True
    )
    usage = getattr(response, "usage", None) or response_data.get("usage")
    return {
        **payload,
        "entity_id": entity.entity_id,
        "handle": entity.handle,
        "input_sha256": entity.input_sha256,
        "model": model,
        "reasoning_effort": effort,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "prompt_sha256": prompt_sha256(),
        "prompt_cache_key": request["prompt_cache_key"],
        "response_id": getattr(response, "id", None) or response_data.get("id"),
        "response_model": getattr(response, "model", None)
        or response_data.get("model"),
        "input_tokens": _usage_value(usage, "input_tokens"),
        "cached_tokens": _input_token_detail(usage, "cached_tokens"),
        "cache_write_tokens": _input_token_detail(usage, "cache_write_tokens"),
        "output_tokens": _usage_value(usage, "output_tokens"),
        "reported_cost_usd": reported_cost,
        "web_actions": actions,
        "consulted_sources": sources,
        "request_tags": list(tags),
    }
