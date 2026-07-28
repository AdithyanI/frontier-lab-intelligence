from fastapi.testclient import TestClient

from fli.network import view as rankings_store
from fli.web.app import app

client = TestClient(app)


def test_registry_returns_complete_typed_entity_universe():
    r = client.get("/api/registry?limit=5000")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == sum(data["counts"].values())
    assert data["filtered_total"] == data["total"]
    assert data["offset"] == 0
    assert data["limit"] == 5000
    assert data["sort"] == "reach"
    assert data["direction"] == "asc"
    if data["network_context"] is not None:
        assert data["network_context"]["network_source_total"] > 0
        assert data["network_context"]["network_rank_total"] > 0
        assert data["network_context"]["snapshot_id"]
    assert data["reach_rank_total"] == data["total"] - data["counts"]["rejected"]
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
        "reach_rank",
        "network_rank",
        "network_follow_count",
        "network_follow_share",
        "network_source_total",
        "network_rank_total",
        "network_channel_count",
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
        "/api/registry?group=organization&limit=40&direction=desc"
    ).json()
    ascending_counts = [
        entity["followers_count"]
        for entity in ascending["entities"]
        if entity["followers_count"] is not None
    ]
    assert ascending["direction"] == "desc"
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
    openai = next(entity for entity in search["entities"] if entity["slug"] == "openai")
    organizations = client.get(
        "/api/registry?group=organization&q=openai&limit=40"
    ).json()
    openai_as_organization = next(
        entity for entity in organizations["entities"] if entity["slug"] == "openai"
    )
    assert openai["reach_rank"] == openai_as_organization["reach_rank"]
    assert openai["network_rank"] == openai_as_organization["network_rank"]
    assert (
        openai["network_source_total"]
        == openai_as_organization["network_source_total"]
    )
    assert search["reach_rank_total"] == organizations["reach_rank_total"]


def test_registry_can_sort_by_entity_union_network_support(monkeypatch):
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
                "network_source_total": 120,
                "network_rank_total": 2,
                "channel_count": 1,
            },
            second_id: {
                "network_rank": 3,
                "cohort_follow_count": 20,
                "cohort_follow_share": 0.2,
                "network_source_total": 120,
                "network_rank_total": 2,
                "channel_count": 2,
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


def test_bit_lens_company_universe_is_a_complete_read_only_projection():
    r = client.get("/api/bit-lens/companies")

    assert r.status_code == 200
    data = r.json()
    assert data["schema_version"] == "investment-company-universe-v5"
    assert data["counts"]["companies"] == 37
    assert data["counts"]["research_memos"] == sum(
        company["research_memo"] is not None for company in data["companies"]
    )
    assert data["mapping_policy"]["candidate_universe"] == "all_profiles"
    assert len(data["companies"]) == 37
    assert all("frontier_lab_relevance" not in company for company in data["companies"])
    assert all(company["analyst_context"]["frontier_ai_channels"] for company in data["companies"])
    companies = {company["ticker"]: company for company in data["companies"]}
    assert companies["IREN"]["research_memo"]["memo"]["source_ledger"]
    assert companies["MSFT"]["research_memo"]["provenance"]["research_date"] == "2026-07-28"
