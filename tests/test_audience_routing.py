import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from fli import audience_insights, audience_routing


class FakeRawResponse:
    def __init__(self, response):
        self._response = response
        self.headers = {"x-litellm-response-cost": "0.0037"}

    def parse(self):
        return self._response


class FakeRawAPI:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = SimpleNamespace(
            id="resp-routing-1",
            model=kwargs["model"],
            status="completed",
            output_text=json.dumps(self.payload),
            usage=SimpleNamespace(
                input_tokens=2_400,
                input_tokens_details=SimpleNamespace(
                    cached_tokens=1_536,
                    cache_write_tokens=256,
                ),
                output_tokens=96,
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
    return audience_routing.RoutingPacket(
        event_id="event-secret-42",
        day="2026-07-12",
        sources=(
            audience_insights.EvidenceSource(
                source_type="x_post",
                source_id="source-secret-root",
                url="https://example.com/private-root",
                author="Satya Nadella",
                relation="root",
                text="The new system reduced inference latency under our workload.",
            ),
            audience_insights.EvidenceSource(
                source_type="x_article_section",
                source_id="source-secret-article",
                url="https://example.com/private-article",
                author="Research Team",
                title="Serving system report",
                relation="artifact",
                text="Tests report lower latency and lower serving cost.",
                section_ordinal=2,
                source_char_start=100,
                source_char_end=154,
            ),
        ),
    )


def routing_payload():
    return {
        "ai_engineering": {
            "relevant": True,
            "reason": "The serving behavior gives engineers a concrete system change to investigate.",
        },
        "investment": {
            "relevant": True,
            "reason": "The reported serving-cost reduction could affect inference unit economics.",
        },
    }


def test_schema_requires_only_two_exact_audience_judgments():
    schema = audience_routing.OUTPUT_FORMAT["schema"]

    assert set(schema["properties"]) == {"ai_engineering", "investment"}
    assert schema["required"] == ["ai_engineering", "investment"]
    assert schema["additionalProperties"] is False
    for audience in ("ai_engineering", "investment"):
        judgment = schema["properties"][audience]
        assert set(judgment["properties"]) == {"relevant", "reason"}
        assert judgment["required"] == ["relevant", "reason"]
        assert judgment["additionalProperties"] is False
        assert judgment["properties"]["relevant"] == {"type": "boolean"}


def test_render_input_preserves_numbered_authorship_but_omits_provenance_hints():
    rendered = audience_routing.render_input(make_packet())

    assert '<EVIDENCE_BLOCK index="1">' in rendered
    assert '<EVIDENCE_BLOCK index="2">' in rendered
    assert "type=x_post | author=Satya Nadella | relation=root" in rendered
    assert "title=Serving system report" in rendered
    assert "reduced inference latency" in rendered
    assert "event-secret-42" not in rendered
    assert "source-secret-root" not in rendered
    assert "source-secret-article" not in rendered
    assert "https://example.com" not in rendered
    assert "section_ordinal" not in rendered
    assert "source_char_start" not in rendered
    assert "feed_rank" not in rendered
    assert "triage" not in rendered.lower()


def test_evidence_hash_binds_hidden_provenance_while_input_hash_does_not():
    packet = make_packet()
    changed_source = replace(
        packet.sources[0],
        source_id="different-source-id",
        url="https://example.com/different-url",
    )
    changed_packet = replace(packet, sources=(changed_source, packet.sources[1]))

    assert changed_packet.evidence_sha256 != packet.evidence_sha256
    assert changed_packet.input_sha256 == packet.input_sha256


def test_request_uses_luna_medium_cache_adapter_tags_and_telemetry():
    client = FakeClient(routing_payload())

    result = audience_routing.evaluate_one(
        client,
        make_packet(),
        run="first-cohort",
    )

    request = client.responses.with_raw_response.calls[0]
    assert request["model"] == "gpt-5.6-luna"
    assert request["reasoning"] == {"effort": "medium"}
    assert request["prompt_cache_retention"] == "24h"
    assert request["instructions"] == audience_routing.instructions()
    assert len(request["instructions"].split()) >= 1_024
    assert request["input"] == audience_routing.render_input(make_packet())
    assert request["prompt_cache_key"] == audience_routing.prompt_cache_key(
        make_packet().event_id
    )
    assert request["text"]["format"] == audience_routing.OUTPUT_FORMAT
    assert request["store"] is False
    assert "tools" not in request
    assert request["extra_body"]["metadata"]["tags"] == result["request_tags"]
    assert request["extra_headers"]["x-litellm-tags"] == ",".join(
        result["request_tags"]
    )
    assert result["request_tags"] == [
        "app:frontier-lab-intelligence",
        "pipeline:audience-routing",
        "job:audience-routing",
        "scope:day-2026-07-12",
        "prompt:audience-routing-v1",
        "run:first-cohort",
    ]
    assert result["ai_engineering"]["relevant"] is True
    assert result["evidence_sha256"] == make_packet().evidence_sha256
    assert result["input_sha256"] == make_packet().input_sha256
    assert result["input_tokens"] == 2_400
    assert result["cached_tokens"] == 1_536
    assert result["cache_write_tokens"] == 256
    assert result["output_tokens"] == 96
    assert result["reported_cost_usd"] == pytest.approx(0.0037)


@pytest.mark.parametrize(
    ("mutate", "error"),
    [
        (
            lambda payload: payload.update({"decision": "keep"}),
            "exact audience-routing schema",
        ),
        (
            lambda payload: payload["investment"].update({"confidence": 0.9}),
            "exact audience-routing schema",
        ),
        (
            lambda payload: payload["investment"].update({"relevant": "true"}),
            "investment.relevant must be a boolean",
        ),
        (
            lambda payload: payload["ai_engineering"].update({"reason": "  "}),
            "ai_engineering.reason must be a non-empty string",
        ),
    ],
)
def test_output_rejects_non_exact_or_invalid_judgments(mutate, error):
    payload = routing_payload()
    mutate(payload)

    with pytest.raises(ValueError, match=error):
        audience_routing._validate_output(json.dumps(payload))


def test_output_normalizes_reasons_and_cache_keys_are_stable_and_sharded():
    payload = routing_payload()
    payload["investment"]["reason"] = "  Cost   changes\nunit economics.  "

    result = audience_routing._validate_output(json.dumps(payload))
    keys = {
        audience_routing.prompt_cache_key(f"event-{index}")
        for index in range(50)
    }

    assert result["investment"]["reason"] == "Cost changes unit economics."
    assert 1 < len(keys) <= audience_routing.PROMPT_CACHE_SHARDS
    assert audience_routing.prompt_cache_key("event-1") == (
        audience_routing.prompt_cache_key("event-1")
    )
    assert all(key.startswith("fli:audience-routing:") for key in keys)


def test_prompt_keeps_audiences_distinct_and_forbids_downstream_work():
    prompt = audience_routing.instructions().lower()

    assert "ai engineering" in prompt
    assert "investment" in prompt
    assert "make the two judgments independently" in prompt
    assert "does not reconsider the earlier keep/drop decision" in prompt
    assert "do not write insight prose" in prompt
    assert "do not quote evidence, cite block numbers, create citations" in prompt
    assert "do not infer relevance from popularity" in prompt
    assert "return no keep/drop field" in prompt
