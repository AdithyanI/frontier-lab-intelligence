from datetime import date

from fastapi.testclient import TestClient

from fli import channels, signal_events, signal_feed, x_content
from fli.web import events as event_store, feed as feed_store
from fli.web.app import app
from test_signal_feed import _raw_fixture, _tweet
from test_web_feed import _registry_fixture


client = TestClient(app)


def _event_fixture(tmp_path, monkeypatch, *, include_singleton=False):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    registry = tmp_path / "registry.db"
    _raw_fixture(raw)
    if include_singleton:
        provider = x_content.TwitterContentClient(api_key="test", db_path=raw)
        with provider.db:
            provider._store_posts(
                url=(
                    "https://api.twitterapi.io/twitter/user/last_tweets"
                    "?userName=alice&includeReplies=false"
                ),
                payload={
                    "data": {
                        "tweets": [
                            _tweet(
                                "4",
                                "alice",
                                "2026-07-11T11:00:00Z",
                                "Independent observation",
                            )
                        ]
                    }
                },
                observed_at="2026-07-12T00:00:00+00:00",
            )
        provider.close()
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


def test_events_api_returns_root_once_with_exact_relationships(tmp_path, monkeypatch):
    _event_fixture(tmp_path, monkeypatch)

    dates = client.get("/api/events/dates").json()
    assert dates["available"] is True
    assert dates["dates"] == [{"day": "2026-07-11", "item_count": 3}]

    payload = client.get("/api/events?date=2026-07-11&limit=20").json()
    assert payload["available"] is True
    assert payload["run"]["clustering_contract"] == "exact-structural-v1"
    assert payload["total"] == 2
    target_group = next(item for item in payload["items"] if item["root"]["post_id"] == "1")
    assert target_group["is_grouped"] is True
    assert target_group["member_count"] == 2
    assert target_group["link_count"] == 1
    assert target_group["anchor_types"] == ["same_target"]
    assert target_group["why_grouped"] == ["Exact same quoted or reposted post"]
    assert [item["post_id"] for item in target_group["evidence"]] == ["2"]
    assert target_group["evidence"][0]["relationship"] == "retweet"
    assert target_group["evidence"][0]["target_post_id"] == "1"


def test_events_api_preserves_ungrouped_posts_as_singletons(tmp_path, monkeypatch):
    _event_fixture(tmp_path, monkeypatch, include_singleton=True)

    dates = client.get("/api/events/dates").json()
    assert dates["dates"] == [{"day": "2026-07-11", "item_count": 4}]
    payload = client.get("/api/events?date=2026-07-11&limit=20").json()
    singleton = next(item for item in payload["items"] if item["root"]["post_id"] == "4")
    assert singleton["is_grouped"] is False
    assert singleton["member_count"] == 1
    assert singleton["evidence"] == []


def test_events_api_traverses_exact_parent_tree_before_later_branches(
    tmp_path, monkeypatch
):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    registry = tmp_path / "registry.db"
    root = _tweet("10", "alice", "2026-07-11T08:00:00Z", "Launch thread")
    root.update({"conversationId": "10", "isReply": False})
    continuation = _tweet(
        "13", "alice", "2026-07-11T08:15:00Z", "One more detail"
    )
    continuation.update(
        {
            "conversationId": "10",
            "inReplyToId": "10",
            "inReplyToUserId": "x-alice",
            "isReply": True,
        }
    )
    continuation_child = _tweet(
        "14", "alice", "2026-07-11T08:20:00Z", "Nested thread detail"
    )
    continuation_child.update(
        {
            "conversationId": "10",
            "inReplyToId": "13",
            "inReplyToUserId": "x-alice",
            "isReply": True,
        }
    )
    later_root_child = _tweet(
        "15", "alice", "2026-07-11T08:25:00Z", "Later root-level detail"
    )
    later_root_child.update(
        {
            "conversationId": "10",
            "inReplyToId": "10",
            "inReplyToUserId": "x-alice",
            "isReply": True,
        }
    )
    quote = _tweet(
        "12",
        "carol",
        "2026-07-11T09:00:00Z",
        "Separate quoted branch",
        relation="quote",
        target=root,
    )
    reply_to_quote = _tweet(
        "16", "outside", "2026-07-11T09:05:00Z", "Reply beneath the quote"
    )
    reply_to_quote.update(
        {
            "conversationId": "12",
            "inReplyToId": "12",
            "inReplyToUserId": "x-carol",
            "isReply": True,
        }
    )
    missing_parent = _tweet(
        "17", "outside", "2026-07-11T10:00:00Z", "Parent was not captured"
    )
    missing_parent.update(
        {
            "conversationId": "10",
            "inReplyToId": "999",
            "inReplyToUserId": "x-missing",
            "isReply": True,
        }
    )
    provider = x_content.TwitterContentClient(api_key="test", db_path=raw)
    with provider.db:
        for handle, tweets in (
            (
                "alice",
                [root, continuation, continuation_child, later_root_child],
            ),
            ("carol", [quote, reply_to_quote, missing_parent]),
        ):
            provider._store_posts(
                url=(
                    "https://api.twitterapi.io/twitter/user/last_tweets"
                    f"?userName={handle}&includeReplies=false"
                ),
                payload={"data": {"tweets": tweets}},
                observed_at="2026-07-12T00:00:00+00:00",
            )
    provider.close()
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

    payload = client.get("/api/events?date=2026-07-11&limit=20").json()
    assert payload["total"] == 1
    item = payload["items"][0]
    assert item["root"]["post_id"] == "10"
    assert [member["post_id"] for member in item["evidence"]] == [
        "13",
        "14",
        "15",
        "12",
        "16",
        "17",
    ]
    (
        continuation_result,
        continuation_child_result,
        later_root_child_result,
        quote_result,
        reply_to_quote_result,
        missing_parent_result,
    ) = item["evidence"]
    assert continuation_result["relationship"] == "reply"
    assert continuation_result["parent_post_id"] == "10"
    assert continuation_result["depth"] == 1
    assert continuation_result["same_author_as_root"] is True
    assert continuation_child_result["parent_post_id"] == "13"
    assert continuation_child_result["depth"] == 2
    assert continuation_child_result["same_author_as_root"] is True
    assert later_root_child_result["parent_post_id"] == "10"
    assert later_root_child_result["depth"] == 1
    assert quote_result["relationship"] == "quote"
    assert quote_result["parent_post_id"] == "10"
    assert quote_result["depth"] == 1
    assert reply_to_quote_result["relationship"] == "reply"
    assert reply_to_quote_result["parent_post_id"] == "12"
    assert reply_to_quote_result["depth"] == 2
    assert reply_to_quote_result["same_author_as_root"] is False
    assert missing_parent_result["parent_post_id"] == "999"
    assert missing_parent_result["parent_missing"] is True
    assert missing_parent_result["depth"] == 1


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
    assert after["total"] == 2
    surviving = next(item for item in after["items"] if item["root"]["post_id"] == "1")
    assert surviving["is_grouped"] is False
    assert surviving["member_count"] == 1
    assert surviving["evidence"] == []
