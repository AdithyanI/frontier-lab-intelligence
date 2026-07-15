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
    } == {"reply_parent", "same_target"}
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


def test_exact_events_use_stable_canonical_root_for_nested_quote_chain(tmp_path):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    client = x_content.TwitterContentClient(api_key="test", db_path=raw)
    root = _tweet("100", "openai", "2026-07-10T08:00:00Z", "Launch")
    middle = _tweet(
        "101",
        "gdb",
        "2026-07-10T09:00:00Z",
        "This is good",
        relation="quote",
        target=root,
    )
    wrapper = _tweet(
        "102",
        "benhylak",
        "2026-07-11T10:00:00Z",
        "It is great",
        relation="quote",
        target=middle,
    )
    with client.db:
        for handle, tweet in (("gdb", middle), ("benhylak", wrapper)):
            client._store_posts(
                url=(
                    "https://api.twitterapi.io/twitter/user/last_tweets"
                    f"?userName={handle}&includeReplies=false"
                ),
                payload={"data": {"tweets": [tweet]}},
                observed_at="2026-07-12T00:00:00+00:00",
            )
    client.close()

    one_day_feed = signal_feed.materialize(
        source_db=raw, feed_db=feed_db, through=date(2026, 7, 10), days=1
    )
    one_day = signal_events.materialize(
        feed_db=feed_db, events_db=events_db, feed_run_id=one_day_feed["run_id"]
    )
    two_day_feed = signal_feed.materialize(
        source_db=raw, feed_db=feed_db, through=date(2026, 7, 11), days=2
    )
    two_day = signal_events.materialize(
        feed_db=feed_db, events_db=events_db, feed_run_id=two_day_feed["run_id"]
    )

    conn = signal_events.connect(events_db)
    one = conn.execute(
        """SELECT event_id, representative_post_id FROM event_cluster
           WHERE run_id = ?""",
        (one_day["run_id"],),
    ).fetchone()
    two = conn.execute(
        """SELECT event_id, representative_post_id, member_count
           FROM event_cluster WHERE run_id = ?""",
        (two_day["run_id"],),
    ).fetchone()
    assert one["event_id"] == two["event_id"]
    assert one["representative_post_id"] == "100"
    assert two["representative_post_id"] == "100"
    assert two["member_count"] == 3
    conn.close()


def test_exact_events_group_wrappers_through_shared_opaque_anchor(tmp_path):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    client = x_content.TwitterContentClient(api_key="test", db_path=raw)
    opaque = {"id": "deleted-900"}
    first = _tweet(
        "901", "alice", "2026-07-10T09:00:00Z", "Quoting missing evidence",
        relation="quote", target=opaque,
    )
    second = _tweet(
        "902", "carol", "2026-07-11T10:00:00Z", "Also quoting it later",
        relation="quote", target=opaque,
    )
    with client.db:
        for handle, tweet in (("alice", first), ("carol", second)):
            client._store_posts(
                url=(
                    "https://api.twitterapi.io/twitter/user/last_tweets"
                    f"?userName={handle}&includeReplies=false"
                ),
                payload={"data": {"tweets": [tweet]}},
                observed_at="2026-07-12T00:00:00+00:00",
            )
    client.close()
    first_feed = signal_feed.materialize(
        source_db=raw, feed_db=feed_db, through=date(2026, 7, 10), days=1
    )
    first_result = signal_events.materialize(
        feed_db=feed_db, events_db=events_db, feed_run_id=first_feed["run_id"]
    )
    second_feed = signal_feed.materialize(
        source_db=raw, feed_db=feed_db, through=date(2026, 7, 11), days=2
    )
    second_result = signal_events.materialize(
        feed_db=feed_db, events_db=events_db, feed_run_id=second_feed["run_id"]
    )
    assert first_result["cluster_count"] == 1
    assert first_result["member_count"] == 1
    assert first_result["link_count"] == 1
    assert second_result["cluster_count"] == 1
    assert second_result["member_count"] == 2
    assert second_result["link_count"] == 2
    conn = signal_events.connect(events_db)
    first_cluster = conn.execute(
        """SELECT canonical_identity_type, canonical_identity_value,
                  event_id, representative_post_id, member_count, link_count
           FROM event_cluster WHERE run_id = ?""",
        (first_result["run_id"],),
    ).fetchone()
    second_cluster = conn.execute(
        """SELECT canonical_identity_type, canonical_identity_value,
                  event_id, representative_post_id, member_count, link_count
           FROM event_cluster WHERE run_id = ?""",
        (second_result["run_id"],),
    ).fetchone()
    assert first_cluster["event_id"] == second_cluster["event_id"]
    assert tuple(first_cluster)[0:2] == ("post", "deleted-900")
    assert tuple(second_cluster)[0:2] == ("post", "deleted-900")
    assert tuple(first_cluster)[3:] == ("901", 1, 1)
    assert tuple(second_cluster)[3:] == ("901", 2, 2)
    link_counts = conn.execute(
        """SELECT run_id, COUNT(*) FROM event_link
           WHERE target_post_id = 'deleted-900' GROUP BY run_id"""
    ).fetchall()
    assert {row[0]: row[1] for row in link_counts} == {
        first_result["run_id"]: 1,
        second_result["run_id"]: 2,
    }
    conn.close()


def test_reply_only_activity_without_captured_root_is_not_a_feed_event(tmp_path):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    client = x_content.TwitterContentClient(api_key="test", db_path=raw)
    earlier = _tweet(
        "900", "alice", "2026-07-10T08:00:00Z", "First captured reply"
    )
    earlier.update(
        {
            "conversationId": "missing-root",
            "inReplyToId": "missing-root",
            "isReply": True,
        }
    )
    later_lower_id = _tweet(
        "100", "alice", "2026-07-11T08:00:00Z", "Later captured reply"
    )
    later_lower_id.update(
        {
            "conversationId": "missing-root",
            "inReplyToId": "missing-root",
            "isReply": True,
        }
    )
    with client.db:
        client._store_posts(
            url=(
                "https://api.twitterapi.io/twitter/user/last_tweets"
                "?userName=alice&includeReplies=false"
            ),
            payload={"data": {"tweets": [earlier, later_lower_id]}},
            observed_at="2026-07-12T00:00:00+00:00",
        )
    client.close()

    first_feed = signal_feed.materialize(
        source_db=raw,
        feed_db=feed_db,
        through=date(2026, 7, 10),
        days=1,
    )
    first_events = signal_events.materialize(
        feed_db=feed_db, events_db=events_db, feed_run_id=first_feed["run_id"]
    )
    second_feed = signal_feed.materialize(
        source_db=raw,
        feed_db=feed_db,
        through=date(2026, 7, 11),
        days=2,
    )
    second_events = signal_events.materialize(
        feed_db=feed_db, events_db=events_db, feed_run_id=second_feed["run_id"]
    )
    assert first_events["cluster_count"] == 0
    assert first_events["member_count"] == 0
    assert second_events["cluster_count"] == 0
    assert second_events["member_count"] == 0


def test_reply_branches_without_captured_conversation_root_are_excluded(tmp_path):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    client = x_content.TwitterContentClient(api_key="test", db_path=raw)
    tweets = []
    for post_id, parent_id in (
        ("a-1", "missing-a"),
        ("a-2", "missing-a"),
        ("b-1", "missing-b"),
        ("b-2", "missing-b"),
    ):
        tweet = _tweet(
            post_id,
            "alice",
            "2026-07-11T08:00:00Z",
            f"Reply in branch {parent_id}",
        )
        tweet.update(
            {
                "conversationId": "wide-conversation",
                "inReplyToId": parent_id,
                "isReply": True,
            }
        )
        tweets.append(tweet)
    with client.db:
        client._store_posts(
            url=(
                "https://api.twitterapi.io/twitter/user/last_tweets"
                "?userName=alice&includeReplies=false"
            ),
            payload={"data": {"tweets": tweets}},
            observed_at="2026-07-12T00:00:00+00:00",
        )
    client.close()

    signal_feed.materialize(
        source_db=raw, feed_db=feed_db, through=date(2026, 7, 11), days=1
    )
    result = signal_events.materialize(feed_db=feed_db, events_db=events_db)
    assert result["cluster_count"] == 0
    assert result["member_count"] == 0


def test_same_author_reply_with_missing_parent_bridges_to_conversation_root(tmp_path):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    client = x_content.TwitterContentClient(api_key="test", db_path=raw)
    root = _tweet("root", "alice", "2026-07-11T08:00:00Z", "Details below")
    root["conversationId"] = "root"
    continuation = _tweet(
        "later", "alice", "2026-07-11T08:05:00Z", "Final link"
    )
    continuation.update(
        {
            "conversationId": "root",
            "inReplyToId": "missing-intermediate",
            "isReply": True,
        }
    )
    with client.db:
        client._store_posts(
            url=(
                "https://api.twitterapi.io/twitter/user/last_tweets"
                "?userName=alice&includeReplies=true"
            ),
            payload={"data": {"tweets": [root, continuation]}},
            observed_at="2026-07-12T00:00:00+00:00",
        )
    client.close()

    feed = signal_feed.materialize(
        source_db=raw, feed_db=feed_db, through=date(2026, 7, 11), days=1
    )
    result = signal_events.materialize(
        feed_db=feed_db, events_db=events_db, feed_run_id=feed["run_id"]
    )

    assert result["cluster_count"] == 1
    assert result["member_count"] == 2
    conn = signal_events.connect(events_db)
    link = conn.execute(
        """SELECT link_type, anchor_value, target_post_id FROM event_link
           WHERE link_type = 'primary_thread'"""
    ).fetchone()
    assert tuple(link) == ("primary_thread", "root", "root")
    anchor = conn.execute(
        """SELECT anchor_type, anchor_value FROM event_anchor
           WHERE anchor_type = 'conversation_root'"""
    ).fetchone()
    assert tuple(anchor) == ("conversation_root", "root")
    conn.close()
