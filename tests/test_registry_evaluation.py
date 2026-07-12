import json
from types import SimpleNamespace

import pytest

from fli import registry_evaluation


class FakeResponses:
    def __init__(self, payload, *, output=()):
        self.payload = payload
        self.output = list(output)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = SimpleNamespace(
            id="response-1",
            model=kwargs["model"],
            status="completed",
            output_text=json.dumps(self.payload),
            usage=SimpleNamespace(
                input_tokens=1_900,
                input_tokens_details=SimpleNamespace(
                    cached_tokens=1_536,
                    cache_write_tokens=0,
                ),
                output_tokens=45,
            ),
        )
        response.model_dump = lambda **_: {
            "id": response.id,
            "model": response.model,
            "status": response.status,
            "output_text": response.output_text,
            "usage": {
                "input_tokens": 1_900,
                "input_tokens_details": {
                    "cached_tokens": 1_536,
                    "cache_write_tokens": 0,
                },
                "output_tokens": 45,
            },
            "output": self.output,
        }
        return response


class FakeClient:
    def __init__(self, payload, *, output=()):
        self.responses = FakeResponses(payload, output=output)


def make_entity(entity_id=6):
    return registry_evaluation.EvaluationInput(
        entity_id=entity_id,
        handle="karpathy",
        display_name="Andrej Karpathy",
        bio="I like to train deep neural nets.",
        profile_url="https://x.com/karpathy",
        recent_posts=(
            {
                "text": "New technical note on language-model training.",
                "created_at": "2026-07-11T10:00:00Z",
                "post_type": "original",
            },
        ),
    )


def keep_person_payload():
    return {
        "kind": "person",
        "kind_reason": "The account speaks in an individual's personal voice.",
        "registry_decision": "keep",
        "registry_decision_reason": (
            "The individual repeatedly publishes original frontier-AI work."
        ),
    }


def test_combined_schema_keeps_kind_and_registry_decision_independent():
    schema = registry_evaluation.OUTPUT_FORMAT["schema"]
    assert set(schema["properties"]) == {
        "kind",
        "kind_reason",
        "registry_decision",
        "registry_decision_reason",
    }
    assert schema["required"] == [
        "kind",
        "kind_reason",
        "registry_decision",
        "registry_decision_reason",
    ]
    assert schema["additionalProperties"] is False


def test_request_uses_optional_open_web_search_and_cacheable_prefix():
    client = FakeClient(keep_person_payload())

    result = registry_evaluation.evaluate_one(
        client, make_entity(), run="calibration"
    )

    request = client.responses.calls[0]
    assert request["instructions"] == registry_evaluation.instructions()
    assert len(request["instructions"].split()) > 1_024
    assert request["input"].startswith("Evaluate this X account")
    assert request["tools"] == [{"type": "web_search"}]
    assert request["tool_choice"] == "auto"
    assert request["include"] == ["web_search_call.action.sources"]
    assert "max_tool_calls" not in request
    assert "search_context_size" not in request["tools"][0]
    assert "return_token_budget" not in request["tools"][0]
    assert request["store"] is False
    assert request["prompt_cache_key"] == registry_evaluation.prompt_cache_key(6)
    assert result["kind"] == "person"
    assert result["registry_decision"] == "keep"
    assert result["cached_tokens"] == 1_536
    assert result["cache_write_tokens"] == 0
    assert result["web_actions"] == []
    assert result["consulted_sources"] == []


def test_cache_keys_are_stable_shards_for_shared_prompt():
    assert registry_evaluation.prompt_cache_key(6) == (
        registry_evaluation.prompt_cache_key(6)
    )
    keys = {registry_evaluation.prompt_cache_key(i) for i in range(256)}
    assert len(keys) > 32
    assert all(
        key.startswith(
            "fli:registry-evaluation:registry-evaluation-v3:shard-"
        )
        for key in keys
    )


def test_prompt_is_detailed_without_unavailable_ranking_warnings():
    prompt = registry_evaluation.instructions()
    assert "TWO INDEPENDENT DECISIONS" in prompt
    assert "Search the open web; do not limit research to X" in prompt
    assert "registry_decision_reason" in prompt
    assert "Grounded identity context" in prompt
    assert "Recent posts describe recent public output" in prompt
    assert "graph position" not in prompt.lower()
    assert "cohort follow" not in prompt.lower()
    assert "follower count" not in prompt.lower()


def test_unsure_actor_cannot_be_kept():
    payload = keep_person_payload()
    payload.update(kind="unsure")
    with pytest.raises(ValueError, match="unsure actor"):
        registry_evaluation._validate_output(json.dumps(payload))


def test_optional_web_search_evidence_is_retained_when_used():
    output = [
        {
            "type": "web_search_call",
            "action": {
                "type": "search",
                "queries": ["Andrej Karpathy official current work"],
                "sources": [
                    {
                        "url": "https://karpathy.ai",
                        "title": "Andrej Karpathy",
                        "type": "url",
                    }
                ],
            },
        }
    ]
    client = FakeClient(keep_person_payload(), output=output)

    result = registry_evaluation.evaluate_one(
        client, make_entity(), run="calibration"
    )

    assert result["web_actions"][0]["type"] == "search"
    assert result["consulted_sources"][0]["url"] == "https://karpathy.ai"


def test_verified_identity_context_is_rendered_separately_from_source_bio():
    entity = make_entity()
    entity = registry_evaluation.EvaluationInput(
        **{
            **entity.__dict__,
            "bio": None,
            "identity_context": {
                "identity_status": "resolved",
                "canonical_name": "Jarred Sumner",
                "current_role": "Technical staff",
                "current_organization": "Anthropic",
                "known_for": ["Created Bun"],
                "frontier_ai_relevance": "Works at a frontier lab.",
                "research_summary": "Resolved through official evidence.",
                "consulted_sources": [
                    {"title": "Official page", "url": "https://example.com"}
                ],
            },
        }
    )

    rendered = registry_evaluation.render_input(entity)

    assert "Bio: No bio observed." in rendered
    assert "Grounded identity context" in rendered
    assert "Current organization: Anthropic" in rendered
    assert "Official page: https://example.com" in rendered
