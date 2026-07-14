import json
from types import SimpleNamespace

import pytest

from fli import cited_insights


class FakeRawResponse:
    def __init__(self, response):
        self._response = response
        self.headers = {"x-litellm-response-cost": "0.0031"}

    def parse(self):
        return self._response


class FakeRawAPI:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = SimpleNamespace(
            id="resp-insight-1",
            model=kwargs["model"],
            status="completed",
            output_text=json.dumps(self.payload),
            usage=SimpleNamespace(
                input_tokens=2_400,
                input_tokens_details=SimpleNamespace(
                    cached_tokens=1_280,
                    cache_write_tokens=0,
                ),
                output_tokens=160,
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
        raw_api = FakeRawAPI(payload)
        self.responses = SimpleNamespace(with_raw_response=raw_api)


def make_packet():
    return cited_insights.InsightInput(
        event_id="event-1",
        day="2026-07-11",
        current_rank=4,
        sources=(
            cited_insights.EvidenceSource(
                source_type="x_post",
                source_id="post-1",
                url="https://x.com/researcher/status/post-1",
                author="@researcher",
                relation="root",
                text="We measured a 35% reduction in serving latency.",
            ),
        ),
    )


def insight_payload():
    return {
        "outcome": "insight",
        "claim": "The researcher reported a 35% reduction in serving latency.",
        "why_it_matters": "The reported change could improve interactive use.",
        "investment_implication": "If reproduced, lower latency may reduce adoption friction.",
        "engineering_implication": "Teams should reproduce the measurement on their workloads.",
        "supporting_quote": "We measured a 35% reduction in serving latency.",
    }


def test_schema_has_only_the_minimal_insight_contract():
    schema = cited_insights.OUTPUT_FORMAT["schema"]

    assert set(schema["properties"]) == set(cited_insights.OUTPUT_FIELDS)
    assert "source_id" not in schema["properties"]
    assert "category" not in schema["properties"]
    assert schema["additionalProperties"] is False


def test_exact_quote_binds_to_runner_owned_source_provenance():
    citation = cited_insights.bind_citation(
        make_packet(), "We measured a 35% reduction in serving latency."
    )

    assert citation == {
        "source_type": "x_post",
        "source_id": "post-1",
        "source_url": "https://x.com/researcher/status/post-1",
        "source_author": "@researcher",
        "source_title": None,
        "exact_quote": "We measured a 35% reduction in serving latency.",
        "matching_source_count": 1,
    }


def test_non_exact_quote_is_rejected():
    with pytest.raises(ValueError, match="not an exact span"):
        cited_insights.bind_citation(make_packet(), "35 percent reduction")


def test_no_extractable_insight_requires_every_other_field_to_be_null():
    payload = {field: None for field in cited_insights.OUTPUT_FIELDS}
    payload["outcome"] = "no_extractable_insight"
    assert cited_insights.validate_output(json.dumps(payload))["outcome"] == (
        "no_extractable_insight"
    )

    payload["claim"] = "A claim slipped through."
    with pytest.raises(ValueError, match="requires null"):
        cited_insights.validate_output(json.dumps(payload))


def test_request_uses_cacheable_prefix_tags_and_verified_citation():
    client = FakeClient(insight_payload())

    result = cited_insights.evaluate_one(client, make_packet(), run="oracle-run")

    request = client.responses.with_raw_response.calls[0]
    assert request["instructions"] == cited_insights.instructions()
    assert len(request["instructions"]) > 4_096
    assert request["prompt_cache_key"] == cited_insights.prompt_cache_key("event-1")
    assert request["text"]["format"] == cited_insights.OUTPUT_FORMAT
    assert request["store"] is False
    assert "tools" not in request
    assert request["extra_body"]["metadata"]["tags"] == result["request_tags"]
    assert result["citation"]["source_id"] == "post-1"
    assert result["cached_tokens"] == 1_280
    assert result["reported_cost_usd"] == pytest.approx(0.0031)

