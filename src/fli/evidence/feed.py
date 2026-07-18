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

from fli.ingestion.x import content as x_content


SCHEMA_VERSION = "signal-feed-v10"
SELECTION_CONTRACT = "complete-calendar-days-v9-embedded-root-threads"
REPO_ROOT = Path(__file__).resolve().parents[3]
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
    opaque_target_count INTEGER NOT NULL,
    shared_opaque_target_count INTEGER NOT NULL,
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
    raw_json TEXT NOT NULL,
    canonical_priority TEXT NOT NULL,
    first_discovered_at TEXT NOT NULL,
    first_discovered_day TEXT NOT NULL,
    disclosure_post_id TEXT NOT NULL,
    PRIMARY KEY (run_id, provider, post_id)
);
CREATE INDEX IF NOT EXISTS idx_feed_post_day
    ON feed_post(run_id, day, published_at DESC, post_id);
CREATE INDEX IF NOT EXISTS idx_feed_post_author
    ON feed_post(run_id, author_x_id, author_handle, day);
CREATE INDEX IF NOT EXISTS idx_feed_post_conversation
    ON feed_post(run_id, conversation_id, in_reply_to_post_id);
CREATE INDEX IF NOT EXISTS idx_feed_post_discovery
    ON feed_post(run_id, first_discovered_day, provider, post_id);

CREATE TABLE IF NOT EXISTS feed_anchor (
    run_id TEXT NOT NULL REFERENCES feed_run(run_id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    anchor_id TEXT NOT NULL,
    renderable INTEGER NOT NULL CHECK (renderable IN (0, 1)),
    PRIMARY KEY (run_id, provider, anchor_id)
);
CREATE INDEX IF NOT EXISTS idx_feed_anchor_opaque
    ON feed_anchor(run_id, renderable, provider, anchor_id);

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
    discovered_at TEXT NOT NULL,
    discovered_day TEXT NOT NULL,
    disclosure_post_id TEXT NOT NULL,
    PRIMARY KEY (run_id, provider, source_post_id, relation_type, target_post_id),
    FOREIGN KEY (run_id, provider, source_post_id)
        REFERENCES feed_post(run_id, provider, post_id),
    FOREIGN KEY (run_id, provider, target_post_id)
        REFERENCES feed_anchor(run_id, provider, anchor_id)
);
CREATE INDEX IF NOT EXISTS idx_feed_relation_target
    ON feed_relation(run_id, provider, target_post_id, relation_type);
CREATE INDEX IF NOT EXISTS idx_feed_relation_discovery
    ON feed_relation(run_id, discovered_day, provider, source_post_id);
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
        if bool(
            tweet.get("isReply")
            or tweet.get("is_reply")
            or tweet.get("inReplyToId")
            or tweet.get("in_reply_to_post_id")
        )
        else "quote"
        if _embedded(tweet, "quote") is not None
        else fallback_type
    )
    metric_values = [
        _as_int(tweet.get(key))
        for key in (
            "likeCount",
            "replyCount",
            "retweetCount",
            "quoteCount",
            "viewCount",
            "bookmarkCount",
        )
    ]
    relation_richness = sum(
        int(_embedded(tweet, relation) is not None)
        for relation in ("retweet", "quote")
    )
    metadata_richness = sum(
        int(bool(value))
        for value in (
            tweet.get("conversationId") or tweet.get("conversation_id"),
            tweet.get("inReplyToId") or tweet.get("in_reply_to_post_id"),
            author["x_id"],
            author["name"],
            tweet.get("url") or tweet.get("twitterUrl"),
        )
    ) + sum(value is not None for value in metric_values)
    engagement_total = sum(value or 0 for value in metric_values)
    canonical_priority = (
        f"{relation_richness:04d}:{metadata_richness:04d}:"
        f"{len(text):08d}:{engagement_total:020d}:{_sha256(raw_json)}"
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
        "raw_json": raw_json,
        "canonical_priority": canonical_priority,
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
    conn: sqlite3.Connection,
    run_id: str,
    post: dict[str, Any],
    *,
    discovered_at: str,
    disclosure_post_id: str,
) -> None:
    discovery = _parse_datetime(discovered_at)
    if discovery is None:
        raise ValueError(f"Invalid discovery timestamp: {discovered_at!r}")
    value = {
        "run_id": run_id,
        **post,
        "first_discovered_at": discovery.isoformat(timespec="seconds"),
        "first_discovered_day": discovery.date().isoformat(),
        "disclosure_post_id": disclosure_post_id,
    }
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
                raw_sha256 = excluded.raw_sha256,
                raw_json = excluded.raw_json,
                canonical_priority = excluded.canonical_priority,
                first_discovered_at = excluded.first_discovered_at,
                first_discovered_day = excluded.first_discovered_day,
                disclosure_post_id = excluded.disclosure_post_id
            WHERE excluded.first_discovered_at < feed_post.first_discovered_at
               OR (
                    excluded.first_discovered_at = feed_post.first_discovered_at
                    AND excluded.canonical_priority > feed_post.canonical_priority
               )""",
        tuple(value[column] for column in columns),
    )
    conn.execute(
        """INSERT INTO feed_anchor
           (run_id, provider, anchor_id, renderable)
           VALUES (?, ?, ?, 1)
           ON CONFLICT(run_id, provider, anchor_id) DO UPDATE SET renderable = 1""",
        (run_id, post["provider"], post["post_id"]),
    )


def _insert_opaque_anchor(
    conn: sqlite3.Connection, run_id: str, provider: str, anchor_id: str
) -> None:
    conn.execute(
        """INSERT OR IGNORE INTO feed_anchor
           (run_id, provider, anchor_id, renderable) VALUES (?, ?, ?, 0)""",
        (run_id, provider, anchor_id),
    )


def _selected_rows(
    source: sqlite3.Connection, start: date, end: date
) -> Iterable[sqlite3.Row]:
    # Provider timestamps are not stored in ISO order, so parse the bounded
    # local corpus once. The raw table is indexed for author workflows, while
    # this derived refresh intentionally optimizes the product read path.
    candidates: list[tuple[sqlite3.Row, dict[str, Any]]] = []
    for row in source.execute(
        """SELECT post.provider, post.post_id, post.author_handle,
                  post.post_type, observed.raw_sha256, observed.raw_json
           FROM x_post post
           JOIN x_post_observation observed
             ON observed.provider = post.provider
            AND observed.post_id = post.post_id
           WHERE NOT EXISTS (
               SELECT 1
               FROM x_post_observation earlier
               WHERE earlier.provider = observed.provider
                 AND earlier.post_id = observed.post_id
                 AND (
                     earlier.observed_at < observed.observed_at
                     OR (
                         earlier.observed_at = observed.observed_at
                         AND earlier.raw_sha256 < observed.raw_sha256
                     )
                 )
           )
           ORDER BY post.provider, post.post_id"""
    ):
        try:
            tweet = json.loads(row["raw_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        published = _parse_datetime(tweet.get("createdAt") or tweet.get("created_at"))
        if published is not None and start <= published.date() <= end:
            candidates.append((row, tweet))

    # Reply-inclusive account timelines are necessary to capture first-party
    # continuations such as "details below" threads and tracked-account replies
    # to other captured roots. They also contain replies in conversations that
    # are otherwise absent from our evidence corpus. Keep a reply only when its
    # conversation root is present in this materialization window; the Event
    # later distinguishes same-author continuation from tracked-author reaction.
    roots: set[str] = set()

    def add_embedded_roots(tweet: dict[str, Any]) -> None:
        for relation in ("retweet", "quote"):
            target = _embedded(tweet, relation)
            if target is None:
                continue
            target_id = str(target.get("id") or target.get("tweetId") or "").strip()
            conversation_id = str(
                target.get("conversationId") or target.get("conversation_id") or ""
            ).strip()
            if conversation_id:
                roots.add(conversation_id)
            elif target_id:
                roots.add(target_id)
            add_embedded_roots(target)

    for _row, tweet in candidates:
        if bool(
            tweet.get("isReply")
            or tweet.get("is_reply")
            or tweet.get("inReplyToId")
            or tweet.get("in_reply_to_post_id")
        ):
            continue
        post_id = str(tweet.get("id") or tweet.get("tweetId") or "").strip()
        if post_id:
            roots.add(post_id)
        add_embedded_roots(tweet)

    # A root first discovered as an embedded quote/retweet can have been
    # published just before this materialization window. Its authored thread
    # is still part of the newly discovered Event, so recover stored replies
    # up to the window cutoff instead of silently reducing the packet to the
    # embedded root. The upper bound prevents future-reply leakage.
    selected_keys = {(row["provider"], row["post_id"]) for row, _tweet in candidates}
    if roots:
        for row in source.execute(
            """SELECT post.provider, post.post_id, post.author_handle,
                      post.post_type, observed.raw_sha256, observed.raw_json
               FROM x_post post
               JOIN x_post_observation observed
                 ON observed.provider = post.provider
                AND observed.post_id = post.post_id
               WHERE post.post_type = 'reply'
                 AND NOT EXISTS (
                     SELECT 1
                     FROM x_post_observation earlier
                     WHERE earlier.provider = observed.provider
                       AND earlier.post_id = observed.post_id
                       AND (
                           earlier.observed_at < observed.observed_at
                           OR (
                               earlier.observed_at = observed.observed_at
                               AND earlier.raw_sha256 < observed.raw_sha256
                           )
                       )
                 )
               ORDER BY post.provider, post.post_id"""
        ):
            key = (row["provider"], row["post_id"])
            if key in selected_keys:
                continue
            try:
                tweet = json.loads(row["raw_json"])
            except (TypeError, json.JSONDecodeError):
                continue
            published = _parse_datetime(
                tweet.get("createdAt") or tweet.get("created_at")
            )
            conversation_id = str(
                tweet.get("conversationId") or tweet.get("conversation_id") or ""
            ).strip()
            if (
                published is not None
                and published.date() < start
                and published.date() <= end
                and conversation_id in roots
            ):
                candidates.append((row, tweet))
                selected_keys.add(key)

    for row, tweet in candidates:
        is_reply = bool(
            tweet.get("isReply")
            or tweet.get("is_reply")
            or tweet.get("inReplyToId")
            or tweet.get("in_reply_to_post_id")
        )
        if not is_reply:
            yield row
            continue
        conversation_id = str(
            tweet.get("conversationId") or tweet.get("conversation_id") or ""
        ).strip()
        if conversation_id in roots:
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
    # Apply raw-store migrations before switching to the read-only scan. This
    # also backfills the pre-migration normalized value as the first immutable
    # observation, so a subsequent provider refresh cannot rewrite history.
    migrated_source = x_content.connect(source_path)
    migrated_source.close()
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
                normalized_post_count, relation_count, opaque_target_count,
                shared_opaque_target_count, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, ?)""",
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
            _insert_post(
                conn,
                run_id,
                direct,
                discovered_at=direct["published_at"],
                disclosure_post_id=direct["post_id"],
            )
            normalized_ids.add((direct["provider"], direct["post_id"]))
            conn.execute(
                """INSERT OR IGNORE INTO feed_run_post
                   (run_id, provider, post_id, role) VALUES (?, ?, ?, 'direct')""",
                (run_id, direct["provider"], direct["post_id"]),
            )

        # Insert embedded targets only after every direct observation exists.
        # A direct provider snapshot is the canonical representation when the
        # same post is also embedded in somebody else's wrapper. Provider
        # payloads can contain quote-of-quote and retweet-of-quote chains, so
        # walk the complete declared relationship tree rather than stopping at
        # the first target. This derived traversal is cycle-safe and remains
        # fully rebuildable from immutable raw payloads.
        direct_ids = {
            (direct["provider"], direct["post_id"])
            for _, _, direct in parsed
        }
        direct_records = {
            (direct["provider"], direct["post_id"]): direct
            for _, _, direct in parsed
        }
        relation_keys: set[tuple[str, str, str, str]] = set()
        opaque_target_sources: dict[tuple[str, str], set[str]] = {}

        def walk_relations(
            *,
            provider: str,
            source_tweet: dict[str, Any],
            source: dict[str, Any],
            ancestry: frozenset[str],
            discovered_at: str,
            disclosure_post_id: str,
        ) -> None:
            source_id = str(source["post_id"])
            if source_id in ancestry:
                return
            next_ancestry = ancestry | {source_id}
            for relation in ("retweet", "quote"):
                target_tweet = _embedded(source_tweet, relation)
                if target_tweet is None:
                    continue
                target_id = str(
                    target_tweet.get("id") or target_tweet.get("tweetId") or ""
                ).strip()
                if not target_id or target_id == source_id:
                    continue
                target = _post_record(
                    target_tweet,
                    fallback_handle="unknown",
                    fallback_type="original",
                )
                if target is None:
                    _insert_opaque_anchor(conn, run_id, provider, target_id)
                    opaque_target_sources.setdefault((provider, target_id), set()).add(
                        source_id
                    )
                else:
                    target["provider"] = provider
                target_key = (provider, target_id)
                if target is not None:
                    if target_key not in direct_ids:
                        _insert_post(
                            conn,
                            run_id,
                            target,
                            discovered_at=discovered_at,
                            disclosure_post_id=disclosure_post_id,
                        )
                    normalized_ids.add(target_key)
                    conn.execute(
                        """INSERT OR IGNORE INTO feed_run_post
                           (run_id, provider, post_id, role)
                           VALUES (?, ?, ?, 'embedded')""",
                        (run_id, provider, target_id),
                    )
                relation_key = (provider, source_id, relation, target_id)
                discovery = _parse_datetime(discovered_at)
                if discovery is None:
                    raise ValueError(
                        f"Invalid relation discovery timestamp: {discovered_at!r}"
                    )
                conn.execute(
                        """INSERT INTO feed_relation
                           (run_id, provider, source_post_id, relation_type,
                            target_post_id, source_author_x_id,
                            source_author_handle, discovered_at, discovered_day,
                            disclosure_post_id)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           ON CONFLICT(
                               run_id, provider, source_post_id, relation_type,
                               target_post_id
                           ) DO UPDATE SET
                               source_author_x_id = excluded.source_author_x_id,
                               source_author_handle = excluded.source_author_handle,
                               discovered_at = excluded.discovered_at,
                               discovered_day = excluded.discovered_day,
                               disclosure_post_id = excluded.disclosure_post_id
                           WHERE excluded.discovered_at < feed_relation.discovered_at
                              OR (
                                  excluded.discovered_at = feed_relation.discovered_at
                                  AND excluded.disclosure_post_id
                                      < feed_relation.disclosure_post_id
                              )""",
                        (
                            run_id,
                            provider,
                            source_id,
                            relation,
                            target_id,
                            source["author_x_id"],
                            source["author_handle"],
                            discovery.isoformat(timespec="seconds"),
                            discovery.date().isoformat(),
                            disclosure_post_id,
                        ),
                    )
                relation_keys.add(relation_key)
                if target is None or target_id in next_ancestry:
                    continue
                # Every selected direct payload is traversed independently at
                # its own publication cutoff. Nested relationships disclosed
                # only by this wrapper inherit the wrapper's discovery time;
                # pulling in another occurrence here would leak future
                # evidence into an earlier daily projection.
                relation_payloads = [target_tweet]
                relation_source = direct_records.get(target_key, target)
                for relation_payload in relation_payloads:
                    walk_relations(
                        provider=provider,
                        source_tweet=relation_payload,
                        source=relation_source,
                        ancestry=next_ancestry,
                        discovered_at=discovered_at,
                        disclosure_post_id=disclosure_post_id,
                    )

        for row, tweet, direct in parsed:
            walk_relations(
                provider=str(row["provider"]),
                source_tweet=tweet,
                source=direct,
                ancestry=frozenset(),
                discovered_at=direct["published_at"],
                disclosure_post_id=direct["post_id"],
            )
        relation_count = len(relation_keys)
        shared_opaque_count = sum(
            len(source_ids) > 1 for source_ids in opaque_target_sources.values()
        )
        conn.execute(
            """UPDATE feed_run
               SET normalized_post_count = ?, relation_count = ?,
                   opaque_target_count = ?, shared_opaque_target_count = ?
               WHERE run_id = ?""",
            (
                len(normalized_ids),
                relation_count,
                len(opaque_target_sources),
                shared_opaque_count,
                run_id,
            ),
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
