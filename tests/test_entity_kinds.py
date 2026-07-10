import json
from types import SimpleNamespace

import pytest

from fli import channels, entity_kinds, registry


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        output = self.outputs.pop(0)
        if isinstance(output, BaseException):
            raise output
        return SimpleNamespace(
            id=f"response-{len(self.calls)}",
            model=kwargs["model"],
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


class FakePostClient:
    def __init__(self, posts=()):
        self.posts = tuple(posts)
        self.calls = []

    def fetch_recent_authored_posts(self, *, username, limit):
        self.calls.append({"username": username, "limit": limit})
        return self.posts[:limit]


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


def make_unsure(conn, *, handle="opaque", name="Opaque", bio=None):
    entity = make_unknown(conn, handle=handle, name=name, bio=bio)
    conn.execute(
        "UPDATE entities SET kind = 'unsure' WHERE id = ?",
        (entity.entity_id,),
    )
    conn.commit()
    return entity_kinds.read_unsure_inputs(conn)[0]


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


def test_reason_has_no_arbitrary_local_character_limit():
    reason = "This is valid evidence. " * 20

    classification, normalized = entity_kinds._validate_output(
        json.dumps({"classification": "person", "reason": reason})
    )

    assert classification == "person"
    assert len(normalized) > 240


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
    assert "prompt:entity-kind-v3" in tags
    assert any(tag.startswith("run:") for tag in tags)
    assert request["extra_headers"]["x-litellm-tags"] == ",".join(tags)


def test_interrupted_batch_persists_completed_results_for_resume(tmp_path):
    conn = entity_kinds.connect(tmp_path / "test.db")
    first = make_unknown(conn, handle="first", name="First Person")
    make_unknown(conn, handle="second", name="Second Person")
    first, second = entity_kinds.read_unknown_inputs(conn)
    interrupted_client = FakeClient(
        [
            {"classification": "person", "reason": "A full personal name."},
            KeyboardInterrupt(),
        ]
    )

    try:
        entity_kinds.run_classification(
            conn,
            [first, second],
            client=interrupted_client,
            workers=1,
        )
    except KeyboardInterrupt:
        pass
    else:
        raise AssertionError("expected the simulated batch interruption")

    assert conn.execute(
        "SELECT COUNT(*) FROM entity_kind_classifications"
    ).fetchone()[0] == 1
    resumed_client = FakeClient(
        [{"classification": "person", "reason": "A full personal name."}]
    )
    resumed = entity_kinds.run_classification(
        conn,
        [first, second],
        client=resumed_client,
        workers=1,
    )

    assert resumed["skipped"] == 1
    assert resumed["classified"] == 1
    assert len(resumed_client.responses.calls) == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM entity_kind_classifications"
    ).fetchone()[0] == 2


def test_promote_classifications_is_atomic_and_idempotent(tmp_path):
    conn = entity_kinds.connect(tmp_path / "test.db")
    channels.upsert_entity(
        conn,
        kind="organization",
        slug="seeded-lab",
        name="Seeded Lab",
        observed_at="2026-07-10T00:00:00+00:00",
    )
    make_unknown(conn, handle="person", name="Person Name")
    make_unknown(conn, handle="company", name="Company")
    make_unknown(conn, handle="opaque", name="Opaque")
    inputs = entity_kinds.read_unknown_inputs(conn)
    client = FakeClient(
        [
            {"classification": "person", "reason": "A full personal name."},
            {
                "classification": "organization",
                "reason": "The profile represents a company.",
            },
            {
                "classification": "unsure",
                "reason": "The identity evidence is too weak.",
            },
        ]
    )
    entity_kinds.run_classification(conn, inputs, client=client, workers=1)

    first = entity_kinds.promote_classifications(conn)
    second = entity_kinds.promote_classifications(conn)

    assert first["promoted"] == 3
    assert second["promoted"] == 0
    assert first["counts"] == {
        "organization": 2,
        "person": 1,
        "unsure": 1,
    }
    assert conn.execute(
        "SELECT COUNT(*) FROM entities WHERE kind = 'unknown'"
    ).fetchone()[0] == 0


def test_promote_classifications_rejects_incomplete_coverage(tmp_path):
    conn = entity_kinds.connect(tmp_path / "test.db")
    make_unknown(conn, handle="first", name="First Person")
    make_unknown(conn, handle="second", name="Second Person")
    first, _ = entity_kinds.read_unknown_inputs(conn)
    entity_kinds.run_classification(
        conn,
        [first],
        client=FakeClient(
            [{"classification": "person", "reason": "A full personal name."}]
        ),
        workers=1,
    )

    with pytest.raises(RuntimeError, match="lack an accepted classification"):
        entity_kinds.promote_classifications(conn)

    assert conn.execute(
        "SELECT COUNT(*) FROM entities WHERE kind = 'unknown'"
    ).fetchone()[0] == 2


def test_invalid_extra_field_is_terminal_and_recorded(tmp_path):
    conn = entity_kinds.connect(tmp_path / "test.db")
    entity = make_unknown(conn)
    client = FakeClient(
        [
            {
                "classification": "person",
                "reason": "A person.",
                "confidence": 0.9,
            }
        ]
    )

    summary = entity_kinds.run_classification(conn, [entity], client=client, workers=1)

    assert summary["classified"] == 0
    assert summary["failed"] == 1
    assert len(client.responses.calls) == 1
    error = conn.execute(
        "SELECT * FROM entity_kind_classification_errors"
    ).fetchone()
    assert error["error_type"] == "OutputContractError"
    assert error["terminal"] == 1


def test_terminal_error_is_structured(tmp_path):
    conn = entity_kinds.connect(tmp_path / "test.db")
    entity = make_unknown(conn)
    client = FakeClient([RuntimeError("proxy unavailable")])

    summary = entity_kinds.run_classification(
        conn,
        [entity],
        client=client,
        workers=1,
    )

    assert summary["status"] == "partial"
    assert summary["failed"] == 1
    error = conn.execute(
        "SELECT * FROM entity_kind_classification_errors"
    ).fetchone()
    assert error["error_type"] == "RuntimeError"
    assert error["terminal"] == 1


def test_accepted_runtime_defaults_are_frozen():
    assert entity_kinds.DEFAULT_MODEL == "gpt-5.6-luna"
    assert entity_kinds.DEFAULT_REASONING_EFFORT == "medium"
    assert entity_kinds.DEFAULT_WORKERS == 100
    assert entity_kinds.default_reasoning_effort("gpt-5.6-luna") == "medium"
    with pytest.raises(ValueError, match="no evaluated reasoning effort"):
        entity_kinds.default_reasoning_effort("some-new-model")


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


def test_post_enrichment_chains_responses_without_persisting(tmp_path):
    conn = entity_kinds.connect(tmp_path / "test.db")
    entity = make_unsure(conn, handle="jack", name="jack")
    client = FakeClient(
        [
            {
                "classification": "unsure",
                "reason": "The profile does not establish the represented actor.",
            },
            {
                "classification": "person",
                "reason": "The account repeatedly speaks as one individual.",
            },
        ]
    )
    post_client = FakePostClient(
        [
            {
                "id": "1",
                "created_at": "2026-07-09T12:00:00Z",
                "text": "I am building a new tool.",
                "url": "https://x.com/jack/status/1",
                "post_type": "original",
            },
            {
                "id": "2",
                "created_at": "2026-07-08T12:00:00Z",
                "text": "My notes from this week.",
                "url": "https://x.com/jack/status/2",
                "post_type": "quote",
            },
        ]
    )

    first = entity_kinds.run_post_enrichment(
        conn,
        [entity],
        client=client,
        post_client=post_client,
        workers=1,
    )
    assert first["enriched"] == 1
    assert first["counts"]["person"] == 1
    assert first["followups"] == 1
    assert first["recent_posts"] == 2
    assert len(client.responses.calls) == 2
    assert post_client.calls == [{"username": "jack", "limit": 20}]
    profile_request, followup_request = client.responses.calls
    assert profile_request["store"] is True
    assert "previous_response_id" not in profile_request
    assert profile_request["input"][0] == {
        "role": "developer",
        "content": entity_kinds.ENTITY_KIND_INSTRUCTIONS,
    }
    assert "Handle: @jack" in profile_request["input"][1]["content"]
    assert followup_request["store"] is True
    assert followup_request["previous_response_id"] == "response-1"
    assert len(followup_request["input"]) == 1
    followup_prompt = followup_request["input"][0]["content"]
    assert "Replies and retweets have been excluded" in followup_prompt
    assert "I am building a new tool." in followup_prompt
    assert followup_request["text"]["format"] == entity_kinds.CLASSIFICATION_FORMAT
    assert "job:entity-kind-post-enrichment" in profile_request["extra_body"][
        "metadata"
    ]["tags"]
    assert first["items"][0]["profile"]["response_id"] == "response-1"
    assert first["items"][0]["followup"]["response_id"] == "response-2"
    assert len(first["items"][0]["recent_posts"]) == 2
    assert conn.execute(
        "SELECT COUNT(*) FROM entity_kind_classification_runs"
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT kind FROM entities WHERE id = ?",
        (entity.entity_id,),
    ).fetchone()[0] == "unsure"


def test_post_enrichment_stops_when_profile_is_decisive(tmp_path):
    conn = entity_kinds.connect(tmp_path / "test.db")
    entity = make_unsure(conn, handle="product", name="Product")
    client = FakeClient(
        [
            {
                "classification": "organization",
                "reason": "The profile presents a product account.",
            },
        ]
    )
    post_client = FakePostClient()

    summary = entity_kinds.run_post_enrichment(
        conn,
        [entity],
        client=client,
        post_client=post_client,
        workers=1,
    )

    assert summary["status"] == "completed"
    assert summary["counts"]["organization"] == 1
    assert summary["profile_only"] == 1
    assert summary["followups"] == 0
    assert len(client.responses.calls) == 1
    assert post_client.calls == []


def test_post_enrichment_rejects_non_unsure_inputs(tmp_path):
    conn = entity_kinds.connect(tmp_path / "test.db")
    entity = make_unknown(conn)

    with pytest.raises(ValueError, match="only current unsure"):
        entity_kinds.run_post_enrichment(
            conn,
            [entity],
            client=FakeClient([]),
            post_client=FakePostClient(),
            workers=1,
        )


def test_post_enrichment_cli_is_bounded_and_staged(tmp_path, capsys):
    db = tmp_path / "test.db"
    conn = entity_kinds.connect(db)
    entity = make_unsure(conn, handle="jack", name="jack")
    client = FakeClient(
        [
            {
                "classification": "person",
                "reason": "The profile identifies one individual.",
            },
        ]
    )
    post_client = FakePostClient()

    code = entity_kinds.main(
        ["enrich", "--db", str(db), "--limit", "1", "--workers", "1"],
        client_factory=lambda: client,
        post_client_factory=lambda: post_client,
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["scope"] == "posts-limited"
    assert payload["requested"] == 1
    assert payload["enriched"] == 1
    assert conn.execute(
        "SELECT kind FROM entities WHERE id = ?",
        (entity.entity_id,),
    ).fetchone()[0] == "unsure"
