import json
from types import SimpleNamespace

from fli import channels, entity_kinds, registry


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return SimpleNamespace(
            id=f"response-{len(self.calls)}",
            model="gpt-5-nano-2026-01-01",
            status="completed",
            output_text=json.dumps(output),
            output=[],
            usage=SimpleNamespace(input_tokens=100, output_tokens=20),
        )


class FakeClient:
    def __init__(self, outputs):
        self.responses = FakeResponses(outputs)


def make_unknown(conn, *, handle="karpathy", name="Andrej Karpathy", bio=None):
    channel_id = channels.upsert_channel(
        conn,
        kind="x",
        key=handle,
        label=name,
        observed_at="2026-07-10T00:00:00+00:00",
    )
    if bio is not None:
        channels.observe_channel(
            conn,
            channel_id=channel_id,
            source="x_profile",
            metric="bio",
            value=bio,
            observed_at="2026-07-10T00:00:00+00:00",
        )
    registry.materialize_unlinked_channels(
        conn, observed_at="2026-07-10T00:00:00+00:00"
    )
    return entity_kinds.read_unknown_inputs(conn)[0]


def test_schema_and_model_payload_are_minimal(tmp_path):
    conn = entity_kinds.connect(tmp_path / "test.db")
    entity = make_unknown(
        conn,
        bio="I like training large deep neural nets.",
    )

    assert set(entity.model_payload) == {
        "handle",
        "display_name",
        "bio",
        "profile_url",
    }
    schema = entity_kinds.CLASSIFICATION_FORMAT["schema"]
    assert set(schema["properties"]) == {"classification", "reason"}
    assert schema["required"] == ["classification", "reason"]
    assert schema["additionalProperties"] is False


def test_completed_result_is_resumable_without_duplicate_call(tmp_path):
    conn = entity_kinds.connect(tmp_path / "test.db")
    entity = make_unknown(conn, bio="Researcher and engineer.")
    client = FakeClient(
        [{"classification": "person", "reason": "The profile describes an individual."}]
    )

    first = entity_kinds.run_classification(
        conn, [entity], client=client, workers=1
    )
    second = entity_kinds.run_classification(
        conn, [entity], client=client, workers=1
    )

    assert first["classified"] == 1
    assert second["classified"] == 0
    assert second["skipped"] == 1
    assert len(client.responses.calls) == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM entity_kind_classifications"
    ).fetchone()[0] == 1
    request = client.responses.calls[0]
    assert set(json.loads(request["input"])) == {
        "handle",
        "display_name",
        "bio",
        "profile_url",
    }
    assert request["text"]["format"] == entity_kinds.CLASSIFICATION_FORMAT
    assert request["reasoning"] == {"effort": "minimal"}


def test_invalid_extra_field_is_retried_and_recorded(tmp_path):
    conn = entity_kinds.connect(tmp_path / "test.db")
    entity = make_unknown(conn)
    client = FakeClient(
        [
            {
                "classification": "person",
                "reason": "A person.",
                "confidence": 0.9,
            },
            {
                "classification": "unsure",
                "reason": "The available identity evidence is too weak.",
            },
        ]
    )

    summary = entity_kinds.run_classification(
        conn, [entity], client=client, workers=1
    )

    assert summary["classified"] == 1
    assert len(client.responses.calls) == 2
    error = conn.execute(
        "SELECT * FROM entity_kind_classification_errors"
    ).fetchone()
    assert error["error_type"] == "OutputContractError"
    assert error["terminal"] == 0


def test_terminal_error_is_structured(tmp_path):
    conn = entity_kinds.connect(tmp_path / "test.db")
    entity = make_unknown(conn)
    client = FakeClient([RuntimeError("proxy unavailable")])

    summary = entity_kinds.run_classification(
        conn,
        [entity],
        client=client,
        workers=1,
        max_attempts=1,
    )

    assert summary["status"] == "partial"
    assert summary["failed"] == 1
    error = conn.execute(
        "SELECT * FROM entity_kind_classification_errors"
    ).fetchone()
    assert error["error_type"] == "RuntimeError"
    assert error["terminal"] == 1


def test_full_run_estimate_scales_calibration_usage():
    estimate = entity_kinds.estimate_full_run(
        calibration_summary={
            "classified": 10,
            "input_tokens": 1_000,
            "output_tokens": 200,
            "estimated_cost_usd": 0.00013,
        },
        full_count=2_956,
    )

    assert estimate == {
        "entities": 2_956,
        "estimated_input_tokens": 295_600,
        "estimated_output_tokens": 59_120,
        "estimated_cost_usd": 0.038428,
    }


def test_reasoning_effort_matches_model_family():
    assert entity_kinds.reasoning_effort("gpt-5-nano") == "minimal"
    assert entity_kinds.reasoning_effort("gpt-5.6-luna") == "none"
