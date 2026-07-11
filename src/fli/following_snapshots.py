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
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
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
MINIMUM_REQUEST_CREDITS = 15

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
    try:
        return int(value)
    except (TypeError, ValueError):
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
        return 60
    if returned >= 200:
        return returned
    if returned >= 100:
        return returned * 2
    return max(60, returned * 3)


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


def record_profile(
    conn: sqlite3.Connection,
    *,
    source_x_id: str,
    profile: dict[str, Any],
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    """Cache one source profile before following pages are requested."""
    retrieved_at = retrieved_at or _now()
    raw_json = _canonical_json(profile)
    profile_sha256 = _sha256_bytes(raw_json.encode())
    observed_x_id = str(profile.get("id") or profile.get("id_str") or "").strip()
    if observed_x_id and observed_x_id != source_x_id:
        raise SnapshotCliError(
            code="E_SOURCE_ID_MISMATCH",
            message=(
                f"Provider handle resolved to X ID {observed_x_id}, "
                f"not frozen source ID {source_x_id}."
            ),
            hint="Do not collect this handle until Registry identity is corrected.",
            exit_code=4,
        )
    protected = sources.is_protected_profile(profile)
    following_count = _profile_following_count(profile)
    conn.execute("BEGIN IMMEDIATE")
    try:
        existing = conn.execute(
            "SELECT profile_sha256 FROM raw_profile WHERE source_x_id = ?",
            (source_x_id,),
        ).fetchone()
        if existing:
            if existing["profile_sha256"] != profile_sha256:
                raise SnapshotCliError(
                    code="E_PROFILE_CONFLICT",
                    message="The same snapshot source produced different profile data.",
                    hint="Create a new snapshot rather than rewriting cached evidence.",
                    exit_code=4,
                )
            conn.rollback()
            return {
                "source_x_id": source_x_id,
                "protected": protected,
                "advertised_following_count": following_count,
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
                hint="Do not add sources to an existing snapshot.",
                exit_code=4,
            )
        if source["status"] in TERMINAL_SOURCE_STATUSES:
            raise SnapshotCliError(
                code="E_SOURCE_TERMINAL",
                message=f"Source @{source['source_handle']} is already {source['status']}.",
                hint="Create a new snapshot to refresh a terminal source.",
                exit_code=4,
            )
        conn.execute(
            """INSERT INTO raw_profile
               (source_x_id, retrieved_at, profile_json, profile_sha256,
                protected, advertised_following_count)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                source_x_id,
                retrieved_at,
                raw_json,
                profile_sha256,
                int(protected),
                following_count,
            ),
        )
        conn.execute(
            """UPDATE source_fetch
               SET advertised_following_count = COALESCE(?, advertised_following_count),
                   updated_at = ?
               WHERE source_x_id = ?""",
            (following_count, retrieved_at, source_x_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {
        "source_x_id": source_x_id,
        "protected": protected,
        "advertised_following_count": following_count,
        "created": True,
    }


def _cached_profile(
    conn: sqlite3.Connection, source_x_id: str
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT profile_json FROM raw_profile WHERE source_x_id = ?", (source_x_id,)
    ).fetchone()
    return json.loads(row["profile_json"]) if row else None


def record_attempt_error(
    conn: sqlite3.Connection,
    *,
    source_x_id: str,
    error_code: str,
    error_message: str,
    observed_at: str | None = None,
) -> None:
    """Persist a retryable failure without discarding the resume cursor."""
    observed_at = observed_at or _now()
    _ensure_mutable(conn)
    updated = conn.execute(
        """UPDATE source_fetch
           SET attempts = attempts + 1, last_error_code = ?,
               last_error_message = ?, updated_at = ?
           WHERE source_x_id = ? AND status IN ('pending', 'in_progress')""",
        (error_code, error_message, observed_at, source_x_id),
    ).rowcount
    if not updated:
        raise SnapshotCliError(
            code="E_SOURCE_NOT_RESUMABLE",
            message=f"Source X ID is not resumable: {source_x_id}",
            hint="Inspect the source status before retrying.",
            exit_code=4,
        )
    conn.commit()


def complete_zero_following_source(
    conn: sqlite3.Connection,
    *,
    source_x_id: str,
    observed_at: str | None = None,
) -> None:
    """Complete a source whose cached provider profile advertises zero follows."""
    observed_at = observed_at or _now()
    _ensure_mutable(conn)
    profile = conn.execute(
        """SELECT advertised_following_count FROM raw_profile
           WHERE source_x_id = ?""",
        (source_x_id,),
    ).fetchone()
    if not profile or profile["advertised_following_count"] != 0:
        raise SnapshotCliError(
            code="E_ZERO_FOLLOWING_EVIDENCE",
            message="Source does not have cached zero-following profile evidence.",
            hint="Fetch and cache the source profile before completing it as empty.",
            exit_code=4,
        )
    updated = conn.execute(
        """UPDATE source_fetch
           SET status = 'complete', next_cursor = '', fetched_count = 0,
               last_error_code = NULL, last_error_message = NULL, updated_at = ?
           WHERE source_x_id = ? AND status IN ('pending', 'in_progress')""",
        (observed_at, source_x_id),
    ).rowcount
    if not updated:
        raise SnapshotCliError(
            code="E_SOURCE_NOT_RESUMABLE",
            message=f"Source X ID is not resumable: {source_x_id}",
            hint="Inspect the source status before completing it.",
            exit_code=4,
        )
    conn.execute(
        "UPDATE snapshot_run SET status = 'collecting' WHERE status = 'initialized'"
    )
    conn.commit()


def _snapshot_cost(conn: sqlite3.Connection) -> dict[str, int | float]:
    profile_requests = conn.execute("SELECT COUNT(*) FROM raw_profile").fetchone()[0]
    unpersisted_requests = conn.execute(
        """SELECT COALESCE(SUM(sf.attempts), 0)
           FROM source_fetch sf
           WHERE NOT EXISTS (
               SELECT 1 FROM raw_profile rp
               WHERE rp.source_x_id = sf.source_x_id
           )"""
    ).fetchone()[0]
    page_rows = conn.execute("SELECT item_count FROM raw_page").fetchall()
    following_credits = sum(_following_page_credits(row["item_count"]) for row in page_rows)
    credits = (
        profile_requests * PROFILE_CREDITS
        + unpersisted_requests * MINIMUM_REQUEST_CREDITS
        + following_credits
    )
    return {
        "profile_requests": profile_requests,
        "unpersisted_error_requests": unpersisted_requests,
        "following_page_requests": len(page_rows),
        "estimated_provider_credits": credits,
        "estimated_provider_cost_usd": round(credits / 100_000, 6),
    }


def profile_cost_projection(conn: sqlite3.Connection) -> dict[str, int | float | None]:
    """Project complete collection cost for sources with cached profile counts."""
    rows = conn.execute(
        """SELECT advertised_following_count
           FROM raw_profile
           WHERE advertised_following_count IS NOT NULL"""
    ).fetchall()
    followed_total = sum(row["advertised_following_count"] for row in rows)
    following_credits = 0
    for row in rows:
        count = row["advertised_following_count"]
        full_pages, remainder = divmod(count, 200)
        following_credits += full_pages * 200
        if remainder:
            following_credits += _following_page_credits(remainder)
    projected_credits = len(rows) * PROFILE_CREDITS + following_credits
    return {
        "sources_with_following_count": len(rows),
        "advertised_following_total": followed_total,
        "average_advertised_following_count": (
            round(followed_total / len(rows), 2) if rows else None
        ),
        "projected_provider_credits_for_profiled_sources": projected_credits,
        "projected_cost_usd_for_profiled_sources": round(
            projected_credits / 100_000, 6
        ),
    }


def _provider_error_status(exc: sources.SourceCliError) -> str | None:
    message = exc.message.lower()
    if "protected" in message or "private" in message:
        return "protected"
    if "not found" in message or "does not exist" in message:
        return "missing"
    if any(word in message for word in ("suspended", "deactivated", "unavailable")):
        return "unavailable"
    return None


def _as_snapshot_error(exc: sources.SourceCliError) -> SnapshotCliError:
    return SnapshotCliError(
        code=exc.code,
        message=exc.message,
        hint=exc.hint,
        exit_code=exc.exit_code,
        retryable=exc.retryable,
    )


def _select_collection_sources(
    conn: sqlite3.Connection,
    *,
    handles: list[str] | None,
    limit: int | None,
    collect_all: bool,
) -> list[sqlite3.Row]:
    selected_modes = sum((bool(handles), limit is not None, collect_all))
    if selected_modes != 1:
        raise SnapshotCliError(
            code="E_SCOPE_REQUIRED",
            message="Choose exactly one collection scope: --handle, --limit, or --all.",
            hint="Use --handle for calibration and --all only for an approved full crawl.",
            exit_code=2,
        )
    if handles:
        normalized = list(dict.fromkeys(_normalize_handle(handle) for handle in handles))
        if None in normalized:
            raise SnapshotCliError(
                code="E_HANDLE_INVALID",
                message="Every --handle value must contain a non-empty X handle.",
                hint="Pass handles with or without the leading @.",
                exit_code=2,
            )
        placeholders = ",".join("?" for _ in normalized)
        rows = conn.execute(
            f"""SELECT * FROM source_fetch
                WHERE source_handle IN ({placeholders})
                ORDER BY source_handle""",
            normalized,
        ).fetchall()
        found = {row["source_handle"] for row in rows}
        missing = sorted(set(normalized) - found)
        if missing:
            raise SnapshotCliError(
                code="E_SOURCE_NOT_IN_COHORT",
                message=f"Handles are not in the frozen cohort: {', '.join(missing)}",
                hint="Inspect the cohort before starting paid collection.",
                exit_code=2,
            )
        return rows
    if limit is not None and limit < 1:
        raise SnapshotCliError(
            code="E_LIMIT_INVALID",
            message="--limit must be at least 1.",
            hint="Use a positive bounded source count.",
            exit_code=2,
        )
    sql = """SELECT * FROM source_fetch
             WHERE status IN ('pending', 'in_progress')
             ORDER BY CASE status WHEN 'in_progress' THEN 0 ELSE 1 END,
                      source_handle"""
    params: tuple[int, ...] = ()
    if limit is not None:
        sql += " LIMIT ?"
        params = (limit,)
    return conn.execute(sql, params).fetchall()


@contextlib.contextmanager
def collection_lock(snapshot_db: Path):
    """Prevent two local collectors from paying for the same cursor."""
    lock_path = snapshot_db.with_suffix(snapshot_db.suffix + ".collect.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w") as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SnapshotCliError(
                code="E_COLLECTION_LOCKED",
                message=f"Another collector holds the snapshot lock: {lock_path}",
                hint="Wait for that process or inspect it before retrying.",
                exit_code=4,
                retryable=True,
            ) from exc
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class RequestStartLimiter:
    """Space request starts so parallel workers stay under provider QPS."""

    def __init__(self, requests_per_second: float) -> None:
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        self.interval = 1.0 / requests_per_second
        self.next_start = 0.0
        self.lock = threading.Lock()

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            start_at = max(now, self.next_start)
            self.next_start = start_at + self.interval
        delay = start_at - now
        if delay > 0:
            time.sleep(delay)


def _fetch_profile_limited(
    client: sources.TwitterApiIoClient | Any,
    *,
    handle: str,
    limiter: RequestStartLimiter,
) -> dict[str, Any]:
    limiter.wait()
    return client.fetch_user(username=handle)


def _collect_profiles_parallel(
    conn: sqlite3.Connection,
    *,
    client: sources.TwitterApiIoClient | Any,
    selected: list[sqlite3.Row],
    workers: int,
    requests_per_second: float,
    progress: str,
) -> dict[str, Any]:
    outcomes = {
        "complete": 0,
        "paused": 0,
        "protected": 0,
        "missing": 0,
        "unavailable": 0,
        "failed": 0,
        "already_terminal": 0,
        "profiled": 0,
        "retryable_error": 0,
    }
    failures: list[dict[str, str]] = []
    profiles_fetched = 0
    profiles_reused = 0
    pending: list[sqlite3.Row] = []

    for source in selected:
        if source["status"] in TERMINAL_SOURCE_STATUSES:
            outcomes["already_terminal"] += 1
            continue
        profile = _cached_profile(conn, source["source_x_id"])
        if profile is None:
            pending.append(source)
            continue
        profiles_reused += 1
        if sources.is_protected_profile(profile):
            mark_source(
                conn,
                source_x_id=source["source_x_id"],
                status="protected",
                error_code="E_ACCOUNT_PROTECTED",
                error_message="The cached provider profile marks this account protected.",
            )
            outcomes["protected"] += 1
        elif _profile_following_count(profile) == 0:
            complete_zero_following_source(
                conn, source_x_id=source["source_x_id"]
            )
            outcomes["complete"] += 1
        else:
            outcomes["profiled"] += 1

    limiter = RequestStartLimiter(requests_per_second)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _fetch_profile_limited,
                client,
                handle=source["source_handle"],
                limiter=limiter,
            ): source
            for source in pending
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            source = futures[future]
            source_x_id = source["source_x_id"]
            handle = source["source_handle"]
            try:
                profile = future.result()
            except sources.SourceCliError as exc:
                terminal_status = _provider_error_status(exc)
                if terminal_status:
                    mark_source(
                        conn,
                        source_x_id=source_x_id,
                        status=terminal_status,
                        error_code=exc.code,
                        error_message=exc.message,
                    )
                    outcomes[terminal_status] += 1
                    failures.append(
                        {"handle": handle, "status": terminal_status, "code": exc.code}
                    )
                else:
                    record_attempt_error(
                        conn,
                        source_x_id=source_x_id,
                        error_code=exc.code,
                        error_message=exc.message,
                    )
                    outcomes["retryable_error"] += 1
                    failures.append(
                        {"handle": handle, "status": "retryable", "code": exc.code}
                    )
                continue
            try:
                record_profile(conn, source_x_id=source_x_id, profile=profile)
            except SnapshotCliError as exc:
                if exc.code != "E_SOURCE_ID_MISMATCH":
                    raise
                mark_source(
                    conn,
                    source_x_id=source_x_id,
                    status="failed",
                    error_code=exc.code,
                    error_message=exc.message,
                )
                outcomes["failed"] += 1
                failures.append(
                    {"handle": handle, "status": "failed", "code": exc.code}
                )
                continue
            profiles_fetched += 1
            if sources.is_protected_profile(profile):
                mark_source(
                    conn,
                    source_x_id=source_x_id,
                    status="protected",
                    error_code="E_ACCOUNT_PROTECTED",
                    error_message="The provider profile marks this X account protected.",
                )
                outcomes["protected"] += 1
            elif _profile_following_count(profile) == 0:
                complete_zero_following_source(conn, source_x_id=source_x_id)
                outcomes["complete"] += 1
            else:
                outcomes["profiled"] += 1
            if progress == "plain" and (
                completed == len(pending) or completed % 100 == 0
            ):
                print(
                    f"profile scan {completed}/{len(pending)} fetched",
                    file=sys.stderr,
                    flush=True,
                )

    cumulative_cost = _snapshot_cost(conn)
    conn.execute(
        "UPDATE snapshot_run SET estimated_cost_usd = ?",
        (cumulative_cost["estimated_provider_cost_usd"],),
    )
    conn.commit()
    preview = [row["source_handle"] for row in selected[:20]]
    return {
        "dry_run": False,
        "profiles_only": True,
        "workers": workers,
        "requests_per_second": requests_per_second,
        "selected_sources": len(selected),
        "selected_handle_preview": preview,
        "selected_handle_preview_truncated": len(selected) > len(preview),
        "profiles_fetched": profiles_fetched,
        "profiles_reused": profiles_reused,
        "pages_fetched": 0,
        "outcomes": outcomes,
        "failures": failures,
        "invocation_estimated_provider_credits": profiles_fetched * PROFILE_CREDITS,
        "invocation_estimated_provider_cost_usd": round(
            profiles_fetched * PROFILE_CREDITS / 100_000, 6
        ),
        "cumulative_cost": cumulative_cost,
        "profile_cost_projection": profile_cost_projection(conn),
        "snapshot": snapshot_summary(conn),
    }


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


def collect_snapshot(
    conn: sqlite3.Connection,
    *,
    client: sources.TwitterApiIoClient | Any | None = None,
    handles: list[str] | None = None,
    limit: int | None = None,
    collect_all: bool = False,
    page_size: int = 200,
    max_pages_per_source: int | None = None,
    profiles_only: bool = False,
    workers: int = 1,
    requests_per_second: float = 9.0,
    key_file: Path = sources.DEFAULT_TWITTERAPI_IO_KEY_FILE,
    timeout_seconds: float = 30.0,
    page_sleep_seconds: float = 0.0,
    dry_run: bool = False,
    progress: str = "off",
) -> dict[str, Any]:
    """Collect a bounded, resumable set of frozen sources."""
    _ensure_mutable(conn)
    if not 20 <= page_size <= 200:
        raise SnapshotCliError(
            code="E_PAGE_SIZE_INVALID",
            message="--page-size must be between 20 and 200.",
            hint="Use 200 for the lowest documented unit price.",
            exit_code=2,
        )
    if max_pages_per_source is not None and max_pages_per_source < 1:
        raise SnapshotCliError(
            code="E_MAX_PAGES_INVALID",
            message="--max-pages-per-source must be at least 1.",
            hint="Omit the flag to finish each selected source.",
            exit_code=2,
        )
    if workers < 1:
        raise SnapshotCliError(
            code="E_WORKERS_INVALID",
            message="--workers must be at least 1.",
            hint="Use 10 workers with --profiles-only on the Builder plan.",
            exit_code=2,
        )
    if workers > 1 and not profiles_only:
        raise SnapshotCliError(
            code="E_WORKERS_PROFILE_ONLY",
            message="Parallel workers are currently limited to --profiles-only scans.",
            hint="Following-page collection remains sequential and cursor-safe.",
            exit_code=2,
        )
    if requests_per_second <= 0:
        raise SnapshotCliError(
            code="E_QPS_INVALID",
            message="--requests-per-second must be positive.",
            hint="Use 9 for headroom under the Builder plan's documented 10 QPS.",
            exit_code=2,
        )
    selected = _select_collection_sources(
        conn,
        handles=handles,
        limit=limit,
        collect_all=collect_all,
    )
    preview = [row["source_handle"] for row in selected[:20]]
    if dry_run:
        return {
            "dry_run": True,
            "selected_sources": len(selected),
            "selected_handle_preview": preview,
            "selected_handle_preview_truncated": len(selected) > len(preview),
            "page_size": page_size,
            "max_pages_per_source": max_pages_per_source,
            "profiles_only": profiles_only,
            "workers": workers,
            "requests_per_second": requests_per_second,
            "profile_scan_max_cost_usd": round(
                len(selected) * PROFILE_CREDITS / 100_000, 6
            ),
            "snapshot": snapshot_summary(conn),
        }
    if client is None:
        try:
            client = sources.create_twitterapi_io_client(
                key_file=key_file,
                timeout=timeout_seconds,
                page_sleep_seconds=page_sleep_seconds,
            )
        except sources.SourceCliError as exc:
            raise _as_snapshot_error(exc) from exc
    if profiles_only and workers > 1:
        return _collect_profiles_parallel(
            conn,
            client=client,
            selected=selected,
            workers=workers,
            requests_per_second=requests_per_second,
            progress=progress,
        )

    outcomes = {
        "complete": 0,
        "paused": 0,
        "protected": 0,
        "missing": 0,
        "unavailable": 0,
        "failed": 0,
        "already_terminal": 0,
        "profiled": 0,
        "retryable_error": 0,
    }
    failures: list[dict[str, str]] = []
    profiles_fetched = 0
    profiles_reused = 0
    pages_fetched = 0
    invocation_credits = 0

    for ordinal, selected_source in enumerate(selected, start=1):
        source_x_id = selected_source["source_x_id"]
        handle = selected_source["source_handle"]
        if selected_source["status"] in TERMINAL_SOURCE_STATUSES:
            outcomes["already_terminal"] += 1
            continue
        if progress == "plain":
            print(
                f"collecting {ordinal}/{len(selected)} @{handle} "
                f"status={selected_source['status']}",
                file=sys.stderr,
                flush=True,
            )

        profile = _cached_profile(conn, source_x_id)
        if profile is None:
            try:
                profile = client.fetch_user(username=handle)
            except sources.SourceCliError as exc:
                terminal_status = _provider_error_status(exc)
                if terminal_status:
                    mark_source(
                        conn,
                        source_x_id=source_x_id,
                        status=terminal_status,
                        error_code=exc.code,
                        error_message=exc.message,
                    )
                    outcomes[terminal_status] += 1
                    failures.append(
                        {"handle": handle, "status": terminal_status, "code": exc.code}
                    )
                    continue
                record_attempt_error(
                    conn,
                    source_x_id=source_x_id,
                    error_code=exc.code,
                    error_message=exc.message,
                )
                raise _as_snapshot_error(exc) from exc
            try:
                profile_result = record_profile(
                    conn, source_x_id=source_x_id, profile=profile
                )
            except SnapshotCliError as exc:
                if exc.code != "E_SOURCE_ID_MISMATCH":
                    raise
                mark_source(
                    conn,
                    source_x_id=source_x_id,
                    status="failed",
                    error_code=exc.code,
                    error_message=exc.message,
                )
                outcomes["failed"] += 1
                failures.append(
                    {"handle": handle, "status": "failed", "code": exc.code}
                )
                continue
            profiles_fetched += int(profile_result["created"])
            invocation_credits += PROFILE_CREDITS
        else:
            profiles_reused += 1

        if sources.is_protected_profile(profile):
            mark_source(
                conn,
                source_x_id=source_x_id,
                status="protected",
                error_code="E_ACCOUNT_PROTECTED",
                error_message="The provider profile marks this X account as protected.",
            )
            outcomes["protected"] += 1
            failures.append(
                {
                    "handle": handle,
                    "status": "protected",
                    "code": "E_ACCOUNT_PROTECTED",
                }
            )
            continue

        if _profile_following_count(profile) == 0:
            complete_zero_following_source(conn, source_x_id=source_x_id)
            outcomes["complete"] += 1
            continue

        if profiles_only:
            outcomes["profiled"] += 1
            continue

        following_count = _profile_following_count(profile)
        pages_this_source = 0
        while True:
            current = conn.execute(
                "SELECT * FROM source_fetch WHERE source_x_id = ?", (source_x_id,)
            ).fetchone()
            cursor = current["next_cursor"] or None
            try:
                payload = client.fetch_following_page(
                    username=handle,
                    cursor=cursor,
                    page_size=page_size,
                )
            except sources.SourceCliError as exc:
                terminal_status = _provider_error_status(exc)
                if terminal_status:
                    mark_source(
                        conn,
                        source_x_id=source_x_id,
                        status=terminal_status,
                        error_code=exc.code,
                        error_message=exc.message,
                    )
                    outcomes[terminal_status] += 1
                    failures.append(
                        {"handle": handle, "status": terminal_status, "code": exc.code}
                    )
                    break
                record_attempt_error(
                    conn,
                    source_x_id=source_x_id,
                    error_code=exc.code,
                    error_message=exc.message,
                )
                raise _as_snapshot_error(exc) from exc
            page = record_page(
                conn,
                source_x_id=source_x_id,
                request_cursor=cursor,
                payload=payload,
                advertised_following_count=following_count,
            )
            pages_fetched += int(page["created"])
            pages_this_source += int(page["created"])
            if page["created"]:
                invocation_credits += _following_page_credits(page["items"])
            if page.get("source_status") == "complete":
                outcomes["complete"] += 1
                break
            if (
                max_pages_per_source is not None
                and pages_this_source >= max_pages_per_source
            ):
                outcomes["paused"] += 1
                break

    cumulative_cost = _snapshot_cost(conn)
    conn.execute(
        "UPDATE snapshot_run SET estimated_cost_usd = ?",
        (cumulative_cost["estimated_provider_cost_usd"],),
    )
    conn.commit()
    return {
        "dry_run": False,
        "selected_sources": len(selected),
        "selected_handle_preview": preview,
        "selected_handle_preview_truncated": len(selected) > len(preview),
        "profiles_fetched": profiles_fetched,
        "profiles_reused": profiles_reused,
        "pages_fetched": pages_fetched,
        "outcomes": outcomes,
        "failures": failures,
        "invocation_estimated_provider_credits": invocation_credits,
        "invocation_estimated_provider_cost_usd": round(
            invocation_credits / 100_000, 6
        ),
        "cumulative_cost": cumulative_cost,
        "profile_cost_projection": profile_cost_projection(conn),
        "snapshot": snapshot_summary(conn),
    }


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
        "raw_profiles": conn.execute("SELECT COUNT(*) FROM raw_profile").fetchone()[0],
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
        "estimated_cost_usd": _snapshot_cost(conn)["estimated_provider_cost_usd"],
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
    for row in conn.execute(
        "SELECT source_x_id, profile_json, profile_sha256 FROM raw_profile"
    ):
        actual = _sha256_bytes(row["profile_json"].encode())
        if actual != row["profile_sha256"]:
            failures.append(f"raw_profile_checksum:{row['source_x_id']}")
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
    snapshot = data.get("snapshot") or {}
    counts = data.get("counts") or snapshot.get("counts") or {}
    selected = data.get("selected_sources")
    selected_text = f" selected={selected}" if selected is not None else ""
    print(
        f"{payload['command']}: status={data.get('status', 'ok')} "
        f"sources={data.get('source_count', counts.get('sources', 0))}"
        f"{selected_text} pages={counts.get('raw_pages', 0)} "
        f"edges={counts.get('edges', 0)}"
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

    collect_p = sub.add_parser(
        "collect", help="Collect a bounded, resumable set of outgoing follows."
    )
    collect_p.add_argument("--snapshot-db", type=Path, required=True)
    scope = collect_p.add_mutually_exclusive_group(required=True)
    scope.add_argument("--handle", action="append", dest="handles")
    scope.add_argument("--limit", type=int)
    scope.add_argument("--all", action="store_true", dest="collect_all")
    collect_p.add_argument("--page-size", type=int, default=200)
    collect_p.add_argument("--max-pages-per-source", type=int)
    collect_p.add_argument(
        "--profiles-only",
        action="store_true",
        help="Cache source profiles/counts without requesting following pages.",
    )
    collect_p.add_argument("--workers", type=int, default=1)
    collect_p.add_argument("--requests-per-second", type=float, default=9.0)
    collect_p.add_argument(
        "--key-file",
        type=Path,
        default=sources.DEFAULT_TWITTERAPI_IO_KEY_FILE,
        help="Path to the provider API-key file.",
    )
    collect_p.add_argument("--timeout-seconds", type=float, default=30.0)
    collect_p.add_argument("--page-sleep-seconds", type=float, default=0.0)
    collect_p.add_argument("--dry-run", action="store_true")
    collect_p.add_argument("--progress", choices=("off", "plain"), default="off")
    _common_output_arguments(collect_p)

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
        elif args.action == "collect":
            if not args.snapshot_db.exists():
                raise SnapshotCliError(
                    code="E_NOT_FOUND",
                    message=f"Snapshot database does not exist: {args.snapshot_db}",
                    hint="Initialize it with `fli following-snapshot init`.",
                    exit_code=3,
                )
            with collection_lock(args.snapshot_db):
                conn = connect_snapshot(args.snapshot_db)
                try:
                    data = collect_snapshot(
                        conn,
                        handles=args.handles,
                        limit=args.limit,
                        collect_all=args.collect_all,
                        page_size=args.page_size,
                        max_pages_per_source=args.max_pages_per_source,
                        profiles_only=args.profiles_only,
                        workers=args.workers,
                        requests_per_second=args.requests_per_second,
                        key_file=args.key_file,
                        timeout_seconds=args.timeout_seconds,
                        page_sleep_seconds=args.page_sleep_seconds,
                        dry_run=args.dry_run,
                        progress=args.progress,
                    )
                finally:
                    conn.close()
            data["database"] = str(args.snapshot_db)
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
    except KeyboardInterrupt:
        exc = SnapshotCliError(
            code="E_INTERRUPTED",
            message="Collection was interrupted; committed pages remain resumable.",
            hint="Run the same command again to continue from stored cursors.",
            exit_code=5,
            retryable=True,
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
