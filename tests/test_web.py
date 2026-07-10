from fastapi.testclient import TestClient

from fli.web.app import app

client = TestClient(app)


def test_status_reports_pipeline_stages():
    r = client.get("/api/status")
    assert r.status_code == 200
    stages = r.json()["stages"]
    ids = [s["id"] for s in stages]
    assert ids == ["sources", "registry", "ingestion", "extraction", "scoring", "delivery"]
    registry = stages[1]
    assert registry["state"] == "live"
    assert any(s["label"] == "entity universe" for s in registry["stats"])
    assert any(s["label"] == "unsure" for s in registry["stats"])


def test_accounts_endpoint_returns_ranked_first():
    r = client.get("/api/accounts?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] > 0
    first = data["accounts"][0]
    assert first["seed_rank"] == 1


def test_accounts_search():
    r = client.get("/api/accounts?q=karpathy")
    assert r.status_code == 200
    handles = [a["handle"] for a in r.json()["accounts"]]
    assert "karpathy" in handles


def test_registry_returns_complete_typed_entity_universe():
    r = client.get("/api/registry?limit=50")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == sum(data["counts"].values())
    assert data["counts"]["person"] == 2_639
    assert data["counts"]["organization"] == 182
    assert data["counts"]["unsure"] == 145
    assert data["counts"]["unknown"] == 0
    assert data["lab_count"] == 10
    openai = next(e for e in data["entities"] if e["slug"] == "openai")
    assert openai["kind"] == "organization"
    assert openai["is_lab"] is True
    assert any(c["kind"] == "x" for c in openai["channels"])
    assert any(c["kind"] == "github" for c in openai["channels"])
    assert set(openai) == {
        "id",
        "slug",
        "kind",
        "is_lab",
        "kind_reason",
        "name",
        "bio",
        "channels",
    }


def test_spa_served_when_built():
    r = client.get("/")
    assert r.status_code == 200
    assert "Frontier Lab Intelligence" in r.text
