"""Curated X source importers.

The TwitterAPI.io adapter imports list membership and trusted users' outgoing
following snapshots. Both remain provenance/graph evidence; neither decides
who is tracked.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sqlite3
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from fli import channels, store

DEFAULT_TWITTERAPI_IO_KEY_FILE = Path.home() / ".secrets/twitterapi-io/api-key"
TWITTERAPI_IO_BASE_URL = "https://api.twitterapi.io"
SCHEMA_VERSION = "1.0"
SOURCE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
X_HANDLE_RE = re.compile(r"^[a-z0-9_]{1,15}$")
PROVIDER = "twitterapi_io"
PROVIDER_MAX_ATTEMPTS = 3
X_ONBOARDING_SOURCE = "x_account_onboarding"


@dataclass
class SourceCliError(Exception):
    code: str
    message: str
    hint: str
    exit_code: int = 1
    retryable: bool = False


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise SourceCliError(
            code="E_USAGE",
            message=message,
            hint=f"Run `{self.prog} --help` for valid arguments.",
            exit_code=2,
            retryable=False,
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_api_key(path: Path) -> str:
    try:
        api_key = path.read_text().strip()
    except FileNotFoundError as exc:
        raise SourceCliError(
            code="E_SECRET_MISSING",
            message="TwitterAPI.io API key file is missing.",
            hint=f"Create {path} with mode 0600, containing only the API key.",
            exit_code=3,
        ) from exc
    if not api_key:
        raise SourceCliError(
            code="E_SECRET_EMPTY",
            message="TwitterAPI.io API key file is empty.",
            hint=f"Put the API key in {path}, containing only the key.",
            exit_code=3,
        )
    return api_key


class TwitterApiIoClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = TWITTERAPI_IO_BASE_URL,
        timeout: float = 30.0,
        page_sleep_seconds: float = 5.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.page_sleep_seconds = page_sleep_seconds

    def _fetch_json(self, url: str) -> dict[str, Any]:
        raw = ""
        for attempt in range(PROVIDER_MAX_ATTEMPTS):
            req = request.Request(url, headers={"X-API-Key": self.api_key})
            try:
                with request.urlopen(req, timeout=self.timeout) as response:
                    raw = response.read().decode("utf-8")
                break
            except error.HTTPError as exc:
                if exc.code == 429 and attempt + 1 < PROVIDER_MAX_ATTEMPTS:
                    retry_after = exc.headers.get("Retry-After")
                    try:
                        delay = float(retry_after) if retry_after else 2**attempt
                    except ValueError:
                        delay = 2**attempt
                    exc.close()
                    time.sleep(max(0.0, min(delay, 60.0)))
                    continue
                exit_code = 3 if exc.code in {401, 403} else 4
                retryable = exc.code in {408, 409, 425, 429, 500, 502, 503, 504}
                raise SourceCliError(
                    code="E_PROVIDER_HTTP",
                    message=f"TwitterAPI.io returned HTTP {exc.code}.",
                    hint="Check the API key, account credits, provider status, and request parameters.",
                    exit_code=exit_code,
                    retryable=retryable,
                ) from exc
            except TimeoutError as exc:
                raise SourceCliError(
                    code="E_TIMEOUT",
                    message="TwitterAPI.io request timed out.",
                    hint="Retry later or increase --timeout-seconds.",
                    exit_code=5,
                    retryable=True,
                ) from exc
            except OSError as exc:
                raise SourceCliError(
                    code="E_NETWORK",
                    message="Could not reach TwitterAPI.io.",
                    hint="Check network connectivity and provider status.",
                    exit_code=4,
                    retryable=True,
                ) from exc
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SourceCliError(
                code="E_PROVIDER_JSON",
                message="TwitterAPI.io returned invalid JSON.",
                hint="Retry later or inspect the provider response.",
                exit_code=4,
                retryable=True,
            ) from exc
        if payload.get("status") == "error":
            raise SourceCliError(
                code="E_PROVIDER_ERROR",
                message=str(
                    payload.get("msg")
                    or payload.get("message")
                    or "TwitterAPI.io returned an error."
                ),
                hint="Check the request parameters, API key, account credits, and provider status.",
                exit_code=4,
                retryable=False,
            )
        return payload

    def fetch_page(self, *, list_id: str, cursor: str | None) -> dict[str, Any]:
        query: dict[str, str] = {"list_id": list_id}
        if cursor:
            query["cursor"] = cursor
        url = f"{self.base_url}/twitter/list/members?{parse.urlencode(query)}"
        return self._fetch_json(url)

    def iter_member_pages(self, *, list_id: str):
        cursor: str | None = None
        seen_cursors: set[str] = set()
        while True:
            payload = self.fetch_page(list_id=list_id, cursor=cursor)
            page_members = payload.get("members")
            if not isinstance(page_members, list):
                raise SourceCliError(
                    code="E_PROVIDER_SHAPE",
                    message="TwitterAPI.io response did not include a members array.",
                    hint="Inspect provider docs/status before retrying.",
                    exit_code=4,
                    retryable=True,
                )
            yield [m for m in page_members if isinstance(m, dict)]
            if not payload.get("has_next_page"):
                return
            next_cursor = str(payload.get("next_cursor") or "")
            if not next_cursor:
                raise SourceCliError(
                    code="E_PROVIDER_CURSOR_MISSING",
                    message="TwitterAPI.io reported another page without a cursor.",
                    hint="Retry later or inspect the provider response.",
                    exit_code=4,
                    retryable=True,
                )
            if next_cursor in seen_cursors:
                raise SourceCliError(
                    code="E_PROVIDER_CURSOR_REPEAT",
                    message="TwitterAPI.io repeated a pagination cursor.",
                    hint="Stopped to avoid an infinite pagination loop.",
                    exit_code=4,
                    retryable=True,
                )
            seen_cursors.add(next_cursor)
            cursor = next_cursor
            if self.page_sleep_seconds > 0:
                time.sleep(self.page_sleep_seconds)

    def fetch_user(self, *, username: str) -> dict[str, Any]:
        query = parse.urlencode({"userName": username})
        payload = self._fetch_json(f"{self.base_url}/twitter/user/info?{query}")
        user = payload.get("data")
        if not isinstance(user, dict):
            raise SourceCliError(
                code="E_PROVIDER_SHAPE",
                message="TwitterAPI.io response did not include a user object.",
                hint="Inspect provider docs/status before retrying.",
                exit_code=4,
                retryable=True,
            )
        return user

    def fetch_recent_tweets_page(
        self,
        *,
        username: str,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Fetch one recent-timeline page without replies."""
        query: dict[str, str] = {
            "userName": username,
            "includeReplies": "false",
        }
        if cursor:
            query["cursor"] = cursor
        url = f"{self.base_url}/twitter/user/last_tweets?{parse.urlencode(query)}"
        return self._fetch_json(url)

    def fetch_recent_authored_posts(
        self,
        *,
        username: str,
        limit: int = 20,
        max_pages: int = 10,
        profile: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], ...]:
        """Return recent authored posts, excluding replies and retweets.

        TwitterAPI.io has returned both ``tweets`` and ``data.tweets`` shapes
        for this endpoint. Pagination continues only as needed to replace
        filtered retweets, bounded by ``max_pages``.
        """
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1")
        handle = username.strip().removeprefix("@").lower()
        if not X_HANDLE_RE.fullmatch(handle):
            raise ValueError(f"invalid X handle: {username!r}")
        profile = profile or self.fetch_user(username=handle)
        if is_protected_profile(profile):
            raise SourceCliError(
                code="E_ACCOUNT_PROTECTED",
                message=f"@{handle} has protected posts.",
                hint="Reject protected accounts; their posts are not public evidence.",
                exit_code=6,
                retryable=False,
            )

        posts: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        seen_cursors: set[str] = set()
        cursor: str | None = None
        for _page_number in range(max_pages):
            payload = self.fetch_recent_tweets_page(
                username=handle,
                cursor=cursor,
            )
            data = payload.get("data")
            nested = data if isinstance(data, dict) else {}
            tweets = nested.get("tweets")
            if not isinstance(tweets, list):
                tweets = payload.get("tweets")
            if not isinstance(tweets, list):
                raise SourceCliError(
                    code="E_PROVIDER_SHAPE",
                    message=(
                        "TwitterAPI.io response did not include a tweets array."
                    ),
                    hint="Inspect provider docs/status before retrying.",
                    exit_code=4,
                    retryable=True,
                )

            for tweet in tweets:
                if not isinstance(tweet, dict) or _is_retweet(tweet):
                    continue
                if _is_reply(tweet):
                    continue
                text = html.unescape(str(tweet.get("text") or ""))
                text = " ".join(text.split())
                if not text:
                    continue
                tweet_id = str(tweet.get("id") or tweet.get("tweetId") or "")
                dedupe_key = tweet_id or hashlib.sha256(text.encode()).hexdigest()
                if dedupe_key in seen_ids:
                    continue
                seen_ids.add(dedupe_key)
                is_quote = bool(
                    tweet.get("quoted_tweet")
                    or tweet.get("quotedTweet")
                    or tweet.get("isQuote")
                    or tweet.get("is_quote")
                )
                posts.append(
                    {
                        "id": tweet_id,
                        "created_at": (
                            tweet.get("createdAt")
                            or tweet.get("created_at")
                        ),
                        "text": text,
                        "url": tweet.get("url") or tweet.get("twitterUrl"),
                        "post_type": "quote" if is_quote else "original",
                    }
                )
                if len(posts) >= limit:
                    return tuple(posts)

            has_next = bool(
                nested.get("has_next_page")
                if "has_next_page" in nested
                else payload.get("has_next_page")
            )
            next_cursor = str(
                nested.get("next_cursor") or payload.get("next_cursor") or ""
            )
            if not has_next and not next_cursor:
                break
            if not next_cursor or next_cursor in seen_cursors:
                break
            seen_cursors.add(next_cursor)
            cursor = next_cursor
            if self.page_sleep_seconds > 0:
                time.sleep(self.page_sleep_seconds)
        return tuple(posts)

    def fetch_following_page(
        self,
        *,
        username: str,
        cursor: str | None,
        page_size: int = 200,
    ) -> dict[str, Any]:
        query: dict[str, str | int] = {
            "userName": username,
            "pageSize": page_size,
        }
        if cursor:
            query["cursor"] = cursor
        url = f"{self.base_url}/twitter/user/followings?{parse.urlencode(query)}"
        return self._fetch_json(url)

    def iter_following_pages(self, *, username: str, page_size: int = 200):
        cursor: str | None = None
        seen_cursors: set[str] = set()
        while True:
            payload = self.fetch_following_page(
                username=username,
                cursor=cursor,
                page_size=page_size,
            )
            page_followings = payload.get("followings")
            if not isinstance(page_followings, list):
                raise SourceCliError(
                    code="E_PROVIDER_SHAPE",
                    message="TwitterAPI.io response did not include a followings array.",
                    hint="Inspect provider docs/status before retrying.",
                    exit_code=4,
                    retryable=True,
                )
            yield [member for member in page_followings if isinstance(member, dict)]
            if not payload.get("has_next_page"):
                return
            next_cursor = str(payload.get("next_cursor") or "")
            if not next_cursor:
                raise SourceCliError(
                    code="E_PROVIDER_CURSOR_MISSING",
                    message="TwitterAPI.io reported another following page without a cursor.",
                    hint="Retry later or inspect the provider response.",
                    exit_code=4,
                    retryable=True,
                )
            if next_cursor in seen_cursors:
                raise SourceCliError(
                    code="E_PROVIDER_CURSOR_REPEAT",
                    message="TwitterAPI.io repeated a following pagination cursor.",
                    hint="Stopped to avoid an infinite pagination loop.",
                    exit_code=4,
                    retryable=True,
                )
            seen_cursors.add(next_cursor)
            cursor = next_cursor
            if self.page_sleep_seconds > 0:
                time.sleep(self.page_sleep_seconds)


def create_twitterapi_io_client(
    *,
    key_file: Path = DEFAULT_TWITTERAPI_IO_KEY_FILE,
    timeout: float = 30.0,
    page_sleep_seconds: float = 0.0,
) -> TwitterApiIoClient:
    """Create the shared TwitterAPI.io client from the machine secret."""
    return TwitterApiIoClient(
        api_key=_read_api_key(key_file),
        timeout=timeout,
        page_sleep_seconds=page_sleep_seconds,
    )


def _normalize_handle(member: dict[str, Any]) -> str | None:
    raw = member.get("userName") or member.get("username") or member.get("screen_name")
    if not raw:
        return None
    handle = str(raw).strip().removeprefix("@").lower()
    return handle or None


def _is_retweet(tweet: dict[str, Any]) -> bool:
    text = str(tweet.get("text") or "").lstrip()
    return bool(
        tweet.get("retweeted_tweet")
        or tweet.get("retweetedTweet")
        or tweet.get("isRetweet")
        or tweet.get("is_retweet")
        or text.startswith("RT @")
    )


def _is_reply(tweet: dict[str, Any]) -> bool:
    return bool(
        tweet.get("isReply")
        or tweet.get("is_reply")
        or tweet.get("inReplyToId")
        or tweet.get("in_reply_to_status_id")
    )


def is_protected_profile(profile: dict[str, Any]) -> bool:
    """Return the provider's explicit protected/private account state."""
    return any(
        profile.get(key) is True
        for key in ("protected", "isProtected", "isPrivate", "private")
    )


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _existing_account(conn: sqlite3.Connection, handle: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM accounts WHERE platform = 'x' AND handle = ?",
        (handle,),
    ).fetchone()


def _upsert_account(
    conn: sqlite3.Connection,
    *,
    member: dict[str, Any],
    handle: str,
    observed_at: str,
) -> tuple[int, bool]:
    row = _existing_account(conn, handle)
    display_name = member.get("name")
    x_id = member.get("id")
    bio = member.get("description")
    followers_value = member.get("followers")
    if followers_value is None:
        followers_value = member.get("followers_count")
    followers_count = _int_or_none(followers_value)
    if row:
        conn.execute(
            """UPDATE accounts SET
                   display_name = COALESCE(?, display_name),
                   x_id = COALESCE(?, x_id),
                   bio = COALESCE(?, bio),
                   followers_count = COALESCE(?, followers_count),
                   last_seen_at = ?
               WHERE id = ?""",
            (display_name, x_id, bio, followers_count, observed_at, row["id"]),
        )
        return row["id"], False
    cur = conn.execute(
        """INSERT INTO accounts
           (platform, handle, display_name, x_id, bio, followers_count,
            first_seen_at, last_seen_at)
           VALUES ('x', ?, ?, ?, ?, ?, ?, ?)""",
        (handle, display_name, x_id, bio, followers_count, observed_at, observed_at),
    )
    return cur.lastrowid, True


def _has_source_fact(
    conn: sqlite3.Connection,
    *,
    account_id: int,
    source: str,
    fact: str = "list_member",
) -> bool:
    return (
        conn.execute(
            """SELECT 1 FROM account_source_facts
               WHERE account_id = ? AND source = ? AND fact = ?""",
            (account_id, source, fact),
        ).fetchone()
        is not None
    )


def _validate_source(source: str) -> None:
    if not SOURCE_RE.match(source):
        raise SourceCliError(
            code="E_SOURCE_INVALID",
            message="--source must be lowercase letters, numbers, underscores, or hyphens.",
            hint="Example: --source trusted_seed_following",
            exit_code=2,
        )


def _normalize_username(username: str) -> str:
    normalized = username.strip().removeprefix("@").lower()
    if not X_HANDLE_RE.match(normalized):
        raise SourceCliError(
            code="E_USERNAME_INVALID",
            message="--username must be a valid X handle.",
            hint="Pass the handle without a profile URL, for example: trusted_seed",
            exit_code=2,
        )
    return normalized


def normalize_x_handle(username: str) -> str:
    """Normalize one externally supplied X handle."""
    return _normalize_username(username)


def profile_followers_count(profile: dict[str, Any]) -> int | None:
    """Read a follower count across the provider's observed profile shapes."""
    for key in ("followers", "followers_count", "followersCount"):
        value = _int_or_none(profile.get(key))
        if value is not None:
            return value
    return None


def persist_x_profile(
    conn: sqlite3.Connection,
    *,
    profile: dict[str, Any],
    source: str = X_ONBOARDING_SOURCE,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Upsert one provider profile into the account/channel/entity spine."""
    from fli import registry

    _validate_source(source)
    handle = _normalize_handle(profile)
    if handle is None:
        raise SourceCliError(
            code="E_PROVIDER_SHAPE",
            message="TwitterAPI.io profile did not include a valid X handle.",
            hint="Inspect the provider profile response before retrying.",
            exit_code=4,
            retryable=False,
        )
    observed_at = observed_at or _now()
    evidence_url = f"https://x.com/{handle}"
    existing_entity = conn.execute(
        """SELECT e.id
           FROM entities e
           JOIN entity_channels ec ON ec.entity_id = e.id
           JOIN channels c ON c.id = ec.channel_id
           WHERE c.kind = 'x' AND c.key = ?""",
        (handle,),
    ).fetchone()
    with conn:
        account_id, account_created = _upsert_account(
            conn,
            member=profile,
            handle=handle,
            observed_at=observed_at,
        )
        conn.execute(
            """INSERT INTO account_source_facts
               (account_id, source, fact, value, observed_at, evidence_url)
               VALUES (?, ?, 'submitted_handle', ?, ?, ?)
               ON CONFLICT (account_id, source, fact) DO UPDATE SET
                   value = excluded.value,
                   observed_at = excluded.observed_at,
                   evidence_url = excluded.evidence_url""",
            (
                account_id,
                source,
                handle,
                observed_at,
                evidence_url,
            ),
        )
        channel_id = channels.upsert_channel(
            conn,
            kind="x",
            key=handle,
            label=str(profile.get("name") or f"@{handle}"),
            url=evidence_url,
            observed_at=observed_at,
        )
        channels.observe_channel(
            conn,
            channel_id=channel_id,
            source="x_profile",
            metric="followers_count",
            value=profile_followers_count(profile),
            observed_at=observed_at,
            evidence_url=evidence_url,
        )
        channels.observe_channel(
            conn,
            channel_id=channel_id,
            source="x_profile",
            metric="bio",
            value=profile.get("description"),
            observed_at=observed_at,
            evidence_url=evidence_url,
        )
    registry.materialize_unlinked_channels(conn, observed_at=observed_at)
    entity = conn.execute(
        """SELECT e.id, e.kind
           FROM entities e
           JOIN entity_channels ec ON ec.entity_id = e.id
           WHERE ec.channel_id = ?""",
        (channel_id,),
    ).fetchone()
    if entity is None:
        raise RuntimeError(f"X channel @{handle} has no entity owner")
    return {
        "handle": handle,
        "account_id": account_id,
        "account_created": account_created,
        "channel_id": channel_id,
        "entity_id": entity["id"],
        "entity_created": existing_entity is None,
        "entity_kind": entity["kind"],
        "profile_url": evidence_url,
    }


def import_members(
    conn: sqlite3.Connection,
    *,
    list_id: str,
    source: str,
    members: list[dict[str, Any]],
    pages_fetched: int,
    dry_run: bool,
    sync_channels: bool = True,
    observed_at: str | None = None,
) -> dict[str, Any]:
    if not list_id.strip():
        raise SourceCliError(
            code="E_LIST_ID_REQUIRED",
            message="--list-id is required.",
            hint="Pass the numeric X list id.",
            exit_code=2,
        )
    _validate_source(source)

    observed_at = observed_at or _now()
    evidence_url = f"https://x.com/i/lists/{list_id}"
    channels.ensure_schema(conn)

    unique: dict[str, dict[str, Any]] = {}
    skipped = 0
    for member in members:
        handle = _normalize_handle(member)
        if not handle:
            skipped += 1
            continue
        unique.setdefault(handle, member)

    existing_handles = {
        row["handle"]
        for row in conn.execute(
            "SELECT handle FROM accounts WHERE platform = 'x'"
        ).fetchall()
    }
    existing_facts = 0
    for handle in unique:
        row = _existing_account(conn, handle)
        if row and _has_source_fact(conn, account_id=row["id"], source=source):
            existing_facts += 1

    would_create = sum(1 for handle in unique if handle not in existing_handles)
    would_update = len(unique) - would_create
    would_write_facts = len(unique) - existing_facts

    created = 0
    updated = 0
    facts_written = 0
    if not dry_run:
        with conn:
            for handle, member in unique.items():
                account_id, is_created = _upsert_account(
                    conn,
                    member=member,
                    handle=handle,
                    observed_at=observed_at,
                )
                created += int(is_created)
                updated += int(not is_created)
                before_exists = _has_source_fact(
                    conn, account_id=account_id, source=source
                )
                conn.execute(
                    """INSERT INTO account_source_facts
                       (account_id, source, fact, value, observed_at, evidence_url)
                       VALUES (?, ?, 'list_member', ?, ?, ?)
                       ON CONFLICT (account_id, source, fact) DO UPDATE SET
                           value = excluded.value,
                           observed_at = excluded.observed_at,
                           evidence_url = excluded.evidence_url""",
                    (account_id, source, list_id, observed_at, evidence_url),
                )
                facts_written += int(not before_exists)
        if sync_channels:
            channels.sync_all(conn)

    return {
        "provider": PROVIDER,
        "list_id": list_id,
        "source": source,
        "dry_run": dry_run,
        "pages_fetched": pages_fetched,
        "members_fetched": len(members),
        "unique_handles": len(unique),
        "skipped_members": skipped,
        "would_create_accounts": would_create,
        "would_update_accounts": would_update,
        "would_write_source_facts": would_write_facts,
        "created_accounts": created,
        "updated_accounts": updated,
        "source_facts_written": facts_written,
        "evidence_url": evidence_url,
    }


def run_import_x_list(
    *,
    db_path: str | None,
    list_id: str,
    source: str,
    key_file: Path,
    dry_run: bool,
    timeout_seconds: float,
    page_sleep_seconds: float,
    client: TwitterApiIoClient | None = None,
) -> dict[str, Any]:
    if client is None:
        api_key = _read_api_key(key_file)
        client = TwitterApiIoClient(
            api_key=api_key,
            timeout=timeout_seconds,
            page_sleep_seconds=page_sleep_seconds,
        )
    conn = channels.connect(db_path) if db_path else channels.connect()
    totals = {
        "provider": PROVIDER,
        "list_id": list_id,
        "source": source,
        "dry_run": dry_run,
        "pages_fetched": 0,
        "members_fetched": 0,
        "unique_handles": 0,
        "skipped_members": 0,
        "would_create_accounts": 0,
        "would_update_accounts": 0,
        "would_write_source_facts": 0,
        "created_accounts": 0,
        "updated_accounts": 0,
        "source_facts_written": 0,
        "evidence_url": f"https://x.com/i/lists/{list_id}",
        "database": str(db_path or store.DEFAULT_DB_PATH),
    }
    seen_handles: set[str] = set()
    wrote_any = False
    try:
        for page_members in client.iter_member_pages(list_id=list_id):
            totals["pages_fetched"] += 1
            totals["members_fetched"] += len(page_members)
            fresh_members = []
            for member in page_members:
                handle = _normalize_handle(member)
                if handle and handle in seen_handles:
                    continue
                if handle:
                    seen_handles.add(handle)
                fresh_members.append(member)
            page_data = import_members(
                conn,
                list_id=list_id,
                source=source,
                members=fresh_members,
                pages_fetched=1,
                dry_run=dry_run,
                sync_channels=False,
            )
            for key in (
                "unique_handles",
                "skipped_members",
                "would_create_accounts",
                "would_update_accounts",
                "would_write_source_facts",
                "created_accounts",
                "updated_accounts",
                "source_facts_written",
            ):
                totals[key] += page_data[key]
            wrote_any = wrote_any or bool(
                page_data["created_accounts"]
                or page_data["updated_accounts"]
                or page_data["source_facts_written"]
            )
    finally:
        try:
            if wrote_any and not dry_run:
                channels.sync_all(conn)
        finally:
            conn.close()
    return totals


def _following_page_credits(returned: int) -> int:
    """Estimate TwitterAPI.io credits from its documented returned-page tiers."""
    if returned <= 0:
        return 0
    if returned >= 200:
        return returned
    if returned >= 100:
        return returned * 2
    return max(60, returned * 3)


def import_followings(
    conn: sqlite3.Connection,
    *,
    username: str,
    source: str,
    source_profile: dict[str, Any],
    followings: list[dict[str, Any]],
    dry_run: bool,
    sync_channels: bool = True,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Replace one user's directed following snapshot atomically."""
    username = _normalize_username(username)
    _validate_source(source)
    observed_at = observed_at or _now()
    evidence_url = f"https://x.com/{username}/following"
    channels.ensure_schema(conn)

    unique: dict[str, dict[str, Any]] = {}
    skipped = 0
    for member in followings:
        handle = _normalize_handle(member)
        if not handle:
            skipped += 1
            continue
        unique.setdefault(handle, member)

    all_handles = set(unique) | {username}
    existing_handles = {
        row["handle"]
        for row in conn.execute(
            "SELECT handle FROM accounts WHERE platform = 'x'"
        ).fetchall()
    }
    existing_fact_handles = {
        row["handle"]
        for row in conn.execute(
            """SELECT a.handle
               FROM account_source_facts f
               JOIN accounts a ON a.id = f.account_id
               WHERE f.source = ? AND f.fact = 'followed_by' AND f.value = ?""",
            (source, username),
        ).fetchall()
    }
    existing_edge_handles = {
        row["handle"]
        for row in conn.execute(
            """SELECT target.handle
               FROM graph_edges edge
               JOIN accounts source_account ON source_account.id = edge.from_account_id
               JOIN accounts target ON target.id = edge.to_account_id
               WHERE edge.source = ?
                 AND edge.relationship = 'follows'
                 AND source_account.handle = ?""",
            (source, username),
        ).fetchall()
    }

    would_create = len(all_handles - existing_handles)
    would_update = len(all_handles & existing_handles)
    would_write_facts = len(set(unique) - existing_fact_handles)
    would_write_edges = len(set(unique) - existing_edge_handles)
    stale_fact_handles = existing_fact_handles - set(unique)
    stale_edge_handles = existing_edge_handles - set(unique)

    created = 0
    updated = 0
    facts_written = 0
    edges_written = 0
    facts_removed = 0
    edges_removed = 0
    source_account_id: int | None = None
    if not dry_run:
        with conn:
            source_member = dict(source_profile)
            source_member["userName"] = username
            source_account_id, source_created = _upsert_account(
                conn,
                member=source_member,
                handle=username,
                observed_at=observed_at,
            )
            created += int(source_created)
            updated += int(not source_created)

            target_ids: list[int] = []
            for handle, member in unique.items():
                account_id, is_created = _upsert_account(
                    conn,
                    member=member,
                    handle=handle,
                    observed_at=observed_at,
                )
                target_ids.append(account_id)
                created += int(is_created)
                updated += int(not is_created)
                before_fact = _has_source_fact(
                    conn,
                    account_id=account_id,
                    source=source,
                    fact="followed_by",
                )
                conn.execute(
                    """INSERT INTO account_source_facts
                       (account_id, source, fact, value, observed_at, evidence_url)
                       VALUES (?, ?, 'followed_by', ?, ?, ?)
                       ON CONFLICT (account_id, source, fact) DO UPDATE SET
                           value = excluded.value,
                           observed_at = excluded.observed_at,
                           evidence_url = excluded.evidence_url""",
                    (account_id, source, username, observed_at, evidence_url),
                )
                facts_written += int(not before_fact)

                before_edge = conn.execute(
                    """SELECT 1 FROM graph_edges
                       WHERE from_account_id = ? AND to_account_id = ?
                         AND relationship = 'follows' AND source = ?""",
                    (source_account_id, account_id, source),
                ).fetchone()
                conn.execute(
                    """INSERT INTO graph_edges
                       (from_account_id, to_account_id, relationship, source,
                        observed_at, evidence_url)
                       VALUES (?, ?, 'follows', ?, ?, ?)
                       ON CONFLICT (from_account_id, to_account_id, relationship, source)
                       DO UPDATE SET
                           observed_at = excluded.observed_at,
                           evidence_url = excluded.evidence_url""",
                    (source_account_id, account_id, source, observed_at, evidence_url),
                )
                edges_written += int(before_edge is None)

            conn.execute(
                "CREATE TEMP TABLE IF NOT EXISTS current_following_ids "
                "(account_id INTEGER PRIMARY KEY)"
            )
            conn.execute("DELETE FROM current_following_ids")
            conn.executemany(
                "INSERT INTO current_following_ids (account_id) VALUES (?)",
                ((account_id,) for account_id in target_ids),
            )
            edge_result = conn.execute(
                """DELETE FROM graph_edges
                   WHERE source = ? AND relationship = 'follows'
                     AND from_account_id = ?
                     AND NOT EXISTS (
                         SELECT 1 FROM current_following_ids current
                         WHERE current.account_id = graph_edges.to_account_id
                     )""",
                (source, source_account_id),
            )
            fact_result = conn.execute(
                """DELETE FROM account_source_facts
                   WHERE source = ? AND fact = 'followed_by' AND value = ?
                     AND NOT EXISTS (
                         SELECT 1 FROM current_following_ids current
                         WHERE current.account_id = account_source_facts.account_id
                     )""",
                (source, username),
            )
            conn.execute("DROP TABLE current_following_ids")
            edges_removed = edge_result.rowcount
            facts_removed = fact_result.rowcount
        if sync_channels:
            channels.sync_all(conn)

    return {
        "provider": PROVIDER,
        "username": username,
        "source": source,
        "dry_run": dry_run,
        "followings_fetched": len(followings),
        "unique_handles": len(unique),
        "skipped_followings": skipped,
        "would_create_accounts": would_create,
        "would_update_accounts": would_update,
        "would_write_source_facts": would_write_facts,
        "would_write_edges": would_write_edges,
        "would_remove_source_facts": len(stale_fact_handles),
        "would_remove_edges": len(stale_edge_handles),
        "created_accounts": created,
        "updated_accounts": updated,
        "source_facts_written": facts_written,
        "edges_written": edges_written,
        "source_facts_removed": facts_removed,
        "edges_removed": edges_removed,
        "source_account_id": source_account_id,
        "evidence_url": evidence_url,
    }


def run_import_x_following(
    *,
    db_path: str | None,
    username: str,
    source: str,
    key_file: Path,
    dry_run: bool,
    timeout_seconds: float,
    page_sleep_seconds: float,
    page_size: int = 200,
    client: TwitterApiIoClient | None = None,
) -> dict[str, Any]:
    username = _normalize_username(username)
    _validate_source(source)
    if not 20 <= page_size <= 200:
        raise SourceCliError(
            code="E_PAGE_SIZE_INVALID",
            message="--page-size must be between 20 and 200.",
            hint="Use 200 for the provider's lowest per-following price.",
            exit_code=2,
        )
    if client is None:
        api_key = _read_api_key(key_file)
        client = TwitterApiIoClient(
            api_key=api_key,
            timeout=timeout_seconds,
            page_sleep_seconds=page_sleep_seconds,
        )

    observed_at = _now()
    source_profile = client.fetch_user(username=username)
    followings: list[dict[str, Any]] = []
    page_counts: list[int] = []
    for page_followings in client.iter_following_pages(
        username=username,
        page_size=page_size,
    ):
        followings.extend(page_followings)
        page_counts.append(len(page_followings))

    conn = channels.connect(db_path) if db_path else channels.connect()
    try:
        data = import_followings(
            conn,
            username=username,
            source=source,
            source_profile=source_profile,
            followings=followings,
            dry_run=dry_run,
            observed_at=observed_at,
        )
        estimated_credits = sum(
            _following_page_credits(count) for count in page_counts
        )
        data.update(
            {
                "pages_fetched": len(page_counts),
                "page_counts": page_counts,
                "estimated_provider_credits": estimated_credits,
                "estimated_provider_cost_usd": round(
                    estimated_credits / 100_000, 6
                ),
                "database": str(db_path or store.DEFAULT_DB_PATH),
            }
        )
        return data
    finally:
        conn.close()


def _result(
    *,
    command: str,
    status: str,
    data: dict[str, Any] | None,
    error_obj: dict[str, Any] | None,
    started: float,
    request_id: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "status": status,
        "data": data,
        "error": error_obj,
        "meta": {
            "request_id": request_id,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "timestamp_utc": _now(),
        },
    }


def _print_result(payload: dict[str, Any], *, plain: bool) -> None:
    if not plain:
        print(json.dumps(payload, sort_keys=True))
        return
    if payload["status"] == "error":
        err = payload["error"] or {}
        print(f"error: {err.get('code')}: {err.get('message')}")
        return
    data = payload["data"] or {}
    action = payload.get("command", "sources").split()[-1]
    print(
        f"{action}: "
        f"{data.get('unique_handles', 0)} handles, "
        f"{data.get('pages_fetched', 0)} pages, "
        f"dry_run={data.get('dry_run')}"
    )


def _add_provider_arguments(
    parser: argparse.ArgumentParser,
    *,
    default_page_sleep_seconds: float,
) -> None:
    parser.add_argument("--source", required=True)
    parser.add_argument("--db", default=None)
    parser.add_argument(
        "--key-file",
        default=str(DEFAULT_TWITTERAPI_IO_KEY_FILE),
        help="Path to a file containing the provider API key.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument(
        "--page-sleep-seconds",
        type=float,
        default=default_page_sleep_seconds,
        help="Optional client-side delay between cursor pages.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-input", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit JSON (default).")
    parser.add_argument("--plain", action="store_true", help="Emit compact text.")


def main(argv: list[str] | None = None) -> int:
    started = time.monotonic()
    request_id = str(uuid.uuid4())
    command = "sources"
    parser = JsonArgumentParser(prog="fli sources")
    sub = parser.add_subparsers(dest="action", required=True)
    import_p = sub.add_parser("import-x-list", help="Import members of one X list.")
    import_p.add_argument("--list-id", required=True)
    _add_provider_arguments(import_p, default_page_sleep_seconds=5.0)
    following_p = sub.add_parser(
        "import-x-following",
        help="Import the current accounts followed by one X user.",
    )
    following_p.add_argument("--username", required=True)
    following_p.add_argument(
        "--page-size",
        type=int,
        default=200,
        help="Provider page size (20-200); 200 has the lowest unit price.",
    )
    _add_provider_arguments(following_p, default_page_sleep_seconds=0.0)
    try:
        args = parser.parse_args(argv)
        command = f"sources {args.action}"
        if args.action == "import-x-list":
            data = run_import_x_list(
                db_path=args.db,
                list_id=args.list_id,
                source=args.source,
                key_file=Path(args.key_file).expanduser(),
                dry_run=args.dry_run,
                timeout_seconds=args.timeout_seconds,
                page_sleep_seconds=args.page_sleep_seconds,
            )
        elif args.action == "import-x-following":
            data = run_import_x_following(
                db_path=args.db,
                username=args.username,
                source=args.source,
                key_file=Path(args.key_file).expanduser(),
                dry_run=args.dry_run,
                timeout_seconds=args.timeout_seconds,
                page_sleep_seconds=args.page_sleep_seconds,
                page_size=args.page_size,
            )
        else:
            raise SourceCliError(
                code="E_USAGE",
                message="Unsupported action.",
                hint="Run `fli sources --help`.",
                exit_code=2,
            )
        payload = _result(
            command=command,
            status="ok",
            data=data,
            error_obj=None,
            started=started,
            request_id=request_id,
        )
        _print_result(payload, plain=args.plain)
        return 0
    except SourceCliError as exc:
        payload = _result(
            command=command,
            status="error",
            data=None,
            error_obj={
                "code": exc.code,
                "message": exc.message,
                "retryable": exc.retryable,
                "hint": exc.hint,
            },
            started=started,
            request_id=request_id,
        )
        plain = "--plain" in (argv or [])
        _print_result(payload, plain=plain)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
