#!/usr/bin/env python3
"""Maintain the sharded Frontier Lab Intelligence build log.

The CLI is machine-primary: JSON is the default output, every operation is
non-interactive, and normal reads are bounded. The complete Markdown timeline
remains a generated submission artifact rather than cold-start context.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Iterator, Sequence


REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_LOG_DIR = REPO_ROOT / "docs/references/build-log"
ARCHIVE_DIR = BUILD_LOG_DIR / "archive"
CURRENT = BUILD_LOG_DIR / "current.jsonl"
MD = REPO_ROOT / "docs/references/build-log.md"
LOCK = REPO_ROOT / "tmp/build-log.lock"

BEGIN = "<!-- BEGIN GENERATED: build timeline (use scripts/build-log.py) -->"
END = "<!-- END GENERATED -->"
REQUIRED = ("date", "title", "intent", "action", "evidence", "impact_next", "tools_spend")
SCHEMA_VERSION = "1.0"
CURRENT_MAX_BYTES = 64 * 1024
MAX_QUERY_LIMIT = 50


@dataclass(frozen=True)
class Record:
    entry: dict[str, str]
    path: Path
    line: int


class ClientError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        hint: str,
        exit_code: int = 2,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.exit_code = exit_code
        self.retryable = retryable


class MachineArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ClientError(
            "E_USAGE",
            message,
            hint=f"Run `{self.prog} --help` for the supported command contract.",
        )


def display_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def source_paths() -> list[Path]:
    archived = sorted(ARCHIVE_DIR.glob("*.jsonl")) if ARCHIVE_DIR.exists() else []
    return [*archived, *([CURRENT] if CURRENT.exists() else [])]


def validate_entry(raw: object, *, location: str) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise ClientError(
            "E_INVALID_LOG",
            f"{location}: entry must be a JSON object",
            hint="Repair the named JSONL line before retrying.",
        )

    missing = [field for field in REQUIRED if not isinstance(raw.get(field), str) or not raw[field].strip()]
    if missing:
        raise ClientError(
            "E_INVALID_LOG",
            f"{location}: missing non-empty string fields: {', '.join(missing)}",
            hint="Provide every documented build-log field as a non-empty string.",
        )

    unknown = sorted(set(raw) - set(REQUIRED))
    if unknown:
        raise ClientError(
            "E_INVALID_LOG",
            f"{location}: unknown fields: {', '.join(unknown)}",
            hint=f"Use only these fields: {', '.join(REQUIRED)}.",
        )

    try:
        parsed_date = date.fromisoformat(raw["date"])
    except ValueError as exc:
        raise ClientError(
            "E_INVALID_LOG",
            f"{location}: date must use YYYY-MM-DD",
            hint="Correct the date and retry validation.",
        ) from exc
    if parsed_date.isoformat() != raw["date"]:
        raise ClientError(
            "E_INVALID_LOG",
            f"{location}: date must use canonical YYYY-MM-DD",
            hint=f"Use {parsed_date.isoformat()}.",
        )

    return {field: raw[field].strip() for field in REQUIRED}


def records_from_path(path: Path) -> list[Record]:
    records: list[Record] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ClientError(
            "E_IO",
            f"Could not read {display_path(path)}: {exc}",
            hint="Check the file path and permissions, then retry.",
            exit_code=1,
            retryable=True,
        ) from exc

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        location = f"{display_path(path)}:{line_number}"
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ClientError(
                "E_INVALID_LOG",
                f"{location}: invalid JSON ({exc.msg})",
                hint="Repair the named JSONL line before retrying.",
            ) from exc
        records.append(Record(validate_entry(raw, location=location), path, line_number))
    return records


def load_records() -> list[Record]:
    paths = source_paths()
    if not paths:
        raise ClientError(
            "E_INVALID_LOG",
            "No build-log JSONL sources exist",
            hint=f"Create {display_path(CURRENT)} before retrying.",
        )

    records = [record for path in paths for record in records_from_path(path)]
    seen: dict[str, Record] = {}
    previous: Record | None = None
    for record in records:
        if previous and record.entry["date"] < previous.entry["date"]:
            raise ClientError(
                "E_INVALID_LOG",
                f"{display_path(record.path)}:{record.line}: date precedes the previous entry",
                hint="Keep archive shards and entries in chronological order.",
            )
        fingerprint = json.dumps(record.entry, ensure_ascii=False, sort_keys=True)
        if fingerprint in seen:
            first = seen[fingerprint]
            raise ClientError(
                "E_INVALID_LOG",
                f"{display_path(record.path)}:{record.line}: exact duplicate of "
                f"{display_path(first.path)}:{first.line}",
                hint="Remove the duplicate entry and retry.",
            )
        seen[fingerprint] = record
        previous = record
    return records


@contextmanager
def append_lock() -> Iterator[None]:
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def next_archive_path(records: Sequence[Record]) -> Path:
    first_date = records[0].entry["date"]
    last_date = records[-1].entry["date"]
    stem = first_date if first_date == last_date else f"{first_date}--{last_date}"
    candidate = ARCHIVE_DIR / f"{stem}.jsonl"
    suffix = 2
    while candidate.exists():
        candidate = ARCHIVE_DIR / f"{stem}.part-{suffix:02d}.jsonl"
        suffix += 1
    return candidate


def rotate_current_if_needed() -> Path | None:
    if not CURRENT.exists() or CURRENT.stat().st_size < CURRENT_MAX_BYTES:
        return None
    current_records = records_from_path(CURRENT)
    if not current_records:
        return None

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    target = next_archive_path(current_records)
    CURRENT.replace(target)
    CURRENT.touch()
    return target


def entry_fingerprint(entry: dict[str, str]) -> str:
    return json.dumps(entry, ensure_ascii=False, sort_keys=True)


def add_entry(args: argparse.Namespace) -> dict[str, object]:
    raw = {
        "date": args.date or date.today().isoformat(),
        "title": args.title,
        "intent": args.intent,
        "action": args.action,
        "evidence": args.evidence,
        "impact_next": args.impact_next,
        "tools_spend": args.tools_spend,
    }
    entry = validate_entry(raw, location="new entry")

    with append_lock():
        BUILD_LOG_DIR.mkdir(parents=True, exist_ok=True)
        CURRENT.touch(exist_ok=True)
        records = load_records()
        fingerprint = entry_fingerprint(entry)
        for record in records:
            if entry_fingerprint(record.entry) == fingerprint:
                return {
                    "appended": False,
                    "entry": entry,
                    "source": display_path(record.path),
                    "line": record.line,
                    "rotated_to": None,
                }

        if records and entry["date"] < records[-1].entry["date"]:
            raise ClientError(
                "E_INVALID_ENTRY_DATE",
                f"New entry date {entry['date']} precedes latest date {records[-1].entry['date']}",
                hint="Use today's date unless deliberately repairing the archive.",
            )

        rotated_to = rotate_current_if_needed()
        serialized = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
        with CURRENT.open("a+", encoding="utf-8") as current_file:
            current_file.seek(0, os.SEEK_END)
            if current_file.tell() > 0:
                current_file.seek(current_file.tell() - 1)
                if current_file.read(1) != "\n":
                    current_file.seek(0, os.SEEK_END)
                    current_file.write("\n")
            current_file.seek(0, os.SEEK_END)
            current_file.write(serialized + "\n")
            current_file.flush()
            os.fsync(current_file.fileno())

        line = len(records_from_path(CURRENT))
        return {
            "appended": True,
            "entry": entry,
            "source": display_path(CURRENT),
            "line": line,
            "rotated_to": display_path(rotated_to) if rotated_to else None,
        }


def bounded_limit(value: int) -> int:
    if value < 1 or value > MAX_QUERY_LIMIT:
        raise ClientError(
            "E_INVALID_LIMIT",
            f"limit must be between 1 and {MAX_QUERY_LIMIT}",
            hint=f"Choose --limit 1..{MAX_QUERY_LIMIT} to keep agent context bounded.",
        )
    return value


def recent_entries(args: argparse.Namespace) -> dict[str, object]:
    limit = bounded_limit(args.limit)
    with append_lock():
        records = load_records()
    selected = records[-limit:]
    return {
        "total_count": len(records),
        "returned_count": len(selected),
        "limit": limit,
        "entries": [record.entry for record in selected],
    }


def search_entries(args: argparse.Namespace) -> dict[str, object]:
    limit = bounded_limit(args.limit)
    query = args.query.strip()
    if not query:
        raise ClientError(
            "E_USAGE",
            "search query must not be empty",
            hint="Provide a word or phrase to search across all build-log fields.",
        )
    needle = query.casefold()
    with append_lock():
        records = load_records()
    matches = [
        record
        for record in records
        if any(needle in record.entry[field].casefold() for field in REQUIRED)
    ]
    selected = matches[-limit:]
    return {
        "query": query,
        "match_count": len(matches),
        "returned_count": len(selected),
        "limit": limit,
        "entries": [record.entry for record in selected],
    }


def validate_log(_args: argparse.Namespace) -> dict[str, object]:
    with append_lock():
        records = load_records()
        paths = source_paths()
    return {
        "entry_count": len(records),
        "source_count": len(paths),
        "sources": [display_path(path) for path in paths],
        "first_date": records[0].entry["date"] if records else None,
        "last_date": records[-1].entry["date"] if records else None,
        "current_bytes": CURRENT.stat().st_size if CURRENT.exists() else 0,
        "rotation_bytes": CURRENT_MAX_BYTES,
    }


def cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def render_timeline(entries: Sequence[dict[str, str]]) -> str:
    lines = [
        BEGIN,
        "",
        "| Date | Intent / trigger | Decision / action | Evidence | Impact / next | Tools / spend |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for entry in entries:
        lines.append(
            "| "
            + " | ".join(
                cell(entry[field])
                for field in ("date", "intent", "action", "evidence", "impact_next", "tools_spend")
            )
            + " |"
        )
    lines += ["", END]
    return "\n".join(lines)


def render_log(_args: argparse.Namespace) -> dict[str, object]:
    with append_lock():
        records = load_records()
        entries = [record.entry for record in records]
        timeline = render_timeline(entries)
        try:
            text = MD.read_text(encoding="utf-8")
        except OSError as exc:
            raise ClientError(
                "E_IO",
                f"Could not read {display_path(MD)}: {exc}",
                hint="Restore the Markdown build-log shell before rendering.",
                exit_code=1,
                retryable=True,
            ) from exc

        if BEGIN in text and END in text:
            head, rest = text.split(BEGIN, 1)
            _, tail = rest.split(END, 1)
            rendered = head + timeline + tail
        else:
            heading = "## Build Timeline"
            next_section = "## Learning Notes"
            if heading not in text or next_section not in text:
                raise ClientError(
                    "E_INVALID_MARKDOWN_SHELL",
                    f"{display_path(MD)} is missing its timeline or learning-notes heading",
                    hint="Restore both headings, then rerun render.",
                )
            head, rest = text.split(heading, 1)
            _, tail = rest.split(next_section, 1)
            rendered = head + heading + "\n\n" + timeline + "\n\n" + next_section + tail

        changed = rendered != text
        if changed:
            MD.write_text(rendered, encoding="utf-8")
    return {"changed": changed, "entry_count": len(entries), "output": display_path(MD)}


def build_parser() -> MachineArgumentParser:
    parser = MachineArgumentParser(description=__doc__)
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="emit the default JSON result envelope")
    output.add_argument("--plain", action="store_true", help="emit concise operator-oriented text")
    parser.add_argument("--no-input", action="store_true", help="guarantee non-interactive execution")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add = subparsers.add_parser("add", help="append one validated milestone entry")
    add.add_argument("--date", help="entry date in YYYY-MM-DD; defaults to today")
    add.add_argument("--title", required=True)
    add.add_argument("--intent", required=True)
    add.add_argument("--action", required=True)
    add.add_argument("--evidence", required=True)
    add.add_argument("--impact-next", dest="impact_next", required=True)
    add.add_argument("--tools-spend", dest="tools_spend", required=True)
    add.set_defaults(handler=add_entry)

    recent = subparsers.add_parser("recent", help="return the newest bounded set of entries")
    recent.add_argument("--limit", type=int, default=10)
    recent.set_defaults(handler=recent_entries)

    search = subparsers.add_parser("search", help="search all fields and return bounded recent matches")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    search.set_defaults(handler=search_entries)

    validate = subparsers.add_parser("validate", help="validate every source shard without writing")
    validate.set_defaults(handler=validate_log)

    render = subparsers.add_parser("render", help="regenerate the complete Markdown submission artifact")
    render.set_defaults(handler=render_log)
    return parser


def envelope(
    *,
    command: str,
    status: str,
    data: dict[str, object] | None,
    error: dict[str, object] | None,
    request_id: str,
    started: float,
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "status": status,
        "data": data,
        "error": error,
        "meta": {
            "request_id": request_id,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "timestamp_utc": datetime.now(UTC).isoformat(),
        },
    }


def emit(result: dict[str, object], *, plain: bool) -> None:
    if not plain:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return

    if result["status"] == "error":
        error = result["error"]
        assert isinstance(error, dict)
        print(f"{error['code']}: {error['message']} Hint: {error['hint']}", file=sys.stderr)
        return

    command = result["command"]
    data = result["data"]
    assert isinstance(data, dict)
    if command in {"build-log recent", "build-log search"}:
        for entry in data["entries"]:
            print(f"{entry['date']} — {entry['title']}")
    elif command == "build-log add":
        verb = "appended" if data["appended"] else "already present"
        print(f"build-log add: {verb} — {data['entry']['title']}")
    elif command == "build-log validate":
        print(
            f"build-log validate: OK ({data['entry_count']} entries across "
            f"{data['source_count']} sources)"
        )
    elif command == "build-log render":
        state = "regenerated" if data["changed"] else "unchanged"
        print(f"build-log render: {state} ({data['entry_count']} entries)")


def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = list(argv if argv is not None else sys.argv[1:])
    plain = "--plain" in raw_argv
    request_id = str(uuid.uuid4())
    started = time.monotonic()
    command = "build-log"
    for token in raw_argv:
        if token in {"add", "recent", "search", "validate", "render"}:
            command = f"build-log {token}"
            break
    try:
        args = build_parser().parse_args(raw_argv)
        command = f"build-log {args.command}"
        data = args.handler(args)
        result = envelope(
            command=command,
            status="ok",
            data=data,
            error=None,
            request_id=request_id,
            started=started,
        )
        emit(result, plain=plain)
        return 0
    except ClientError as exc:
        result = envelope(
            command=command,
            status="error",
            data=None,
            error={
                "code": exc.code,
                "message": exc.message,
                "retryable": exc.retryable,
                "hint": exc.hint,
            },
            request_id=request_id,
            started=started,
        )
        emit(result, plain=plain)
        return exc.exit_code
    except KeyboardInterrupt:
        result = envelope(
            command=command,
            status="error",
            data=None,
            error={
                "code": "E_INTERRUPTED",
                "message": "Command interrupted",
                "retryable": True,
                "hint": "Retry the command; completed appends are durable and exact retries are idempotent.",
            },
            request_id=request_id,
            started=started,
        )
        emit(result, plain=plain)
        return 5
    except OSError as exc:
        result = envelope(
            command=command,
            status="error",
            data=None,
            error={
                "code": "E_IO",
                "message": f"Filesystem operation failed: {exc}",
                "retryable": True,
                "hint": "Check repository paths and permissions, then retry.",
            },
            request_id=request_id,
            started=started,
        )
        emit(result, plain=plain)
        return 1
    except Exception as exc:  # pragma: no cover - last-resort contract guard
        result = envelope(
            command=command,
            status="error",
            data=None,
            error={
                "code": "E_INTERNAL",
                "message": f"Unexpected {type(exc).__name__}",
                "retryable": False,
                "hint": "Run `scripts/build-log.py validate`, then inspect the client implementation.",
            },
            request_id=request_id,
            started=started,
        )
        emit(result, plain=plain)
        return 1


if __name__ == "__main__":
    sys.exit(main())
