"""Audience-routing model boundary for Feed-kept evidence packets.

Feed triage has already made the general keep/drop decision. This module asks
one model call for two audience-specific relevance judgments and does not
generate Insight prose or expose ranking and provenance identifiers to the
model.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fli import audience_insights, llm_responses


PROMPT_VERSION = "audience-routing-v1"
SCHEMA_VERSION = "audience-routing-output-v1"
DEFAULT_MODEL = llm_responses.DEFAULT_EFFICIENT_MODEL
DEFAULT_REASONING_EFFORT = "medium"
PROMPT_CACHE_SHARDS = 2
PROMPT_PATH = Path(__file__).with_name("prompts") / "audience_routing_v1.txt"

AUDIENCES = ("ai_engineering", "investment")
JUDGMENT_FIELDS = ("relevant", "reason")

_JUDGMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "relevant": {"type": "boolean"},
        "reason": {"type": "string", "minLength": 1},
    },
    "required": list(JUDGMENT_FIELDS),
    "additionalProperties": False,
}

OUTPUT_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "name": "audience_routing_v1",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            audience: _JUDGMENT_SCHEMA for audience in AUDIENCES
        },
        "required": list(AUDIENCES),
        "additionalProperties": False,
    },
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class RoutingPacket:
    """One immutable Evidence packet presented to the audience router."""

    event_id: str
    day: str
    sources: tuple[audience_insights.EvidenceSource, ...]

    @property
    def evidence_sha256(self) -> str:
        """Hash exact evidence and runner-owned provenance, not the prompt view."""
        payload = {
            "event_id": self.event_id,
            "day": self.day,
            "sources": [
                {
                    "source_type": source.source_type,
                    "source_id": source.source_id,
                    "url": source.url,
                    "text": source.normalized_text(),
                    "author": source.author,
                    "title": source.title,
                    "relation": source.relation,
                    "source_sha256": source.effective_source_sha256(),
                    "section_ordinal": source.section_ordinal,
                    "source_char_start": source.source_char_start,
                    "source_char_end": source.source_char_end,
                }
                for source in self.sources
            ],
        }
        return _sha256(_canonical_json(payload))

    @property
    def input_sha256(self) -> str:
        """Hash the exact variable model input."""
        return _sha256(render_input(self))


def instructions() -> str:
    """Return the stable cacheable prefix shared across routing requests."""
    return PROMPT_PATH.read_text().strip()


def prompt_sha256() -> str:
    return _sha256(instructions())


def prompt_cache_key(scope_key: str | int) -> str:
    """Route calls over a small stable set of cache lanes for the first cohort."""
    return llm_responses.sharded_prompt_cache_key(
        namespace="audience-routing",
        prompt_version=PROMPT_VERSION,
        scope_key=scope_key,
        shards=PROMPT_CACHE_SHARDS,
    )


def request_tags(*, run: str, day: str) -> tuple[str, ...]:
    return (
        "app:frontier-lab-intelligence",
        "pipeline:audience-routing",
        "job:audience-routing",
        f"scope:day-{day}",
        f"prompt:{PROMPT_VERSION}",
        f"run:{run}",
    )


def render_input(packet: RoutingPacket) -> str:
    """Render attributed sources without IDs, URLs, rank, or triage outcome."""
    blocks = [
        "Route this Feed-kept evidence packet by audience.",
        "Judge each numbered source independently before judging the full packet.",
    ]
    for index, source in enumerate(packet.sources, start=1):
        details = [f"type={source.source_type}"]
        if source.author:
            details.append(f"author={source.author}")
        if source.relation:
            details.append(f"relation={source.relation}")
        if source.title:
            details.append(f"title={source.title}")
        blocks.extend(
            (
                "",
                f'<EVIDENCE_BLOCK index="{index}">',
                f"[{' | '.join(details)}]",
                "<VERBATIM_TEXT>",
                source.normalized_text(),
                "</VERBATIM_TEXT>",
                "</EVIDENCE_BLOCK>",
            )
        )
    return "\n".join(blocks)


def _validate_output(output_text: str) -> dict[str, Any]:
    payload = json.loads(output_text)
    if not isinstance(payload, dict) or set(payload) != set(AUDIENCES):
        raise ValueError("response does not match the exact audience-routing schema")

    validated: dict[str, Any] = {}
    for audience in AUDIENCES:
        judgment = payload[audience]
        if not isinstance(judgment, dict) or set(judgment) != set(JUDGMENT_FIELDS):
            raise ValueError(
                "response does not match the exact audience-routing schema"
            )
        relevant = judgment["relevant"]
        if not isinstance(relevant, bool):
            raise ValueError(f"{audience}.relevant must be a boolean")
        reason = judgment["reason"]
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"{audience}.reason must be a non-empty string")
        validated[audience] = {
            "relevant": relevant,
            "reason": " ".join(reason.split()),
        }
    return validated


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
    return response, response_data, reported_cost


def evaluate_one(
    client: Any,
    packet: RoutingPacket,
    *,
    run: str,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_REASONING_EFFORT,
) -> dict[str, Any]:
    """Route one frozen packet without tools or canonical-state mutation."""
    tags = request_tags(run=run, day=packet.day)
    request = {
        "model": model,
        "instructions": instructions(),
        "input": render_input(packet),
        "prompt_cache_key": prompt_cache_key(packet.event_id),
        **llm_responses.litellm_prompt_cache_kwargs(model),
        "reasoning": {"effort": effort},
        "text": {"format": OUTPUT_FORMAT},
        "store": False,
        "extra_body": {"metadata": {"tags": list(tags)}},
        "extra_headers": {"x-litellm-tags": ",".join(tags)},
    }
    response, response_data, reported_cost = _create_response(client, request)
    raw_output_text = llm_responses.output_text(response_data)
    payload = _validate_output(raw_output_text)
    usage = getattr(response, "usage", None) or response_data.get("usage")
    return {
        **payload,
        "raw_output_text": raw_output_text,
        "event_id": packet.event_id,
        "day": packet.day,
        "evidence_sha256": packet.evidence_sha256,
        "input_sha256": packet.input_sha256,
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
        "request_tags": list(tags),
    }
