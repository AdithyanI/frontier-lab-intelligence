"""Model boundary and citation verifier for ``insight-v1`` extraction.

Upstream triage has already decided that an evidence envelope is worth
investigating. This module does not repeat that gate. It asks for one useful
claim (or an explicit miss), then binds the returned quote to the frozen input
in application code. Runner-owned source identifiers never come from the
model.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fli import llm_responses


PROMPT_VERSION = "insight-v1.0"
SCHEMA_VERSION = "insight-output-v1"
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_REASONING_EFFORT = "medium"
PROMPT_CACHE_SHARDS = 1
PROMPT_PATH = Path(__file__).with_name("prompts") / "insight_extraction_v1.txt"

OUTPUT_FIELDS = (
    "outcome",
    "claim",
    "why_it_matters",
    "investment_implication",
    "engineering_implication",
    "supporting_quote",
)

OUTPUT_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "name": "cited_insight_v1",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "outcome": {
                "type": "string",
                "enum": ["insight", "no_extractable_insight"],
            },
            "claim": {"type": ["string", "null"]},
            "why_it_matters": {"type": ["string", "null"]},
            "investment_implication": {"type": ["string", "null"]},
            "engineering_implication": {"type": ["string", "null"]},
            "supporting_quote": {"type": ["string", "null"]},
        },
        "required": list(OUTPUT_FIELDS),
        "additionalProperties": False,
    },
}


@dataclass(frozen=True)
class EvidenceSource:
    source_type: str
    source_id: str
    url: str
    text: str
    author: str | None = None
    title: str | None = None
    relation: str | None = None

    def normalized_text(self) -> str:
        return unicodedata.normalize("NFC", self.text)


@dataclass(frozen=True)
class InsightInput:
    event_id: str
    day: str
    current_rank: int
    sources: tuple[EvidenceSource, ...]

    @property
    def input_sha256(self) -> str:
        return hashlib.sha256(render_input(self).encode()).hexdigest()


def instructions() -> str:
    """Return the stable cacheable prefix shared by extraction requests."""
    return PROMPT_PATH.read_text().strip()


def prompt_sha256() -> str:
    return hashlib.sha256(instructions().encode()).hexdigest()


def prompt_cache_key(scope_key: str | int) -> str:
    return llm_responses.sharded_prompt_cache_key(
        namespace="cited-insights-extraction",
        prompt_version=PROMPT_VERSION,
        scope_key=scope_key,
        shards=PROMPT_CACHE_SHARDS,
    )


def request_tags(*, run: str, day: str) -> tuple[str, ...]:
    return (
        "app:frontier-lab-intelligence",
        "pipeline:cited-insights",
        "job:insight-extraction",
        f"scope:day-{day}",
        f"prompt:{PROMPT_VERSION}",
        f"run:{run}",
    )


def render_input(packet: InsightInput) -> str:
    """Render variable evidence after the stable prompt instructions."""
    blocks = [
        "Extract one cited insight from this accepted evidence envelope.",
        "The evidence blocks are independent sources; do not merge their authorship.",
    ]
    for index, source in enumerate(packet.sources, start=1):
        label = f"EVIDENCE {index} · {source.source_type.upper()}"
        details = []
        if source.author:
            details.append(f"author={source.author}")
        if source.relation:
            details.append(f"role={source.relation}")
        if source.title:
            details.append(f"title={source.title}")
        blocks.extend(("", label, f"[{' | '.join(details)}]" if details else ""))
        blocks.append(source.normalized_text())
    return "\n".join(block for block in blocks if block != "")


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("insight output fields must be strings or null")
    cleaned = " ".join(value.split())
    return cleaned or None


def validate_output(output_text: str) -> dict[str, Any]:
    payload = json.loads(output_text)
    if not isinstance(payload, dict) or tuple(payload) != OUTPUT_FIELDS:
        if not isinstance(payload, dict) or set(payload) != set(OUTPUT_FIELDS):
            raise ValueError("response does not match the exact insight-v1 schema")
        payload = {field: payload[field] for field in OUTPUT_FIELDS}
    outcome = payload["outcome"]
    if outcome not in {"insight", "no_extractable_insight"}:
        raise ValueError(f"invalid insight outcome: {outcome!r}")
    cleaned = {
        field: _clean_optional(payload[field])
        for field in OUTPUT_FIELDS
        if field != "outcome"
    }
    if outcome == "insight" and any(cleaned[field] is None for field in cleaned):
        raise ValueError("insight outcome requires every insight-v1 text field")
    if outcome == "no_extractable_insight" and any(
        cleaned[field] is not None for field in cleaned
    ):
        raise ValueError("no_extractable_insight requires null insight fields")
    return {"outcome": outcome, **cleaned}


def bind_citation(
    packet: InsightInput, supporting_quote: str | None
) -> dict[str, Any] | None:
    """Bind one exact quote to runner-owned source provenance."""
    if supporting_quote is None:
        return None
    quote = unicodedata.normalize("NFC", supporting_quote)
    matches = [source for source in packet.sources if quote in source.normalized_text()]
    if not matches:
        raise ValueError("supporting quote is not an exact span of supplied evidence")
    source = matches[0]
    return {
        "source_type": source.source_type,
        "source_id": source.source_id,
        "source_url": source.url,
        "source_author": source.author,
        "source_title": source.title,
        "exact_quote": quote,
        "matching_source_count": len(matches),
    }


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
    packet: InsightInput,
    *,
    run: str,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_REASONING_EFFORT,
) -> dict[str, Any]:
    """Extract and application-bind one frozen evidence packet."""
    tags = request_tags(run=run, day=packet.day)
    request = {
        "model": model,
        "instructions": instructions(),
        "input": render_input(packet),
        "prompt_cache_key": prompt_cache_key(packet.event_id),
        "reasoning": {"effort": effort},
        "text": {"format": OUTPUT_FORMAT},
        "store": False,
        "extra_body": {"metadata": {"tags": list(tags)}},
        "extra_headers": {"x-litellm-tags": ",".join(tags)},
    }
    response, response_data, reported_cost = _create_response(client, request)
    payload = validate_output(llm_responses.output_text(response_data))
    citation = bind_citation(packet, payload["supporting_quote"])
    usage = getattr(response, "usage", None) or response_data.get("usage")
    return {
        **payload,
        "citation": citation,
        "event_id": packet.event_id,
        "day": packet.day,
        "current_rank": packet.current_rank,
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
