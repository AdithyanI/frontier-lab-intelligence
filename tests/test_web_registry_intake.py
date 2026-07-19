from fastapi.testclient import TestClient

from fli.registry import channels
from fli.web import app as web_app


client = TestClient(web_app.app)


def test_intake_returns_engine_result(monkeypatch, tmp_path):
    db_path = tmp_path / "registry.db"
    conn = channels.connect(db_path)
    conn.close()
    monkeypatch.setattr(web_app, "_model_conn", lambda: channels.connect(db_path))
    monkeypatch.setattr(web_app.entity_kinds, "create_litellm_client", lambda: object())
    monkeypatch.setattr(web_app.sources, "create_twitterapi_io_client", lambda: object())
    calls = []

    def fake_run(conn, **kwargs):
        calls.append(kwargs)
        return {
            "audit_id": 4,
            "handle": "example",
            "mode": "direct",
            "outcome": "active",
            "entity_id": None,
            "registry_decision": "manual_keep",
            "decision_reason": "Operator knows this source.",
            "kind": "person",
            "kind_reason": "One person.",
            "followers_count": 10,
        }

    monkeypatch.setattr(web_app.registry_intake, "run_intake", fake_run)
    response = client.post(
        "/api/registry/intake",
        json={
            "profile": "https://x.com/example",
            "mode": "direct",
            "reason": "Operator knows this source.",
        },
    )

    assert response.status_code == 200
    assert response.json()["registry_decision"] == "manual_keep"
    assert response.json()["entity"] is None
    assert calls[0]["profile"] == "https://x.com/example"
    assert calls[0]["mode"] == "direct"


def test_intake_validation_error_is_a_422(monkeypatch, tmp_path):
    db_path = tmp_path / "registry.db"
    channels.connect(db_path).close()
    monkeypatch.setattr(web_app, "_model_conn", lambda: channels.connect(db_path))
    monkeypatch.setattr(web_app.entity_kinds, "create_litellm_client", lambda: object())
    monkeypatch.setattr(web_app.sources, "create_twitterapi_io_client", lambda: object())
    monkeypatch.setattr(
        web_app.registry_intake,
        "run_intake",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("bad profile")),
    )
    response = client.post(
        "/api/registry/intake",
        json={"profile": "bad", "mode": "screen"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "bad profile"


def test_intake_is_disabled_in_read_only_mode(monkeypatch):
    monkeypatch.setenv("FLI_READ_ONLY", "1")

    response = client.post(
        "/api/registry/intake",
        json={"profile": "https://x.com/example", "mode": "screen"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "This reviewer demo is read-only."
