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


class FakeRawResponses(FakeResponses):
    @property
    def with_raw_response(self):
        return self

    def create(self, **kwargs):
        parsed = super().create(**kwargs)
        return SimpleNamespace(
            headers={"x-litellm-response-cost": "0.00125"},
            parse=lambda: parsed,
        )


class FakeRawClient:
    def __init__(self, outputs):
        self.responses = FakeRawResponses(outputs)


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
    assert request["reasoning"] == {"effort": "medium"}
    tags = request["extra_body"]["metadata"]["tags"]
    assert "app:frontier-lab-intelligence" in tags
    assert "pipeline:entity-kind-classification" in tags
    assert "job:entity-kind-classification" in tags
    assert "scope:custom" in tags
    assert "prompt:entity-kind-v2" in tags
    assert any(tag.startswith("run:") for tag in tags)
    assert request["extra_headers"]["x-litellm-tags"] == ",".join(tags)


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
    assert entity_kinds.DEFAULT_MODEL == "gpt-5.6-luna"
    assert entity_kinds.default_reasoning_effort("gpt-5-nano") == "minimal"
    assert entity_kinds.default_reasoning_effort("gpt-5.6-luna") == "medium"


def test_reasoning_effort_is_part_of_resume_identity(tmp_path):
    conn = entity_kinds.connect(tmp_path / "test.db")
    entity = make_unknown(conn)
    client = FakeClient(
        [
            {"classification": "person", "reason": "A full personal name."},
            {"classification": "person", "reason": "A full personal name."},
        ]
    )

    first = entity_kinds.run_classification(
        conn,
        [entity],
        client=client,
        model="gpt-5.6-luna",
        workers=1,
        reasoning_effort_override="none",
    )
    second = entity_kinds.run_classification(
        conn,
        [entity],
        client=client,
        model="gpt-5.6-luna",
        workers=1,
        reasoning_effort_override="medium",
    )

    assert first["classified"] == 1
    assert second["classified"] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM entity_kind_classifications"
    ).fetchone()[0] == 2


def test_proxy_reported_cost_is_captured(tmp_path):
    conn = entity_kinds.connect(tmp_path / "test.db")
    entity = make_unknown(conn)
    client = FakeRawClient(
        [{"classification": "person", "reason": "A full personal name."}]
    )

    summary = entity_kinds.run_classification(
        conn, [entity], client=client, workers=1
    )

    assert summary["reported_cost_usd"] == 0.00125
    assert summary["reported_cost_count"] == 1
    stored = conn.execute(
        "SELECT reported_cost_usd FROM entity_kind_classifications"
    ).fetchone()[0]
    assert stored == 0.00125


def test_legacy_results_migrate_reasoning_effort_without_loss(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    channel_id = channels.upsert_channel(
        conn,
        kind="x",
        key="karpathy",
        label="Andrej Karpathy",
        observed_at="2026-07-10T00:00:00+00:00",
    )
    registry.materialize_unlinked_channels(conn)
    entity_id = conn.execute(
        "SELECT entity_id FROM entity_channels WHERE channel_id = ?",
        (channel_id,),
    ).fetchone()[0]
    conn.executescript(
        """CREATE TABLE entity_kind_classification_runs (
               id INTEGER PRIMARY KEY,
               model TEXT NOT NULL,
               prompt_version TEXT NOT NULL,
               schema_version TEXT NOT NULL,
               prompt_sha256 TEXT NOT NULL,
               scope TEXT NOT NULL,
               requested_count INTEGER NOT NULL,
               skipped_count INTEGER NOT NULL DEFAULT 0,
               success_count INTEGER NOT NULL DEFAULT 0,
               failure_count INTEGER NOT NULL DEFAULT 0,
               input_tokens INTEGER NOT NULL DEFAULT 0,
               output_tokens INTEGER NOT NULL DEFAULT 0,
               estimated_cost_usd REAL NOT NULL DEFAULT 0,
               status TEXT NOT NULL,
               started_at TEXT NOT NULL,
               completed_at TEXT
           );
           CREATE TABLE entity_kind_classifications (
               entity_id INTEGER NOT NULL REFERENCES entities (id),
               input_sha256 TEXT NOT NULL,
               classification TEXT NOT NULL,
               reason TEXT NOT NULL,
               model TEXT NOT NULL,
               response_model TEXT,
               prompt_version TEXT NOT NULL,
               schema_version TEXT NOT NULL,
               response_id TEXT,
               input_tokens INTEGER NOT NULL,
               output_tokens INTEGER NOT NULL,
               estimated_cost_usd REAL NOT NULL,
               run_id INTEGER NOT NULL,
               classified_at TEXT NOT NULL,
               PRIMARY KEY (entity_id, input_sha256, model, prompt_version)
           );"""
    )
    conn.execute(
        """INSERT INTO entity_kind_classification_runs
           (id, model, prompt_version, schema_version, prompt_sha256, scope,
            requested_count, success_count, status, started_at, completed_at)
           VALUES (1, 'gpt-5.6-luna', 'entity-kind-v2',
                   'entity-kind-output-v1', 'prompt-hash', 'calibration',
                   1, 1, 'completed', '2026-07-10', '2026-07-10')"""
    )
    conn.execute(
        """INSERT INTO entity_kind_classifications
           (entity_id, input_sha256, classification, reason, model,
            response_model, prompt_version, schema_version, response_id,
            input_tokens, output_tokens, estimated_cost_usd, run_id,
            classified_at)
           VALUES (?, 'input-hash', 'person', 'A full personal name.',
                   'gpt-5.6-luna', 'gpt-5.6-luna', 'entity-kind-v2',
                   'entity-kind-output-v1', 'response-1', 100, 20,
                   0.00022, 1, '2026-07-10')""",
        (entity_id,),
    )
    conn.commit()

    entity_kinds.ensure_schema(conn)
    entity_kinds.ensure_schema(conn)

    result = conn.execute(
        "SELECT * FROM entity_kind_classifications"
    ).fetchone()
    run = conn.execute(
        "SELECT * FROM entity_kind_classification_runs"
    ).fetchone()
    assert result["classification"] == "person"
    assert result["reasoning_effort"] == "none"
    assert result["reported_cost_usd"] is None
    assert run["reasoning_effort"] == "none"
    assert conn.execute(
        "SELECT COUNT(*) FROM entity_kind_classifications"
    ).fetchone()[0] == 1
