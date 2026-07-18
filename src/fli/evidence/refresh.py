"""One resumable refresh path for Feed Events and source artifacts."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import httpx

from fli import store
from fli.evidence import events as signal_events
from fli.evidence import feed as signal_feed
from fli.evidence.artifacts import arxiv as artifact_arxiv
from fli.evidence.artifacts import fetch as artifact_fetch
from fli.evidence.artifacts import store as artifacts
from fli.evidence.artifacts import x_articles as artifact_x_articles
from fli.ingestion import sources
from fli.ingestion.x import collection as x_daily_collection
from fli.ingestion.x import content as x_content


DEFAULT_VIEW_BASE_URL = "http://127.0.0.1:8797"
CLI_SCHEMA_VERSION = "1.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _day(value: str | date) -> date:
    return value if isinstance(value, date) else datetime.strptime(value, "%Y-%m-%d").date()


def _completed_collection_coverage(
    *,
    manifest_path: Path | str,
    start_day: date,
    end_day: date,
    contract: str,
    cohort_sha256: str,
) -> dict[str, Any]:
    """Prove an inclusive range from contiguous completed collection runs."""
    conn = sqlite3.connect(manifest_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT run_id, horizon_start_day, horizon_end_day
               FROM collection_run
               WHERE status = 'complete'
                 AND collection_contract = ?
                 AND cohort_sha256 = ?
                 AND horizon_end_day >= ?
                 AND horizon_start_day <= ?
               ORDER BY horizon_start_day, horizon_end_day DESC""",
            (contract, cohort_sha256, start_day.isoformat(), end_day.isoformat()),
        ).fetchall()
    finally:
        conn.close()

    cursor = start_day
    selected: list[str] = []
    while cursor <= end_day:
        candidates = [
            row
            for row in rows
            if _day(row["horizon_start_day"]) <= cursor
            and _day(row["horizon_end_day"]) >= cursor
        ]
        if not candidates:
            return {
                "status": "incomplete",
                "start_day": start_day.isoformat(),
                "end_day": end_day.isoformat(),
                "first_uncovered_day": cursor.isoformat(),
                "run_ids": selected,
            }
        winner = max(candidates, key=lambda row: row["horizon_end_day"])
        selected.append(str(winner["run_id"]))
        cursor = _day(winner["horizon_end_day"]) + timedelta(days=1)
    return {
        "status": "complete",
        "start_day": start_day.isoformat(),
        "end_day": end_day.isoformat(),
        "run_ids": selected,
    }


def _optimize_stores(stores: dict[str, Path | str]) -> dict[str, Any]:
    """Refresh SQLite planner statistics after the materialized writes."""
    results: dict[str, Any] = {}
    for label, value in stores.items():
        path = Path(value)
        if not path.is_file():
            results[label] = {"status": "missing", "path": str(path)}
            continue
        started = time.monotonic()
        conn = sqlite3.connect(path, timeout=60.0)
        try:
            index_count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type = 'index'"
                ).fetchone()[0]
            )
            conn.execute("PRAGMA optimize")
            conn.commit()
            checkpoint_row = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        finally:
            conn.close()
        checkpoint = tuple(int(value) for value in checkpoint_row)
        results[label] = {
            "status": "optimized",
            "path": str(path),
            "index_count": index_count,
            "wal_checkpoint": {
                "busy": checkpoint[0],
                "log_frames": checkpoint[1],
                "checkpointed_frames": checkpoint[2],
            },
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
        }
    return results


def _warm_evidence_views(
    *,
    base_url: str = DEFAULT_VIEW_BASE_URL,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    """Warm the always-on app after a new publication invalidates its caches."""
    normalized = base_url.rstrip("/")
    started = time.monotonic()
    requests: list[dict[str, Any]] = []
    try:
        with httpx.Client(
            base_url=normalized,
            timeout=httpx.Timeout(30.0, connect=3.0),
            transport=transport,
        ) as client:
            dates_started = time.monotonic()
            dates_response = client.get("/api/events/dates")
            dates_response.raise_for_status()
            dates_payload = dates_response.json()
            requests.append(
                {
                    "path": "/api/events/dates",
                    "status_code": dates_response.status_code,
                    "duration_ms": round(
                        (time.monotonic() - dates_started) * 1000, 3
                    ),
                }
            )
            date_from = str(dates_payload.get("date_from") or "")
            date_to = str(dates_payload.get("date_to") or "")
            current_days = [
                str(item["day"])
                for item in dates_payload.get("dates") or []
                if date_from <= str(item.get("day") or "") <= date_to
            ]
            for day in current_days:
                request_started = time.monotonic()
                response = client.get(
                    "/api/events",
                    params={
                        "date": day,
                        "lane": "all",
                        "sort": "attention",
                        "routing": "relevant",
                        "q": "",
                        "event_id": "",
                        "include_evidence": "false",
                        "limit": 20,
                        "offset": 0,
                    },
                )
                response.raise_for_status()
                requests.append(
                    {
                        "path": "/api/events",
                        "day": day,
                        "status_code": response.status_code,
                        "duration_ms": round(
                            (time.monotonic() - request_started) * 1000, 3
                        ),
                    }
                )
            artifact_started = time.monotonic()
            artifact_response = client.get("/api/artifacts/dates")
            artifact_response.raise_for_status()
            requests.append(
                {
                    "path": "/api/artifacts/dates",
                    "status_code": artifact_response.status_code,
                    "duration_ms": round(
                        (time.monotonic() - artifact_started) * 1000, 3
                    ),
                }
            )
    except (httpx.HTTPError, ValueError) as exc:
        return {
            "status": "unavailable",
            "base_url": normalized,
            "error": f"{type(exc).__name__}: {exc}",
            "requests": requests,
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
        }
    return {
        "status": "ready",
        "base_url": normalized,
        "event_run_id": dates_payload.get("run_id"),
        "days_warmed": len(current_days),
        "requests": requests,
        "duration_ms": round((time.monotonic() - started) * 1000, 3),
    }


def refresh_evidence(
    *,
    through: str | date,
    days: int = 9,
    collection_days: int | None = None,
    workers: int = 32,
    timeout_seconds: float = 30.0,
    artifact_limit: int | None = None,
    x_article_limit: int | None = None,
    reader_fallback: bool = True,
    collect: bool = True,
    registry_db: Path | str = store.DEFAULT_DB_PATH,
    raw_db: Path | str = x_content.DEFAULT_DB_PATH,
    collection_db: Path | str = x_daily_collection.DEFAULT_MANIFEST_PATH,
    feed_db: Path | str = signal_feed.DEFAULT_FEED_DB,
    events_db: Path | str = signal_events.DEFAULT_EVENTS_DB,
    artifact_db: Path | str = artifacts.DEFAULT_DB,
    key_file: Path = sources.DEFAULT_TWITTERAPI_IO_KEY_FILE,
    view_warmup: bool = True,
    view_base_url: str = DEFAULT_VIEW_BASE_URL,
    progress: Callable[[str, str], None] | None = None,
) -> dict[str, Any]:
    """Refresh every deterministic Evidence stage, reusing valid cached work."""
    end = _day(through)
    if days < 1 or days > 90:
        raise ValueError("days must be between 1 and 90")
    if collection_days is not None and not 1 <= collection_days <= days:
        raise ValueError("collection_days must be between 1 and days")
    if workers < 1 or workers > 64:
        raise ValueError("workers must be between 1 and 64")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    if (artifact_limit is not None and artifact_limit < 0) or (
        x_article_limit is not None and x_article_limit < 0
    ):
        raise ValueError("artifact limits cannot be negative")
    start = end - timedelta(days=days - 1)
    collection_start = end - timedelta(days=(collection_days or days) - 1)

    collection: dict[str, Any]
    collection_coverage: dict[str, Any]
    if collect:
        if progress:
            progress("collection", "running")
        client = x_content.create_client(
            db_path=raw_db,
            key_file=key_file.expanduser(),
            timeout=timeout_seconds,
            page_sleep_seconds=0.0,
        )
        try:
            collection = x_daily_collection.execute_collection(
                client=client,
                registry_path=registry_db,
                raw_path=raw_db,
                manifest_path=collection_db,
                start_day=collection_start,
                end_day=end,
                workers=workers,
            )
        finally:
            client.close()
        if int(collection.get("failures", 0)) or int(
            collection.get("unfinished_accounts", 0)
        ):
            raise sources.SourceCliError(
                code="E_COLLECTION_INCOMPLETE",
                message="X collection is incomplete.",
                hint="Resume the same command after fixing the reported account failures.",
                exit_code=4,
                retryable=True,
            )
        if collection_start > start:
            collection_coverage = _completed_collection_coverage(
                manifest_path=collection_db,
                start_day=start,
                end_day=end,
                contract=str(collection["contract"]),
                cohort_sha256=str(collection["cohort_sha256"]),
            )
            if collection_coverage["status"] != "complete":
                raise sources.SourceCliError(
                    code="E_COLLECTION_COVERAGE_GAP",
                    message=(
                        "Completed collection runs do not cover the retained "
                        "publication window."
                    ),
                    hint="Increase --collection-days and resume the same command.",
                    exit_code=2,
                    retryable=False,
                )
        else:
            collection_coverage = {
                "status": "complete",
                "start_day": start.isoformat(),
                "end_day": end.isoformat(),
                "run_ids": [str(collection.get("run_id") or "")],
            }
        if progress:
            progress("collection", "complete")
    else:
        collection = {
            "status": "skipped",
            "start_day": collection_start.isoformat(),
            "end_day": end.isoformat(),
        }
        collection_coverage = {
            "status": "skipped",
            "start_day": start.isoformat(),
            "end_day": end.isoformat(),
            "run_ids": [],
        }

    if progress:
        progress("feed", "running")
    feed = signal_feed.materialize(
        source_db=raw_db,
        feed_db=feed_db,
        through=end,
        days=days,
    )
    events = signal_events.materialize(
        feed_db=feed_db,
        events_db=events_db,
        feed_run_id=str(feed["run_id"]),
    )
    publication = signal_events.publish(
        events_db=events_db,
        feed_db=feed_db,
        event_run_id=str(events["run_id"]),
    )
    if progress:
        progress("feed", "complete")
        progress("artifacts", "running")
    catalog = artifacts.import_feed_events(
        db_path=artifact_db,
        feed_db=feed_db,
        events_db=events_db,
    )

    content: dict[str, Any] | None = None
    if artifact_limit is None:
        content = artifact_fetch.fetch_all_supported(
            db_path=artifact_db,
            workers=workers,
        )
    elif artifact_limit:
        content = artifact_fetch.fetch_cohort(db_path=artifact_db, limit=artifact_limit)
    arxiv: dict[str, Any] | None = None
    if artifact_limit != 0:
        arxiv = artifact_arxiv.fetch_arxiv_metadata(db_path=artifact_db)
    x_articles: dict[str, Any] | None = None
    if x_article_limit is None:
        x_articles = artifact_x_articles.fetch_x_articles(
            db_path=artifact_db,
            limit=None,
            key_file=key_file.expanduser(),
        )
    elif x_article_limit:
        x_articles = artifact_x_articles.fetch_x_articles(
            db_path=artifact_db,
            limit=x_article_limit,
            key_file=key_file.expanduser(),
        )
    fallback: dict[str, Any] | None = None
    if reader_fallback and artifact_limit != 0:
        fallback = artifact_fetch.recover_with_jina_reader(
            db_path=artifact_db,
            workers=min(workers, 16),
        )
    if progress:
        progress("artifacts", "complete")
        progress("maintenance", "running")
    index_maintenance = _optimize_stores(
        {"feed": feed_db, "events": events_db, "artifacts": artifact_db}
    )
    view_cache = (
        _warm_evidence_views(base_url=view_base_url)
        if view_warmup
        else {"status": "skipped", "base_url": view_base_url}
    )
    if progress:
        progress("maintenance", "complete")

    return {
        "range": {"start_day": start.isoformat(), "end_day": end.isoformat()},
        "collection_range": {
            "start_day": collection_start.isoformat(),
            "end_day": end.isoformat(),
        },
        "collection": collection,
        "collection_coverage": collection_coverage,
        "feed": feed,
        "events": events,
        "publication": publication,
        "artifacts": catalog,
        "content_fetch": content,
        "arxiv_fetch": arxiv,
        "x_article_fetch": x_articles,
        "reader_fallback": fallback,
        "index_maintenance": index_maintenance,
        "view_cache": view_cache,
    }


def _result(
    *,
    status: str,
    data: dict[str, Any] | None,
    error: dict[str, Any] | None,
    started: float,
    request_id: str,
) -> dict[str, Any]:
    return {
        "schema_version": CLI_SCHEMA_VERSION,
        "command": "evidence-refresh",
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
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
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
    data = payload["data"] or {}
    collection = data.get("collection") or {}
    publication = data.get("publication") or {}
    print(
        " ".join(
            (
                "status=ok",
                f"collection_run_id={collection.get('run_id', '')}",
                f"provider_requests={collection.get('provider_requests', 0)}",
                f"event_run_id={publication.get('event_run_id', publication.get('run_id', ''))}",
            )
        )
    )


def main(argv: list[str] | None = None) -> int:
    started = time.monotonic()
    request_id = str(uuid.uuid4())
    parser = sources.JsonArgumentParser(
        prog="fli evidence-refresh",
        description=(
            "Refresh raw X evidence, Feed Events, source links, and supported "
            "artifact text with cache reuse at every stage."
        ),
        epilog=(
            "Example:\n"
            "  fli evidence-refresh --through 2026-07-15 --days 11 "
            "--collection-days 3 --workers 32 --no-input --json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--through", required=True, help="Latest complete UTC day.")
    parser.add_argument("--days", type=int, default=9)
    parser.add_argument(
        "--collection-days",
        type=int,
        default=None,
        help=(
            "Collect only the latest N days while retaining --days in the "
            "published Feed; completed collection runs must cover the earlier range."
        ),
    )
    parser.add_argument("--workers", type=int, default=32)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument(
        "--artifact-limit",
        type=int,
        default=None,
        help="Bound direct extraction for a calibration run; default fetches all supported.",
    )
    parser.add_argument(
        "--x-article-limit",
        type=int,
        default=None,
        help="Bound X Article extraction; default fetches all catalogued X Articles.",
    )
    parser.add_argument("--skip-collection", action="store_true")
    parser.add_argument("--no-reader-fallback", action="store_true")
    parser.add_argument("--no-view-warmup", action="store_true")
    parser.add_argument("--view-base-url", default=DEFAULT_VIEW_BASE_URL)
    parser.add_argument("--key-file", type=Path, default=sources.DEFAULT_TWITTERAPI_IO_KEY_FILE)
    parser.add_argument("--progress", choices=("off", "plain"), default="plain")
    parser.add_argument("--no-input", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true")
    mode.add_argument("--plain", action="store_true")
    args = None
    try:
        args = parser.parse_args(argv)
        progress = None
        if args.progress == "plain":
            progress = lambda stage, status: print(
                f"stage={stage} status={status}", file=sys.stderr, flush=True
            )
        result = refresh_evidence(
            through=args.through,
            days=args.days,
            collection_days=args.collection_days,
            workers=args.workers,
            timeout_seconds=args.timeout_seconds,
            artifact_limit=args.artifact_limit,
            x_article_limit=args.x_article_limit,
            reader_fallback=not args.no_reader_fallback,
            collect=not args.skip_collection,
            key_file=args.key_file,
            view_warmup=not args.no_view_warmup,
            view_base_url=args.view_base_url,
            progress=progress,
        )
    except KeyboardInterrupt:
        payload = _result(
            status="error",
            data=None,
            error={
                "code": "E_INTERRUPTED",
                "message": "Evidence refresh was interrupted.",
                "retryable": True,
                "hint": "Resume the same command; completed account work is retained.",
            },
            started=started,
            request_id=request_id,
        )
        _print_result(payload, plain=bool(args and args.plain))
        return 5
    except sources.SourceCliError as exc:
        payload = _result(
            status="error",
            data=None,
            error={
                "code": exc.code,
                "message": exc.message,
                "retryable": exc.retryable,
                "hint": exc.hint,
            },
            started=started,
            request_id=request_id,
        )
        _print_result(payload, plain=bool(args and args.plain))
        return exc.exit_code
    except (ValueError, FileNotFoundError) as exc:
        payload = _result(
            status="error",
            data=None,
            error={
                "code": "E_VALIDATION",
                "message": str(exc),
                "retryable": False,
                "hint": "Check the requested dates, windows, paths, and numeric limits.",
            },
            started=started,
            request_id=request_id,
        )
        _print_result(payload, plain=bool(args and args.plain))
        return 2
    except httpx.TimeoutException as exc:
        payload = _result(
            status="error",
            data=None,
            error={
                "code": "E_TIMEOUT",
                "message": str(exc) or "A remote dependency timed out.",
                "retryable": True,
                "hint": "Resume the same command or increase --timeout-seconds.",
            },
            started=started,
            request_id=request_id,
        )
        _print_result(payload, plain=bool(args and args.plain))
        return 5
    except Exception as exc:
        payload = _result(
            status="error",
            data=None,
            error={
                "code": "E_INTERNAL",
                "message": str(exc) or type(exc).__name__,
                "retryable": False,
                "hint": "Inspect the command inputs and repository checks before retrying.",
            },
            started=started,
            request_id=request_id,
        )
        _print_result(payload, plain=bool(args and args.plain))
        return 1
    payload = _result(
        status="ok",
        data=result,
        error=None,
        started=started,
        request_id=request_id,
    )
    _print_result(payload, plain=args.plain)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
