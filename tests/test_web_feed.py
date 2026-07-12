from datetime import date

from fastapi.testclient import TestClient

from fli import channels, signal_feed
from fli.web import feed as feed_store
from fli.web.app import app
from test_signal_feed import _raw_fixture


client = TestClient(app)


def _registry_fixture(path):
    conn = channels.connect(path)
    now = "2026-07-12T00:00:00+00:00"
    for index, handle in enumerate(("alice", "bob", "carol"), start=1):
        conn.execute(
            """INSERT INTO entities (id, kind, slug, name, created_at, updated_at)
               VALUES (?, 'person', ?, ?, ?, ?)""",
            (index, handle, handle.title(), now, now),
        )
        conn.execute(
            """INSERT INTO channels (kind, key, label, url, first_seen_at, last_seen_at)
               VALUES ('x', ?, ?, ?, ?, ?)""",
            (handle, handle.title(), f"https://x.com/{handle}", now, now),
        )
        channel_id = conn.execute(
            "SELECT id FROM channels WHERE kind = 'x' AND key = ?", (handle,)
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO entity_channels
               (entity_id, channel_id, relationship, confidence, created_at)
               VALUES (?, ?, 'identity', 1.0, ?)""",
            (index, channel_id, now),
        )
        conn.execute(
            """INSERT INTO accounts
               (platform, handle, display_name, x_id, followers_count,
                first_seen_at, last_seen_at)
               VALUES ('x', ?, ?, ?, 1000, ?, ?)""",
            (handle, handle.title(), f"x-{handle}", now, now),
        )
    conn.commit()
    conn.close()


def _feed_fixture(tmp_path, monkeypatch):
    raw = tmp_path / "x-content.db"
    derived = tmp_path / "feed.db"
    registry = tmp_path / "registry.db"
    _raw_fixture(raw)
    _registry_fixture(registry)
    signal_feed.materialize(
        source_db=raw, feed_db=derived, through=date(2026, 7, 11), days=1
    )
    empty_rankings = tmp_path / "following"
    empty_rankings.mkdir()
    monkeypatch.setattr(feed_store, "DEFAULT_FEED_DB", derived)
    monkeypatch.setattr(feed_store, "DEFAULT_REGISTRY_DB", registry)
    monkeypatch.setattr(feed_store, "DEFAULT_DERIVED_ROOT", empty_rankings)
    return registry


def test_feed_api_deduplicates_and_explains_network_attention(tmp_path, monkeypatch):
    _feed_fixture(tmp_path, monkeypatch)

    dates = client.get("/api/feed/dates").json()
    assert dates["latest_complete_date"] == "2026-07-11"

    payload = client.get("/api/feed?date=2026-07-11&limit=20").json()
    assert payload["available"] is True
    assert payload["score_formula"]["version"] == "attention-v1"
    ids = [item["post_id"] for item in payload["items"]]
    assert "2" not in ids  # pure retweet wrapper collapses into target 1
    target = next(item for item in payload["items"] if item["post_id"] == "1")
    assert target["score_components"]["registry_amplifiers"] == 1
    assert target["amplifiers"][0]["entity_name"] == "Bob"
    quote = next(item for item in payload["items"] if item["post_id"] == "3")
    assert quote["post_type"] == "quote"
    assert quote["context"] == {"target_post_id": "9", "target_handle": "outside"}

    searched = client.get(
        "/api/feed?date=2026-07-11&q=alice&lane=firsthand&limit=20"
    ).json()
    searched_target = next(
        item for item in searched["items"] if item["post_id"] == "1"
    )
    assert searched_target["attention_score"] == target["attention_score"]


def test_feed_uses_current_registry_rejections_without_rebuild(tmp_path, monkeypatch):
    registry = _feed_fixture(tmp_path, monkeypatch)
    before = client.get("/api/feed?date=2026-07-11&limit=20").json()
    before_date_count = client.get("/api/feed/dates").json()["dates"][0]["item_count"]
    assert any(item["post_id"] == "1" for item in before["items"])

    conn = channels.connect(registry)
    conn.execute(
        """INSERT INTO entity_registry_rejections
           (entity_id, reason_code, reason, source, rejected_at)
           VALUES (1, 'test', 'Rejected in current Registry.', 'test',
                   '2026-07-12T01:00:00+00:00')"""
    )
    conn.commit()
    conn.close()

    after = client.get("/api/feed?date=2026-07-11&limit=20").json()
    after_date_count = client.get("/api/feed/dates").json()["dates"][0]["item_count"]
    assert not any(item["post_id"] == "1" for item in after["items"])
    assert after_date_count == before_date_count - 1


def test_feed_removes_rejected_amplifier_vote_without_rebuild(tmp_path, monkeypatch):
    registry = _feed_fixture(tmp_path, monkeypatch)
    before = client.get("/api/feed?date=2026-07-11&limit=20").json()
    target = next(item for item in before["items"] if item["post_id"] == "1")
    assert target["score_components"]["registry_amplifiers"] == 1

    conn = channels.connect(registry)
    conn.execute(
        """INSERT INTO entity_registry_rejections
           (entity_id, reason_code, reason, source, rejected_at)
           VALUES (2, 'test', 'Rejected amplifier.', 'test',
                   '2026-07-12T01:00:00+00:00')"""
    )
    conn.commit()
    conn.close()

    after = client.get("/api/feed?date=2026-07-11&limit=20").json()
    target = next(item for item in after["items"] if item["post_id"] == "1")
    assert target["score_components"]["registry_amplifiers"] == 0
