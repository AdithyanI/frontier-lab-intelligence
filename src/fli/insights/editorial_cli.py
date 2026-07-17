"""Machine-primary client for the daily agent editorial workbench."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time
from typing import Any, Callable
from uuid import uuid4

from openai import APIConnectionError, APITimeoutError, AuthenticationError

from fli.insights import editorial
from fli.insights import editorial_runs
from fli.registry import classification as entity_kinds


CLI_SCHEMA_VERSION = "1.0"


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical_json(value: Any, *, pretty: bool = False) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    )


def _meta(request_id: str, started: float) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "duration_ms": round((time.monotonic() - started) * 1000, 3),
        "timestamp_utc": _now(),
    }


def _success(command: str, data: Any, *, request_id: str, started: float) -> dict[str, Any]:
    return {
        "schema_version": CLI_SCHEMA_VERSION,
        "command": command,
        "status": "ok",
        "data": data,
        "error": None,
        "meta": _meta(request_id, started),
    }


def _error(
    command: str,
    *,
    code: str,
    message: str,
    retryable: bool,
    hint: str,
    request_id: str,
    started: float,
) -> dict[str, Any]:
    return {
        "schema_version": CLI_SCHEMA_VERSION,
        "command": command,
        "status": "error",
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "hint": hint,
        },
        "meta": _meta(request_id, started),
    }


def _add_output_flags(parser: argparse.ArgumentParser) -> None:
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true", help="Emit stable JSON (default).")
    mode.add_argument("--plain", action="store_true", help="Emit a compact inspection view.")
    parser.add_argument("--no-input", action="store_true", help="Never prompt (always honored).")


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="fli daily-intelligence",
        description="Prepare, retrieve, validate, and import agent-authored daily intelligence.",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    contract = sub.add_parser("contract", help="Inspect the draft and persistence contract.")
    _add_output_flags(contract)

    context = sub.add_parser("context", help="Read the audience context the agent must apply.")
    context.add_argument("--audience", choices=editorial.AUDIENCES, required=True)
    _add_output_flags(context)

    prepare = sub.add_parser("prepare", help="Freeze one union-positive daily Evidence workspace.")
    prepare.add_argument("--day", required=True)
    prepare.add_argument("--routing-root", type=Path, default=editorial_runs.DEFAULT_ROUTING_ROOT)
    prepare.add_argument("--insights-db", type=Path, default=editorial_runs.DEFAULT_INSIGHTS_DB)
    prepare.add_argument("--workspace-root", type=Path, default=editorial_runs.DEFAULT_WORKSPACE_ROOT)
    prepare.add_argument("--dry-run", action="store_true")
    _add_output_flags(prepare)

    search = sub.add_parser("search", help="Search frozen Event text without model calls.")
    search.add_argument("--workspace", type=Path, required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--audience", choices=editorial.AUDIENCES)
    search.add_argument("--limit", type=int, default=10)
    _add_output_flags(search)

    inspect_event = sub.add_parser("inspect-event", help="Inspect one exact frozen Event packet.")
    inspect_event.add_argument("--workspace", type=Path, required=True)
    inspect_event.add_argument("--event-id", required=True)
    _add_output_flags(inspect_event)

    index = sub.add_parser("index", help="Embed only missing or changed Event packets.")
    index.add_argument("--workspace", type=Path, required=True)
    index.add_argument("--db", type=Path, default=editorial_runs.DEFAULT_DB)
    index.add_argument("--model", default=editorial_runs.DEFAULT_MODEL)
    index.add_argument("--timeout", type=float, default=180.0)
    index.add_argument("--progress", choices=("off", "plain"), default="plain")
    _add_output_flags(index)

    similar = sub.add_parser("similar", help="Return nearest indexed Events; never merge them.")
    similar.add_argument("--workspace", type=Path, required=True)
    similar.add_argument("--event-id", required=True)
    similar.add_argument("--db", type=Path, default=editorial_runs.DEFAULT_DB)
    similar.add_argument("--model", default=editorial_runs.DEFAULT_MODEL)
    similar.add_argument("--limit", type=int, default=10)
    similar.add_argument("--min-score", type=float, default=0.0)
    _add_output_flags(similar)

    validate = sub.add_parser("validate", help="Validate a complete draft without writing state.")
    validate.add_argument("--workspace", type=Path, required=True)
    validate.add_argument("--draft", type=Path, required=True)
    _add_output_flags(validate)

    imported = sub.add_parser("import-result", help="Atomically import one validated draft.")
    imported.add_argument("--workspace", type=Path, required=True)
    imported.add_argument("--draft", type=Path, required=True)
    imported.add_argument("--db", type=Path, default=editorial_runs.DEFAULT_DB)
    imported.add_argument("--dry-run", action="store_true")
    _add_output_flags(imported)

    inspect_run = sub.add_parser("inspect-run", help="Inspect one durable editorial run.")
    inspect_run.add_argument("--run-id", required=True)
    inspect_run.add_argument("--db", type=Path, default=editorial_runs.DEFAULT_DB)
    _add_output_flags(inspect_run)

    summary = sub.add_parser("summary", help="Inspect aggregate durable editorial state.")
    summary.add_argument("--db", type=Path, default=editorial_runs.DEFAULT_DB)
    _add_output_flags(summary)
    return parser


def _context_payload(audience: str) -> dict[str, Any]:
    path = editorial_runs.CONTEXT_PATHS[audience]
    if not path.is_file():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    return {
        "audience": audience,
        "path": editorial_runs._display_path(path),
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
        "text": text,
    }


def _plain(payload: dict[str, Any]) -> str:
    if payload["status"] == "error":
        return f"{payload['error']['code']}: {payload['error']['message']}"
    command = payload["command"]
    data = payload["data"]
    if command == "daily-intelligence.prepare":
        return (
            f"{data['run_id']} · {data['counts']['events']} Events · "
            f"{data['counts']['candidate_pairs']} audience candidates · {data['workspace']}"
        )
    if command == "daily-intelligence.search":
        return "\n".join(
            f"#{item['feed_rank']} {item['event_id']} · {item['root_text']}"
            for item in data["items"]
        )
    if command == "daily-intelligence.similar":
        return "\n".join(
            f"#{item['feed_rank']} {item['event_id']} · cosine {item['cosine_similarity']:.4f}"
            for item in data["items"]
        )
    if command == "daily-intelligence.index":
        return (
            f"{data['event_count']} Events · {data['indexed_count']} indexed · "
            f"{data['reused_count']} reused"
        )
    return _canonical_json(data, pretty=True)


def main(
    argv: list[str] | None = None,
    *,
    client_factory: Callable[[], Any] = entity_kinds.create_litellm_client,
) -> int:
    started = time.monotonic()
    request_id = str(uuid4())
    args: argparse.Namespace | None = None
    command = "daily-intelligence"
    exit_code = 0
    try:
        args = _parser().parse_args(argv)
        command = f"daily-intelligence.{args.action}"
        if args.action == "contract":
            data = {
                "cli_schema_version": CLI_SCHEMA_VERSION,
                "workspace_schema_version": editorial_runs.WORKSPACE_SCHEMA_VERSION,
                "store_schema_version": editorial_runs.STORE_SCHEMA_VERSION,
                "draft": editorial.output_contract(),
            }
        elif args.action == "context":
            data = _context_payload(args.audience)
        elif args.action == "prepare":
            data = editorial_runs.prepare_workspace(
                day=args.day,
                routing_root=args.routing_root,
                insights_db=args.insights_db,
                workspace_root=args.workspace_root,
                dry_run=args.dry_run,
            )
        elif args.action == "search":
            data = editorial_runs.search_workspace(
                args.workspace,
                query=args.query,
                audience=args.audience,
                limit=args.limit,
            )
        elif args.action == "inspect-event":
            data = editorial_runs.inspect_event(args.workspace, args.event_id)
        elif args.action == "index":
            if args.progress == "plain":
                print(
                    f"daily-intelligence: indexing missing Event embeddings with {args.model}",
                    file=sys.stderr,
                    flush=True,
                )
            data = editorial_runs.index_workspace(
                args.workspace,
                db_path=args.db,
                model=args.model,
                client_factory=client_factory,
                timeout_seconds=args.timeout,
            )
        elif args.action == "similar":
            data = editorial_runs.similar_events(
                args.workspace,
                event_id=args.event_id,
                db_path=args.db,
                model=args.model,
                limit=args.limit,
                min_score=args.min_score,
            )
        elif args.action == "validate":
            _, report, context = editorial_runs.validate_result(args.workspace, args.draft)
            data = {
                "workspace_run_id": context["manifest"]["run_id"],
                "draft": editorial_runs._display_path(args.draft),
                "result_sha256": context["result_sha256"],
                "valid": True,
                "report": report,
            }
        elif args.action == "import-result":
            data = editorial_runs.import_result(
                args.workspace,
                args.draft,
                db_path=args.db,
                dry_run=args.dry_run,
            )
        elif args.action in {"inspect-run", "summary"}:
            if not args.db.is_file():
                raise FileNotFoundError(args.db)
            conn = editorial_runs.connect(args.db)
            try:
                data = (
                    editorial_runs.run_payload(conn, args.run_id)
                    if args.action == "inspect-run"
                    else {"db": editorial_runs._display_path(args.db), **editorial_runs.summary_payload(conn)}
                )
            finally:
                conn.close()
        else:
            raise ValueError(f"unsupported action {args.action!r}")
        payload = _success(command, data, request_id=request_id, started=started)
    except AuthenticationError as error:
        exit_code = 3
        payload = _error(
            command,
            code="E_AUTH",
            message=str(error),
            retryable=False,
            hint="Repair the shared LiteLLM client credentials, then rerun the identical command.",
            request_id=request_id,
            started=started,
        )
    except (APITimeoutError, TimeoutError, KeyboardInterrupt) as error:
        exit_code = 5
        payload = _error(
            command,
            code="E_TIMEOUT" if not isinstance(error, KeyboardInterrupt) else "E_INTERRUPTED",
            message=str(error) or "Command interrupted.",
            retryable=True,
            hint="Rerun the identical command; completed embeddings and imported results are reused.",
            request_id=request_id,
            started=started,
        )
    except APIConnectionError as error:
        exit_code = 4
        payload = _error(
            command,
            code="E_DEPENDENCY_UNAVAILABLE",
            message=str(error),
            retryable=True,
            hint="Check the shared LiteLLM endpoint, then rerun the identical command.",
            request_id=request_id,
            started=started,
        )
    except FileNotFoundError as error:
        exit_code = 2
        payload = _error(
            command,
            code="E_NOT_FOUND",
            message=str(error),
            retryable=False,
            hint="Prepare the workspace or provide an existing local path.",
            request_id=request_id,
            started=started,
        )
    except (ValueError, json.JSONDecodeError) as error:
        exit_code = 2
        payload = _error(
            command,
            code="E_INVALID_INPUT",
            message=str(error),
            retryable=False,
            hint="Inspect `fli daily-intelligence contract` and correct the supplied input.",
            request_id=request_id,
            started=started,
        )
    except sqlite3.Error as error:
        exit_code = 1
        payload = _error(
            command,
            code="E_STORE",
            message=str(error),
            retryable=True,
            hint="Inspect the editorial database and retry after the local store is available.",
            request_id=request_id,
            started=started,
        )
    except Exception as error:
        exit_code = 1
        payload = _error(
            command,
            code="E_INTERNAL",
            message=f"{type(error).__name__}: {error}",
            retryable=False,
            hint="Inspect the local command inputs and repository checks before retrying.",
            request_id=request_id,
            started=started,
        )
    print(_plain(payload) if args is not None and getattr(args, "plain", False) else _canonical_json(payload))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
