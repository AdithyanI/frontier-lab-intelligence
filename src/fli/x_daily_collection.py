"""Date-complete, resumable collection of Registry X timelines.

This module is deliberately a thin orchestration layer around
``TwitterContentClient``.  Provider payloads remain immutable in
``x-content.db``; this module stores only the frozen cohort and evidence that
the cached request chain covers a requested UTC day range.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time as monotonic_time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib import parse

from fli import channels, sources, store, x_content


DEFAULT_MANIFEST_PATH = Path("data/derived/x-daily-collection.db")
COLLECTION_CONTRACT = "registry-x-date-complete-v2-authored-replies"
CLI_SCHEMA_VERSION = "1.0"

SCHEMA = """
CREATE TABLE IF NOT EXISTS collection_run (
    run_id TEXT PRIMARY KEY,
    collection_contract TEXT NOT NULL,
    horizon_start_day TEXT NOT NULL,
    horizon_end_day TEXT NOT NULL,
    cohort_sha256 TEXT NOT NULL,
    cohort_count INTEGER NOT NULL,
    excluded_rejected_count INTEGER NOT NULL,
    excluded_protected_count INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('planned', 'running', 'complete', 'partial')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS collection_account (
    run_id TEXT NOT NULL REFERENCES collection_run(run_id) ON DELETE CASCADE,
    handle TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    entity_kind TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    relationship TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('pending', 'cached', 'fetched', 'protected', 'failed')
    ),
    coverage_reason TEXT,
    page_count INTEGER NOT NULL DEFAULT 0,
    provider_requests INTEGER NOT NULL DEFAULT 0,
    cache_hits INTEGER NOT NULL DEFAULT 0,
    newest_published_at TEXT,
    oldest_published_at TEXT,
    observed_after_horizon INTEGER NOT NULL DEFAULT 0 CHECK (observed_after_horizon IN (0, 1)),
    reached_start_boundary INTEGER NOT NULL DEFAULT 0 CHECK (reached_start_boundary IN (0, 1)),
    reached_terminal_page INTEGER NOT NULL DEFAULT 0 CHECK (reached_terminal_page IN (0, 1)),
    error_code TEXT,
    error_message TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (run_id, handle)
);

CREATE INDEX IF NOT EXISTS idx_collection_account_work
    ON collection_account (run_id, status, handle);

CREATE TABLE IF NOT EXISTS collection_coverage_page (
    run_id TEXT NOT NULL,
    handle TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    request_sha256 TEXT NOT NULL,
    response_sha256 TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    cursor TEXT,
    next_cursor TEXT,
    newest_published_at TEXT,
    oldest_published_at TEXT,
    has_next_page INTEGER NOT NULL CHECK (has_next_page IN (0, 1)),
    PRIMARY KEY (run_id, handle, ordinal),
    FOREIGN KEY (run_id, handle)
        REFERENCES collection_account(run_id, handle) ON DELETE CASCADE
);
"""


@dataclass(frozen=True)
class CoveragePage:
    ordinal: int
    request_sha256: str
    response_sha256: str
    fetched_at: str
    cursor: str | None
    next_cursor: str | None
    newest_published_at: str | None
    oldest_published_at: str | None
    has_next_page: bool


@dataclass(frozen=True)
class Coverage:
    complete: bool
    reason: str
    pages: tuple[CoveragePage, ...]
    observed_after_horizon: bool
    reached_start_boundary: bool
    reached_terminal_page: bool
    newest_published_at: str | None
    oldest_published_at: str | None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _day(value: str | date) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)


def _day_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _published_at(value: Any) -> datetime | None:
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


def _tweets(payload: dict[str, Any]) -> list[dict[str, Any]]:
    nested = payload.get("data")
    if isinstance(nested, dict) and isinstance(nested.get("tweets"), list):
        return [item for item in nested["tweets"] if isinstance(item, dict)]
    if isinstance(payload.get("tweets"), list):
        return [item for item in payload["tweets"] if isinstance(item, dict)]
    return []


def _has_tweets_array(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    nested = payload.get("data")
    tweets = (
        nested.get("tweets")
        if isinstance(nested, dict) and "tweets" in nested
        else payload.get("tweets")
    )
    return isinstance(tweets, list) and all(
        isinstance(tweet, dict) for tweet in tweets
    )


def _tweet_dates(payload: dict[str, Any]) -> list[datetime] | None:
    """Return every tweet timestamp, failing closed on partial date evidence."""
    tweets = _tweets(payload)
    dates = [
        _published_at(tweet.get("createdAt") or tweet.get("created_at"))
        for tweet in tweets
    ]
    if any(value is None for value in dates):
        return None
    return [value for value in dates if value is not None]


def _pagination(payload: dict[str, Any]) -> tuple[bool, str | None]:
    nested = payload.get("data")
    values = nested if isinstance(nested, dict) else {}
    next_cursor = str(
        values.get("next_cursor") or payload.get("next_cursor") or ""
    ).strip() or None
    # The provider sometimes leaves an inert cursor on a terminal page.  An
    # explicit pagination flag is authoritative; the cursor is only a legacy
    # fallback when the flag is absent altogether.
    if "has_next_page" in values:
        has_next = bool(values["has_next_page"])
    elif "has_next_page" in payload:
        has_next = bool(payload["has_next_page"])
    else:
        has_next = bool(next_cursor)
    return has_next, next_cursor


def _timeline_url(handle: str, cursor: str | None = None) -> str:
    query: dict[str, str] = {
        "userName": handle,
        "includeReplies": "true",
    }
    if cursor:
        query["cursor"] = cursor
    return (
        f"{sources.TWITTERAPI_IO_BASE_URL}/twitter/user/last_tweets?"
        f"{parse.urlencode(query)}"
    )


def connect_manifest(path: Path | str = DEFAULT_MANIFEST_PATH) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn


def _cohort(registry_path: Path | str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    conn = channels.connect(registry_path)
    try:
        rows = conn.execute(
            """SELECT c.key AS handle, e.id AS entity_id, e.kind AS entity_kind,
                      e.name AS entity_name, ec.relationship
               FROM entities e
               JOIN entity_channels ec ON ec.entity_id = e.id
               JOIN channels c ON c.id = ec.channel_id AND c.kind = 'x'
               LEFT JOIN entity_registry_rejections rejected
                 ON rejected.entity_id = e.id
               WHERE rejected.entity_id IS NULL
                 AND e.kind IN ('person', 'organization')
               ORDER BY c.key, e.id, ec.relationship"""
        ).fetchall()
        # A channel has one owner by Registry contract.  Defensive de-duplication
        # keeps the cohort hash stable if relationship evidence is repeated.
        cohort: dict[str, dict[str, Any]] = {}
        for row in rows:
            cohort.setdefault(
                row["handle"],
                {
                    "handle": row["handle"],
                    "entity_id": row["entity_id"],
                    "entity_kind": row["entity_kind"],
                    "entity_name": row["entity_name"],
                    "relationship": row["relationship"],
                },
            )
        excluded = conn.execute(
            """SELECT COUNT(DISTINCT c.key) AS rejected,
                      COUNT(DISTINCT CASE
                          WHEN rejected.reason_code IN (
                              'protected_x_account',
                              'protected_x_no_public_channel'
                          ) THEN c.key END) AS protected
               FROM entity_registry_rejections rejected
               JOIN entity_channels ec ON ec.entity_id = rejected.entity_id
               JOIN channels c ON c.id = ec.channel_id AND c.kind = 'x'"""
        ).fetchone()
        return list(cohort.values()), {
            "rejected": int(excluded["rejected"] or 0),
            "protected": int(excluded["protected"] or 0),
        }
    finally:
        conn.close()


def freeze_run(
    *,
    registry_path: Path | str = store.DEFAULT_DB_PATH,
    manifest_path: Path | str = DEFAULT_MANIFEST_PATH,
    start_day: str | date,
    end_day: str | date,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Freeze the active Registry X cohort for one inclusive UTC day range."""
    start = _day(start_day)
    end = _day(end_day)
    if end < start:
        raise ValueError("end_day cannot be earlier than start_day")
    if end >= datetime.now(timezone.utc).date():
        raise ValueError("end_day must be a complete UTC day before today")
    cohort, excluded = _cohort(registry_path)
    cohort_sha = _sha256(_canonical_json(cohort))
    run_id = run_id or (
        f"x-daily-{start.isoformat()}-{end.isoformat()}-{cohort_sha[:12]}"
    )
    now = _now()
    conn = connect_manifest(manifest_path)
    try:
        existing = conn.execute(
            "SELECT * FROM collection_run WHERE run_id = ?", (run_id,)
        ).fetchone()
        if existing is not None:
            expected = (
                COLLECTION_CONTRACT,
                start.isoformat(),
                end.isoformat(),
                cohort_sha,
            )
            actual = (
                existing["collection_contract"],
                existing["horizon_start_day"],
                existing["horizon_end_day"],
                existing["cohort_sha256"],
            )
            if actual != expected:
                raise ValueError(f"run_id {run_id!r} already names a different cohort")
            return dict(existing)
        with conn:
            conn.execute(
                """INSERT INTO collection_run
                   (run_id, collection_contract, horizon_start_day,
                    horizon_end_day, cohort_sha256, cohort_count,
                    excluded_rejected_count, excluded_protected_count,
                    status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'planned', ?, ?)""",
                (
                    run_id,
                    COLLECTION_CONTRACT,
                    start.isoformat(),
                    end.isoformat(),
                    cohort_sha,
                    len(cohort),
                    excluded["rejected"],
                    excluded["protected"],
                    now,
                    now,
                ),
            )
            conn.executemany(
                """INSERT INTO collection_account
                   (run_id, handle, entity_id, entity_kind, entity_name,
                    relationship, status, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)""",
                [
                    (
                        run_id,
                        item["handle"],
                        item["entity_id"],
                        item["entity_kind"],
                        item["entity_name"],
                        item["relationship"],
                        now,
                    )
                    for item in cohort
                ],
            )
        return dict(
            conn.execute(
                "SELECT * FROM collection_run WHERE run_id = ?", (run_id,)
            ).fetchone()
        )
    finally:
        conn.close()


def _open_raw(path: Path | str) -> sqlite3.Connection | None:
    path = Path(path)
    if not path.exists():
        return None
    uri = f"file:{parse.quote(str(path.resolve()))}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _cached_response(
    conn: sqlite3.Connection,
    *,
    url: str,
    fetched_not_before: datetime,
) -> sqlite3.Row | None:
    return conn.execute(
        """SELECT rr.fetched_at, rr.response_sha256, rr.response_json
           FROM raw_request rq
           JOIN raw_response rr ON rr.request_sha256 = rq.request_sha256
           WHERE rq.url = ? AND rr.fetched_at >= ?
           ORDER BY rr.fetched_at DESC
           LIMIT 1""",
        (url, fetched_not_before.isoformat(timespec="seconds")),
    ).fetchone()


def inspect_cached_coverage(
    *,
    raw_path: Path | str = x_content.DEFAULT_DB_PATH,
    handle: str,
    start_day: str | date,
    end_day: str | date,
    max_pages: int = 100,
) -> Coverage:
    """Prove coverage from immutable cached raw responses without fetching."""
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")
    start_boundary = _day_start(_day(start_day))
    # A complete UTC end day can only be known from a response observed at or
    # after the following midnight.
    observed_after = _day_start(_day(end_day) + timedelta(days=1))
    conn = _open_raw(raw_path)
    if conn is None:
        return Coverage(False, "raw cache does not exist", (), False, False, False, None, None)
    pages: list[CoveragePage] = []
    newest: datetime | None = None
    oldest: datetime | None = None
    cursor: str | None = None
    seen: set[str] = set()
    reached_start = False
    reached_terminal = False
    try:
        for ordinal in range(1, max_pages + 1):
            url = _timeline_url(handle, cursor)
            row = _cached_response(
                conn, url=url, fetched_not_before=observed_after
            )
            if row is None:
                reason = "base response missing or stale" if ordinal == 1 else "cursor response missing or stale"
                return Coverage(False, reason, tuple(pages), bool(pages), reached_start, reached_terminal, _iso_or_none(newest), _iso_or_none(oldest))
            payload = json.loads(row["response_json"])
            if not _has_tweets_array(payload):
                return Coverage(
                    False,
                    "cached provider response is missing the tweets array",
                    tuple(pages),
                    bool(pages),
                    reached_start,
                    reached_terminal,
                    _iso_or_none(newest),
                    _iso_or_none(oldest),
                )
            dates = _tweet_dates(payload)
            if dates is None:
                return Coverage(
                    False,
                    "cached provider response contains an unparseable tweet timestamp",
                    tuple(pages),
                    bool(pages),
                    reached_start,
                    reached_terminal,
                    _iso_or_none(newest),
                    _iso_or_none(oldest),
                )
            page_newest = max(dates) if dates else None
            page_oldest = min(dates) if dates else None
            newest = max(filter(None, (newest, page_newest)), default=None)
            oldest = min(filter(None, (oldest, page_oldest)), default=None)
            has_next, next_cursor = _pagination(payload)
            pages.append(
                CoveragePage(
                    ordinal=ordinal,
                    request_sha256=_sha256(url),
                    response_sha256=row["response_sha256"],
                    fetched_at=row["fetched_at"],
                    cursor=cursor,
                    next_cursor=next_cursor,
                    newest_published_at=_iso_or_none(page_newest),
                    oldest_published_at=_iso_or_none(page_oldest),
                    has_next_page=has_next,
                )
            )
            if page_oldest is not None and page_oldest < start_boundary:
                reached_start = True
                return Coverage(True, "cached chain reaches start boundary", tuple(pages), True, True, False, _iso_or_none(newest), _iso_or_none(oldest))
            if not has_next:
                reached_terminal = True
                return Coverage(True, "cached chain reaches terminal page", tuple(pages), True, reached_start, True, _iso_or_none(newest), _iso_or_none(oldest))
            if not next_cursor:
                return Coverage(False, "provider advertised another page without a cursor", tuple(pages), True, reached_start, False, _iso_or_none(newest), _iso_or_none(oldest))
            if next_cursor in seen:
                return Coverage(False, "provider repeated a pagination cursor", tuple(pages), True, reached_start, False, _iso_or_none(newest), _iso_or_none(oldest))
            seen.add(next_cursor)
            cursor = next_cursor
        return Coverage(False, "maximum page limit reached before coverage boundary", tuple(pages), True, reached_start, reached_terminal, _iso_or_none(newest), _iso_or_none(oldest))
    finally:
        conn.close()


def _iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat(timespec="seconds") if value else None


def _write_coverage(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    handle: str,
    coverage: Coverage,
    status: str,
    provider_requests: int = 0,
    cache_hits: int = 0,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    conn.execute(
        "DELETE FROM collection_coverage_page WHERE run_id = ? AND handle = ?",
        (run_id, handle),
    )
    conn.executemany(
        """INSERT INTO collection_coverage_page
           (run_id, handle, ordinal, request_sha256, response_sha256,
            fetched_at, cursor, next_cursor, newest_published_at,
            oldest_published_at, has_next_page)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                run_id,
                handle,
                page.ordinal,
                page.request_sha256,
                page.response_sha256,
                page.fetched_at,
                page.cursor,
                page.next_cursor,
                page.newest_published_at,
                page.oldest_published_at,
                int(page.has_next_page),
            )
            for page in coverage.pages
        ],
    )
    conn.execute(
        """UPDATE collection_account
           SET status = ?, coverage_reason = ?, page_count = ?,
               provider_requests = provider_requests + ?,
               cache_hits = cache_hits + ?, newest_published_at = ?,
               oldest_published_at = ?, observed_after_horizon = ?,
               reached_start_boundary = ?, reached_terminal_page = ?,
               error_code = ?, error_message = ?, updated_at = ?
           WHERE run_id = ? AND handle = ?""",
        (
            status,
            coverage.reason,
            len(coverage.pages),
            provider_requests,
            cache_hits,
            coverage.newest_published_at,
            coverage.oldest_published_at,
            int(coverage.observed_after_horizon),
            int(coverage.reached_start_boundary),
            int(coverage.reached_terminal_page),
            error_code,
            error_message,
            _now(),
            run_id,
            handle,
        ),
    )


def _summary(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    run = conn.execute(
        "SELECT * FROM collection_run WHERE run_id = ?", (run_id,)
    ).fetchone()
    if run is None:
        raise ValueError(f"unknown collection run: {run_id}")
    statuses = {
        row["status"]: row["n"]
        for row in conn.execute(
            """SELECT status, COUNT(*) AS n FROM collection_account
               WHERE run_id = ? GROUP BY status""",
            (run_id,),
        )
    }
    totals = conn.execute(
        """SELECT COALESCE(SUM(provider_requests), 0) AS provider_requests,
                  COALESCE(SUM(cache_hits), 0) AS cache_hits,
                  COALESCE(SUM(page_count), 0) AS pages,
                  COUNT(*) AS accounts
           FROM collection_account WHERE run_id = ?""",
        (run_id,),
    ).fetchone()
    return {
        "run_id": run_id,
        "status": run["status"],
        "contract": run["collection_contract"],
        "start_day": run["horizon_start_day"],
        "end_day": run["horizon_end_day"],
        "cohort_sha256": run["cohort_sha256"],
        "accounts": totals["accounts"],
        "statuses": statuses,
        "pages": totals["pages"],
        "provider_requests": totals["provider_requests"],
        "cache_hits": totals["cache_hits"],
        "cached_accounts": statuses.get("cached", 0),
        "cached_pages": conn.execute(
            """SELECT COALESCE(SUM(page_count), 0)
               FROM collection_account
               WHERE run_id = ? AND status = 'cached'""",
            (run_id,),
        ).fetchone()[0],
        "failures": statuses.get("failed", 0),
        "pending_accounts": statuses.get("pending", 0),
        "unfinished_accounts": statuses.get("pending", 0)
        + statuses.get("failed", 0),
        "excluded": {
            "rejected": run["excluded_rejected_count"],
            "protected": run["excluded_protected_count"],
        },
        "zero_following_policy": "included when Registry-active; outbound graph degree does not govern public-post collection",
    }


def collection_status(
    *,
    manifest_path: Path | str = DEFAULT_MANIFEST_PATH,
    run_id: str,
) -> dict[str, Any]:
    """Return the durable status of one frozen collection run."""
    conn = connect_manifest(manifest_path)
    try:
        return _summary(conn, run_id)
    finally:
        conn.close()


def plan_collection(
    *,
    registry_path: Path | str = store.DEFAULT_DB_PATH,
    raw_path: Path | str = x_content.DEFAULT_DB_PATH,
    manifest_path: Path | str = DEFAULT_MANIFEST_PATH,
    start_day: str | date,
    end_day: str | date,
    run_id: str | None = None,
    max_pages: int = 100,
) -> dict[str, Any]:
    """Freeze and inspect a run.  No provider call is made."""
    frozen = freeze_run(
        registry_path=registry_path,
        manifest_path=manifest_path,
        start_day=start_day,
        end_day=end_day,
        run_id=run_id,
    )
    run_id = frozen["run_id"]
    conn = connect_manifest(manifest_path)
    try:
        accounts = conn.execute(
            """SELECT handle, status FROM collection_account
               WHERE run_id = ? ORDER BY handle""",
            (run_id,),
        ).fetchall()
        for account in accounts:
            if account["status"] == "protected":
                continue
            coverage = inspect_cached_coverage(
                raw_path=raw_path,
                handle=account["handle"],
                start_day=start_day,
                end_day=end_day,
                max_pages=max_pages,
            )
            with conn:
                _write_coverage(
                    conn,
                    run_id=run_id,
                    handle=account["handle"],
                    coverage=coverage,
                    status=(
                        account["status"]
                        if coverage.complete
                        and account["status"] == "fetched"
                        else "cached"
                        if coverage.complete
                        else "pending"
                    ),
                )
        complete = conn.execute(
            """SELECT COUNT(*) FROM collection_account
               WHERE run_id = ? AND status IN ('cached', 'fetched', 'protected')""",
            (run_id,),
        ).fetchone()[0]
        total = conn.execute(
            "SELECT cohort_count FROM collection_run WHERE run_id = ?", (run_id,)
        ).fetchone()[0]
        status = "complete" if complete == total else "planned"
        with conn:
            conn.execute(
                """UPDATE collection_run SET status = ?, updated_at = ?
                   WHERE run_id = ?""",
                (status, _now(), run_id),
            )
        return _summary(conn, run_id)
    finally:
        conn.close()


def _fetch_missing_chain(
    *,
    client: x_content.TwitterContentClient,
    handle: str,
    start_day: date,
    max_pages: int,
) -> None:
    start_boundary = _day_start(start_day)
    cursor: str | None = None
    seen: set[str] = set()
    original_refresh = getattr(client, "refresh", None)
    if original_refresh is not None:
        # Planning already proved the cached chain insufficient.  Reusing the
        # same stale base page would not advance coverage.
        client.refresh = True
    try:
        for _ordinal in range(1, max_pages + 1):
            payload = client.fetch_recent_tweets_page(
                username=handle,
                cursor=cursor,
                include_replies=True,
            )
            if not _has_tweets_array(payload):
                raise sources.SourceCliError(
                    code="E_PROVIDER_SCHEMA",
                    message="Timeline response is missing the tweets array.",
                    hint="Retry after the provider contract is healthy.",
                    retryable=True,
                )
            dates = _tweet_dates(payload)
            if dates is None:
                raise sources.SourceCliError(
                    code="E_PROVIDER_SCHEMA",
                    message="Timeline response contains an unparseable tweet timestamp.",
                    hint="Retry after the provider contract is healthy.",
                    retryable=True,
                )
            if dates and min(dates) < start_boundary:
                return
            has_next, next_cursor = _pagination(payload)
            if not has_next:
                return
            if not next_cursor or next_cursor in seen:
                return
            seen.add(next_cursor)
            cursor = next_cursor
    finally:
        if original_refresh is not None:
            client.refresh = original_refresh


def execute_collection(
    *,
    client: x_content.TwitterContentClient,
    registry_path: Path | str = store.DEFAULT_DB_PATH,
    raw_path: Path | str = x_content.DEFAULT_DB_PATH,
    manifest_path: Path | str = DEFAULT_MANIFEST_PATH,
    start_day: str | date,
    end_day: str | date,
    run_id: str | None = None,
    max_pages: int = 100,
    workers: int = 1,
) -> dict[str, Any]:
    """Fetch only insufficient accounts and resume safely account by account."""
    if workers < 1 or workers > 64:
        raise ValueError("workers must be between 1 and 64")
    client_db = getattr(client, "db", None)
    if client_db is not None:
        db_file = client_db.execute("PRAGMA database_list").fetchone()[2]
        if db_file and Path(db_file).resolve() != Path(raw_path).resolve():
            raise ValueError(
                "client db_path and raw_path must identify the same X content cache"
            )
    planned = plan_collection(
        registry_path=registry_path,
        raw_path=raw_path,
        manifest_path=manifest_path,
        start_day=start_day,
        end_day=end_day,
        run_id=run_id,
        max_pages=max_pages,
    )
    run_id = planned["run_id"]
    conn = connect_manifest(manifest_path)
    try:
        with conn:
            conn.execute(
                "UPDATE collection_run SET status = 'running', updated_at = ? WHERE run_id = ?",
                (_now(), run_id),
            )
        pending = conn.execute(
            """SELECT handle FROM collection_account
               WHERE run_id = ? AND status IN ('pending', 'failed')
               ORDER BY handle""",
            (run_id,),
        ).fetchall()
        def collect_account(handle: str) -> dict[str, Any]:
            before = client.stats() if workers == 1 else None
            error_code = None
            error_message = None
            status = "failed"
            try:
                _fetch_missing_chain(
                    client=client,
                    handle=handle,
                    start_day=_day(start_day),
                    max_pages=max_pages,
                )
                coverage = inspect_cached_coverage(
                    raw_path=raw_path,
                    handle=handle,
                    start_day=start_day,
                    end_day=end_day,
                    max_pages=max_pages,
                )
                status = "fetched" if coverage.complete else "failed"
                if not coverage.complete:
                    error_code = "E_COVERAGE_INCOMPLETE"
                    error_message = coverage.reason
            except sources.SourceCliError as exc:
                protected = exc.code == "E_ACCOUNT_PROTECTED" or any(
                    word in exc.message.lower() for word in ("protected", "private")
                )
                status = "protected" if protected else "failed"
                error_code = exc.code
                error_message = exc.message
                coverage = Coverage(
                    protected,
                    "provider identifies protected account" if protected else "provider request failed",
                    (),
                    False,
                    False,
                    False,
                    None,
                    None,
                )
            except Exception as exc:  # account-local failure; the run remains resumable
                error_code = type(exc).__name__
                error_message = str(exc)
                coverage = Coverage(False, "provider request failed", (), False, False, False, None, None)
            after = client.stats() if workers == 1 else None
            return {
                "handle": handle,
                "coverage": coverage,
                "status": status,
                "provider_requests": (
                    max(
                        0,
                        int(after["provider_requests"])
                        - int(before["provider_requests"]),
                    )
                    if before is not None and after is not None
                    else len(coverage.pages)
                ),
                "cache_hits": (
                    max(0, int(after["cache_hits"]) - int(before["cache_hits"]))
                    if before is not None and after is not None
                    else 0
                ),
                "error_code": error_code,
                "error_message": error_message,
            }

        def persist(result: dict[str, Any]) -> None:
            with conn:
                _write_coverage(
                    conn,
                    run_id=run_id,
                    handle=str(result["handle"]),
                    coverage=result["coverage"],
                    status=str(result["status"]),
                    provider_requests=int(result["provider_requests"]),
                    cache_hits=int(result["cache_hits"]),
                    error_code=result["error_code"],
                    error_message=result["error_message"],
                )

        handles = [str(account["handle"]) for account in pending]
        if workers == 1:
            for handle in handles:
                persist(collect_account(handle))
        else:
            original_refresh = client.refresh
            client.refresh = True
            try:
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    futures = {
                        executor.submit(collect_account, handle): handle
                        for handle in handles
                    }
                    for future in as_completed(futures):
                        persist(future.result())
            finally:
                client.refresh = original_refresh
        failures = conn.execute(
            """SELECT COUNT(*) FROM collection_account
               WHERE run_id = ? AND status IN ('pending', 'failed')""",
            (run_id,),
        ).fetchone()[0]
        with conn:
            conn.execute(
                """UPDATE collection_run SET status = ?, updated_at = ?
                   WHERE run_id = ?""",
                ("complete" if failures == 0 else "partial", _now(), run_id),
            )
        return _summary(conn, run_id)
    finally:
        conn.close()


def _result(
    *,
    command: str,
    status: str,
    data: dict[str, Any] | None,
    error: dict[str, Any] | None,
    started: float,
    request_id: str,
) -> dict[str, Any]:
    return {
        "schema_version": CLI_SCHEMA_VERSION,
        "command": command,
        "status": status,
        "data": data,
        "error": error,
        "meta": {
            "request_id": request_id,
            "duration_ms": round(
                (monotonic_time.monotonic() - started) * 1000, 3
            ),
            "timestamp_utc": _now(),
        },
    }


def _print_result(payload: dict[str, Any], *, plain: bool) -> None:
    if not plain:
        print(json.dumps(payload, sort_keys=True))
        return
    if payload["status"] == "error":
        error = payload["error"] or {}
        print(
            " ".join(
                (
                    "status=error",
                    f"code={error.get('code', 'E_INTERNAL')}",
                    f"retryable={str(bool(error.get('retryable'))).lower()}",
                    f"message={json.dumps(error.get('message', ''))}",
                )
            )
        )
        return
    data = payload["data"] or {}
    print(
        " ".join(
            (
                "status=ok",
                f"run_id={data.get('run_id', '')}",
                f"run_status={data.get('status', '')}",
                f"accounts={data.get('accounts', 0)}",
                f"cached_accounts={data.get('cached_accounts', 0)}",
                f"provider_requests={data.get('provider_requests', 0)}",
                f"failures={data.get('failures', 0)}",
            )
        )
    )


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--registry-db", type=Path, default=store.DEFAULT_DB_PATH)
    parser.add_argument("--raw-db", type=Path, default=x_content.DEFAULT_DB_PATH)
    parser.add_argument("--manifest-db", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--start-day", type=date.fromisoformat, required=True)
    parser.add_argument("--end-day", type=date.fromisoformat, required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--no-input", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true")
    mode.add_argument("--plain", action="store_true")


def main(argv: list[str] | None = None) -> int:
    """Machine-primary CLI for planning and resuming daily X collection."""
    started = monotonic_time.monotonic()
    request_id = str(uuid.uuid4())
    command = "x-daily-collection"
    parser = sources.JsonArgumentParser(
        prog="fli x-daily-collection",
        description="Prove or collect date-complete Registry X timelines.",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    plan_parser = subparsers.add_parser(
        "plan", help="Freeze the cohort and inspect raw-cache coverage only."
    )
    _add_common_arguments(plan_parser)
    execute_parser = subparsers.add_parser(
        "execute", help="Resume the plan, fetching only insufficient accounts."
    )
    _add_common_arguments(execute_parser)
    execute_parser.add_argument(
        "--key-file",
        type=Path,
        default=sources.DEFAULT_TWITTERAPI_IO_KEY_FILE,
        help="File containing the TwitterAPI.io key.",
    )
    execute_parser.add_argument("--timeout-seconds", type=float, default=30.0)
    execute_parser.add_argument("--page-sleep-seconds", type=float, default=0.0)
    execute_parser.add_argument("--workers", type=int, default=1)
    status_parser = subparsers.add_parser(
        "status", help="Inspect one durable collection run without provider access."
    )
    status_parser.add_argument("--manifest-db", type=Path, default=DEFAULT_MANIFEST_PATH)
    status_parser.add_argument("--run-id", required=True)
    status_parser.add_argument("--no-input", action="store_true")
    status_mode = status_parser.add_mutually_exclusive_group()
    status_mode.add_argument("--json", action="store_true")
    status_mode.add_argument("--plain", action="store_true")
    args = None
    client = None
    try:
        args = parser.parse_args(argv)
        command = f"x-daily-collection {args.action}"
        if args.action == "plan":
            data = plan_collection(
                registry_path=args.registry_db,
                raw_path=args.raw_db,
                manifest_path=args.manifest_db,
                start_day=args.start_day,
                end_day=args.end_day,
                run_id=args.run_id,
                max_pages=args.max_pages,
            )
        elif args.action == "execute":
            if args.timeout_seconds <= 0:
                raise ValueError("timeout-seconds must be greater than zero")
            if args.page_sleep_seconds < 0:
                raise ValueError("page-sleep-seconds cannot be negative")
            client = x_content.create_client(
                db_path=args.raw_db,
                key_file=args.key_file.expanduser(),
                timeout=args.timeout_seconds,
                page_sleep_seconds=args.page_sleep_seconds,
            )
            data = execute_collection(
                client=client,
                registry_path=args.registry_db,
                raw_path=args.raw_db,
                manifest_path=args.manifest_db,
                start_day=args.start_day,
                end_day=args.end_day,
                run_id=args.run_id,
                max_pages=args.max_pages,
                workers=args.workers,
            )
        else:
            data = collection_status(
                manifest_path=args.manifest_db,
                run_id=args.run_id,
            )
        payload = _result(
            command=command,
            status="ok",
            data=data,
            error=None,
            started=started,
            request_id=request_id,
        )
        _print_result(payload, plain=args.plain)
        return 0
    except sources.SourceCliError as exc:
        payload = _result(
            command=command,
            status="error",
            data=None,
            error={
                "code": exc.code,
                "message": exc.message,
                "retryable": exc.retryable,
                "hint": exc.hint,
            },
            started=started,
            request_id=request_id,
        )
        _print_result(payload, plain=bool(args and args.plain))
        return exc.exit_code
    except (ValueError, FileNotFoundError) as exc:
        payload = _result(
            command=command,
            status="error",
            data=None,
            error={
                "code": "E_VALIDATION",
                "message": str(exc),
                "retryable": False,
                "hint": "Check the requested dates, paths, run id, and numeric limits.",
            },
            started=started,
            request_id=request_id,
        )
        _print_result(payload, plain=bool(args and args.plain))
        return 2
    except TimeoutError as exc:
        payload = _result(
            command=command,
            status="error",
            data=None,
            error={
                "code": "E_TIMEOUT",
                "message": str(exc) or "Collection dependency timed out.",
                "retryable": True,
                "hint": "Retry the same command; the manifest will resume completed accounts.",
            },
            started=started,
            request_id=request_id,
        )
        _print_result(payload, plain=bool(args and args.plain))
        return 5
    except sqlite3.Error as exc:
        payload = _result(
            command=command,
            status="error",
            data=None,
            error={
                "code": "E_STORAGE",
                "message": str(exc),
                "retryable": True,
                "hint": "Check database paths and locks, then retry the same command.",
            },
            started=started,
            request_id=request_id,
        )
        _print_result(payload, plain=bool(args and args.plain))
        return 4
    except KeyboardInterrupt:
        payload = _result(
            command=command,
            status="error",
            data=None,
            error={
                "code": "E_INTERRUPTED",
                "message": "Collection was interrupted; completed accounts remain resumable.",
                "retryable": True,
                "hint": "Run the same execute command again to resume.",
            },
            started=started,
            request_id=request_id,
        )
        _print_result(payload, plain=bool(args and args.plain))
        return 5
    except Exception as exc:
        payload = _result(
            command=command,
            status="error",
            data=None,
            error={
                "code": "E_INTERNAL",
                "message": str(exc) or type(exc).__name__,
                "retryable": False,
                "hint": "Inspect the saved manifest and rerun after correcting the reported issue.",
            },
            started=started,
            request_id=request_id,
        )
        _print_result(payload, plain=bool(args and args.plain))
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    sys.exit(main())
