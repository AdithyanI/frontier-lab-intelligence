"""Audience-specific cited insight extraction and daily editorial boundaries.

The two audience products share frozen evidence but never share one compromise
model output. Models select a numbered evidence block and an exact quotation;
application code owns source identity, provenance, offsets, and publication
eligibility. Daily editors return runner-owned IDs only and cannot rewrite a
candidate.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fli import llm_responses


INVESTMENT = "investment"
AI_ENGINEERING = "ai_engineering"
AUDIENCES = frozenset({INVESTMENT, AI_ENGINEERING})

DEFAULT_MODEL = llm_responses.DEFAULT_EFFICIENT_MODEL
AUDIENCE_EXTRACTION_REASONING_EFFORTS = {
    INVESTMENT: "high",
    AI_ENGINEERING: "medium",
}
# The generic alias remains the conservative direct-call default for callers
# that do not own an audience boundary. Audience runs resolve through
# ``default_extraction_effort`` instead.
DEFAULT_EXTRACTION_REASONING_EFFORT = "medium"
DEFAULT_EDITOR_REASONING_EFFORT = "high"
# Stable public names used by the run-store boundary.
DEFAULT_EXTRACTION_EFFORT = DEFAULT_EXTRACTION_REASONING_EFFORT
DEFAULT_EDITOR_EFFORT = DEFAULT_EDITOR_REASONING_EFFORT
EXTRACTION_PROMPT_CACHE_SHARDS = 32
EDITOR_PROMPT_CACHE_SHARDS = 1

INPUT_RENDER_VERBATIM_V1 = "verbatim-v1"
INPUT_RENDER_PROVIDER_SAFE_V2 = "provider-safe-v2"
INPUT_RENDER_CITATION_SAFE_V3 = "citation-safe-v3"
INPUT_RENDER_VERSIONS = (
    INPUT_RENDER_VERBATIM_V1,
    INPUT_RENDER_PROVIDER_SAFE_V2,
    INPUT_RENDER_CITATION_SAFE_V3,
)
DEFAULT_INPUT_RENDER_VERSION = INPUT_RENDER_PROVIDER_SAFE_V2

# Nova can return a completed, empty, zero-token response for otherwise valid
# evidence packets containing this expletive. Keep the source packet exact and
# normalize only the provider-safe model transcription. Citation binding still
# runs against the original packet, so a quote spanning the marker fails closed.
_MODEL_INPUT_EXPLETIVE = re.compile(r"\bfucking\b", flags=re.IGNORECASE)
_MODEL_INPUT_EXPLETIVE_MARKER = "[EXPLETIVE]"

EXTRACTION_PROMPT_VERSIONS = {
    INVESTMENT: "investment-insight-v2.2",
    AI_ENGINEERING: "ai-engineering-insight-v2.2",
}
EXTRACTION_SCHEMA_VERSIONS = {
    INVESTMENT: "investment-insight-output-v2",
    AI_ENGINEERING: "ai-engineering-insight-output-v2",
}
EDITOR_PROMPT_VERSIONS = {
    INVESTMENT: "investment-daily-editor-v2.1",
    AI_ENGINEERING: "ai-engineering-daily-editor-v2.4",
}
EDITOR_SCHEMA_VERSION = "audience-daily-editor-output-v2"

_PROMPT_ROOT = Path(__file__).with_name("prompts")
EXTRACTION_PROMPT_PATHS = {
    INVESTMENT: _PROMPT_ROOT / "investment_insight_v2.txt",
    AI_ENGINEERING: _PROMPT_ROOT / "ai_engineering_insight_v2.txt",
}
EDITOR_PROMPT_PATHS = {
    INVESTMENT: _PROMPT_ROOT / "investment_daily_editor_v2.txt",
    AI_ENGINEERING: _PROMPT_ROOT / "ai_engineering_daily_editor_v2.txt",
}

NO_INSIGHT_REASONS = (
    "no_audience_decision_value",
    "insufficiently_concrete",
    "missing_required_evidence",
    "ambiguous_attribution",
    "unsupported_inference_required",
)
CLAIM_POSTURES = (
    "directly_documented",
    "first_party_report",
    "third_party_observation",
    "opinion_or_forecast",
)
ENGINEERING_ACTION_TYPES = (
    "investigate",
    "reproduce",
    "benchmark",
    "prototype",
    "regression_test",
    "monitor",
)
INVESTMENT_DECISION_VALUES = (
    "thesis_or_model",
    "watchlist_or_exposure",
    "diligence_question",
    "execution_or_competitive_risk",
)
ENGINEERING_DECISION_VALUES = (
    "experiment_or_benchmark",
    "implementation_choice",
    "regression_or_reliability",
    "research_or_tooling_watch",
)

INVESTMENT_OUTPUT_FIELDS = (
    "outcome",
    "no_insight_reason",
    "claim",
    "claim_posture",
    "why_it_matters",
    "investment_implication",
    "what_to_watch",
    "supporting_quote",
    "citation_block_index",
)
ENGINEERING_OUTPUT_FIELDS = (
    "outcome",
    "no_insight_reason",
    "claim",
    "claim_posture",
    "why_it_matters",
    "action_type",
    "engineering_action",
    "validation_boundary",
    "supporting_quote",
    "citation_block_index",
)

_COMMON_EXTRACTION_PROPERTIES: dict[str, Any] = {
    "outcome": {
        "type": "string",
        "enum": ["insight", "no_extractable_insight"],
    },
    "no_insight_reason": {
        "type": ["string", "null"],
        "enum": [None, *NO_INSIGHT_REASONS],
    },
    "claim": {"type": ["string", "null"]},
    "claim_posture": {
        "type": ["string", "null"],
        "enum": [None, *CLAIM_POSTURES],
    },
    "why_it_matters": {"type": ["string", "null"]},
    "supporting_quote": {"type": ["string", "null"]},
    "citation_block_index": {
        "type": ["integer", "null"],
        "minimum": 1,
    },
}


def _extraction_format(
    *, name: str, fields: tuple[str, ...], properties: dict[str, Any]
) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": name,
        "strict": True,
        "schema": {
            "type": "object",
            "properties": properties,
            "required": list(fields),
            "additionalProperties": False,
        },
    }


INVESTMENT_OUTPUT_FORMAT = _extraction_format(
    name="investment_cited_insight_v2",
    fields=INVESTMENT_OUTPUT_FIELDS,
    properties={
        **_COMMON_EXTRACTION_PROPERTIES,
        "investment_implication": {"type": ["string", "null"]},
        "what_to_watch": {"type": ["string", "null"]},
    },
)
ENGINEERING_OUTPUT_FORMAT = _extraction_format(
    name="ai_engineering_cited_insight_v2",
    fields=ENGINEERING_OUTPUT_FIELDS,
    properties={
        **_COMMON_EXTRACTION_PROPERTIES,
        "action_type": {
            "type": ["string", "null"],
            "enum": [None, *ENGINEERING_ACTION_TYPES],
        },
        "engineering_action": {"type": ["string", "null"]},
        "validation_boundary": {"type": ["string", "null"]},
    },
)
EXTRACTION_OUTPUT_FORMATS = {
    INVESTMENT: INVESTMENT_OUTPUT_FORMAT,
    AI_ENGINEERING: ENGINEERING_OUTPUT_FORMAT,
}


def _editor_format(audience: str) -> dict[str, Any]:
    decision_values = (
        INVESTMENT_DECISION_VALUES
        if audience == INVESTMENT
        else ENGINEERING_DECISION_VALUES
    )
    selected_item = {
        "type": "object",
        "properties": {
            "candidate_id": {"type": "string"},
            "decision_value": {"type": "string", "enum": list(decision_values)},
            "audit_reason": {"type": "string"},
            "updates_prior_id": {"type": ["string", "null"]},
        },
        "required": [
            "candidate_id",
            "decision_value",
            "audit_reason",
            "updates_prior_id",
        ],
        "additionalProperties": False,
    }
    duplicate_item = {
        "type": "object",
        "properties": {
            "candidate_id": {"type": "string"},
            "duplicate_of_id": {"type": "string"},
            "duplicate_scope": {
                "type": "string",
                "enum": ["same_day", "cross_day"],
            },
            "audit_reason": {"type": "string"},
        },
        "required": [
            "candidate_id",
            "duplicate_of_id",
            "duplicate_scope",
            "audit_reason",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "json_schema",
        "name": (
            "investment_daily_editor_v2"
            if audience == INVESTMENT
            else "ai_engineering_daily_editor_v2"
        ),
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "selected": {
                    "type": "array",
                    "items": selected_item,
                    "maxItems": 5,
                },
                "suppressed_duplicates": {
                    "type": "array",
                    "items": duplicate_item,
                },
                "thin_day_reason": {"type": ["string", "null"]},
            },
            "required": [
                "selected",
                "suppressed_duplicates",
                "thin_day_reason",
            ],
            "additionalProperties": False,
        },
    }


EDITOR_OUTPUT_FORMATS = {
    INVESTMENT: _editor_format(INVESTMENT),
    AI_ENGINEERING: _editor_format(AI_ENGINEERING),
}


@dataclass(frozen=True)
class AudienceContract:
    audience: str
    prompt_version: str
    schema_version: str
    editor_prompt_version: str


CONTRACTS = {
    audience: AudienceContract(
        audience=audience,
        prompt_version=EXTRACTION_PROMPT_VERSIONS[audience],
        schema_version=EXTRACTION_SCHEMA_VERSIONS[audience],
        editor_prompt_version=EDITOR_PROMPT_VERSIONS[audience],
    )
    for audience in sorted(AUDIENCES)
}


class CitationVerificationError(ValueError):
    """An extraction result whose quote did not bind to frozen evidence."""

    def __init__(self, message: str, *, result: dict[str, Any]):
        super().__init__(message)
        self.result = result


class ExtractionValidationError(ValueError):
    """A completed extraction response that violated the frozen schema."""

    def __init__(self, message: str, *, result: dict[str, Any]):
        super().__init__(message)
        self.result = result


@dataclass(frozen=True)
class EvidenceSource:
    source_type: str
    source_id: str
    url: str
    text: str
    author: str | None = None
    title: str | None = None
    relation: str | None = None
    source_sha256: str | None = None
    section_ordinal: int | None = None
    source_char_start: int | None = None
    source_char_end: int | None = None

    def normalized_text(self) -> str:
        return unicodedata.normalize("NFC", self.text)

    def effective_source_sha256(self) -> str:
        return self.source_sha256 or hashlib.sha256(
            self.normalized_text().encode()
        ).hexdigest()


@dataclass(frozen=True)
class EvidencePacket:
    event_id: str
    day: str
    feed_rank: int
    sources: tuple[EvidenceSource, ...]

    @property
    def evidence_sha256(self) -> str:
        payload = {
            "event_id": self.event_id,
            "day": self.day,
            "feed_rank": self.feed_rank,
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
        return _sha256(render_input(self))


@dataclass(frozen=True)
class EditorCandidate:
    candidate_id: str
    claim: str
    claim_posture: str
    why_it_matters: str
    audience_fields: dict[str, str]
    source_type: str
    source_author: str | None = None
    source_title: str | None = None


@dataclass(frozen=True)
class PriorSelection:
    selected_item_id: str
    day: str
    claim: str
    audience_fields: dict[str, str]
    source_author: str | None = None
    source_title: str | None = None


@dataclass(frozen=True)
class AudienceEditorInput:
    audience: str
    day: str
    candidates: tuple[EditorCandidate | dict[str, Any], ...]
    prior_selected: tuple[PriorSelection | dict[str, Any], ...]
    candidate_set_sha256: str = ""
    history_sha256: str = ""
    target_min: int = 3
    target_max: int = 5

    @property
    def input_sha256(self) -> str:
        return _sha256(render_editor_input(self))


# The runner-facing name is intentionally terse; the longer name remains useful
# in type annotations where several input boundaries are in view.
EditorInput = AudienceEditorInput


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _require_audience(audience: str) -> str:
    if audience not in AUDIENCES:
        raise ValueError(f"invalid audience: {audience!r}")
    return audience


def require_audience(audience: str) -> str:
    return _require_audience(audience)


def default_extraction_effort(audience: str) -> str:
    """Return the frozen production extraction effort for one audience."""
    return AUDIENCE_EXTRACTION_REASONING_EFFORTS[_require_audience(audience)]


def require_input_render_version(version: str) -> str:
    if version not in INPUT_RENDER_VERSIONS:
        raise ValueError(f"invalid input render version: {version!r}")
    return version


def _cache_audience_segment(audience: str) -> str:
    return "investment" if audience == INVESTMENT else "engineering"


def contract(audience: str) -> AudienceContract:
    return CONTRACTS[_require_audience(audience)]


def prompt_version(audience: str) -> str:
    return EXTRACTION_PROMPT_VERSIONS[_require_audience(audience)]


def schema_version(audience: str) -> str:
    return EXTRACTION_SCHEMA_VERSIONS[_require_audience(audience)]


def output_format(audience: str) -> dict[str, Any]:
    return EXTRACTION_OUTPUT_FORMATS[_require_audience(audience)]


def instructions(audience: str) -> str:
    return EXTRACTION_PROMPT_PATHS[_require_audience(audience)].read_text().strip()


def prompt_sha256(audience: str) -> str:
    return _sha256(instructions(audience))


def prompt_cache_key(audience: str, scope_key: str | int) -> str:
    audience = _require_audience(audience)
    return llm_responses.sharded_prompt_cache_key(
        namespace=f"audience-insights-v2-{_cache_audience_segment(audience)}-extraction",
        prompt_version=prompt_version(audience),
        scope_key=scope_key,
        shards=EXTRACTION_PROMPT_CACHE_SHARDS,
    )


def editor_prompt_version(audience: str) -> str:
    return EDITOR_PROMPT_VERSIONS[_require_audience(audience)]


def editor_schema_version(audience: str) -> str:
    _require_audience(audience)
    return EDITOR_SCHEMA_VERSION


def editor_output_format(audience: str) -> dict[str, Any]:
    return EDITOR_OUTPUT_FORMATS[_require_audience(audience)]


def editor_instructions(audience: str) -> str:
    return EDITOR_PROMPT_PATHS[_require_audience(audience)].read_text().strip()


def editor_prompt_sha256(audience: str) -> str:
    return _sha256(editor_instructions(audience))


def editor_prompt_cache_key(audience: str, scope_key: str | int) -> str:
    audience = _require_audience(audience)
    return llm_responses.sharded_prompt_cache_key(
        namespace=f"audience-insights-v2-{_cache_audience_segment(audience)}-editor",
        prompt_version=editor_prompt_version(audience),
        scope_key=scope_key,
        shards=EDITOR_PROMPT_CACHE_SHARDS,
    )


def request_tags(
    *, audience: str, job: str, run: str, day: str, version: str
) -> tuple[str, ...]:
    audience = _require_audience(audience)
    if job not in {"insight-extraction", "daily-editor"}:
        raise ValueError(f"invalid audience-insights job: {job!r}")
    return (
        "app:frontier-lab-intelligence",
        "pipeline:audience-insights",
        f"audience:{audience.replace('_', '-')}",
        f"job:{job}",
        f"scope:day-{day}",
        f"prompt:{version}",
        f"run:{run}",
    )


def render_input(packet: EvidencePacket) -> str:
    """Render legacy verbatim input without runner IDs, URLs, rank, or popularity."""
    return render_model_input(packet, version=INPUT_RENDER_VERBATIM_V1)


def render_model_input(packet: EvidencePacket, *, version: str) -> str:
    """Render one explicitly versioned, deterministic model-input transcription."""
    version = require_input_render_version(version)
    if not packet.sources:
        raise ValueError("evidence packet must contain at least one source")
    blocks = [
        "Evaluate this accepted evidence packet for the audience in the instructions.",
        "Each numbered block has independent authorship. Return the one-based block index for the exact quote.",
    ]
    if version == INPUT_RENDER_CITATION_SAFE_V3:
        blocks.append(
            "Citation-safe mode: supporting_quote must be one contiguous, "
            "character-for-character substring copied from one VERBATIM_TEXT "
            "block. Similar sentences are not interchangeable: never splice, "
            "merge, or paraphrase them. Narrow the claim or return "
            "no_extractable_insight if one exact span cannot support it."
        )
    for block_index, source in enumerate(packet.sources, start=1):
        source_text = source.normalized_text()
        if version in {
            INPUT_RENDER_PROVIDER_SAFE_V2,
            INPUT_RENDER_CITATION_SAFE_V3,
        }:
            source_text = _MODEL_INPUT_EXPLETIVE.sub(
                _MODEL_INPUT_EXPLETIVE_MARKER,
                source_text,
            )
        details = []
        if source.author:
            details.append(f"author={source.author}")
        if source.relation:
            details.append(f"role={source.relation}")
        if source.title:
            details.append(f"title={source.title}")
        if source.section_ordinal is not None:
            details.append(f"section={source.section_ordinal}")
        blocks.extend(
            (
                "",
                f'<EVIDENCE_BLOCK index="{block_index}" type="{source.source_type.upper()}">',
                f"[{' | '.join(details)}]" if details else "",
                "<VERBATIM_TEXT>",
                source_text,
                "</VERBATIM_TEXT>",
                "</EVIDENCE_BLOCK>",
            )
        )
    if version == INPUT_RENDER_CITATION_SAFE_V3:
        blocks.extend(
            (
                "",
                "<FINAL_CITATION_CHECK>",
                "Before returning, search the chosen VERBATIM_TEXT for the "
                "complete supporting_quote. If it is not present exactly once "
                "as one contiguous span, do not return that insight.",
                "</FINAL_CITATION_CHECK>",
            )
        )
    return "\n".join(block for block in blocks if block != "")


def _clean_prose(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return " ".join(value.split())


def validate_extraction_output(audience: str, output_text: str) -> dict[str, Any]:
    audience = _require_audience(audience)
    fields = (
        INVESTMENT_OUTPUT_FIELDS
        if audience == INVESTMENT
        else ENGINEERING_OUTPUT_FIELDS
    )
    payload = json.loads(output_text)
    if not isinstance(payload, dict) or set(payload) != set(fields):
        raise ValueError("response does not match the exact audience insight schema")

    outcome = payload["outcome"]
    if outcome not in {"insight", "no_extractable_insight"}:
        raise ValueError(f"invalid insight outcome: {outcome!r}")

    if outcome == "no_extractable_insight":
        if payload["no_insight_reason"] not in NO_INSIGHT_REASONS:
            raise ValueError("no_extractable_insight requires one valid reason")
        populated = [
            field
            for field in fields
            if field not in {"outcome", "no_insight_reason"}
            and payload[field] is not None
        ]
        if populated:
            raise ValueError(
                "no_extractable_insight requires null audience fields: "
                + ", ".join(populated)
            )
        return {field: payload[field] for field in fields}

    if payload["no_insight_reason"] is not None:
        raise ValueError("insight outcome requires a null no_insight_reason")
    if payload["claim_posture"] not in CLAIM_POSTURES:
        raise ValueError("insight outcome requires one valid claim_posture")
    block_index = payload["citation_block_index"]
    if isinstance(block_index, bool) or not isinstance(block_index, int) or block_index < 1:
        raise ValueError("insight outcome requires a positive citation_block_index")
    quote = payload["supporting_quote"]
    if not isinstance(quote, str) or not quote.strip():
        raise ValueError("insight outcome requires a non-empty supporting_quote")

    prose_fields = ["claim", "why_it_matters"]
    if audience == INVESTMENT:
        prose_fields.extend(("investment_implication", "what_to_watch"))
    else:
        if payload["action_type"] not in ENGINEERING_ACTION_TYPES:
            raise ValueError("engineering insight requires one valid action_type")
        prose_fields.extend(("engineering_action", "validation_boundary"))
    for field in prose_fields:
        payload[field] = _clean_prose(payload[field], field=field)

    # Deliberately do not strip or collapse this field. Citation matching owns it.
    payload["supporting_quote"] = quote
    return {field: payload[field] for field in fields}


def bind_citation(
    packet: EvidencePacket,
    citation_block_index: int | None,
    supporting_quote: str | None,
) -> dict[str, Any] | None:
    """Bind a block-selected exact quote to runner-owned immutable provenance."""
    if citation_block_index is None and supporting_quote is None:
        return None
    if isinstance(citation_block_index, bool) or not isinstance(
        citation_block_index, int
    ):
        raise ValueError("citation block index must be an integer")
    if citation_block_index < 1 or citation_block_index > len(packet.sources):
        raise ValueError("citation block index is outside the evidence packet")
    if not isinstance(supporting_quote, str) or not supporting_quote.strip():
        raise ValueError("supporting quote must be a non-empty string")

    quote = unicodedata.normalize("NFC", supporting_quote)
    source = packet.sources[citation_block_index - 1]
    selected_text = source.normalized_text()
    occurrence_count = selected_text.count(quote)
    if occurrence_count == 0:
        raise ValueError("supporting quote is not an exact span of the selected block")
    if occurrence_count != 1:
        raise ValueError("supporting quote is not unique inside the selected block")
    if not source.url:
        raise ValueError("selected citation source has no URL")

    local_start = selected_text.index(quote)
    local_end = local_start + len(quote)
    base = source.source_char_start or 0
    source_start = base + local_start
    source_end = base + local_end
    if source.source_char_end is not None and source_end > source.source_char_end:
        raise ValueError("citation offsets exceed the selected source section")
    matching_blocks = sum(
        quote in candidate.normalized_text() for candidate in packet.sources
    )
    return {
        "citation_block_index": citation_block_index,
        "source_type": source.source_type,
        "source_id": source.source_id,
        "source_url": source.url,
        "source_author": source.author,
        "source_title": source.title,
        "source_relation": source.relation,
        "source_sha256": source.effective_source_sha256(),
        "section_ordinal": source.section_ordinal,
        "char_start": source_start,
        "char_end": source_end,
        "exact_quote": supporting_quote,
        "global_matching_block_count": matching_blocks,
    }


def _expected_audience_fields(audience: str) -> set[str]:
    return (
        {"investment_implication", "what_to_watch"}
        if audience == INVESTMENT
        else {"action_type", "engineering_action", "validation_boundary"}
    )


def _candidate_payload(item: EditorCandidate | dict[str, Any]) -> dict[str, Any]:
    if isinstance(item, EditorCandidate):
        return {
            "candidate_id": item.candidate_id,
            "claim": item.claim,
            "claim_posture": item.claim_posture,
            "why_it_matters": item.why_it_matters,
            "audience_fields": item.audience_fields,
            "source_type": item.source_type,
            "source_author": item.source_author,
            "source_title": item.source_title,
        }
    if not isinstance(item, dict):
        raise ValueError("daily editor candidate must be an object")
    required = {
        "candidate_id",
        "claim",
        "claim_posture",
        "why_it_matters",
        "audience_fields",
        "source_type",
        "source_author",
        "source_title",
    }
    if set(item) != required:
        raise ValueError("daily editor candidate has unexpected fields")
    return dict(item)


def _prior_payload(item: PriorSelection | dict[str, Any]) -> dict[str, Any]:
    if isinstance(item, PriorSelection):
        return {
            "selected_item_id": item.selected_item_id,
            "day": item.day,
            "claim": item.claim,
            "audience_fields": item.audience_fields,
            "source_author": item.source_author,
            "source_title": item.source_title,
        }
    if not isinstance(item, dict):
        raise ValueError("prior selection must be an object")
    required = {
        "selected_item_id",
        "day",
        "claim",
        "audience_fields",
        "source_author",
        "source_title",
    }
    if set(item) != required:
        raise ValueError("prior selection has unexpected fields")
    return dict(item)


def _candidate_rows(editor_input: AudienceEditorInput) -> list[dict[str, Any]]:
    return [_candidate_payload(item) for item in editor_input.candidates]


def _prior_rows(editor_input: AudienceEditorInput) -> list[dict[str, Any]]:
    return [_prior_payload(item) for item in editor_input.prior_selected]


def _candidate_set_sha256(editor_input: AudienceEditorInput) -> str:
    return editor_input.candidate_set_sha256 or _sha256(
        _canonical_json(sorted(_candidate_rows(editor_input), key=lambda item: item["candidate_id"]))
    )


def _history_sha256(editor_input: AudienceEditorInput) -> str:
    return editor_input.history_sha256 or _sha256(
        _canonical_json(
            sorted(
                _prior_rows(editor_input),
                key=lambda item: (item["day"], item["selected_item_id"]),
            )
        )
    )


def _validate_editor_input(editor_input: AudienceEditorInput) -> None:
    audience = _require_audience(editor_input.audience)
    if editor_input.target_min != 3 or editor_input.target_max != 5:
        raise ValueError("daily editor target must remain 3 to 5")
    expected_fields = _expected_audience_fields(audience)
    candidate_ids: set[str] = set()
    for candidate in _candidate_rows(editor_input):
        candidate_id = candidate["candidate_id"]
        if not candidate_id or candidate_id in candidate_ids:
            raise ValueError("daily editor candidate IDs must be non-empty and unique")
        candidate_ids.add(candidate_id)
        if candidate["claim_posture"] not in CLAIM_POSTURES:
            raise ValueError("daily editor candidate has an invalid claim posture")
        if set(candidate["audience_fields"]) != expected_fields:
            raise ValueError("daily editor candidate has wrong audience fields")
        for field, value in candidate["audience_fields"].items():
            _clean_prose(value, field=field)
        if audience == AI_ENGINEERING and (
            candidate["audience_fields"]["action_type"]
            not in ENGINEERING_ACTION_TYPES
        ):
            raise ValueError("daily editor candidate has an invalid action type")
    prior_ids: set[str] = set()
    for prior in _prior_rows(editor_input):
        selected_item_id = prior["selected_item_id"]
        if not selected_item_id or selected_item_id in prior_ids:
            raise ValueError("prior selected IDs must be non-empty and unique")
        prior_ids.add(selected_item_id)
        if set(prior["audience_fields"]) != expected_fields:
            raise ValueError("prior selection has wrong audience fields")


def _editor_input_payload(editor_input: AudienceEditorInput) -> dict[str, Any]:
    _validate_editor_input(editor_input)
    return {
        "audience": editor_input.audience,
        "day": editor_input.day,
        "target_min": editor_input.target_min,
        "target_max": editor_input.target_max,
        "candidate_set_sha256": _candidate_set_sha256(editor_input),
        "history_sha256": _history_sha256(editor_input),
        "candidates": [
            {
                "candidate_id": item["candidate_id"],
                "claim": item["claim"],
                "claim_posture": item["claim_posture"],
                "why_it_matters": item["why_it_matters"],
                "audience_fields": item["audience_fields"],
                "source_type": item["source_type"],
                "source_author": item["source_author"],
                "source_title": item["source_title"],
            }
            for item in sorted(_candidate_rows(editor_input), key=lambda item: item["candidate_id"])
        ],
        "prior_selected": [
            {
                "selected_item_id": item["selected_item_id"],
                "day": item["day"],
                "claim": item["claim"],
                "audience_fields": item["audience_fields"],
                "source_author": item["source_author"],
                "source_title": item["source_title"],
            }
            for item in sorted(
                _prior_rows(editor_input),
                key=lambda item: (item["day"], item["selected_item_id"]),
            )
        ],
    }


def render_editor_input(editor_input: AudienceEditorInput) -> str:
    return "\n".join(
        (
            "Select and order the strongest daily audience set from these frozen verified candidates.",
            "Return runner-owned IDs only; never rewrite candidate content.",
            _canonical_json(_editor_input_payload(editor_input)),
        )
    )


def validate_editor_output(
    audience: str,
    output_text: str,
    editor_input: AudienceEditorInput,
) -> dict[str, Any]:
    audience = _require_audience(audience)
    if editor_input.audience != audience:
        raise ValueError("editor output audience does not match its frozen input")
    _validate_editor_input(editor_input)
    payload = json.loads(output_text)
    fields = {"selected", "suppressed_duplicates", "thin_day_reason"}
    if not isinstance(payload, dict) or set(payload) != fields:
        raise ValueError("response does not match the exact daily editor schema")
    selected = payload["selected"]
    suppressed = payload["suppressed_duplicates"]
    if not isinstance(selected, list) or not isinstance(suppressed, list):
        raise ValueError("daily editor selected and suppressed fields must be arrays")
    if len(selected) > editor_input.target_max:
        raise ValueError("daily editor selected more than five candidates")

    current_ids = {item["candidate_id"] for item in _candidate_rows(editor_input)}
    prior_ids = {item["selected_item_id"] for item in _prior_rows(editor_input)}
    decision_values = (
        INVESTMENT_DECISION_VALUES
        if audience == INVESTMENT
        else ENGINEERING_DECISION_VALUES
    )
    clean_selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    selected_fields = {
        "candidate_id",
        "decision_value",
        "audit_reason",
        "updates_prior_id",
    }
    for item in selected:
        if not isinstance(item, dict) or set(item) != selected_fields:
            raise ValueError("selected item does not match the exact editor schema")
        candidate_id = item["candidate_id"]
        if candidate_id not in current_ids or candidate_id in selected_ids:
            raise ValueError("selected candidate ID is unknown or repeated")
        selected_ids.add(candidate_id)
        if item["decision_value"] not in decision_values:
            raise ValueError("selected item has an invalid audience decision value")
        updates_prior_id = item["updates_prior_id"]
        if updates_prior_id is not None and updates_prior_id not in prior_ids:
            raise ValueError("selected item references an unknown prior item")
        clean_selected.append(
            {
                "candidate_id": candidate_id,
                "decision_value": item["decision_value"],
                "audit_reason": _clean_prose(
                    item["audit_reason"], field="audit_reason"
                ),
                "updates_prior_id": updates_prior_id,
            }
        )

    clean_suppressed: list[dict[str, Any]] = []
    suppressed_ids: set[str] = set()
    suppressed_fields = {
        "candidate_id",
        "duplicate_of_id",
        "duplicate_scope",
        "audit_reason",
    }
    for item in suppressed:
        if not isinstance(item, dict) or set(item) != suppressed_fields:
            raise ValueError("suppressed item does not match the exact editor schema")
        candidate_id = item["candidate_id"]
        if (
            candidate_id not in current_ids
            or candidate_id in selected_ids
            or candidate_id in suppressed_ids
        ):
            raise ValueError("suppressed candidate ID is unknown or repeated")
        suppressed_ids.add(candidate_id)
        scope = item["duplicate_scope"]
        duplicate_of_id = item["duplicate_of_id"]
        if scope == "same_day":
            if duplicate_of_id not in selected_ids:
                raise ValueError("same-day duplicate must point to a selected candidate")
        elif scope == "cross_day":
            if duplicate_of_id not in prior_ids:
                raise ValueError("cross-day duplicate must point to a prior selection")
        else:
            raise ValueError("invalid duplicate scope")
        clean_suppressed.append(
            {
                "candidate_id": candidate_id,
                "duplicate_of_id": duplicate_of_id,
                "duplicate_scope": scope,
                "audit_reason": _clean_prose(
                    item["audit_reason"], field="audit_reason"
                ),
            }
        )

    thin_day_reason = payload["thin_day_reason"]
    if len(clean_selected) < editor_input.target_min:
        thin_day_reason = _clean_prose(thin_day_reason, field="thin_day_reason")
    elif thin_day_reason is not None:
        raise ValueError("thin_day_reason must be null when at least three are selected")
    return {
        "selected": clean_selected,
        "suppressed_duplicates": clean_suppressed,
        "thin_day_reason": thin_day_reason,
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


def _telemetry(
    *, response: Any, response_data: dict[str, Any], reported_cost: float | None
) -> dict[str, Any]:
    usage = getattr(response, "usage", None) or response_data.get("usage")
    return {
        "response_id": getattr(response, "id", None) or response_data.get("id"),
        "response_model": getattr(response, "model", None)
        or response_data.get("model"),
        "input_tokens": _usage_value(usage, "input_tokens"),
        "cached_tokens": _input_token_detail(usage, "cached_tokens"),
        "cache_write_tokens": _input_token_detail(usage, "cache_write_tokens"),
        "output_tokens": _usage_value(usage, "output_tokens"),
        "reported_cost_usd": reported_cost,
    }


def evaluate_one(
    client: Any,
    packet: EvidencePacket,
    *,
    audience: str,
    run: str,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_EXTRACTION_REASONING_EFFORT,
    frozen_input_text: str | None = None,
) -> dict[str, Any]:
    """Extract and application-bind one audience-specific frozen packet."""
    audience = _require_audience(audience)
    input_text = (
        render_model_input(packet, version=DEFAULT_INPUT_RENDER_VERSION)
        if frozen_input_text is None
        else frozen_input_text
    )
    if not isinstance(input_text, str) or not input_text.strip():
        raise ValueError("frozen_input_text must be a non-empty string")
    version = prompt_version(audience)
    tags = request_tags(
        audience=audience,
        job="insight-extraction",
        run=run,
        day=packet.day,
        version=version,
    )
    request = {
        "model": model,
        "instructions": instructions(audience),
        "input": input_text,
        "prompt_cache_key": prompt_cache_key(audience, packet.event_id),
        **llm_responses.litellm_prompt_cache_kwargs(model),
        "reasoning": {"effort": effort},
        "text": {"format": output_format(audience)},
        "store": False,
        "extra_body": {"metadata": {"tags": list(tags)}},
        "extra_headers": {"x-litellm-tags": ",".join(tags)},
    }
    response, response_data, reported_cost = _create_response(client, request)
    raw_output_text = llm_responses.output_text(response_data)
    response_provenance = {
        "raw_output_text": raw_output_text,
        "audience": audience,
        "event_id": packet.event_id,
        "day": packet.day,
        "feed_rank": packet.feed_rank,
        "evidence_sha256": packet.evidence_sha256,
        "input_sha256": _sha256(input_text),
        "model": model,
        "reasoning_effort": effort,
        "prompt_version": version,
        "schema_version": schema_version(audience),
        "prompt_sha256": prompt_sha256(audience),
        "prompt_cache_key": request["prompt_cache_key"],
        "request_tags": list(tags),
        **_telemetry(
            response=response,
            response_data=response_data,
            reported_cost=reported_cost,
        ),
    }
    try:
        payload = validate_extraction_output(audience, raw_output_text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ExtractionValidationError(
            str(exc), result=response_provenance
        ) from exc
    result = {
        **payload,
        "audience_fields": (
            {
                "investment_implication": payload["investment_implication"],
                "what_to_watch": payload["what_to_watch"],
            }
            if audience == INVESTMENT and payload["outcome"] == "insight"
            else {
                "action_type": payload["action_type"],
                "engineering_action": payload["engineering_action"],
                "validation_boundary": payload["validation_boundary"],
            }
            if audience == AI_ENGINEERING and payload["outcome"] == "insight"
            else None
        ),
        "citation": None,
        **response_provenance,
    }
    try:
        result["citation"] = bind_citation(
            packet,
            payload["citation_block_index"],
            payload["supporting_quote"],
        )
    except ValueError as exc:
        raise CitationVerificationError(str(exc), result=result) from exc
    return result


def evaluate_editor(
    client: Any,
    editor_input: AudienceEditorInput,
    *,
    run: str,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_EDITOR_REASONING_EFFORT,
) -> dict[str, Any]:
    """Select one daily audience set without permitting content mutation."""
    audience = _require_audience(editor_input.audience)
    version = editor_prompt_version(audience)
    tags = request_tags(
        audience=audience,
        job="daily-editor",
        run=run,
        day=editor_input.day,
        version=version,
    )
    request = {
        "model": model,
        "instructions": editor_instructions(audience),
        "input": render_editor_input(editor_input),
        "prompt_cache_key": editor_prompt_cache_key(audience, editor_input.day),
        **llm_responses.litellm_prompt_cache_kwargs(model),
        "reasoning": {"effort": effort},
        "text": {"format": editor_output_format(audience)},
        "store": False,
        "extra_body": {"metadata": {"tags": list(tags)}},
        "extra_headers": {"x-litellm-tags": ",".join(tags)},
    }
    response, response_data, reported_cost = _create_response(client, request)
    raw_output_text = llm_responses.output_text(response_data)
    payload = validate_editor_output(audience, raw_output_text, editor_input)
    return {
        **payload,
        "raw_output_text": raw_output_text,
        "audience": audience,
        "day": editor_input.day,
        "candidate_set_sha256": _candidate_set_sha256(editor_input),
        "history_sha256": _history_sha256(editor_input),
        "input_sha256": editor_input.input_sha256,
        "model": model,
        "reasoning_effort": effort,
        "prompt_version": version,
        "schema_version": editor_schema_version(audience),
        "prompt_sha256": editor_prompt_sha256(audience),
        "prompt_cache_key": request["prompt_cache_key"],
        "request_tags": list(tags),
        **_telemetry(
            response=response,
            response_data=response_data,
            reported_cost=reported_cost,
        ),
    }
