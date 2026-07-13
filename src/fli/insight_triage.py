"""Model boundary for conservative cited-insight envelope triage.

Attention chooses candidates upstream. This module judges substance without
seeing ranking or popularity features and never mutates evidence or Registry
state.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fli import llm_responses


PROMPT_VERSION = "envelope-triage-v1"
SCHEMA_VERSION = "envelope-triage-output-v1"
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_REASONING_EFFORT = "medium"
PROMPT_PATH = Path(__file__).with_name("prompts") / "envelope_triage_v1.txt"

CATEGORIES = frozenset(
    {
        "technical_development",
        "business_or_people",
        "strategy_or_policy",
        "safety_or_incident",
        "attributed_view",
        "source_material",
        "banter_or_meme",
        "insufficient_substance",
        "off_topic",
        "other",
    }
)

OUTPUT_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "name": "evidence_envelope_triage",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "decision": {"type": "string", "enum": ["keep", "drop"]},
            "category": {"type": "string", "enum": sorted(CATEGORIES)},
            "signal_post_ids": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 32,
            },
            "reason": {"type": "string"},
        },
        "required": ["decision", "category", "signal_post_ids", "reason"],
        "additionalProperties": False,
    },
}


@dataclass(frozen=True)
class EnvelopeInput:
    event_id: str
    day: str
    root: dict[str, Any]
    related_posts: tuple[dict[str, Any], ...] = ()
    urls: tuple[dict[str, str], ...] = ()
    embedded_artifacts: tuple[dict[str, str], ...] = ()
    retweet_count: int = 0

    @property
    def input_sha256(self) -> str:
        return hashlib.sha256(render_input(self).encode()).hexdigest()

    @property
    def valid_post_ids(self) -> set[str]:
        return {
            str(self.root["post_id"]),
            *(str(post["post_id"]) for post in self.related_posts),
        }


def instructions() -> str:
    """Return the stable cacheable prefix shared across triage requests."""
    return PROMPT_PATH.read_text().strip()


def prompt_sha256() -> str:
    return hashlib.sha256(instructions().encode()).hexdigest()


def prompt_cache_key() -> str:
    """One sequential cache lane is sufficient for the top-20 daily cohort."""
    return f"fli:cited-insights-triage:{PROMPT_VERSION}:shard-00"


def request_tags(*, run: str, day: str) -> tuple[str, ...]:
    return (
        "app:frontier-lab-intelligence",
        "pipeline:cited-insights",
        "job:envelope-triage",
        f"scope:day-{day}",
        f"prompt:{PROMPT_VERSION}",
        f"run:{run}",
    )


def render_input(envelope: EnvelopeInput) -> str:
    """Render variable evidence after the cacheable instructions."""
    root = envelope.root
    blocks = [
        "Evaluate this evidence envelope.",
        "",
        "ROOT POST",
        (
            f"[post_id={root['post_id']} | author={root['author']} | "
            f"type={root['post_type']}]"
        ),
        str(root.get("text") or ""),
    ]
    quoted_target = root.get("quoted_target_handle")
    if quoted_target:
        blocks.append(f"Quoted target: {quoted_target}")
    blocks.extend(("", "RELATED NON-RETWEET POSTS"))
    if not envelope.related_posts:
        blocks.append("None supplied.")
    for post in envelope.related_posts:
        authorship = "same-author" if post.get("same_author_as_root") else "other-author"
        blocks.extend(
            (
                "",
                (
                    f"[post_id={post['post_id']} | relation={post['relation']} | "
                    f"{authorship} | author={post['author']}]"
                ),
                str(post.get("text") or ""),
            )
        )
    blocks.extend(("", "EXPANDED EXTERNAL URLS"))
    if not envelope.urls:
        blocks.append("None supplied.")
    for link in envelope.urls:
        blocks.append(f"[post_id={link['post_id']}] {link['url']}")
    blocks.extend(("", "PROVIDER-SUPPLIED ARTIFACT METADATA"))
    if not envelope.embedded_artifacts:
        blocks.append("None supplied.")
    for artifact in envelope.embedded_artifacts:
        blocks.extend(
            (
                "",
                (
                    f"[post_id={artifact['post_id']} | kind={artifact['kind']}] "
                    f"{artifact.get('title') or 'Untitled artifact'}"
                ),
                str(artifact.get("preview") or "No preview supplied."),
                f"URL: {artifact.get('url') or 'No URL supplied.'}",
            )
        )
    blocks.extend(
        (
            "",
            "RETWEET SUMMARY",
            f"{envelope.retweet_count} exact retweet copies omitted.",
        )
    )
    return "\n".join(blocks)


def _validate_output(output_text: str, *, valid_ids: set[str]) -> dict[str, Any]:
    payload = json.loads(output_text)
    required = set(OUTPUT_FORMAT["schema"]["required"])
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("response does not match the exact triage schema")
    if payload["decision"] not in {"keep", "drop"}:
        raise ValueError(f"invalid decision: {payload['decision']!r}")
    if payload["category"] not in CATEGORIES:
        raise ValueError(f"invalid category: {payload['category']!r}")
    post_ids = payload["signal_post_ids"]
    if not isinstance(post_ids, list) or any(
        not isinstance(post_id, str) or post_id not in valid_ids
        for post_id in post_ids
    ):
        raise ValueError("signal_post_ids contains an ID absent from the input")
    if payload["decision"] == "drop" and post_ids:
        raise ValueError("drop must have no signal_post_ids")
    if payload["decision"] == "keep" and not post_ids:
        raise ValueError("keep must identify at least one signal_post_id")
    reason = payload["reason"]
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason must be a non-empty string")
    payload["reason"] = " ".join(reason.split())
    payload["signal_post_ids"] = list(dict.fromkeys(post_ids))
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
    envelope: EnvelopeInput,
    *,
    run: str,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_REASONING_EFFORT,
) -> dict[str, Any]:
    """Triage one frozen envelope without tools or canonical-state mutation."""
    tags = request_tags(run=run, day=envelope.day)
    request = {
        "model": model,
        "instructions": instructions(),
        "input": render_input(envelope),
        "prompt_cache_key": prompt_cache_key(),
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
    payload = _validate_output(
        llm_responses.output_text(response_data),
        valid_ids=envelope.valid_post_ids,
    )
    usage = getattr(response, "usage", None) or response_data.get("usage")
    return {
        **payload,
        "event_id": envelope.event_id,
        "day": envelope.day,
        "input_sha256": envelope.input_sha256,
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
