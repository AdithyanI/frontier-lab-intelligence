import sqlite3
from datetime import date

import pytest
from fastapi.testclient import TestClient

from fli.evidence import feed as signal_feed
from fli.ingestion.x import content as x_content
from fli.registry import channels
from fli.web import feed as feed_store
from fli.web.app import app
from tests.evidence.test_feed import _raw_fixture, _tweet


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
    monkeypatch.setattr(
        feed_store.rankings_store,
        "entity_network_ranks",
        lambda: {},
    )
    return registry


def test_feed_api_emits_event_rank_contract_and_positioned_amplifiers(
    tmp_path, monkeypatch
):
    _feed_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        feed_store.rankings_store,
        "entity_network_ranks",
        lambda: {
            2: {
                "network_rank": 2,
                "network_rank_total": 2_524,
                "network_rank_level_total": 3,
            }
        },
    )

    dates = client.get("/api/feed/dates").json()
    assert dates["latest_complete_date"] == "2026-07-11"

    payload = client.get("/api/feed?date=2026-07-11&limit=20").json()
    assert payload["available"] is True
    assert payload["rank_contract"]["version"] == "daily-rank-v2"
    assert payload["rank_contract"]["kind"] == "lexicographic_event_rank"
    assert payload["rank_contract"]["layers"] == [
        "trusted_votes",
        "mean_voter_position",
        "author_position",
        "public_interactions",
        "event_id",
    ]
    assert "score_formula" not in payload
    ids = [item["post_id"] for item in payload["items"]]
    assert "2" not in ids  # pure retweet wrapper collapses into target 1
    target = next(item for item in payload["items"] if item["post_id"] == "1")
    assert len(target["amplifiers"]) == 1
    assert target["amplifiers"][0]["entity_name"] == "Bob"
    assert target["amplifiers"][0]["network_position"] == pytest.approx(0.5)
    assert "attention_score" not in target
    assert "score_components" not in target
    assert "daily_rank" not in target
    assert "rank_components" not in target
    quote = next(item for item in payload["items"] if item["post_id"] == "3")
    assert quote["post_type"] == "quote"
    assert quote["context"] == {"target_post_id": "9", "target_handle": "outside"}

    searched = client.get(
        "/api/feed?date=2026-07-11&q=alice&lane=firsthand&limit=20"
    ).json()
    searched_target = next(
        item for item in searched["items"] if item["post_id"] == "1"
    )
    assert searched_target["amplifiers"] == target["amplifiers"]


def test_feed_support_and_context_are_provider_qualified(tmp_path, monkeypatch):
    _feed_fixture(tmp_path, monkeypatch)
    conn = sqlite3.connect(feed_store.DEFAULT_FEED_DB)
    conn.row_factory = sqlite3.Row
    run_id = str(conn.execute("SELECT run_id FROM feed_run").fetchone()[0])
    source = conn.execute(
        "SELECT * FROM feed_post WHERE run_id = ? AND post_id = '1'",
        (run_id,),
    ).fetchone()
    columns = list(source.keys())
    values = [source[column] for column in columns]
    values[columns.index("provider")] = "other.provider"
    values[columns.index("raw_sha256")] = "other-provider-raw"
    conn.execute(
        f"INSERT INTO feed_post ({', '.join(columns)}) "
        f"VALUES ({', '.join('?' for _ in columns)})",
        values,
    )
    conn.execute(
        "INSERT INTO feed_run_post (run_id, provider, post_id, role) "
        "VALUES (?, 'other.provider', '1', 'direct')",
        (run_id,),
    )
    conn.commit()
    conn.close()

    payload = client.get("/api/feed?date=2026-07-11&limit=20").json()
    duplicates = {
        item["provider"]: item
        for item in payload["items"]
        if item["post_id"] == "1"
    }
    assert set(duplicates) == {"twitterapi_io", "other.provider"}
    assert len(duplicates["twitterapi_io"]["amplifiers"]) == 1
    assert duplicates["twitterapi_io"]["amplifiers"][0]["network_position"] == 0.0
    assert duplicates["other.provider"]["amplifiers"] == []


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
    assert len(target["amplifiers"]) == 1

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
    assert target["amplifiers"] == []


def test_embedded_relation_context_does_not_manufacture_day_activity(
    tmp_path, monkeypatch
):
    raw = tmp_path / "x-content.db"
    derived = tmp_path / "feed.db"
    registry = tmp_path / "registry.db"
    root = _tweet("root", "outside", "2026-07-10T08:00:00Z", "Root")
    embedded = _tweet(
        "embedded",
        "bob",
        "2026-07-10T09:00:00Z",
        "Embedded quote",
        relation="quote",
        target=root,
    )
    wrapper = _tweet(
        "wrapper",
        "carol",
        "2026-07-11T09:00:00Z",
        "Directly observed wrapper",
        relation="quote",
        target=embedded,
    )
    provider = x_content.TwitterContentClient(api_key="test", db_path=raw)
    with provider.db:
        provider._store_posts(
            url=(
                "https://api.twitterapi.io/twitter/user/last_tweets"
                "?userName=carol&includeReplies=false"
            ),
            payload={"data": {"tweets": [wrapper]}},
            observed_at="2026-07-12T00:00:00+00:00",
        )
    provider.close()
    _registry_fixture(registry)
    signal_feed.materialize(
        source_db=raw,
        feed_db=derived,
        through=date(2026, 7, 11),
        days=2,
    )
    empty_rankings = tmp_path / "following"
    empty_rankings.mkdir()
    monkeypatch.setattr(feed_store, "DEFAULT_FEED_DB", derived)
    monkeypatch.setattr(feed_store, "DEFAULT_REGISTRY_DB", registry)
    monkeypatch.setattr(feed_store, "DEFAULT_DERIVED_ROOT", empty_rankings)

    july_10 = client.get("/api/feed?date=2026-07-10&limit=20").json()
    july_11 = client.get("/api/feed?date=2026-07-11&limit=20").json()
    assert july_10["items"] == []
    assert {item["post_id"] for item in july_11["items"]} == {
        "embedded",
        "wrapper",
    }
