import json

import pytest

from fli import audience_routing, insight_generation


def _packet() -> audience_routing.RoutingPacket:
    return audience_routing.RoutingPacket(
        event_id="event-1",
        day="2026-07-15",
        sources=(
            audience_routing.EvidenceSource(
                source_type="x_post",
                source_id="post-1",
                url="https://x.com/alice/status/post-1",
                text="We released a new evaluation method.",
                author="@alice",
                relation="root",
            ),
            audience_routing.EvidenceSource(
                source_type="artifact",
                source_id="artifact-1",
                url="https://example.com/evaluation",
                text="The method compares agent recovery after tool failures.",
                author="@alice",
                title="Recovery evaluation",
                relation="self_published_artifact",
            ),
        ),
    )


def _payload(**overrides):
    payload = {
        "decision": "surface",
        "suppression_reason": None,
        "summary": "Alice reports a new agent-recovery evaluation method.",
        "implication": "It could expose reliability failures hidden by success-only benchmarks.",
        "next_step": "Run the method against one current tool-using workflow.",
    }
    payload.update(overrides)
    return payload


def test_contracts_are_separate_and_share_one_schema():
    investment = insight_generation.contract("investment")
    engineering = insight_generation.contract("ai_engineering")

    assert investment.version == "investment-insight-v1"
    assert engineering.version == "ai-engineering-insight-v1"
    assert investment.cache_key != engineering.cache_key
    assert investment.sha256 != engineering.sha256
    assert "Investment decision standard" in investment.instructions()
    assert "AI Engineering decision standard" in engineering.instructions()
    assert insight_generation.OUTPUT_FORMAT["strict"] is True
    assert set(insight_generation.OUTPUT_FORMAT["schema"]["properties"]) == {
        "decision",
        "suppression_reason",
        "summary",
        "implication",
        "next_step",
    }


def test_candidate_input_reuses_attributed_envelope_without_rank_or_router_reason():
    candidate = insight_generation.InsightCandidate.create(
        audience="ai_engineering", packet=_packet(), feed_rank=7
    )

    rendered = insight_generation.render_input(candidate)

    assert rendered.startswith("<candidate_evidence>\nevidence_packet:")
    assert rendered.endswith("\n</candidate_evidence>")
    assert 'author: "@alice"' in rendered
    assert "kind: authored_artifact" in rendered
    assert "feed_rank" not in rendered
    assert "routing" not in rendered
    assert candidate.feed_rank == 7
    assert candidate.candidate_id == insight_generation.InsightCandidate.create(
        audience="ai_engineering", packet=_packet(), feed_rank=19
    ).candidate_id


def test_build_request_is_pure_and_keeps_variable_evidence_last():
    candidate = insight_generation.InsightCandidate.create(
        audience="investment", packet=_packet(), feed_rank=3
    )

    request = insight_generation.build_request(
        candidate,
        model="gpt-5.4-mini",
        effort="high",
        run="spike-not-executed",
    )

    assert request["instructions"] == insight_generation.contract(
        "investment"
    ).instructions()
    assert request["input"] == insight_generation.render_input(candidate)
    assert request["prompt_cache_key"] == "fli:insights:investment:v1"
    assert request["text"]["format"] == insight_generation.OUTPUT_FORMAT
    assert request["store"] is False
    assert "audience:investment" in request["extra_body"]["metadata"]["tags"]


def test_surface_output_requires_all_content_and_no_reason():
    result = insight_generation.validate_output(json.dumps(_payload()))

    assert result.decision is insight_generation.InsightDecision.SURFACE
    assert result.suppression_reason is None
    assert result.as_dict()["next_step"].startswith("Run the method")

    with pytest.raises(ValueError, match="null suppression_reason"):
        insight_generation.validate_output(_payload(suppression_reason="Weak."))
    with pytest.raises(ValueError, match="requires summary"):
        insight_generation.validate_output(_payload(summary=None))


def test_suppress_output_keeps_freeform_reason_and_null_content():
    result = insight_generation.validate_output(
        {
            "decision": "suppress",
            "suppression_reason": (
                "The post names a method but supplies no artifact, behavior, "
                "or implementation detail from which to derive a concrete test."
            ),
            "summary": None,
            "implication": None,
            "next_step": None,
        }
    )

    assert result.decision is insight_generation.InsightDecision.SUPPRESS
    assert result.suppression_reason.startswith("The post names")

    with pytest.raises(ValueError, match="concrete suppression_reason"):
        insight_generation.validate_output(
            {
                **result.as_dict(),
                "suppression_reason": "   ",
            }
        )
    with pytest.raises(ValueError, match="null audience content"):
        insight_generation.validate_output(
            {
                **result.as_dict(),
                "summary": "A partial summary should not leak through.",
            }
        )


def test_publish_binds_model_content_to_application_owned_feed_metadata():
    candidate = insight_generation.InsightCandidate.create(
        audience="investment", packet=_packet(), feed_rank=3
    )
    result = insight_generation.validate_output(_payload())

    published = insight_generation.publish(candidate, result)

    assert published.as_dict() == {
        "candidate_id": candidate.candidate_id,
        "event_id": "event-1",
        "day": "2026-07-15",
        "audience": "investment",
        "feed_rank": 3,
        "summary": _payload()["summary"],
        "implication": _payload()["implication"],
        "next_step": _payload()["next_step"],
    }
    suppressed = insight_generation.validate_output(
        {
            "decision": "suppress",
            "suppression_reason": "The evidence is too thin to act on.",
            "summary": None,
            "implication": None,
            "next_step": None,
        }
    )
    with pytest.raises(ValueError, match="cannot be published"):
        insight_generation.publish(candidate, suppressed)


def test_validation_rejects_unknown_fields_and_audiences():
    with pytest.raises(ValueError, match="exact Insight schema"):
        insight_generation.validate_output({**_payload(), "confidence": 0.9})
    with pytest.raises(ValueError, match="unsupported Insight audience"):
        insight_generation.InsightCandidate.create(
            audience="general", packet=_packet(), feed_rank=1
        )
    with pytest.raises(ValueError, match="positive integer"):
        insight_generation.InsightCandidate.create(
            audience="investment", packet=_packet(), feed_rank=0
        )
