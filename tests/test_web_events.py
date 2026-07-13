from datetime import date

from fastapi.testclient import TestClient

from fli import channels, signal_events, signal_feed
from fli.web import events as event_store, feed as feed_store
from fli.web.app import app
from test_signal_feed import _raw_fixture
from test_web_feed import _registry_fixture


client = TestClient(app)


def _event_fixture(tmp_path, monkeypatch):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    registry = tmp_path / "registry.db"
    _raw_fixture(raw)
    _registry_fixture(registry)
    signal_feed.materialize(
        source_db=raw, feed_db=feed_db, through=date(2026, 7, 11), days=1
    )
    signal_events.materialize(feed_db=feed_db, events_db=events_db)
    empty_rankings = tmp_path / "following"
    empty_rankings.mkdir()
    monkeypatch.setattr(feed_store, "DEFAULT_FEED_DB", feed_db)
    monkeypatch.setattr(feed_store, "DEFAULT_REGISTRY_DB", registry)
    monkeypatch.setattr(feed_store, "DEFAULT_DERIVED_ROOT", empty_rankings)
    monkeypatch.setattr(event_store, "DEFAULT_FEED_DB", feed_db)
    monkeypatch.setattr(event_store, "DEFAULT_EVENTS_DB", events_db)
    return registry


def test_events_api_exposes_only_exact_structural_groups(tmp_path, monkeypatch):
    _event_fixture(tmp_path, monkeypatch)

    dates = client.get("/api/events/dates").json()
    assert dates["available"] is True
    assert dates["dates"] == [{"day": "2026-07-11", "item_count": 2}]

    payload = client.get("/api/events?date=2026-07-11&limit=20").json()
    assert payload["available"] is True
    assert payload["run"]["clustering_contract"] == "exact-structural-v1"
    assert payload["total"] == 2
    target_group = next(
        item for item in payload["items"] if item["representative"]["post_id"] == "1"
    )
    assert target_group["member_count"] == 2
    assert target_group["link_count"] == 1
    assert target_group["anchor_types"] == ["same_target"]
    assert target_group["why_grouped"] == ["Exact same quoted or reposted post"]
    assert {item["post_id"] for item in target_group["evidence"]} == {"1", "2"}


def test_events_follow_current_registry_rejections_without_rebuild(
    tmp_path, monkeypatch
):
    registry = _event_fixture(tmp_path, monkeypatch)
    before = client.get("/api/events?date=2026-07-11&limit=20").json()
    assert before["total"] == 2

    conn = channels.connect(registry)
    conn.execute(
        """INSERT INTO entity_registry_rejections
           (entity_id, reason_code, reason, source, rejected_at)
           VALUES (2, 'test', 'Rejected structural member.', 'test',
                   '2026-07-12T01:00:00+00:00')"""
    )
    conn.commit()
    conn.close()

    after = client.get("/api/events?date=2026-07-11&limit=20").json()
    assert after["total"] == 1
    assert all(
        item["representative"]["post_id"] != "1" for item in after["items"]
    )
