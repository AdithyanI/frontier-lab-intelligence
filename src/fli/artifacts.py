"""Canonical artifact catalog over outbound links in kept X envelopes."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

from fli import artifact_urls, evidence_lineage, signal_events, signal_feed, sources


SCHEMA_VERSION = "artifact-store-v1"
RESULT_SCHEMA_VERSION = "1.0"
REVIEWED_SUPPLEMENT_CONTRACT = "artifact-reviewed-supplement-v1"
PRIMARY_AUTHOR_SELECTION_POLICY = "kept-envelope-primary-author-thread-artifacts-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "data" / "derived" / "artifacts" / "artifacts.db"
DEFAULT_TRIAGE_ROOT = (
    REPO_ROOT / "data" / "derived" / "cited-insights" / "triage"
)

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
    first_envelope_day TEXT NOT NULL,
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
    first_envelope_day TEXT NOT NULL,
    last_envelope_day TEXT NOT NULL,
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
    envelope_day TEXT NOT NULL,
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
    envelope_day TEXT NOT NULL,
    source_rank INTEGER NOT NULL,
    day_candidate_count INTEGER NOT NULL,
    source_triage_run_id TEXT NOT NULL,
    source_input_sha256 TEXT NOT NULL,
    source_snapshot_content_sha256 TEXT NOT NULL,
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
    ON artifact_event_supplement(artifact_id, envelope_day, source_rank);

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
    return conn


def _open_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _latest_complete_triage_run(root: Path, day: str) -> tuple[Path, dict[str, Any]]:
    candidates: list[tuple[str, str, Path, dict[str, Any]]] = []
    for path in root.glob("*/triage.db"):
        try:
            source = _open_readonly(path)
            meta = source.execute(
                "SELECT * FROM run_meta WHERE singleton = 1"
            ).fetchone()
            if meta is None or str(meta["day"]) != day:
                source.close()
                continue
            complete = int(
                source.execute(
                    "SELECT COUNT(*) FROM triage_item WHERE status = 'complete'"
                ).fetchone()[0]
            )
            source.close()
            if complete != int(meta["expected_count"]):
                continue
            payload = dict(meta)
            candidates.append(
                (str(meta["updated_at"]), str(meta["run_id"]), path, payload)
            )
        except (OSError, sqlite3.Error):
            continue
    if not candidates:
        raise FileNotFoundError(f"No complete triage run for {day} under {root}")
    _updated, _run_id, path, payload = max(candidates)
    return path, payload


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


def _candidate_targets(envelope: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    targets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in envelope.get("urls") or []:
        if isinstance(item, dict) and item.get("post_id") and item.get("url"):
            targets[str(item["post_id"])].append(
                {
                    "url": str(item["url"]),
                    "source": "envelope_url",
                    "title": "",
                    "kind": "",
                }
            )
    previews: dict[tuple[str, str], dict[str, str]] = {}
    for item in envelope.get("embedded_artifacts") or []:
        if isinstance(item, dict) and item.get("post_id") and item.get("url"):
            previews[(str(item["post_id"]), str(item["url"]))] = {
                "source": str(item.get("kind") or "embedded_artifact"),
                "title": str(item.get("title") or ""),
                "kind": str(item.get("kind") or ""),
            }
    for post_id, values in targets.items():
        for value in values:
            preview = previews.get((post_id, value["url"]))
            if preview is not None:
                value.update(preview)
        targets[post_id] = list(
            {
                (value["url"], value["source"], value["title"], value["kind"]): value
                for value in values
            }.values()
        )
    return targets


def _matching_evidence(
    raw_json: str, target_url: str, *, fallback_owner_external_id: str
) -> artifact_urls.UrlEvidence:
    payload = json.loads(raw_json)
    evidence = artifact_urls.url_evidence(payload)
    for item in evidence:
        if item.expanded_url == target_url or item.observed_url == target_url:
            return item
    try:
        target_canonical = artifact_urls.canonicalize_url(target_url)
    except ValueError:
        target_canonical = None
    if target_canonical is not None:
        for item in evidence:
            try:
                if artifact_urls.canonicalize_url(item.expanded_url) == target_canonical:
                    return item
            except ValueError:
                continue
    return artifact_urls.UrlEvidence(
        target_url, target_url, "envelope", fallback_owner_external_id
    )


def _matching_primary_evidence(
    raw_json: str, target_url: str, *, post_id: str
) -> artifact_urls.UrlEvidence | None:
    evidence = _matching_evidence(
        raw_json,
        target_url,
        fallback_owner_external_id=post_id,
    )
    return evidence if evidence.owner_external_id == post_id else None


def _iter_frozen_candidates(
    *,
    feed_db: Path,
    feed_run_id: str,
    triage_runs: list[tuple[str, Path, dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    feed = _open_readonly(feed_db)
    candidates: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    for day, path, meta in triage_runs:
        triage = _open_readonly(path)
        rows = triage.execute(
            """SELECT event_id, current_rank, envelope_json, input_sha256,
                      snapshot_content_sha256
               FROM triage_item
               WHERE status = 'complete' AND decision = 'keep'
               ORDER BY current_rank, event_id"""
        ).fetchall()
        manifest.append(
            {
                "day": day,
                "run_id": str(meta["run_id"]),
                "path": str(path.relative_to(REPO_ROOT)),
                "prompt_version": str(meta["prompt_version"]),
                "kept_count": len(rows),
                "items": [
                    [
                        str(row["event_id"]),
                        str(row["input_sha256"]),
                        str(row["snapshot_content_sha256"] or ""),
                    ]
                    for row in rows
                ],
            }
        )
        for row in rows:
            envelope = json.loads(row["envelope_json"])
            primary_post_ids = evidence_lineage.verified_primary_post_ids(
                feed,
                feed_run_id=feed_run_id,
                envelope=envelope,
            )
            frozen_targets = _candidate_targets(envelope)
            for post_id in sorted(primary_post_ids):
                targets = list(frozen_targets.get(post_id, []))
                post = feed.execute(
                    """SELECT * FROM feed_post
                       WHERE run_id = ? AND provider = 'twitterapi_io'
                         AND post_id = ?""",
                    (feed_run_id, post_id),
                ).fetchone()
                if post is not None:
                    for evidence in artifact_urls.url_evidence(
                        json.loads(str(post["raw_json"]))
                    ):
                        if evidence.owner_external_id != post_id:
                            continue
                        decision = artifact_urls.classify_candidate(
                            evidence.observed_url,
                            evidence.expanded_url,
                        )
                        targets.append(
                            {
                                "url": evidence.expanded_url,
                                "source": evidence.source,
                                "title": "",
                                "kind": (
                                    "x_article"
                                    if decision.reason_code == "x_longform_article"
                                    else ""
                                ),
                            }
                        )
                    targets_by_url: dict[str, dict[str, str]] = {}
                    for target in targets:
                        existing = targets_by_url.get(target["url"])
                        if existing is None or (
                            target["kind"] == "x_article"
                            and existing["kind"] != "x_article"
                        ):
                            targets_by_url[target["url"]] = target
                        elif not existing["title"] and target["title"]:
                            existing["title"] = target["title"]
                    targets = list(targets_by_url.values())
                if not targets:
                    continue
                if post is None:
                    for target in targets:
                        candidates.append(
                            {
                                "envelope_day": day,
                                "event_id": str(row["event_id"]),
                                "source_rank": int(row["current_rank"]),
                                "day_candidate_count": int(meta["expected_count"]),
                                "source_kind": "x_post",
                                "source_provider": "twitterapi_io",
                                "source_external_id": post_id,
                                "source_snapshot_sha256": "missing",
                                "source_url": f"https://x.com/i/status/{post_id}",
                                "disclosure_external_id": post_id,
                                "disclosure_snapshot_sha256": "missing",
                                "disclosure_url": f"https://x.com/i/status/{post_id}",
                                "disclosure_published_at": day,
                                "source_published_at": day,
                                "observed_url": target["url"],
                                "expanded_url": target["url"],
                                "candidate_source": target["source"],
                                "title_hint": target["title"],
                                "relation": "links_to",
                                "forced_failure": "missing_source_snapshot",
                            }
                        )
                    continue
                for target in targets:
                    evidence = _matching_primary_evidence(
                        str(post["raw_json"]),
                        target["url"],
                        post_id=post_id,
                    )
                    if evidence is None:
                        continue
                    owner = feed.execute(
                        """SELECT * FROM feed_post
                           WHERE run_id = ? AND provider = 'twitterapi_io'
                             AND post_id = ?""",
                        (feed_run_id, evidence.owner_external_id),
                    ).fetchone()
                    if owner is None:
                        owner = post
                    disclosure_id = str(owner["disclosure_post_id"] or post_id)
                    disclosure = feed.execute(
                        """SELECT * FROM feed_post
                           WHERE run_id = ? AND provider = 'twitterapi_io'
                             AND post_id = ?""",
                        (feed_run_id, disclosure_id),
                    ).fetchone()
                    if disclosure is None:
                        disclosure = post
                    candidates.append(
                        {
                            "envelope_day": day,
                            "event_id": str(row["event_id"]),
                            "source_rank": int(row["current_rank"]),
                            "day_candidate_count": int(meta["expected_count"]),
                            "source_kind": "x_post",
                            "source_provider": str(post["provider"]),
                            "source_external_id": str(owner["post_id"]),
                            "source_snapshot_sha256": str(owner["raw_sha256"]),
                            "source_url": str(owner["url"]),
                            "disclosure_external_id": str(disclosure["post_id"]),
                            "disclosure_snapshot_sha256": str(
                                disclosure["raw_sha256"]
                            ),
                            "disclosure_url": str(disclosure["url"]),
                            "disclosure_published_at": str(
                                disclosure["published_at"]
                            ),
                            "source_published_at": str(owner["published_at"]),
                            "observed_url": evidence.observed_url,
                            "expanded_url": evidence.expanded_url,
                            "candidate_source": (
                                target["source"]
                                if target["source"] != "envelope_url"
                                else evidence.source
                            ),
                            "title_hint": target["title"],
                            "relation": (
                                "self_publishes"
                                if target["kind"] == "x_article"
                                else "links_to"
                            ),
                            "forced_failure": None,
                        }
                    )
        triage.close()
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
           (candidate_id, import_run_id, envelope_day, event_id, source_rank,
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
            candidate["envelope_day"],
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
        candidate["envelope_day"],
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


def import_kept_envelopes(
    *,
    db_path: Path | str = DEFAULT_DB,
    feed_db: Path | str = signal_feed.DEFAULT_FEED_DB,
    events_db: Path | str = signal_events.DEFAULT_EVENTS_DB,
    triage_root: Path | str = DEFAULT_TRIAGE_ROOT,
) -> dict[str, Any]:
    feed_path = Path(feed_db)
    events_path = Path(events_db)
    triage_path = Path(triage_root)
    event_run, feed_run = _published_context(events_path, feed_path)
    start = datetime.fromisoformat(str(feed_run["date_from"])).date()
    end = datetime.fromisoformat(str(feed_run["date_to"])).date()
    days = []
    current = start
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
    triage_runs = [
        (day, *_latest_complete_triage_run(triage_path, day)) for day in days
    ]
    candidates, manifest = _iter_frozen_candidates(
        feed_db=feed_path,
        feed_run_id=str(feed_run["run_id"]),
        triage_runs=triage_runs,
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
                "triage": manifest,
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

    stable_time = max(str(item[2]["updated_at"]) for item in triage_runs)
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
                conflicting_alias = next(
                    (
                        alias
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
                        and str(existing_alias["artifact_id"]) != target_artifact_id
                    ),
                    None,
                )
                if conflicting_alias is not None:
                    decision = artifact_urls.CandidateDecision(
                        "failed", "alias_conflict"
                    )
                    target_artifact_id = None
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
                            first_envelope_day, best_source_rank, first_seen_at,
                            last_seen_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           ON CONFLICT(observation_id) DO UPDATE SET
                               artifact_id = excluded.artifact_id,
                               best_source_rank = MIN(
                                   best_source_rank, excluded.best_source_rank
                               ),
                               first_envelope_day = MIN(
                                   first_envelope_day, excluded.first_envelope_day
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
                            candidate["envelope_day"],
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
                        first_envelope_day, last_envelope_day)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(disclosure_id) DO UPDATE SET
                           first_envelope_day = MIN(
                               first_envelope_day, excluded.first_envelope_day
                           ),
                           last_envelope_day = MAX(
                               last_envelope_day, excluded.last_envelope_day
                           )""",
                    (
                        disclosure_id,
                        observation_id,
                        candidate["source_provider"],
                        candidate["disclosure_external_id"],
                        candidate["disclosure_snapshot_sha256"],
                        candidate["disclosure_url"],
                        candidate["disclosure_published_at"],
                        candidate["envelope_day"],
                        candidate["envelope_day"],
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
        envelope_day = str(meta["day"])
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
                          snapshot_content_sha256, status, decision
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
                    f"items[{ordinal}] event must be a completed kept envelope"
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
                "envelope_day": envelope_day,
                "source_rank": int(source_row["current_rank"]),
                "day_candidate_count": day_candidate_count,
                "source_triage_run_id": source_triage_run_id,
                "source_input_sha256": str(source_row["input_sha256"]),
                "source_snapshot_content_sha256": str(
                    source_row["snapshot_content_sha256"] or ""
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
                        event_id, envelope_day, source_rank,
                        day_candidate_count, source_triage_run_id,
                        source_input_sha256, source_snapshot_content_sha256,
                        evidence_role, source_published_at, rationale,
                        reviewed_by, reviewed_at, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item["supplement_id"],
                        item["contract"],
                        item["manifest_sha256"],
                        item["artifact_id"],
                        item["event_id"],
                        item["envelope_day"],
                        item["source_rank"],
                        item["day_candidate_count"],
                        item["source_triage_run_id"],
                        item["source_input_sha256"],
                        item["source_snapshot_content_sha256"],
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


def _result(
    *,
    command: str,
    status: str,
    data: Any,
    error: dict[str, Any] | None,
    started: float,
    request_id: str,
) -> dict[str, Any]:
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "command": command,
        "status": status,
        "data": data,
        "error": error,
        "meta": {
            "request_id": request_id,
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
            "timestamp_utc": _now(),
        },
    }


def _print_result(payload: dict[str, Any], *, plain: bool) -> None:
    if not plain:
        print(_canonical_json(payload))
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
    print(
        " ".join(
            (
                "status=ok",
                f"command={payload['command']}",
                f"data={_canonical_json(payload['data'])}",
            )
        )
    )


def _add_output_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--no-input", action="store_true")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true")
    output.add_argument("--plain", action="store_true")


def main(argv: list[str] | None = None) -> int:
    started = time.monotonic()
    request_id = str(uuid.uuid4())
    command = "artifacts"
    parser = sources.JsonArgumentParser(prog="fli artifacts")
    sub = parser.add_subparsers(dest="action", required=True)
    import_parser = sub.add_parser("import-kept", help="Index URLs from kept envelopes.")
    import_parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    import_parser.add_argument("--feed-db", type=Path, default=signal_feed.DEFAULT_FEED_DB)
    import_parser.add_argument("--events-db", type=Path, default=signal_events.DEFAULT_EVENTS_DB)
    import_parser.add_argument("--triage-root", type=Path, default=DEFAULT_TRIAGE_ROOT)
    _add_output_arguments(import_parser)
    supplement_parser = sub.add_parser(
        "import-reviewed-supplements",
        help="Import frozen human-reviewed primary evidence for exact events.",
    )
    supplement_parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    supplement_parser.add_argument("--manifest", type=Path, required=True)
    supplement_parser.add_argument("--triage-db", type=Path, required=True)
    _add_output_arguments(supplement_parser)
    summary_parser = sub.add_parser("summary", help="Summarize the artifact catalog.")
    summary_parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    _add_output_arguments(summary_parser)
    inspect_parser = sub.add_parser("inspect", help="Inspect prioritized artifacts.")
    inspect_parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    inspect_parser.add_argument("--limit", type=int, default=20)
    _add_output_arguments(inspect_parser)
    fetch_parser = sub.add_parser("fetch", help="Fetch a bounded artifact cohort.")
    fetch_parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    fetch_parser.add_argument("--limit", type=int, default=None)
    fetch_parser.add_argument(
        "--artifact-id",
        action="append",
        help=(
            "Fetch exactly this catalog artifact ID; repeat for a frozen cohort "
            "(cannot be combined with --limit)."
        ),
    )
    _add_output_arguments(fetch_parser)
    reader_parser = sub.add_parser(
        "reader-fallback",
        help="Recover eligible native-fetch failures through Jina Reader.",
    )
    reader_parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    _add_output_arguments(reader_parser)
    x_article_parser = sub.add_parser(
        "fetch-x-articles",
        help="Fetch X Article bodies through the dedicated provider adapter.",
    )
    x_article_parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    x_article_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Fetch the first N catalogued X Articles (default: 20).",
    )
    x_article_parser.add_argument(
        "--artifact-id",
        action="append",
        help=(
            "Fetch exactly this catalog artifact ID; repeat for a frozen cohort "
            "(cannot be combined with --limit)."
        ),
    )
    _add_output_arguments(x_article_parser)
    fetch_inspect_parser = sub.add_parser(
        "inspect-fetches", help="Inspect artifact fetch outcomes."
    )
    fetch_inspect_parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    fetch_inspect_parser.add_argument("--fetch-run-id")
    _add_output_arguments(fetch_inspect_parser)
    args = None
    try:
        args = parser.parse_args(argv)
        command = f"artifacts.{args.action}"
        parsed_limit = getattr(args, "limit", None)
        if parsed_limit is not None and parsed_limit <= 0:
            raise ValueError("limit must be greater than zero")
        if args.action == "import-kept":
            data = import_kept_envelopes(
                db_path=args.db,
                feed_db=args.feed_db,
                events_db=args.events_db,
                triage_root=args.triage_root,
            )
        elif args.action == "import-reviewed-supplements":
            data = import_reviewed_supplements(
                db_path=args.db,
                manifest_path=args.manifest,
                triage_db=args.triage_db,
            )
        elif args.action == "fetch":
            from fli import artifact_fetch

            if args.limit is not None and args.artifact_id is not None:
                raise ValueError("--limit cannot be combined with --artifact-id")
            data = artifact_fetch.fetch_cohort(
                db_path=args.db,
                limit=args.limit if args.limit is not None else 30,
                artifact_ids=args.artifact_id,
            )
        elif args.action == "reader-fallback":
            from fli import artifact_fetch

            data = artifact_fetch.recover_with_jina_reader(db_path=args.db)
        elif args.action == "fetch-x-articles":
            from fli import artifact_x_articles

            data = artifact_x_articles.fetch_x_articles(
                db_path=args.db,
                limit=(
                    args.limit
                    if args.limit is not None
                    else (None if args.artifact_id is not None else 20)
                ),
                artifact_ids=args.artifact_id,
            )
        elif args.action == "inspect-fetches":
            from fli import artifact_fetch

            conn = connect(args.db)
            data = artifact_fetch.inspect_fetches(
                conn, fetch_run_id=args.fetch_run_id
            )
            conn.close()
        else:
            conn = connect(args.db)
            if args.action == "summary":
                data = summary(conn)
            else:
                data = inspect_artifacts(conn, limit=args.limit)
            conn.close()
        _print_result(
            _result(
                command=command,
                status="ok",
                data=data,
                error=None,
                started=started,
                request_id=request_id,
            ),
            plain=args.plain,
        )
        return 0
    except sources.SourceCliError as exc:
        error = {
            "code": exc.code,
            "message": exc.message,
            "retryable": exc.retryable,
            "hint": exc.hint,
        }
        exit_code = exc.exit_code
    except (ValueError, FileNotFoundError) as exc:
        error = {
            "code": "E_VALIDATION",
            "message": str(exc),
            "retryable": False,
            "hint": "Check the requested paths, limit, and published source runs.",
        }
        exit_code = 2
    except sqlite3.Error as exc:
        error = {
            "code": "E_STORAGE",
            "message": str(exc),
            "retryable": False,
            "hint": "Inspect the artifact database and rerun its integrity checks.",
        }
        exit_code = 1
    except OSError as exc:
        error = {
            "code": "E_DEPENDENCY",
            "message": str(exc),
            "retryable": True,
            "hint": "Check local paths and network availability, then resume the command.",
        }
        exit_code = 4
    except KeyboardInterrupt:
        error = {
            "code": "E_INTERRUPTED",
            "message": "Artifact operation was interrupted.",
            "retryable": True,
            "hint": "Run the same command again; completed rows are reused.",
        }
        exit_code = 5
    except Exception as exc:  # keep the machine contract intact for unexpected bugs
        error = {
            "code": "E_INTERNAL",
            "message": f"{type(exc).__name__}: {exc}",
            "retryable": False,
            "hint": "Inspect the local traceback in development and fix the implementation.",
        }
        exit_code = 1
    payload = _result(
        command=command,
        status="error",
        data=None,
        error=error,
        started=started,
        request_id=request_id,
    )
    _print_result(payload, plain=bool(args and args.plain))
    if exit_code == 1 and error["code"] == "E_INTERNAL":
        print(error["message"], file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
