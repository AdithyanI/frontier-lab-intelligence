import json
import hashlib
import sqlite3
from datetime import date

from fli import signal_feed, x_content


def _tweet(post_id, handle, when, text, *, relation=None, target=None):
    value = {
        "id": post_id,
        "createdAt": when,
        "text": text,
        "url": f"https://x.com/{handle}/status/{post_id}",
        "author": {"id": f"x-{handle}", "userName": handle, "name": handle.title()},
        "likeCount": 10,
        "replyCount": 2,
        "retweetCount": 3,
        "quoteCount": 1,
        "viewCount": 100,
    }
    if relation:
        value[f"{relation}ed_tweet" if relation == "retweet" else "quoted_tweet"] = target
    return value


def _raw_fixture(path):
    client = x_content.TwitterContentClient(api_key="test", db_path=path)
    original = _tweet(
        "1", "alice", "2026-07-11T08:00:00Z", "A new model result"
    )
    retweet = _tweet(
        "2",
        "bob",
        "2026-07-11T09:00:00Z",
        "RT @alice: A new model result",
        relation="retweet",
        target=original,
    )
    external = _tweet(
        "9", "outside", "2026-07-10T18:00:00Z", "Primary research result"
    )
    quote = _tweet(
        "3",
        "carol",
        "2026-07-11T10:00:00Z",
        "This result matters",
        relation="quote",
        target=external,
    )
    with client.db:
        for handle, tweet in (("alice", original), ("bob", retweet), ("carol", quote)):
            client._store_posts(
                url=(
                    "https://api.twitterapi.io/twitter/user/last_tweets"
                    f"?userName={handle}&includeReplies=false"
                ),
                payload={"data": {"tweets": [tweet]}},
                observed_at="2026-07-12T00:00:00+00:00",
            )
    client.close()


def test_materialize_deduplicates_retweet_target_and_preserves_quote(tmp_path):
    raw = tmp_path / "x-content.db"
    derived = tmp_path / "feed.db"
    _raw_fixture(raw)

    result = signal_feed.materialize(
        source_db=raw, feed_db=derived, through=date(2026, 7, 11), days=1
    )
    repeated = signal_feed.materialize(
        source_db=raw, feed_db=derived, through=date(2026, 7, 11), days=1
    )

    assert result["source_post_count"] == 3
    assert result["normalized_post_count"] == 4
    assert result["relation_count"] == 2
    assert repeated["run_id"] == result["run_id"]
    assert repeated["reused"] is True

    conn = signal_feed.connect(derived)
    assert conn.execute("SELECT COUNT(*) FROM feed_run").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM feed_post").fetchone()[0] == 4
    assert conn.execute("SELECT COUNT(*) FROM feed_relation").fetchone()[0] == 2
    relations = conn.execute(
        "SELECT source_post_id, relation_type, target_post_id FROM feed_relation ORDER BY source_post_id"
    ).fetchall()
    assert [tuple(row) for row in relations] == [
        ("2", "retweet", "1"),
        ("3", "quote", "9"),
    ]
    quote = conn.execute("SELECT * FROM feed_post WHERE post_id = '3'").fetchone()
    assert quote["post_type"] == "quote"
    assert json.loads(json.dumps(dict(quote)))["author_x_id"] == "x-carol"
    conn.close()


def test_materialize_keeps_replies_only_for_captured_conversation_roots(tmp_path):
    raw = tmp_path / "x-content.db"
    derived = tmp_path / "feed.db"
    client = x_content.TwitterContentClient(api_key="test", db_path=raw)
    root = _tweet(
        "root", "alice", "2026-07-11T08:00:00Z", "Technical report. Details below"
    )
    root["conversationId"] = "root"
    continuation = _tweet(
        "continuation",
        "alice",
        "2026-07-11T08:01:00Z",
        "Link: https://arxiv.org/abs/2607.00001",
    )
    continuation.update(
        {
            "conversationId": "root",
            "inReplyToId": "root",
            "isReply": True,
        }
    )
    unrelated_reply = _tweet(
        "unrelated",
        "alice",
        "2026-07-11T09:00:00Z",
        "A reply in somebody else's conversation",
    )
    unrelated_reply.update(
        {
            "conversationId": "outside-root",
            "inReplyToId": "outside-root",
            "isReply": True,
        }
    )
    foreign_reply = _tweet(
        "foreign", "bob", "2026-07-11T10:00:00Z", "A reaction to Alice"
    )
    foreign_reply.update(
        {
            "conversationId": "root",
            "inReplyToId": "root",
            "isReply": True,
        }
    )
    with client.db:
        client._store_posts(
            url=(
                "https://api.twitterapi.io/twitter/user/last_tweets"
                "?userName=alice&includeReplies=true"
            ),
            payload={"data": {"tweets": [root, continuation, unrelated_reply]}},
            observed_at="2026-07-12T00:00:00+00:00",
        )
        client._store_posts(
            url=(
                "https://api.twitterapi.io/twitter/user/last_tweets"
                "?userName=bob&includeReplies=true"
            ),
            payload={"data": {"tweets": [foreign_reply]}},
            observed_at="2026-07-12T00:00:00+00:00",
        )
    client.close()

    result = signal_feed.materialize(
        source_db=raw, feed_db=derived, through=date(2026, 7, 11), days=1
    )

    assert result["source_post_count"] == 3
    conn = signal_feed.connect(derived)
    rows = conn.execute(
        "SELECT post_id, post_type FROM feed_post ORDER BY post_id"
    ).fetchall()
    assert [tuple(row) for row in rows] == [
        ("continuation", "reply"),
        ("foreign", "reply"),
        ("root", "original"),
    ]
    conn.close()


def test_materialize_recovers_stored_thread_for_embedded_root_before_window(tmp_path):
    raw = tmp_path / "x-content.db"
    derived = tmp_path / "feed.db"
    client = x_content.TwitterContentClient(api_key="test", db_path=raw)
    root = _tweet(
        "root", "lab", "2026-07-10T23:58:00Z", "Technical report. Thread below"
    )
    root["conversationId"] = "root"
    continuation = _tweet(
        "continuation",
        "lab",
        "2026-07-10T23:59:00Z",
        "Paper: https://arxiv.org/abs/2607.00001",
    )
    continuation.update(
        {
            "conversationId": "root",
            "inReplyToId": "root",
            "isReply": True,
        }
    )
    wrapper = _tweet(
        "wrapper",
        "alice",
        "2026-07-11T08:00:00Z",
        "This new result matters",
        relation="quote",
        target=root,
    )
    with client.db:
        client._store_posts(
            url=(
                "https://api.twitterapi.io/twitter/user/last_tweets"
                "?userName=lab&includeReplies=true"
            ),
            payload={"data": {"tweets": [root, continuation]}},
            observed_at="2026-07-12T00:00:00+00:00",
        )
        client._store_posts(
            url=(
                "https://api.twitterapi.io/twitter/user/last_tweets"
                "?userName=alice&includeReplies=true"
            ),
            payload={"data": {"tweets": [wrapper]}},
            observed_at="2026-07-12T00:00:00+00:00",
        )
    client.close()

    result = signal_feed.materialize(
        source_db=raw, feed_db=derived, through=date(2026, 7, 11), days=1
    )

    assert result["source_post_count"] == 2
    conn = signal_feed.connect(derived)
    rows = conn.execute(
        "SELECT post_id, post_type FROM feed_post ORDER BY post_id"
    ).fetchall()
    assert [tuple(row) for row in rows] == [
        ("continuation", "reply"),
        ("root", "original"),
        ("wrapper", "quote"),
    ]
    conn.close()


def test_materialize_recursively_preserves_nested_quote_chain(tmp_path):
    raw = tmp_path / "x-content.db"
    derived = tmp_path / "feed.db"
    client = x_content.TwitterContentClient(api_key="test", db_path=raw)
    root = _tweet("100", "openai", "2026-07-11T08:00:00Z", "Launch")
    middle = _tweet(
        "101",
        "gdb",
        "2026-07-11T09:00:00Z",
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
        client._store_posts(
            url=(
                "https://api.twitterapi.io/twitter/user/last_tweets"
                "?userName=benhylak&includeReplies=false"
            ),
            payload={"data": {"tweets": [wrapper]}},
            observed_at="2026-07-12T00:00:00+00:00",
        )
    client.close()

    result = signal_feed.materialize(
        source_db=raw, feed_db=derived, through=date(2026, 7, 11), days=1
    )

    assert result["source_post_count"] == 1
    assert result["normalized_post_count"] == 3
    assert result["relation_count"] == 2
    conn = signal_feed.connect(derived)
    relations = conn.execute(
        """SELECT source_post_id, relation_type, target_post_id
           FROM feed_relation ORDER BY source_post_id"""
    ).fetchall()
    assert [tuple(row) for row in relations] == [
        ("101", "quote", "100"),
        ("102", "quote", "101"),
    ]
    assert conn.execute(
        "SELECT COUNT(*) FROM feed_run_post WHERE role = 'embedded'"
    ).fetchone()[0] == 2
    conn.close()


def test_direct_content_keeps_relations_from_richer_embedded_occurrence(tmp_path):
    raw = tmp_path / "x-content.db"
    derived = tmp_path / "feed.db"
    client = x_content.TwitterContentClient(api_key="test", db_path=raw)
    target = _tweet(
        "target", "lab", "2026-07-11T08:00:00Z", "Primary launch evidence"
    )
    direct_sparse = _tweet(
        "source", "alice", "2026-07-11T09:00:00Z", "Canonical direct text"
    )
    embedded_rich = _tweet(
        "source",
        "alice",
        "2026-07-11T09:00:00Z",
        "Embedded copy must not replace direct content",
        relation="quote",
        target=target,
    )
    wrapper = _tweet(
        "wrapper",
        "bob",
        "2026-07-11T10:00:00Z",
        "Wrapper",
        relation="quote",
        target=embedded_rich,
    )
    with client.db:
        for handle, tweet in (("alice", direct_sparse), ("bob", wrapper)):
            client._store_posts(
                url=(
                    "https://api.twitterapi.io/twitter/user/last_tweets"
                    f"?userName={handle}&includeReplies=false"
                ),
                payload={"data": {"tweets": [tweet]}},
                observed_at="2026-07-12T00:00:00+00:00",
            )
    client.close()

    result = signal_feed.materialize(
        source_db=raw, feed_db=derived, through=date(2026, 7, 11), days=1
    )

    assert result["source_post_count"] == 2
    assert result["normalized_post_count"] == 3
    assert result["relation_count"] == 2
    conn = signal_feed.connect(derived)
    source = conn.execute(
        "SELECT text, post_type FROM feed_post WHERE post_id = 'source'"
    ).fetchone()
    assert tuple(source) == ("Canonical direct text", "original")
    relations = conn.execute(
        """SELECT source_post_id, relation_type, target_post_id
           FROM feed_relation ORDER BY source_post_id"""
    ).fetchall()
    assert [tuple(row) for row in relations] == [
        ("source", "quote", "target"),
        ("wrapper", "quote", "source"),
    ]
    conn.close()


def test_materialize_preserves_shared_opaque_relation_anchor(tmp_path):
    raw = tmp_path / "x-content.db"
    derived = tmp_path / "feed.db"
    client = x_content.TwitterContentClient(api_key="test", db_path=raw)
    opaque = {"id": "deleted-900"}
    first = _tweet(
        "901", "alice", "2026-07-11T09:00:00Z", "Quoting missing evidence",
        relation="quote", target=opaque,
    )
    second = _tweet(
        "902", "carol", "2026-07-11T10:00:00Z", "Also quoting it",
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

    result = signal_feed.materialize(
        source_db=raw, feed_db=derived, through=date(2026, 7, 11), days=1
    )
    assert result["opaque_target_count"] == 1
    assert result["shared_opaque_target_count"] == 1
    assert result["normalized_post_count"] == 2
    assert result["relation_count"] == 2
    conn = signal_feed.connect(derived)
    anchor = conn.execute(
        "SELECT anchor_id, renderable FROM feed_anchor WHERE anchor_id = 'deleted-900'"
    ).fetchone()
    assert tuple(anchor) == ("deleted-900", 0)
    assert conn.execute(
        "SELECT COUNT(*) FROM feed_relation WHERE target_post_id = 'deleted-900'"
    ).fetchone()[0] == 2
    conn.close()


def test_later_normalized_update_does_not_rewrite_historical_feed(tmp_path):
    raw = tmp_path / "x-content.db"
    derived = tmp_path / "feed.db"
    _raw_fixture(raw)
    first = signal_feed.materialize(
        source_db=raw, feed_db=derived, through=date(2026, 7, 11), days=1
    )

    source = sqlite3.connect(raw)
    original = json.loads(
        source.execute("SELECT raw_json FROM x_post WHERE post_id = '1'").fetchone()[0]
    )
    original["text"] = "Corrected provider snapshot"
    raw_json = json.dumps(
        original, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    source.execute(
        "UPDATE x_post SET raw_json = ?, raw_sha256 = ? WHERE post_id = '1'",
        (raw_json, hashlib.sha256(raw_json.encode()).hexdigest()),
    )
    source.commit()
    source.close()

    second = signal_feed.materialize(
        source_db=raw, feed_db=derived, through=date(2026, 7, 11), days=1
    )
    assert second["run_id"] == first["run_id"]

    conn = signal_feed.connect(derived)
    first_text = conn.execute(
        "SELECT text FROM feed_post WHERE run_id = ? AND post_id = '1'",
        (first["run_id"],),
    ).fetchone()[0]
    assert first_text == "A new model result"
    assert conn.execute(
        "SELECT COUNT(*) FROM feed_run"
    ).fetchone()[0] == 1
    conn.close()


def test_later_provider_observation_does_not_rewrite_historical_feed(tmp_path):
    raw = tmp_path / "x-content.db"
    before_db = tmp_path / "before.db"
    after_db = tmp_path / "after.db"
    client = x_content.TwitterContentClient(api_key="test", db_path=raw)
    original = _tweet(
        "stable", "lab", "2026-07-11T08:00:00Z", "Stable launch claim"
    )
    client._store_raw(
        url=(
            "https://api.twitterapi.io/twitter/user/last_tweets"
            "?userName=lab&includeReplies=false"
        ),
        payload={"data": {"tweets": [original]}},
    )
    client.close()
    before = signal_feed.materialize(
        source_db=raw,
        feed_db=before_db,
        through=date(2026, 7, 11),
        days=1,
    )

    client = x_content.TwitterContentClient(api_key="test", db_path=raw)
    original_json = json.dumps(
        original, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    original_sha = hashlib.sha256(original_json.encode()).hexdigest()
    for suffix in range(10_000):
        updated = {
            **original,
            "likeCount": 9999,
            "text": f"Provider-edited text {suffix}",
        }
        updated_json = json.dumps(
            updated, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        if hashlib.sha256(updated_json.encode()).hexdigest() < original_sha:
            break
    else:  # pragma: no cover - cryptographically implausible
        raise AssertionError("could not construct an adversarial lower hash")
    client._store_posts(
        url=(
            "https://api.twitterapi.io/twitter/user/last_tweets"
            "?userName=lab&includeReplies=false"
        ),
        payload={"data": {"tweets": [updated]}},
        observed_at="2026-07-14T00:00:05+00:00",
    )
    client.close()
    after = signal_feed.materialize(
        source_db=raw,
        feed_db=after_db,
        through=date(2026, 7, 11),
        days=1,
    )

    assert after["run_id"] == before["run_id"]
    first = signal_feed.connect(before_db).execute(
        "SELECT text, like_count, raw_sha256 FROM feed_post WHERE post_id = 'stable'"
    ).fetchone()
    second = signal_feed.connect(after_db).execute(
        "SELECT text, like_count, raw_sha256 FROM feed_post WHERE post_id = 'stable'"
    ).fetchone()
    assert tuple(first) == tuple(second)
    assert tuple(first)[:2] == ("Stable launch claim", 10)


def test_embedded_snapshot_selection_is_order_independent(tmp_path):
    """The earliest disclosed embedded snapshot wins regardless of row order."""

    def build(raw, derived, *, rich_wrapper_id, poor_wrapper_id):
        client = x_content.TwitterContentClient(api_key="test", db_path=raw)
        poor_target = {
            "id": "shared-root",
            "createdAt": "2026-07-11T08:00:00Z",
            "text": "Launch",
            "author": {"userName": "lab"},
        }
        rich_target = _tweet(
            "shared-root",
            "lab",
            "2026-07-11T08:00:00Z",
            "Launch with the complete provider metadata and metrics",
        )
        rich_target["conversationId"] = "shared-root"
        rich_wrapper = _tweet(
            rich_wrapper_id,
            "rich",
            "2026-07-11T10:00:00Z",
            "Rich wrapper",
            relation="quote",
            target=rich_target,
        )
        poor_wrapper = _tweet(
            poor_wrapper_id,
            "poor",
            "2026-07-11T09:00:00Z",
            "Poor wrapper",
            relation="quote",
            target=poor_target,
        )
        with client.db:
            for handle, tweet in (("rich", rich_wrapper), ("poor", poor_wrapper)):
                client._store_posts(
                    url=(
                        "https://api.twitterapi.io/twitter/user/last_tweets"
                        f"?userName={handle}&includeReplies=false"
                    ),
                    payload={"data": {"tweets": [tweet]}},
                    observed_at="2026-07-12T00:00:00+00:00",
                )
        client.close()
        result = signal_feed.materialize(
            source_db=raw,
            feed_db=derived,
            through=date(2026, 7, 11),
            days=1,
        )
        conn = signal_feed.connect(derived)
        target = dict(
            conn.execute(
                "SELECT * FROM feed_post WHERE run_id = ? AND post_id = 'shared-root'",
                (result["run_id"],),
            ).fetchone()
        )
        conn.close()
        return target

    rich_first = build(
        tmp_path / "a-raw.db",
        tmp_path / "a-feed.db",
        rich_wrapper_id="100",
        poor_wrapper_id="200",
    )
    poor_first = build(
        tmp_path / "b-raw.db",
        tmp_path / "b-feed.db",
        rich_wrapper_id="200",
        poor_wrapper_id="100",
    )

    assert rich_first["raw_sha256"] == poor_first["raw_sha256"]
    assert rich_first["text"] == poor_first["text"]
    assert rich_first["conversation_id"] is None
    assert rich_first["author_x_id"] is None
    assert rich_first["text"] == "Launch"
    assert rich_first["first_discovered_at"] == "2026-07-11T09:00:00+00:00"
    assert rich_first["disclosure_post_id"] in {"100", "200"}
