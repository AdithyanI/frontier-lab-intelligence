"""Freeze, run, and inspect the bounded ``insight-v1`` extraction oracle."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from fli import artifacts, cited_insights, entity_kinds


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_ROOT = REPO_ROOT / "data" / "derived" / "cited-insights" / "extraction"
DEFAULT_TRIAGE_DB = (
    REPO_ROOT
    / "data"
    / "derived"
    / "cited-insights"
    / "triage"
    / "triage-v2.2-canonical-v8-2026-07-11-top1000"
    / "triage.db"
)
DEFAULT_ARTIFACT_DB = artifacts.DEFAULT_DB
DEFAULT_RUN_ID = "insight-v1.1-oracle-2026-07-11"
DEFAULT_DAY = "2026-07-11"
ORACLE_EVENT_IDS = (
    "4eea8e96c4ba717b4ef2246b9ebaf3ef7849a00f484e95132a62210fa8e25e3a",
    "cb7a2c49717c7a53ab6a21f8706ee1c219ab3702b7686283a2c3a1f4ccf8e9ce",
    "dfaad8312be2f0be95c48a72dd46455ac8d701b64a33fd53092a266dd1c3fdb8",
    "c0d7fe525b4cf4c4079a52e68734395dd56309341594d3a4691c4a1f1f7b868f",
    "eb08b978f54de0e97583c258568326cab53045d269a8ee06ad06a4e07e094dec",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS run_meta (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    run_id TEXT NOT NULL,
    day TEXT NOT NULL,
    model TEXT NOT NULL,
    reasoning_effort TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    prompt_sha256 TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    source_triage_db TEXT NOT NULL,
    source_artifact_db TEXT NOT NULL,
    event_ids_json TEXT NOT NULL,
    cohort_sha256 TEXT NOT NULL,
    expected_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS insight_item (
    event_id TEXT PRIMARY KEY,
    day TEXT NOT NULL,
    current_rank INTEGER NOT NULL,
    packet_json TEXT NOT NULL,
    input_text TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    prompt_cache_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'complete', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    outcome TEXT CHECK (
        outcome IS NULL OR outcome IN ('insight', 'no_extractable_insight')
    ),
    claim TEXT,
    why_it_matters TEXT,
    investment_implication TEXT,
    engineering_implication TEXT,
    supporting_quote TEXT,
    citation_source_type TEXT,
    citation_source_id TEXT,
    citation_source_url TEXT,
    citation_source_author TEXT,
    citation_source_title TEXT,
    citation_matching_source_count INTEGER,
    response_id TEXT,
    response_model TEXT,
    input_tokens INTEGER,
    cached_tokens INTEGER,
    cache_write_tokens INTEGER,
    output_tokens INTEGER,
    reported_cost_usd REAL,
    request_tags_json TEXT,
    raw_output_text TEXT,
    error_type TEXT,
    error_message TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_insight_item_status_rank
    ON insight_item(status, current_rank, event_id);
CREATE INDEX IF NOT EXISTS idx_insight_item_outcome_rank
    ON insight_item(outcome, current_rank, event_id);
CREATE INDEX IF NOT EXISTS idx_insight_item_input
    ON insight_item(input_sha256, status, event_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def default_run_db(run_id: str) -> Path:
    if not run_id or any(
        character
        not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        for character in run_id
    ):
        raise ValueError("run_id may contain only letters, numbers, '-', '_', and '.'")
    return DEFAULT_RUN_ROOT / run_id / "insights.db"


def connect_run(path: Path | str) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.executescript(SCHEMA)
    existing_columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(insight_item)").fetchall()
    }
    if "raw_output_text" not in existing_columns:
        conn.execute("ALTER TABLE insight_item ADD COLUMN raw_output_text TEXT")
        conn.commit()
    return conn


def _open_readonly(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(path)
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _x_url(author: str | None, post_id: str) -> str:
    handle = (author or "i").removeprefix("@")
    return f"https://x.com/{handle}/status/{post_id}"


def _x_source(post: dict[str, Any], *, relation: str) -> cited_insights.EvidenceSource:
    post_id = str(post["post_id"])
    author = str(post.get("author") or "") or None
    return cited_insights.EvidenceSource(
        source_type="x_post",
        source_id=post_id,
        url=_x_url(author, post_id),
        text=str(post.get("text") or ""),
        author=author,
        relation=relation,
    )


def _artifact_sources(
    artifact_conn: sqlite3.Connection,
    *,
    event_id: str,
) -> list[cited_insights.EvidenceSource]:
    rows = artifact_conn.execute(
        """SELECT DISTINCT a.artifact_id, a.canonical_url, a.title,
                          latest.text_snapshot_ref
           FROM artifact_import_candidate AS candidate
           JOIN artifact AS a ON a.artifact_id = candidate.artifact_id
           JOIN artifact_fetch AS latest ON latest.fetch_id = (
               SELECT fetch.fetch_id
               FROM artifact_fetch AS fetch
               WHERE fetch.artifact_id = a.artifact_id
                 AND fetch.status = 'success'
                 AND fetch.text_snapshot_ref IS NOT NULL
               ORDER BY fetch.completed_at DESC, fetch.fetch_id DESC
               LIMIT 1
           )
           WHERE candidate.event_id = ?
             AND candidate.decision = 'accepted'
           ORDER BY a.artifact_id""",
        (event_id,),
    ).fetchall()
    sources: list[cited_insights.EvidenceSource] = []
    for row in rows:
        snapshot_path = REPO_ROOT / str(row["text_snapshot_ref"])
        if not snapshot_path.is_file():
            continue
        sources.append(
            cited_insights.EvidenceSource(
                source_type="artifact",
                source_id=str(row["artifact_id"]),
                url=str(row["canonical_url"]),
                title=str(row["title"] or "") or None,
                text=snapshot_path.read_text(),
                relation="optional_strengthening",
            )
        )
    return sources


def _packet_from_row(
    row: sqlite3.Row,
    *,
    artifact_conn: sqlite3.Connection,
) -> cited_insights.InsightInput:
    envelope = json.loads(row["envelope_json"])
    root = dict(envelope["root"])
    sources = [_x_source(root, relation="root")]
    for related in envelope.get("related_posts") or []:
        sources.append(
            _x_source(dict(related), relation=str(related.get("relation") or "related"))
        )
    sources.extend(_artifact_sources(artifact_conn, event_id=str(row["event_id"])))
    return cited_insights.InsightInput(
        event_id=str(row["event_id"]),
        day=str(envelope.get("day") or DEFAULT_DAY),
        current_rank=int(row["current_rank"]),
        sources=tuple(sources),
    )


def _packet_payload(packet: cited_insights.InsightInput) -> dict[str, Any]:
    return {
        "event_id": packet.event_id,
        "day": packet.day,
        "current_rank": packet.current_rank,
        "sources": [asdict(source) for source in packet.sources],
    }


def _packet_from_payload(payload: dict[str, Any]) -> cited_insights.InsightInput:
    return cited_insights.InsightInput(
        event_id=str(payload["event_id"]),
        day=str(payload["day"]),
        current_rank=int(payload["current_rank"]),
        sources=tuple(
            cited_insights.EvidenceSource(**source) for source in payload["sources"]
        ),
    )


def freeze_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    day: str = DEFAULT_DAY,
    event_ids: Iterable[str] = ORACLE_EVENT_IDS,
    triage_db: Path = DEFAULT_TRIAGE_DB,
    artifact_db: Path = DEFAULT_ARTIFACT_DB,
    model: str = cited_insights.DEFAULT_MODEL,
    effort: str = cited_insights.DEFAULT_REASONING_EFFORT,
) -> int:
    frozen_ids = tuple(event_ids)
    if not frozen_ids:
        raise ValueError("at least one event_id is required")
    triage = _open_readonly(triage_db)
    artifact_conn = _open_readonly(artifact_db)
    try:
        placeholders = ",".join("?" for _ in frozen_ids)
        rows = triage.execute(
            f"""SELECT event_id, current_rank, envelope_json, status, decision
                FROM triage_item
                WHERE event_id IN ({placeholders})
                ORDER BY current_rank, event_id""",
            frozen_ids,
        ).fetchall()
        if len(rows) != len(frozen_ids):
            found = {str(row["event_id"]) for row in rows}
            missing = sorted(set(frozen_ids) - found)
            raise ValueError(f"source triage run is missing events: {missing}")
        invalid = [
            str(row["event_id"])
            for row in rows
            if row["status"] != "complete" or row["decision"] != "keep"
        ]
        if invalid:
            raise ValueError(f"oracle events are not completed kept envelopes: {invalid}")
        packets = [
            _packet_from_row(row, artifact_conn=artifact_conn) for row in rows
        ]
    finally:
        triage.close()
        artifact_conn.close()

    cohort = [_packet_payload(packet) for packet in packets]
    cohort_sha256 = _sha256(_canonical_json(cohort))
    event_ids_json = _canonical_json([packet.event_id for packet in packets])
    existing = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if existing is not None:
        expected = {
            "run_id": run_id,
            "day": day,
            "model": model,
            "reasoning_effort": effort,
            "prompt_version": cited_insights.PROMPT_VERSION,
            "prompt_sha256": cited_insights.prompt_sha256(),
            "schema_version": cited_insights.SCHEMA_VERSION,
            "event_ids_json": event_ids_json,
            "cohort_sha256": cohort_sha256,
            "expected_count": len(packets),
        }
        mismatches = [
            key for key, value in expected.items() if existing[key] != value
        ]
        if mismatches:
            raise ValueError(
                "run database does not match the frozen request: " + ", ".join(mismatches)
            )
        return int(existing["expected_count"])

    now = _now()
    with conn:
        conn.execute(
            """INSERT INTO run_meta
               (singleton, run_id, day, model, reasoning_effort,
                prompt_version, prompt_sha256, schema_version,
                source_triage_db, source_artifact_db, event_ids_json,
                cohort_sha256, expected_count, created_at, updated_at)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                day,
                model,
                effort,
                cited_insights.PROMPT_VERSION,
                cited_insights.prompt_sha256(),
                cited_insights.SCHEMA_VERSION,
                _display_path(triage_db),
                _display_path(artifact_db),
                event_ids_json,
                cohort_sha256,
                len(packets),
                now,
                now,
            ),
        )
        conn.executemany(
            """INSERT INTO insight_item
               (event_id, day, current_rank, packet_json, input_text,
                input_sha256, prompt_cache_key, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    packet.event_id,
                    packet.day,
                    packet.current_rank,
                    _canonical_json(_packet_payload(packet)),
                    cited_insights.render_input(packet),
                    packet.input_sha256,
                    cited_insights.prompt_cache_key(packet.event_id),
                    now,
                )
                for packet in packets
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
                      SUM(outcome = 'insight') AS insights,
                      SUM(outcome = 'no_extractable_insight') AS no_extractable,
                      SUM(COALESCE(input_tokens, 0)) AS input_tokens,
                      SUM(COALESCE(cached_tokens, 0)) AS cached_tokens,
                      SUM(COALESCE(cache_write_tokens, 0)) AS cache_write_tokens,
                      SUM(COALESCE(output_tokens, 0)) AS output_tokens,
                      SUM(COALESCE(reported_cost_usd, 0)) AS reported_cost_usd,
                      SUM(reported_cost_usd IS NOT NULL) AS reported_cost_count,
                      COUNT(DISTINCT prompt_cache_key) AS prompt_cache_keys,
                      SUM(COALESCE(input_tokens, 0) >= 1024) AS cache_eligible_requests,
                      SUM(COALESCE(cached_tokens, 0) > 0) AS cache_hit_requests
               FROM insight_item"""
        ).fetchone()
    )
    input_tokens = int(counts["input_tokens"] or 0)
    counts["cache_read_ratio"] = (
        round(int(counts["cached_tokens"] or 0) / input_tokens, 6)
        if input_tokens
        else 0.0
    )
    return {"run": dict(meta), "counts": counts}


def _store_success(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    result: dict[str, Any],
) -> None:
    citation = result["citation"] or {}
    now = _now()
    with conn:
        conn.execute(
            """UPDATE insight_item
               SET status = 'complete', attempts = attempts + 1,
                   outcome = ?, claim = ?, why_it_matters = ?,
                   investment_implication = ?, engineering_implication = ?,
                   supporting_quote = ?, citation_source_type = ?,
                   citation_source_id = ?, citation_source_url = ?,
                   citation_source_author = ?, citation_source_title = ?,
                   citation_matching_source_count = ?, response_id = ?,
                   response_model = ?, input_tokens = ?, cached_tokens = ?,
                   cache_write_tokens = ?, output_tokens = ?,
                   reported_cost_usd = ?, request_tags_json = ?,
                   raw_output_text = ?,
                   error_type = NULL, error_message = NULL,
                   completed_at = ?, updated_at = ?
               WHERE event_id = ?""",
            (
                result["outcome"],
                result["claim"],
                result["why_it_matters"],
                result["investment_implication"],
                result["engineering_implication"],
                result["supporting_quote"],
                citation.get("source_type"),
                citation.get("source_id"),
                citation.get("source_url"),
                citation.get("source_author"),
                citation.get("source_title"),
                citation.get("matching_source_count"),
                result["response_id"],
                result["response_model"],
                result["input_tokens"],
                result["cached_tokens"],
                result["cache_write_tokens"],
                result["output_tokens"],
                result["reported_cost_usd"],
                _canonical_json(result["request_tags"]),
                result["raw_output_text"],
                now,
                now,
                row["event_id"],
            ),
        )


def run_pending(
    conn: sqlite3.Connection,
    *,
    client: Any,
    retry_failed: bool = False,
) -> dict[str, Any]:
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("run database has not been prepared")
    statuses = ("pending", "failed") if retry_failed else ("pending",)
    placeholders = ",".join("?" for _ in statuses)
    rows = conn.execute(
        f"""SELECT * FROM insight_item
            WHERE status IN ({placeholders})
            ORDER BY current_rank, event_id""",
        statuses,
    ).fetchall()
    for processed, row in enumerate(rows, start=1):
        packet = _packet_from_payload(json.loads(row["packet_json"]))
        try:
            result = cited_insights.evaluate_one(
                client,
                packet,
                run=str(meta["run_id"]),
                model=str(meta["model"]),
                effort=str(meta["reasoning_effort"]),
            )
            _store_success(conn, row, result)
            status = "complete"
        except Exception as exc:
            now = _now()
            rejected = (
                exc.result
                if isinstance(exc, cited_insights.CitationVerificationError)
                else None
            )
            with conn:
                if rejected is None:
                    conn.execute(
                        """UPDATE insight_item
                           SET status = 'failed', attempts = attempts + 1,
                               error_type = ?, error_message = ?, updated_at = ?
                           WHERE event_id = ?""",
                        (type(exc).__name__, str(exc), now, row["event_id"]),
                    )
                else:
                    conn.execute(
                        """UPDATE insight_item
                           SET status = 'failed', attempts = attempts + 1,
                               outcome = ?, claim = ?, why_it_matters = ?,
                               investment_implication = ?,
                               engineering_implication = ?, supporting_quote = ?,
                               response_id = ?, response_model = ?,
                               input_tokens = ?, cached_tokens = ?,
                               cache_write_tokens = ?, output_tokens = ?,
                               reported_cost_usd = ?, request_tags_json = ?,
                               raw_output_text = ?, error_type = ?,
                               error_message = ?, updated_at = ?
                           WHERE event_id = ?""",
                        (
                            rejected["outcome"],
                            rejected["claim"],
                            rejected["why_it_matters"],
                            rejected["investment_implication"],
                            rejected["engineering_implication"],
                            rejected["supporting_quote"],
                            rejected["response_id"],
                            rejected["response_model"],
                            rejected["input_tokens"],
                            rejected["cached_tokens"],
                            rejected["cache_write_tokens"],
                            rejected["output_tokens"],
                            rejected["reported_cost_usd"],
                            _canonical_json(rejected["request_tags"]),
                            rejected["raw_output_text"],
                            type(exc).__name__,
                            str(exc),
                            now,
                            row["event_id"],
                        ),
                    )
            status = "failed"
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
    return summary(conn)


def inspect_item(conn: sqlite3.Connection, event_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM insight_item WHERE event_id = ?", (event_id,)
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
    parser = argparse.ArgumentParser(prog="fli cited-insights")
    sub = parser.add_subparsers(dest="action", required=True)

    run_parser = sub.add_parser("run", help="Freeze and extract the five-item oracle.")
    run_parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    run_parser.add_argument("--run-db", type=Path)
    run_parser.add_argument("--day", default=DEFAULT_DAY)
    run_parser.add_argument("--triage-db", type=Path, default=DEFAULT_TRIAGE_DB)
    run_parser.add_argument("--artifact-db", type=Path, default=DEFAULT_ARTIFACT_DB)
    run_parser.add_argument("--model", default=cited_insights.DEFAULT_MODEL)
    run_parser.add_argument(
        "--reasoning-effort", default=cited_insights.DEFAULT_REASONING_EFFORT
    )
    run_parser.add_argument("--retry-failed", action="store_true")
    run_parser.add_argument("--dry-run", action="store_true")

    summary_parser = sub.add_parser("summary", help="Inspect a frozen run.")
    summary_parser.add_argument("--run-db", type=Path, required=True)

    item_parser = sub.add_parser("inspect-item", help="Inspect one exact run item.")
    item_parser.add_argument("--run-db", type=Path, required=True)
    item_parser.add_argument("--event-id", required=True)

    args = parser.parse_args(argv)
    started = time.monotonic()
    command = f"cited-insights.{args.action}"
    try:
        if args.action == "run":
            run_db = args.run_db or default_run_db(args.run_id)
            conn = connect_run(run_db)
            freeze_run(
                conn,
                run_id=args.run_id,
                day=args.day,
                triage_db=args.triage_db,
                artifact_db=args.artifact_db,
                model=args.model,
                effort=args.reasoning_effort,
            )
            if args.dry_run:
                data = summary(conn)
                data["will_call_model"] = False
            else:
                client = entity_kinds.create_litellm_client()
                if hasattr(client, "with_options"):
                    client = client.with_options(max_retries=0, timeout=180.0)
                data = run_pending(conn, client=client, retry_failed=args.retry_failed)
            conn.close()
        elif args.action == "summary":
            conn = connect_run(args.run_db)
            data = summary(conn)
            conn.close()
        else:
            conn = connect_run(args.run_db)
            data = inspect_item(conn, args.event_id)
            conn.close()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(
            _canonical_json(
                {
                    "schema_version": "1.0",
                    "command": command,
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
