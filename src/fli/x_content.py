"""Local-first, queryable X content storage backed by TwitterAPI.io."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib import parse

from fli import sources

DEFAULT_DB_PATH = Path("data/raw/x/x-content.db")
DEFAULT_MAX_AGE = timedelta(hours=24)
POST_SELECTION_CONTRACT = "recent-authored-posts-v1"

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_request (
    request_sha256 TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_response (
    request_sha256 TEXT NOT NULL REFERENCES raw_request(request_sha256),
    fetched_at TEXT NOT NULL,
    response_sha256 TEXT NOT NULL,
    response_json TEXT NOT NULL,
    PRIMARY KEY (request_sha256, fetched_at)
);

CREATE INDEX IF NOT EXISTS idx_raw_response_latest
    ON raw_response (request_sha256, fetched_at DESC);

CREATE TABLE IF NOT EXISTS x_post (
    provider TEXT NOT NULL,
    post_id TEXT NOT NULL,
    author_handle TEXT NOT NULL,
    published_at TEXT,
    text TEXT NOT NULL,
    url TEXT,
    post_type TEXT NOT NULL,
    is_reply INTEGER NOT NULL CHECK (is_reply IN (0, 1)),
    is_retweet INTEGER NOT NULL CHECK (is_retweet IN (0, 1)),
    like_count INTEGER,
    reply_count INTEGER,
    retweet_count INTEGER,
    quote_count INTEGER,
    view_count INTEGER,
    bookmark_count INTEGER,
    raw_sha256 TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    first_observed_at TEXT NOT NULL,
    last_observed_at TEXT NOT NULL,
    PRIMARY KEY (provider, post_id)
);

CREATE INDEX IF NOT EXISTS idx_x_post_author_time
    ON x_post (author_handle, published_at DESC, post_id);

CREATE TABLE IF NOT EXISTS post_bundle (
    bundle_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    author_handle TEXT NOT NULL,
    selection_contract TEXT NOT NULL,
    requested_limit INTEGER NOT NULL,
    post_count INTEGER NOT NULL,
    evidence_sha256 TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    UNIQUE (
        provider, author_handle, selection_contract,
        requested_limit, evidence_sha256
    )
);

CREATE TABLE IF NOT EXISTS post_bundle_item (
    bundle_id TEXT NOT NULL REFERENCES post_bundle(bundle_id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    provider TEXT NOT NULL,
    post_id TEXT NOT NULL,
    PRIMARY KEY (bundle_id, ordinal),
    UNIQUE (bundle_id, provider, post_id),
    FOREIGN KEY (provider, post_id) REFERENCES x_post(provider, post_id)
);

CREATE INDEX IF NOT EXISTS idx_post_bundle_author
    ON post_bundle (author_handle, observed_at DESC);
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def connect(path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.executescript(SCHEMA)
    return conn


def _tweets(payload: dict[str, Any]) -> list[dict[str, Any]]:
    nested = payload.get("data")
    if isinstance(nested, dict) and isinstance(nested.get("tweets"), list):
        return [item for item in nested["tweets"] if isinstance(item, dict)]
    if isinstance(payload.get("tweets"), list):
        return [item for item in payload["tweets"] if isinstance(item, dict)]
    return []


def _request_handle(url: str) -> str | None:
    query = parse.parse_qs(parse.urlparse(url).query)
    values = query.get("userName")
    if not values:
        return None
    return values[0].strip().removeprefix("@").lower() or None


class TwitterContentClient(sources.TwitterApiIoClient):
    """Persist raw responses, normalized posts, and reusable post bundles."""

    def __init__(
        self,
        *,
        api_key: str,
        db_path: Path | str = DEFAULT_DB_PATH,
        max_age: timedelta = DEFAULT_MAX_AGE,
        refresh: bool = False,
        before_upstream_request: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key=api_key, **kwargs)
        if max_age.total_seconds() < 0:
            raise ValueError("max_age cannot be negative")
        self.db = connect(db_path)
        self.max_age = max_age
        self.refresh = refresh
        self.before_upstream_request = before_upstream_request
        self.lock = threading.Lock()
        self.cache_hits = 0
        self.cache_misses = 0

    def _latest(self, request_sha256: str) -> sqlite3.Row | None:
        with self.lock:
            return self.db.execute(
                """SELECT fetched_at, response_json
                   FROM raw_response
                   WHERE request_sha256 = ?
                   ORDER BY fetched_at DESC
                   LIMIT 1""",
                (request_sha256,),
            ).fetchone()

    def _store_posts(
        self,
        *,
        url: str,
        payload: dict[str, Any],
        observed_at: str,
    ) -> None:
        handle = _request_handle(url)
        if handle is None or "/twitter/user/last_tweets" not in url:
            return
        for tweet in _tweets(payload):
            raw_json = _canonical_json(tweet)
            text = " ".join(str(tweet.get("text") or "").split())
            published_at = tweet.get("createdAt") or tweet.get("created_at")
            post_id = str(tweet.get("id") or tweet.get("tweetId") or "").strip()
            if not post_id:
                post_id = "sha256:" + _sha256(
                    _canonical_json([handle, published_at, text])
                )
            is_retweet = sources._is_retweet(tweet)
            is_reply = sources._is_reply(tweet)
            is_quote = bool(
                tweet.get("quoted_tweet")
                or tweet.get("quotedTweet")
                or tweet.get("isQuote")
                or tweet.get("is_quote")
            )
            post_type = (
                "retweet"
                if is_retweet
                else "reply"
                if is_reply
                else "quote"
                if is_quote
                else "original"
            )
            self.db.execute(
                """INSERT INTO x_post
                   (provider, post_id, author_handle, published_at, text, url,
                    post_type, is_reply, is_retweet, like_count, reply_count,
                    retweet_count, quote_count, view_count, bookmark_count,
                    raw_sha256, raw_json, first_observed_at, last_observed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(provider, post_id) DO UPDATE SET
                       author_handle = excluded.author_handle,
                       published_at = COALESCE(excluded.published_at, x_post.published_at),
                       text = excluded.text,
                       url = COALESCE(excluded.url, x_post.url),
                       post_type = excluded.post_type,
                       is_reply = excluded.is_reply,
                       is_retweet = excluded.is_retweet,
                       like_count = excluded.like_count,
                       reply_count = excluded.reply_count,
                       retweet_count = excluded.retweet_count,
                       quote_count = excluded.quote_count,
                       view_count = excluded.view_count,
                       bookmark_count = excluded.bookmark_count,
                       raw_sha256 = excluded.raw_sha256,
                       raw_json = excluded.raw_json,
                       last_observed_at = excluded.last_observed_at""",
                (
                    sources.PROVIDER,
                    post_id,
                    handle,
                    published_at,
                    text,
                    tweet.get("url") or tweet.get("twitterUrl"),
                    post_type,
                    int(is_reply),
                    int(is_retweet),
                    _int_or_none(tweet.get("likeCount") or tweet.get("like_count")),
                    _int_or_none(tweet.get("replyCount") or tweet.get("reply_count")),
                    _int_or_none(
                        tweet.get("retweetCount") or tweet.get("retweet_count")
                    ),
                    _int_or_none(tweet.get("quoteCount") or tweet.get("quote_count")),
                    _int_or_none(tweet.get("viewCount") or tweet.get("view_count")),
                    _int_or_none(
                        tweet.get("bookmarkCount") or tweet.get("bookmark_count")
                    ),
                    _sha256(raw_json),
                    raw_json,
                    observed_at,
                    observed_at,
                ),
            )

    def _store_raw(self, *, url: str, payload: dict[str, Any]) -> None:
        request_sha256 = _sha256(url)
        response_json = _canonical_json(payload)
        fetched_at = _iso(_now())
        with self.lock, self.db:
            self.db.execute(
                """INSERT INTO raw_request
                   (request_sha256, provider, url, created_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(request_sha256) DO NOTHING""",
                (request_sha256, sources.PROVIDER, url, fetched_at),
            )
            self.db.execute(
                """INSERT INTO raw_response
                   (request_sha256, fetched_at, response_sha256, response_json)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(request_sha256, fetched_at) DO UPDATE SET
                       response_sha256 = excluded.response_sha256,
                       response_json = excluded.response_json""",
                (request_sha256, fetched_at, _sha256(response_json), response_json),
            )
            self._store_posts(url=url, payload=payload, observed_at=fetched_at)

    def _fetch_upstream(self, url: str) -> dict[str, Any]:
        if self.before_upstream_request is not None:
            self.before_upstream_request()
        return super()._fetch_json(url)

    def _fetch_json(self, url: str) -> dict[str, Any]:
        request_sha256 = _sha256(url)
        if not self.refresh:
            cached = self._latest(request_sha256)
            if cached is not None:
                fetched_at = datetime.fromisoformat(cached["fetched_at"])
                if _now() - fetched_at <= self.max_age:
                    with self.lock:
                        self.cache_hits += 1
                    return json.loads(cached["response_json"])
        with self.lock:
            self.cache_misses += 1
        payload = self._fetch_upstream(url)
        self._store_raw(url=url, payload=payload)
        return payload

    def store_post_bundle(
        self,
        *,
        username: str,
        posts: tuple[dict[str, Any], ...],
        requested_limit: int,
    ) -> str:
        handle = sources.normalize_x_handle(username)
        evidence_json = _canonical_json(list(posts))
        evidence_sha256 = _sha256(evidence_json)
        bundle_id = _sha256(
            _canonical_json(
                [
                    sources.PROVIDER,
                    handle,
                    POST_SELECTION_CONTRACT,
                    requested_limit,
                    evidence_sha256,
                ]
            )
        )
        observed_at = _iso(_now())
        with self.lock, self.db:
            self.db.execute(
                """INSERT INTO post_bundle
                   (bundle_id, provider, author_handle, selection_contract,
                    requested_limit, post_count, evidence_sha256, observed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(bundle_id) DO NOTHING""",
                (
                    bundle_id,
                    sources.PROVIDER,
                    handle,
                    POST_SELECTION_CONTRACT,
                    requested_limit,
                    len(posts),
                    evidence_sha256,
                    observed_at,
                ),
            )
            for ordinal, post in enumerate(posts, start=1):
                post_id = str(post.get("id") or "").strip()
                if not post_id:
                    post_id = "sha256:" + _sha256(
                        _canonical_json(
                            [handle, post.get("created_at"), post.get("text")]
                        )
                    )
                existing = self.db.execute(
                    """SELECT 1 FROM x_post
                       WHERE provider = ? AND post_id = ?""",
                    (sources.PROVIDER, post_id),
                ).fetchone()
                if existing is None:
                    normalized_json = _canonical_json(post)
                    self.db.execute(
                        """INSERT INTO x_post
                           (provider, post_id, author_handle, published_at, text,
                            url, post_type, is_reply, is_retweet, raw_sha256,
                            raw_json, first_observed_at, last_observed_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?, ?)""",
                        (
                            sources.PROVIDER,
                            post_id,
                            handle,
                            post.get("created_at"),
                            str(post.get("text") or ""),
                            post.get("url"),
                            post.get("post_type") or "original",
                            _sha256(normalized_json),
                            normalized_json,
                            observed_at,
                            observed_at,
                        ),
                    )
                self.db.execute(
                    """INSERT INTO post_bundle_item
                       (bundle_id, ordinal, provider, post_id)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(bundle_id, ordinal) DO NOTHING""",
                    (bundle_id, ordinal, sources.PROVIDER, post_id),
                )
        return bundle_id

    def stats(self) -> dict[str, int]:
        with self.lock:
            return {"cache_hits": self.cache_hits, "provider_requests": self.cache_misses}

    def close(self) -> None:
        with self.lock:
            self.db.close()


def create_client(
    *,
    db_path: Path | str = DEFAULT_DB_PATH,
    max_age: timedelta = DEFAULT_MAX_AGE,
    refresh: bool = False,
    before_upstream_request: Callable[[], None] | None = None,
    key_file: Path = sources.DEFAULT_TWITTERAPI_IO_KEY_FILE,
    timeout: float = 30.0,
    page_sleep_seconds: float = 0.0,
) -> TwitterContentClient:
    return TwitterContentClient(
        api_key=sources._read_api_key(key_file),
        db_path=db_path,
        max_age=max_age,
        refresh=refresh,
        before_upstream_request=before_upstream_request,
        timeout=timeout,
        page_sleep_seconds=page_sleep_seconds,
    )
