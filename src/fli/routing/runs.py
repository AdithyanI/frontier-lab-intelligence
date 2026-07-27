"""Freeze and route ranked Event packets projected from Feed evidence."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import re
import shutil
import sqlite3
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fli.evidence.artifacts import store as artifacts
from fli.registry import classification as entity_kinds
from fli.routing import freshness
from fli.routing import model as routing_model
from fli.scoring import attention


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUN_ROOT = REPO_ROOT / "data" / "derived" / "audience-routing"
DEFAULT_ARTIFACT_DB = artifacts.DEFAULT_DB
DEFAULT_TOP_RANKED = 10
DEFAULT_REFRESH_TOP_RANKED = 100
DEFAULT_REFRESH_DAYS = 9
DEFAULT_REFRESH_WORKERS = 1
DEFAULT_REFRESH_DAY_WORKERS = 1

EXACT_REUSE_META_FIELDS = (
    "day",
    "model",
    "reasoning_effort",
    "prompt_version",
    "prompt_sha256",
    "schema_version",
    "selection_kind",
    "selection_limit",
    "requested_event_id",
)

INCREMENTAL_TELEMETRY_FIELDS = (
    "input_tokens",
    "cached_tokens",
    "cache_write_tokens",
    "output_tokens",
    "reported_cost_count",
)

RUN_SCHEMA = """
CREATE TABLE IF NOT EXISTS run_meta (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    run_id TEXT NOT NULL,
    day TEXT NOT NULL,
    model TEXT NOT NULL,
    reasoning_effort TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    prompt_sha256 TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    rank_version TEXT NOT NULL,
    source_rank_input_sha256 TEXT NOT NULL
        CHECK (length(source_rank_input_sha256) = 64),
    source_event_run_id TEXT NOT NULL,
    source_feed_run_id TEXT NOT NULL,
    source_artifact_db TEXT NOT NULL,
    selection_kind TEXT NOT NULL
        CHECK (selection_kind IN ('top_ranked', 'single_event', 'review_cohort')),
    selection_limit INTEGER,
    requested_event_id TEXT,
    cohort_sha256 TEXT NOT NULL,
    expected_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS routing_item (
    event_id TEXT PRIMARY KEY,
    feed_rank INTEGER NOT NULL,
    root_url TEXT NOT NULL,
    semantic_snapshot_sha256 TEXT NOT NULL,
    packet_json TEXT NOT NULL,
    evidence_sha256 TEXT NOT NULL,
    input_text TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'complete', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    ai_engineering_relevant INTEGER CHECK (ai_engineering_relevant IN (0, 1)),
    ai_engineering_reason TEXT,
    investment_relevant INTEGER CHECK (investment_relevant IN (0, 1)),
    investment_reason TEXT,
    raw_output_text TEXT,
    response_id TEXT,
    response_model TEXT,
    input_tokens INTEGER,
    cached_tokens INTEGER,
    cache_write_tokens INTEGER,
    output_tokens INTEGER,
    reported_cost_usd REAL,
    request_tags_json TEXT,
    error_type TEXT,
    error_message TEXT,
    reused_from_run_id TEXT,
    reused_from_event_id TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_routing_item_status_rank
    ON routing_item(status, feed_rank, event_id);
CREATE INDEX IF NOT EXISTS idx_routing_item_audiences_rank
    ON routing_item(
        ai_engineering_relevant, investment_relevant, feed_rank, event_id
    );
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def default_run_db(run_id: str) -> Path:
    if not run_id or any(
        character
        not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        for character in run_id
    ):
        raise ValueError("run_id may contain only letters, numbers, '-', '_', and '.'")
    return DEFAULT_RUN_ROOT / run_id / "routing.db"


def _stored_cohort_sha256(
    conn: sqlite3.Connection, *, snapshot_key: str = "semantic_snapshot_sha256"
) -> str:
    rows = conn.execute(
        """SELECT event_id, feed_rank, semantic_snapshot_sha256,
                  evidence_sha256, input_sha256
           FROM routing_item ORDER BY feed_rank, event_id"""
    ).fetchall()
    cohort = [
        {
            "event_id": str(row["event_id"]),
            "feed_rank": int(row["feed_rank"]),
            snapshot_key: str(row["semantic_snapshot_sha256"]),
            "evidence_sha256": str(row["evidence_sha256"]),
            "input_sha256": str(row["input_sha256"]),
        }
        for row in rows
    ]
    return _sha256(_canonical_json(cohort))


def migrate_run_storage(path: Path | str) -> bool:
    """Validate current routing storage without upgrading stale lineage."""
    path = Path(path)
    if not path.is_file():
        return False
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 60000")
    try:
        meta_columns = {
            str(row["name"])
            for row in conn.execute("PRAGMA table_info(run_meta)").fetchall()
        }
        columns = {
            str(row["name"])
            for row in conn.execute("PRAGMA table_info(routing_item)").fetchall()
        }
        if (
            "source_rank_input_sha256" not in meta_columns
            or "semantic_snapshot_sha256" not in columns
        ):
            return False
        meta = conn.execute(
            "SELECT cohort_sha256 FROM run_meta WHERE singleton = 1"
        ).fetchone()
        if meta is not None and str(meta["cohort_sha256"]) != _stored_cohort_sha256(conn):
            raise RuntimeError(
                "routing storage cohort hash does not match stored items"
            )
        integrity = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity != "ok":
            raise RuntimeError(f"routing storage integrity check failed: {integrity}")
        return False
    finally:
        conn.close()


def _published_event_source() -> dict[str, str]:
    from fli.evidence import events as signal_events

    path = signal_events.DEFAULT_EVENTS_DB.resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """SELECT run.run_id, run.feed_run_id
               FROM signal_publication AS publication
               JOIN event_run AS run
                 ON run.run_id = publication.event_run_id
               WHERE publication.singleton = 1"""
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ValueError("No Event run is currently published.")
    return {"event_run_id": str(row["run_id"]), "feed_run_id": str(row["feed_run_id"])}


def _current_rank_identities(days: list[str]) -> dict[str, dict[str, str]]:
    """Resolve the exact full-day rank inputs before routing is frozen."""
    from fli.web import events as event_store

    return {
        day: event_store.current_rank_identity(day=day)
        for day in days
    }


def _refresh_days(through: str, days: int) -> list[str]:
    if days < 1 or days > 90:
        raise ValueError("days must be between 1 and 90")
    end = date.fromisoformat(through)
    start = end - timedelta(days=days - 1)
    return [(start + timedelta(days=offset)).isoformat() for offset in range(days)]


def _run_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _refresh_plan(
    *,
    through: str,
    days: int,
    top_ranked: int,
    model: str,
    effort: str,
    source_event_run_id: str,
    rank_identities: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    if top_ranked < 1:
        raise ValueError("top_ranked must be positive")
    source_label = source_event_run_id[:12]
    return [
        {
            "day": day,
            "source_rank_input_sha256": rank_identities[day][
                "rank_input_sha256"
            ],
            "run_id": (
                f"{routing_model.PROMPT_VERSION}-{_run_label(model)}-{day}-"
                f"top{top_ranked}-{_run_label(effort)}-"
                f"{_run_label(attention.DAILY_RANK_VERSION)}-{source_label}-"
                f"{rank_identities[day]['rank_input_sha256'][:12]}"
            ),
        }
        for day in _refresh_days(through, days)
    ]


def _freeze_refresh_day(
    item: dict[str, Any],
    *,
    top_ranked: int,
    artifact_db: Path,
    model: str,
    effort: str,
    expected_event_run_id: str,
    run_root: Path,
) -> float:
    run_db = run_root / str(item["run_id"]) / "routing.db"
    conn = connect_run(run_db)
    try:
        packaging_started = time.monotonic()
        freeze_run(
            conn,
            run_id=str(item["run_id"]),
            day=str(item["day"]),
            top_ranked=top_ranked,
            event_id=None,
            artifact_db=artifact_db,
            model=model,
            effort=effort,
            expected_rank_input_sha256=str(
                item["source_rank_input_sha256"]
            ),
        )
        packaging_duration_ms = round(
            (time.monotonic() - packaging_started) * 1000,
            3,
        )
        meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
        if (
            meta is None
            or str(meta["source_event_run_id"]) != expected_event_run_id
            or str(meta["source_rank_input_sha256"])
            != str(item["source_rank_input_sha256"])
        ):
            raise RuntimeError(
                f"{item['day']} froze a different Event publication; rerun the refresh."
            )
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return packaging_duration_ms
    finally:
        conn.close()


def _execute_refresh_day(
    item: dict[str, Any],
    *,
    workers: int,
    run_root: Path,
    packaging_duration_ms: float,
) -> dict[str, Any]:
    run_db = run_root / str(item["run_id"]) / "routing.db"
    conn = connect_run(run_db)
    try:
        resumed_complete_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM routing_item WHERE status = 'complete'"
            ).fetchone()[0]
        )
        reuse = reuse_previous_results(
            conn,
            target_run_db=run_db,
            run_root=run_root,
        )
        model_requests = int(
            conn.execute(
                "SELECT COUNT(*) FROM routing_item WHERE status != 'complete'"
            ).fetchone()[0]
        )
        telemetry_before = _telemetry_totals(conn)
        if model_requests:
            client = entity_kinds.create_litellm_client()
            if hasattr(client, "with_options"):
                client = client.with_options(max_retries=0, timeout=180.0)
            result = run_pending(conn, client=client, workers=workers)
        else:
            result = summary(conn)
        telemetry_after = _telemetry_totals(conn)
        if int(result["counts"]["failed"] or 0):
            raise RuntimeError(
                f"{item['day']} has {result['counts']['failed']} failed routing items; "
                "rerun the same refresh to retry them."
            )
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return {
            **result,
            "packaging_duration_ms": packaging_duration_ms,
            "resumed_complete_count": resumed_complete_count,
            "reused_exact_count": reuse["reused_exact_count"],
            "reuse_source_run_ids": reuse["source_run_ids"],
            "model_requests": model_requests,
            "incremental_telemetry": _telemetry_delta(
                telemetry_after,
                telemetry_before,
            ),
        }
    finally:
        conn.close()


def refresh_all_days(
    *,
    through: str,
    days: int = DEFAULT_REFRESH_DAYS,
    top_ranked: int = DEFAULT_REFRESH_TOP_RANKED,
    artifact_db: Path = DEFAULT_ARTIFACT_DB,
    model: str = routing_model.DEFAULT_MODEL,
    effort: str = routing_model.DEFAULT_REASONING_EFFORT,
    workers: int = DEFAULT_REFRESH_WORKERS,
    day_workers: int = DEFAULT_REFRESH_DAY_WORKERS,
    replace: bool = False,
    dry_run: bool = False,
    run_root: Path = DEFAULT_RUN_ROOT,
) -> dict[str, Any]:
    """Route one top-ranked cohort for every day against one publication.

    Matching deterministic run IDs resume in place. Older live routing runs are
    pruned only after every requested day completes and the Event publication
    is proven unchanged.
    """
    if workers < 1 or workers > 64:
        raise ValueError("workers must be between 1 and 64")
    if day_workers < 1 or day_workers > 31:
        raise ValueError("day_workers must be between 1 and 31")
    source = _published_event_source()
    refresh_days = _refresh_days(through, days)
    rank_identities = _current_rank_identities(refresh_days)
    if any(
        identity["event_run_id"] != source["event_run_id"]
        or identity["feed_run_id"] != source["feed_run_id"]
        for identity in rank_identities.values()
    ):
        raise RuntimeError(
            "The current daily rank is not bound to the published Event source."
        )
    plan = _refresh_plan(
        through=through,
        days=days,
        top_ranked=top_ranked,
        model=model,
        effort=effort,
        source_event_run_id=source["event_run_id"],
        rank_identities=rank_identities,
    )
    base = {
        "source_event_run_id": source["event_run_id"],
        "source_feed_run_id": source["feed_run_id"],
        "through": through,
        "days": days,
        "top_ranked": top_ranked,
        "model": model,
        "reasoning_effort": effort,
        "rank_version": attention.DAILY_RANK_VERSION,
        "workers_per_day": workers,
        "day_workers": min(day_workers, len(plan)),
        "replace": replace,
        "reuse_policy": "exact-event-evidence-input",
        "plan": [
            {
                **item,
                "run_db": str(run_root / str(item["run_id"]) / "routing.db"),
            }
            for item in plan
        ],
    }
    if dry_run:
        return {**base, "dry_run": True, "will_call_model": False}

    run_root.mkdir(parents=True, exist_ok=True)
    packaging_by_day: dict[str, float] = {}
    for item in plan:
        packaging_by_day[str(item["day"])] = _freeze_refresh_day(
            item,
            top_ranked=top_ranked,
            artifact_db=artifact_db,
            model=model,
            effort=effort,
            expected_event_run_id=source["event_run_id"],
            run_root=run_root,
        )

    if (
        _published_event_source() != source
        or _current_rank_identities(refresh_days) != rank_identities
    ):
        raise RuntimeError(
            "The published Event run or daily rank inputs changed while audience "
            "packets were frozen; model calls were not started. Rerun the refresh."
        )

    results: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=min(day_workers, len(plan))) as executor:
        futures = {
            executor.submit(
                _execute_refresh_day,
                item,
                workers=workers,
                run_root=run_root,
                packaging_duration_ms=packaging_by_day[str(item["day"])],
            ): item
            for item in plan
        }
        for future in as_completed(futures):
            item = futures[future]
            try:
                results[str(item["day"])] = future.result()
            except Exception as exc:
                errors.append(f"{item['day']}: {type(exc).__name__}: {exc}")
    if errors:
        raise RuntimeError("Audience refresh did not complete: " + " | ".join(errors))

    current_source = _published_event_source()
    if (
        current_source != source
        or _current_rank_identities(refresh_days) != rank_identities
    ):
        raise RuntimeError(
            "The published Event run or daily rank inputs changed during audience "
            "routing; completed runs were retained, but old runs were not removed. "
            "Rerun the refresh."
        )

    keep = {str(item["run_id"]) for item in plan}
    pruned: list[str] = []
    if replace:
        for path in sorted(run_root.iterdir()):
            if path.is_dir() and path.name not in keep:
                shutil.rmtree(path)
                pruned.append(path.name)

    count_fields = (
        "total",
        "complete",
        "failed",
        "ai_engineering_only",
        "investment_only",
        "both",
        "neither",
        "input_tokens",
        "cached_tokens",
        "cache_write_tokens",
        "output_tokens",
        "reported_cost_count",
        "cache_eligible_requests",
        "cache_hit_requests",
        "reused_exact_count",
    )
    counts = {
        field: sum(int(result["counts"].get(field) or 0) for result in results.values())
        for field in count_fields
    }
    counts["reported_cost_usd"] = round(
        sum(float(result["counts"].get("reported_cost_usd") or 0) for result in results.values()),
        6,
    )
    counts["cache_read_ratio"] = (
        round(counts["cached_tokens"] / counts["input_tokens"], 6)
        if counts["input_tokens"]
        else 0.0
    )
    model_requests = sum(
        int(result.get("model_requests") or 0) for result in results.values()
    )
    resumed_complete_count = sum(
        int(result.get("resumed_complete_count") or 0)
        for result in results.values()
    )
    reused_exact_count = sum(
        int(result.get("reused_exact_count") or 0)
        for result in results.values()
    )
    incremental_telemetry = {
        field: sum(
            int((result.get("incremental_telemetry") or {}).get(field) or 0)
            for result in results.values()
        )
        for field in INCREMENTAL_TELEMETRY_FIELDS
    }
    incremental_telemetry["reported_cost_usd"] = round(
        sum(
            float(
                (result.get("incremental_telemetry") or {}).get(
                    "reported_cost_usd"
                )
                or 0
            )
            for result in results.values()
        ),
        6,
    )
    return {
        **base,
        "dry_run": False,
        "resumed_complete_count": resumed_complete_count,
        "reused_exact_count": reused_exact_count,
        "days_with_exact_reuse": sum(
            int(result.get("reused_exact_count") or 0) > 0
            for result in results.values()
        ),
        "will_call_model": model_requests > 0,
        "model_requests": model_requests,
        "incremental_telemetry": incremental_telemetry,
        "packaging": {
            "total_duration_ms": round(
                sum(
                    float(result.get("packaging_duration_ms") or 0)
                    for result in results.values()
                ),
                3,
            ),
            "max_day_duration_ms": round(
                max(
                    (
                        float(result.get("packaging_duration_ms") or 0)
                        for result in results.values()
                    ),
                    default=0.0,
                ),
                3,
            ),
        },
        "counts": counts,
        "runs": [results[day] for day in sorted(results)],
        "pruned_runs": pruned,
    }


def connect_run(path: Path | str) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.executescript(RUN_SCHEMA)
    meta_columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(run_meta)").fetchall()
    }
    if "source_rank_input_sha256" not in meta_columns:
        conn.close()
        raise RuntimeError(
            "routing database predates rank-input lineage; create a new run"
        )
    conn.execute("PRAGMA user_version = 4")
    conn.commit()
    return conn


def _open_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(path)
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _x_url(author: str | None, post_id: str) -> str:
    handle = (author or "i").lstrip("@") or "i"
    return f"https://x.com/{handle}/status/{post_id}"


def _source_payload(source: routing_model.EvidenceSource) -> dict[str, Any]:
    return {
        "source_type": source.source_type,
        "source_id": source.source_id,
        "url": source.url,
        "text": source.text,
        "author": source.author,
        "title": source.title,
        "relation": source.relation,
        "source_sha256": source.source_sha256,
        "section_ordinal": source.section_ordinal,
        "source_char_start": source.source_char_start,
        "source_char_end": source.source_char_end,
    }


def _source_from_payload(payload: dict[str, Any]) -> routing_model.EvidenceSource:
    return routing_model.EvidenceSource(**payload)


def _packet_payload(packet: routing_model.RoutingPacket) -> dict[str, Any]:
    return {
        "event_id": packet.event_id,
        "day": packet.day,
        "sources": [_source_payload(source) for source in packet.sources],
    }


def _packet_from_payload(payload: dict[str, Any]) -> routing_model.RoutingPacket:
    return routing_model.RoutingPacket(
        event_id=str(payload["event_id"]),
        day=str(payload["day"]),
        sources=tuple(
            _source_from_payload(dict(source)) for source in payload["sources"]
        ),
    )


def _x_source(post: dict[str, Any], *, relation: str) -> routing_model.EvidenceSource:
    post_id = str(post["post_id"])
    author = str(post.get("author") or "") or None
    return routing_model.EvidenceSource(
        source_type="x_post",
        source_id=post_id,
        url=_x_url(author, post_id),
        text=str(post.get("text") or ""),
        author=author,
        relation=relation,
    )


def _artifact_sources(
    conn: sqlite3.Connection,
    *,
    event_id: str,
    post_authors: dict[str, str],
    primary_author: str,
    eligible_source_ids: set[str] | None = None,
) -> list[routing_model.EvidenceSource]:
    """Load full accepted primary-author artifacts without old Insight state."""
    rows = conn.execute(
        """SELECT DISTINCT candidate.artifact_id, candidate.relation,
                          candidate.source_external_id,
                          candidate.source_snapshot_sha256,
                          artifact.canonical_url, artifact.title,
                          latest.text_snapshot_ref, latest.text_sha256
           FROM artifact_import_candidate AS candidate
           JOIN artifact_import_run AS import_run USING (import_run_id)
           JOIN artifact AS artifact USING (artifact_id)
           JOIN artifact_fetch AS latest ON latest.fetch_id = (
               SELECT fetch.fetch_id
               FROM artifact_fetch AS fetch
               WHERE fetch.artifact_id = candidate.artifact_id
                 AND fetch.status = 'success'
                 AND fetch.text_snapshot_ref IS NOT NULL
               ORDER BY fetch.completed_at DESC, fetch.fetch_id DESC
               LIMIT 1
           )
           WHERE candidate.event_id = ?
             AND candidate.decision = 'accepted'
             AND import_run.selection_policy = ?
           ORDER BY candidate.artifact_id,
                    CASE candidate.relation
                        WHEN 'self_publishes' THEN 0 ELSE 1
                    END,
                    candidate.source_external_id,
                    candidate.source_snapshot_sha256""",
        (event_id, artifacts.PRIMARY_AUTHOR_SELECTION_POLICY),
    ).fetchall()
    sources: list[routing_model.EvidenceSource] = []
    seen_artifact_ids: set[str] = set()
    for row in rows:
        source_external_id = str(row["source_external_id"])
        if (
            eligible_source_ids is not None
            and source_external_id not in eligible_source_ids
        ):
            continue
        artifact_id = str(row["artifact_id"])
        if artifact_id in seen_artifact_ids:
            continue
        seen_artifact_ids.add(artifact_id)
        snapshot = REPO_ROOT / str(row["text_snapshot_ref"])
        if not snapshot.is_file():
            raise FileNotFoundError(snapshot)
        text = snapshot.read_text()
        relation = str(row["relation"])
        author = (
            post_authors.get(source_external_id, primary_author)
            if relation == "self_publishes"
            else None
        )
        sources.append(
            routing_model.EvidenceSource(
                source_type="artifact",
                source_id=artifact_id,
                url=str(row["canonical_url"]),
                title=str(row["title"] or "") or None,
                text=text,
                author=author,
                relation=(
                    "self_published_artifact"
                    if relation == "self_publishes"
                    else "linked_artifact"
                ),
                source_sha256=str(row["text_sha256"] or _sha256(text)),
            )
        )
    return sources


def packet_from_event(
    item: dict[str, Any],
    *,
    day: str,
    artifact_conn: sqlite3.Connection,
) -> routing_model.RoutingPacket | None:
    root_item = dict(item["root"])
    root = {
        "post_id": str(root_item["post_id"]),
        "author": "@" + str(root_item["author"]["handle"]),
        "text": str(root_item.get("text") or ""),
        "published_at": str(root_item.get("published_at") or ""),
    }
    x_posts: list[dict[str, Any]] = []
    if freshness.is_current(
        published_at=root["published_at"], evaluation_day=day
    ):
        x_posts.append({**root, "relation": "root"})
    root_is_current = bool(x_posts)
    for evidence in item.get("evidence") or []:
        if (
            not evidence.get("same_author_as_root")
            or str(evidence.get("relationship") or "related") == "retweet"
        ):
            continue
        post = {
            "post_id": str(evidence["post_id"]),
            "author": "@" + str(evidence["author"]["handle"]),
            "text": str(evidence.get("text") or ""),
            "published_at": str(evidence.get("published_at") or ""),
        }
        if freshness.is_current(
            published_at=post["published_at"], evaluation_day=day
        ):
            x_posts.append({**post, "relation": "same_author_continuation"})
    if not x_posts:
        return None
    if not root_is_current:
        x_posts[0]["relation"] = "root"
    sources = [
        _x_source(post, relation=str(post["relation"])) for post in x_posts
    ]
    post_authors = {
        str(post["post_id"]): str(post.get("author") or "") for post in x_posts
    }
    eligible_source_ids = set(post_authors)
    sources.extend(
        _artifact_sources(
            artifact_conn,
            event_id=str(item["event_id"]),
            post_authors=post_authors,
            primary_author=str(root.get("author") or ""),
            eligible_source_ids=eligible_source_ids,
        )
    )
    return routing_model.RoutingPacket(
        event_id=str(item["event_id"]),
        day=day,
        sources=tuple(sources),
    )


def freeze_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    day: str,
    top_ranked: int,
    event_id: str | None,
    artifact_db: Path,
    model: str,
    effort: str,
    expected_rank_input_sha256: str | None = None,
) -> int:
    if top_ranked < 1:
        raise ValueError("top_ranked must be positive")
    from fli.web import events as event_store

    payload = event_store.events_payload(
        day=day,
        lane="all",
        sort="rank",
        query="",
        event_id=event_id or "",
        routing_filter="all",
        limit=1 if event_id else top_ranked,
        offset=0,
    )
    if not payload.get("available"):
        raise ValueError(str(payload.get("reason") or "Evidence is unavailable"))
    source_run = dict(payload.get("run") or {})
    rank_contract = dict(payload.get("rank_contract") or {})
    source_rank_input_sha256 = str(
        rank_contract.get("input_sha256") or ""
    )
    if not source_run.get("run_id") or not source_run.get("feed_run_id"):
        raise ValueError("Evidence projection is missing run provenance")
    if not source_rank_input_sha256:
        raise ValueError("Evidence projection is missing rank-input provenance")
    if (
        expected_rank_input_sha256 is not None
        and source_rank_input_sha256 != expected_rank_input_sha256
    ):
        raise RuntimeError(
            "The daily rank inputs changed before audience packets were frozen."
        )
    items = list(payload.get("items") or [])
    if event_id:
        items = [item for item in items if item["event_id"] == event_id]
    else:
        items = items[:top_ranked]
    if not items:
        raise ValueError("Evidence projection has no matching Events")
    missing_hashes = [
        str(item["event_id"])
        for item in items
        if not item.get("semantic_snapshot_sha256")
    ]
    if missing_hashes:
        raise ValueError(
            "Feed Events are missing snapshot hashes: "
            + ", ".join(missing_hashes)
        )

    artifact_conn = _open_readonly(artifact_db)
    try:
        frozen = [
            (item, packet)
            for item in items
            if (
                packet := packet_from_event(
                    item,
                    day=day,
                    artifact_conn=artifact_conn,
                )
            )
            is not None
        ]
    finally:
        artifact_conn.close()

    if not frozen:
        raise ValueError(
            f"Evidence projection has no first-party X sources within "
            f"{freshness.MAX_SOURCE_AGE_DAYS} days of {day}"
        )
    items = [item for item, _packet in frozen]
    packets = [packet for _item, packet in frozen]

    rendered_inputs = [routing_model.render_input(packet) for packet in packets]

    cohort = [
        {
            "event_id": packet.event_id,
            "feed_rank": int(item["daily_rank"]),
            "semantic_snapshot_sha256": str(item["semantic_snapshot_sha256"]),
            "evidence_sha256": packet.evidence_sha256,
            "input_sha256": _sha256(input_text),
        }
        for item, packet, input_text in zip(
            items, packets, rendered_inputs, strict=True
        )
    ]
    cohort_sha256 = _sha256(_canonical_json(cohort))
    existing = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    expected = {
        "run_id": run_id,
        "day": day,
        "model": model,
        "reasoning_effort": effort,
        "prompt_version": routing_model.PROMPT_VERSION,
        "prompt_sha256": routing_model.prompt_sha256(),
        "schema_version": routing_model.SCHEMA_VERSION,
        "rank_version": attention.DAILY_RANK_VERSION,
        "source_rank_input_sha256": source_rank_input_sha256,
        "source_event_run_id": str(source_run["run_id"]),
        "source_feed_run_id": str(source_run["feed_run_id"]),
        "source_artifact_db": _display_path(artifact_db),
        "selection_kind": "single_event" if event_id else "top_ranked",
        "selection_limit": None if event_id else top_ranked,
        "requested_event_id": event_id,
        "cohort_sha256": cohort_sha256,
        "expected_count": len(packets),
    }
    if existing is not None:
        mismatches = [key for key, value in expected.items() if existing[key] != value]
        if mismatches:
            raise ValueError(
                "run database does not match the frozen request: "
                + ", ".join(mismatches)
            )
        return int(existing["expected_count"])

    now = _now()
    with conn:
        conn.execute(
            """INSERT INTO run_meta
               (singleton, run_id, day, model, reasoning_effort,
                prompt_version, prompt_sha256, schema_version,
                rank_version, source_rank_input_sha256,
                source_event_run_id, source_feed_run_id, source_artifact_db,
                selection_kind, selection_limit, requested_event_id,
                cohort_sha256, expected_count,
                created_at, updated_at)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                expected["run_id"], expected["day"], expected["model"],
                expected["reasoning_effort"], expected["prompt_version"],
                expected["prompt_sha256"], expected["schema_version"],
                expected["rank_version"],
                expected["source_rank_input_sha256"],
                expected["source_event_run_id"], expected["source_feed_run_id"],
                expected["source_artifact_db"], expected["selection_kind"],
                expected["selection_limit"],
                expected["requested_event_id"], expected["cohort_sha256"],
                expected["expected_count"], now, now,
            ),
        )
        conn.executemany(
            """INSERT INTO routing_item
               (event_id, feed_rank, root_url, semantic_snapshot_sha256,
                packet_json, evidence_sha256, input_text, input_sha256,
                updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    packet.event_id,
                    int(item["daily_rank"]),
                    next(
                        source.url
                        for source in packet.sources
                        if source.relation == "root"
                    ),
                    str(item["semantic_snapshot_sha256"]),
                    _canonical_json(_packet_payload(packet)),
                    packet.evidence_sha256,
                    input_text,
                    _sha256(input_text),
                    now,
                )
                for item, packet, input_text in zip(
                    items, packets, rendered_inputs, strict=True
                )
            ],
        )
    return len(packets)


def summary(conn: sqlite3.Connection) -> dict[str, Any]:
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("run database has not been prepared")
    counts = dict(
        conn.execute(
            """SELECT COUNT(*) AS total,
                      SUM(status = 'pending') AS pending,
                      SUM(status = 'complete') AS complete,
                      SUM(status = 'failed') AS failed,
                      SUM(ai_engineering_relevant = 1 AND investment_relevant = 0)
                          AS ai_engineering_only,
                      SUM(ai_engineering_relevant = 0 AND investment_relevant = 1)
                          AS investment_only,
                      SUM(ai_engineering_relevant = 1 AND investment_relevant = 1)
                          AS both,
                      SUM(ai_engineering_relevant = 0 AND investment_relevant = 0)
                          AS neither,
                      SUM(COALESCE(input_tokens, 0)) AS input_tokens,
                      SUM(COALESCE(cached_tokens, 0)) AS cached_tokens,
                      SUM(COALESCE(cache_write_tokens, 0)) AS cache_write_tokens,
                      SUM(COALESCE(output_tokens, 0)) AS output_tokens,
                      SUM(COALESCE(reported_cost_usd, 0)) AS reported_cost_usd,
                      SUM(reported_cost_usd IS NOT NULL) AS reported_cost_count,
                      SUM(COALESCE(input_tokens, 0) >= 1024) AS cache_eligible_requests,
                      SUM(COALESCE(cached_tokens, 0) > 0) AS cache_hit_requests,
                      SUM(reused_from_run_id IS NOT NULL) AS reused_exact_count
               FROM routing_item"""
        ).fetchone()
    )
    input_tokens = int(counts["input_tokens"] or 0)
    counts["cache_read_ratio"] = (
        round(int(counts["cached_tokens"] or 0) / input_tokens, 6)
        if input_tokens
        else 0.0
    )
    return {"run": dict(meta), "counts": counts}


def _telemetry_totals(conn: sqlite3.Connection) -> dict[str, int | float]:
    row = conn.execute(
        """SELECT SUM(COALESCE(input_tokens, 0)) AS input_tokens,
                  SUM(COALESCE(cached_tokens, 0)) AS cached_tokens,
                  SUM(COALESCE(cache_write_tokens, 0)) AS cache_write_tokens,
                  SUM(COALESCE(output_tokens, 0)) AS output_tokens,
                  SUM(COALESCE(reported_cost_usd, 0)) AS reported_cost_usd,
                  SUM(reported_cost_usd IS NOT NULL) AS reported_cost_count
           FROM routing_item"""
    ).fetchone()
    return {
        field: int(row[field] or 0)
        for field in INCREMENTAL_TELEMETRY_FIELDS
    } | {"reported_cost_usd": float(row["reported_cost_usd"] or 0)}


def _telemetry_delta(
    after: dict[str, int | float],
    before: dict[str, int | float],
) -> dict[str, int | float]:
    return {
        field: int(after[field]) - int(before[field])
        for field in INCREMENTAL_TELEMETRY_FIELDS
    } | {
        "reported_cost_usd": round(
            float(after["reported_cost_usd"])
            - float(before["reported_cost_usd"]),
            12,
        )
    }


def reuse_exact_results(
    target: sqlite3.Connection,
    source: sqlite3.Connection,
) -> int:
    """Copy exact judgments across immutable publications with compatible contracts.

    Event and Feed run IDs, cohort size, rank, and semantic snapshot metadata may
    change when a later global publication is built. They do not invalidate a
    completed audience judgment when the same Event has identical frozen
    evidence and identical rendered model input under the same model contract.
    """
    source_meta = source.execute(
        "SELECT * FROM run_meta WHERE singleton = 1"
    ).fetchone()
    target_meta = target.execute(
        "SELECT * FROM run_meta WHERE singleton = 1"
    ).fetchone()
    if source_meta is None or target_meta is None:
        raise ValueError("source and target run databases must both be frozen")
    for key in EXACT_REUSE_META_FIELDS:
        if source_meta[key] != target_meta[key]:
            raise ValueError(f"source and target run metadata differ: {key}")

    source_rows = {
        (
            str(row["event_id"]),
            str(row["evidence_sha256"]),
            str(row["input_sha256"]),
        ): row
        for row in source.execute(
            "SELECT * FROM routing_item WHERE status = 'complete'"
        ).fetchall()
    }
    reusable = []
    for row in target.execute(
        """SELECT event_id, evidence_sha256, input_sha256
           FROM routing_item WHERE status != 'complete'"""
    ).fetchall():
        source_row = source_rows.get(
            (
                str(row["event_id"]),
                str(row["evidence_sha256"]),
                str(row["input_sha256"]),
            )
        )
        if source_row is not None:
            reusable.append(source_row)
    if not reusable:
        return 0

    now = _now()
    with target:
        target.executemany(
            """UPDATE routing_item
               SET status = 'complete', attempts = 0,
                   ai_engineering_relevant = ?, ai_engineering_reason = ?,
                   investment_relevant = ?, investment_reason = ?,
                   raw_output_text = ?, response_id = ?, response_model = ?,
                   input_tokens = ?, cached_tokens = ?, cache_write_tokens = ?,
                   output_tokens = ?, reported_cost_usd = ?,
                   request_tags_json = ?, error_type = NULL,
                   error_message = NULL, reused_from_run_id = ?,
                   reused_from_event_id = ?, completed_at = ?, updated_at = ?
               WHERE event_id = ? AND input_sha256 = ?
                 AND status != 'complete'""",
            [
                (
                    row["ai_engineering_relevant"],
                    row["ai_engineering_reason"],
                    row["investment_relevant"],
                    row["investment_reason"],
                    row["raw_output_text"],
                    row["response_id"],
                    row["response_model"],
                    row["input_tokens"],
                    row["cached_tokens"],
                    row["cache_write_tokens"],
                    row["output_tokens"],
                    row["reported_cost_usd"],
                    row["request_tags_json"],
                    str(source_meta["run_id"]),
                    str(row["event_id"]),
                    row["completed_at"],
                    now,
                    row["event_id"],
                    row["input_sha256"],
                )
                for row in reusable
            ],
        )
        target.execute(
            "UPDATE run_meta SET updated_at = ? WHERE singleton = 1",
            (now,),
        )
    return len(reusable)


def _complete_reuse_candidates(
    target: sqlite3.Connection,
    *,
    target_run_db: Path,
    run_root: Path,
) -> list[Path]:
    """Return newest complete compatible predecessor runs for one target."""
    target_meta = target.execute(
        "SELECT * FROM run_meta WHERE singleton = 1"
    ).fetchone()
    if target_meta is None:
        raise ValueError("target run database has not been prepared")

    candidates: list[tuple[str, str, Path]] = []
    target_path = target_run_db.resolve()
    for path in sorted(run_root.glob("*/routing.db")):
        if path.resolve() == target_path:
            continue
        source = None
        try:
            source = _open_readonly(path)
            source_meta = source.execute(
                "SELECT * FROM run_meta WHERE singleton = 1"
            ).fetchone()
            if source_meta is None or any(
                source_meta[key] != target_meta[key]
                for key in EXACT_REUSE_META_FIELDS
            ):
                continue
            counts = source.execute(
                """SELECT COUNT(*) AS total,
                          SUM(status = 'complete') AS complete
                   FROM routing_item"""
            ).fetchone()
            expected = int(source_meta["expected_count"])
            if (
                int(counts["total"] or 0) != expected
                or int(counts["complete"] or 0) != expected
            ):
                continue
            candidates.append(
                (
                    str(source_meta["updated_at"]),
                    str(source_meta["run_id"]),
                    path,
                )
            )
        except (OSError, sqlite3.Error):
            continue
        finally:
            if source is not None:
                source.close()
    return [path for _updated, _run_id, path in sorted(candidates, reverse=True)]


def reuse_previous_results(
    target: sqlite3.Connection,
    *,
    target_run_db: Path,
    run_root: Path,
) -> dict[str, Any]:
    """Reuse exact completed rows from prior same-day publication snapshots."""
    reused_exact_count = 0
    source_run_ids: list[str] = []
    for path in _complete_reuse_candidates(
        target,
        target_run_db=target_run_db,
        run_root=run_root,
    ):
        source = _open_readonly(path)
        try:
            source_meta = source.execute(
                "SELECT run_id FROM run_meta WHERE singleton = 1"
            ).fetchone()
            reused = reuse_exact_results(target, source)
            if reused:
                reused_exact_count += reused
                source_run_ids.append(str(source_meta["run_id"]))
            pending = int(
                target.execute(
                    "SELECT COUNT(*) FROM routing_item WHERE status != 'complete'"
                ).fetchone()[0]
            )
            if pending == 0:
                break
        finally:
            source.close()
    return {
        "reused_exact_count": reused_exact_count,
        "source_run_ids": source_run_ids,
    }


def refresh_run_packets(
    *,
    source_run_db: Path,
    target_run_db: Path,
    run_id: str,
    artifact_db: Path,
    client: Any,
    workers: int = 1,
) -> dict[str, Any]:
    """Freeze a successor run and evaluate only packets whose input changed."""
    if source_run_db.resolve() == target_run_db.resolve():
        raise ValueError("target run database must differ from source run database")
    source = _open_readonly(source_run_db)
    try:
        source_meta = source.execute(
            "SELECT * FROM run_meta WHERE singleton = 1"
        ).fetchone()
        if source_meta is None:
            raise ValueError("source run database has not been prepared")
        if str(source_meta["selection_kind"]) != "top_ranked":
            raise ValueError("selective refresh requires a top_ranked source run")
        complete_count = int(
            source.execute(
                "SELECT COUNT(*) FROM routing_item WHERE status = 'complete'"
            ).fetchone()[0]
        )
        if complete_count != int(source_meta["expected_count"]):
            raise ValueError("source run must be complete before selective refresh")

        target = connect_run(target_run_db)
        try:
            freeze_run(
                target,
                run_id=run_id,
                day=str(source_meta["day"]),
                top_ranked=int(source_meta["selection_limit"]),
                event_id=None,
                artifact_db=artifact_db,
                model=str(source_meta["model"]),
                effort=str(source_meta["reasoning_effort"]),
            )
            reused_count = reuse_exact_results(target, source)
            model_requests = int(
                target.execute(
                    "SELECT COUNT(*) FROM routing_item WHERE status != 'complete'"
                ).fetchone()[0]
            )
            telemetry_before = _telemetry_totals(target)
            result = (
                run_pending(target, client=client, workers=workers)
                if model_requests
                else summary(target)
            )
            telemetry_after = _telemetry_totals(target)
            target.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            target.close()
    finally:
        source.close()
    return {
        **result,
        "source_run_id": str(source_meta["run_id"]),
        "reused_exact_count": reused_count,
        "model_requests": model_requests,
        "incremental_telemetry": _telemetry_delta(
            telemetry_after,
            telemetry_before,
        ),
    }


def run_pending(
    conn: sqlite3.Connection,
    *,
    client: Any,
    workers: int = 1,
) -> dict[str, Any]:
    if workers < 1:
        raise ValueError("workers must be at least 1")
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("run database has not been prepared")
    rows = conn.execute(
        """SELECT * FROM routing_item
           WHERE status != 'complete'
           ORDER BY feed_rank, event_id"""
    ).fetchall()
    if not rows:
        return summary(conn)

    def evaluate(row: sqlite3.Row):
        packet = _packet_from_payload(json.loads(str(row["packet_json"])))
        try:
            return row, routing_model.evaluate_one(
                client,
                packet,
                run=str(meta["run_id"]),
                model=str(meta["model"]),
                effort=str(meta["reasoning_effort"]),
            ), None
        except Exception as exc:
            return row, None, exc

    if workers == 1:
        evaluations = map(evaluate, rows)
    else:
        executor = ThreadPoolExecutor(max_workers=min(workers, len(rows)))
        futures = [executor.submit(evaluate, row) for row in rows]
        evaluations = (future.result() for future in as_completed(futures))

    try:
        for processed, (row, result, error) in enumerate(evaluations, start=1):
            now = _now()
            if result is not None:
                with conn:
                    conn.execute(
                        """UPDATE routing_item
                           SET status = 'complete', attempts = attempts + 1,
                               ai_engineering_relevant = ?,
                               ai_engineering_reason = ?,
                               investment_relevant = ?, investment_reason = ?,
                               raw_output_text = ?, response_id = ?,
                               response_model = ?, input_tokens = ?,
                               cached_tokens = ?, cache_write_tokens = ?,
                               output_tokens = ?, reported_cost_usd = ?,
                               request_tags_json = ?, error_type = NULL,
                               error_message = NULL, completed_at = ?, updated_at = ?
                           WHERE event_id = ?""",
                        (
                            int(result["ai_engineering"]["relevant"]),
                            result["ai_engineering"]["reason"],
                            int(result["investment"]["relevant"]),
                            result["investment"]["reason"],
                            result["raw_output_text"], result["response_id"],
                            result["response_model"], result["input_tokens"],
                            result["cached_tokens"], result["cache_write_tokens"],
                            result["output_tokens"], result["reported_cost_usd"],
                            _canonical_json(result["request_tags"]), now, now,
                            row["event_id"],
                        ),
                    )
                status = "complete"
            else:
                assert error is not None
                with conn:
                    conn.execute(
                        """UPDATE routing_item
                           SET status = 'failed', attempts = attempts + 1,
                               error_type = ?, error_message = ?, updated_at = ?
                           WHERE event_id = ?""",
                        (type(error).__name__, str(error), now, row["event_id"]),
                    )
                status = "failed"
            print(
                _canonical_json(
                    {
                        "event_id": row["event_id"],
                        "rank": row["feed_rank"],
                        "status": status,
                        "processed": processed,
                        "pending_batch": len(rows),
                    }
                ),
                file=sys.stderr,
                flush=True,
            )
    finally:
        if workers > 1:
            executor.shutdown(wait=True)
    return summary(conn)


def inspect_item(conn: sqlite3.Connection, event_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM routing_item WHERE event_id = ?", (event_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"event is not in this run: {event_id}")
    return dict(row)


def _result(command: str, data: Any) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "command": command,
        "status": "ok",
        "data": data,
        "error": None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fli audience-routing")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run", help="Route ranked Evidence directly.")
    run_parser.add_argument("--run-id", required=True)
    run_parser.add_argument("--run-db", type=Path)
    run_parser.add_argument("--day", required=True)
    run_parser.add_argument("--top-ranked", type=int, default=DEFAULT_TOP_RANKED)
    run_parser.add_argument("--event-id")
    run_parser.add_argument("--artifact-db", type=Path, default=DEFAULT_ARTIFACT_DB)
    run_parser.add_argument("--model", default=routing_model.DEFAULT_MODEL)
    run_parser.add_argument(
        "--reasoning-effort", default=routing_model.DEFAULT_REASONING_EFFORT
    )
    run_parser.add_argument("--workers", type=int, default=1)
    run_parser.add_argument("--dry-run", action="store_true")
    summary_parser = sub.add_parser("summary", help="Inspect a frozen run.")
    summary_parser.add_argument("--run-db", type=Path, required=True)
    item_parser = sub.add_parser("inspect-item", help="Inspect one exact result.")
    item_parser.add_argument("--run-db", type=Path, required=True)
    item_parser.add_argument("--event-id", required=True)
    refresh_parser = sub.add_parser(
        "refresh",
        help="Route the top-ranked cohort for every day against one publication.",
    )
    refresh_parser.add_argument("--through", required=True)
    refresh_parser.add_argument("--days", type=int, default=DEFAULT_REFRESH_DAYS)
    refresh_parser.add_argument(
        "--top-ranked", type=int, default=DEFAULT_REFRESH_TOP_RANKED
    )
    refresh_parser.add_argument(
        "--artifact-db", type=Path, default=DEFAULT_ARTIFACT_DB
    )
    refresh_parser.add_argument("--model", default=routing_model.DEFAULT_MODEL)
    refresh_parser.add_argument(
        "--reasoning-effort", default=routing_model.DEFAULT_REASONING_EFFORT
    )
    refresh_parser.add_argument(
        "--workers", type=int, default=DEFAULT_REFRESH_WORKERS
    )
    refresh_parser.add_argument(
        "--day-workers", type=int, default=DEFAULT_REFRESH_DAY_WORKERS
    )
    refresh_parser.add_argument(
        "--replace",
        action="store_true",
        help="Remove older routing runs only after the full refresh succeeds.",
    )
    refresh_parser.add_argument("--dry-run", action="store_true")
    refresh_run_parser = sub.add_parser(
        "refresh-run",
        help="Freeze a successor run and reroute only changed exact inputs.",
    )
    refresh_run_parser.add_argument("--source-run-db", type=Path, required=True)
    refresh_run_parser.add_argument("--run-id", required=True)
    refresh_run_parser.add_argument("--run-db", type=Path)
    refresh_run_parser.add_argument(
        "--artifact-db", type=Path, default=DEFAULT_ARTIFACT_DB
    )
    refresh_run_parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args(argv)
    started = time.monotonic()
    try:
        if args.action == "run" and args.dry_run:
            data = {
                "run_id": args.run_id,
                "run_db": str(args.run_db or default_run_db(args.run_id)),
                "day": args.day,
                "top_ranked": args.top_ranked,
                "event_id": args.event_id,
                "artifact_db": str(args.artifact_db),
                "model": args.model,
                "reasoning_effort": args.reasoning_effort,
                "workers": args.workers,
                "prompt_version": routing_model.PROMPT_VERSION,
                "prompt_caching": "single_stable_prefix_key",
                "execution": "bounded_parallel" if args.workers > 1 else "sequential",
                "will_call_model": False,
            }
            print(_canonical_json(_result("audience-routing.run", data)))
            return 0
        if args.action == "run":
            run_db = args.run_db or default_run_db(args.run_id)
            conn = connect_run(run_db)
            freeze_run(
                conn,
                run_id=args.run_id,
                day=args.day,
                top_ranked=args.top_ranked,
                event_id=args.event_id,
                artifact_db=args.artifact_db,
                model=args.model,
                effort=args.reasoning_effort,
            )
            client = entity_kinds.create_litellm_client()
            if hasattr(client, "with_options"):
                client = client.with_options(max_retries=0, timeout=180.0)
            data = run_pending(conn, client=client, workers=args.workers)
            conn.close()
            command = "audience-routing.run"
        elif args.action == "refresh":
            data = refresh_all_days(
                through=args.through,
                days=args.days,
                top_ranked=args.top_ranked,
                artifact_db=args.artifact_db,
                model=args.model,
                effort=args.reasoning_effort,
                workers=args.workers,
                day_workers=args.day_workers,
                replace=args.replace,
                dry_run=args.dry_run,
            )
            command = "audience-routing.refresh"
        elif args.action == "refresh-run":
            client = entity_kinds.create_litellm_client()
            if hasattr(client, "with_options"):
                client = client.with_options(max_retries=0, timeout=180.0)
            data = refresh_run_packets(
                source_run_db=args.source_run_db,
                target_run_db=args.run_db or default_run_db(args.run_id),
                run_id=args.run_id,
                artifact_db=args.artifact_db,
                client=client,
                workers=args.workers,
            )
            command = "audience-routing.refresh-run"
        elif args.action == "summary":
            conn = connect_run(args.run_db)
            data = summary(conn)
            conn.close()
            command = "audience-routing.summary"
        else:
            conn = connect_run(args.run_db)
            data = inspect_item(conn, args.event_id)
            conn.close()
            command = "audience-routing.inspect-item"
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(
            _canonical_json(
                {
                    "schema_version": "1.0",
                    "command": f"audience-routing.{args.action}",
                    "status": "error",
                    "data": None,
                    "error": {"code": "E_INVALID_INPUT", "message": str(exc)},
                }
            )
        )
        return 2
    data["duration_ms"] = round((time.monotonic() - started) * 1000)
    print(_canonical_json(_result(command, data)))
    if args.action == "run" and data["counts"]["failed"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
