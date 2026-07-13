"""Resumable daily execution for conservative cited-insight triage."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fli import entity_kinds, insight_triage, x_content
from fli.web.events import events_payload


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_ROOT = REPO_ROOT / "data" / "derived" / "cited-insights" / "triage"

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
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'complete', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    decision TEXT,
    category TEXT,
    signal_post_ids_json TEXT,
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
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_triage_item_status_rank
    ON triage_item (status, current_rank, event_id);
CREATE INDEX IF NOT EXISTS idx_triage_item_decision_rank
    ON triage_item (decision, current_rank, event_id);
"""


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
    return conn


def _expanded_urls(
    conn: sqlite3.Connection,
    post_ids: list[str],
) -> dict[str, list[str]]:
    if not post_ids:
        return {}
    placeholders = ",".join("?" for _ in post_ids)
    rows = conn.execute(
        f"SELECT post_id, raw_json FROM x_post WHERE post_id IN ({placeholders})",
        post_ids,
    ).fetchall()
    found: dict[str, list[str]] = {}
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
        found[str(row["post_id"])] = list(dict.fromkeys(urls))
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
    post_ids: list[str],
) -> list[dict[str, str]]:
    if not post_ids:
        return []
    placeholders = ",".join("?" for _ in post_ids)
    rows = conn.execute(
        f"SELECT post_id, raw_json FROM x_post WHERE post_id IN ({placeholders})",
        post_ids,
    ).fetchall()
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
) -> insight_triage.EnvelopeInput:
    root = item["root"]
    related = tuple(
        post for post in item["evidence"] if post["relationship"] != "retweet"
    )
    post_ids = [str(root["post_id"]), *(str(post["post_id"]) for post in related)]
    urls_by_post = _expanded_urls(raw_conn, post_ids)
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
            for post_id in post_ids
            for url in urls_by_post.get(post_id, [])
        ),
        embedded_artifacts=tuple(_provider_artifacts(raw_conn, post_ids)),
        retweet_count=sum(
            post["relationship"] == "retweet" for post in item["evidence"]
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
        "retweet_count": envelope.retweet_count,
    }


def _envelope_from_payload(payload: dict[str, Any]) -> insight_triage.EnvelopeInput:
    return insight_triage.EnvelopeInput(
        event_id=str(payload["event_id"]),
        day=str(payload["day"]),
        root=dict(payload["root"]),
        related_posts=tuple(payload.get("related_posts") or ()),
        urls=tuple(payload.get("urls") or ()),
        embedded_artifacts=tuple(payload.get("embedded_artifacts") or ()),
        retweet_count=int(payload.get("retweet_count") or 0),
    )


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
        return int(existing["expected_count"])

    payload = events_payload(
        day=day,
        lane="all",
        sort="attention",
        query="",
        limit=limit,
        offset=0,
    )
    items = payload["items"][:limit]
    raw_conn = sqlite3.connect(x_content.DEFAULT_DB_PATH)
    raw_conn.row_factory = sqlite3.Row
    try:
        frozen = [
            (rank, item, envelope_from_event(item, day=day, raw_conn=raw_conn))
            for rank, item in enumerate(items, start=1)
        ]
    finally:
        raw_conn.close()
    cohort = [
        {
            "rank": rank,
            "event_id": envelope.event_id,
            "root_post_id": envelope.root["post_id"],
            "input_sha256": envelope.input_sha256,
        }
        for rank, _, envelope in frozen
    ]
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
                _sha256(_canonical_json(cohort)),
                len(frozen),
                now,
                now,
            ),
        )
        conn.executemany(
            """INSERT INTO triage_item
               (event_id, current_rank, root_post_id, root_url,
                envelope_json, input_text, input_sha256, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    envelope.event_id,
                    rank,
                    str(envelope.root["post_id"]),
                    str(item["root"]["url"]),
                    _canonical_json(_envelope_payload(envelope)),
                    insight_triage.render_input(envelope),
                    envelope.input_sha256,
                    now,
                )
                for rank, item, envelope in frozen
            ],
        )
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
                  SUM(decision = 'keep') AS kept,
                  SUM(decision = 'drop') AS dropped,
                  SUM(COALESCE(input_tokens, 0)) AS input_tokens,
                  SUM(COALESCE(cached_tokens, 0)) AS cached_tokens,
                  SUM(COALESCE(cache_write_tokens, 0)) AS cache_write_tokens,
                  SUM(COALESCE(output_tokens, 0)) AS output_tokens,
                  SUM(COALESCE(reported_cost_usd, 0)) AS reported_cost_usd,
                  SUM(reported_cost_usd IS NOT NULL) AS reported_cost_count
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
) -> dict[str, Any]:
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if meta is None:
        raise ValueError("run database has not been prepared")
    rows = conn.execute(
        """SELECT * FROM triage_item
           WHERE status != 'complete'
           ORDER BY current_rank, event_id"""
    ).fetchall()
    for row in rows:
        envelope = _envelope_from_payload(json.loads(row["envelope_json"]))
        now = _now()
        try:
            result = insight_triage.evaluate_one(
                client,
                envelope,
                run=str(meta["run_id"]),
                model=str(meta["model"]),
                effort=str(meta["reasoning_effort"]),
            )
            with conn:
                conn.execute(
                    """UPDATE triage_item
                       SET status = 'complete', attempts = attempts + 1,
                           decision = ?, category = ?,
                           signal_post_ids_json = ?, reason = ?,
                           response_id = ?, response_model = ?,
                           input_tokens = ?, cached_tokens = ?,
                           cache_write_tokens = ?, output_tokens = ?,
                           reported_cost_usd = ?, request_tags_json = ?,
                           error_type = NULL, error_message = NULL,
                           completed_at = ?, updated_at = ?
                       WHERE event_id = ?""",
                    (
                        result["decision"],
                        result["category"],
                        _canonical_json(result["signal_post_ids"]),
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
        except Exception as exc:
            with conn:
                conn.execute(
                    """UPDATE triage_item
                       SET status = 'failed', attempts = attempts + 1,
                           error_type = ?, error_message = ?, updated_at = ?
                       WHERE event_id = ?""",
                    (type(exc).__name__, str(exc), now, row["event_id"]),
                )
            status = "failed"
        print(
            _canonical_json(
                {
                    "event_id": row["event_id"],
                    "rank": row["current_rank"],
                    "status": status,
                }
            ),
            file=sys.stderr,
            flush=True,
        )
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
            data = run_pending(conn, client=client)
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
