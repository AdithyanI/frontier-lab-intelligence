import json
from types import SimpleNamespace

import pytest

from fli import audience_insight_evaluations as evaluations


class FakeRawResponse:
    def __init__(self, response):
        self._response = response
        self.headers = {"x-litellm-response-cost": "0.0042"}

    def parse(self):
        return self._response


class FakeRawAPI:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = SimpleNamespace(
            id="resp-review-1",
            model=kwargs["model"],
            status="completed",
            output_text=json.dumps(self.payload),
            usage=SimpleNamespace(
                input_tokens=2_000,
                input_tokens_details=SimpleNamespace(
                    cached_tokens=1_100, cache_write_tokens=25
                ),
                output_tokens=120,
            ),
        )
        response.model_dump = lambda **_: {
            "id": response.id,
            "model": response.model,
            "status": response.status,
            "output_text": response.output_text,
        }
        return FakeRawResponse(response)


class FakeClient:
    def __init__(self, payload):
        self.responses = SimpleNamespace(with_raw_response=FakeRawAPI(payload))


def passing_item(candidate_id="candidate-1"):
    return {
        "candidate_id": candidate_id,
        "claim_fidelity": "pass",
        "epistemic_discipline": "pass",
        "audience_usefulness": "pass",
        "actionability": "pass",
        "specificity": "pass",
        "failure_codes": [],
        "rationale": "The claim and next decision remain bounded and concrete.",
    }


def item_input():
    return evaluations.ItemReviewInput(
        candidate_id="candidate-1",
        audience="investment",
        day="2026-07-11",
        evidence_blocks=(
            evaluations.ReviewerEvidenceBlock(
                block_index=1,
                source_type="x_post",
                source_author="@researcher",
                relation="root",
                verbatim_text="We measured a 35% reduction in serving latency.",
            ),
        ),
        extracted_item={
            "claim": "The researcher reported a 35% latency reduction.",
            "claim_posture": "first_party_report",
            "why_it_matters": "If validated, the result could reduce friction.",
            "investment_implication": "It could change the serving-cost thesis.",
            "what_to_watch": "Compare latency under the same workload.",
            "supporting_quote": "We measured a 35% reduction in serving latency.",
            "citation_block_index": 1,
        },
    )


def day_review_payload(**overrides):
    payload = {
        "duplicate_pairs": [],
        "padding_detected": False,
        "thin_day_honest": False,
        "set_rationale": "The set contains distinct decision-relevant stories.",
    }
    payload.update(overrides)
    return payload


def engineering_day_item(candidate_id, claim, *, prior_day=None):
    item = {
        "candidate_id": candidate_id,
        "claim": claim,
        "claim_posture": "first_party_report",
        "why_it_matters": "The result may change a bounded technical decision.",
        "action_type": "benchmark",
        "engineering_action": "Benchmark the same workload against the baseline.",
        "validation_boundary": "The provider's disclosed workload is the boundary.",
        "source_type": "x_post",
        "source_author": "@author",
        "source_title": None,
    }
    if prior_day is not None:
        item["selected_item_id"] = item.pop("candidate_id")
        item["day"] = prior_day
    return item


def test_review_schemas_are_strict_and_contain_only_contract_fields():
    item_schema = evaluations.ITEM_REVIEW_FORMAT["schema"]
    day_schema = evaluations.DAY_SET_REVIEW_FORMAT["schema"]

    assert item_schema["additionalProperties"] is False
    assert set(item_schema["properties"]) == set(evaluations.ITEM_REVIEW_FIELDS)
    assert day_schema["additionalProperties"] is False
    assert set(day_schema["properties"]) == set(evaluations.DAY_SET_REVIEW_FIELDS)
    assert "feed_rank" not in item_schema["properties"]
    assert "editor_order" not in item_schema["properties"]


def test_item_response_schema_binds_identity_without_mutating_shared_contract():
    first = evaluations.item_review_format("candidate-first")
    second = evaluations.item_review_format("candidate-second")

    assert first["schema"]["properties"]["candidate_id"] == {
        "type": "string",
        "enum": ["candidate-first"],
    }
    assert second["schema"]["properties"]["candidate_id"] == {
        "type": "string",
        "enum": ["candidate-second"],
    }
    assert evaluations.ITEM_REVIEW_FORMAT["schema"]["properties"][
        "candidate_id"
    ] == {"type": "string"}


def test_item_validator_enforces_candidate_codes_and_binary_dimensions():
    assert evaluations.validate_item_review(
        json.dumps(passing_item()), expected_candidate_id="candidate-1"
    )["claim_fidelity"] == "pass"

    wrong = passing_item("other")
    with pytest.raises(ValueError, match="wrong candidate_id"):
        evaluations.validate_item_review(
            json.dumps(wrong), expected_candidate_id="candidate-1"
        )

    failed = passing_item()
    failed["actionability"] = "fail"
    with pytest.raises(ValueError, match="failure_codes"):
        evaluations.validate_item_review(
            json.dumps(failed), expected_candidate_id="candidate-1"
        )

    failed["failure_codes"] = ["generic_investment_implication"]
    assert evaluations.validate_item_review(
        json.dumps(failed), expected_candidate_id="candidate-1"
    )["failure_codes"] == ["generic_investment_implication"]


def test_item_request_uses_luna_high_isolated_tags_and_four_lane_namespace():
    client = FakeClient(passing_item())

    result = evaluations.review_item(client, item_input(), run="gate-v2")

    request = client.responses.with_raw_response.calls[0]
    assert request["model"] == "gpt-5.6-luna"
    assert request["reasoning"] == {"effort": "high"}
    assert request["prompt_cache_retention"] == "24h"
    assert request["text"]["format"] == evaluations.item_review_format(
        "candidate-1"
    )
    assert request["prompt_cache_key"].startswith(
        "fli:audience-insights-v2-investment-evaluation:"
    )
    assert "job:quality-evaluation" in result["request_tags"]
    assert "audience:investment" in result["request_tags"]
    assert "Feed rank" not in request["input"]
    assert evaluations.item_prompt_version("investment") == (
        "audience-insight-item-review-v2.3"
    )
    assert evaluations.item_prompt_version("ai_engineering") == (
        "audience-insight-item-review-v2.4"
    )
    normalized_instructions = " ".join(request["instructions"].split())
    assert "A posture enum, source_author field" in normalized_instructions
    assert (
        "Funding or investment participation establishes only participation"
        in normalized_instructions
    )
    assert "A generic source category is not itself a watchpoint" in (
        normalized_instructions
    )
    assert "One concrete named observable is sufficient" in normalized_instructions
    engineering_instructions = " ".join(
        evaluations.item_instructions("ai_engineering").split()
    )
    assert "naming an API, model, or broad capability area is not enough" in (
        engineering_instructions
    )
    assert "it is not an operational validation boundary" in (
        engineering_instructions
    )
    assert "naming an API, model, or broad capability area is not enough" not in (
        normalized_instructions
    )
    assert result["reasoning_effort"] == "high"
    assert result["cached_tokens"] == 1_100
    assert result["reported_cost_usd"] == pytest.approx(0.0042)


def test_item_input_filters_cross_audience_and_untrusted_provenance_fields():
    review = item_input()
    item = dict(review.extracted_item)
    item.update(
        {
            "engineering_action": "This must not cross audiences.",
            "source_url": "https://untrusted.example",
            "feed_rank": 1,
        }
    )
    rendered = evaluations.render_item_input(
        evaluations.ItemReviewInput(
            candidate_id=review.candidate_id,
            audience=review.audience,
            day=review.day,
            evidence_blocks=review.evidence_blocks,
            extracted_item=item,
        )
    )

    assert "engineering_action" not in rendered
    assert "untrusted.example" not in rendered
    assert "feed_rank" not in rendered


def test_day_set_validator_enforces_same_day_and_cross_day_reference_integrity():
    payload = day_review_payload(
        duplicate_pairs=[
            {
                "left_id": "current-1",
                "right_id": "prior-1",
                "scope": "cross_day",
                "rationale": "The current candidate repeats the prior release.",
            }
        ]
    )
    result = evaluations.validate_day_set_review(
        json.dumps(payload),
        selected_candidate_ids=["current-1"],
        current_candidate_ids=["current-1", "current-2"],
        prior_selected_ids=["prior-1"],
    )
    assert result["duplicate_pairs"][0]["scope"] == "cross_day"

    payload["duplicate_pairs"][0]["right_id"] = "missing"
    with pytest.raises(ValueError, match="one published selection and one prior"):
        evaluations.validate_day_set_review(
            json.dumps(payload),
            selected_candidate_ids=["current-1"],
            current_candidate_ids=["current-1", "current-2"],
            prior_selected_ids=["prior-1"],
        )

    payload["duplicate_pairs"] = [
        {
            "left_id": "current-1",
            "right_id": "current-2",
            "scope": "same_day",
            "rationale": "Only one item is published, so this pair is irrelevant.",
        }
    ]
    with pytest.raises(ValueError, match="both be published selections"):
        evaluations.validate_day_set_review(
            json.dumps(payload),
            selected_candidate_ids=["current-1"],
            current_candidate_ids=["current-1", "current-2"],
            prior_selected_ids=["prior-1"],
        )


def test_day_set_request_canonicalizes_order_and_uses_engineering_namespace():
    review = evaluations.DaySetReviewInput(
        audience="ai_engineering",
        day="2026-07-09",
        selected=(
            engineering_day_item("candidate-b", "B"),
            engineering_day_item("candidate-a", "A"),
        ),
        unselected=(engineering_day_item("candidate-c", "C"),),
        prior_selected=(
            engineering_day_item("prior-a", "Prior", prior_day="2026-07-08"),
        ),
    )
    client = FakeClient(day_review_payload())

    result = evaluations.review_day_set(client, review, run="gate-v2")

    request = client.responses.with_raw_response.calls[0]
    assert request["reasoning"] == {"effort": "high"}
    assert request["prompt_cache_key"].startswith(
        "fli:audience-insights-v2-engineering-evaluation:"
    )
    assert "audience:ai-engineering" in result["request_tags"]
    decoded = json.loads(request["input"])
    assert [item["candidate_id"] for item in decoded["selected"]] == [
        "candidate-a",
        "candidate-b",
    ]
    assert "feed_rank" not in request["input"]
    assert (
        evaluations.DAY_SET_PROMPT_VERSION
        == "audience-insight-day-set-review-v2.4"
    )
    normalized_instructions = " ".join(request["instructions"].split())
    assert "A reference to the author's, vendor's, or another private harness" in (
        normalized_instructions
    )
    assert "Generic instructions to monitor earnings" in normalized_instructions
    assert "An unselected testimonial, availability detail" in (
        normalized_instructions
    )


def test_reconciled_day_set_uses_distinct_namespace_even_on_same_shard(monkeypatch):
    monkeypatch.setattr(
        evaluations.llm_responses,
        "sharded_prompt_cache_key",
        lambda *, namespace, prompt_version, scope_key, shards: (
            f"fli:{namespace}:{prompt_version}:shard-00"
        ),
    )
    initial = evaluations.day_set_prompt_cache_key(
        "ai_engineering", "same-input-shard"
    )
    reconciled = evaluations.day_set_prompt_cache_key(
        "ai_engineering",
        "different-input-same-shard",
        cache_scope="padding_tail_trim",
    )

    assert initial != reconciled
    assert "padding-tail-trim" not in initial
    assert "padding-tail-trim" in reconciled
    with pytest.raises(ValueError, match="unsupported day-set cache scope"):
        evaluations.day_set_prompt_cache_key(
            "ai_engineering", "scope", cache_scope="unknown"
        )


def make_gate(
    *,
    audience="investment",
    day="2026-07-11",
    count=5,
    quality_failures=0,
    thin_honest=False,
    duplicates=None,
    padding=False,
):
    ids = tuple(f"{audience}-{day}-{index}" for index in range(count))
    reviews = []
    for index, candidate_id in enumerate(ids):
        review = passing_item(candidate_id)
        if index < quality_failures:
            review["specificity"] = "fail"
            review["failure_codes"] = ["vague_or_promotional"]
        reviews.append(review)
    return evaluations.DayGateInput(
        audience=audience,
        day=day,
        selected_candidate_ids=ids,
        item_reviews=tuple(reviews),
        day_set_review=day_review_payload(
            duplicate_pairs=duplicates or [],
            padding_detected=padding,
            thin_day_honest=thin_honest,
        ),
        schema_checks_passed=True,
        citation_checks_passed=True,
        editor_output_valid=True,
    )


def test_day_gate_uses_ceil_eighty_percent_of_selected_items():
    passes = evaluations.compute_day_gate(make_gate(count=5, quality_failures=1))
    fails = evaluations.compute_day_gate(make_gate(count=5, quality_failures=2))
    four_items = evaluations.compute_day_gate(make_gate(count=4, quality_failures=1))

    assert passes["passed"] is True
    assert passes["required_quality_pass_count"] == 4
    assert fails["passed"] is False
    assert "quality_threshold" in fails["failure_reasons"]
    assert four_items["required_quality_pass_count"] == 4
    assert four_items["passed"] is False


def test_thin_day_requires_every_item_to_pass_and_honest_review():
    honest = evaluations.compute_day_gate(make_gate(count=2, thin_honest=True))
    dishonest = evaluations.compute_day_gate(make_gate(count=2, thin_honest=False))
    weak = evaluations.compute_day_gate(
        make_gate(count=2, quality_failures=1, thin_honest=True)
    )

    assert honest["passed"] is True
    assert dishonest["passed"] is False
    assert weak["passed"] is False
    assert "thin_day_honest_and_all_quality" in weak["failure_reasons"]


def test_day_gate_rejects_duplicate_stories_padding_and_unhandled_items():
    gate = make_gate(count=3, padding=True)
    gate = evaluations.DayGateInput(
        **{
            **gate.__dict__,
            "day_set_review": day_review_payload(
                duplicate_pairs=[
                    {
                        "left_id": gate.selected_candidate_ids[0],
                        "right_id": gate.selected_candidate_ids[1],
                        "scope": "same_day",
                        "rationale": "Same release.",
                    }
                ],
                padding_detected=True,
            ),
            "pending_count": 1,
        }
    )

    result = evaluations.compute_day_gate(gate)

    assert result["passed"] is False
    assert {"no_duplicate_stories", "no_padding", "no_unhandled_items"} <= set(
        result["failure_reasons"]
    )


def test_two_day_gate_requires_both_audiences_on_known_and_blind_days():
    gates = [
        make_gate(audience=audience, day=day, count=3)
        for day in ("2026-07-11", "2026-07-09")
        for audience in evaluations.AUDIENCES
    ]

    complete = evaluations.compute_two_day_gate(gates)
    missing = evaluations.compute_two_day_gate(gates[:-1])

    assert complete["passed"] is True
    assert len(complete["day_results"]) == 4
    assert missing["passed"] is False
    assert missing["missing"] == [
        {"day": "2026-07-09", "audience": "ai_engineering"}
    ]


def test_two_day_gate_rejects_a_vacuous_all_thin_audience():
    gates = [
        make_gate(
            audience=audience,
            day=day,
            count=0 if audience == "investment" else 3,
            thin_honest=True,
        )
        for day in ("2026-07-11", "2026-07-09")
        for audience in evaluations.AUDIENCES
    ]

    result = evaluations.compute_two_day_gate(gates)

    assert result["passed"] is False
    assert result["selected_by_audience"]["investment"] == 0
    assert result["insufficient_selected"] == [
        {"audience": "investment", "selected_count": 0, "required_count": 3}
    ]
