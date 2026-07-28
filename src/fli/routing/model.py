"""Audience-routing model boundary for complete attributed evidence packets.

One model call makes two audience-specific relevance judgments directly over
Evidence. It does not generate Insight prose or expose ranking and provenance
identifiers to the model.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tiktoken

from fli import llm_responses


PROMPT_VERSION = "audience-routing-v11"
SCHEMA_VERSION = "audience-routing-output-v1"
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_REASONING_EFFORT = "high"
MAX_OUTPUT_TOKENS = 32_768
MAX_INPUT_TOKENS = 20_000
INPUT_ENCODING = "o200k_base"
TRUNCATION_MARKER = (
    "\n\n---\n"
    "TRUNCATED_EVIDENCE: The evidence packet exceeded the 20,000-token "
    "routing input limit. Remaining lower-priority evidence was omitted "
    "from this model call."
)
PROMPT_PATH = Path(__file__).with_name("prompts") / "audience_routing.txt"
PROMPT_CACHE_KEY = f"fli:audience-routing:{PROMPT_VERSION}"

AUDIENCES = ("ai_engineering", "investment")
JUDGMENT_FIELDS = ("relevant", "reason")
_URL_ONLY_RE = re.compile(r"(?:https?://\S+\s*)+", re.IGNORECASE)
_OPAQUE_X_URL_RE = re.compile(r"https?://t\.co/\S+", re.IGNORECASE)
_MULTISPACE_RE = re.compile(r"[ \t]{2,}")

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
    "name": "audience_routing_v11",
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
class EvidenceSource:
    """One immutable, independently attributed routing source block."""

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
    # Insight-only temporal context. Deliberately excluded from the routing
    # evidence hash and serialized routing packet so existing runs remain
    # immutable and replayable.
    posted: str | None = None

    def normalized_text(self) -> str:
        return unicodedata.normalize("NFC", self.text)

    def effective_source_sha256(self) -> str:
        return self.source_sha256 or _sha256(self.normalized_text())


@dataclass(frozen=True)
class RoutingPacket:
    """One immutable Evidence packet presented to the audience router."""

    event_id: str
    day: str
    sources: tuple[EvidenceSource, ...]

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


def request_tags(*, run: str, day: str) -> tuple[str, ...]:
    return (
        "app:frontier-lab-intelligence",
        "pipeline:audience-routing",
        "job:audience-routing",
        f"scope:day-{day}",
        f"prompt:{PROMPT_VERSION}",
        f"run:{run}",
    )


def _display_text(source: EvidenceSource) -> str:
    """Return readable evidence text without changing stored source evidence."""
    text = html.unescape(source.normalized_text()).strip()
    if _URL_ONLY_RE.fullmatch(text):
        return ""
    if source.source_type == "x_post":
        text = _OPAQUE_X_URL_RE.sub("[link]", text)
        text = _MULTISPACE_RE.sub(" ", text)
    return text


def _one_line(value: str) -> str:
    return " ".join(html.unescape(value).split())


def _quoted_text(text: str) -> list[str]:
    lines = text.splitlines() or [""]
    return [f"> {line}" if line else ">" for line in lines]


def _is_transport_only(text: str) -> bool:
    return not text or _URL_ONLY_RE.fullmatch(text) is not None


def is_model_visible(source: EvidenceSource) -> bool:
    """Return whether one frozen source contributes a block to the model input."""
    if source.source_type == "artifact":
        return True
    if source.relation in {"root", "independent_original"}:
        return True
    if source.relation == "same_author_continuation":
        return not _is_transport_only(_display_text(source))
    return False


def _render_full_input(
    packet: RoutingPacket, *, include_dates: bool = False
) -> str:
    """Render a compact reading view without internal provenance."""
    roots = [source for source in packet.sources if source.relation == "root"]
    if len(roots) != 1:
        raise ValueError("routing packet must contain exactly one root source")
    root = roots[0]

    continuations = [
        source
        for source in packet.sources
        if source.relation == "same_author_continuation"
        and is_model_visible(source)
    ]
    independent_originals = [
        source
        for source in packet.sources
        if source.relation == "independent_original"
    ]
    artifacts = [
        source for source in packet.sources if source.source_type == "artifact"
    ]
    source_posts = [root, *independent_originals]
    lines = [
        "# Evidence about one development",
        "",
        f"Date: {packet.day}",
        "",
        f"## Source posts ({len(source_posts)})",
    ]

    for ordinal, source in enumerate(source_posts, start=1):
        author = _one_line(source.author or "Unknown author")
        lines.extend(["", f"### {ordinal}. {author}"])
        if include_dates and source.posted:
            lines.append(f"Posted: {_one_line(source.posted)}")
        lines.append("")
        text = _display_text(source)
        if _is_transport_only(text):
            lines.append(
                "> No substantive post text beyond the supporting artifact link."
                if artifacts
                else "> No substantive post text was available."
            )
        else:
            lines.extend(_quoted_text(text))

    if continuations:
        lines.extend(["", f"## Author updates ({len(continuations)})"])
        for ordinal, source in enumerate(continuations, start=1):
            author = _one_line(source.author or "Unknown author")
            lines.extend(["", f"### {ordinal}. {author}"])
            if include_dates and source.posted:
                lines.append(f"Posted: {_one_line(source.posted)}")
            lines.append("")
            lines.extend(_quoted_text(_display_text(source)))

    lines.extend(["", f"## Supporting artifacts ({len(artifacts)})"])
    if not artifacts:
        lines.extend(
            [
                "",
                "No supporting artifact text was included in this packet.",
            ]
        )
    for ordinal, source in enumerate(artifacts, start=1):
        title = _one_line(source.title or f"Artifact {ordinal}")
        lines.extend(["", f"### {ordinal}. {title}"])
        if source.author:
            lines.append(f"Author: {_one_line(source.author)}")
        lines.append("")
        lines.extend(_quoted_text(_display_text(source)))

    return "\n".join(lines)


def _input_encoding() -> Any:
    return tiktoken.get_encoding(INPUT_ENCODING)


def input_token_count(text: str) -> int:
    """Count model-facing input tokens with the GPT-5 family encoding."""
    return len(_input_encoding().encode(text))


def _truncate_input(text: str) -> str:
    """Bound only the model-facing view while retaining an explicit marker."""
    encoding = _input_encoding()
    tokens = encoding.encode(text)
    if len(tokens) <= MAX_INPUT_TOKENS:
        return text
    marker_tokens = encoding.encode(TRUNCATION_MARKER)
    prefix_tokens = tokens[: MAX_INPUT_TOKENS - len(marker_tokens)]
    return encoding.decode(prefix_tokens).rstrip() + TRUNCATION_MARKER


def render_input(
    packet: RoutingPacket, *, include_dates: bool = False
) -> str:
    """Render a readable model view capped at ``MAX_INPUT_TOKENS`` tokens.

    ``RoutingPacket`` and its evidence hash continue to bind the complete
    evidence. Only this derived model-facing view is truncated.
    """
    return _truncate_input(
        _render_full_input(packet, include_dates=include_dates)
    )


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
    model_input = render_input(packet)
    request = {
        "model": model,
        "instructions": instructions(),
        "input": model_input,
        "prompt_cache_key": PROMPT_CACHE_KEY,
        **llm_responses.litellm_prompt_cache_kwargs(model),
        "reasoning": {"effort": effort},
        "max_output_tokens": MAX_OUTPUT_TOKENS,
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
        "input_sha256": _sha256(model_input),
        "model": model,
        "reasoning_effort": effort,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "prompt_sha256": prompt_sha256(),
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
