import json

import pytest

from fli.routing import model as routing_model
from fli.insights import generation as insight_generation


def _packet() -> routing_model.RoutingPacket:
    return routing_model.RoutingPacket(
        event_id="event-1",
        day="2026-07-15",
        sources=(
            routing_model.EvidenceSource(
                source_type="x_post",
                source_id="post-1",
                url="https://x.com/alice/status/post-1",
                text="We released a new evaluation method.",
                author="@alice",
                relation="root",
                posted="2026-07-15",
            ),
            routing_model.EvidenceSource(
                source_type="artifact",
                source_id="artifact-1",
                url="https://example.com/evaluation",
                text="The method compares agent recovery after tool failures.",
                author="@alice",
                title="Recovery evaluation",
                relation="self_published_artifact",
            ),
            routing_model.EvidenceSource(
                source_type="x_post",
                source_id="post-reaction",
                url="https://x.com/bob/status/post-reaction",
                text="This looks exciting, but I have not tested it.",
                author="@bob",
                relation="quote",
            ),
        ),
    )


def _payload(audience="ai_engineering", **overrides):
    action_field = (
        "watchpoint" if audience == "investment" else "experiment"
    )
    payload = {
        "decision": "surface",
        "suppression_reason": None,
        "title": "Test recovery where agents actually fail",
        "summary": "Alice reports a new agent-recovery evaluation method.",
        "why_it_matters": "It could expose reliability failures hidden by success-only benchmarks.",
        action_field: "Run the method against one current tool-using workflow.",
    }
    payload.update(overrides)
    return payload


def test_contracts_are_separate_and_use_audience_specific_schemas():
    investment = insight_generation.contract("investment")
    engineering = insight_generation.contract("ai_engineering")

    assert investment.version == "investment-insight-v11"
    assert engineering.version == "ai-engineering-insight-v8"
    assert investment.cache_key != engineering.cache_key
    assert investment.sha256 != engineering.sha256
    assert "Investment decision standard" in investment.instructions()
    assert "assignment-critical Investment signal" in investment.instructions()
    assert "do not require disclosed funding" in investment.instructions()
    assert "sharp internal research note" in investment.instructions()
    assert "private frontier labs" in investment.instructions()
    assert "Never describe your own editorial process" in investment.instructions()
    assert "specific attributed strategic thesis" in investment.instructions()
    assert "specific attributed capability observation" in investment.instructions()
    assert "precise internal engineering review" in engineering.instructions()
    assert "AI Engineering decision standard" in engineering.instructions()
    assert "specific attributed capability observation" in engineering.instructions()
    assert "an unspecified comparison" in engineering.instructions()
    assert "generic aspirations" in engineering.instructions()
    assert "smallest practical investigation" in engineering.instructions()
    assert "Reproduce a source project only when" in engineering.instructions()
    assert "is not the team's assigned action" in engineering.instructions()
    assert routing_model.input_token_count(investment.instructions()) >= 1_024
    assert routing_model.input_token_count(engineering.instructions()) >= 1_024
    investment_schema = insight_generation.output_format("investment")
    engineering_schema = insight_generation.output_format("ai_engineering")
    assert investment_schema["strict"] is True
    assert set(investment_schema["schema"]["properties"]) == {
        "decision",
        "suppression_reason",
        "title",
        "summary",
        "why_it_matters",
        "watchpoint",
    }
    assert set(engineering_schema["schema"]["properties"]) == {
        "decision",
        "suppression_reason",
        "title",
        "summary",
        "why_it_matters",
        "experiment",
    }


def test_candidate_input_reuses_attributed_event_without_rank_or_router_reason():
    candidate = insight_generation.InsightCandidate.create(
        audience="ai_engineering", packet=_packet(), feed_rank=7
    )

    rendered = insight_generation.render_input(candidate)

    assert rendered.startswith(
        "<candidate_evidence>\n# Evidence about one development"
    )
    assert rendered.endswith("\n</candidate_evidence>")
    assert "Date: 2026-07-15" in rendered
    assert "## Source posts (1)" in rendered
    assert "### 1. @alice" in rendered
    assert "Posted: 2026-07-15" in rendered
    assert "## Supporting artifacts (1)" in rendered
    assert "### 1. Recovery evaluation" in rendered
    assert "https://x.com" not in rendered
    assert "https://example.com" not in rendered
    assert "This looks exciting" not in rendered
    assert "independent_reactions" not in rendered
    assert "feed_rank" not in rendered
    assert "routing" not in rendered
    assert candidate.feed_rank == 7
    assert candidate.candidate_id == insight_generation.InsightCandidate.create(
        audience="ai_engineering", packet=_packet(), feed_rank=19
    ).candidate_id


def test_insight_dates_do_not_change_the_frozen_routing_contract():
    packet = _packet()
    without_date = routing_model.RoutingPacket(
        event_id=packet.event_id,
        day=packet.day,
        sources=tuple(
            routing_model.EvidenceSource(
                **{
                    key: value
                    for key, value in source.__dict__.items()
                    if key != "posted"
                }
            )
            for source in packet.sources
        ),
    )

    assert packet.evidence_sha256 == without_date.evidence_sha256
    assert "evaluation_day" not in routing_model.render_input(packet)
    assert "posted:" not in routing_model.render_input(packet)


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
    assert request["prompt_cache_key"] == "fli:insights:investment:v11"
    assert request["text"]["format"] == insight_generation.output_format(
        "investment"
    )
    assert request["store"] is False
    assert "audience:investment" in request["extra_body"]["metadata"]["tags"]


def test_surface_output_requires_all_content_and_no_reason():
    result = insight_generation.validate_output(
        json.dumps(_payload()), audience="ai_engineering"
    )

    assert result.decision is insight_generation.InsightDecision.SURFACE
    assert result.suppression_reason is None
    assert result.as_dict()["experiment"].startswith("Run the method")

    with pytest.raises(ValueError, match="null suppression_reason"):
        insight_generation.validate_output(
            _payload(suppression_reason="Weak."), audience="ai_engineering"
        )
    with pytest.raises(ValueError, match="requires summary"):
        insight_generation.validate_output(
            _payload(summary=None), audience="ai_engineering"
        )


def test_suppress_output_keeps_freeform_reason_and_null_content():
    result = insight_generation.validate_output(
        {
            "decision": "suppress",
            "suppression_reason": (
                "The post names a method but supplies no artifact, behavior, "
                "or implementation detail from which to derive a concrete test."
            ),
            "title": "A method announcement without testable evidence",
            "summary": None,
            "why_it_matters": None,
            "experiment": None,
        },
        audience="ai_engineering",
    )

    assert result.decision is insight_generation.InsightDecision.SUPPRESS
    assert result.suppression_reason.startswith("The post names")
    assert result.title == "A method announcement without testable evidence"

    with pytest.raises(ValueError, match="concrete suppression_reason"):
        insight_generation.validate_output(
            {
                **result.as_dict(),
                "suppression_reason": "   ",
            },
            audience="ai_engineering",
        )
    with pytest.raises(ValueError, match="null summary"):
        insight_generation.validate_output(
            {
                **result.as_dict(),
                "summary": "A partial summary should not leak through.",
            },
            audience="ai_engineering",
        )
    with pytest.raises(ValueError, match="title is required"):
        insight_generation.validate_output(
            {**result.as_dict(), "title": None}, audience="ai_engineering"
        )


def test_publish_binds_model_content_to_application_owned_feed_metadata():
    candidate = insight_generation.InsightCandidate.create(
        audience="investment", packet=_packet(), feed_rank=3
    )
    result = insight_generation.validate_output(
        _payload("investment"), audience="investment"
    )

    published = insight_generation.publish(candidate, result)

    assert published.as_dict() == {
        "candidate_id": candidate.candidate_id,
        "event_id": "event-1",
        "day": "2026-07-15",
        "audience": "investment",
        "feed_rank": 3,
        "title": _payload("investment")["title"],
        "summary": _payload("investment")["summary"],
        "why_it_matters": _payload("investment")["why_it_matters"],
        "action": _payload("investment")["watchpoint"],
        "action_label": "Watchpoint",
    }
    suppressed = insight_generation.validate_output(
        {
            "decision": "suppress",
            "suppression_reason": "The evidence is too thin to act on.",
            "title": "A thinly evidenced technical claim",
            "summary": None,
            "why_it_matters": None,
            "watchpoint": None,
        },
        audience="investment",
    )
    with pytest.raises(ValueError, match="cannot be published"):
        insight_generation.publish(candidate, suppressed)


def test_validation_rejects_unknown_fields_and_audiences():
    with pytest.raises(ValueError, match="exact Insight schema"):
        insight_generation.validate_output(
            {**_payload(), "confidence": 0.9}, audience="ai_engineering"
        )
    with pytest.raises(ValueError, match="unsupported Insight audience"):
        insight_generation.InsightCandidate.create(
            audience="general", packet=_packet(), feed_rank=1
        )
    with pytest.raises(ValueError, match="positive integer"):
        insight_generation.InsightCandidate.create(
            audience="investment", packet=_packet(), feed_rank=0
        )
    with pytest.raises(ValueError, match="positive integer"):
        insight_generation.InsightCandidate.create(
            audience="investment", packet=_packet(), feed_rank=True
        )
