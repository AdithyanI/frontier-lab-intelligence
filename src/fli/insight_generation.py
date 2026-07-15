"""Prompt and schema boundary for the successor audience Insight stage.

This module deliberately stops before model execution or run storage. It owns
the two audience prompt contracts, the shared structured output, the exact
Evidence input view, and deterministic application validation. A later runner
can load one positively routed envelope and call ``build_request`` without
reviving the superseded multi-stage Insight stack.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from fli import audience_routing, llm_responses


SCHEMA_VERSION = "audience-insight-output-v1"
MAX_OUTPUT_TOKENS = 4_096
_PROMPT_ROOT = Path(__file__).with_name("prompts")
_OUTPUT_FIELDS = (
    "decision",
    "suppression_reason",
    "summary",
    "implication",
    "next_step",
)


class InsightAudience(StrEnum):
    INVESTMENT = "investment"
    AI_ENGINEERING = "ai_engineering"


class InsightDecision(StrEnum):
    SURFACE = "surface"
    SUPPRESS = "suppress"


@dataclass(frozen=True)
class PromptContract:
    audience: InsightAudience
    version: str
    path: Path
    cache_key: str

    def instructions(self) -> str:
        return self.path.read_text(encoding="utf-8").strip()

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.instructions().encode()).hexdigest()


PROMPT_CONTRACTS = {
    InsightAudience.INVESTMENT: PromptContract(
        audience=InsightAudience.INVESTMENT,
        version="investment-insight-v1",
        path=_PROMPT_ROOT / "investment_insight_v1.txt",
        cache_key="fli:insights:investment:v1",
    ),
    InsightAudience.AI_ENGINEERING: PromptContract(
        audience=InsightAudience.AI_ENGINEERING,
        version="ai-engineering-insight-v1",
        path=_PROMPT_ROOT / "ai_engineering_insight_v1.txt",
        cache_key="fli:insights:ai-engineering:v1",
    ),
}


OUTPUT_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "name": "audience_insight_v1",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "decision": {
                "type": "string",
                "enum": [decision.value for decision in InsightDecision],
            },
            "suppression_reason": {"type": ["string", "null"]},
            "summary": {"type": ["string", "null"]},
            "implication": {"type": ["string", "null"]},
            "next_step": {"type": ["string", "null"]},
        },
        "required": list(_OUTPUT_FIELDS),
        "additionalProperties": False,
    },
}


@dataclass(frozen=True)
class InsightCandidate:
    """One audience decision over one immutable routed Evidence packet."""

    audience: InsightAudience
    packet: audience_routing.RoutingPacket
    feed_rank: int

    @classmethod
    def create(
        cls,
        *,
        audience: str | InsightAudience,
        packet: audience_routing.RoutingPacket,
        feed_rank: int,
    ) -> "InsightCandidate":
        if feed_rank < 1:
            raise ValueError("feed_rank must be a positive integer")
        return cls(
            audience=require_audience(audience),
            packet=packet,
            feed_rank=feed_rank,
        )

    @property
    def candidate_id(self) -> str:
        value = f"{self.audience.value}:{self.packet.day}:{self.packet.event_id}"
        return hashlib.sha256(value.encode()).hexdigest()

    @property
    def input_sha256(self) -> str:
        return hashlib.sha256(render_input(self).encode()).hexdigest()


@dataclass(frozen=True)
class InsightResult:
    decision: InsightDecision
    suppression_reason: str | None
    summary: str | None
    implication: str | None
    next_step: str | None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "decision": self.decision.value,
            "suppression_reason": self.suppression_reason,
            "summary": self.summary,
            "implication": self.implication,
            "next_step": self.next_step,
        }


@dataclass(frozen=True)
class PublishedInsight:
    """Application-owned UI projection for one surfaced model result.

    Feed identity and rank come from the frozen routing candidate, never from
    model output. The successor contract deliberately carries no quotation.
    """

    candidate_id: str
    event_id: str
    day: str
    audience: InsightAudience
    feed_rank: int
    summary: str
    implication: str
    next_step: str

    def as_dict(self) -> dict[str, str | int]:
        return {
            "candidate_id": self.candidate_id,
            "event_id": self.event_id,
            "day": self.day,
            "audience": self.audience.value,
            "feed_rank": self.feed_rank,
            "summary": self.summary,
            "implication": self.implication,
            "next_step": self.next_step,
        }


def require_audience(value: str | InsightAudience) -> InsightAudience:
    try:
        return InsightAudience(value)
    except ValueError as error:
        raise ValueError(f"unsupported Insight audience: {value!r}") from error


def contract(audience: str | InsightAudience) -> PromptContract:
    return PROMPT_CONTRACTS[require_audience(audience)]


def render_input(candidate: InsightCandidate) -> str:
    """Put the changing Evidence packet after the stable prompt prefix."""
    packet = audience_routing.render_input(candidate.packet)
    return f"<candidate_evidence>\n{packet}\n</candidate_evidence>"


def request_tags(
    *, candidate: InsightCandidate, run: str
) -> tuple[str, ...]:
    prompt = contract(candidate.audience)
    return (
        "app:frontier-lab-intelligence",
        "pipeline:insights",
        "job:audience-insight",
        f"audience:{candidate.audience.value}",
        f"scope:day-{candidate.packet.day}",
        f"prompt:{prompt.version}",
        f"run:{run}",
    )


def build_request(
    candidate: InsightCandidate,
    *,
    model: str,
    effort: str,
    run: str,
) -> dict[str, Any]:
    """Build but do not execute one Responses API request."""
    prompt = contract(candidate.audience)
    tags = request_tags(candidate=candidate, run=run)
    return {
        "model": model,
        "instructions": prompt.instructions(),
        "input": render_input(candidate),
        "prompt_cache_key": prompt.cache_key,
        **llm_responses.litellm_prompt_cache_kwargs(model),
        "reasoning": {"effort": effort},
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "text": {"format": OUTPUT_FORMAT},
        "store": False,
        "extra_body": {"metadata": {"tags": list(tags)}},
        "extra_headers": {"x-litellm-tags": ",".join(tags)},
    }


def _clean_optional(value: Any, *, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string or null")
    cleaned = " ".join(value.split())
    return cleaned or None


def validate_output(output: str | dict[str, Any]) -> InsightResult:
    """Validate schema shape plus the surface/suppress cross-field contract."""
    payload = json.loads(output) if isinstance(output, str) else output
    if not isinstance(payload, dict) or set(payload) != set(_OUTPUT_FIELDS):
        raise ValueError("response does not match the exact Insight schema")
    try:
        decision = InsightDecision(payload["decision"])
    except (TypeError, ValueError) as error:
        raise ValueError("decision must be surface or suppress") from error

    values = {
        field: _clean_optional(payload[field], field=field)
        for field in _OUTPUT_FIELDS
        if field != "decision"
    }
    content = (values["summary"], values["implication"], values["next_step"])
    if decision is InsightDecision.SURFACE:
        if values["suppression_reason"] is not None:
            raise ValueError("surface requires a null suppression_reason")
        if any(value is None for value in content):
            raise ValueError("surface requires summary, implication, and next_step")
    else:
        if values["suppression_reason"] is None:
            raise ValueError("suppress requires a concrete suppression_reason")
        if any(value is not None for value in content):
            raise ValueError("suppress requires null audience content fields")

    return InsightResult(decision=decision, **values)


def publish(candidate: InsightCandidate, result: InsightResult) -> PublishedInsight:
    """Bind a surfaced result to immutable UI metadata without a model quote."""
    if result.decision is not InsightDecision.SURFACE:
        raise ValueError("suppressed results cannot be published")
    assert result.summary is not None
    assert result.implication is not None
    assert result.next_step is not None
    return PublishedInsight(
        candidate_id=candidate.candidate_id,
        event_id=candidate.packet.event_id,
        day=candidate.packet.day,
        audience=candidate.audience,
        feed_rank=candidate.feed_rank,
        summary=result.summary,
        implication=result.implication,
        next_step=result.next_step,
    )
