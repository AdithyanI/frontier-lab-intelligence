import json
from types import SimpleNamespace

import pytest

from fli import relevance


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
        response.model_dump = lambda: {
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


def test_cli_requires_explicit_scope_before_paid_run(tmp_path):
    with pytest.raises(SystemExit):
        relevance.main(["run", "--run", "test", "--output", str(tmp_path / "x")])
