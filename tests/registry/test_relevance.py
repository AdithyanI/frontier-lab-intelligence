import json
from types import SimpleNamespace

import pytest

from fli import llm_responses
from fli.registry import relevance


class FakeResponses:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = SimpleNamespace(
            id="response-1",
            model=kwargs["model"],
            status="completed",
            output_text=json.dumps(self.payload),
            usage=SimpleNamespace(input_tokens=100, output_tokens=25),
        )
        response.model_dump = lambda **_: {
            "id": response.id,
            "model": response.model,
            "status": response.status,
            "output_text": response.output_text,
            "usage": {"input_tokens": 100, "output_tokens": 25},
            "output": [
                {
                    "type": "web_search_call",
                    "action": {
                        "type": "search",
                        "queries": ["OpenAI official research"],
                        "sources": [
                            {"url": "https://openai.com/research", "type": "url"}
                        ],
                    },
                }
            ],
        }
        return response


class FakeClient:
    def __init__(self, payload):
        self.responses = FakeResponses(payload)


def make_entity():
    return relevance.RelevanceInput(
        entity_id=6,
        structural_kind="organization",
        name="OpenAI",
        slug="openai",
        is_curated_lab=True,
        channels=(
            {
                "kind": "x",
                "key": "openai",
                "url": "https://x.com/openai",
                "bio": "Ensuring AGI benefits all of humanity.",
            },
        ),
    )


def keep_payload():
    return {
        "entity_id": 6,
        "decision": "keep",
        "relevance_basis": "lab_activity",
        "audience": "both",
        "reason": "OpenAI develops frontier models and publishes primary research.",
        "current_connection": "Frontier model development and deployment.",
        "confidence": "high",
        "evidence_urls": ["https://openai.com/research"],
    }


def test_request_requires_high_context_web_search_and_structured_output():
    client = FakeClient(keep_payload())
    result = relevance.audit_one(client, make_entity(), run="calibration")

    request = client.responses.calls[0]
    assert request["model"] == "gpt-5.6-terra"
    assert request["prompt_cache_key"] == relevance.prompt_cache_key(6)
    assert request["prompt_cache_retention"] == "24h"
    assert "max_output_tokens" not in request
    assert request["reasoning"] == {"effort": "high"}
    assert request["tools"] == [
        {
            "type": "web_search",
            "search_context_size": "high",
            "return_token_budget": "unlimited",
        }
    ]
    assert request["tool_choice"] == "required"
    assert request["include"] == ["web_search_call.action.sources"]
    assert request["text"]["format"] == relevance.OUTPUT_FORMAT
    assert "followers" not in request["input"]
    assert result["decision"] == "keep"
    assert result["consulted_sources"][0]["url"] == "https://openai.com/research"


@pytest.mark.parametrize(
    ("decision", "basis", "audience"),
    [
        ("keep", "out_of_scope", "both"),
        ("keep", "lab_activity", "neither"),
        ("remove", "lab_activity", "ai_team"),
        ("review", "lab_activity", "ai_team"),
    ],
)
def test_output_rejects_inconsistent_decision_dimensions(
    decision, basis, audience
):
    payload = keep_payload()
    payload.update(
        decision=decision,
        relevance_basis=basis,
        audience=audience,
    )
    with pytest.raises(ValueError):
        relevance._validate_output(json.dumps(payload), entity_id=6)


def test_prompt_is_versioned_and_contains_product_boundary():
    prompt = relevance.instructions()
    assert relevance.PROMPT_VERSION == "registry-relevance-v1"
    assert "SemiAnalysis" in prompt
    assert "TechCrunch" in prompt
    assert "Do not use follower count" in prompt


def test_prompt_cache_key_is_stable_and_sharded():
    assert relevance.prompt_cache_key(6) == relevance.prompt_cache_key(6)
    assert relevance.prompt_cache_key(6).startswith(
        "fli:registry-relevance:registry-relevance-v1:shard-"
    )
    assert (
        len({relevance.prompt_cache_key(i) for i in range(256)})
        == relevance.PROMPT_CACHE_SHARDS
    )


def test_relevance_uses_shared_prompt_cache_sharding():
    assert relevance.prompt_cache_key(6) == llm_responses.sharded_prompt_cache_key(
        namespace="registry-relevance",
        prompt_version=relevance.PROMPT_VERSION,
        scope_key=6,
        shards=relevance.PROMPT_CACHE_SHARDS,
    )


def test_output_text_ignores_nullable_translated_blocks():
    assert llm_responses.output_text(
        {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": None},
                        {"type": "output_text", "text": '{"decision":"keep"}'},
                    ],
                }
            ]
        }
    ) == '{"decision":"keep"}'


def test_translated_claude_search_is_normalized_with_cited_urls():
    response = {
        "output": [
            {
                "type": "reasoning",
                "content": [{"type": "output_text", "text": "private analysis"}],
            },
            {
                "type": "message",
                "content": [{"type": "output_text", "text": '{"decision":"keep"}'}],
            },
            {
                "type": "function_call",
                "name": "web_search",
                "arguments": '{"query":"OpenAI research"}',
            },
        ]
    }
    assert llm_responses.output_text(response) == '{"decision":"keep"}'
    actions, sources = llm_responses.web_evidence(
        response,
        cited_urls=["https://openai.com/research"],
        require_search_action=True,
    )
    assert actions == [
        {
            "type": "search",
            "query": "OpenAI research",
            "translated_from": "function_call",
        }
    ]
    assert sources == [
        {"url": "https://openai.com/research", "type": "model_citation"}
    ]


def test_claude_can_finish_after_required_native_web_search():
    assert llm_responses.required_web_search_tool_choice("gpt-5.6-terra") == "required"
    assert llm_responses.required_web_search_tool_choice("claude-opus-4-6") == "auto"


def test_cli_requires_explicit_scope_before_paid_run(tmp_path):
    with pytest.raises(SystemExit):
        relevance.main(["run", "--run", "test", "--output", str(tmp_path / "x")])


def test_checkpoint_reuses_only_matching_completed_results(tmp_path):
    entity = make_entity()
    result = {
        **keep_payload(),
        "input_sha256": entity.input_sha256,
        "model": relevance.DEFAULT_MODEL,
        "reasoning_effort": relevance.DEFAULT_REASONING_EFFORT,
        "prompt_version": relevance.PROMPT_VERSION,
    }
    path = tmp_path / "checkpoint.jsonl"
    with path.open("w") as stream:
        relevance._append_checkpoint(stream, "result", result)

    completed, errors = relevance._load_checkpoint(
        path,
        by_id={entity.entity_id: entity},
        model=relevance.DEFAULT_MODEL,
        effort=relevance.DEFAULT_REASONING_EFFORT,
    )

    assert completed == {entity.entity_id: result}
    assert errors == {}
