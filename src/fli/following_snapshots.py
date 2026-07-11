"""Local-first, resumable storage for outgoing-X-follow snapshots.

The tracked product database supplies a frozen source cohort. Provider pages
and derived edges live in a separate, ignored SQLite file keyed by snapshot,
source X ID, and request cursor. This module deliberately does not call the
provider; collection can be added without changing the storage contract.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import sqlite3
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fli import sources


RESULT_SCHEMA_VERSION = "1.0"
SNAPSHOT_SCHEMA_VERSION = "following-snapshot-v1"
COHORT_SCHEMA_VERSION = "following-cohort-v1"
DEFAULT_PROVIDER = "twitterapi_io"
DEFAULT_ENDPOINT = "/twitter/user/followings"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRODUCT_DB = REPO_ROOT / "data" / "fli.db"
DEFAULT_COHORT_DIR = REPO_ROOT / "data" / "following" / "cohorts"
DEFAULT_SNAPSHOT_ROOT = REPO_ROOT / "data" / "raw" / "following"
PROFILE_CREDITS = 18

SOURCE_STATUSES = frozenset(
    {
        "pending",
        "in_progress",
        "complete",
        "protected",
        "missing",
        "unavailable",
        "failed",
    }
)
TERMINAL_SOURCE_STATUSES = frozenset(
    {"complete", "protected", "missing", "unavailable", "failed"}
)

SCHEMA = f"""
CREATE TABLE snapshot_run (
    snapshot_id TEXT PRIMARY KEY,
    cohort_id TEXT NOT NULL,
    cohort_sha256 TEXT NOT NULL,
    cohort_manifest_path TEXT NOT NULL,
    checkpoint_commit TEXT NOT NULL,
    checkpoint_db_sha256 TEXT NOT NULL,
    provider TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    schema_version TEXT NOT NULL CHECK (schema_version = '{SNAPSHOT_SCHEMA_VERSION}'),
    created_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('initialized', 'collecting', 'complete')),
    source_count INTEGER NOT NULL CHECK (source_count >= 0),
    reported_cost_usd REAL,
    estimated_cost_usd REAL
);

CREATE TABLE source_fetch (
    source_x_id TEXT PRIMARY KEY,
    source_handle TEXT NOT NULL UNIQUE,
    display_name TEXT,
    followers_count INTEGER,
    advertised_following_count INTEGER,
    next_cursor TEXT NOT NULL DEFAULT '',
    fetched_count INTEGER NOT NULL DEFAULT 0 CHECK (fetched_count >= 0),
    raw_page_count INTEGER NOT NULL DEFAULT 0 CHECK (raw_page_count >= 0),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'in_progress', 'complete', 'protected',
                          'missing', 'unavailable', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    last_error_code TEXT,
    last_error_message TEXT,
    updated_at TEXT NOT NULL
);
CREATE INDEX idx_source_fetch_status ON source_fetch (status, source_handle);

CREATE TABLE raw_profile (
    source_x_id TEXT PRIMARY KEY REFERENCES source_fetch (source_x_id),
    retrieved_at TEXT NOT NULL,
    profile_json TEXT NOT NULL,
    profile_sha256 TEXT NOT NULL,
    protected INTEGER NOT NULL CHECK (protected IN (0, 1)),
    advertised_following_count INTEGER
);

CREATE TABLE raw_page (
    id INTEGER PRIMARY KEY,
    source_x_id TEXT NOT NULL REFERENCES source_fetch (source_x_id),
    request_cursor TEXT NOT NULL,
    next_cursor TEXT,
    item_count INTEGER NOT NULL CHECK (item_count >= 0),
    retrieved_at TEXT NOT NULL,
    response_json TEXT NOT NULL,
    response_sha256 TEXT NOT NULL,
    UNIQUE (source_x_id, request_cursor)
);
CREATE INDEX idx_raw_page_source ON raw_page (source_x_id, id);

CREATE TABLE account (
    x_id TEXT PRIMARY KEY,
    handle TEXT NOT NULL,
    display_name TEXT,
    bio TEXT,
    followers_count INTEGER,
    first_observed_at TEXT NOT NULL,
    last_observed_at TEXT NOT NULL
);
CREATE INDEX idx_account_handle ON account (handle);

CREATE TABLE edge (
    source_x_id TEXT NOT NULL REFERENCES source_fetch (source_x_id),
    target_x_id TEXT NOT NULL REFERENCES account (x_id),
    raw_page_id INTEGER NOT NULL REFERENCES raw_page (id),
    observed_at TEXT NOT NULL,
    PRIMARY KEY (source_x_id, target_x_id)
);
CREATE INDEX idx_edge_target ON edge (target_x_id, source_x_id);
"""


@dataclass
class SnapshotCliError(Exception):
    code: str
    message: str
    hint: str
    exit_code: int = 1
    retryable: bool = False


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise SnapshotCliError(
            code="E_USAGE",
            message=message,
            hint=f"Run `{self.prog} --help` for valid arguments.",
            exit_code=2,
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _normalize_handle(value: Any) -> str | None:
    handle = str(value or "").strip().removeprefix("@").lower()
    return handle or None


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None


def _profile_following_count(profile: dict[str, Any]) -> int | None:
    for key in (
        "following",
        "following_count",
        "followingCount",
        "friends_count",
        "friendsCount",
    ):
        value = _int_or_none(profile.get(key))
        if value is not None:
            return value
    return None


def _following_page_credits(returned: int) -> int:
    if returned <= 0:
        return 0
    if returned >= 200:
        return returned
    if returned >= 100:
        return returned * 2
    return max(60, returned * 3)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise SnapshotCliError(
            code="E_NOT_FOUND",
            message=f"File does not exist: {path}",
            hint="Check the path and freeze the cohort before initializing a snapshot.",
            exit_code=3,
        ) from exc
    except json.JSONDecodeError as exc:
        raise SnapshotCliError(
            code="E_INVALID_JSON",
            message=f"File is not valid JSON: {path}",
            hint="Regenerate the artifact from its source command.",
            exit_code=3,
        ) from exc
    if not isinstance(value, dict):
        raise SnapshotCliError(
            code="E_INVALID_MANIFEST",
            message=f"Manifest must contain one JSON object: {path}",
            hint="Regenerate the cohort manifest.",
            exit_code=3,
        )
    return value


def _cohort_hash(sources: list[dict[str, Any]]) -> str:
    return _sha256_bytes(_canonical_json(sources).encode())


def _active_x_sources(product_db: Path) -> list[dict[str, Any]]:
    if not product_db.exists():
        raise SnapshotCliError(
            code="E_NOT_FOUND",
            message=f"Product database does not exist: {product_db}",
            hint="Pass --db with the tracked Registry database path.",
            exit_code=3,
        )
    uri = f"file:{product_db.resolve()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT a.x_id, lower(a.handle) AS handle,
                      a.display_name, a.followers_count
               FROM accounts a
               WHERE a.platform = 'x'
                 AND trim(COALESCE(a.x_id, '')) != ''
                 AND NOT EXISTS (
                     SELECT 1
                     FROM channels c
                     JOIN entity_channels ec ON ec.channel_id = c.id
                     JOIN entity_registry_rejections r ON r.entity_id = ec.entity_id
                     WHERE c.kind = 'x'
                       AND lower(c.key) = lower(a.handle)
                 )
               ORDER BY lower(a.handle), a.x_id"""
        ).fetchall()
    except sqlite3.Error as exc:
        raise SnapshotCliError(
            code="E_PRODUCT_DB_SCHEMA",
            message="Product database does not contain the expected Registry schema.",
            hint="Use the cleaned tracked data/fli.db checkpoint.",
            exit_code=3,
        ) from exc
    finally:
        conn.close()

    sources = [
        {
            "x_id": str(row["x_id"]),
            "handle": row["handle"],
            "display_name": row["display_name"],
            "followers_count": row["followers_count"],
        }
        for row in rows
    ]
    x_ids = [source["x_id"] for source in sources]
    handles = [source["handle"] for source in sources]
    if len(x_ids) != len(set(x_ids)) or len(handles) != len(set(handles)):
        raise SnapshotCliError(
            code="E_COHORT_DUPLICATE",
            message="Active X cohort contains a duplicate stable ID or handle.",
            hint="Resolve Registry identity duplication before freezing the cohort.",
            exit_code=3,
        )
    return sources


def freeze_cohort(
    *,
    product_db: Path,
    output_path: Path,
    cohort_id: str,
    created_at: str | None = None,
    checkpoint_commit: str | None = None,
) -> dict[str, Any]:
    """Freeze active, non-rejected Registry X accounts into tracked JSON."""
    product_db = product_db.resolve()
    sources = _active_x_sources(product_db)
    manifest = {
        "schema_version": COHORT_SCHEMA_VERSION,
        "cohort_id": cohort_id,
        "created_at": created_at or _now(),
        "source": {
            "database": str(product_db.relative_to(REPO_ROOT))
            if product_db.is_relative_to(REPO_ROOT)
            else str(product_db),
            "checkpoint_commit": checkpoint_commit or _git_head(),
            "database_sha256": _sha256_file(product_db),
        },
        "selection": {
            "platform": "x",
            "rule": "all stored X accounts except reason-bearing Registry rejections",
            "requires_stable_x_id": True,
        },
        "source_count": len(sources),
        "cohort_sha256": _cohort_hash(sources),
        "sources": sources,
    }
    if output_path.exists():
        existing = _load_json(output_path)
        immutable_fields = ("cohort_id", "cohort_sha256", "source_count", "sources")
        if all(existing.get(field) == manifest.get(field) for field in immutable_fields):
            return {**existing, "output_path": str(output_path), "created": False}
        raise SnapshotCliError(
            code="E_IMMUTABLE_CONFLICT",
            message=f"Frozen cohort already exists with different content: {output_path}",
            hint="Use a new cohort ID and output path for a changed Registry boundary.",
            exit_code=4,
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return {**manifest, "output_path": str(output_path), "created": True}


def _validated_cohort(path: Path) -> dict[str, Any]:
    manifest = _load_json(path)
    sources = manifest.get("sources")
    source_meta = manifest.get("source")
    if (
        manifest.get("schema_version") != COHORT_SCHEMA_VERSION
        or not isinstance(sources, list)
        or not isinstance(source_meta, dict)
        or not source_meta.get("checkpoint_commit")
        or not source_meta.get("database_sha256")
        or manifest.get("source_count") != len(sources)
        or manifest.get("cohort_sha256") != _cohort_hash(sources)
    ):
        raise SnapshotCliError(
            code="E_INVALID_COHORT",
            message=f"Cohort manifest failed schema or checksum validation: {path}",
            hint="Regenerate it with `fli following-snapshot freeze-cohort`.",
            exit_code=3,
        )
    return manifest


def connect_snapshot(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_snapshot(
    *,
    snapshot_id: str,
    cohort_path: Path,
    snapshot_db: Path,
    created_at: str | None = None,
    provider: str = DEFAULT_PROVIDER,
    endpoint: str = DEFAULT_ENDPOINT,
) -> dict[str, Any]:
    """Create one local snapshot DB from an immutable cohort manifest."""
    cohort = _validated_cohort(cohort_path)
    snapshot_db.parent.mkdir(parents=True, exist_ok=True)
    if snapshot_db.exists():
        conn = connect_snapshot(snapshot_db)
        try:
            row = conn.execute("SELECT * FROM snapshot_run").fetchone()
        except sqlite3.Error as exc:
            conn.close()
            raise SnapshotCliError(
                code="E_INVALID_SNAPSHOT",
                message=f"Existing snapshot database has an invalid schema: {snapshot_db}",
                hint="Choose a new snapshot ID or remove only the unneeded local artifact.",
                exit_code=4,
            ) from exc
        if (
            row
            and row["snapshot_id"] == snapshot_id
            and row["cohort_sha256"] == cohort["cohort_sha256"]
        ):
            data = snapshot_summary(conn)
            conn.close()
            return {**data, "database": str(snapshot_db), "created": False}
        conn.close()
        raise SnapshotCliError(
            code="E_IMMUTABLE_CONFLICT",
            message=f"Snapshot path already belongs to a different run: {snapshot_db}",
            hint="Use a new snapshot ID/path; snapshots are never replaced in place.",
            exit_code=4,
        )

    conn = connect_snapshot(snapshot_db)
    observed_at = created_at or _now()
    source_meta = cohort["source"]
    try:
        conn.executescript(SCHEMA)
        conn.execute(
            """INSERT INTO snapshot_run
               (snapshot_id, cohort_id, cohort_sha256, cohort_manifest_path,
                checkpoint_commit, checkpoint_db_sha256, provider, endpoint,
                schema_version, created_at, status, source_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'initialized', ?)""",
            (
                snapshot_id,
                cohort["cohort_id"],
                cohort["cohort_sha256"],
                str(cohort_path),
                source_meta["checkpoint_commit"],
                source_meta["database_sha256"],
                provider,
                endpoint,
                SNAPSHOT_SCHEMA_VERSION,
                observed_at,
                cohort["source_count"],
            ),
        )
        conn.executemany(
            """INSERT INTO source_fetch
               (source_x_id, source_handle, display_name, followers_count, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (
                    source["x_id"],
                    source["handle"],
                    source.get("display_name"),
                    source.get("followers_count"),
                    observed_at,
                )
                for source in cohort["sources"]
            ],
        )
        conn.commit()
        data = snapshot_summary(conn)
    except Exception:
        conn.close()
        snapshot_db.unlink(missing_ok=True)
        raise
    conn.close()
    return {**data, "database": str(snapshot_db), "created": True}


def _snapshot_run(conn: sqlite3.Connection) -> sqlite3.Row:
    try:
        rows = conn.execute("SELECT * FROM snapshot_run").fetchall()
    except sqlite3.Error as exc:
        raise SnapshotCliError(
            code="E_INVALID_SNAPSHOT",
            message="Snapshot database does not contain the expected schema.",
            hint="Initialize it with `fli following-snapshot init`.",
            exit_code=3,
        ) from exc
    if len(rows) != 1:
        raise SnapshotCliError(
            code="E_INVALID_SNAPSHOT",
            message="Snapshot database must contain exactly one run.",
            hint="Create one SQLite file per snapshot ID.",
            exit_code=3,
        )
    return rows[0]


def _ensure_mutable(conn: sqlite3.Connection) -> sqlite3.Row:
    run = _snapshot_run(conn)
    if run["status"] == "complete":
        raise SnapshotCliError(
            code="E_SNAPSHOT_COMPLETE",
            message=f"Snapshot {run['snapshot_id']} is complete and immutable.",
            hint="Create a new snapshot ID for refreshed provider evidence.",
            exit_code=4,
        )
    return run


def _member_fields(member: dict[str, Any]) -> tuple[str | None, str | None]:
    x_id = str(member.get("id") or member.get("id_str") or "").strip() or None
    handle = _normalize_handle(
        member.get("userName") or member.get("username") or member.get("screen_name")
    )
    return x_id, handle


def record_page(
    conn: sqlite3.Connection,
    *,
    source_x_id: str,
    request_cursor: str | None,
    payload: dict[str, Any],
    retrieved_at: str | None = None,
    advertised_following_count: int | None = None,
) -> dict[str, Any]:
    """Atomically cache one provider page and derive its accounts/edges."""
    retrieved_at = retrieved_at or _now()
    cursor_key = request_cursor or ""
    raw_json = _canonical_json(payload)
    response_sha256 = _sha256_bytes(raw_json.encode())
    followers = payload.get("followings")
    if not isinstance(followers, list):
        raise SnapshotCliError(
            code="E_PROVIDER_SHAPE",
            message="Following response does not contain a followings array.",
            hint="Preserve the response separately and inspect the provider contract.",
            exit_code=4,
            retryable=True,
        )
    has_next = bool(payload.get("has_next_page"))
    next_cursor = str(payload.get("next_cursor") or "")
    if has_next and not next_cursor:
        raise SnapshotCliError(
            code="E_PROVIDER_CURSOR_MISSING",
            message="Provider reported another page without a cursor.",
            hint="Do not advance the source; retry or inspect the provider response.",
            exit_code=4,
            retryable=True,
        )
    if next_cursor == cursor_key and has_next:
        raise SnapshotCliError(
            code="E_PROVIDER_CURSOR_REPEAT",
            message="Provider repeated the current pagination cursor.",
            hint="Stop this source to avoid an infinite collection loop.",
            exit_code=4,
            retryable=True,
        )

    conn.execute("BEGIN IMMEDIATE")
    try:
        existing = conn.execute(
            """SELECT id, response_sha256 FROM raw_page
               WHERE source_x_id = ? AND request_cursor = ?""",
            (source_x_id, cursor_key),
        ).fetchone()
        if existing:
            if existing["response_sha256"] != response_sha256:
                raise SnapshotCliError(
                    code="E_PAGE_CONFLICT",
                    message="The same source/cursor key produced different response data.",
                    hint="Start a new snapshot rather than rewriting cached evidence.",
                    exit_code=4,
                )
            conn.rollback()
            return {
                "source_x_id": source_x_id,
                "request_cursor": cursor_key,
                "raw_page_id": existing["id"],
                "created": False,
            }

        _ensure_mutable(conn)
        source = conn.execute(
            "SELECT * FROM source_fetch WHERE source_x_id = ?", (source_x_id,)
        ).fetchone()
        if not source:
            raise SnapshotCliError(
                code="E_SOURCE_NOT_IN_COHORT",
                message=f"Source X ID is not in the frozen cohort: {source_x_id}",
                hint="Do not add sources to an existing snapshot; freeze a new cohort.",
                exit_code=4,
            )
        if source["status"] in TERMINAL_SOURCE_STATUSES:
            raise SnapshotCliError(
                code="E_SOURCE_TERMINAL",
                message=f"Source @{source['source_handle']} is already {source['status']}.",
                hint="Create a new snapshot to refresh a terminal source.",
                exit_code=4,
            )
        if source["next_cursor"] != cursor_key:
            raise SnapshotCliError(
                code="E_CURSOR_OUT_OF_ORDER",
                message="Page cursor does not match the source resume cursor.",
                hint=f"Resume with cursor {source['next_cursor']!r}.",
                exit_code=4,
            )

        cur = conn.execute(
            """INSERT INTO raw_page
               (source_x_id, request_cursor, next_cursor, item_count,
                retrieved_at, response_json, response_sha256)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                source_x_id,
                cursor_key,
                next_cursor or None,
                len(followers),
                retrieved_at,
                raw_json,
                response_sha256,
            ),
        )
        raw_page_id = int(cur.lastrowid)
        normalized = 0
        duplicates = 0
        skipped = 0
        for member in followers:
            if not isinstance(member, dict):
                skipped += 1
                continue
            target_x_id, handle = _member_fields(member)
            if not target_x_id or not handle:
                skipped += 1
                continue
            followers_value = member.get("followers")
            if followers_value is None:
                followers_value = member.get("followers_count")
            conn.execute(
                """INSERT INTO account
                   (x_id, handle, display_name, bio, followers_count,
                    first_observed_at, last_observed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(x_id) DO UPDATE SET
                       handle = excluded.handle,
                       display_name = COALESCE(excluded.display_name, account.display_name),
                       bio = COALESCE(excluded.bio, account.bio),
                       followers_count = COALESCE(excluded.followers_count,
                                                  account.followers_count),
                       last_observed_at = excluded.last_observed_at""",
                (
                    target_x_id,
                    handle,
                    member.get("name"),
                    member.get("description"),
                    _int_or_none(followers_value),
                    retrieved_at,
                    retrieved_at,
                ),
            )
            edge_cur = conn.execute(
                """INSERT OR IGNORE INTO edge
                   (source_x_id, target_x_id, raw_page_id, observed_at)
                   VALUES (?, ?, ?, ?)""",
                (source_x_id, target_x_id, raw_page_id, retrieved_at),
            )
            if edge_cur.rowcount:
                normalized += 1
            else:
                duplicates += 1

        source_status = "in_progress" if has_next else "complete"
        fetched_count = conn.execute(
            "SELECT COUNT(*) FROM edge WHERE source_x_id = ?", (source_x_id,)
        ).fetchone()[0]
        conn.execute(
            """UPDATE source_fetch
               SET advertised_following_count = COALESCE(?, advertised_following_count),
                   next_cursor = ?, fetched_count = ?,
                   raw_page_count = raw_page_count + 1,
                   status = ?, attempts = attempts + 1,
                   last_error_code = NULL, last_error_message = NULL,
                   updated_at = ?
               WHERE source_x_id = ?""",
            (
                advertised_following_count,
                next_cursor if has_next else "",
                fetched_count,
                source_status,
                retrieved_at,
                source_x_id,
            ),
        )
        conn.execute(
            """UPDATE snapshot_run SET status = 'collecting'
               WHERE status = 'initialized'"""
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {
        "source_x_id": source_x_id,
        "request_cursor": cursor_key,
        "next_cursor": next_cursor if has_next else None,
        "raw_page_id": raw_page_id,
        "items": len(followers),
        "edges_created": normalized,
        "duplicates": duplicates,
        "skipped": skipped,
        "source_status": source_status,
        "created": True,
    }


def mark_source(
    conn: sqlite3.Connection,
    *,
    source_x_id: str,
    status: str,
    error_code: str | None = None,
    error_message: str | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Record an explicit non-success terminal state for one source."""
    if status not in TERMINAL_SOURCE_STATUSES - {"complete"}:
        raise ValueError(f"unsupported terminal source status: {status}")
    observed_at = observed_at or _now()
    _ensure_mutable(conn)
    source = conn.execute(
        "SELECT * FROM source_fetch WHERE source_x_id = ?", (source_x_id,)
    ).fetchone()
    if not source:
        raise SnapshotCliError(
            code="E_SOURCE_NOT_IN_COHORT",
            message=f"Source X ID is not in the frozen cohort: {source_x_id}",
            hint="Do not add sources to an existing snapshot.",
            exit_code=4,
        )
    if source["status"] in TERMINAL_SOURCE_STATUSES:
        raise SnapshotCliError(
            code="E_SOURCE_TERMINAL",
            message=f"Source @{source['source_handle']} is already {source['status']}.",
            hint="Create a new snapshot to revise terminal source evidence.",
            exit_code=4,
        )
    conn.execute(
        """UPDATE source_fetch
           SET status = ?, attempts = attempts + 1,
               last_error_code = ?, last_error_message = ?, updated_at = ?
           WHERE source_x_id = ?""",
        (status, error_code, error_message, observed_at, source_x_id),
    )
    conn.execute(
        "UPDATE snapshot_run SET status = 'collecting' WHERE status = 'initialized'"
    )
    conn.commit()
    return {"source_x_id": source_x_id, "status": status}


def finalize_snapshot(
    conn: sqlite3.Connection,
    *,
    reported_cost_usd: float | None = None,
    estimated_cost_usd: float | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    """Make a fully terminal snapshot immutable."""
    _ensure_mutable(conn)
    unfinished = conn.execute(
        """SELECT status, COUNT(*) AS n FROM source_fetch
           WHERE status NOT IN ('complete', 'protected', 'missing', 'unavailable', 'failed')
           GROUP BY status ORDER BY status"""
    ).fetchall()
    if unfinished:
        counts = ", ".join(f"{row['status']}={row['n']}" for row in unfinished)
        raise SnapshotCliError(
            code="E_SNAPSHOT_INCOMPLETE",
            message=f"Snapshot still has unfinished sources: {counts}.",
            hint="Resume the stored cursor or mark each inaccessible source explicitly.",
            exit_code=4,
        )
    conn.execute(
        """UPDATE snapshot_run
           SET status = 'complete', completed_at = ?,
               reported_cost_usd = ?, estimated_cost_usd = ?""",
        (completed_at or _now(), reported_cost_usd, estimated_cost_usd),
    )
    conn.commit()
    return snapshot_summary(conn)


def snapshot_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    run = _snapshot_run(conn)
    status_counts = {
        row["status"]: row["n"]
        for row in conn.execute(
            "SELECT status, COUNT(*) AS n FROM source_fetch GROUP BY status"
        ).fetchall()
    }
    counts = {
        "sources": conn.execute("SELECT COUNT(*) FROM source_fetch").fetchone()[0],
        "raw_pages": conn.execute("SELECT COUNT(*) FROM raw_page").fetchone()[0],
        "accounts": conn.execute("SELECT COUNT(*) FROM account").fetchone()[0],
        "edges": conn.execute("SELECT COUNT(*) FROM edge").fetchone()[0],
    }
    return {
        "snapshot_id": run["snapshot_id"],
        "cohort_id": run["cohort_id"],
        "cohort_sha256": run["cohort_sha256"],
        "schema_version": run["schema_version"],
        "provider": run["provider"],
        "endpoint": run["endpoint"],
        "status": run["status"],
        "created_at": run["created_at"],
        "completed_at": run["completed_at"],
        "counts": counts,
        "source_statuses": {
            status: status_counts.get(status, 0) for status in sorted(SOURCE_STATUSES)
        },
        "reported_cost_usd": run["reported_cost_usd"],
        "estimated_cost_usd": run["estimated_cost_usd"],
    }


def validate_snapshot(conn: sqlite3.Connection) -> dict[str, Any]:
    """Run local integrity and reconciliation checks without changing state."""
    run = _snapshot_run(conn)
    failures: list[str] = []
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        failures.append(f"sqlite_integrity:{integrity}")
    foreign_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_keys:
        failures.append(f"foreign_key_violations:{len(foreign_keys)}")
    source_count = conn.execute("SELECT COUNT(*) FROM source_fetch").fetchone()[0]
    if source_count != run["source_count"]:
        failures.append(
            f"source_count:expected={run['source_count']},actual={source_count}"
        )
    for row in conn.execute(
        "SELECT id, response_json, response_sha256 FROM raw_page ORDER BY id"
    ):
        actual = _sha256_bytes(row["response_json"].encode())
        if actual != row["response_sha256"]:
            failures.append(f"raw_page_checksum:{row['id']}")
    bad_page_counts = conn.execute(
        """SELECT COUNT(*) FROM source_fetch sf
           WHERE sf.raw_page_count != (
               SELECT COUNT(*) FROM raw_page rp WHERE rp.source_x_id = sf.source_x_id
           )"""
    ).fetchone()[0]
    if bad_page_counts:
        failures.append(f"source_page_count_mismatch:{bad_page_counts}")
    bad_edge_counts = conn.execute(
        """SELECT COUNT(*) FROM source_fetch sf
           WHERE sf.fetched_count != (
               SELECT COUNT(*) FROM edge e WHERE e.source_x_id = sf.source_x_id
           )"""
    ).fetchone()[0]
    if bad_edge_counts:
        failures.append(f"source_edge_count_mismatch:{bad_edge_counts}")
    bad_cursors = conn.execute(
        """SELECT COUNT(*) FROM source_fetch
           WHERE (status = 'in_progress' AND next_cursor = '')
              OR (status = 'complete' AND next_cursor != '')"""
    ).fetchone()[0]
    if bad_cursors:
        failures.append(f"source_cursor_state:{bad_cursors}")
    if run["status"] == "complete":
        unfinished = conn.execute(
            """SELECT COUNT(*) FROM source_fetch
               WHERE status NOT IN ('complete', 'protected', 'missing',
                                    'unavailable', 'failed')"""
        ).fetchone()[0]
        if unfinished:
            failures.append(f"complete_snapshot_unfinished_sources:{unfinished}")
    return {
        **snapshot_summary(conn),
        "valid": not failures,
        "validation_failures": failures,
    }


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
        "schema_version": RESULT_SCHEMA_VERSION,
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
        error = payload["error"] or {}
        print(f"error: {error.get('code')}: {error.get('message')}")
        return
    data = payload["data"] or {}
    counts = data.get("counts") or {}
    print(
        f"{payload['command']}: status={data.get('status', 'ok')} "
        f"sources={data.get('source_count', counts.get('sources', 0))} "
        f"pages={counts.get('raw_pages', 0)} edges={counts.get('edges', 0)}"
    )


def _common_output_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--no-input", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit JSON (default).")
    parser.add_argument("--plain", action="store_true", help="Emit compact text.")


def main(argv: list[str] | None = None) -> int:
    started = time.monotonic()
    request_id = str(uuid.uuid4())
    command = "following-snapshot"
    parser = JsonArgumentParser(prog="fli following-snapshot")
    sub = parser.add_subparsers(dest="action", required=True)

    freeze_p = sub.add_parser("freeze-cohort", help="Freeze active Registry X sources.")
    freeze_p.add_argument("--db", type=Path, default=DEFAULT_PRODUCT_DB)
    freeze_p.add_argument("--cohort-id", required=True)
    freeze_p.add_argument("--output", type=Path, required=True)
    _common_output_arguments(freeze_p)

    init_p = sub.add_parser("init", help="Initialize one local snapshot database.")
    init_p.add_argument("--snapshot-id", required=True)
    init_p.add_argument("--cohort", type=Path, required=True)
    init_p.add_argument("--snapshot-db", type=Path)
    _common_output_arguments(init_p)

    status_p = sub.add_parser("status", help="Inspect snapshot progress.")
    status_p.add_argument("--snapshot-db", type=Path, required=True)
    _common_output_arguments(status_p)

    validate_p = sub.add_parser("validate", help="Validate snapshot integrity.")
    validate_p.add_argument("--snapshot-db", type=Path, required=True)
    _common_output_arguments(validate_p)

    try:
        args = parser.parse_args(argv)
        command = f"following-snapshot {args.action}"
        if args.action == "freeze-cohort":
            data = freeze_cohort(
                product_db=args.db,
                output_path=args.output,
                cohort_id=args.cohort_id,
            )
            data = {key: value for key, value in data.items() if key != "sources"}
        elif args.action == "init":
            snapshot_db = args.snapshot_db or (
                DEFAULT_SNAPSHOT_ROOT / args.snapshot_id / "snapshot.db"
            )
            data = initialize_snapshot(
                snapshot_id=args.snapshot_id,
                cohort_path=args.cohort,
                snapshot_db=snapshot_db,
            )
        elif args.action in {"status", "validate"}:
            if not args.snapshot_db.exists():
                raise SnapshotCliError(
                    code="E_NOT_FOUND",
                    message=f"Snapshot database does not exist: {args.snapshot_db}",
                    hint="Initialize it with `fli following-snapshot init`.",
                    exit_code=3,
                )
            conn = connect_snapshot(args.snapshot_db)
            try:
                data = (
                    snapshot_summary(conn)
                    if args.action == "status"
                    else validate_snapshot(conn)
                )
            finally:
                conn.close()
            data["database"] = str(args.snapshot_db)
            if args.action == "validate" and not data["valid"]:
                raise SnapshotCliError(
                    code="E_VALIDATION",
                    message="Snapshot validation failed.",
                    hint="Inspect data.validation_failures before collection resumes.",
                    exit_code=5,
                )
        else:
            raise AssertionError("unreachable")
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
    except (SnapshotCliError, sqlite3.Error) as exc:
        if isinstance(exc, sqlite3.Error):
            exc = SnapshotCliError(
                code="E_SQLITE",
                message=str(exc),
                hint="Check that the snapshot path is a valid writable SQLite file.",
                exit_code=3,
            )
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
        _print_result(payload, plain="--plain" in (argv or []))
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
