"""Freeze and route ranked Evidence envelopes directly by audience."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fli import artifacts, audience_routing, entity_kinds


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_ROOT = REPO_ROOT / "data" / "derived" / "audience-routing"
DEFAULT_ARTIFACT_DB = artifacts.DEFAULT_DB
DEFAULT_TOP_RANKED = 10

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
    snapshot_content_sha256 TEXT NOT NULL,
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


def connect_run(path: Path | str) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.executescript(RUN_SCHEMA)
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


def _source_payload(source: audience_routing.EvidenceSource) -> dict[str, Any]:
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


def _source_from_payload(payload: dict[str, Any]) -> audience_routing.EvidenceSource:
    return audience_routing.EvidenceSource(**payload)


def _packet_payload(packet: audience_routing.RoutingPacket) -> dict[str, Any]:
    return {
        "event_id": packet.event_id,
        "day": packet.day,
        "sources": [_source_payload(source) for source in packet.sources],
    }


def _packet_from_payload(payload: dict[str, Any]) -> audience_routing.RoutingPacket:
    return audience_routing.RoutingPacket(
        event_id=str(payload["event_id"]),
        day=str(payload["day"]),
        sources=tuple(
            _source_from_payload(dict(source)) for source in payload["sources"]
        ),
    )


def _x_source(post: dict[str, Any], *, relation: str) -> audience_routing.EvidenceSource:
    post_id = str(post["post_id"])
    author = str(post.get("author") or "") or None
    return audience_routing.EvidenceSource(
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
) -> list[audience_routing.EvidenceSource]:
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
           ORDER BY candidate.artifact_id""",
        (event_id, artifacts.PRIMARY_AUTHOR_SELECTION_POLICY),
    ).fetchall()
    sources: list[audience_routing.EvidenceSource] = []
    for row in rows:
        snapshot = REPO_ROOT / str(row["text_snapshot_ref"])
        if not snapshot.is_file():
            raise FileNotFoundError(snapshot)
        text = snapshot.read_text()
        relation = str(row["relation"])
        author = (
            post_authors.get(str(row["source_external_id"]))
            if relation == "self_publishes"
            else None
        )
        sources.append(
            audience_routing.EvidenceSource(
                source_type="artifact",
                source_id=str(row["artifact_id"]),
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
) -> audience_routing.RoutingPacket:
    root_item = dict(item["root"])
    root = {
        "post_id": str(root_item["post_id"]),
        "author": "@" + str(root_item["author"]["handle"]),
        "text": str(root_item.get("text") or ""),
    }
    sources = [_x_source(root, relation="root")]
    post_authors = {str(root["post_id"]): str(root.get("author") or "")}
    for evidence in item.get("evidence") or []:
        post = {
            "post_id": str(evidence["post_id"]),
            "author": "@" + str(evidence["author"]["handle"]),
            "text": str(evidence.get("text") or ""),
        }
        post_id = str(post["post_id"])
        relationship = str(evidence.get("relationship") or "related")
        if relationship == "retweet":
            continue
        relation = (
            "same_author_continuation"
            if evidence.get("same_author_as_root")
            else relationship
        )
        post_authors[post_id] = str(post.get("author") or "")
        sources.append(_x_source(post, relation=relation))
    sources.extend(
        _artifact_sources(
            artifact_conn,
            event_id=str(item["event_id"]),
            post_authors=post_authors,
        )
    )
    return audience_routing.RoutingPacket(
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
) -> int:
    if top_ranked < 1:
        raise ValueError("top_ranked must be positive")
    from fli.web import events as event_store

    payload = event_store.events_payload(
        day=day,
        lane="all",
        sort="attention",
        query="",
        event_id=event_id or "",
        routing_filter="all",
        limit=5000,
        offset=0,
    )
    if not payload.get("available"):
        raise ValueError(str(payload.get("reason") or "Evidence is unavailable"))
    source_run = dict(payload.get("run") or {})
    if not source_run.get("run_id") or not source_run.get("feed_run_id"):
        raise ValueError("Evidence projection is missing run provenance")
    items = list(payload.get("items") or [])
    if event_id:
        items = [item for item in items if item["event_id"] == event_id]
    else:
        items = items[:top_ranked]
    if not items:
        raise ValueError("Evidence projection has no matching envelopes")
    missing_hashes = [
        str(item["event_id"])
        for item in items
        if not item.get("snapshot_content_sha256")
    ]
    if missing_hashes:
        raise ValueError(
            "Evidence envelopes are missing snapshot hashes: "
            + ", ".join(missing_hashes)
        )

    artifact_conn = _open_readonly(artifact_db)
    try:
        packets = [
            packet_from_event(item, day=day, artifact_conn=artifact_conn)
            for item in items
        ]
    finally:
        artifact_conn.close()

    rendered_inputs = [audience_routing.render_input(packet) for packet in packets]

    cohort = [
        {
            "event_id": packet.event_id,
            "feed_rank": int(item["daily_rank"]),
            "snapshot_content_sha256": str(item["snapshot_content_sha256"]),
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
        "prompt_version": audience_routing.PROMPT_VERSION,
        "prompt_sha256": audience_routing.prompt_sha256(),
        "schema_version": audience_routing.SCHEMA_VERSION,
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
                source_event_run_id, source_feed_run_id, source_artifact_db,
                selection_kind, selection_limit, requested_event_id,
                cohort_sha256, expected_count,
                created_at, updated_at)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                expected["run_id"], expected["day"], expected["model"],
                expected["reasoning_effort"], expected["prompt_version"],
                expected["prompt_sha256"], expected["schema_version"],
                expected["source_event_run_id"], expected["source_feed_run_id"],
                expected["source_artifact_db"], expected["selection_kind"],
                expected["selection_limit"],
                expected["requested_event_id"], expected["cohort_sha256"],
                expected["expected_count"], now, now,
            ),
        )
        conn.executemany(
            """INSERT INTO routing_item
               (event_id, feed_rank, root_url, snapshot_content_sha256,
                packet_json, evidence_sha256, input_text, input_sha256,
                updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    packet.event_id,
                    int(item["daily_rank"]),
                    str(item["root"]["url"]),
                    str(item["snapshot_content_sha256"]),
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
                      SUM(COALESCE(cached_tokens, 0) > 0) AS cache_hit_requests
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
            return row, audience_routing.evaluate_one(
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
    run_parser.add_argument("--model", default=audience_routing.DEFAULT_MODEL)
    run_parser.add_argument(
        "--reasoning-effort", default=audience_routing.DEFAULT_REASONING_EFFORT
    )
    run_parser.add_argument("--workers", type=int, default=1)
    run_parser.add_argument("--dry-run", action="store_true")
    summary_parser = sub.add_parser("summary", help="Inspect a frozen run.")
    summary_parser.add_argument("--run-db", type=Path, required=True)
    item_parser = sub.add_parser("inspect-item", help="Inspect one exact result.")
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
                "top_ranked": args.top_ranked,
                "event_id": args.event_id,
                "artifact_db": str(args.artifact_db),
                "model": args.model,
                "reasoning_effort": args.reasoning_effort,
                "workers": args.workers,
                "prompt_version": audience_routing.PROMPT_VERSION,
                "prompt_caching": "single_stable_prefix_key",
                "execution": "sequential",
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
    except (FileNotFoundError, ValueError) as exc:
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
