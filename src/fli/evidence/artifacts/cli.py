"""Machine-first command adapter for the Artifact catalog and fetchers."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
import time
from typing import Any
import uuid

from fli.evidence import events as signal_events
from fli.evidence import feed as signal_feed
from fli.evidence.artifacts.store import (
    DEFAULT_DB,
    audit_primary_author_lineage,
    connect,
    import_feed_events,
    import_reviewed_supplements,
    inspect_artifacts,
    summary,
)
from fli.ingestion import sources


RESULT_SCHEMA_VERSION = "1.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


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
    import_parser = sub.add_parser(
        "import-feed",
        help="Index first-party URLs from the published Feed Events.",
    )
    import_parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    import_parser.add_argument("--feed-db", type=Path, default=signal_feed.DEFAULT_FEED_DB)
    import_parser.add_argument("--events-db", type=Path, default=signal_events.DEFAULT_EVENTS_DB)
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
    audit_parser = sub.add_parser(
        "audit-lineage",
        help="Verify that live artifacts come only from primary-account posts.",
    )
    audit_parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    audit_parser.add_argument(
        "--feed-db", type=Path, default=signal_feed.DEFAULT_FEED_DB
    )
    _add_output_arguments(audit_parser)
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
    revalidate_parser = sub.add_parser(
        "revalidate-content",
        help="Quarantine stored successes that fail the current content contract.",
    )
    revalidate_parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    _add_output_arguments(revalidate_parser)
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
        if args.action == "import-feed":
            data = import_feed_events(
                db_path=args.db,
                feed_db=args.feed_db,
                events_db=args.events_db,
            )
        elif args.action == "import-reviewed-supplements":
            data = import_reviewed_supplements(
                db_path=args.db,
                manifest_path=args.manifest,
                triage_db=args.triage_db,
            )
        elif args.action == "fetch":
            from fli.evidence.artifacts import fetch as artifact_fetch

            if args.limit is not None and args.artifact_id is not None:
                raise ValueError("--limit cannot be combined with --artifact-id")
            data = artifact_fetch.fetch_cohort(
                db_path=args.db,
                limit=args.limit if args.limit is not None else 30,
                artifact_ids=args.artifact_id,
            )
        elif args.action == "reader-fallback":
            from fli.evidence.artifacts import fetch as artifact_fetch

            data = artifact_fetch.recover_with_jina_reader(db_path=args.db)
        elif args.action == "revalidate-content":
            from fli.evidence.artifacts import fetch as artifact_fetch

            data = artifact_fetch.revalidate_successful_fetches(db_path=args.db)
        elif args.action == "fetch-x-articles":
            from fli.evidence.artifacts import x_articles as artifact_x_articles

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
            from fli.evidence.artifacts import fetch as artifact_fetch

            conn = connect(args.db)
            data = artifact_fetch.inspect_fetches(
                conn, fetch_run_id=args.fetch_run_id
            )
            conn.close()
        elif args.action == "audit-lineage":
            data = audit_primary_author_lineage(
                db_path=args.db,
                feed_db=args.feed_db,
            )
            if not data["passed"]:
                _print_result(
                    _result(
                        command=command,
                        status="error",
                        data=data,
                        error={
                            "code": "E_INTEGRITY",
                            "message": "Artifact primary-author lineage audit failed.",
                            "retryable": False,
                            "hint": (
                                "Inspect data.violation_reasons and rebuild the "
                                "catalog from the canonical Feed."
                            ),
                        },
                        started=started,
                        request_id=request_id,
                    ),
                    plain=args.plain,
                )
                return 1
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
