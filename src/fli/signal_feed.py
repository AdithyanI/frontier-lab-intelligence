"""Versioned, deterministic Feed materialization over stored X evidence.

Raw provider payloads remain immutable in ``x-content.db``. This module parses
the selected top-level timeline posts and their embedded quote/retweet targets
into a small derived database that is cheap to query and safe to rebuild.
Registry state is deliberately *not* copied here; the web read model joins the
current Registry so rejection changes take effect without rewriting evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable

from fli import x_content


SCHEMA_VERSION = "signal-feed-v3"
SELECTION_CONTRACT = "complete-calendar-days-v3"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_DB = REPO_ROOT / "data" / "raw" / "x" / "x-content.db"
DEFAULT_FEED_DB = REPO_ROOT / "data" / "derived" / "signal-feed" / "feed.db"

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS feed_run (
    run_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL CHECK (schema_version = '{SCHEMA_VERSION}'),
    selection_contract TEXT NOT NULL,
    date_from TEXT NOT NULL,
    date_to TEXT NOT NULL,
    source_db TEXT NOT NULL,
    source_fingerprint TEXT NOT NULL,
    source_post_count INTEGER NOT NULL,
    normalized_post_count INTEGER NOT NULL,
    relation_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (selection_contract, date_from, date_to, source_fingerprint)
);

CREATE TABLE IF NOT EXISTS feed_post (
    run_id TEXT NOT NULL REFERENCES feed_run(run_id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    post_id TEXT NOT NULL,
    author_x_id TEXT,
    author_handle TEXT NOT NULL,
    author_name TEXT,
    published_at TEXT NOT NULL,
    day TEXT NOT NULL,
    text TEXT NOT NULL,
    url TEXT,
    post_type TEXT NOT NULL,
    conversation_id TEXT,
    in_reply_to_post_id TEXT,
    like_count INTEGER,
    reply_count INTEGER,
    retweet_count INTEGER,
    quote_count INTEGER,
    view_count INTEGER,
    bookmark_count INTEGER,
    raw_sha256 TEXT NOT NULL,
    PRIMARY KEY (run_id, provider, post_id)
);
CREATE INDEX IF NOT EXISTS idx_feed_post_day
    ON feed_post(run_id, day, published_at DESC, post_id);
CREATE INDEX IF NOT EXISTS idx_feed_post_author
    ON feed_post(run_id, author_x_id, author_handle, day);
CREATE INDEX IF NOT EXISTS idx_feed_post_conversation
    ON feed_post(run_id, conversation_id, in_reply_to_post_id);

CREATE TABLE IF NOT EXISTS feed_run_post (
    run_id TEXT NOT NULL REFERENCES feed_run(run_id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    post_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('direct', 'embedded')),
    PRIMARY KEY (run_id, provider, post_id, role),
    FOREIGN KEY (run_id, provider, post_id)
        REFERENCES feed_post(run_id, provider, post_id)
);
CREATE INDEX IF NOT EXISTS idx_feed_run_post_run
    ON feed_run_post(run_id, role, post_id);

CREATE TABLE IF NOT EXISTS feed_relation (
    run_id TEXT NOT NULL REFERENCES feed_run(run_id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    source_post_id TEXT NOT NULL,
    relation_type TEXT NOT NULL CHECK (relation_type IN ('quote', 'retweet')),
    target_post_id TEXT NOT NULL,
    source_author_x_id TEXT,
    source_author_handle TEXT NOT NULL,
    PRIMARY KEY (run_id, provider, source_post_id, relation_type, target_post_id),
    FOREIGN KEY (run_id, provider, source_post_id)
        REFERENCES feed_post(run_id, provider, post_id),
    FOREIGN KEY (run_id, provider, target_post_id)
        REFERENCES feed_post(run_id, provider, post_id)
);
CREATE INDEX IF NOT EXISTS idx_feed_relation_target
    ON feed_relation(run_id, provider, target_post_id, relation_type);
"""


def connect(path: Path | str = DEFAULT_FEED_DB) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        probe = sqlite3.connect(path)
        try:
            has_run = probe.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'feed_run'"
            ).fetchone()
            versions = (
                {
                    row[0]
                    for row in probe.execute(
                        "SELECT DISTINCT schema_version FROM feed_run"
                    ).fetchall()
                }
                if has_run
                else set()
            )
        finally:
            probe.close()
        if versions and versions != {SCHEMA_VERSION}:
            found = ", ".join(sorted(versions))
            raise RuntimeError(
                f"Feed store uses {found}; rebuild the derived store for {SCHEMA_VERSION}."
            )
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _tweet_author(tweet: dict[str, Any], fallback_handle: str) -> dict[str, str | None]:
    author = tweet.get("author") if isinstance(tweet.get("author"), dict) else {}
    handle = str(
        author.get("userName")
        or author.get("username")
        or fallback_handle
        or "unknown"
    ).strip().removeprefix("@").lower()
    return {
        "x_id": str(author.get("id") or "").strip() or None,
        "handle": handle,
        "name": str(author.get("name") or "").strip() or None,
    }


def _tweet_url(tweet: dict[str, Any], handle: str, post_id: str) -> str:
    return str(
        tweet.get("url")
        or tweet.get("twitterUrl")
        or f"https://x.com/{handle}/status/{post_id}"
    )


def _post_record(
    tweet: dict[str, Any],
    *,
    fallback_handle: str,
    fallback_type: str,
) -> dict[str, Any] | None:
    post_id = str(tweet.get("id") or tweet.get("tweetId") or "").strip()
    published = _parse_datetime(tweet.get("createdAt") or tweet.get("created_at"))
    if not post_id or published is None:
        return None
    author = _tweet_author(tweet, fallback_handle)
    text = " ".join(str(tweet.get("text") or "").split())
    raw_json = _canonical_json(tweet)
    post_type = (
        "retweet"
        if _embedded(tweet, "retweet") is not None
        else "reply"
        if bool(tweet.get("isReply") or tweet.get("is_reply"))
        else "quote"
        if _embedded(tweet, "quote") is not None
        else fallback_type
    )
    return {
        "provider": "twitterapi.io",
        "post_id": post_id,
        "author_x_id": author["x_id"],
        "author_handle": author["handle"],
        "author_name": author["name"],
        "published_at": published.isoformat(timespec="seconds"),
        "day": published.date().isoformat(),
        "text": text,
        "url": _tweet_url(tweet, str(author["handle"]), post_id),
        "post_type": post_type,
        "conversation_id": str(
            tweet.get("conversationId") or tweet.get("conversation_id") or ""
        ).strip()
        or None,
        "in_reply_to_post_id": str(
            tweet.get("inReplyToId") or tweet.get("in_reply_to_post_id") or ""
        ).strip()
        or None,
        "like_count": _as_int(tweet.get("likeCount") or tweet.get("like_count")),
        "reply_count": _as_int(tweet.get("replyCount") or tweet.get("reply_count")),
        "retweet_count": _as_int(
            tweet.get("retweetCount") or tweet.get("retweet_count")
        ),
        "quote_count": _as_int(tweet.get("quoteCount") or tweet.get("quote_count")),
        "view_count": _as_int(tweet.get("viewCount") or tweet.get("view_count")),
        "bookmark_count": _as_int(
            tweet.get("bookmarkCount") or tweet.get("bookmark_count")
        ),
        "raw_sha256": _sha256(raw_json),
    }


def _embedded(tweet: dict[str, Any], relation: str) -> dict[str, Any] | None:
    keys = (
        ("retweeted_tweet", "retweetedTweet")
        if relation == "retweet"
        else ("quoted_tweet", "quotedTweet")
    )
    for key in keys:
        value = tweet.get(key)
        if isinstance(value, dict) and value:
            return value
    return None


def _insert_post(
    conn: sqlite3.Connection, run_id: str, post: dict[str, Any]
) -> None:
    value = {"run_id": run_id, **post}
    columns = tuple(value)
    conn.execute(
        f"""INSERT INTO feed_post ({', '.join(columns)})
            VALUES ({', '.join('?' for _ in columns)})
            ON CONFLICT(run_id, provider, post_id) DO UPDATE SET
                author_x_id = excluded.author_x_id,
                author_handle = excluded.author_handle,
                author_name = excluded.author_name,
                published_at = excluded.published_at,
                day = excluded.day,
                text = excluded.text,
                url = excluded.url,
                post_type = excluded.post_type,
                conversation_id = excluded.conversation_id,
                in_reply_to_post_id = excluded.in_reply_to_post_id,
                like_count = excluded.like_count,
                reply_count = excluded.reply_count,
                retweet_count = excluded.retweet_count,
                quote_count = excluded.quote_count,
                view_count = excluded.view_count,
                bookmark_count = excluded.bookmark_count,
                raw_sha256 = excluded.raw_sha256""",
        tuple(value[column] for column in columns),
    )


def _selected_rows(
    source: sqlite3.Connection, start: date, end: date
) -> Iterable[sqlite3.Row]:
    # Provider timestamps are not stored in ISO order, so parse the bounded
    # local corpus once. The raw table is indexed for author workflows, while
    # this derived refresh intentionally optimizes the product read path.
    for row in source.execute(
        """SELECT provider, post_id, author_handle, post_type, raw_sha256, raw_json
           FROM x_post
           ORDER BY provider, post_id"""
    ):
        try:
            tweet = json.loads(row["raw_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        published = _parse_datetime(tweet.get("createdAt") or tweet.get("created_at"))
        if published is not None and start <= published.date() <= end:
            yield row


def materialize(
    *,
    source_db: Path | str = DEFAULT_SOURCE_DB,
    feed_db: Path | str = DEFAULT_FEED_DB,
    through: date,
    days: int = 7,
) -> dict[str, Any]:
    """Materialize ``days`` complete UTC calendar days ending at ``through``."""
    if days < 1 or days > 90:
        raise ValueError("days must be between 1 and 90")
    source_path = Path(source_db).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    start = through - timedelta(days=days - 1)
    source = sqlite3.connect(f"file:{source_path.as_posix()}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    rows = list(_selected_rows(source, start, through))
    source.close()
    fingerprint = _sha256(
        _canonical_json([(r["provider"], r["post_id"], r["raw_sha256"]) for r in rows])
    )
    run_id = _sha256(
        _canonical_json(
            [SCHEMA_VERSION, SELECTION_CONTRACT, start.isoformat(), through.isoformat(), fingerprint]
        )
    )
    conn = connect(feed_db)
    existing = conn.execute(
        "SELECT * FROM feed_run WHERE run_id = ?", (run_id,)
    ).fetchone()
    if existing is not None:
        result = dict(existing)
        result["reused"] = True
        conn.close()
        return result

    normalized_ids: set[tuple[str, str]] = set()
    relation_count = 0
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn:
        conn.execute(
            """INSERT INTO feed_run
               (run_id, schema_version, selection_contract, date_from, date_to,
                source_db, source_fingerprint, source_post_count,
                normalized_post_count, relation_count, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)""",
            (
                run_id,
                SCHEMA_VERSION,
                SELECTION_CONTRACT,
                start.isoformat(),
                through.isoformat(),
                str(source_path),
                fingerprint,
                len(rows),
                now,
            ),
        )
        parsed: list[tuple[sqlite3.Row, dict[str, Any], dict[str, Any]]] = []
        for row in rows:
            tweet = json.loads(row["raw_json"])
            direct = _post_record(
                tweet,
                fallback_handle=row["author_handle"],
                fallback_type=row["post_type"],
            )
            if direct is None:
                continue
            direct["provider"] = row["provider"]
            direct["raw_sha256"] = row["raw_sha256"]
            parsed.append((row, tweet, direct))
            _insert_post(conn, run_id, direct)
            normalized_ids.add((direct["provider"], direct["post_id"]))
            conn.execute(
                """INSERT OR IGNORE INTO feed_run_post
                   (run_id, provider, post_id, role) VALUES (?, ?, ?, 'direct')""",
                (run_id, direct["provider"], direct["post_id"]),
            )

        # Insert embedded targets only after every direct observation exists.
        # A direct provider snapshot is the canonical representation when the
        # same post is also embedded in somebody else's wrapper.
        direct_ids = {
            (direct["provider"], direct["post_id"])
            for _, _, direct in parsed
        }
        for row, tweet, direct in parsed:
            relation = (
                "retweet"
                if row["post_type"] == "retweet"
                else "quote"
                if row["post_type"] == "quote"
                else None
            )
            target_tweet = _embedded(tweet, relation) if relation else None
            if relation is None or target_tweet is None:
                continue
            target = _post_record(
                target_tweet,
                fallback_handle="unknown",
                fallback_type="original",
            )
            if target is None:
                continue
            target["provider"] = row["provider"]
            target_key = (target["provider"], target["post_id"])
            if target_key not in direct_ids:
                _insert_post(conn, run_id, target)
            normalized_ids.add((target["provider"], target["post_id"]))
            conn.execute(
                """INSERT OR IGNORE INTO feed_run_post
                   (run_id, provider, post_id, role) VALUES (?, ?, ?, 'embedded')""",
                (run_id, target["provider"], target["post_id"]),
            )
            conn.execute(
                """INSERT OR IGNORE INTO feed_relation
                   (run_id, provider, source_post_id, relation_type,
                    target_post_id, source_author_x_id, source_author_handle)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    direct["provider"],
                    direct["post_id"],
                    relation,
                    target["post_id"],
                    direct["author_x_id"],
                    direct["author_handle"],
                ),
            )
            relation_count += 1
        conn.execute(
            """UPDATE feed_run
               SET normalized_post_count = ?, relation_count = ?
               WHERE run_id = ?""",
            (len(normalized_ids), relation_count, run_id),
        )
    result = dict(conn.execute("SELECT * FROM feed_run WHERE run_id = ?", (run_id,)).fetchone())
    result["reused"] = False
    conn.close()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fli signal-feed")
    parser.add_argument("action", choices=("refresh",))
    parser.add_argument("--source-db", type=Path, default=DEFAULT_SOURCE_DB)
    parser.add_argument("--feed-db", type=Path, default=DEFAULT_FEED_DB)
    parser.add_argument(
        "--through",
        type=date.fromisoformat,
        default=datetime.now(timezone.utc).date() - timedelta(days=1),
        help="Latest complete UTC day (default: yesterday).",
    )
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args(argv)
    result = materialize(
        source_db=args.source_db,
        feed_db=args.feed_db,
        through=args.through,
        days=args.days,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
