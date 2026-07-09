"""Curated source importers.

This is intentionally small: one generic X-list importer backed by
TwitterAPI.io. It layers list membership as evidence; it does not decide who
is tracked.
"""

from __future__ import annotations

import argparse
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
PROVIDER = "twitterapi_io"


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

    def fetch_page(self, *, list_id: str, cursor: str | None) -> dict[str, Any]:
        query: dict[str, str] = {"list_id": list_id}
        if cursor:
            query["cursor"] = cursor
        url = f"{self.base_url}/twitter/list/members?{parse.urlencode(query)}"
        req = request.Request(url, headers={"X-API-Key": self.api_key})
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            exit_code = 3 if exc.code in {401, 403} else 4
            retryable = exc.code in {408, 409, 425, 429, 500, 502, 503, 504}
            raise SourceCliError(
                code="E_PROVIDER_HTTP",
                message=f"TwitterAPI.io returned HTTP {exc.code}.",
                hint="Check the API key, account credits, provider status, and list id.",
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
                message=str(payload.get("msg") or "TwitterAPI.io returned an error."),
                hint="Check the list id, API key, account credits, and provider status.",
                exit_code=4,
                retryable=False,
            )
        return payload

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


def _normalize_handle(member: dict[str, Any]) -> str | None:
    raw = member.get("userName") or member.get("username") or member.get("screen_name")
    if not raw:
        return None
    handle = str(raw).strip().removeprefix("@").lower()
    return handle or None


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
    followers_count = _int_or_none(member.get("followers"))
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


def _has_source_fact(conn: sqlite3.Connection, *, account_id: int, source: str) -> bool:
    return (
        conn.execute(
            """SELECT 1 FROM account_source_facts
               WHERE account_id = ? AND source = ? AND fact = 'list_member'""",
            (account_id, source),
        ).fetchone()
        is not None
    )


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
    if not SOURCE_RE.match(source):
        raise SourceCliError(
            code="E_SOURCE_INVALID",
            message="--source must be lowercase letters, numbers, underscores, or hyphens.",
            hint="Example: --source ai_high_signal",
            exit_code=2,
        )

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
            channels.sync_x_channels_from_accounts(conn)

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
        if wrote_any and not dry_run:
            channels.sync_x_channels_from_accounts(conn)
    return totals


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
    print(
        "import-x-list: "
        f"{data.get('unique_handles', 0)} handles, "
        f"{data.get('pages_fetched', 0)} pages, "
        f"dry_run={data.get('dry_run')}"
    )


def main(argv: list[str] | None = None) -> int:
    started = time.monotonic()
    request_id = str(uuid.uuid4())
    parser = JsonArgumentParser(prog="fli sources")
    sub = parser.add_subparsers(dest="action", required=True)
    import_p = sub.add_parser("import-x-list", help="Import members of one X list.")
    import_p.add_argument("--list-id", required=True)
    import_p.add_argument("--source", required=True)
    import_p.add_argument("--db", default=None)
    import_p.add_argument(
        "--key-file",
        default=str(DEFAULT_TWITTERAPI_IO_KEY_FILE),
        help="Path to a file containing the provider API key.",
    )
    import_p.add_argument("--timeout-seconds", type=float, default=30.0)
    import_p.add_argument(
        "--page-sleep-seconds",
        type=float,
        default=5.0,
        help="Seconds to wait between provider pages; default respects new-account QPS.",
    )
    import_p.add_argument("--dry-run", action="store_true")
    import_p.add_argument("--no-input", action="store_true")
    import_p.add_argument("--json", action="store_true", help="Emit JSON (default).")
    import_p.add_argument("--plain", action="store_true", help="Emit compact text.")
    try:
        args = parser.parse_args(argv)
        if args.action != "import-x-list":
            raise SourceCliError(
                code="E_USAGE",
                message="Unsupported action.",
                hint="Run `fli sources --help`.",
                exit_code=2,
            )
        data = run_import_x_list(
            db_path=args.db,
            list_id=args.list_id,
            source=args.source,
            key_file=Path(args.key_file).expanduser(),
            dry_run=args.dry_run,
            timeout_seconds=args.timeout_seconds,
            page_sleep_seconds=args.page_sleep_seconds,
        )
        payload = _result(
            command="sources import-x-list",
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
            command="sources import-x-list",
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
