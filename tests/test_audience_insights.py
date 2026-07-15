import json
from types import SimpleNamespace

import pytest

from fli import audience_insights


class FakeRawResponse:
    def __init__(self, response):
        self._response = response
        self.headers = {"x-litellm-response-cost": "0.0075"}

    def parse(self):
        return self._response


class FakeRawAPI:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = SimpleNamespace(
            id=f"resp-audience-{len(self.calls)}",
            model=kwargs["model"],
            status="completed",
            output_text=json.dumps(self.payload),
            usage=SimpleNamespace(
                input_tokens=2_800,
                input_tokens_details=SimpleNamespace(
                    cached_tokens=1_536,
                    cache_write_tokens=0,
                ),
                output_tokens=180,
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


def make_packet(*, repeated_in_selected=False):
    quote = "We  measured a 35% reduction in serving latency."
    second_text = quote if not repeated_in_selected else f"{quote} Later: {quote}"
    return audience_insights.EvidencePacket(
        event_id="event-1",
        day="2026-07-11",
        feed_rank=4,
        sources=(
            audience_insights.EvidenceSource(
                source_type="x_post",
                source_id="post-1",
                url="https://x.com/observer/status/post-1",
                text=quote,
                author="@observer",
                relation="quote",
            ),
            audience_insights.EvidenceSource(
                source_type="artifact",
                source_id="artifact-2",
                url="https://example.com/report",
                text=second_text,
                author="Example Lab",
                title="Serving report",
                relation="article_section",
                source_sha256="a" * 64,
                section_ordinal=2,
                source_char_start=100,
                source_char_end=100 + len(second_text),
            ),
        ),
    )


def investment_payload():
    return {
        "outcome": "insight",
        "no_insight_reason": None,
        "claim": "Example Lab reported a 35% reduction in serving latency.",
        "claim_posture": "first_party_report",
        "why_it_matters": "Lower latency could reduce adoption friction.",
        "investment_implication": "If validated, the change could improve product differentiation.",
        "what_to_watch": "Check whether independent production workloads reproduce the reduction.",
        "supporting_quote": "We  measured a 35% reduction in serving latency.",
        "citation_block_index": 2,
    }


def engineering_payload():
    return {
        "outcome": "insight",
        "no_insight_reason": None,
        "claim": "Example Lab reported a 35% reduction in serving latency.",
        "claim_posture": "first_party_report",
        "why_it_matters": "The reported change could affect interactive systems.",
        "action_type": "benchmark",
        "engineering_action": "Benchmark the release on representative interactive workloads.",
        "validation_boundary": "The result remains scoped to the lab's undisclosed serving setup.",
        "supporting_quote": "We  measured a 35% reduction in serving latency.",
        "citation_block_index": 2,
    }


def no_insight_payload(audience):
    fields = (
        audience_insights.INVESTMENT_OUTPUT_FIELDS
        if audience == audience_insights.INVESTMENT
        else audience_insights.ENGINEERING_OUTPUT_FIELDS
    )
    payload = {field: None for field in fields}
    payload["outcome"] = "no_extractable_insight"
    payload["no_insight_reason"] = "no_audience_decision_value"
    return payload


def investment_candidate(candidate_id):
    return audience_insights.EditorCandidate(
        candidate_id=candidate_id,
        claim=f"Claim for {candidate_id}.",
        claim_posture="directly_documented",
        why_it_matters="It changes a concrete competitive question.",
        audience_fields={
            "investment_implication": "It could affect product differentiation.",
            "what_to_watch": "Check the next disclosed adoption result.",
        },
        source_type="x_post",
        source_author="@source",
    )


def make_editor_input():
    return audience_insights.AudienceEditorInput(
        audience=audience_insights.INVESTMENT,
        day="2026-07-11",
        candidates=tuple(investment_candidate(f"candidate-{index}") for index in range(1, 5)),
        prior_selected=(
            audience_insights.PriorSelection(
                selected_item_id="prior-1",
                day="2026-07-10",
                claim="An earlier release was documented.",
                audience_fields={
                    "investment_implication": "It could affect differentiation.",
                    "what_to_watch": "Check whether a correction appears.",
                },
                source_author="@source",
            ),
        ),
        candidate_set_sha256="b" * 64,
        history_sha256="c" * 64,
    )


def editor_payload():
    return {
        "selected": [
            {
                "candidate_id": "candidate-1",
                "decision_value": "thesis_or_model",
                "audit_reason": "It sharpens a competitive assumption.",
                "updates_prior_id": None,
            },
            {
                "candidate_id": "candidate-2",
                "decision_value": "diligence_question",
                "audit_reason": "It creates a concrete diligence question.",
                "updates_prior_id": "prior-1",
            },
            {
                "candidate_id": "candidate-3",
                "decision_value": "execution_or_competitive_risk",
                "audit_reason": "It identifies an execution risk.",
                "updates_prior_id": None,
            },
        ],
        "suppressed_duplicates": [
            {
                "candidate_id": "candidate-4",
                "duplicate_of_id": "candidate-1",
                "duplicate_scope": "same_day",
                "audit_reason": "It repeats the selected release.",
            }
        ],
        "thin_day_reason": None,
    }


def test_contracts_and_schemas_are_audience_specific():
    investment = audience_insights.contract(audience_insights.INVESTMENT)
    engineering = audience_insights.contract(audience_insights.AI_ENGINEERING)

    assert investment.prompt_version == "investment-insight-v2.2"
    assert engineering.prompt_version == "ai-engineering-insight-v2.2"
    engineering_prompt = audience_insights.instructions(
        audience_insights.AI_ENGINEERING
    )
    assert "benchmark on \"representative workloads\"" in engineering_prompt
    assert "one-off anecdotal failure" in engineering_prompt
    assert investment.editor_prompt_version == "investment-daily-editor-v2.1"
    assert engineering.editor_prompt_version == "ai-engineering-daily-editor-v2.4"
    assert audience_insights.EDITOR_SCHEMA_VERSION == "audience-daily-editor-output-v2"
    investment_properties = audience_insights.output_format(
        audience_insights.INVESTMENT
    )["schema"]["properties"]
    engineering_properties = audience_insights.output_format(
        audience_insights.AI_ENGINEERING
    )["schema"]["properties"]
    assert "investment_implication" in investment_properties
    assert "engineering_action" not in investment_properties
    assert "engineering_action" in engineering_properties
    assert "investment_implication" not in engineering_properties
    engineering_editor = " ".join(
        audience_insights.editor_instructions(
            audience_insights.AI_ENGINEERING
        ).split()
    )
    assert "compare every unselected eligible candidate" in engineering_editor
    assert "another private harness" in engineering_editor


def test_outcome_null_contract_and_engineering_action_enum_are_exact():
    result = audience_insights.validate_extraction_output(
        audience_insights.INVESTMENT,
        json.dumps(no_insight_payload(audience_insights.INVESTMENT)),
    )
    assert result["no_insight_reason"] == "no_audience_decision_value"

    invalid = no_insight_payload(audience_insights.INVESTMENT)
    invalid["claim"] = "A field escaped null validation."
    with pytest.raises(ValueError, match="requires null"):
        audience_insights.validate_extraction_output(
            audience_insights.INVESTMENT, json.dumps(invalid)
        )

    invalid_action = engineering_payload()
    invalid_action["action_type"] = "adopt"
    with pytest.raises(ValueError, match="valid action_type"):
        audience_insights.validate_extraction_output(
            audience_insights.AI_ENGINEERING, json.dumps(invalid_action)
        )


def test_supporting_quote_is_not_cleaned_or_collapsed():
    payload = investment_payload()
    payload["claim"] = "  Example Lab   reported lower latency.  "
    result = audience_insights.validate_extraction_output(
        audience_insights.INVESTMENT, json.dumps(payload)
    )

    assert result["claim"] == "Example Lab reported lower latency."
    assert result["supporting_quote"] == (
        "We  measured a 35% reduction in serving latency."
    )


def test_numbered_block_binds_runner_provenance_and_exact_offsets():
    citation = audience_insights.bind_citation(
        make_packet(),
        2,
        "We  measured a 35% reduction in serving latency.",
    )

    assert citation == {
        "citation_block_index": 2,
        "source_type": "artifact",
        "source_id": "artifact-2",
        "source_url": "https://example.com/report",
        "source_author": "Example Lab",
        "source_title": "Serving report",
        "source_relation": "article_section",
        "source_sha256": "a" * 64,
        "section_ordinal": 2,
        "char_start": 100,
        "char_end": 148,
        "exact_quote": "We  measured a 35% reduction in serving latency.",
        "global_matching_block_count": 2,
    }


def test_binding_rejects_wrong_block_and_repeated_quote_inside_block():
    with pytest.raises(ValueError, match="outside"):
        audience_insights.bind_citation(make_packet(), 3, "anything")
    with pytest.raises(ValueError, match="not unique"):
        audience_insights.bind_citation(
            make_packet(repeated_in_selected=True),
            2,
            "We  measured a 35% reduction in serving latency.",
        )


def test_rendered_evidence_exposes_block_selector_but_not_provenance_or_rank():
    rendered = audience_insights.render_input(make_packet())

    assert '<EVIDENCE_BLOCK index="1" type="X_POST">' in rendered
    assert '<EVIDENCE_BLOCK index="2" type="ARTIFACT">' in rendered
    assert "author=Example Lab" in rendered
    assert "artifact-2" not in rendered
    assert "https://example.com" not in rendered
    assert "feed_rank" not in rendered
    assert "engagement" not in rendered.lower()


def test_model_input_render_versions_are_deterministic_and_preserve_packet():
    packet = audience_insights.EvidencePacket(
        event_id="event-expletive",
        day="2026-07-10",
        feed_rank=23,
        sources=(
            audience_insights.EvidenceSource(
                source_type="x_post",
                source_id="post-expletive",
                url="https://x.com/source/status/post-expletive",
                text="thank fucking god",
                author="@source",
                relation="reply",
            ),
        ),
    )

    legacy = audience_insights.render_input(packet)
    first = audience_insights.render_model_input(
        packet,
        version=audience_insights.INPUT_RENDER_PROVIDER_SAFE_V2,
    )
    second = audience_insights.render_model_input(
        packet,
        version=audience_insights.INPUT_RENDER_PROVIDER_SAFE_V2,
    )

    assert "thank fucking god" in legacy
    assert "thank [EXPLETIVE] god" in first
    assert "fucking" not in first.lower()
    assert packet.sources[0].text == "thank fucking god"
    assert first == second
    assert packet.input_sha256 == audience_insights._sha256(legacy)
    assert packet.input_sha256 != audience_insights._sha256(first)


def test_citation_across_model_input_normalization_still_fails_closed():
    packet = audience_insights.EvidencePacket(
        event_id="event-expletive",
        day="2026-07-10",
        feed_rank=23,
        sources=(
            audience_insights.EvidenceSource(
                source_type="x_post",
                source_id="post-expletive",
                url="https://x.com/source/status/post-expletive",
                text="thank fucking god",
                author="@source",
                relation="reply",
            ),
        ),
    )
    payload = investment_payload()
    payload["supporting_quote"] = "thank [EXPLETIVE] god"
    payload["citation_block_index"] = 1
    client = FakeClient(payload)

    with pytest.raises(audience_insights.CitationVerificationError):
        audience_insights.evaluate_one(
            client,
            packet,
            audience=audience_insights.INVESTMENT,
            run="provider-safe-input-test",
            frozen_input_text=audience_insights.render_model_input(
                packet,
                version=audience_insights.INPUT_RENDER_PROVIDER_SAFE_V2,
            ),
        )

    assert "thank [EXPLETIVE] god" in client.responses.with_raw_response.calls[0][
        "input"
    ]
    assert packet.sources[0].text == "thank fucking god"


@pytest.mark.parametrize(
    ("audience", "payload"),
    [
        (audience_insights.INVESTMENT, investment_payload()),
        (audience_insights.AI_ENGINEERING, engineering_payload()),
    ],
)
def test_extraction_request_uses_audience_prompt_cache_tags_and_luna_medium(
    audience, payload
):
    client = FakeClient(payload)

    result = audience_insights.evaluate_one(
        client,
        make_packet(),
        audience=audience,
        run="calibration-v2",
    )

    request = client.responses.with_raw_response.calls[0]
    namespace = audience.replace("_", "-")
    cache_namespace = "investment" if audience == "investment" else "engineering"
    assert request["model"] == "gpt-5.6-luna"
    assert request["reasoning"] == {"effort": "medium"}
    assert request["prompt_cache_retention"] == "24h"
    assert request["instructions"] == audience_insights.instructions(audience)
    assert request["text"]["format"] == audience_insights.output_format(audience)
    assert request["store"] is False
    assert request["prompt_cache_key"].startswith(
        f"fli:audience-insights-v2-{cache_namespace}-extraction:"
    )
    assert f"audience:{namespace}" in result["request_tags"]
    assert result["citation"]["source_id"] == "artifact-2"
    assert result["audience_fields"]
    assert result["cached_tokens"] == 1_536
    assert result["reported_cost_usd"] == pytest.approx(0.0075)


def test_citation_failure_preserves_raw_model_result_for_audit():
    payload = investment_payload()
    payload["supporting_quote"] = "35 percent reduction"
    client = FakeClient(payload)

    with pytest.raises(audience_insights.CitationVerificationError) as captured:
        audience_insights.evaluate_one(
            client,
            make_packet(),
            audience=audience_insights.INVESTMENT,
            run="calibration-v2",
        )

    assert captured.value.result["supporting_quote"] == "35 percent reduction"
    assert captured.value.result["response_id"] == "resp-audience-1"


def test_schema_failure_preserves_raw_response_telemetry_and_provenance():
    payload = engineering_payload()
    payload["action_type"] = "adopt"
    client = FakeClient(payload)

    with pytest.raises(audience_insights.ExtractionValidationError) as captured:
        audience_insights.evaluate_one(
            client,
            make_packet(),
            audience=audience_insights.AI_ENGINEERING,
            run="calibration-v2",
        )

    result = captured.value.result
    assert json.loads(result["raw_output_text"])["action_type"] == "adopt"
    assert result["response_id"] == "resp-audience-1"
    assert result["response_model"] == "gpt-5.6-luna"
    assert result["input_tokens"] == 2_800
    assert result["cached_tokens"] == 1_536
    assert result["reported_cost_usd"] == pytest.approx(0.0075)
    assert result["audience"] == "ai_engineering"
    assert result["event_id"] == "event-1"
    assert result["day"] == "2026-07-11"
    assert result["evidence_sha256"] == make_packet().evidence_sha256
    assert result["input_sha256"] == make_packet().input_sha256
    assert result["schema_version"] == "ai-engineering-insight-output-v2"
    assert "audience:ai-engineering" in result["request_tags"]


def test_editor_validation_accepts_only_runner_ids_and_duplicate_references():
    result = audience_insights.validate_editor_output(
        audience_insights.INVESTMENT,
        json.dumps(editor_payload()),
        make_editor_input(),
    )

    assert [item["candidate_id"] for item in result["selected"]] == [
        "candidate-1",
        "candidate-2",
        "candidate-3",
    ]
    assert result["suppressed_duplicates"][0]["duplicate_of_id"] == "candidate-1"
    assert set(audience_insights.editor_output_format(
        audience_insights.INVESTMENT
    )["schema"]["properties"]) == {
        "selected",
        "suppressed_duplicates",
        "thin_day_reason",
    }


def test_editor_rejects_unknown_ids_invalid_duplicates_and_dishonest_thin_day():
    unknown = editor_payload()
    unknown["selected"][0]["candidate_id"] = "unknown"
    with pytest.raises(ValueError, match="unknown or repeated"):
        audience_insights.validate_editor_output(
            audience_insights.INVESTMENT,
            json.dumps(unknown),
            make_editor_input(),
        )

    bad_duplicate = editor_payload()
    bad_duplicate["suppressed_duplicates"][0]["duplicate_of_id"] = "candidate-4"
    with pytest.raises(ValueError, match="selected candidate"):
        audience_insights.validate_editor_output(
            audience_insights.INVESTMENT,
            json.dumps(bad_duplicate),
            make_editor_input(),
        )

    thin = editor_payload()
    thin["selected"] = thin["selected"][:2]
    thin["suppressed_duplicates"] = []
    with pytest.raises(ValueError, match="thin_day_reason"):
        audience_insights.validate_editor_output(
            audience_insights.INVESTMENT,
            json.dumps(thin),
            make_editor_input(),
        )


def test_editor_request_uses_id_only_schema_luna_high_and_stable_cache_lane():
    payload = editor_payload()
    client = FakeClient(payload)

    result = audience_insights.evaluate_editor(
        client,
        make_editor_input(),
        run="editor-v2",
    )

    request = client.responses.with_raw_response.calls[0]
    assert request["model"] == "gpt-5.6-luna"
    assert request["reasoning"] == {"effort": "high"}
    assert request["prompt_cache_retention"] == "24h"
    assert request["text"]["format"] == audience_insights.editor_output_format(
        audience_insights.INVESTMENT
    )
    assert request["prompt_cache_key"].startswith(
        "fli:audience-insights-v2-investment-editor:"
    )
    assert "candidate-1" in request["input"]
    assert "feed_rank" not in request["input"]
    assert "supporting_quote" not in request["input"]
    assert result["schema_version"] == "audience-daily-editor-output-v2"
    assert "job:daily-editor" in result["request_tags"]
