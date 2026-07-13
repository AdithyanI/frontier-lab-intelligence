from datetime import date

from fli import signal_events, signal_feed, x_content
from test_signal_feed import _raw_fixture, _tweet


def test_exact_events_group_only_explicit_feed_relations(tmp_path):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    _raw_fixture(raw)
    signal_feed.materialize(
        source_db=raw, feed_db=feed_db, through=date(2026, 7, 11), days=1
    )

    first = signal_events.materialize(feed_db=feed_db, events_db=events_db)
    repeated = signal_events.materialize(feed_db=feed_db, events_db=events_db)

    assert first["cluster_count"] == 2
    assert first["member_count"] == 4
    assert first["link_count"] == 2
    assert repeated["run_id"] == first["run_id"]
    assert repeated["reused"] is True

    conn = signal_events.connect(events_db)
    indexes = {
        row[1] for row in conn.execute("PRAGMA index_list('event_link')").fetchall()
    }
    assert "idx_event_link_source" in indexes
    clusters = conn.execute(
        "SELECT event_id, member_count, link_count FROM event_cluster ORDER BY event_id"
    ).fetchall()
    assert [(row["member_count"], row["link_count"]) for row in clusters] == [
        (2, 1),
        (2, 1),
    ]
    assert {
        row[0] for row in conn.execute("SELECT DISTINCT anchor_type FROM event_anchor")
    } == {"same_target"}
    conn.close()


def test_exact_events_connect_partial_reply_to_present_parent(tmp_path):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    client = x_content.TwitterContentClient(api_key="test", db_path=raw)
    root = _tweet("10", "alice", "2026-07-11T08:00:00Z", "Launch thread")
    root.update({"conversationId": "10", "isReply": False})
    reply = _tweet("11", "outside", "2026-07-11T08:30:00Z", "@alice details")
    reply.update(
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
        "Useful answer",
        relation="quote",
        target=reply,
    )
    quote.update({"conversationId": "12", "isReply": False})
    with client.db:
        for handle, tweet in (("alice", root), ("carol", quote)):
            client._store_posts(
                url=(
                    "https://api.twitterapi.io/twitter/user/last_tweets"
                    f"?userName={handle}&includeReplies=false"
                ),
                payload={"data": {"tweets": [tweet]}},
                observed_at="2026-07-12T00:00:00+00:00",
            )
    client.close()

    signal_feed.materialize(
        source_db=raw, feed_db=feed_db, through=date(2026, 7, 11), days=1
    )
    feed = signal_feed.connect(feed_db)
    stored_reply = feed.execute(
        "SELECT * FROM feed_post WHERE post_id = '11'"
    ).fetchone()
    assert stored_reply["post_type"] == "reply"
    assert stored_reply["conversation_id"] == "10"
    assert stored_reply["in_reply_to_post_id"] == "10"
    feed.close()

    result = signal_events.materialize(feed_db=feed_db, events_db=events_db)
    assert result["cluster_count"] == 1
    assert result["member_count"] == 3
    conn = signal_events.connect(events_db)
    assert {
        row[0] for row in conn.execute("SELECT DISTINCT anchor_type FROM event_anchor")
    } == {"reply_parent", "same_conversation", "same_target"}
    assert {
        row[0] for row in conn.execute("SELECT post_id FROM event_member")
    } == {"10", "11", "12"}
    conn.close()


def test_exact_events_do_not_group_shared_urls(tmp_path):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    client = x_content.TwitterContentClient(api_key="test", db_path=raw)
    posts = []
    for post_id, handle in (("20", "alice"), ("21", "bob")):
        post = _tweet(
            post_id,
            handle,
            "2026-07-11T10:00:00Z",
            "Independent launch commentary https://example.com/launch",
        )
        post["entities"] = {
            "urls": [{"expanded_url": "https://example.com/launch"}]
        }
        posts.append((handle, post))
    with client.db:
        for handle, post in posts:
            client._store_posts(
                url=(
                    "https://api.twitterapi.io/twitter/user/last_tweets"
                    f"?userName={handle}&includeReplies=false"
                ),
                payload={"data": {"tweets": [post]}},
                observed_at="2026-07-12T00:00:00+00:00",
            )
    client.close()

    signal_feed.materialize(
        source_db=raw, feed_db=feed_db, through=date(2026, 7, 11), days=1
    )
    result = signal_events.materialize(feed_db=feed_db, events_db=events_db)
    assert result["cluster_count"] == 0
    assert result["member_count"] == 0
    assert result["link_count"] == 0
