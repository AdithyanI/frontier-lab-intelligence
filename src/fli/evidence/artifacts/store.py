"""Canonical artifact catalog over first-party links in Feed Events."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

from fli.evidence import events as signal_events
from fli.evidence import feed as signal_feed
from fli.evidence.artifacts import lineage as evidence_lineage
from fli.evidence.artifacts import urls as artifact_urls
SCHEMA_VERSION = "artifact-store-v2"
REVIEWED_SUPPLEMENT_CONTRACT = "artifact-reviewed-supplement-v1"
PRIMARY_AUTHOR_SELECTION_POLICY = "feed-event-primary-author-thread-artifacts-v2"
REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DB = REPO_ROOT / "data" / "derived" / "artifacts" / "artifacts.db"

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS artifact_import_run (
    import_run_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL CHECK (schema_version = '{SCHEMA_VERSION}'),
    canonicalization_contract TEXT NOT NULL,
    source_feed_run_id TEXT NOT NULL,
    source_event_run_id TEXT NOT NULL,
    triage_runs_json TEXT NOT NULL,
    selection_policy TEXT NOT NULL,
    input_fingerprint TEXT NOT NULL,
    expected_candidate_count INTEGER NOT NULL,
    accepted_count INTEGER NOT NULL,
    excluded_count INTEGER NOT NULL,
    failed_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    UNIQUE (canonicalization_contract, input_fingerprint)
);

CREATE TABLE IF NOT EXISTS artifact (
    artifact_id TEXT PRIMARY KEY,
    canonical_url TEXT NOT NULL UNIQUE,
    canonicalization_contract TEXT NOT NULL,
    host TEXT NOT NULL,
    artifact_kind TEXT NOT NULL CHECK (
        artifact_kind IN (
            'paper', 'repository', 'announcement', 'article', 'video', 'other'
        )
    ),
    title TEXT,
    title_fetch_id TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_artifact_host_seen
    ON artifact(host, first_seen_at, artifact_id);
CREATE INDEX IF NOT EXISTS idx_artifact_last_seen
    ON artifact(last_seen_at DESC, artifact_id);

CREATE TABLE IF NOT EXISTS artifact_alias (
    alias_url TEXT PRIMARY KEY,
    artifact_id TEXT NOT NULL REFERENCES artifact(artifact_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    alias_kind TEXT NOT NULL CHECK (
        alias_kind IN (
            'observed', 'expanded', 'canonical', 'redirect',
            'declared_canonical'
        )
    ),
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_artifact_alias_artifact
    ON artifact_alias(artifact_id, alias_kind, alias_url);

CREATE TABLE IF NOT EXISTS artifact_observation (
    observation_id TEXT PRIMARY KEY,
    artifact_id TEXT NOT NULL REFERENCES artifact(artifact_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    source_kind TEXT NOT NULL,
    source_provider TEXT NOT NULL,
    source_external_id TEXT NOT NULL,
    source_snapshot_sha256 TEXT NOT NULL,
    source_url TEXT NOT NULL,
    observed_url TEXT NOT NULL,
    expanded_url TEXT NOT NULL,
    relation TEXT NOT NULL CHECK (relation IN ('links_to', 'self_publishes')),
    source_published_at TEXT NOT NULL,
    first_event_day TEXT NOT NULL,
    best_source_rank INTEGER NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    UNIQUE (
        source_kind, source_provider, source_external_id,
        source_snapshot_sha256, observed_url, relation
    )
);
CREATE INDEX IF NOT EXISTS idx_artifact_observation_artifact
    ON artifact_observation(
        artifact_id, source_published_at, source_provider, source_external_id
    );
CREATE INDEX IF NOT EXISTS idx_artifact_observation_source
    ON artifact_observation(
        source_kind, source_provider, source_external_id,
        source_snapshot_sha256
    );
CREATE INDEX IF NOT EXISTS idx_artifact_observation_rank
    ON artifact_observation(best_source_rank, artifact_id);
CREATE INDEX IF NOT EXISTS idx_artifact_observation_published
    ON artifact_observation(source_published_at DESC, best_source_rank, artifact_id);
CREATE INDEX IF NOT EXISTS idx_artifact_observation_day
    ON artifact_observation(
        substr(source_published_at, 1, 10), source_published_at DESC, artifact_id
    );

CREATE TABLE IF NOT EXISTS artifact_disclosure (
    disclosure_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL REFERENCES artifact_observation(observation_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    source_provider TEXT NOT NULL,
    disclosure_external_id TEXT NOT NULL,
    disclosure_snapshot_sha256 TEXT NOT NULL,
    disclosure_url TEXT NOT NULL,
    disclosure_published_at TEXT NOT NULL,
    first_event_day TEXT NOT NULL,
    last_event_day TEXT NOT NULL,
    UNIQUE (
        observation_id, source_provider, disclosure_external_id,
        disclosure_snapshot_sha256
    )
);
CREATE INDEX IF NOT EXISTS idx_artifact_disclosure_source
    ON artifact_disclosure(
        source_provider, disclosure_external_id, disclosure_snapshot_sha256
    );

CREATE TABLE IF NOT EXISTS artifact_import_candidate (
    candidate_id TEXT PRIMARY KEY,
    import_run_id TEXT NOT NULL REFERENCES artifact_import_run(import_run_id)
        ON DELETE CASCADE,
    event_day TEXT NOT NULL,
    event_id TEXT NOT NULL,
    source_rank INTEGER NOT NULL,
    day_candidate_count INTEGER NOT NULL,
    source_kind TEXT NOT NULL,
    source_provider TEXT NOT NULL,
    source_external_id TEXT NOT NULL,
    source_snapshot_sha256 TEXT NOT NULL,
    source_url TEXT NOT NULL,
    disclosure_external_id TEXT NOT NULL,
    disclosure_snapshot_sha256 TEXT NOT NULL,
    disclosure_url TEXT NOT NULL,
    disclosure_published_at TEXT NOT NULL,
    observed_url TEXT NOT NULL,
    expanded_url TEXT NOT NULL,
    candidate_source TEXT NOT NULL,
    title_hint TEXT,
    relation TEXT NOT NULL CHECK (relation IN ('links_to', 'self_publishes')),
    decision TEXT NOT NULL CHECK (decision IN ('accepted', 'excluded', 'failed')),
    reason_code TEXT NOT NULL,
    artifact_id TEXT REFERENCES artifact(artifact_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_artifact_candidate_decision
    ON artifact_import_candidate(import_run_id, decision, reason_code);
CREATE INDEX IF NOT EXISTS idx_artifact_candidate_source
    ON artifact_import_candidate(
        source_provider, source_external_id, source_snapshot_sha256
    );

CREATE TABLE IF NOT EXISTS artifact_event_supplement (
    supplement_id TEXT PRIMARY KEY,
    contract TEXT NOT NULL CHECK (
        contract = '{REVIEWED_SUPPLEMENT_CONTRACT}'
    ),
    manifest_sha256 TEXT NOT NULL,
    artifact_id TEXT NOT NULL REFERENCES artifact(artifact_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    event_id TEXT NOT NULL,
    event_day TEXT NOT NULL,
    source_rank INTEGER NOT NULL,
    day_candidate_count INTEGER NOT NULL,
    source_triage_run_id TEXT NOT NULL,
    source_input_sha256 TEXT NOT NULL,
    source_semantic_snapshot_sha256 TEXT NOT NULL,
    evidence_role TEXT NOT NULL CHECK (
        evidence_role = 'official_primary_source'
    ),
    source_published_at TEXT NOT NULL,
    rationale TEXT NOT NULL,
    reviewed_by TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (contract, source_triage_run_id, event_id, artifact_id)
);
CREATE INDEX IF NOT EXISTS idx_artifact_supplement_event
    ON artifact_event_supplement(event_id, artifact_id);
CREATE INDEX IF NOT EXISTS idx_artifact_supplement_artifact
    ON artifact_event_supplement(artifact_id, event_day, source_rank);

CREATE TABLE IF NOT EXISTS artifact_fetch_run (
    fetch_run_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL CHECK (schema_version = '{SCHEMA_VERSION}'),
    fetch_policy TEXT NOT NULL,
    selection_policy TEXT NOT NULL,
    input_fingerprint TEXT NOT NULL,
    expected_count INTEGER NOT NULL,
    success_count INTEGER NOT NULL,
    failed_retryable_count INTEGER NOT NULL,
    failed_terminal_count INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('in_progress', 'complete')),
    UNIQUE (fetch_policy, input_fingerprint)
);

CREATE TABLE IF NOT EXISTS artifact_fetch_run_item (
    fetch_run_id TEXT NOT NULL REFERENCES artifact_fetch_run(fetch_run_id)
        ON DELETE CASCADE,
    artifact_id TEXT NOT NULL REFERENCES artifact(artifact_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    selection_rank INTEGER NOT NULL,
    stratum TEXT NOT NULL,
    selected_url TEXT NOT NULL,
    source_day TEXT NOT NULL,
    source_rank INTEGER NOT NULL,
    normalized_rank REAL NOT NULL,
    source_event_id TEXT NOT NULL,
    PRIMARY KEY (fetch_run_id, artifact_id),
    UNIQUE (fetch_run_id, selection_rank)
);
CREATE INDEX IF NOT EXISTS idx_artifact_fetch_run_item_rank
    ON artifact_fetch_run_item(fetch_run_id, selection_rank, artifact_id);

CREATE TABLE IF NOT EXISTS artifact_fetch (
    fetch_id TEXT PRIMARY KEY,
    fetch_run_id TEXT NOT NULL REFERENCES artifact_fetch_run(fetch_run_id)
        ON DELETE RESTRICT,
    artifact_id TEXT NOT NULL REFERENCES artifact(artifact_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    fetch_policy TEXT NOT NULL,
    requested_url TEXT NOT NULL,
    request_key TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'in_progress', 'success', 'failed_retryable', 'failed_terminal'
        )
    ),
    attempt_number INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    lease_expires_at TEXT,
    completed_at TEXT,
    final_url TEXT,
    redirect_chain_json TEXT,
    http_status INTEGER,
    response_headers_json TEXT,
    content_type TEXT,
    charset TEXT,
    content_length INTEGER,
    raw_sha256 TEXT,
    raw_snapshot_ref TEXT,
    extractor_contract TEXT,
    extractor_version TEXT,
    extracted_title TEXT,
    text_sha256 TEXT,
    text_snapshot_ref TEXT,
    text_char_count INTEGER,
    text_truncated INTEGER CHECK (text_truncated IN (0, 1)),
    declared_canonical_url TEXT,
    error_code TEXT,
    error_message TEXT,
    retryable INTEGER CHECK (retryable IN (0, 1)),
    UNIQUE (artifact_id, fetch_policy, requested_url, attempt_number)
);
CREATE INDEX IF NOT EXISTS idx_artifact_fetch_artifact
    ON artifact_fetch(artifact_id, status, completed_at DESC, fetch_id);
CREATE INDEX IF NOT EXISTS idx_artifact_fetch_reclaim
    ON artifact_fetch(status, lease_expires_at, artifact_id);
CREATE INDEX IF NOT EXISTS idx_artifact_fetch_run
    ON artifact_fetch(fetch_run_id, status, artifact_id, attempt_number);
CREATE UNIQUE INDEX IF NOT EXISTS idx_artifact_fetch_success
    ON artifact_fetch(artifact_id, fetch_policy, requested_url)
    WHERE status = 'success';

CREATE TABLE IF NOT EXISTS artifact_x_article_fetch (
    fetch_id TEXT PRIMARY KEY REFERENCES artifact_fetch(fetch_id)
        ON DELETE CASCADE,
    artifact_id TEXT NOT NULL REFERENCES artifact(artifact_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    provider TEXT NOT NULL CHECK (provider = 'twitterapi_io'),
    endpoint TEXT NOT NULL,
    request_post_id TEXT,
    canonical_article_id TEXT NOT NULL,
    canonical_article_url TEXT NOT NULL,
    request_made INTEGER NOT NULL CHECK (request_made IN (0, 1)),
    estimated_provider_credits INTEGER NOT NULL CHECK (
        estimated_provider_credits >= 0
    ),
    provider_status TEXT,
    provider_message TEXT,
    response_fetched_at TEXT,
    content_block_count INTEGER CHECK (content_block_count >= 0),
    content_blocks_json TEXT,
    content_blocks_sha256 TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_artifact_x_article_artifact
    ON artifact_x_article_fetch(artifact_id, fetch_id);
CREATE INDEX IF NOT EXISTS idx_artifact_x_article_post
    ON artifact_x_article_fetch(request_post_id, fetch_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {
        str(row["name"])
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }


def _rename_column(
    conn: sqlite3.Connection, table: str, old_name: str, new_name: str
) -> bool:
    columns = _table_columns(conn, table)
    if old_name not in columns:
        return False
    if new_name in columns:
        raise RuntimeError(
            f"{table} contains both {old_name} and {new_name}; migration is ambiguous"
        )
    conn.execute(f"ALTER TABLE {table} RENAME COLUMN {old_name} TO {new_name}")
    return True


def _rebuild_import_run_v2(conn: sqlite3.Connection) -> None:
    if not _table_columns(conn, "artifact_import_run"):
        return
    conn.execute(
        f"""CREATE TABLE artifact_import_run_v2 (
                import_run_id TEXT PRIMARY KEY,
                schema_version TEXT NOT NULL CHECK (schema_version = '{SCHEMA_VERSION}'),
                canonicalization_contract TEXT NOT NULL,
                source_feed_run_id TEXT NOT NULL,
                source_event_run_id TEXT NOT NULL,
                triage_runs_json TEXT NOT NULL,
                selection_policy TEXT NOT NULL,
                input_fingerprint TEXT NOT NULL,
                expected_candidate_count INTEGER NOT NULL,
                accepted_count INTEGER NOT NULL,
                excluded_count INTEGER NOT NULL,
                failed_count INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                UNIQUE (canonicalization_contract, input_fingerprint)
            )"""
    )
    conn.execute(
        """INSERT INTO artifact_import_run_v2 (
               import_run_id, schema_version, canonicalization_contract,
               source_feed_run_id, source_event_run_id, triage_runs_json,
               selection_policy, input_fingerprint, expected_candidate_count,
               accepted_count, excluded_count, failed_count, created_at,
               completed_at)
           SELECT import_run_id, ?, canonicalization_contract,
                  source_feed_run_id, source_event_run_id, triage_runs_json,
                  selection_policy, input_fingerprint, expected_candidate_count,
                  accepted_count, excluded_count, failed_count, created_at,
                  completed_at
           FROM artifact_import_run""",
        (SCHEMA_VERSION,),
    )
    conn.execute("DROP TABLE artifact_import_run")
    conn.execute("ALTER TABLE artifact_import_run_v2 RENAME TO artifact_import_run")


def _rebuild_fetch_run_v2(conn: sqlite3.Connection) -> None:
    if not _table_columns(conn, "artifact_fetch_run"):
        return
    conn.execute(
        f"""CREATE TABLE artifact_fetch_run_v2 (
                fetch_run_id TEXT PRIMARY KEY,
                schema_version TEXT NOT NULL CHECK (schema_version = '{SCHEMA_VERSION}'),
                fetch_policy TEXT NOT NULL,
                selection_policy TEXT NOT NULL,
                input_fingerprint TEXT NOT NULL,
                expected_count INTEGER NOT NULL,
                success_count INTEGER NOT NULL,
                failed_retryable_count INTEGER NOT NULL,
                failed_terminal_count INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL CHECK (status IN ('in_progress', 'complete')),
                UNIQUE (fetch_policy, input_fingerprint)
            )"""
    )
    conn.execute(
        """INSERT INTO artifact_fetch_run_v2 (
               fetch_run_id, schema_version, fetch_policy, selection_policy,
               input_fingerprint, expected_count, success_count,
               failed_retryable_count, failed_terminal_count, started_at,
               completed_at, status)
           SELECT fetch_run_id, ?, fetch_policy, selection_policy,
                  input_fingerprint, expected_count, success_count,
                  failed_retryable_count, failed_terminal_count, started_at,
                  completed_at, status
           FROM artifact_fetch_run""",
        (SCHEMA_VERSION,),
    )
    conn.execute("DROP TABLE artifact_fetch_run")
    conn.execute("ALTER TABLE artifact_fetch_run_v2 RENAME TO artifact_fetch_run")


def migrate_store(path: Path | str = DEFAULT_DB) -> bool:
    """Migrate a v1 artifact store to the Event-native v2 storage schema."""
    path = Path(path)
    if not path.is_file():
        return False
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA foreign_keys = OFF")
    renames = (
        ("artifact_observation", "first_envelope_day", "first_event_day"),
        ("artifact_disclosure", "first_envelope_day", "first_event_day"),
        ("artifact_disclosure", "last_envelope_day", "last_event_day"),
        ("artifact_import_candidate", "envelope_day", "event_day"),
        ("artifact_event_supplement", "envelope_day", "event_day"),
        (
            "artifact_event_supplement",
            "source_snapshot_content_sha256",
            "source_semantic_snapshot_sha256",
        ),
    )
    import_columns = _table_columns(conn, "artifact_import_run")
    import_versions = (
        {
            str(row[0])
            for row in conn.execute(
                "SELECT DISTINCT schema_version FROM artifact_import_run"
            ).fetchall()
        }
        if "schema_version" in import_columns
        else set()
    )
    fetch_columns = _table_columns(conn, "artifact_fetch_run")
    fetch_versions = (
        {
            str(row[0])
            for row in conn.execute(
                "SELECT DISTINCT schema_version FROM artifact_fetch_run"
            ).fetchall()
        }
        if "schema_version" in fetch_columns
        else set()
    )
    legacy_columns = any(
        old_name in _table_columns(conn, table)
        for table, old_name, _new_name in renames
    )
    if not (
        legacy_columns
        or import_versions - {SCHEMA_VERSION}
        or fetch_versions - {SCHEMA_VERSION}
    ):
        conn.close()
        return False

    changed = False
    try:
        conn.execute("BEGIN IMMEDIATE")
        for table, old_name, new_name in renames:
            changed = _rename_column(conn, table, old_name, new_name) or changed

        if import_versions - {SCHEMA_VERSION}:
            _rebuild_import_run_v2(conn)
            changed = True
        if fetch_versions - {SCHEMA_VERSION}:
            _rebuild_fetch_run_v2(conn)
            changed = True
        if changed:
            conn.execute("PRAGMA user_version = 2")
        conn.commit()
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(
                f"artifact-store-v2 migration created {len(violations)} foreign-key violations"
            )
        integrity = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity != "ok":
            raise RuntimeError(f"artifact-store-v2 integrity check failed: {integrity}")
        return changed
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def connect(path: Path | str = DEFAULT_DB) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        probe = sqlite3.connect(path)
        try:
            exists = probe.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' "
                "AND name = 'artifact_import_run'"
            ).fetchone()
            versions = (
                {
                    str(row[0])
                    for row in probe.execute(
                        "SELECT DISTINCT schema_version FROM artifact_import_run"
                    ).fetchall()
                }
                if exists
                else set()
            )
        finally:
            probe.close()
        if versions and versions != {SCHEMA_VERSION}:
            found = ", ".join(sorted(versions))
            raise RuntimeError(
                f"Artifact store uses {found}; rebuild it for {SCHEMA_VERSION}."
            )
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.executescript(SCHEMA)
    conn.execute("PRAGMA user_version = 2")
    return conn


def _open_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _published_context(
    events_db: Path, feed_db: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    events = _open_readonly(events_db)
    event_run = signal_events.published_run(events)
    events.close()
    if event_run is None:
        raise RuntimeError("Event store has no published run")
    feed = _open_readonly(feed_db)
    feed_run = feed.execute(
        "SELECT * FROM feed_run WHERE run_id = ?", (event_run["feed_run_id"],)
    ).fetchone()
    feed.close()
    if feed_run is None:
        raise RuntimeError("Published Event run references a missing Feed run")
    return dict(event_run), dict(feed_run)


def _matching_evidence(
    raw_json: str, target_url: str
) -> artifact_urls.UrlEvidence | None:
    evidence = artifact_urls.url_evidence(json.loads(raw_json))
    for item in evidence:
        if item.expanded_url == target_url or item.observed_url == target_url:
            return item
    try:
        target_canonical = artifact_urls.canonicalize_url(target_url)
    except ValueError:
        return None
    for item in evidence:
        try:
            if artifact_urls.canonicalize_url(item.expanded_url) == target_canonical:
                return item
        except ValueError:
            continue
    return None


def _matching_primary_evidence(
    raw_json: str, target_url: str, *, post_id: str
) -> artifact_urls.UrlEvidence | None:
    evidence = _matching_evidence(raw_json, target_url)
    return (
        evidence
        if evidence is not None and evidence.owner_external_id == post_id
        else None
    )


def _iter_feed_candidates(
    *,
    feed_db: Path,
    feed_run_id: str,
    events_db: Path,
    event_run_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Collect URLs from each visible root and its same-author replies."""
    if (
        feed_db.resolve() != Path(signal_feed.DEFAULT_FEED_DB).resolve()
        or events_db.resolve() != Path(signal_events.DEFAULT_EVENTS_DB).resolve()
    ):
        raise ValueError(
            "Primary artifact import currently requires the published canonical "
            "Feed and Event stores."
        )

    from fli.web import events as event_store

    feed = _open_readonly(feed_db)
    feed_run = feed.execute(
        "SELECT date_from, date_to FROM feed_run WHERE run_id = ?",
        (feed_run_id,),
    ).fetchone()
    if feed_run is None:
        feed.close()
        raise ValueError(f"Unknown Feed run: {feed_run_id}")
    posts = {
        str(row["post_id"]): row
        for row in feed.execute(
            """SELECT * FROM feed_post
               WHERE run_id = ? AND provider = 'twitterapi_io'
               ORDER BY post_id""",
            (feed_run_id,),
        ).fetchall()
    }

    start = datetime.fromisoformat(str(feed_run["date_from"])).date()
    end = datetime.fromisoformat(str(feed_run["date_to"])).date()
    current = start
    candidates: list[dict[str, Any]] = []
    day_counts: dict[str, int] = {}
    seen_sources: set[tuple[str, str]] = set()
    while current <= end:
        day = current.isoformat()
        payload = event_store.events_payload(
            day=day,
            lane="all",
            sort="attention",
            query="",
            routing_filter="all",
            limit=2**31 - 1,
            offset=0,
        )
        day_counts[day] = int(payload.get("daily_rank_total") or 0)
        for item in payload.get("items") or []:
            event_id = str(item["event_id"])
            source_rank = int(item["daily_rank"])
            primary_ids = evidence_lineage.verified_primary_post_ids(
                feed,
                feed_run_id=feed_run_id,
                event={"root": item["root"]},
            )
            root_id = str(item["root"]["post_id"])
            root_post = posts.get(root_id)
            if root_post is not None and str(root_post["post_type"]) == "reply":
                conversation_root = posts.get(
                    str(root_post["conversation_id"] or "")
                )
                root_author = str(
                    root_post["author_x_id"] or root_post["author_handle"]
                ).lower()
                conversation_author = (
                    str(
                        conversation_root["author_x_id"]
                        or conversation_root["author_handle"]
                    ).lower()
                    if conversation_root is not None
                    else ""
                )
                if not conversation_author or conversation_author != root_author:
                    primary_ids = set()
            for post_id in primary_ids:
                post = posts.get(post_id)
                if post is None:
                    continue
                # Process each source artifact on the first day its Event is
                # visible in this run. A quoted root and its stored thread may
                # predate the window even though the Event is first
                # discovered inside it; source publication day must not erase
                # those first-party artifact links.
                source_key = (event_id, post_id)
                if source_key in seen_sources:
                    continue
                seen_sources.add(source_key)
                disclosure_id = str(post["disclosure_post_id"] or post_id)
                disclosure = posts.get(disclosure_id) or post
                for evidence in artifact_urls.url_evidence(
                    json.loads(str(post["raw_json"]))
                ):
                    if evidence.owner_external_id != post_id:
                        continue
                    preliminary = artifact_urls.classify_candidate(
                        evidence.observed_url,
                        evidence.expanded_url,
                    )
                    candidates.append(
                        {
                            "event_day": day,
                            "event_id": event_id,
                            "source_rank": source_rank,
                            "day_candidate_count": day_counts[day],
                            "source_kind": "x_post",
                            "source_provider": str(post["provider"]),
                            "source_external_id": post_id,
                            "source_snapshot_sha256": str(post["raw_sha256"]),
                            "source_url": str(post["url"]),
                            "disclosure_external_id": str(disclosure["post_id"]),
                            "disclosure_snapshot_sha256": str(
                                disclosure["raw_sha256"]
                            ),
                            "disclosure_url": str(disclosure["url"]),
                            "disclosure_published_at": str(
                                disclosure["published_at"]
                            ),
                            "source_published_at": str(post["published_at"]),
                            "observed_url": evidence.observed_url,
                            "expanded_url": evidence.expanded_url,
                            "candidate_source": evidence.source,
                            "title_hint": "",
                            "relation": (
                                "self_publishes"
                                if preliminary.reason_code == "x_longform_article"
                                else "links_to"
                            ),
                            "forced_failure": None,
                        }
                    )
        current += timedelta(days=1)

    candidates.sort(key=lambda item: _canonical_json(_candidate_identity(item)))
    manifest = {
        "feed_run_id": feed_run_id,
        "event_run_id": event_run_id,
        "selection_policy": PRIMARY_AUTHOR_SELECTION_POLICY,
        "candidate_days": day_counts,
    }
    feed.close()
    return candidates, manifest


def _upsert_alias(
    conn: sqlite3.Connection,
    *,
    alias_url: str,
    target_artifact_id: str,
    alias_kind: str,
    seen_at: str,
) -> None:
    existing = conn.execute(
        "SELECT artifact_id FROM artifact_alias WHERE alias_url = ?", (alias_url,)
    ).fetchone()
    if existing is not None and str(existing["artifact_id"]) != target_artifact_id:
        raise ValueError("alias_conflict")
    conn.execute(
        """INSERT INTO artifact_alias
           (alias_url, artifact_id, alias_kind, first_seen_at, last_seen_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(alias_url) DO UPDATE SET
               first_seen_at = CASE
                   WHEN excluded.first_seen_at < first_seen_at
                   THEN excluded.first_seen_at ELSE first_seen_at END,
               last_seen_at = CASE
                   WHEN excluded.last_seen_at > last_seen_at
                   THEN excluded.last_seen_at ELSE last_seen_at END""",
        (alias_url, target_artifact_id, alias_kind, seen_at, seen_at),
    )


def _insert_candidate(
    conn: sqlite3.Connection,
    *,
    import_run_id: str,
    candidate: dict[str, Any],
    decision: str,
    reason_code: str,
    target_artifact_id: str | None,
    created_at: str,
) -> None:
    candidate_id = _sha256(_canonical_json([import_run_id, *_candidate_identity(candidate)]))
    conn.execute(
        """INSERT OR IGNORE INTO artifact_import_candidate
           (candidate_id, import_run_id, event_day, event_id, source_rank,
            day_candidate_count,
            source_kind, source_provider, source_external_id,
            source_snapshot_sha256, source_url, disclosure_external_id,
            disclosure_snapshot_sha256, disclosure_url, disclosure_published_at,
            observed_url, expanded_url,
            candidate_source, title_hint, relation, decision, reason_code,
            artifact_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            candidate_id,
            import_run_id,
            candidate["event_day"],
            candidate["event_id"],
            candidate["source_rank"],
            candidate["day_candidate_count"],
            candidate["source_kind"],
            candidate["source_provider"],
            candidate["source_external_id"],
            candidate["source_snapshot_sha256"],
            candidate["source_url"],
            candidate["disclosure_external_id"],
            candidate["disclosure_snapshot_sha256"],
            candidate["disclosure_url"],
            candidate["disclosure_published_at"],
            candidate["observed_url"],
            candidate["expanded_url"],
            candidate["candidate_source"],
            candidate["title_hint"] or None,
            candidate["relation"],
            decision,
            reason_code,
            target_artifact_id,
            created_at,
        ),
    )


def _candidate_identity(candidate: dict[str, Any]) -> list[Any]:
    return [
        candidate["event_day"],
        candidate["event_id"],
        candidate["source_external_id"],
        candidate["source_snapshot_sha256"],
        candidate["disclosure_external_id"],
        candidate["disclosure_snapshot_sha256"],
        candidate["observed_url"],
        candidate["expanded_url"],
        candidate["candidate_source"],
        candidate["title_hint"],
        candidate["relation"],
    ]


def import_feed_events(
    *,
    db_path: Path | str = DEFAULT_DB,
    feed_db: Path | str = signal_feed.DEFAULT_FEED_DB,
    events_db: Path | str = signal_events.DEFAULT_EVENTS_DB,
) -> dict[str, Any]:
    feed_path = Path(feed_db)
    events_path = Path(events_db)
    event_run, feed_run = _published_context(events_path, feed_path)
    candidates, manifest = _iter_feed_candidates(
        feed_db=feed_path,
        feed_run_id=str(feed_run["run_id"]),
        events_db=events_path,
        event_run_id=str(event_run["run_id"]),
    )
    candidates = list(
        {
            _canonical_json(_candidate_identity(candidate)): candidate
            for candidate in candidates
        }.values()
    )
    candidates.sort(key=lambda item: _canonical_json(_candidate_identity(item)))
    fingerprint = _sha256(
        _canonical_json(
            {
                "feed_run_id": feed_run["run_id"],
                "event_run_id": event_run["run_id"],
                "canonicalization_contract": artifact_urls.CANONICALIZATION_CONTRACT,
                "source_manifest": manifest,
                "candidates": candidates,
            }
        )
    )
    import_run_id = _sha256(
        _canonical_json([artifact_urls.CANONICALIZATION_CONTRACT, fingerprint])
    )
    conn = connect(db_path)
    existing = conn.execute(
        "SELECT * FROM artifact_import_run WHERE import_run_id = ?",
        (import_run_id,),
    ).fetchone()
    if existing is not None:
        result = dict(existing)
        result.pop("triage_runs_json", None)
        result["reused"] = True
        conn.close()
        return result

    stable_time = str(event_run["created_at"])
    conn.execute(
        """INSERT INTO artifact_import_run
           (import_run_id, schema_version, canonicalization_contract,
            source_feed_run_id, source_event_run_id, triage_runs_json,
            selection_policy, input_fingerprint, expected_candidate_count,
            accepted_count, excluded_count, failed_count, created_at,
            completed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?)""",
        (
            import_run_id,
            SCHEMA_VERSION,
            artifact_urls.CANONICALIZATION_CONTRACT,
            feed_run["run_id"],
            event_run["run_id"],
            _canonical_json(manifest),
            PRIMARY_AUTHOR_SELECTION_POLICY,
            fingerprint,
            len(candidates),
            stable_time,
            stable_time,
        ),
    )
    counts = {"accepted": 0, "excluded": 0, "failed": 0}
    with conn:
        for candidate in candidates:
            if candidate["forced_failure"]:
                decision = artifact_urls.CandidateDecision(
                    "failed", str(candidate["forced_failure"])
                )
            else:
                decision = artifact_urls.classify_candidate(
                    candidate["observed_url"], candidate["expanded_url"]
                )
            target_artifact_id: str | None = None
            if decision.decision == "accepted":
                assert decision.canonical_url and decision.artifact_kind
                target_artifact_id = artifact_urls.artifact_id(decision.canonical_url)
                seen_at = str(candidate["source_published_at"])
                host = str(urlsplit(decision.canonical_url).hostname or "")
                alias_targets = {
                    str(existing_alias["artifact_id"])
                    for alias in {
                        decision.canonical_url,
                        str(candidate["observed_url"]),
                        str(candidate["expanded_url"]),
                    }
                    if (
                        existing_alias := conn.execute(
                            "SELECT artifact_id FROM artifact_alias "
                            "WHERE alias_url = ?",
                            (alias,),
                        ).fetchone()
                    )
                    is not None
                }
                if len(alias_targets) > 1:
                    decision = artifact_urls.CandidateDecision(
                        "failed", "alias_conflict"
                    )
                    target_artifact_id = None
                elif alias_targets:
                    # A previous successful fetch may have proven a redirect
                    # and converged the preliminary artifact into its final
                    # identity. Reimports must follow that durable alias rather
                    # than resurrecting the pre-redirect ID or failing replay.
                    target_artifact_id = next(iter(alias_targets))
            if decision.decision == "accepted":
                assert decision.canonical_url and decision.artifact_kind
                assert target_artifact_id is not None
                seen_at = str(candidate["source_published_at"])
                host = str(urlsplit(decision.canonical_url).hostname or "")
                conn.execute(
                    """INSERT INTO artifact
                       (artifact_id, canonical_url, canonicalization_contract,
                        host, artifact_kind, first_seen_at, last_seen_at,
                        created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(artifact_id) DO UPDATE SET
                           first_seen_at = CASE
                               WHEN excluded.first_seen_at < first_seen_at
                               THEN excluded.first_seen_at ELSE first_seen_at END,
                           last_seen_at = CASE
                               WHEN excluded.last_seen_at > last_seen_at
                               THEN excluded.last_seen_at ELSE last_seen_at END,
                           updated_at = CASE
                               WHEN excluded.updated_at > updated_at
                               THEN excluded.updated_at ELSE updated_at END""",
                    (
                        target_artifact_id,
                        decision.canonical_url,
                        artifact_urls.CANONICALIZATION_CONTRACT,
                        host,
                        decision.artifact_kind,
                        seen_at,
                        seen_at,
                        stable_time,
                        stable_time,
                    ),
                )
                _upsert_alias(
                    conn,
                    alias_url=decision.canonical_url,
                    target_artifact_id=target_artifact_id,
                    alias_kind="canonical",
                    seen_at=seen_at,
                )
                _upsert_alias(
                    conn,
                    alias_url=str(candidate["observed_url"]),
                    target_artifact_id=target_artifact_id,
                    alias_kind="observed",
                    seen_at=seen_at,
                )
                _upsert_alias(
                    conn,
                    alias_url=str(candidate["expanded_url"]),
                    target_artifact_id=target_artifact_id,
                    alias_kind="expanded",
                    seen_at=seen_at,
                )
                observation_id = _sha256(
                        _canonical_json(
                            [
                                candidate["source_kind"],
                                candidate["source_provider"],
                                candidate["source_external_id"],
                                candidate["source_snapshot_sha256"],
                                candidate["observed_url"],
                                candidate["relation"],
                            ]
                        )
                    )
                conn.execute(
                        """INSERT INTO artifact_observation
                           (observation_id, artifact_id, source_kind,
                            source_provider, source_external_id,
                            source_snapshot_sha256, source_url, observed_url,
                            expanded_url, relation, source_published_at,
                            first_event_day, best_source_rank, first_seen_at,
                            last_seen_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           ON CONFLICT(observation_id) DO UPDATE SET
                               artifact_id = excluded.artifact_id,
                               best_source_rank = excluded.best_source_rank,
                               first_event_day = MIN(
                                   first_event_day, excluded.first_event_day
                               ),
                               first_seen_at = MIN(first_seen_at, excluded.first_seen_at),
                               last_seen_at = MAX(last_seen_at, excluded.last_seen_at)""",
                        (
                            observation_id,
                            target_artifact_id,
                            candidate["source_kind"],
                            candidate["source_provider"],
                            candidate["source_external_id"],
                            candidate["source_snapshot_sha256"],
                            candidate["source_url"],
                            candidate["observed_url"],
                            candidate["expanded_url"],
                            candidate["relation"],
                            candidate["source_published_at"],
                            candidate["event_day"],
                            candidate["source_rank"],
                            candidate["source_published_at"],
                            candidate["source_published_at"],
                        ),
                )
                disclosure_id = _sha256(
                    _canonical_json(
                        [
                            observation_id,
                            candidate["source_provider"],
                            candidate["disclosure_external_id"],
                            candidate["disclosure_snapshot_sha256"],
                        ]
                    )
                )
                conn.execute(
                    """INSERT INTO artifact_disclosure
                       (disclosure_id, observation_id, source_provider,
                        disclosure_external_id, disclosure_snapshot_sha256,
                        disclosure_url, disclosure_published_at,
                        first_event_day, last_event_day)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(disclosure_id) DO UPDATE SET
                           first_event_day = MIN(
                               first_event_day, excluded.first_event_day
                           ),
                           last_event_day = MAX(
                               last_event_day, excluded.last_event_day
                           )""",
                    (
                        disclosure_id,
                        observation_id,
                        candidate["source_provider"],
                        candidate["disclosure_external_id"],
                        candidate["disclosure_snapshot_sha256"],
                        candidate["disclosure_url"],
                        candidate["disclosure_published_at"],
                        candidate["event_day"],
                        candidate["event_day"],
                    ),
                )
            _insert_candidate(
                conn,
                import_run_id=import_run_id,
                candidate=candidate,
                decision=decision.decision,
                reason_code=decision.reason_code,
                target_artifact_id=target_artifact_id,
                created_at=stable_time,
            )
            counts[decision.decision] += 1
        conn.execute(
            """UPDATE artifact_import_run
               SET accepted_count = ?, excluded_count = ?, failed_count = ?
               WHERE import_run_id = ?""",
            (counts["accepted"], counts["excluded"], counts["failed"], import_run_id),
        )
        conn.execute(
            """DELETE FROM artifact_observation AS observation
               WHERE NOT EXISTS (
                   SELECT 1
                   FROM artifact_import_candidate AS candidate
                   WHERE candidate.import_run_id = ?
                     AND candidate.decision = 'accepted'
                     AND candidate.artifact_id = observation.artifact_id
                     AND candidate.source_kind = observation.source_kind
                     AND candidate.source_provider = observation.source_provider
                     AND candidate.source_external_id = observation.source_external_id
                     AND candidate.source_snapshot_sha256 = observation.source_snapshot_sha256
                     AND candidate.observed_url = observation.observed_url
                     AND candidate.relation = observation.relation
               )""",
            (import_run_id,),
        )
        conn.execute(
            "DELETE FROM artifact_import_run WHERE import_run_id != ?",
            (import_run_id,),
        )
        conn.execute(
            """DELETE FROM artifact
               WHERE NOT EXISTS (
                   SELECT 1 FROM artifact_observation
                   WHERE artifact_observation.artifact_id = artifact.artifact_id
               )
                 AND NOT EXISTS (
                   SELECT 1 FROM artifact_event_supplement
                   WHERE artifact_event_supplement.artifact_id = artifact.artifact_id
               )"""
        )
    result = dict(
        conn.execute(
            "SELECT * FROM artifact_import_run WHERE import_run_id = ?",
            (import_run_id,),
        ).fetchone()
    )
    result.pop("triage_runs_json", None)
    result.update(
        {
            "reused": False,
            "artifact_count": int(
                conn.execute("SELECT COUNT(*) FROM artifact").fetchone()[0]
            ),
            "observation_count": int(
                conn.execute("SELECT COUNT(*) FROM artifact_observation").fetchone()[0]
            ),
            "disclosure_count": int(
                conn.execute("SELECT COUNT(*) FROM artifact_disclosure").fetchone()[0]
            ),
        }
    )
    conn.close()
    return result


def _require_manifest_keys(
    value: dict[str, Any], *, required: set[str], label: str
) -> None:
    missing = sorted(required - set(value))
    extra = sorted(set(value) - required)
    if missing or extra:
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unknown " + ", ".join(extra))
        raise ValueError(f"{label} fields are invalid: {'; '.join(details)}")


def _require_review_timestamp(value: Any) -> str:
    rendered = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(rendered.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("reviewed_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("reviewed_at must include a timezone")
    return parsed.isoformat(timespec="seconds")


def _require_source_date(value: Any) -> str:
    rendered = str(value or "").strip()
    try:
        if "T" in rendered:
            parsed = datetime.fromisoformat(rendered.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError
        else:
            datetime.strptime(rendered, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(
            "source_published_at must be an ISO date or timezone-aware timestamp"
        ) from exc
    return rendered


def import_reviewed_supplements(
    *,
    manifest_path: Path | str,
    triage_db: Path | str,
    db_path: Path | str = DEFAULT_DB,
) -> dict[str, Any]:
    """Import explicitly reviewed event evidence without rewriting X provenance."""
    manifest_file = Path(manifest_path)
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"reviewed supplement manifest is invalid JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ValueError("reviewed supplement manifest must be a JSON object")
    _require_manifest_keys(
        manifest,
        required={"schema_version", "reviewed_by", "reviewed_at", "items"},
        label="manifest",
    )
    if manifest["schema_version"] != REVIEWED_SUPPLEMENT_CONTRACT:
        raise ValueError(
            "reviewed supplement manifest schema_version must be "
            + REVIEWED_SUPPLEMENT_CONTRACT
        )
    reviewed_by = str(manifest["reviewed_by"] or "").strip()
    if not reviewed_by:
        raise ValueError("reviewed_by must be non-empty")
    reviewed_at = _require_review_timestamp(manifest["reviewed_at"])
    raw_items = manifest["items"]
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("reviewed supplement manifest items must be a non-empty list")
    manifest_sha256 = _sha256(_canonical_json(manifest))

    triage_path = Path(triage_db)
    triage = _open_readonly(triage_path)
    try:
        meta = triage.execute(
            "SELECT run_id, day, expected_count FROM run_meta WHERE singleton = 1"
        ).fetchone()
        if meta is None:
            raise ValueError("triage database has no run metadata")
        source_triage_run_id = str(meta["run_id"])
        event_day = str(meta["day"])
        day_candidate_count = int(meta["expected_count"])
        prepared: list[dict[str, Any]] = []
        for ordinal, raw_item in enumerate(raw_items, start=1):
            if not isinstance(raw_item, dict):
                raise ValueError(f"items[{ordinal}] must be a JSON object")
            _require_manifest_keys(
                raw_item,
                required={
                    "event_id",
                    "artifact_url",
                    "evidence_role",
                    "source_published_at",
                    "rationale",
                },
                label=f"items[{ordinal}]",
            )
            event_id = str(raw_item["event_id"] or "").strip()
            rationale = str(raw_item["rationale"] or "").strip()
            if not event_id or not rationale:
                raise ValueError(
                    f"items[{ordinal}] event_id and rationale must be non-empty"
                )
            if raw_item["evidence_role"] != "official_primary_source":
                raise ValueError(
                    f"items[{ordinal}] evidence_role must be official_primary_source"
                )
            source_row = triage.execute(
                """SELECT event_id, current_rank, input_sha256,
                          semantic_snapshot_sha256, status, decision
                   FROM triage_item WHERE event_id = ?""",
                (event_id,),
            ).fetchone()
            if source_row is None:
                raise ValueError(
                    f"items[{ordinal}] event_id is not in the frozen triage run"
                )
            if str(source_row["status"]) != "complete" or str(
                source_row["decision"]
            ) != "keep":
                raise ValueError(
                    f"items[{ordinal}] event must be a completed kept Event"
                )
            artifact_url = str(raw_item["artifact_url"] or "").strip()
            decision = artifact_urls.classify_candidate(artifact_url, artifact_url)
            if decision.decision != "accepted":
                raise ValueError(
                    f"items[{ordinal}] artifact URL is not fetchable: "
                    f"{decision.reason_code}"
                )
            assert decision.canonical_url and decision.artifact_kind
            artifact_id = artifact_urls.artifact_id(decision.canonical_url)
            source_published_at = _require_source_date(
                raw_item["source_published_at"]
            )
            frozen = {
                "contract": REVIEWED_SUPPLEMENT_CONTRACT,
                "manifest_sha256": manifest_sha256,
                "artifact_id": artifact_id,
                "canonical_url": decision.canonical_url,
                "artifact_kind": decision.artifact_kind,
                "observed_url": artifact_url,
                "event_id": event_id,
                "event_day": event_day,
                "source_rank": int(source_row["current_rank"]),
                "day_candidate_count": day_candidate_count,
                "source_triage_run_id": source_triage_run_id,
                "source_input_sha256": str(source_row["input_sha256"]),
                "source_semantic_snapshot_sha256": str(
                    source_row["semantic_snapshot_sha256"] or ""
                ),
                "evidence_role": "official_primary_source",
                "source_published_at": source_published_at,
                "rationale": rationale,
                "reviewed_by": reviewed_by,
                "reviewed_at": reviewed_at,
            }
            frozen["supplement_id"] = _sha256(_canonical_json(frozen))
            prepared.append(frozen)
    finally:
        triage.close()

    identities = [(item["event_id"], item["artifact_id"]) for item in prepared]
    if len(set(identities)) != len(identities):
        raise ValueError("reviewed supplement manifest contains duplicate event artifacts")

    conn = connect(db_path)
    imported = 0
    reused = 0
    try:
        with conn:
            for item in prepared:
                conflict = conn.execute(
                    """SELECT supplement_id FROM artifact_event_supplement
                       WHERE contract = ? AND source_triage_run_id = ?
                         AND event_id = ? AND artifact_id = ?""",
                    (
                        REVIEWED_SUPPLEMENT_CONTRACT,
                        item["source_triage_run_id"],
                        item["event_id"],
                        item["artifact_id"],
                    ),
                ).fetchone()
                if conflict is not None:
                    if str(conflict["supplement_id"]) != item["supplement_id"]:
                        raise ValueError(
                            "reviewed supplement conflicts with an existing frozen "
                            f"association for event {item['event_id']}"
                        )
                    reused += 1
                    continue
                host = str(urlsplit(item["canonical_url"]).hostname or "")
                conn.execute(
                    """INSERT INTO artifact
                       (artifact_id, canonical_url, canonicalization_contract,
                        host, artifact_kind, first_seen_at, last_seen_at,
                        created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(artifact_id) DO UPDATE SET
                           last_seen_at = MAX(last_seen_at, excluded.last_seen_at),
                           updated_at = MAX(updated_at, excluded.updated_at)""",
                    (
                        item["artifact_id"],
                        item["canonical_url"],
                        artifact_urls.CANONICALIZATION_CONTRACT,
                        host,
                        item["artifact_kind"],
                        item["reviewed_at"],
                        item["reviewed_at"],
                        item["reviewed_at"],
                        item["reviewed_at"],
                    ),
                )
                _upsert_alias(
                    conn,
                    alias_url=item["canonical_url"],
                    target_artifact_id=item["artifact_id"],
                    alias_kind="canonical",
                    seen_at=item["reviewed_at"],
                )
                if item["observed_url"] != item["canonical_url"]:
                    _upsert_alias(
                        conn,
                        alias_url=item["observed_url"],
                        target_artifact_id=item["artifact_id"],
                        alias_kind="observed",
                        seen_at=item["reviewed_at"],
                    )
                conn.execute(
                    """INSERT INTO artifact_event_supplement
                       (supplement_id, contract, manifest_sha256, artifact_id,
                        event_id, event_day, source_rank,
                        day_candidate_count, source_triage_run_id,
                        source_input_sha256, source_semantic_snapshot_sha256,
                        evidence_role, source_published_at, rationale,
                        reviewed_by, reviewed_at, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item["supplement_id"],
                        item["contract"],
                        item["manifest_sha256"],
                        item["artifact_id"],
                        item["event_id"],
                        item["event_day"],
                        item["source_rank"],
                        item["day_candidate_count"],
                        item["source_triage_run_id"],
                        item["source_input_sha256"],
                        item["source_semantic_snapshot_sha256"],
                        item["evidence_role"],
                        item["source_published_at"],
                        item["rationale"],
                        item["reviewed_by"],
                        item["reviewed_at"],
                        item["reviewed_at"],
                    ),
                )
                imported += 1
        return {
            "contract": REVIEWED_SUPPLEMENT_CONTRACT,
            "manifest_sha256": manifest_sha256,
            "source_triage_run_id": source_triage_run_id,
            "expected_count": len(prepared),
            "imported_count": imported,
            "reused_count": reused,
            "artifact_ids": sorted(item["artifact_id"] for item in prepared),
            "supplement_ids": sorted(item["supplement_id"] for item in prepared),
        }
    finally:
        conn.close()


def converge_artifact(
    conn: sqlite3.Connection,
    *,
    source_artifact_id: str,
    final_url: str,
    seen_at: str,
) -> str:
    """Converge a proven redirect target and preserve the old identity as alias."""
    final_canonical = artifact_urls.canonicalize_url(final_url)
    target_id = artifact_urls.artifact_id(final_canonical)
    if target_id == source_artifact_id:
        _upsert_alias(
            conn,
            alias_url=final_url,
            target_artifact_id=source_artifact_id,
            alias_kind="redirect",
            seen_at=seen_at,
        )
        return source_artifact_id
    source = conn.execute(
        "SELECT * FROM artifact WHERE artifact_id = ?", (source_artifact_id,)
    ).fetchone()
    if source is None:
        raise ValueError("source_artifact_missing")
    target = conn.execute(
        "SELECT * FROM artifact WHERE artifact_id = ?", (target_id,)
    ).fetchone()
    if target is None:
        conn.execute(
            """INSERT INTO artifact
               (artifact_id, canonical_url, canonicalization_contract, host,
                artifact_kind, title, title_fetch_id, first_seen_at, last_seen_at,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                target_id,
                final_canonical,
                source["canonicalization_contract"],
                urlsplit(final_canonical).hostname or "",
                source["artifact_kind"],
                source["title"],
                source["title_fetch_id"],
                source["first_seen_at"],
                max(str(source["last_seen_at"]), seen_at),
                source["created_at"],
                seen_at,
            ),
        )
    for row in conn.execute(
        "SELECT alias_url FROM artifact_alias WHERE artifact_id = ?",
        (source_artifact_id,),
    ).fetchall():
        existing = conn.execute(
            "SELECT artifact_id FROM artifact_alias WHERE alias_url = ?",
            (row["alias_url"],),
        ).fetchone()
        if existing is not None and str(existing["artifact_id"]) not in {
            source_artifact_id,
            target_id,
        }:
            raise ValueError("alias_conflict")
    conn.execute(
        "UPDATE artifact_alias SET artifact_id = ? WHERE artifact_id = ?",
        (target_id, source_artifact_id),
    )
    conn.execute(
        "UPDATE artifact_observation SET artifact_id = ? WHERE artifact_id = ?",
        (target_id, source_artifact_id),
    )
    conn.execute(
        "UPDATE artifact_import_candidate SET artifact_id = ? WHERE artifact_id = ?",
        (target_id, source_artifact_id),
    )
    for item in conn.execute(
        "SELECT fetch_run_id FROM artifact_fetch_run_item WHERE artifact_id = ?",
        (source_artifact_id,),
    ).fetchall():
        duplicate = conn.execute(
            """SELECT 1 FROM artifact_fetch_run_item
               WHERE fetch_run_id = ? AND artifact_id = ?""",
            (item["fetch_run_id"], target_id),
        ).fetchone()
        if duplicate is None:
            conn.execute(
                """UPDATE artifact_fetch_run_item SET artifact_id = ?
                   WHERE fetch_run_id = ? AND artifact_id = ?""",
                (target_id, item["fetch_run_id"], source_artifact_id),
            )
        else:
            conn.execute(
                """DELETE FROM artifact_fetch_run_item
                   WHERE fetch_run_id = ? AND artifact_id = ?""",
                (item["fetch_run_id"], source_artifact_id),
            )
    conn.execute(
        "UPDATE artifact_x_article_fetch SET artifact_id = ? WHERE artifact_id = ?",
        (target_id, source_artifact_id),
    )
    conn.execute(
        "UPDATE artifact_fetch SET artifact_id = ? WHERE artifact_id = ?",
        (target_id, source_artifact_id),
    )
    conn.execute("DELETE FROM artifact WHERE artifact_id = ?", (source_artifact_id,))
    _upsert_alias(
        conn,
        alias_url=str(source["canonical_url"]),
        target_artifact_id=target_id,
        alias_kind="redirect",
        seen_at=seen_at,
    )
    _upsert_alias(
        conn,
        alias_url=final_url,
        target_artifact_id=target_id,
        alias_kind="redirect",
        seen_at=seen_at,
    )
    return target_id


def audit_primary_author_lineage(
    *,
    db_path: Path | str = DEFAULT_DB,
    feed_db: Path | str = signal_feed.DEFAULT_FEED_DB,
) -> dict[str, Any]:
    """Verify that the live catalog is derivable from primary-account posts."""

    catalog = _open_readonly(Path(db_path))
    import_run = catalog.execute(
        """SELECT * FROM artifact_import_run
           ORDER BY completed_at DESC, import_run_id DESC LIMIT 1"""
    ).fetchone()
    if import_run is None:
        catalog.close()
        raise ValueError("artifact catalog has no import run to audit")

    candidates = catalog.execute(
        """SELECT * FROM artifact_import_candidate
           WHERE import_run_id = ? AND decision = 'accepted'
           ORDER BY candidate_id""",
        (import_run["import_run_id"],),
    ).fetchall()
    observations = catalog.execute(
        """SELECT observation_id, artifact_id, source_external_id,
                  source_snapshot_sha256, observed_url
           FROM artifact_observation
           ORDER BY observation_id"""
    ).fetchall()
    artifacts_without_lineage = catalog.execute(
        """SELECT artifact_id FROM artifact artifact_row
           WHERE NOT EXISTS (
               SELECT 1 FROM artifact_observation observation
               WHERE observation.artifact_id = artifact_row.artifact_id
           ) AND NOT EXISTS (
               SELECT 1 FROM artifact_event_supplement supplement
               WHERE supplement.artifact_id = artifact_row.artifact_id
           )
           ORDER BY artifact_id"""
    ).fetchall()
    observations_without_disclosure = catalog.execute(
        """SELECT observation_id, source_external_id
           FROM artifact_observation observation
           WHERE NOT EXISTS (
               SELECT 1 FROM artifact_disclosure disclosure
               WHERE disclosure.observation_id = observation.observation_id
           )
           ORDER BY observation_id"""
    ).fetchall()
    artifact_count = int(catalog.execute("SELECT COUNT(*) FROM artifact").fetchone()[0])
    supplement_count = int(
        catalog.execute("SELECT COUNT(*) FROM artifact_event_supplement").fetchone()[0]
    )
    catalog.close()

    violations: list[dict[str, str]] = []

    def add_violation(
        reason_code: str,
        *,
        candidate_id: str = "",
        event_id: str = "",
        root_external_id: str = "",
        source_external_id: str = "",
    ) -> None:
        violations.append(
            {
                "reason_code": reason_code,
                "candidate_id": candidate_id,
                "event_id": event_id,
                "root_external_id": root_external_id,
                "source_external_id": source_external_id,
            }
        )

    selection_policy = str(import_run["selection_policy"])
    if selection_policy != PRIMARY_AUTHOR_SELECTION_POLICY:
        add_violation("unexpected_selection_policy")

    feed = _open_readonly(Path(feed_db))
    feed_rows = {
        str(row["post_id"]): row
        for row in feed.execute(
            """SELECT post_id, author_x_id, conversation_id, post_type,
                      raw_sha256, raw_json
               FROM feed_post
               WHERE run_id = ? AND provider = 'twitterapi_io'
               ORDER BY post_id""",
            (import_run["source_feed_run_id"],),
        ).fetchall()
    }
    feed.close()

    accepted_observation_keys: set[tuple[str, str, str, str]] = set()
    unverified_conversation_roots = 0
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        event_id = str(candidate["event_id"])
        source_id = str(candidate["source_external_id"])
        source = feed_rows.get(source_id)
        root_id = (
            str(source["conversation_id"] or source_id) if source is not None else ""
        )
        common = {
            "candidate_id": candidate_id,
            "event_id": event_id,
            "root_external_id": root_id,
            "source_external_id": source_id,
        }
        if str(candidate["source_kind"]) != "x_post" or str(
            candidate["source_provider"]
        ) != "twitterapi_io":
            add_violation("unexpected_source_provider", **common)
        if candidate["artifact_id"] is None:
            add_violation("accepted_candidate_missing_artifact", **common)
        if source is None:
            add_violation("missing_source_post", **common)
            continue
        root = feed_rows.get(root_id)
        if root is None:
            # Some same-author thread replies were frozen without retaining the
            # conversation root in this Feed run. Their immutable import
            # decision and source snapshot remain auditable, but the root
            # author's identity cannot be independently rechecked here.
            unverified_conversation_roots += 1
        if str(source["raw_sha256"]) != str(candidate["source_snapshot_sha256"]):
            add_violation("stale_source_snapshot", **common)
        if source_id != root_id and root is not None:
            root_author = str(root["author_x_id"] or "")
            source_author = str(source["author_x_id"] or "")
            if not root_author or source_author != root_author:
                add_violation("foreign_author", **common)
            if str(source["post_type"] or "") != "reply":
                add_violation("non_reply_continuation", **common)
            root_conversation = str(root["conversation_id"] or root_id)
            source_conversation = str(source["conversation_id"] or source_id)
            if source_conversation != root_conversation:
                add_violation("wrong_conversation", **common)
        if _matching_primary_evidence(
            str(source["raw_json"]),
            str(candidate["expanded_url"]),
            post_id=source_id,
        ) is None:
            add_violation("unbound_source_url", **common)
        accepted_observation_keys.add(
            (
                str(candidate["artifact_id"]),
                source_id,
                str(candidate["source_snapshot_sha256"]),
                str(candidate["observed_url"]),
            )
        )

    for observation in observations:
        key = (
            str(observation["artifact_id"]),
            str(observation["source_external_id"]),
            str(observation["source_snapshot_sha256"]),
            str(observation["observed_url"]),
        )
        if key not in accepted_observation_keys:
            add_violation(
                "orphan_observation",
                source_external_id=str(observation["source_external_id"]),
            )
    for row in artifacts_without_lineage:
        add_violation(
            "artifact_without_lineage",
            candidate_id=str(row["artifact_id"]),
        )
    for row in observations_without_disclosure:
        add_violation(
            "observation_without_disclosure",
            candidate_id=str(row["observation_id"]),
            source_external_id=str(row["source_external_id"]),
        )
    violations.sort(
        key=lambda item: (
            item["reason_code"],
            item["event_id"],
            item["source_external_id"],
            item["candidate_id"],
        )
    )
    reason_counts = dict(sorted(Counter(v["reason_code"] for v in violations).items()))
    return {
        "passed": not violations,
        "import_run_id": str(import_run["import_run_id"]),
        "source_feed_run_id": str(import_run["source_feed_run_id"]),
        "selection_policy": selection_policy,
        "coverage": {
            "conversation_roots_verified": len(candidates)
            - unverified_conversation_roots,
            "conversation_roots_frozen_import_only": unverified_conversation_roots,
        },
        "counts": {
            "accepted_candidates": len(candidates),
            "artifacts": artifact_count,
            "observations": len(observations),
            "reviewed_supplements": supplement_count,
            "violations": len(violations),
        },
        "violation_reasons": reason_counts,
        "violations": violations[:100],
        "violations_truncated": len(violations) > 100,
    }


def summary(conn: sqlite3.Connection) -> dict[str, Any]:
    counts = {
        "imports": int(conn.execute("SELECT COUNT(*) FROM artifact_import_run").fetchone()[0]),
        "artifacts": int(conn.execute("SELECT COUNT(*) FROM artifact").fetchone()[0]),
        "aliases": int(conn.execute("SELECT COUNT(*) FROM artifact_alias").fetchone()[0]),
        "observations": int(conn.execute("SELECT COUNT(*) FROM artifact_observation").fetchone()[0]),
        "disclosures": int(conn.execute("SELECT COUNT(*) FROM artifact_disclosure").fetchone()[0]),
        "candidates": int(conn.execute("SELECT COUNT(*) FROM artifact_import_candidate").fetchone()[0]),
        "reviewed_supplements": int(
            conn.execute("SELECT COUNT(*) FROM artifact_event_supplement").fetchone()[0]
        ),
        "fetch_runs": int(conn.execute("SELECT COUNT(*) FROM artifact_fetch_run").fetchone()[0]),
        "fetch_attempts": int(
            conn.execute("SELECT COUNT(*) FROM artifact_fetch").fetchone()[0]
        ),
        "x_article_provider_requests": int(
            conn.execute(
                """SELECT COUNT(*) FROM artifact_x_article_fetch
                   WHERE request_made = 1"""
            ).fetchone()[0]
        ),
        "x_article_estimated_provider_credits": int(
            conn.execute(
                """SELECT COALESCE(SUM(estimated_provider_credits), 0)
                   FROM artifact_x_article_fetch"""
            ).fetchone()[0]
        ),
    }
    decisions = {
        str(row["decision"]): int(row["n"])
        for row in conn.execute(
            "SELECT decision, COUNT(*) AS n FROM artifact_import_candidate GROUP BY decision"
        ).fetchall()
    }
    fetch_attempts = {
        str(row["status"]): int(row["n"])
        for row in conn.execute(
            "SELECT status, COUNT(*) AS n FROM artifact_fetch GROUP BY status"
        ).fetchall()
    }
    fetch_outcomes = {
        str(row["status"]): int(row["n"])
        for row in conn.execute(
            """WITH ranked AS (
                   SELECT artifact_id, status,
                          ROW_NUMBER() OVER (
                              PARTITION BY artifact_id
                              ORDER BY CASE status
                                  WHEN 'success' THEN 0
                                  WHEN 'failed_terminal' THEN 1
                                  WHEN 'failed_retryable' THEN 2
                                  ELSE 3 END,
                                  attempt_number DESC
                          ) AS ordinal
                   FROM artifact_fetch
               )
               SELECT status, COUNT(*) AS n
               FROM ranked WHERE ordinal = 1 GROUP BY status"""
        ).fetchall()
    }
    return {
        "counts": counts,
        "candidate_decisions": decisions,
        "fetch_outcomes": fetch_outcomes,
        "fetch_attempt_statuses": fetch_attempts,
    }


def inspect_artifacts(conn: sqlite3.Connection, *, limit: int = 20) -> list[dict[str, Any]]:
    rows = conn.execute(
        """SELECT artifact.*,
                  COUNT(DISTINCT observation.observation_id) AS observation_count,
                  MIN(observation.best_source_rank) AS best_source_rank,
                  COUNT(DISTINCT CASE WHEN fetch.status = 'success'
                      THEN fetch.fetch_id END) AS successful_fetch_count
           FROM artifact
           LEFT JOIN artifact_observation observation
             ON observation.artifact_id = artifact.artifact_id
           LEFT JOIN artifact_fetch fetch ON fetch.artifact_id = artifact.artifact_id
           GROUP BY artifact.artifact_id
           ORDER BY best_source_rank, observation_count DESC, artifact.canonical_url
           LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]
