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


def test_materialized_runs_own_immutable_post_snapshots(tmp_path):
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
    assert second["run_id"] != first["run_id"]

    conn = signal_feed.connect(derived)
    first_text = conn.execute(
        "SELECT text FROM feed_post WHERE run_id = ? AND post_id = '1'",
        (first["run_id"],),
    ).fetchone()[0]
    second_text = conn.execute(
        "SELECT text FROM feed_post WHERE run_id = ? AND post_id = '1'",
        (second["run_id"],),
    ).fetchone()[0]
    assert first_text == "A new model result"
    assert second_text == "Corrected provider snapshot"
    conn.close()
