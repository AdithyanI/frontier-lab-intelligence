import json
from types import SimpleNamespace

import pytest

from fli import insight_triage


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
        payload = (
            self.payload[len(self.calls) - 1]
            if isinstance(self.payload, list)
            else self.payload
        )
        response = SimpleNamespace(
            id=f"resp-triage-{len(self.calls)}",
            model=kwargs["model"],
            status="completed",
            output_text=json.dumps(payload),
            usage=SimpleNamespace(
                input_tokens=2_000,
                input_tokens_details=SimpleNamespace(
                    cached_tokens=1_280,
                    cache_write_tokens=0,
                ),
                output_tokens=80,
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


def make_envelope():
    return insight_triage.EnvelopeInput(
        event_id="event-1",
        day="2026-07-11",
        root={
            "post_id": "root-1",
            "author": "@founder",
            "post_type": "quote",
            "text": "compute daddy has spoken",
            "quoted_target_handle": "@researcher",
        },
        related_posts=(
            {
                "post_id": "child-1",
                "relation": "quote",
                "same_author_as_root": False,
                "author": "@expert",
                "text": "Post-training data creates a compounding advantage.",
            },
        ),
        urls=(
            {
                "post_id": "child-1",
                "url": "https://example.com/research",
            },
        ),
        embedded_artifacts=(
            {
                "post_id": "child-1",
                "kind": "link_card",
                "title": "A post-training research note",
                "preview": "Experiments on post-training data and model behavior.",
                "url": "https://example.com/research",
            },
        ),
    )


def keep_child_payload():
    return {
        "decision": "keep",
        "reason": "The child states a concrete thesis about post-training data.",
    }


def test_schema_contains_only_the_envelope_decision_and_reason():
    schema = insight_triage.OUTPUT_FORMAT["schema"]

    assert set(schema["properties"]) == {"decision", "reason"}
    assert schema["additionalProperties"] is False


def test_render_input_preserves_relationships_without_ranking_features():
    rendered = insight_triage.render_input(make_envelope())

    assert "[author=@founder | type=quote]" in rendered
    assert "[relation=quote | other-author | author=@expert]" in rendered
    assert "https://example.com/research" in rendered
    assert "PROVIDER-SUPPLIED ARTIFACT METADATA" in rendered
    assert "A post-training research note" in rendered
    assert "RETWEET SUMMARY" not in rendered
    assert "post_id=" not in rendered
    assert "attention" not in rendered.lower()
    assert "engagement" not in rendered.lower()
    assert "followers" not in rendered.lower()


def test_request_uses_cacheable_prefix_structured_output_and_litellm_tags():
    client = FakeClient(keep_child_payload())

    result = insight_triage.evaluate_one(
        client,
        make_envelope(),
        run="calibration-v2",
    )

    request = client.responses.with_raw_response.calls[0]
    assert request["model"] == "gpt-5.6-luna"
    assert request["reasoning"] == {"effort": "medium"}
    assert request["prompt_cache_retention"] == "24h"
    assert request["instructions"] == insight_triage.instructions()
    assert len(request["instructions"].split()) > 1_024
    assert request["prompt_cache_key"] == insight_triage.prompt_cache_key(
        make_envelope().event_id
    )
    assert request["text"]["format"] == insight_triage.OUTPUT_FORMAT
    assert request["store"] is False
    assert "tools" not in request
    assert request["extra_body"]["metadata"]["tags"] == result["request_tags"]
    assert request["extra_headers"]["x-litellm-tags"] == ",".join(
        result["request_tags"]
    )
    assert result["decision"] == "keep"
    assert result["cached_tokens"] == 1_280
    assert result["reported_cost_usd"] == pytest.approx(0.0042)


def test_prompt_cache_keys_are_stable_and_sharded_by_event():
    keys = {
        insight_triage.prompt_cache_key(f"event-{index}")
        for index in range(100)
    }

    assert 1 < len(keys) <= insight_triage.PROMPT_CACHE_SHARDS
    assert insight_triage.prompt_cache_key("event-1") == (
        insight_triage.prompt_cache_key("event-1")
    )
    assert all(key.startswith("fli:cited-insights-triage:") for key in keys)


def test_output_rejects_fields_outside_the_minimal_contract():
    payload = keep_child_payload()
    payload["category"] = "strategy_or_policy"

    with pytest.raises(ValueError, match="exact triage schema"):
        insight_triage._validate_output(json.dumps(payload))


def test_prompt_keeps_time_bounded_views_but_excludes_popularity():
    prompt = insight_triage.instructions().lower()

    assert "agentic coding is a completely different world" in prompt
    assert "do not infer quality from engagement" in prompt
    assert "a noisy root can contain a valuable quote or reply" in prompt
    assert "first-hand product experience" in prompt
    assert "provider-supplied titles" in prompt
    assert "signal_post_ids" not in prompt
    assert "category" not in prompt
