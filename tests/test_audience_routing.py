import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from fli import audience_routing


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
            audience_routing.EvidenceSource(
                source_type="x_post",
                source_id="source-secret-root",
                url="https://example.com/private-root",
                author="Satya Nadella",
                relation="root",
                text="The new system reduced inference latency under our workload.",
            ),
            audience_routing.EvidenceSource(
                source_type="artifact",
                source_id="source-secret-article",
                url="https://example.com/private-article",
                author="Satya Nadella",
                title="Serving system report",
                relation="self_published_artifact",
                text="Tests report lower latency and lower serving cost.",
                section_ordinal=2,
                source_char_start=100,
                source_char_end=154,
            ),
            audience_routing.EvidenceSource(
                source_type="x_post",
                source_id="source-secret-reaction",
                url="https://example.com/private-reaction",
                author="Independent Engineer",
                relation="quote",
                text="This serving result should be tested under burst traffic &amp; load.",
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
        assert judgment["properties"]["reason"] == {
            "type": "string",
            "minLength": 1,
        }


def test_v6_prompt_uses_soft_reason_word_guidance_without_truncation():
    prompt = audience_routing.instructions()

    assert audience_routing.PROMPT_VERSION == "audience-routing-v6"
    assert "Aim for roughly 40 to 50 words" in prompt
    assert "guidance, not a hard limit" in prompt
    assert "never truncate, reject, or add filler" in prompt


def test_v6_prompt_defines_the_two_approved_audience_boundaries():
    prompt = audience_routing.instructions()

    assert "temporary access extensions or resets" in prompt
    assert "usage or rate limits are not sufficient by themselves" in prompt
    assert "persistent operational constraint" in prompt
    assert "measured effect on cost, reliability, throughput" in prompt
    assert "promise or announcement that efficiency or behavior will improve" in prompt
    assert "not a measured effect" in prompt
    assert "independently verified before marking it relevant" in prompt
    assert "can qualify even when it is anecdotal or unquantified" in prompt
    assert "Do not reject it for those reasons alone" in prompt
    assert "reason must clearly preserve its epistemic status" in prompt


def test_render_input_uses_readable_hierarchy_before_separate_reactions():
    rendered = audience_routing.render_input(make_packet())

    assert "evidence_packet:" in rendered
    assert "  primary_source:" in rendered
    assert '    author: "Satya Nadella"' in rendered
    assert "    post:" in rendered
    assert "      kind: x_post" in rendered
    assert "      - kind: authored_artifact" in rendered
    assert '        title: "Serving system report"' in rendered
    assert "  independent_reactions:" in rendered
    assert "    - kind: quote_post" in rendered
    assert '      author: "Independent Engineer"' in rendered
    assert "burst traffic & load" in rendered
    assert "&amp;" not in rendered
    assert rendered.index("    post:") < rendered.index(
        "      - kind: authored_artifact"
    ) < rendered.index("  independent_reactions:")
    assert "reduced inference latency" in rendered
    assert "event-secret-42" not in rendered
    assert "source-secret-root" not in rendered
    assert "source-secret-article" not in rendered
    assert "source-secret-reaction" not in rendered
    assert "https://example.com" not in rendered
    assert "relation:" not in rendered
    assert "ref:" not in rendered
    assert "CDATA" not in rendered
    assert "<QUOTE_POST" not in rendered
    assert "section_ordinal" not in rendered
    assert "source_char_start" not in rendered
    assert "feed_rank" not in rendered
    assert "triage" not in rendered.lower()


def test_render_input_replaces_link_only_post_and_omits_transport_reaction():
    packet = make_packet()
    root = replace(packet.sources[0], text="https://t.co/example")
    transport_reaction = audience_routing.EvidenceSource(
        source_type="x_post",
        source_id="transport-reaction",
        url="https://example.com/transport-reaction",
        author="Link Only",
        relation="quote",
        text="https://t.co/another-link",
    )
    rendered = audience_routing.render_input(
        replace(packet, sources=(root, *packet.sources[1:], transport_reaction))
    )

    assert "      kind: artifact_link" in rendered
    assert "https://t.co/example" not in rendered
    assert "Link Only" not in rendered
    assert "https://t.co/another-link" not in rendered


def test_render_input_keeps_short_reactions_and_cleans_duplicates_and_links():
    packet = make_packet()
    inline_link = audience_routing.EvidenceSource(
        source_type="x_post",
        source_id="inline-link",
        url="https://example.com/inline-link",
        author="Useful Reaction",
        relation="quote",
        text=(
            "This adds a distinct reliability implication "
            "https://t.co/opaque for production evaluation."
        ),
    )
    short_reaction = audience_routing.EvidenceSource(
        source_type="x_post",
        source_id="short-reaction",
        url="https://example.com/short-reaction",
        author="Short Reaction",
        relation="quote",
        text="Good, but late.",
    )
    duplicate_reaction = audience_routing.EvidenceSource(
        source_type="x_post",
        source_id="duplicate-reaction",
        url="https://example.com/duplicate-reaction",
        author="Duplicate Reaction",
        relation="quote",
        text=(
            "Tests report lower latency and lower serving cost. "
            "Tests report lower latency and lower serving cost."
        ),
    )
    artifact = replace(
        packet.sources[1],
        text=(
            "Tests report lower latency and lower serving cost. "
            "Tests report lower latency and lower serving cost."
        ),
    )
    rendered = audience_routing.render_input(
        replace(
            packet,
            sources=(
                packet.sources[0],
                artifact,
                packet.sources[2],
                inline_link,
                short_reaction,
                duplicate_reaction,
            ),
        )
    )

    assert "Useful Reaction" in rendered
    assert "distinct reliability implication" in rendered
    assert "https://t.co/opaque" not in rendered
    assert "Short Reaction" in rendered
    assert "Good, but late." in rendered
    assert "Duplicate Reaction" not in rendered


def test_evidence_hash_binds_hidden_provenance_while_input_hash_does_not():
    packet = make_packet()
    changed_source = replace(
        packet.sources[0],
        source_id="different-source-id",
        url="https://example.com/different-url",
    )
    changed_packet = replace(
        packet,
        sources=(changed_source, *packet.sources[1:]),
    )

    assert changed_packet.evidence_sha256 != packet.evidence_sha256
    assert changed_packet.input_sha256 == packet.input_sha256


def test_request_uses_mini_high_minimal_cache_tags_and_telemetry():
    client = FakeClient(routing_payload())

    result = audience_routing.evaluate_one(
        client,
        make_packet(),
        run="first-cohort",
    )

    request = client.responses.with_raw_response.calls[0]
    assert request["model"] == "gpt-5.4-mini"
    assert request["reasoning"] == {"effort": "high"}
    assert "prompt_cache_retention" not in request
    assert request["prompt_cache_key"] == audience_routing.PROMPT_CACHE_KEY
    assert request["instructions"] == audience_routing.instructions()
    assert len(request["instructions"].split()) >= 1_024
    assert request["input"] == audience_routing.render_input(make_packet())
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
        "prompt:audience-routing-v6",
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


def test_output_normalizes_reasons():
    payload = routing_payload()
    payload["investment"]["reason"] = "  Cost   changes\nunit economics.  "

    result = audience_routing._validate_output(json.dumps(payload))
    assert result["investment"]["reason"] == "Cost changes unit economics."


def test_prompt_explains_product_evidence_and_independent_audience_job():
    prompt = audience_routing.instructions().lower()

    assert "frontier lab intelligence" in prompt
    assert "current system collects public posts from x" in prompt
    assert "groups connected material into one evidence packet" in prompt
    assert "primary post" in prompt
    assert "full text of an available artifact" in prompt
    assert "separate reactions" in prompt
    assert "ai engineering" in prompt
    assert "investment" in prompt
    assert "decide independently" in prompt
    assert "earlier feed stage" not in prompt
    assert "keep/drop" not in prompt
    assert "insight prose" not in prompt
