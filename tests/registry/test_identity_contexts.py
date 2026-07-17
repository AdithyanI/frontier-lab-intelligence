import json
from types import SimpleNamespace

import pytest

from fli.registry import identity_contexts


class FakeResponses:
    def __init__(self, payload, *, output):
        self.payload = payload
        self.output = output
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = SimpleNamespace(
            id="identity-response-1",
            model=kwargs["model"],
            status="completed",
            output_text=json.dumps(self.payload),
            usage=SimpleNamespace(
                input_tokens=2_000,
                input_tokens_details=SimpleNamespace(
                    cached_tokens=1_024,
                    cache_write_tokens=0,
                ),
                output_tokens=100,
            ),
        )
        response.model_dump = lambda **_: {
            "id": response.id,
            "model": response.model,
            "status": response.status,
            "output_text": response.output_text,
            "usage": {
                "input_tokens": 2_000,
                "input_tokens_details": {
                    "cached_tokens": 1_024,
                    "cache_write_tokens": 0,
                },
                "output_tokens": 100,
            },
            "output": self.output,
        }
        return response


def payload():
    return {
        "identity_status": "resolved",
        "canonical_name": "Jarred Sumner",
        "current_role": "Technical staff",
        "current_organization": "Anthropic ([official.example](https://official.example))",
        "known_for": ["Created Bun"],
        "frontier_ai_relevance": "Works at a frontier model laboratory.",
        "research_summary": "The exact account belongs to Jarred Sumner.",
    }


def make_input():
    return identity_contexts.IdentityInput(
        entity_id=42,
        handle="jarredsumner",
        display_name="Jarred Sumner",
        profile_url="https://x.com/jarredsumner",
        recent_posts=({"text": "Rewriting Bun in Rust", "created_at": "2026"},),
    )


def test_missing_bio_enrichment_requires_grounded_search_and_is_cacheable():
    output = [
        {
            "type": "web_search_call",
            "action": {
                "type": "search",
                "queries": ["Jarred Sumner current role"],
                "sources": [
                    {
                        "url": "https://example.com/official",
                        "title": "Official biography",
                    }
                ],
            },
        }
    ]
    client = SimpleNamespace(responses=FakeResponses(payload(), output=output))

    result = identity_contexts.enrich_one(client, make_input(), run="calibration")

    request = client.responses.calls[0]
    assert request["model"] == "gpt-5.6-luna"
    assert request["reasoning"] == {"effort": "high"}
    assert request["prompt_cache_retention"] == "24h"
    assert len(request["instructions"].split()) > 1_024
    assert request["tools"] == [
        {"type": "web_search", "search_context_size": "medium"}
    ]
    assert request["tool_choice"] == "required"
    assert request["text"]["format"] == identity_contexts.OUTPUT_FORMAT
    assert request["prompt_cache_key"] == identity_contexts.prompt_cache_key(42)
    assert request["store"] is False
    assert result["current_organization"] == "Anthropic"
    assert result["cached_tokens"] == 1_024
    assert result["consulted_sources"][0]["url"].startswith("https://")


def test_enrichment_rejects_a_response_without_required_search_evidence():
    client = SimpleNamespace(responses=FakeResponses(payload(), output=[]))

    with pytest.raises(ValueError, match="required web search"):
        identity_contexts.enrich_one(client, make_input(), run="calibration")


def test_identity_cache_keys_use_a_small_stable_shard_set():
    keys = {identity_contexts.prompt_cache_key(i) for i in range(256)}
    assert len(keys) == identity_contexts.PROMPT_CACHE_SHARDS
    assert all(
        key.startswith("fli:identity-context:identity-context-v1:shard-")
        for key in keys
    )
