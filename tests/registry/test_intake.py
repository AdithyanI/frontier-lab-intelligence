import json
from types import SimpleNamespace

import pytest

from fli.ingestion import sources
from fli.registry import channels, intake as registry_intake
from fli.registry import store as registry
from fli.registry import view as registry_view


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        payload = self.outputs.pop(0)
        response = SimpleNamespace(
            id=f"response-{len(self.calls)}",
            model=kwargs["model"],
            status="completed",
            output_text=json.dumps(payload),
            output=[],
            usage=SimpleNamespace(input_tokens=120, output_tokens=24),
        )
        response.model_dump = lambda **_: {
            "id": response.id,
            "model": response.model,
            "status": response.status,
            "output_text": response.output_text,
            "output": [],
            "usage": {"input_tokens": 120, "output_tokens": 24},
        }
        return response


class FakeClient:
    def __init__(self, outputs=()):
        self.responses = FakeResponses(outputs)


class FakePostClient:
    def __init__(self, *, followers=2_000, protected=False, posts=()):
        self.followers = followers
        self.protected = protected
        self.posts = tuple(posts)
        self.profile_calls = []
        self.post_calls = []

    def fetch_user(self, *, username):
        self.profile_calls.append(username)
        return {
            "id": f"x-{username}",
            "userName": username,
            "name": "Candidate Name",
            "description": "AI researcher building model systems.",
            "followers": self.followers,
            "protected": self.protected,
        }

    def fetch_recent_authored_posts(self, *, username, limit, profile=None):
        self.post_calls.append((username, limit))
        return self.posts[:limit]


def test_normalize_x_profile_accepts_url_handle_and_rejects_post_urls():
    assert registry_intake.normalize_x_profile("https://x.com/ThSottiaux") == (
        "thsottiaux",
        "https://x.com/thsottiaux",
    )
    assert registry_intake.normalize_x_profile("@thsottiaux")[0] == "thsottiaux"
    with pytest.raises(ValueError, match="profile URL"):
        registry_intake.normalize_x_profile("https://x.com/thsottiaux/status/1")
    with pytest.raises(ValueError, match="HTTPS x.com"):
        registry_intake.normalize_x_profile("https://example.com/thsottiaux")


def test_existing_active_profile_returns_without_provider_or_model_calls(tmp_path):
    conn = channels.connect(tmp_path / "registry.db")
    materialized = sources.persist_x_profile(
        conn,
        profile={
            "id": "612",
            "userName": "thsottiaux",
            "name": "Tibo",
            "description": "AI researcher",
            "followers": 9_000,
            "protected": False,
        },
    )
    conn.execute(
        "UPDATE entities SET kind = 'person' WHERE id = ?",
        (materialized["entity_id"],),
    )
    conn.commit()
    llm = FakeClient()
    posts = FakePostClient()

    result = registry_intake.run_intake(
        conn,
        profile="https://x.com/thsottiaux",
        mode="screen",
        reason=None,
        llm_client=llm,
        post_client=posts,
    )

    assert result["outcome"] == "existing"
    assert result["entity_id"] == materialized["entity_id"]
    assert posts.profile_calls == []
    assert llm.responses.calls == []
    audit = conn.execute(
        "SELECT status, outcome, registry_decision FROM entity_registry_intake_audit"
    ).fetchone()
    assert tuple(audit) == ("completed", "existing", "existing")


def test_screen_mode_persists_combined_keep_decision_and_kind_reason(tmp_path):
    conn = channels.connect(tmp_path / "registry.db")
    llm = FakeClient(
        [
            {
                "kind": "person",
                "kind_reason": "The profile describes one individual researcher.",
                "registry_decision": "keep",
                "registry_decision_reason": "The authored work is directly relevant to frontier model systems.",
            }
        ]
    )
    posts = FakePostClient(
        posts=(
            {
                "created_at": "2026-07-15T00:00:00Z",
                "post_type": "original",
                "text": "We released a new inference method.",
            },
        )
    )

    result = registry_intake.run_intake(
        conn,
        profile="candidate",
        mode="screen",
        reason=None,
        llm_client=llm,
        post_client=posts,
    )

    assert result["outcome"] == "active"
    assert result["registry_decision"] == "keep"
    entity = registry_view.read_entities(
        conn, limit=1, entity_id=result["entity_id"]
    )[0]
    assert entity["kind"] == "person"
    assert entity["kind_reason"] == "The profile describes one individual researcher."
    assert entity["registry_state"] == "active"
    audit = conn.execute(
        "SELECT status, model, prompt_version, input_tokens, output_tokens "
        "FROM entity_registry_intake_audit"
    ).fetchone()
    assert audit["status"] == "completed"
    assert audit["prompt_version"] == "registry-evaluation-v3"
    assert audit["input_tokens"] == 120
    assert audit["output_tokens"] == 24


def test_screen_mode_records_below_floor_profile_as_rejected_without_llm(tmp_path):
    conn = channels.connect(tmp_path / "registry.db")
    llm = FakeClient()
    posts = FakePostClient(followers=75)

    result = registry_intake.run_intake(
        conn,
        profile="smallaccount",
        mode="screen",
        reason=None,
        llm_client=llm,
        post_client=posts,
    )

    assert result["outcome"] == "rejected"
    assert result["registry_decision"] == "remove"
    assert "1,000-follower" in result["decision_reason"]
    assert llm.responses.calls == []
    entity = registry_view.read_entities(
        conn, limit=1, entity_id=result["entity_id"]
    )[0]
    assert entity["registry_state"] == "rejected"
    assert entity["rejection_reason_code"] == "below_follower_floor"


def test_direct_mode_requires_reason_and_bypasses_follower_floor(tmp_path):
    conn = channels.connect(tmp_path / "registry.db")
    with pytest.raises(ValueError, match="audit reason"):
        registry_intake.run_intake(
            conn,
            profile="smallaccount",
            mode="direct",
            reason="",
            llm_client=FakeClient(),
            post_client=FakePostClient(),
        )

    llm = FakeClient(
        [
            {
                "classification": "person",
                "reason": "The profile describes one individual researcher.",
            }
        ]
    )
    result = registry_intake.run_intake(
        conn,
        profile="smallaccount",
        mode="direct",
        reason="Known relevant researcher requested by the operator.",
        llm_client=llm,
        post_client=FakePostClient(followers=75),
    )

    assert result["outcome"] == "active"
    assert result["registry_decision"] == "manual_keep"
    assert result["followers_count"] == 75
    audit = conn.execute(
        "SELECT mode, override_reason, registry_decision FROM entity_registry_intake_audit"
    ).fetchone()
    assert tuple(audit) == (
        "direct",
        "Known relevant researcher requested by the operator.",
        "manual_keep",
    )
