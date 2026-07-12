"""One-request structural-kind and Registry-status evaluation.

This module owns the read-only model boundary. Mechanical eligibility gates and
canonical Registry mutation remain application responsibilities.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fli import llm_responses

PROMPT_VERSION = "registry-evaluation-v1"
SCHEMA_VERSION = "registry-evaluation-output-v1"
DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_REASONING_EFFORT = "high"
PROMPT_CACHE_SHARDS = llm_responses.DEFAULT_PROMPT_CACHE_SHARDS
PROMPT_PATH = Path(__file__).with_name("prompts") / "registry_evaluation_v1.txt"

KINDS = frozenset({"person", "organization", "unsure"})
REGISTRY_STATUSES = frozenset({"active", "rejected", "review"})

OUTPUT_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "name": "registry_evaluation",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": sorted(KINDS)},
            "kind_reason": {"type": "string"},
            "registry_status": {
                "type": "string",
                "enum": sorted(REGISTRY_STATUSES),
            },
            "registry_status_reason": {"type": "string"},
        },
        "required": [
            "kind",
            "kind_reason",
            "registry_status",
            "registry_status_reason",
        ],
        "additionalProperties": False,
    },
}


@dataclass(frozen=True)
class EvaluationInput:
    entity_id: int
    handle: str
    display_name: str
    bio: str | None
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
                    "bio": self.bio,
                    "profile_url": self.profile_url,
                    "recent_posts": self.recent_posts,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()


def instructions() -> str:
    """Return the exact stable prefix shared by every evaluation request."""
    return PROMPT_PATH.read_text().strip()


def prompt_sha256() -> str:
    return hashlib.sha256(instructions().encode()).hexdigest()


def prompt_cache_key(entity_id: int) -> str:
    """Use the same stable shard convention as the existing relevance audit."""
    return llm_responses.sharded_prompt_cache_key(
        namespace="registry-evaluation",
        prompt_version=PROMPT_VERSION,
        scope_key=entity_id,
        shards=PROMPT_CACHE_SHARDS,
    )


def request_tags(*, run: str) -> tuple[str, ...]:
    return (
        "app:frontier-lab-intelligence",
        "pipeline:registry-evaluation",
        "job:combined-kind-and-status",
        "scope:single-entity",
        f"prompt:{PROMPT_VERSION}",
        f"run:{run}",
    )


def render_input(entity: EvaluationInput) -> str:
    """Render variable evidence after the cacheable instruction prefix."""
    blocks = [
        "Evaluate this X account using the supplied evidence.",
        "",
        f"Handle: @{entity.handle}",
        f"Display name: {entity.display_name}",
        f"Bio: {entity.bio.strip() if entity.bio else 'No bio observed.'}",
        f"Profile: {entity.profile_url}",
        "",
        "Recent authored posts (replies and retweets excluded):",
    ]
    if not entity.recent_posts:
        blocks.append("No recent authored posts were supplied.")
    for index, post in enumerate(entity.recent_posts, start=1):
        created_at = post.get("created_at") or "date unavailable"
        post_type = post.get("post_type") or "original"
        blocks.extend(
            (
                "",
                f"Post {index} ({post_type}, {created_at}):",
                str(post.get("text") or ""),
            )
        )
    return "\n".join(blocks)


def _validate_output(output_text: str) -> dict[str, str]:
    payload = json.loads(output_text)
    required = set(OUTPUT_FORMAT["schema"]["required"])
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("response does not match the exact evaluation schema")
    if payload["kind"] not in KINDS:
        raise ValueError(f"invalid kind: {payload['kind']!r}")
    if payload["registry_status"] not in REGISTRY_STATUSES:
        raise ValueError(
            f"invalid registry status: {payload['registry_status']!r}"
        )
    if payload["kind"] == "unsure" and payload["registry_status"] == "active":
        raise ValueError("an unsure actor cannot enter the active Registry")
    for field in ("kind_reason", "registry_status_reason"):
        value = payload[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
        payload[field] = " ".join(value.split())
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


def evaluate_one(
    client: Any,
    entity: EvaluationInput,
    *,
    run: str,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_REASONING_EFFORT,
) -> dict[str, Any]:
    """Evaluate one account without mutating canonical Registry state."""
    tags = request_tags(run=run)
    request = {
        "model": model,
        "instructions": instructions(),
        "input": render_input(entity),
        "prompt_cache_key": prompt_cache_key(entity.entity_id),
        "tools": [{"type": "web_search"}],
        "tool_choice": "auto",
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
    actions, sources = llm_responses.web_evidence(response_data)
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
