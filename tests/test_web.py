from fastapi.testclient import TestClient

from fli.web import rankings as rankings_store
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
    assert data["sort"] == "followers"
    assert data["direction"] == "desc"
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
        "network_rank",
        "network_follow_count",
        "network_follow_share",
        "network_account_handle",
        "name",
        "bio",
        "channels",
    }


def test_registry_pages_filters_and_searches_on_the_server():
    all_entities = client.get("/api/registry?limit=40").json()["entities"]
    follower_counts = [
        entity["followers_count"]
        for entity in all_entities
        if entity["followers_count"] is not None
    ]
    assert follower_counts == sorted(follower_counts, reverse=True)

    ascending = client.get(
        "/api/registry?group=organization&limit=40&direction=asc"
    ).json()
    ascending_counts = [
        entity["followers_count"]
        for entity in ascending["entities"]
        if entity["followers_count"] is not None
    ]
    assert ascending["direction"] == "asc"
    assert ascending_counts == sorted(ascending_counts)

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


def test_registry_can_sort_by_best_owned_account_network_rank(monkeypatch):
    baseline = client.get("/api/registry?limit=2").json()["entities"]
    first_id, second_id = (entity["id"] for entity in baseline)
    monkeypatch.setattr(
        rankings_store,
        "entity_network_ranks",
        lambda: {
            first_id: {
                "network_rank": 7,
                "cohort_follow_count": 12,
                "cohort_follow_share": 0.1,
                "handle": "first",
            },
            second_id: {
                "network_rank": 3,
                "cohort_follow_count": 20,
                "cohort_follow_share": 0.2,
                "handle": "second",
            },
        },
    )

    data = client.get(
        "/api/registry?limit=2&sort=network&direction=asc"
    ).json()

    assert data["sort"] == "network"
    assert [entity["id"] for entity in data["entities"]] == [
        second_id,
        first_id,
    ]
    assert [entity["network_rank"] for entity in data["entities"]] == [3, 7]


def test_registry_entity_returns_one_identity_card_payload():
    listed = client.get("/api/registry?q=openai&limit=5").json()["entities"]
    openai = next(e for e in listed if e["slug"] == "openai")

    r = client.get(f"/api/registry/entity/{openai['id']}")
    assert r.status_code == 200
    entity = r.json()["entity"]
    assert entity["id"] == openai["id"]
    assert entity["slug"] == "openai"
    assert entity["kind"] == "organization"
    assert any(c["kind"] == "x" for c in entity["channels"])
    assert set(entity) == set(openai)

    missing = client.get("/api/registry/entity/999999999")
    assert missing.status_code == 404


def test_spa_served_when_built():
    r = client.get("/")
    assert r.status_code == 200
    assert "Frontier Lab Intelligence" in r.text
