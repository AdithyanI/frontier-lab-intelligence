import sqlite3

from fli import evidence_lineage


def test_verified_primary_posts_require_stable_author_and_reply_chain():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE feed_post (
               run_id TEXT, provider TEXT, post_id TEXT, author_x_id TEXT,
               post_type TEXT, in_reply_to_post_id TEXT
           )"""
    )
    conn.executemany(
        "INSERT INTO feed_post VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("run", "twitterapi_io", "root", "author-1", "original", ""),
            ("run", "twitterapi_io", "reply-1", "author-1", "reply", "root"),
            ("run", "twitterapi_io", "reply-2", "author-1", "reply", "reply-1"),
            ("run", "twitterapi_io", "same-author-quote", "author-1", "quote", ""),
            ("run", "twitterapi_io", "foreign-reply", "author-2", "reply", "root"),
            ("run", "twitterapi_io", "orphan", "author-1", "reply", "missing"),
        ],
    )
    envelope = {
        "root": {"post_id": "root"},
        "related_posts": [
            {
                "post_id": post_id,
                "relation": "quote" if post_id == "same-author-quote" else "reply",
                "same_author_as_root": post_id != "foreign-reply",
            }
            for post_id in (
                "reply-1",
                "reply-2",
                "same-author-quote",
                "foreign-reply",
                "orphan",
            )
        ],
    }

    assert evidence_lineage.verified_primary_post_ids(
        conn,
        feed_run_id="run",
        envelope=envelope,
    ) == {"root", "reply-1", "reply-2"}
