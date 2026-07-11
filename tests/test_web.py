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
    assert any(s["label"] == "rejected" for s in registry["stats"])


def test_registry_returns_complete_typed_entity_universe():
    r = client.get("/api/registry?limit=5000")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == sum(data["counts"].values())
    assert data["filtered_total"] == data["total"]
    assert data["offset"] == 0
    assert data["limit"] == 5000
    assert data["counts"]["person"] > 0
    assert data["counts"]["organization"] >= 10
    assert data["counts"]["unsure"] >= 0
    assert data["counts"]["rejected"] >= 0
    assert data["counts"]["unknown"] == 0
    openai = next(e for e in data["entities"] if e["slug"] == "openai")
    assert openai["kind"] == "organization"
    assert any(c["kind"] == "x" for c in openai["channels"])
    assert any(c["kind"] == "github" for c in openai["channels"])
    linatawfik = next(
        e
        for e in data["entities"]
        if any(c["kind"] == "x" and c["key"] == "linatawfik9" for c in e["channels"])
    )
    assert linatawfik["registry_state"] == "rejected"
    assert linatawfik["rejection_reason_code"] == "manual_scope_rejection"
    assert set(openai) == {
        "id",
        "slug",
        "kind",
        "kind_reason",
        "registry_state",
        "rejection_reason_code",
        "rejection_reason",
        "rejection_source",
        "rejection_evidence_url",
        "followers_count",
        "name",
        "bio",
        "channels",
    }


def test_registry_pages_filters_and_searches_on_the_server():
    people = client.get("/api/registry?group=person&limit=2").json()
    assert people["filtered_total"] == people["counts"]["person"]
    assert len(people["entities"]) == 2
    assert all(entity["kind"] == "person" for entity in people["entities"])
    assert all(entity["registry_state"] == "active" for entity in people["entities"])

    next_page = client.get("/api/registry?group=person&limit=2&offset=2").json()
    assert {entity["id"] for entity in people["entities"]}.isdisjoint(
        entity["id"] for entity in next_page["entities"]
    )

    search = client.get("/api/registry?q=openai&limit=40").json()
    assert 0 < search["filtered_total"] < search["total"]
    assert any(entity["slug"] == "openai" for entity in search["entities"])


def test_spa_served_when_built():
    r = client.get("/")
    assert r.status_code == 200
    assert "Frontier Lab Intelligence" in r.text
