"""Independent quality review and deterministic expansion gates for v2 insights.

Review models produce auditable binary judgments. Publication eligibility is
computed separately from those stored judgments so a run can be reproduced
without another model call.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from fli import llm_responses


AUDIENCES = ("investment", "ai_engineering")
DEFAULT_MODEL = llm_responses.DEFAULT_EFFICIENT_MODEL
DEFAULT_REASONING_EFFORT = "high"
PROMPT_CACHE_SHARDS = 4
DAY_SET_CACHE_SCOPES = ("initial", "padding_tail_trim")

ITEM_PROMPT_VERSIONS = {
    "investment": "audience-insight-item-review-v2.3",
    "ai_engineering": "audience-insight-item-review-v2.4",
}
ITEM_SCHEMA_VERSION = "audience-insight-item-review-output-v2"
DAY_SET_PROMPT_VERSION = "audience-insight-day-set-review-v2.4"
DAY_SET_SCHEMA_VERSION = "audience-insight-day-set-review-output-v2"

PROMPT_DIR = Path(__file__).with_name("prompts")
ITEM_PROMPT_PATHS = {
    "investment": PROMPT_DIR / "audience_insight_item_reviewer_investment_v2.txt",
    "ai_engineering": PROMPT_DIR / "audience_insight_item_reviewer_v2.txt",
}
DAY_SET_PROMPT_PATH = PROMPT_DIR / "audience_insight_day_set_reviewer_v2.txt"

PASS_FAIL = ("pass", "fail")
ITEM_REVIEW_FIELDS = (
    "candidate_id",
    "claim_fidelity",
    "epistemic_discipline",
    "audience_usefulness",
    "actionability",
    "specificity",
    "failure_codes",
    "rationale",
)
FAILURE_CODES = (
    "unsupported_claim",
    "wrong_attribution",
    "attribution_upgrade",
    "modal_or_scope_loss",
    "unsupported_analysis_fact",
    "forced_ticker_or_trade",
    "generic_investment_implication",
    "generic_engineering_action",
    "missing_validation_boundary",
    "audience_mismatch",
    "not_decision_relevant",
    "vague_or_promotional",
    "other",
)

ITEM_REVIEW_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "name": "audience_insight_item_review_v2",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "candidate_id": {"type": "string"},
            "claim_fidelity": {"type": "string", "enum": list(PASS_FAIL)},
            "epistemic_discipline": {
                "type": "string",
                "enum": list(PASS_FAIL),
            },
            "audience_usefulness": {
                "type": "string",
                "enum": list(PASS_FAIL),
            },
            "actionability": {"type": "string", "enum": list(PASS_FAIL)},
            "specificity": {"type": "string", "enum": list(PASS_FAIL)},
            "failure_codes": {
                "type": "array",
                "items": {"type": "string", "enum": list(FAILURE_CODES)},
            },
            "rationale": {"type": "string"},
        },
        "required": list(ITEM_REVIEW_FIELDS),
        "additionalProperties": False,
    },
}


def item_review_format(candidate_id: str) -> dict[str, Any]:
    """Bind the structured response identity to this one review request.

    Candidate identity is application-owned: every item is reviewed in an
    isolated request whose input hash is frozen by the runner. Constraining the
    response schema to the expected ID prevents a model transcription error
    from breaking an otherwise valid review, while the validator below still
    rejects any response that could be associated with another candidate.
    """
    candidate_id = _non_empty_string(candidate_id, label="candidate_id")
    response_format = copy.deepcopy(ITEM_REVIEW_FORMAT)
    response_format["schema"]["properties"]["candidate_id"] = {
        "type": "string",
        "enum": [candidate_id],
    }
    return response_format

DAY_SET_REVIEW_FIELDS = (
    "duplicate_pairs",
    "padding_detected",
    "thin_day_honest",
    "set_rationale",
)
DAY_SET_REVIEW_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "name": "audience_insight_day_set_review_v2",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "duplicate_pairs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "left_id": {"type": "string"},
                        "right_id": {"type": "string"},
                        "scope": {
                            "type": "string",
                            "enum": ["same_day", "cross_day"],
                        },
                        "rationale": {"type": "string"},
                    },
                    "required": ["left_id", "right_id", "scope", "rationale"],
                    "additionalProperties": False,
                },
            },
            "padding_detected": {"type": "boolean"},
            "thin_day_honest": {"type": "boolean"},
            "set_rationale": {"type": "string"},
        },
        "required": list(DAY_SET_REVIEW_FIELDS),
        "additionalProperties": False,
    },
}


@dataclass(frozen=True)
class ReviewerEvidenceBlock:
    """Frozen evidence fields that the independent item reviewer may see."""

    block_index: int
    source_type: str
    verbatim_text: str
    source_author: str | None = None
    source_title: str | None = None
    relation: str | None = None


@dataclass(frozen=True)
class ItemReviewInput:
    candidate_id: str
    audience: str
    day: str
    evidence_blocks: tuple[ReviewerEvidenceBlock, ...]
    extracted_item: Mapping[str, Any]

    @property
    def input_sha256(self) -> str:
        return hashlib.sha256(render_item_input(self).encode()).hexdigest()


@dataclass(frozen=True)
class DaySetReviewInput:
    audience: str
    day: str
    selected: tuple[Mapping[str, Any], ...]
    unselected: tuple[Mapping[str, Any], ...]
    prior_selected: tuple[Mapping[str, Any], ...]

    @property
    def input_sha256(self) -> str:
        return hashlib.sha256(render_day_set_input(self).encode()).hexdigest()


@dataclass(frozen=True)
class DayGateInput:
    """Mechanically verified inputs plus independent reviewer outputs."""

    audience: str
    day: str
    selected_candidate_ids: tuple[str, ...]
    item_reviews: tuple[Mapping[str, Any], ...]
    day_set_review: Mapping[str, Any]
    schema_checks_passed: bool
    citation_checks_passed: bool
    editor_output_valid: bool
    pending_count: int = 0
    failed_count: int = 0


def _validate_audience(audience: str) -> str:
    if audience not in AUDIENCES:
        raise ValueError(f"unsupported audience: {audience!r}")
    return audience


def _audience_tag(audience: str) -> str:
    _validate_audience(audience)
    return "ai-engineering" if audience == "ai_engineering" else audience


def _evaluation_namespace(audience: str) -> str:
    _validate_audience(audience)
    label = "engineering" if audience == "ai_engineering" else "investment"
    return f"audience-insights-v2-{label}-evaluation"


def item_prompt_version(audience: str) -> str:
    return ITEM_PROMPT_VERSIONS[_validate_audience(audience)]


def item_instructions(audience: str) -> str:
    return ITEM_PROMPT_PATHS[_validate_audience(audience)].read_text().strip()


def day_set_instructions() -> str:
    return DAY_SET_PROMPT_PATH.read_text().strip()


def item_prompt_sha256(audience: str) -> str:
    return hashlib.sha256(item_instructions(audience).encode()).hexdigest()


def day_set_prompt_sha256() -> str:
    return hashlib.sha256(day_set_instructions().encode()).hexdigest()


def item_prompt_cache_key(audience: str, candidate_id: str) -> str:
    return llm_responses.sharded_prompt_cache_key(
        namespace=_evaluation_namespace(audience),
        prompt_version=item_prompt_version(audience),
        scope_key=f"item:{candidate_id}",
        shards=PROMPT_CACHE_SHARDS,
    )


def day_set_prompt_cache_key(
    audience: str,
    scope_key: str,
    *,
    cache_scope: str = "initial",
) -> str:
    if cache_scope not in DAY_SET_CACHE_SCOPES:
        raise ValueError(f"unsupported day-set cache scope: {cache_scope}")
    namespace = _evaluation_namespace(audience)
    if cache_scope != "initial":
        namespace = f"{namespace}-{cache_scope.replace('_', '-')}"
    routing_scope = (
        f"day-set:{scope_key}"
        if cache_scope == "initial"
        else f"day-set:{cache_scope}:{scope_key}"
    )
    return llm_responses.sharded_prompt_cache_key(
        namespace=namespace,
        prompt_version=DAY_SET_PROMPT_VERSION,
        scope_key=routing_scope,
        shards=PROMPT_CACHE_SHARDS,
    )


def request_tags(
    *, audience: str, run: str, day: str, prompt_version: str
) -> tuple[str, ...]:
    return (
        "app:frontier-lab-intelligence",
        "pipeline:audience-insights",
        f"audience:{_audience_tag(audience)}",
        "job:quality-evaluation",
        f"scope:day-{day}",
        f"prompt:{prompt_version}",
        f"run:{run}",
    )


def _json_input(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _review_item_fields(audience: str, item: Mapping[str, Any]) -> dict[str, Any]:
    common = (
        "claim",
        "claim_posture",
        "why_it_matters",
        "supporting_quote",
        "citation_block_index",
    )
    audience_fields = (
        ("investment_implication", "what_to_watch")
        if audience == "investment"
        else ("action_type", "engineering_action", "validation_boundary")
    )
    allowed = common + audience_fields
    missing = [field for field in allowed if field not in item]
    if missing:
        raise ValueError(f"review item is missing fields: {', '.join(missing)}")
    return {field: item[field] for field in allowed}


def render_item_input(review: ItemReviewInput) -> str:
    audience = _validate_audience(review.audience)
    if not review.candidate_id.strip():
        raise ValueError("candidate_id must be non-empty")
    if not review.evidence_blocks:
        raise ValueError("item review requires frozen evidence")
    indexes = [block.block_index for block in review.evidence_blocks]
    if any(index < 1 for index in indexes) or len(indexes) != len(set(indexes)):
        raise ValueError("evidence block indexes must be unique positive integers")
    payload = {
        "audience": audience,
        "candidate_id": review.candidate_id,
        "day": review.day,
        "evidence_blocks": [
            {
                "block_index": block.block_index,
                "source_type": block.source_type,
                "source_author": block.source_author,
                "source_title": block.source_title,
                "relation": block.relation,
                "verbatim_text": block.verbatim_text,
            }
            for block in review.evidence_blocks
        ],
        "extracted_item": _review_item_fields(audience, review.extracted_item),
    }
    return _json_input(payload)


def _candidate_id(item: Mapping[str, Any], *, label: str) -> str:
    candidate_id = item.get("candidate_id") or item.get("selected_item_id")
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        raise ValueError(f"{label} needs a non-empty candidate ID")
    return candidate_id


def _day_review_item(
    audience: str, item: Mapping[str, Any], *, prior: bool
) -> dict[str, Any]:
    identifier = _candidate_id(item, label="prior item" if prior else "current item")
    required = (
        ("claim",)
        if prior
        else ("claim", "claim_posture", "why_it_matters", "source_type")
    )
    missing = [field for field in required if field not in item]
    if missing:
        raise ValueError(f"day review item is missing fields: {', '.join(missing)}")
    audience_field_names = (
        ("investment_implication", "what_to_watch")
        if audience == "investment"
        else ("action_type", "engineering_action", "validation_boundary")
    )
    supplied_audience_fields = item.get("audience_fields")
    if supplied_audience_fields is not None:
        if not isinstance(supplied_audience_fields, Mapping) or set(
            supplied_audience_fields
        ) != set(audience_field_names):
            raise ValueError("day review audience_fields do not match the audience")
        audience_fields = {
            field: supplied_audience_fields[field] for field in audience_field_names
        }
    else:
        missing = [field for field in audience_field_names if field not in item]
        if missing:
            raise ValueError(
                f"day review item is missing audience fields: {', '.join(missing)}"
            )
        audience_fields = {field: item[field] for field in audience_field_names}
    normalized = {
        "selected_item_id" if prior else "candidate_id": identifier,
        "claim": item["claim"],
        "audience_fields": audience_fields,
        "source_author": item.get("source_author"),
        "source_title": item.get("source_title"),
    }
    if prior:
        if "day" not in item:
            raise ValueError("prior day review item is missing day")
        normalized["day"] = item["day"]
    else:
        normalized.update(
            {
                "claim_posture": item["claim_posture"],
                "why_it_matters": item["why_it_matters"],
                "source_type": item["source_type"],
            }
        )
    return normalized


def render_day_set_input(review: DaySetReviewInput) -> str:
    audience = _validate_audience(review.audience)
    current_items = tuple(review.selected) + tuple(review.unselected)
    current_ids = [_candidate_id(item, label="current item") for item in current_items]
    prior_ids = [_candidate_id(item, label="prior item") for item in review.prior_selected]
    if len(current_ids) != len(set(current_ids)):
        raise ValueError("current day-set candidate IDs must be unique")
    if len(prior_ids) != len(set(prior_ids)):
        raise ValueError("prior selected IDs must be unique")
    if set(current_ids) & set(prior_ids):
        raise ValueError("current and prior day-set IDs must not overlap")
    selected = [
        _day_review_item(audience, item, prior=False) for item in review.selected
    ]
    unselected = [
        _day_review_item(audience, item, prior=False) for item in review.unselected
    ]
    prior_selected = [
        _day_review_item(audience, item, prior=True)
        for item in review.prior_selected
    ]
    payload = {
        "audience": audience,
        "day": review.day,
        # Canonical ID order prevents editor order from leaking to the reviewer.
        "selected": sorted(selected, key=lambda item: item["candidate_id"]),
        "unselected": sorted(unselected, key=lambda item: item["candidate_id"]),
        "prior_selected": sorted(
            prior_selected,
            key=lambda item: item["selected_item_id"],
        ),
    }
    return _json_input(payload)


def _exact_object(payload: Any, fields: Sequence[str], *, label: str) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != set(fields):
        raise ValueError(f"response does not match the exact {label} schema")
    return {field: payload[field] for field in fields}


def _non_empty_string(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def validate_item_review(
    output_text: str, *, expected_candidate_id: str
) -> dict[str, Any]:
    payload = _exact_object(
        json.loads(output_text), ITEM_REVIEW_FIELDS, label="item-review-v2"
    )
    candidate_id = _non_empty_string(payload["candidate_id"], label="candidate_id")
    if candidate_id != expected_candidate_id:
        raise ValueError("item reviewer returned the wrong candidate_id")
    for field in (
        "claim_fidelity",
        "epistemic_discipline",
        "audience_usefulness",
        "actionability",
        "specificity",
    ):
        if payload[field] not in PASS_FAIL:
            raise ValueError(f"invalid {field}: {payload[field]!r}")
    codes = payload["failure_codes"]
    if not isinstance(codes, list) or any(code not in FAILURE_CODES for code in codes):
        raise ValueError("item review has invalid failure_codes")
    if len(codes) != len(set(codes)):
        raise ValueError("item review failure_codes must be unique")
    any_failure = any(payload[field] == "fail" for field in ITEM_REVIEW_FIELDS[1:6])
    if any_failure != bool(codes):
        raise ValueError("failure_codes must be present exactly when a dimension fails")
    payload["candidate_id"] = candidate_id
    payload["failure_codes"] = list(codes)
    payload["rationale"] = _non_empty_string(payload["rationale"], label="rationale")
    return payload


def validate_day_set_review(
    output_text: str,
    *,
    selected_candidate_ids: Iterable[str],
    current_candidate_ids: Iterable[str],
    prior_selected_ids: Iterable[str],
) -> dict[str, Any]:
    payload = _exact_object(
        json.loads(output_text), DAY_SET_REVIEW_FIELDS, label="day-set-review-v2"
    )
    selected = set(selected_candidate_ids)
    current = set(current_candidate_ids)
    prior = set(prior_selected_ids)
    if not selected <= current:
        raise ValueError("selected reviewer IDs must be current candidates")
    if current & prior:
        raise ValueError("current and prior reviewer ID sets must not overlap")
    pairs = payload["duplicate_pairs"]
    if not isinstance(pairs, list):
        raise ValueError("duplicate_pairs must be an array")
    normalized_pairs: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    pair_fields = ("left_id", "right_id", "scope", "rationale")
    for raw_pair in pairs:
        pair = _exact_object(raw_pair, pair_fields, label="duplicate-pair")
        left = _non_empty_string(pair["left_id"], label="duplicate left_id")
        right = _non_empty_string(pair["right_id"], label="duplicate right_id")
        if left == right:
            raise ValueError("duplicate pair IDs must be distinct")
        scope = pair["scope"]
        if scope == "same_day":
            if left not in current or right not in current:
                raise ValueError("same-day duplicate IDs must both be current candidates")
            if left not in selected or right not in selected:
                raise ValueError(
                    "same-day duplicate IDs must both be published selections"
                )
        elif scope == "cross_day":
            if not (
                (left in selected and right in prior)
                or (right in selected and left in prior)
            ):
                raise ValueError(
                    "cross-day duplicate needs one published selection and one prior ID"
                )
        else:
            raise ValueError(f"invalid duplicate scope: {scope!r}")
        identity = (scope, *sorted((left, right)))
        if identity in seen:
            raise ValueError("duplicate_pairs contains the same pair twice")
        seen.add(identity)
        normalized_pairs.append(
            {
                "left_id": left,
                "right_id": right,
                "scope": scope,
                "rationale": _non_empty_string(
                    pair["rationale"], label="duplicate rationale"
                ),
            }
        )
    for field in ("padding_detected", "thin_day_honest"):
        if type(payload[field]) is not bool:
            raise ValueError(f"{field} must be a boolean")
    return {
        "duplicate_pairs": normalized_pairs,
        "padding_detected": payload["padding_detected"],
        "thin_day_honest": payload["thin_day_honest"],
        "set_rationale": _non_empty_string(
            payload["set_rationale"], label="set_rationale"
        ),
    }


def _usage_value(usage: Any, field: str) -> int | None:
    value = usage.get(field) if isinstance(usage, dict) else getattr(usage, field, None)
    return int(value) if value is not None else None


def _input_token_detail(usage: Any, field: str) -> int | None:
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
    *,
    response: Any,
    response_data: Mapping[str, Any],
    reported_cost: float | None,
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


def review_item(
    client: Any,
    review: ItemReviewInput,
    *,
    run: str,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_REASONING_EFFORT,
) -> dict[str, Any]:
    prompt_version = item_prompt_version(review.audience)
    tags = request_tags(
        audience=review.audience,
        run=run,
        day=review.day,
        prompt_version=prompt_version,
    )
    request = {
        "model": model,
        "instructions": item_instructions(review.audience),
        "input": render_item_input(review),
        "prompt_cache_key": item_prompt_cache_key(
            review.audience, review.candidate_id
        ),
        **llm_responses.litellm_prompt_cache_kwargs(model),
        "reasoning": {"effort": effort},
        "text": {"format": item_review_format(review.candidate_id)},
        "store": False,
        "extra_body": {"metadata": {"tags": list(tags)}},
        "extra_headers": {"x-litellm-tags": ",".join(tags)},
    }
    response, response_data, cost = _create_response(client, request)
    raw_output_text = llm_responses.output_text(dict(response_data))
    result = validate_item_review(
        raw_output_text, expected_candidate_id=review.candidate_id
    )
    return {
        **result,
        "raw_output_text": raw_output_text,
        "audience": review.audience,
        "day": review.day,
        "input_sha256": review.input_sha256,
        "model": model,
        "reasoning_effort": effort,
        "prompt_version": prompt_version,
        "schema_version": ITEM_SCHEMA_VERSION,
        "prompt_sha256": item_prompt_sha256(review.audience),
        "prompt_cache_key": request["prompt_cache_key"],
        "request_tags": list(tags),
        **_telemetry(
            response=response,
            response_data=response_data,
            reported_cost=cost,
        ),
    }


def review_day_set(
    client: Any,
    review: DaySetReviewInput,
    *,
    run: str,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_REASONING_EFFORT,
    cache_scope: str = "initial",
) -> dict[str, Any]:
    if cache_scope not in DAY_SET_CACHE_SCOPES:
        raise ValueError(f"unsupported day-set cache scope: {cache_scope}")
    tags = request_tags(
        audience=review.audience,
        run=run,
        day=review.day,
        prompt_version=DAY_SET_PROMPT_VERSION,
    )
    current_ids = [
        _candidate_id(item, label="current item")
        for item in tuple(review.selected) + tuple(review.unselected)
    ]
    selected_ids = [
        _candidate_id(item, label="selected item") for item in review.selected
    ]
    prior_ids = [
        _candidate_id(item, label="prior item") for item in review.prior_selected
    ]
    request = {
        "model": model,
        "instructions": day_set_instructions(),
        "input": render_day_set_input(review),
        "prompt_cache_key": day_set_prompt_cache_key(
            review.audience,
            review.input_sha256,
            cache_scope=cache_scope,
        ),
        **llm_responses.litellm_prompt_cache_kwargs(model),
        "reasoning": {"effort": effort},
        "text": {"format": DAY_SET_REVIEW_FORMAT},
        "store": False,
        "extra_body": {"metadata": {"tags": list(tags)}},
        "extra_headers": {"x-litellm-tags": ",".join(tags)},
    }
    response, response_data, cost = _create_response(client, request)
    raw_output_text = llm_responses.output_text(dict(response_data))
    result = validate_day_set_review(
        raw_output_text,
        selected_candidate_ids=selected_ids,
        current_candidate_ids=current_ids,
        prior_selected_ids=prior_ids,
    )
    return {
        **result,
        "raw_output_text": raw_output_text,
        "audience": review.audience,
        "day": review.day,
        "input_sha256": review.input_sha256,
        "model": model,
        "reasoning_effort": effort,
        "prompt_version": DAY_SET_PROMPT_VERSION,
        "schema_version": DAY_SET_SCHEMA_VERSION,
        "prompt_sha256": day_set_prompt_sha256(),
        "prompt_cache_key": request["prompt_cache_key"],
        "cache_scope": cache_scope,
        "request_tags": list(tags),
        **_telemetry(
            response=response,
            response_data=response_data,
            reported_cost=cost,
        ),
    }


def compute_day_gate(gate: DayGateInput) -> dict[str, Any]:
    """Return the reproducible publication gate for one audience/day."""
    _validate_audience(gate.audience)
    if (
        type(gate.pending_count) is not int
        or type(gate.failed_count) is not int
        or gate.pending_count < 0
        or gate.failed_count < 0
    ):
        raise ValueError("pending_count and failed_count must be non-negative")
    selected = tuple(gate.selected_candidate_ids)
    selected_set = set(selected)
    selected_ids_valid = all(
        isinstance(candidate_id, str) and bool(candidate_id.strip())
        for candidate_id in selected
    )
    reviewer_by_id: dict[str, Mapping[str, Any]] = {}
    review_payloads_valid = True
    for review in gate.item_reviews:
        candidate_id = review.get("candidate_id")
        if not isinstance(candidate_id, str) or candidate_id in reviewer_by_id:
            review_payloads_valid = False
            continue
        try:
            strict_payload = {field: review[field] for field in ITEM_REVIEW_FIELDS}
            validate_item_review(
                json.dumps(strict_payload), expected_candidate_id=candidate_id
            )
        except (KeyError, TypeError, ValueError):
            review_payloads_valid = False
        reviewer_by_id[candidate_id] = review
    reviewer_coverage = (
        review_payloads_valid
        and selected_ids_valid
        and len(selected) == len(selected_set)
        and set(reviewer_by_id) == selected_set
    )

    def passes(candidate_id: str, fields: Sequence[str]) -> bool:
        review = reviewer_by_id.get(candidate_id, {})
        return all(review.get(field) == "pass" for field in fields)

    safety_fields = ("claim_fidelity", "epistemic_discipline")
    quality_fields = ("audience_usefulness", "actionability", "specificity")
    safety_pass = reviewer_coverage and all(
        passes(candidate_id, safety_fields) for candidate_id in selected
    )
    quality_pass_count = sum(
        passes(candidate_id, quality_fields) for candidate_id in selected
    )
    required_quality_pass_count = math.ceil(0.8 * len(selected))
    quality_threshold_pass = (
        reviewer_coverage and quality_pass_count >= required_quality_pass_count
    )
    thin_day = len(selected) < 3
    thin_day_quality_pass = (
        not thin_day
        or (
            quality_pass_count == len(selected)
            and gate.day_set_review.get("thin_day_honest") is True
        )
    )
    day_set_payload_valid = (
        isinstance(gate.day_set_review.get("duplicate_pairs"), list)
        and type(gate.day_set_review.get("padding_detected")) is bool
        and type(gate.day_set_review.get("thin_day_honest")) is bool
        and isinstance(gate.day_set_review.get("set_rationale"), str)
        and bool(gate.day_set_review.get("set_rationale", "").strip())
    )
    no_duplicates = gate.day_set_review.get("duplicate_pairs") == []
    no_padding = gate.day_set_review.get("padding_detected") is False
    checks = {
        "selected_ids_valid": selected_ids_valid,
        "selected_ids_unique": len(selected) == len(selected_set),
        "selected_count_within_editor_bound": len(selected) <= 5,
        "schema_checks_passed": gate.schema_checks_passed is True,
        "citation_checks_passed": gate.citation_checks_passed is True,
        "editor_output_valid": gate.editor_output_valid is True,
        "reviewer_coverage": reviewer_coverage,
        "day_set_review_valid": day_set_payload_valid,
        "claim_fidelity_and_epistemics": safety_pass,
        "quality_threshold": quality_threshold_pass,
        "thin_day_honest_and_all_quality": thin_day_quality_pass,
        "no_duplicate_stories": no_duplicates,
        "no_padding": no_padding,
        "no_unhandled_items": gate.pending_count == 0 and gate.failed_count == 0,
    }
    failure_reasons = tuple(name for name, passed in checks.items() if not passed)
    return {
        "audience": gate.audience,
        "day": gate.day,
        "passed": not failure_reasons,
        "selected_count": len(selected),
        "quality_pass_count": quality_pass_count,
        "required_quality_pass_count": required_quality_pass_count,
        "thin_day": thin_day,
        "checks": checks,
        "failure_reasons": list(failure_reasons),
    }


def compute_two_day_gate(
    gates: Iterable[DayGateInput],
    *,
    required_days: Sequence[str] = ("2026-07-11", "2026-07-09"),
    required_audiences: Sequence[str] = AUDIENCES,
    minimum_selected_per_audience: int = 3,
) -> dict[str, Any]:
    """Combine the known and blind day gates for both independent audiences."""
    if (
        type(minimum_selected_per_audience) is not int
        or minimum_selected_per_audience < 0
    ):
        raise ValueError("minimum_selected_per_audience must be non-negative")
    for audience in required_audiences:
        _validate_audience(audience)
    results: dict[tuple[str, str], dict[str, Any]] = {}
    for gate in gates:
        key = (gate.day, gate.audience)
        if key in results:
            raise ValueError(f"duplicate day gate input: {key!r}")
        results[key] = compute_day_gate(gate)
    required_keys = {
        (day, audience) for day in required_days for audience in required_audiences
    }
    missing = sorted(required_keys - set(results))
    required_results = [results[key] for key in sorted(required_keys & set(results))]
    selected_by_audience = {
        audience: sum(
            result["selected_count"]
            for result in required_results
            if result["audience"] == audience
        )
        for audience in required_audiences
    }
    insufficient_selected = [
        {
            "audience": audience,
            "selected_count": selected_by_audience[audience],
            "required_count": minimum_selected_per_audience,
        }
        for audience in required_audiences
        if selected_by_audience[audience] < minimum_selected_per_audience
    ]
    passed = (
        not missing
        and not insufficient_selected
        and all(result["passed"] for result in required_results)
    )
    return {
        "passed": passed,
        "required_days": list(required_days),
        "required_audiences": list(required_audiences),
        "minimum_selected_per_audience": minimum_selected_per_audience,
        "selected_by_audience": selected_by_audience,
        "insufficient_selected": insufficient_selected,
        "missing": [
            {"day": day, "audience": audience} for day, audience in missing
        ],
        "day_results": required_results,
    }
