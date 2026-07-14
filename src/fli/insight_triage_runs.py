"""Resumable daily execution for conservative cited-insight triage."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import sqlite3
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fli import entity_kinds, insight_triage, signal_feed, sources, x_content
from fli.web.events import events_payload


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_ROOT = REPO_ROOT / "data" / "derived" / "cited-insights" / "triage"
DEFAULT_WORKERS = 32
DEFAULT_PROGRESS_EVERY = 25

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
    candidate_limit INTEGER NOT NULL,
    cohort_sha256 TEXT NOT NULL,
    expected_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS triage_item (
    event_id TEXT PRIMARY KEY,
    current_rank INTEGER NOT NULL,
    root_post_id TEXT NOT NULL,
    root_url TEXT NOT NULL,
    envelope_json TEXT NOT NULL,
    input_text TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    snapshot_content_sha256 TEXT,
    prompt_cache_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'complete', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    decision TEXT,
    reason TEXT,
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
    completed_at TEXT,
    reused_from_run_id TEXT,
    reused_from_event_id TEXT,
    reused_from_response_id TEXT,
    reused_from_reported_cost_usd REAL,
    reused_at TEXT,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_triage_item_status_rank
    ON triage_item (status, current_rank, event_id);
CREATE INDEX IF NOT EXISTS idx_triage_item_decision_rank
    ON triage_item (decision, current_rank, event_id);
CREATE INDEX IF NOT EXISTS idx_triage_item_cache_key_rank
    ON triage_item (prompt_cache_key, current_rank, event_id);
CREATE INDEX IF NOT EXISTS idx_triage_item_input_reuse
    ON triage_item (input_sha256, status, event_id);
"""


_TRIAGE_ITEM_MIGRATIONS: dict[str, str] = {
    "snapshot_content_sha256": "TEXT",
    "reused_from_run_id": "TEXT",
    "reused_from_event_id": "TEXT",
    "reused_from_response_id": "TEXT",
    "reused_from_reported_cost_usd": "REAL",
    "reused_at": "TEXT",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def default_run_db(run_id: str) -> Path:
    if not run_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for character in run_id):
        raise ValueError("run_id may contain only letters, numbers, '-', '_', and '.'")
    return DEFAULT_RUN_ROOT / run_id / "triage.db"


def connect_run(path: Path | str) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.executescript(RUN_SCHEMA)
    existing_columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(triage_item)").fetchall()
    }
    for column, definition in _TRIAGE_ITEM_MIGRATIONS.items():
        if column not in existing_columns:
            conn.execute(
                f"ALTER TABLE triage_item ADD COLUMN {column} {definition}"
            )
    conn.execute(
        """CREATE INDEX IF NOT EXISTS idx_triage_item_input_reuse
           ON triage_item (input_sha256, status, event_id)"""
    )
    conn.commit()
    return conn


def _expanded_urls(
    conn: sqlite3.Connection,
    post_refs: list[tuple[str, str, str]],
    *,
    feed_conn: sqlite3.Connection | None = None,
    feed_run_id: str | None = None,
) -> dict[tuple[str, str], list[str]]:
    if not post_refs:
        return {}
    predicates = " OR ".join(
        "(provider = ? AND post_id = ? AND raw_sha256 = ?)"
        for _ in post_refs
    )
    parameters = [value for post_ref in post_refs for value in post_ref]
    rows = list(conn.execute(
        f"""SELECT DISTINCT provider, post_id, raw_json
            FROM x_post_observation
            WHERE {predicates}""",
        parameters,
    ).fetchall())
    found_refs = {(str(row["provider"]), str(row["post_id"])) for row in rows}
    missing = [
        post_ref for post_ref in post_refs
        if (post_ref[0], post_ref[1]) not in found_refs
    ]
    if feed_conn is not None and feed_run_id and missing:
        feed_predicates = " OR ".join(
            "(provider = ? AND post_id = ? AND raw_sha256 = ?)"
            for _ in missing
        )
        feed_parameters = [value for post_ref in missing for value in post_ref]
        rows.extend(
            feed_conn.execute(
                f"""SELECT DISTINCT provider, post_id, raw_json
                    FROM feed_post
                    WHERE run_id = ? AND ({feed_predicates})""",
                (feed_run_id, *feed_parameters),
            ).fetchall()
        )
    found: dict[tuple[str, str], list[str]] = {}
    for row in rows:
        payload = json.loads(row["raw_json"])
        urls: list[str] = []
        for tweet in (
            payload,
            payload.get("quoted_tweet"),
            payload.get("retweeted_tweet"),
        ):
            if not isinstance(tweet, dict):
                continue
            for item in (tweet.get("entities") or {}).get("urls") or []:
                if not isinstance(item, dict):
                    continue
                url = item.get("expanded_url") or item.get("url")
                if isinstance(url, str) and url.startswith(("http://", "https://")):
                    urls.append(url)
        found[(str(row["provider"]), str(row["post_id"]))] = list(
            dict.fromkeys(urls)
        )
    return found


def _card_value(card: dict[str, Any], key: str) -> str | None:
    for binding in card.get("binding_values") or []:
        if not isinstance(binding, dict) or binding.get("key") != key:
            continue
        value = binding.get("value") or {}
        string_value = value.get("string_value")
        if isinstance(string_value, str) and string_value.strip():
            return string_value.strip()
    return None


def _provider_artifacts(
    conn: sqlite3.Connection,
    post_refs: list[tuple[str, str, str]],
    *,
    feed_conn: sqlite3.Connection | None = None,
    feed_run_id: str | None = None,
) -> list[dict[str, str]]:
    if not post_refs:
        return []
    predicates = " OR ".join(
        "(provider = ? AND post_id = ? AND raw_sha256 = ?)"
        for _ in post_refs
    )
    parameters = [value for post_ref in post_refs for value in post_ref]
    rows = list(conn.execute(
        f"""SELECT DISTINCT provider, post_id, raw_json
            FROM x_post_observation
            WHERE {predicates}""",
        parameters,
    ).fetchall())
    found_refs = {(str(row["provider"]), str(row["post_id"])) for row in rows}
    missing = [
        post_ref for post_ref in post_refs
        if (post_ref[0], post_ref[1]) not in found_refs
    ]
    if feed_conn is not None and feed_run_id and missing:
        feed_predicates = " OR ".join(
            "(provider = ? AND post_id = ? AND raw_sha256 = ?)"
            for _ in missing
        )
        feed_parameters = [value for post_ref in missing for value in post_ref]
        rows.extend(
            feed_conn.execute(
                f"""SELECT DISTINCT provider, post_id, raw_json
                    FROM feed_post
                    WHERE run_id = ? AND ({feed_predicates})""",
                (feed_run_id, *feed_parameters),
            ).fetchall()
        )
    artifacts: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for row in rows:
        payload = json.loads(row["raw_json"])
        post_id = str(row["post_id"])
        for tweet in (payload, payload.get("quoted_tweet")):
            if not isinstance(tweet, dict):
                continue
            expanded_by_short = {
                str(item.get("url")): str(item.get("expanded_url") or item.get("url"))
                for item in (tweet.get("entities") or {}).get("urls") or []
                if isinstance(item, dict) and item.get("url")
            }
            expanded_urls = list(expanded_by_short.values())
            article = tweet.get("article")
            if isinstance(article, dict):
                title = str(article.get("title") or "").strip()
                preview = str(article.get("preview_text") or "").strip()
                url = next(
                    (url for url in expanded_urls if "/i/article/" in url),
                    expanded_urls[0] if expanded_urls else "",
                )
                identity = (post_id, "x_article", title, url)
                if (title or preview) and identity not in seen:
                    seen.add(identity)
                    artifacts.append(
                        {
                            "post_id": post_id,
                            "kind": "x_article",
                            "title": title,
                            "preview": preview,
                            "url": url,
                        }
                    )
            card = tweet.get("card")
            if isinstance(card, dict):
                title = _card_value(card, "title") or ""
                preview = _card_value(card, "description") or ""
                short_url = _card_value(card, "card_url") or str(card.get("url") or "")
                url = expanded_by_short.get(short_url, short_url)
                identity = (post_id, "link_card", title, url)
                if (title or preview) and identity not in seen:
                    seen.add(identity)
                    artifacts.append(
                        {
                            "post_id": post_id,
                            "kind": "link_card",
                            "title": title,
                            "preview": preview,
                            "url": url,
                        }
                    )
    return artifacts


def envelope_from_event(
    item: dict[str, Any],
    *,
    day: str,
    raw_conn: sqlite3.Connection,
    feed_conn: sqlite3.Connection | None = None,
    feed_run_id: str | None = None,
) -> insight_triage.EnvelopeInput:
    root = item["root"]
    related = tuple(
        post for post in item["evidence"] if post["relationship"] != "retweet"
    )
    posts = (root, *related)
    post_refs = [
        (
            str(post.get("provider") or sources.PROVIDER),
            str(post["post_id"]),
            str(post["raw_sha256"]),
        )
        for post in posts
    ]
    urls_by_post = _expanded_urls(
        raw_conn,
        post_refs,
        feed_conn=feed_conn,
        feed_run_id=feed_run_id,
    )
    context = root.get("context") or {}
    return insight_triage.EnvelopeInput(
        event_id=str(item["event_id"]),
        day=day,
        root={
            "post_id": str(root["post_id"]),
            "author": "@" + str(root["author"]["handle"]),
            "post_type": str(root["post_type"]),
            "text": str(root.get("text") or ""),
            "quoted_target_handle": (
                "@" + str(context["target_handle"])
                if context.get("target_handle")
                else None
            ),
        },
        related_posts=tuple(
            {
                "post_id": str(post["post_id"]),
                "relation": str(post["relationship"]),
                "same_author_as_root": bool(post["same_author_as_root"]),
                "author": "@" + str(post["author"]["handle"]),
                "text": str(post.get("text") or ""),
            }
            for post in related
        ),
        urls=tuple(
            {"post_id": post_id, "url": url}
            for provider, post_id, _raw_sha256 in post_refs
            for url in urls_by_post.get((provider, post_id), [])
        ),
        embedded_artifacts=tuple(
            _provider_artifacts(
                raw_conn,
                post_refs,
                feed_conn=feed_conn,
                feed_run_id=feed_run_id,
            )
        ),
    )


def _envelope_payload(envelope: insight_triage.EnvelopeInput) -> dict[str, Any]:
    return {
        "event_id": envelope.event_id,
        "day": envelope.day,
        "root": envelope.root,
        "related_posts": list(envelope.related_posts),
        "urls": list(envelope.urls),
        "embedded_artifacts": list(envelope.embedded_artifacts),
    }


def _envelope_from_payload(payload: dict[str, Any]) -> insight_triage.EnvelopeInput:
    return insight_triage.EnvelopeInput(
        event_id=str(payload["event_id"]),
        day=str(payload["day"]),
        root=dict(payload["root"]),
        related_posts=tuple(payload.get("related_posts") or ()),
        urls=tuple(payload.get("urls") or ()),
        embedded_artifacts=tuple(payload.get("embedded_artifacts") or ()),
    )


def _freeze_candidates(
    *,
    day: str,
    limit: int,
) -> tuple[
    list[tuple[int, dict[str, Any], insight_triage.EnvelopeInput]],
    list[dict[str, Any]],
]:
    payload = events_payload(
        day=day,
        lane="all",
        sort="attention",
        query="",
        limit=limit,
        offset=0,
    )
    items = payload["items"][:limit]
    missing_snapshot_ids = [
        str(item.get("event_id"))
        for item in items
        if not item.get("snapshot_content_sha256")
    ]
    if missing_snapshot_ids:
        raise ValueError(
            "event projection is missing snapshot_content_sha256 for: "
            + ", ".join(missing_snapshot_ids[:5])
        )
    raw_conn = sqlite3.connect(x_content.DEFAULT_DB_PATH)
    raw_conn.row_factory = sqlite3.Row
    feed_conn = sqlite3.connect(signal_feed.DEFAULT_FEED_DB)
    feed_conn.row_factory = sqlite3.Row
    feed_run_id = str((payload.get("run") or {}).get("feed_run_id") or "")
    if not feed_run_id:
        raw_conn.close()
        feed_conn.close()
        raise ValueError("event projection is missing its feed_run_id")
    try:
        frozen = [
            (
                rank,
                item,
                envelope_from_event(
                    item,
                    day=day,
                    raw_conn=raw_conn,
                    feed_conn=feed_conn,
                    feed_run_id=feed_run_id,
                ),
            )
            for rank, item in enumerate(items, start=1)
        ]
    finally:
        raw_conn.close()
        feed_conn.close()
    cohort = [
        {
            "rank": rank,
            "event_id": envelope.event_id,
            "root_post_id": envelope.root["post_id"],
            "input_sha256": envelope.input_sha256,
            "snapshot_content_sha256": str(item["snapshot_content_sha256"]),
            "prompt_cache_key": insight_triage.prompt_cache_key(envelope.event_id),
        }
        for rank, item, envelope in frozen
    ]
    return frozen, cohort


def _current_run_path(conn: sqlite3.Connection) -> Path | None:
    row = conn.execute("PRAGMA database_list").fetchone()
    if row is None or not row["file"]:
        return None
    return Path(str(row["file"])).resolve()


def _reuse_completed_inputs(
    conn: sqlite3.Connection,
    *,
    run_root: Path | None = None,
) -> int:
    """Reuse exact completed model inputs from compatible, complete prior runs."""
    run_root = DEFAULT_RUN_ROOT if run_root is None else run_root
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if meta is None or not run_root.is_dir():
        return 0
    current_path = _current_run_path(conn)
    candidates: dict[tuple[str, str], dict[str, Any]] = {}
    for path in run_root.glob("*/triage.db"):
        try:
            if current_path is not None and path.resolve() == current_path:
                continue
            source = sqlite3.connect(
                f"file:{path.resolve().as_posix()}?mode=ro", uri=True
            )
            source.row_factory = sqlite3.Row
            source_meta = source.execute(
                "SELECT * FROM run_meta WHERE singleton = 1"
            ).fetchone()
            if source_meta is None or any(
                source_meta[key] != meta[key]
                for key in (
                    "model",
                    "reasoning_effort",
                    "prompt_version",
                    "prompt_sha256",
                    "schema_version",
                )
            ):
                source.close()
                continue
            completed_count, total_count = source.execute(
                """SELECT SUM(status = 'complete'), COUNT(*)
                   FROM triage_item"""
            ).fetchone()
            if (
                int(completed_count or 0) != int(source_meta["expected_count"])
                or int(total_count) != int(source_meta["expected_count"])
            ):
                source.close()
                continue
            source_columns = {
                str(row["name"])
                for row in source.execute("PRAGMA table_info(triage_item)").fetchall()
            }
            # Old triage runs predate temporal snapshot identity. They are not
            # safe reuse sources because identical rendered text can represent
            # different exact relationship topology.
            if "snapshot_content_sha256" not in source_columns:
                source.close()
                continue
            response_id_expr = (
                "response_id" if "response_id" in source_columns else "NULL"
            )
            cost_expr = (
                "reported_cost_usd"
                if "reported_cost_usd" in source_columns
                else "NULL"
            )
            rows = source.execute(
                f"""SELECT event_id, input_sha256, snapshot_content_sha256,
                           decision, reason,
                           {response_id_expr} AS response_id,
                           {cost_expr} AS reported_cost_usd,
                           completed_at, updated_at
                    FROM triage_item
                    WHERE status = 'complete'
                      AND decision IN ('keep', 'drop')
                      AND reason IS NOT NULL
                      AND snapshot_content_sha256 IS NOT NULL"""
            ).fetchall()
            source.close()
        except (OSError, sqlite3.Error):
            continue
        for row in rows:
            value = {
                "run_id": str(source_meta["run_id"]),
                "event_id": str(row["event_id"]),
                "response_id": row["response_id"],
                "source_cost": row["reported_cost_usd"],
                "decision": str(row["decision"]),
                "reason": str(row["reason"]),
                "sort_key": (
                    str(row["completed_at"] or row["updated_at"] or ""),
                    str(source_meta["run_id"]),
                    str(row["event_id"]),
                ),
            }
            input_key = (
                str(row["snapshot_content_sha256"]),
                str(row["input_sha256"]),
            )
            if (
                input_key not in candidates
                or value["sort_key"] > candidates[input_key]["sort_key"]
            ):
                candidates[input_key] = value
    if not candidates:
        return 0

    pending = conn.execute(
        """SELECT event_id, input_sha256, snapshot_content_sha256
           FROM triage_item
           WHERE status = 'pending'
             AND snapshot_content_sha256 IS NOT NULL
           ORDER BY current_rank, event_id"""
    ).fetchall()
    now = _now()
    reused = 0
    with conn:
        for row in pending:
            source = candidates.get(
                (
                    str(row["snapshot_content_sha256"]),
                    str(row["input_sha256"]),
                )
            )
            if source is None:
                continue
            conn.execute(
                """UPDATE triage_item
                   SET status = 'complete', attempts = 0,
                       decision = ?, reason = ?,
                       response_id = NULL, response_model = ?,
                       input_tokens = 0, cached_tokens = 0,
                       cache_write_tokens = 0, output_tokens = 0,
                       reported_cost_usd = 0.0, request_tags_json = '[]',
                       error_type = NULL, error_message = NULL,
                       completed_at = ?, reused_from_run_id = ?,
                       reused_from_event_id = ?, reused_from_response_id = ?,
                       reused_from_reported_cost_usd = ?, reused_at = ?,
                       updated_at = ?
                   WHERE event_id = ? AND status = 'pending'""",
                (
                    source["decision"],
                    source["reason"],
                    str(meta["model"]),
                    now,
                    source["run_id"],
                    source["event_id"],
                    source["response_id"],
                    source["source_cost"],
                    now,
                    now,
                    row["event_id"],
                ),
            )
            reused += 1
    return reused


def freeze_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    day: str,
    limit: int,
    model: str,
    effort: str,
) -> int:
    if limit < 1:
        raise ValueError("limit must be positive")
    frozen, cohort = _freeze_candidates(day=day, limit=limit)
    cohort_sha256 = _sha256(_canonical_json(cohort))
    existing = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if existing is not None:
        expected = {
            "run_id": run_id,
            "day": day,
            "model": model,
            "reasoning_effort": effort,
            "prompt_version": insight_triage.PROMPT_VERSION,
            "prompt_sha256": insight_triage.prompt_sha256(),
            "schema_version": insight_triage.SCHEMA_VERSION,
            "candidate_limit": limit,
        }
        mismatches = [
            key for key, value in expected.items() if existing[key] != value
        ]
        if mismatches:
            raise ValueError(
                "run database does not match current request: "
                + ", ".join(mismatches)
            )
        if (
            int(existing["expected_count"]) != len(frozen)
            or str(existing["cohort_sha256"]) != cohort_sha256
        ):
            raise ValueError(
                "run database cohort no longer matches the current event projection; "
                "use a new run_id"
            )
        _reuse_completed_inputs(conn)
        return int(existing["expected_count"])
    now = _now()
    with conn:
        conn.execute(
            """INSERT INTO run_meta
               (singleton, run_id, day, model, reasoning_effort,
                prompt_version, prompt_sha256, schema_version,
                candidate_limit, cohort_sha256, expected_count,
                created_at, updated_at)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                day,
                model,
                effort,
                insight_triage.PROMPT_VERSION,
                insight_triage.prompt_sha256(),
                insight_triage.SCHEMA_VERSION,
                limit,
                cohort_sha256,
                len(frozen),
                now,
                now,
            ),
        )
        conn.executemany(
            """INSERT INTO triage_item
               (event_id, current_rank, root_post_id, root_url,
                envelope_json, input_text, input_sha256,
                snapshot_content_sha256, prompt_cache_key,
                updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    envelope.event_id,
                    rank,
                    str(envelope.root["post_id"]),
                    str(item["root"]["url"]),
                    _canonical_json(_envelope_payload(envelope)),
                    insight_triage.render_input(envelope),
                    envelope.input_sha256,
                    str(item["snapshot_content_sha256"]),
                    insight_triage.prompt_cache_key(envelope.event_id),
                    now,
                )
                for rank, item, envelope in frozen
            ],
        )
    _reuse_completed_inputs(conn)
    return len(frozen)


def summary(conn: sqlite3.Connection) -> dict[str, Any]:
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("run database has not been prepared")
    counts = conn.execute(
        """SELECT COUNT(*) AS total,
                  SUM(status = 'pending') AS pending,
                  SUM(status = 'complete') AS complete,
                  SUM(status = 'failed') AS failed,
                  SUM(reused_from_run_id IS NOT NULL) AS reused,
                  SUM(decision = 'keep') AS kept,
                  SUM(decision = 'drop') AS dropped,
                  SUM(COALESCE(input_tokens, 0)) AS input_tokens,
                  SUM(COALESCE(cached_tokens, 0)) AS cached_tokens,
                  SUM(COALESCE(cache_write_tokens, 0)) AS cache_write_tokens,
                  SUM(COALESCE(output_tokens, 0)) AS output_tokens,
                  SUM(COALESCE(reported_cost_usd, 0)) AS reported_cost_usd,
                  SUM(reported_cost_usd IS NOT NULL) AS reported_cost_count,
                  COUNT(DISTINCT prompt_cache_key) AS prompt_cache_keys,
                  SUM(COALESCE(input_tokens, 0) >= 1024) AS cache_eligible_requests,
                  SUM(COALESCE(cached_tokens, 0) > 0) AS cache_hit_requests
           FROM triage_item"""
    ).fetchone()
    data = dict(counts)
    input_tokens = int(data["input_tokens"] or 0)
    data["cache_read_ratio"] = (
        round(int(data["cached_tokens"] or 0) / input_tokens, 6)
        if input_tokens
        else 0.0
    )
    return {"run": dict(meta), "counts": data}


def run_pending(
    conn: sqlite3.Connection,
    *,
    client: Any,
    workers: int = DEFAULT_WORKERS,
    progress_every: int = DEFAULT_PROGRESS_EVERY,
) -> dict[str, Any]:
    if workers < 1:
        raise ValueError("workers must be at least 1")
    if progress_every < 1:
        raise ValueError("progress_every must be at least 1")
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("run database has not been prepared")
    rows = conn.execute(
        """SELECT * FROM triage_item
           WHERE status != 'complete'
           ORDER BY current_rank, event_id"""
    ).fetchall()
    def evaluate(row: sqlite3.Row) -> tuple[sqlite3.Row, dict[str, Any] | None, Exception | None]:
        envelope = _envelope_from_payload(json.loads(row["envelope_json"]))
        try:
            result = insight_triage.evaluate_one(
                client,
                envelope,
                run=str(meta["run_id"]),
                model=str(meta["model"]),
                effort=str(meta["reasoning_effort"]),
            )
            return row, result, None
        except Exception as exc:
            return row, None, exc

    if not rows:
        return summary(conn)

    lanes: dict[str, deque[sqlite3.Row]] = {}
    for row in rows:
        lanes.setdefault(str(row["prompt_cache_key"]), deque()).append(row)
    waiting_lanes = deque(lanes)
    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=min(workers, len(lanes))
    )
    active: dict[concurrent.futures.Future, str] = {}

    def start_next(cache_key: str) -> None:
        active[executor.submit(evaluate, lanes[cache_key].popleft())] = cache_key

    while waiting_lanes and len(active) < workers:
        start_next(waiting_lanes.popleft())

    def outcomes():
        while active:
            done, _ = concurrent.futures.wait(
                active,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            for future in done:
                cache_key = active.pop(future)
                yield future.result()
                if lanes[cache_key]:
                    start_next(cache_key)
                elif waiting_lanes:
                    start_next(waiting_lanes.popleft())

    try:
        for processed, (row, result, error) in enumerate(outcomes(), start=1):
            now = _now()
            if result is not None:
                with conn:
                    conn.execute(
                        """UPDATE triage_item
                           SET status = 'complete', attempts = attempts + 1,
                               decision = ?, reason = ?,
                               response_id = ?, response_model = ?,
                               input_tokens = ?, cached_tokens = ?,
                               cache_write_tokens = ?, output_tokens = ?,
                               reported_cost_usd = ?, request_tags_json = ?,
                               error_type = NULL, error_message = NULL,
                               completed_at = ?, updated_at = ?
                           WHERE event_id = ?""",
                        (
                            result["decision"],
                            result["reason"],
                            result["response_id"],
                            result["response_model"],
                            result["input_tokens"],
                            result["cached_tokens"],
                            result["cache_write_tokens"],
                            result["output_tokens"],
                            result["reported_cost_usd"],
                            _canonical_json(result["request_tags"]),
                            now,
                            now,
                            row["event_id"],
                        ),
                    )
                status = "complete"
            else:
                assert error is not None
                with conn:
                    conn.execute(
                        """UPDATE triage_item
                           SET status = 'failed', attempts = attempts + 1,
                               error_type = ?, error_message = ?, updated_at = ?
                           WHERE event_id = ?""",
                        (type(error).__name__, str(error), now, row["event_id"]),
                    )
                status = "failed"

            if (
                status == "failed"
                or processed % progress_every == 0
                or processed == len(rows)
            ):
                print(
                    _canonical_json(
                        {
                            "event_id": row["event_id"],
                            "rank": row["current_rank"],
                            "status": status,
                            "processed": processed,
                            "pending_batch": len(rows),
                        }
                    ),
                    file=sys.stderr,
                    flush=True,
                )
    finally:
        executor.shutdown(wait=True)
    return summary(conn)


def inspect_item(conn: sqlite3.Connection, event_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM triage_item WHERE event_id = ?",
        (event_id,),
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
    parser = argparse.ArgumentParser(prog="fli insight-triage")
    sub = parser.add_subparsers(dest="action", required=True)

    run_parser = sub.add_parser("run", help="Freeze and triage one daily cohort.")
    run_parser.add_argument("--run-id", required=True)
    run_parser.add_argument("--run-db", type=Path)
    run_parser.add_argument("--day", required=True)
    run_parser.add_argument("--limit", type=int, default=20)
    run_parser.add_argument("--model", default=insight_triage.DEFAULT_MODEL)
    run_parser.add_argument(
        "--reasoning-effort",
        default=insight_triage.DEFAULT_REASONING_EFFORT,
    )
    run_parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    run_parser.add_argument(
        "--progress-every", type=int, default=DEFAULT_PROGRESS_EVERY
    )
    run_parser.add_argument("--dry-run", action="store_true")

    summary_parser = sub.add_parser("summary", help="Inspect a frozen run.")
    summary_parser.add_argument("--run-db", type=Path, required=True)

    item_parser = sub.add_parser("inspect-item", help="Inspect one exact run item.")
    item_parser.add_argument("--run-db", type=Path, required=True)
    item_parser.add_argument("--event-id", required=True)

    args = parser.parse_args(argv)
    started = time.monotonic()
    try:
        if args.action == "run" and args.dry_run:
            data = {
                "run_id": args.run_id,
                "run_db": str(args.run_db or default_run_db(args.run_id)),
                "day": args.day,
                "candidate_limit": args.limit,
                "model": args.model,
                "reasoning_effort": args.reasoning_effort,
                "prompt_version": insight_triage.PROMPT_VERSION,
                "workers": args.workers,
                "prompt_cache_shards": insight_triage.PROMPT_CACHE_SHARDS,
                "will_call_model": False,
            }
            print(_canonical_json(_result("insight-triage.run", data)))
            return 0
        if args.action == "run":
            run_db = args.run_db or default_run_db(args.run_id)
            conn = connect_run(run_db)
            freeze_run(
                conn,
                run_id=args.run_id,
                day=args.day,
                limit=args.limit,
                model=args.model,
                effort=args.reasoning_effort,
            )
            client = entity_kinds.create_litellm_client()
            if hasattr(client, "with_options"):
                client = client.with_options(max_retries=0, timeout=180.0)
            data = run_pending(
                conn,
                client=client,
                workers=args.workers,
                progress_every=args.progress_every,
            )
            conn.close()
            command = "insight-triage.run"
        elif args.action == "summary":
            conn = connect_run(args.run_db)
            data = summary(conn)
            conn.close()
            command = "insight-triage.summary"
        else:
            conn = connect_run(args.run_db)
            data = inspect_item(conn, args.event_id)
            conn.close()
            command = "insight-triage.inspect-item"
    except (FileNotFoundError, ValueError) as exc:
        print(
            _canonical_json(
                {
                    "schema_version": "1.0",
                    "command": f"insight-triage.{args.action}",
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
