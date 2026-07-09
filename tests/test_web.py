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
    assert registry["state"] == "in-progress"
    assert any(s["label"] == "candidate accounts" for s in registry["stats"])


def test_accounts_endpoint_returns_ranked_first():
    r = client.get("/api/accounts?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] > 0
    first = data["accounts"][0]
    assert first["digg_rank"] == 1


def test_accounts_search():
    r = client.get("/api/accounts?q=karpathy")
    assert r.status_code == 200
    handles = [a["handle"] for a in r.json()["accounts"]]
    assert "karpathy" in handles


def test_registry_returns_labs_and_candidates():
    r = client.get("/api/registry?limit=50")
    assert r.status_code == 200
    data = r.json()
    assert len(data["labs"]) == 10
    openai = next(l for l in data["labs"] if l["slug"] == "openai")
    assert openai["linked"] is True
    assert openai["x_handle"] == "openai"

    handles = [c["handle"] for c in data["candidates"]]
    assert "karpathy" in handles
    # lab org accounts must not double-count as person candidates
    assert "openai" not in handles
    assert "googledeepmind" not in handles

    karpathy = next(c for c in data["candidates"] if c["handle"] == "karpathy")
    assert karpathy["digg_rank"] == 1
    assert karpathy["pagerank_rank"] is not None

    assert data["candidates_pool_total"] >= len(data["candidates"])


def test_spa_served_when_built():
    r = client.get("/")
    assert r.status_code == 200
    assert "Frontier Lab Intelligence" in r.text
