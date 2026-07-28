"""Date-keyed orchestration from Evidence refresh to one Codex daily brief."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import redirect_stdout
import fcntl
import hashlib
import io
import json
import sqlite3
import sys
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TextIO
from uuid import uuid4

from fli.evidence import events as signal_events
from fli.evidence import feed as signal_feed
from fli.evidence import refresh as evidence_refresh
from fli.insights import editorial, editorial_runs
from fli.insights.codex_app_server import (
    STANDARD_SERVICE_TIER,
    CodexAppServerClient,
    CodexTaskError,
)
from fli.routing import model as routing_model
from fli.routing import runs as routing_runs
from fli.routing import view as routing_view
from fli.scoring import development_attention


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = editorial_runs.DEFAULT_DB
DEFAULT_SKILL_PATH = REPO_ROOT / ".agents/skills/fli-daily-intelligence/SKILL.md"
CLI_SCHEMA_VERSION = "1.0"
STORE_SCHEMA_VERSION = "daily-orchestration-store-v2"
RUN_CONTRACT_VERSION = "daily-orchestration-v3"
DEFAULT_CODEX_TIMEOUT_SECONDS = 4 * 60 * 60
DEFAULT_CODEX_SERVICE_TIER = STANDARD_SERVICE_TIER
DEFAULT_EVIDENCE_WINDOW_DAYS = 9
AGENT_FEEDBACK_DIR = (
    REPO_ROOT / "data/derived/daily-intelligence/agent-feedback"
)
PREPARATION_STAGES = ("evidence", "routing", "prepare")
CODEX_SETTING_KEYS = ("model", "reasoning_effort", "service_tier")
SOURCE_LINEAGE_KEYS = (
    "event_run_id",
    "feed_run_id",
    "routing_run_id",
    "routing_cohort_sha256",
    "source_rank_input_sha256",
)


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


class DailyRunError(RuntimeError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        hint: str,
        retryable: bool,
        exit_code: int,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.retryable = retryable
        self.exit_code = exit_code


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


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _agent_feedback_path(day: str) -> Path:
    return AGENT_FEEDBACK_DIR / f"{day}.md"


def _agent_feedback_prompt(day: str, output_path: Path) -> str:
    display_path = _display_path(output_path)
    return f"""The main daily-intelligence goal for {day} is complete. Do not reopen it.

Write a short, candid post-run reflection to `{display_path}`. This is feedback about the harness, not another editorial pass. Do not modify the brief, editorial database, skill, tools, product code, or goal. Only write the designated Markdown file.

Use these headings:

# Daily intelligence run reflection — {day}
## Overall assessment
## Friction encountered
## Tools or context I wished I had
## Suggested improvements
## What should be preserved
## Anything else

Ground every point in this run and clearly distinguish concrete experience from speculation. It is acceptable to say that nothing material was missing.

Under “Anything else”, answer this open question: Beyond the questions above, was there anything else you wish you had—such as a tool, command, context, data representation, permission, instruction, or workflow—that would have made this run easier, faster, more reliable, or produced a better result? Include unexpected observations even if they do not fit the earlier sections. Clearly distinguish concrete run experience from speculation. It is acceptable to say “nothing else.”
"""


def _normalize_codex_setting(value: str | None, *, name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    if name == "codex-service-tier":
        lowered = normalized.lower()
        if lowered in {"default", "normal", STANDARD_SERVICE_TIER}:
            return STANDARD_SERVICE_TIER
        if lowered == "fast":
            return "priority"
    return normalized


def _expected_effective_codex_setting(
    key: str, value: str | None
) -> str | None:
    if key == "service_tier" and value == STANDARD_SERVICE_TIER:
        return "default"
    return value


def _codex_settings(
    *,
    model: str | None,
    reasoning_effort: str | None,
    service_tier: str | None,
) -> dict[str, str | None]:
    return {
        "model": _normalize_codex_setting(model, name="codex-model"),
        "reasoning_effort": _normalize_codex_setting(
            reasoning_effort, name="codex-reasoning-effort"
        ),
        "service_tier": _normalize_codex_setting(
            service_tier, name="codex-service-tier"
        ),
    }


def _checkpoint_codex_settings(
    value: Any, *, require_resolved: bool
) -> dict[str, str | None]:
    if not isinstance(value, dict) or any(
        key not in value for key in CODEX_SETTING_KEYS
    ):
        raise DailyRunError(
            code="E_CODEX_SETTINGS_INVALID",
            message="Codex returned invalid effective model settings.",
            hint="Inspect the App Server response before resuming this task.",
            retryable=False,
            exit_code=4,
        )
    settings: dict[str, str | None] = {}
    for key in CODEX_SETTING_KEYS:
        raw = value[key]
        if raw is None:
            settings[key] = None
            continue
        normalized = str(raw).strip()
        if not normalized:
            raise DailyRunError(
                code="E_CODEX_SETTINGS_INVALID",
                message="Codex returned blank effective model settings.",
                hint="Inspect the App Server response before resuming this task.",
                retryable=False,
                exit_code=4,
            )
        settings[key] = normalized
    if require_resolved and (
        settings["model"] is None or settings["reasoning_effort"] is None
    ):
        raise DailyRunError(
            code="E_CODEX_SETTINGS_INVALID",
            message="Codex did not report an effective model and reasoning effort.",
            hint="Inspect the App Server response before resuming this task.",
            retryable=False,
            exit_code=4,
        )
    return settings


def _bound_codex_settings(
    existing_codex: dict[str, Any],
    requested: dict[str, str | None],
    *,
    thread_id: str | None,
) -> tuple[dict[str, str | None], dict[str, str | None]]:
    raw_requested = existing_codex.get("requested_settings")
    if raw_requested is None:
        if thread_id:
            raise DailyRunError(
                code="E_CODEX_SETTINGS_UNKNOWN",
                message="The persisted Codex task predates the model-settings contract.",
                hint=(
                    "Leave that task untouched and inspect its imported editorial run; "
                    "new dates record exact Codex settings before launch."
                ),
                retryable=False,
                exit_code=4,
            )
        bound_requested = dict(requested)
    else:
        bound_requested = _checkpoint_codex_settings(
            raw_requested, require_resolved=False
        )
    if thread_id:
        effective = _checkpoint_codex_settings(
            existing_codex.get("settings"), require_resolved=True
        )
        comparison = effective
        launch_settings = {
            **effective,
            "service_tier": (
                STANDARD_SERVICE_TIER
                if effective["service_tier"] == "default"
                else effective["service_tier"]
            ),
        }
    else:
        comparison = bound_requested
        launch_settings = bound_requested
    mismatches = {
        key: {"bound": comparison[key], "requested": requested[key]}
        for key in CODEX_SETTING_KEYS
        if requested[key] is not None
        and _expected_effective_codex_setting(key, requested[key])
        != _expected_effective_codex_setting(key, comparison[key])
    }
    if mismatches:
        raise DailyRunError(
            code="E_CODEX_CONFIG_MISMATCH",
            message="The daily run is already bound to different Codex model settings.",
            hint=(
                "Resume without overrides or use the exact model, reasoning effort, "
                "and service tier shown by inspect-day-run."
            ),
            retryable=False,
            exit_code=2,
        )
    return launch_settings, bound_requested


def _acquire_day_lock(db_path: Path, day: str) -> TextIO:
    lock_path = db_path.parent / ".run-day-locks" / f"{db_path.name}.{day}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        handle.close()
        raise DailyRunError(
            code="E_RUN_BUSY",
            message=f"Daily orchestration for {day} is already running.",
            hint="Wait for the existing command to finish, then inspect or resume it.",
            retryable=True,
            exit_code=5,
        ) from error
    return handle


def _release_day_lock(handle: TextIO) -> None:
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def connect(path: Path = DEFAULT_DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=60000")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS daily_orchestration_meta (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            schema_version TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS daily_orchestration_run (
            run_id TEXT PRIMARY KEY,
            day TEXT NOT NULL,
            contract_version TEXT NOT NULL,
            config_sha256 TEXT NOT NULL,
            config_json TEXT NOT NULL,
            status TEXT NOT NULL,
            stage TEXT NOT NULL,
            state_json TEXT NOT NULL,
            codex_thread_id TEXT,
            editorial_run_id TEXT,
            error_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_daily_orchestration_run_day_updated
            ON daily_orchestration_run(day, updated_at DESC, run_id);
        """
    )
    row = conn.execute(
        "SELECT schema_version FROM daily_orchestration_meta WHERE singleton = 1"
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO daily_orchestration_meta(singleton, schema_version) VALUES (1, ?)",
            (STORE_SCHEMA_VERSION,),
        )
    elif str(row["schema_version"]) == "daily-orchestration-store-v1":
        with conn:
            conn.execute("DROP INDEX IF EXISTS idx_daily_orchestration_run_day_updated")
            conn.execute(
                "ALTER TABLE daily_orchestration_run "
                "RENAME TO daily_orchestration_run_v1"
            )
            conn.execute(
                """CREATE TABLE daily_orchestration_run (
                       run_id TEXT PRIMARY KEY,
                       day TEXT NOT NULL,
                       contract_version TEXT NOT NULL,
                       config_sha256 TEXT NOT NULL,
                       config_json TEXT NOT NULL,
                       status TEXT NOT NULL,
                       stage TEXT NOT NULL,
                       state_json TEXT NOT NULL,
                       codex_thread_id TEXT,
                       editorial_run_id TEXT,
                       error_json TEXT,
                       created_at TEXT NOT NULL,
                       updated_at TEXT NOT NULL
                   )"""
            )
            conn.execute(
                """INSERT INTO daily_orchestration_run
                   SELECT * FROM daily_orchestration_run_v1"""
            )
            conn.execute("DROP TABLE daily_orchestration_run_v1")
            conn.execute(
                """CREATE INDEX idx_daily_orchestration_run_day_updated
                   ON daily_orchestration_run(day, updated_at DESC, run_id)"""
            )
            conn.execute(
                """UPDATE daily_orchestration_meta SET schema_version = ?
                   WHERE singleton = 1""",
                (STORE_SCHEMA_VERSION,),
            )
    elif str(row["schema_version"]) != STORE_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported daily-run store schema {row['schema_version']!r}"
        )
    conn.commit()
    return conn


def _record_payload(row: sqlite3.Row) -> dict[str, Any]:
    state = json.loads(str(row["state_json"]))
    return {
        "run_id": str(row["run_id"]),
        "day": str(row["day"]),
        "contract_version": str(row["contract_version"]),
        "config_sha256": str(row["config_sha256"]),
        "config": json.loads(str(row["config_json"])),
        "status": str(row["status"]),
        "stage": str(row["stage"]),
        "stages": state.get("stages") or {},
        "codex_thread_id": row["codex_thread_id"],
        "editorial_run_id": row["editorial_run_id"],
        "error": json.loads(str(row["error_json"])) if row["error_json"] else None,
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def inspect_run(
    *,
    db_path: Path = DEFAULT_DB,
    run_id: str | None = None,
    day: str | None = None,
) -> dict[str, Any]:
    if not db_path.is_file():
        raise FileNotFoundError(db_path)
    conn = connect(db_path)
    try:
        if run_id:
            row = conn.execute(
                "SELECT * FROM daily_orchestration_run WHERE run_id = ?", (run_id,)
            ).fetchone()
        elif day:
            datetime.strptime(day, "%Y-%m-%d")
            row = conn.execute(
                """SELECT * FROM daily_orchestration_run
                   WHERE day = ? ORDER BY updated_at DESC, run_id DESC LIMIT 1""",
                (day,),
            ).fetchone()
        else:
            raise ValueError("inspect requires --run-id or --day")
    finally:
        conn.close()
    if row is None:
        raise ValueError("daily run was not found")
    return _record_payload(row)


def _ensure_run(
    conn: sqlite3.Connection,
    *,
    day: str,
    config: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    config_sha256 = _sha256(config)
    run_id = f"daily-run-{day}-{config_sha256[:12]}"
    row = conn.execute(
        """SELECT * FROM daily_orchestration_run
           WHERE day = ? AND config_sha256 = ?
           ORDER BY updated_at DESC, run_id DESC LIMIT 1""",
        (day, config_sha256),
    ).fetchone()
    if row is not None:
        return _record_payload(row), True
    now = _now()
    state = {"stages": {}}
    conn.execute(
        """INSERT INTO daily_orchestration_run(
               run_id, day, contract_version, config_sha256, config_json,
               status, stage, state_json, created_at, updated_at
           ) VALUES (?, ?, ?, ?, ?, 'planned', 'planned', ?, ?, ?)""",
        (
            run_id,
            day,
            RUN_CONTRACT_VERSION,
            config_sha256,
            _canonical_json(config),
            _canonical_json(state),
            now,
            now,
        ),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM daily_orchestration_run WHERE run_id = ?", (run_id,)
    ).fetchone()
    assert row is not None
    return _record_payload(row), False


def _save_record(
    conn: sqlite3.Connection,
    record: dict[str, Any],
    *,
    status: str,
    stage: str,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = _now()
    conn.execute(
        """UPDATE daily_orchestration_run
           SET status = ?, stage = ?, state_json = ?, codex_thread_id = ?,
               editorial_run_id = ?, error_json = ?, updated_at = ?
           WHERE run_id = ?""",
        (
            status,
            stage,
            _canonical_json({"stages": record.get("stages") or {}}),
            record.get("codex_thread_id"),
            record.get("editorial_run_id"),
            _canonical_json(error) if error else None,
            now,
            record["run_id"],
        ),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM daily_orchestration_run WHERE run_id = ?", (record["run_id"],)
    ).fetchone()
    assert row is not None
    return _record_payload(row)


def _published_feed_start() -> date | None:
    events_path = signal_events.DEFAULT_EVENTS_DB.resolve()
    feed_path = signal_feed.DEFAULT_FEED_DB.resolve()
    if not events_path.is_file() or not feed_path.is_file():
        return None
    event_conn = sqlite3.connect(f"file:{events_path.as_posix()}?mode=ro", uri=True)
    try:
        row = event_conn.execute(
            """SELECT run.feed_run_id
               FROM signal_publication AS publication
               JOIN event_run AS run ON run.run_id = publication.event_run_id
               WHERE publication.singleton = 1"""
        ).fetchone()
    finally:
        event_conn.close()
    if row is None:
        return None
    feed_conn = sqlite3.connect(f"file:{feed_path.as_posix()}?mode=ro", uri=True)
    try:
        feed_row = feed_conn.execute(
            "SELECT date_from FROM feed_run WHERE run_id = ?", (str(row[0]),)
        ).fetchone()
    finally:
        feed_conn.close()
    return date.fromisoformat(str(feed_row[0])) if feed_row else None


def resolve_evidence_days(day: str, requested: int | None) -> int:
    target = date.fromisoformat(day)
    if target >= datetime.now(timezone.utc).date():
        raise ValueError("day must be a complete UTC day before today")
    if requested is not None:
        if requested < 1 or requested > 90:
            raise ValueError("evidence-days must be between 1 and 90")
        return requested
    default_start = target - timedelta(days=DEFAULT_EVIDENCE_WINDOW_DAYS - 1)
    published_start = _published_feed_start()
    start = min(default_start, published_start) if published_start else default_start
    resolved = (target - start).days + 1
    if resolved > 90:
        raise ValueError(
            "preserving the published Feed would exceed 90 days; pass --evidence-days"
        )
    return resolved


def _compact_evidence(value: dict[str, Any]) -> dict[str, Any]:
    collection = value.get("collection") if isinstance(value.get("collection"), dict) else {}
    feed = value.get("feed") if isinstance(value.get("feed"), dict) else {}
    events = value.get("events") if isinstance(value.get("events"), dict) else {}
    publication = (
        value.get("publication") if isinstance(value.get("publication"), dict) else {}
    )
    return {
        "range": value.get("range"),
        "collection_range": value.get("collection_range"),
        "collection": {
            key: collection.get(key)
            for key in (
                "run_id",
                "status",
                "provider_requests",
                "accounts_complete",
                "failures",
                "unfinished_accounts",
            )
            if key in collection
        },
        "collection_coverage": value.get("collection_coverage"),
        "feed": {
            key: feed.get(key)
            for key in (
                "run_id",
                "date_from",
                "date_to",
                "normalized_post_count",
                "relation_count",
                "reused",
            )
            if key in feed
        },
        "events": {
            key: events.get(key)
            for key in (
                "run_id",
                "cluster_count",
                "member_count",
                "link_count",
                "reused",
            )
            if key in events
        },
        "publication": publication,
        "artifact_counts": (
            value.get("artifacts", {}).get("counts")
            if isinstance(value.get("artifacts"), dict)
            else None
        ),
        "view_cache": value.get("view_cache"),
    }


def _compact_routing(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value.get(key)
        for key in (
            "source_event_run_id",
            "source_feed_run_id",
            "through",
            "days",
            "top_ranked",
            "model",
            "reasoning_effort",
            "rank_version",
            "routing_cohort_sha256",
            "source_rank_input_sha256",
            "plan",
            "reuse_policy",
            "resumed_complete_count",
            "reused_exact_count",
            "days_with_exact_reuse",
            "model_requests",
            "incremental_telemetry",
            "counts",
            "runs",
            "will_call_model",
        )
        if key in value
    }


def _routing_checkpoint(value: dict[str, Any], *, day: str) -> dict[str, Any]:
    """Normalize one completed refresh day to its exact immutable lineage."""
    plan_items = [
        item
        for item in value.get("plan") or []
        if isinstance(item, dict) and str(item.get("day") or "") == day
    ]
    if len(plan_items) != 1:
        raise ValueError(f"routing refresh must contain exactly one plan item for {day}")
    plan_item = plan_items[0]
    routing_run_id = str(plan_item.get("run_id") or "").strip()
    if not routing_run_id:
        raise ValueError(f"routing refresh plan has no run ID for {day}")

    run_meta_rows = [
        item["run"]
        for item in value.get("runs") or []
        if isinstance(item, dict)
        and isinstance(item.get("run"), dict)
        and str(item["run"].get("run_id") or "") == routing_run_id
    ]
    if len(run_meta_rows) > 1:
        raise ValueError(f"routing refresh has duplicate run metadata for {day}")
    run_meta = run_meta_rows[0] if run_meta_rows else {}

    def exact_value(name: str, *candidates: Any) -> str:
        values = {
            str(candidate).strip()
            for candidate in candidates
            if candidate is not None and str(candidate).strip()
        }
        if len(values) > 1:
            raise ValueError(f"routing refresh has inconsistent {name} for {day}")
        return next(iter(values), "")

    source_rank_input_sha256 = exact_value(
        "source rank-input SHA",
        value.get("source_rank_input_sha256"),
        plan_item.get("source_rank_input_sha256"),
        run_meta.get("source_rank_input_sha256"),
    )
    routing_cohort_sha256 = exact_value(
        "routing cohort SHA",
        value.get("routing_cohort_sha256"),
        run_meta.get("cohort_sha256"),
    )
    source_event_run_id = exact_value(
        "source Event run ID",
        value.get("source_event_run_id"),
        run_meta.get("source_event_run_id"),
    )
    source_feed_run_id = exact_value(
        "source Feed run ID",
        value.get("source_feed_run_id"),
        run_meta.get("source_feed_run_id"),
    )
    missing = [
        name
        for name, candidate in (
            ("source_rank_input_sha256", source_rank_input_sha256),
            ("routing_cohort_sha256", routing_cohort_sha256),
            ("source_event_run_id", source_event_run_id),
            ("source_feed_run_id", source_feed_run_id),
        )
        if not candidate
    ]
    if missing:
        raise ValueError(
            "routing refresh is missing required lineage: " + ", ".join(missing)
        )
    return _compact_routing(
        {
            **value,
            "source_event_run_id": source_event_run_id,
            "source_feed_run_id": source_feed_run_id,
            "routing_cohort_sha256": routing_cohort_sha256,
            "source_rank_input_sha256": source_rank_input_sha256,
        }
    )


def _event_run_id(evidence: dict[str, Any]) -> str:
    publication = evidence.get("publication") or {}
    events = evidence.get("events") or {}
    value = publication.get("event_run_id") or publication.get("run_id") or events.get("run_id")
    return str(value or "")


def _feed_run_id(evidence: dict[str, Any]) -> str:
    return str((evidence.get("feed") or {}).get("run_id") or "")


def _expected_routing_run_id(routing: dict[str, Any], day: str) -> str:
    plan = routing.get("plan") or []
    return next(
        (
            str(item.get("run_id"))
            for item in plan
            if isinstance(item, dict) and str(item.get("day")) == day
        ),
        "",
    )


def _normalize_source_lineage(
    source_lineage: dict[str, Any] | None,
) -> dict[str, str] | None:
    if source_lineage is None:
        return None
    if not isinstance(source_lineage, dict):
        raise ValueError("source_lineage must be an object")
    unexpected = sorted(set(source_lineage) - set(SOURCE_LINEAGE_KEYS))
    if unexpected:
        raise ValueError(
            "source_lineage has unsupported fields: " + ", ".join(unexpected)
        )
    normalized = {
        key: str(source_lineage.get(key) or "").strip()
        for key in SOURCE_LINEAGE_KEYS
    }
    missing = [key for key, value in normalized.items() if not value]
    if missing:
        raise ValueError(
            "source_lineage is missing required fields: " + ", ".join(missing)
        )
    return normalized


def _checkpoint_source_lineage(
    *,
    day: str,
    evidence: dict[str, Any],
    routing: dict[str, Any],
) -> dict[str, str]:
    return {
        "event_run_id": _event_run_id(evidence),
        "feed_run_id": _feed_run_id(evidence),
        "routing_run_id": _expected_routing_run_id(routing, day),
        "routing_cohort_sha256": str(
            routing.get("routing_cohort_sha256") or ""
        ),
        "source_rank_input_sha256": str(
            routing.get("source_rank_input_sha256") or ""
        ),
    }


def _require_checkpoint_source_lineage(
    *,
    day: str,
    evidence: dict[str, Any],
    routing: dict[str, Any],
) -> dict[str, str]:
    lineage = _checkpoint_source_lineage(
        day=day,
        evidence=evidence,
        routing=routing,
    )
    missing = [key for key, value in lineage.items() if not value]
    if missing:
        _raise_source_lineage_mismatch(missing)
    return lineage


def _raise_source_lineage_mismatch(mismatches: list[str]) -> None:
    raise DailyRunError(
        code="E_SOURCE_LINEAGE_MISMATCH",
        message=(
            "The frozen Evidence/routing checkpoint does not match this daily "
            "run's source lineage: "
            + ", ".join(mismatches)
        ),
        hint=(
            "Inspect the frozen batch inputs and start or resume the run with "
            "their exact source lineage."
        ),
        retryable=False,
        exit_code=4,
    )


def _validate_evidence_source_lineage(
    *,
    expected: dict[str, str],
    evidence: dict[str, Any],
) -> None:
    actual = {
        "event_run_id": _event_run_id(evidence),
        "feed_run_id": _feed_run_id(evidence),
    }
    mismatches = [
        key for key, value in actual.items() if value != expected[key]
    ]
    if mismatches:
        _raise_source_lineage_mismatch(mismatches)


def _validate_source_lineage(
    *,
    day: str,
    expected: dict[str, str],
    evidence: dict[str, Any],
    routing: dict[str, Any],
) -> None:
    actual = _checkpoint_source_lineage(
        day=day,
        evidence=evidence,
        routing=routing,
    )
    mismatches = [
        key for key, value in actual.items() if value != expected[key]
    ]
    if mismatches:
        _raise_source_lineage_mismatch(mismatches)


def _validate_prepared_workspace(
    *,
    checkpoint: dict[str, Any],
    day: str,
    evidence: dict[str, Any],
    routing: dict[str, Any],
    workspace_loader: Callable[[Path], dict[str, Any]],
    template_loader: Callable[[Path], dict[str, Any]],
) -> None:
    """Verify that a resumed prepare checkpoint is still the supported packet."""
    raw_workspace = str(checkpoint.get("workspace") or "").strip()
    if not raw_workspace:
        raise ValueError("prepare checkpoint has no workspace path")
    raw_path = Path(raw_workspace)
    workspace_path = raw_path if raw_path.is_absolute() else REPO_ROOT / raw_path
    manifest = workspace_loader(workspace_path)
    expected = {
        "schema_version": editorial_runs.WORKSPACE_SCHEMA_VERSION,
        "day": day,
        "run_id": str(checkpoint.get("run_id") or ""),
        "manifest_sha256": str(checkpoint.get("manifest_sha256") or ""),
        "routing_run_id": _expected_routing_run_id(routing, day),
        "event_run_id": _event_run_id(evidence),
        "feed_run_id": _feed_run_id(evidence),
    }
    actual_source = manifest.get("source") or {}
    actual = {
        "schema_version": str(manifest.get("schema_version") or ""),
        "day": str(manifest.get("day") or ""),
        "run_id": str(manifest.get("run_id") or ""),
        "manifest_sha256": str(manifest.get("manifest_sha256") or ""),
        "routing_run_id": str(actual_source.get("routing_run_id") or ""),
        "event_run_id": str(actual_source.get("event_run_id") or ""),
        "feed_run_id": str(actual_source.get("feed_run_id") or ""),
    }
    mismatches = [key for key, value in expected.items() if value != actual[key]]
    if mismatches:
        raise ValueError(
            "prepare checkpoint no longer matches its frozen manifest: "
            + ", ".join(mismatches)
        )
    expected_template_path = workspace_path / "draft.template.json"
    raw_template_path = str(checkpoint.get("draft_template") or "").strip()
    if raw_template_path:
        template_path = Path(raw_template_path)
        if not template_path.is_absolute():
            template_path = REPO_ROOT / template_path
        if template_path.resolve() != expected_template_path.resolve():
            raise ValueError("prepare checkpoint points to a different draft template")
    template = template_loader(expected_template_path)
    if template != editorial.draft_template(manifest):
        raise ValueError("draft template does not match the frozen manifest")


def _load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _latest_editorial_run(
    *, workspace_run_id: str, db_path: Path = editorial_runs.DEFAULT_DB
) -> str | None:
    if not db_path.is_file():
        return None
    conn = sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        if conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'editorial_run'"
        ).fetchone() is None:
            return None
        row = conn.execute(
            """SELECT run_id FROM editorial_run
               WHERE workspace_run_id = ? AND status = 'complete'
               ORDER BY created_at DESC, run_id DESC LIMIT 1""",
            (workspace_run_id,),
        ).fetchone()
    finally:
        conn.close()
    return str(row[0]) if row else None


def _complete_from_editorial_run(
    conn: sqlite3.Connection,
    record: dict[str, Any],
    *,
    editorial_run_id: str,
) -> dict[str, Any]:
    stages = record["stages"]
    existing_codex = stages.get("codex") or {}
    completed_codex = {
        "status": "complete",
        "completion_source": "editorial_run",
    }
    for key in (
        "thread_id",
        "thread_name",
        "requested_settings",
        "settings",
        "feedback",
    ):
        if existing_codex.get(key):
            completed_codex[key] = existing_codex[key]
    stages["codex"] = completed_codex
    record["editorial_run_id"] = editorial_run_id
    return _save_record(conn, record, status="complete", stage="codex", error=None)


EvidenceRunner = Callable[..., dict[str, Any]]
RoutingRunner = Callable[..., dict[str, Any]]
WorkspacePreparer = Callable[..., dict[str, Any]]
WorkspaceLoader = Callable[[Path], dict[str, Any]]
WorkspaceTemplateLoader = Callable[[Path], dict[str, Any]]
CodexRunner = Callable[..., dict[str, Any]]
ProgressCallback = Callable[[str, str], None]


def run_day(
    *,
    day: str,
    db_path: Path = DEFAULT_DB,
    evidence_days: int | None = None,
    collection_days: int = 1,
    workers: int = 32,
    top_ranked: int = routing_runs.DEFAULT_REFRESH_TOP_RANKED,
    routing_workers: int = routing_runs.DEFAULT_REFRESH_WORKERS,
    routing_day_workers: int = 1,
    stop_after: str = "prepare",
    launch_codex: bool = False,
    codex_timeout_seconds: float = DEFAULT_CODEX_TIMEOUT_SECONDS,
    codex_binary: str = "codex",
    codex_model: str | None = None,
    codex_reasoning_effort: str | None = None,
    codex_service_tier: str | None = DEFAULT_CODEX_SERVICE_TIER,
    skill_path: Path = DEFAULT_SKILL_PATH,
    dry_run: bool = False,
    progress: ProgressCallback | None = None,
    evidence_runner: EvidenceRunner = evidence_refresh.refresh_evidence,
    routing_runner: RoutingRunner = routing_runs.refresh_all_days,
    workspace_preparer: WorkspacePreparer = editorial_runs.prepare_workspace,
    workspace_loader: WorkspaceLoader = editorial_runs.load_manifest,
    workspace_template_loader: WorkspaceTemplateLoader = _load_json_object,
    codex_runner: CodexRunner | None = None,
    source_lineage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    datetime.strptime(day, "%Y-%m-%d")
    if stop_after not in PREPARATION_STAGES:
        raise ValueError(
            f"stop-after must be one of {', '.join(PREPARATION_STAGES)}"
        )
    if launch_codex and stop_after != "prepare":
        raise ValueError("--launch-codex cannot be combined with an earlier stop-after")
    if collection_days < 1:
        raise ValueError("collection-days must be positive")
    resolved_evidence_days = resolve_evidence_days(day, evidence_days)
    if collection_days > resolved_evidence_days:
        raise ValueError("collection-days cannot exceed evidence-days")
    requested_codex_settings = _codex_settings(
        model=codex_model,
        reasoning_effort=codex_reasoning_effort,
        service_tier=codex_service_tier,
    )
    normalized_source_lineage = _normalize_source_lineage(source_lineage)
    config = {
        "contract_version": RUN_CONTRACT_VERSION,
        "day": day,
        "evidence_days": resolved_evidence_days,
        "collection_days": collection_days,
        "workers": workers,
        "routing_days": 1,
        "top_ranked": top_ranked,
        "routing_model": routing_model.DEFAULT_MODEL,
        "routing_reasoning_effort": routing_model.DEFAULT_REASONING_EFFORT,
        "rank_version": development_attention.DAILY_RANK_VERSION,
        "routing_workers": routing_workers,
        "routing_day_workers": routing_day_workers,
        "repo_root": str(REPO_ROOT),
        "skill_path": str(skill_path.resolve()),
    }
    if normalized_source_lineage is not None:
        config["source_lineage"] = normalized_source_lineage
    plan = {
        "day": day,
        "stop_after": "codex" if launch_codex else stop_after,
        "will_collect_external_evidence": True,
        "will_call_routing_model": True,
        "will_launch_codex": launch_codex,
        "codex_settings": requested_codex_settings,
        "config": config,
    }
    if dry_run:
        return {"dry_run": True, "plan": plan}

    run_lock = _acquire_day_lock(db_path, day)
    try:
        conn = connect(db_path)
    except Exception:
        _release_day_lock(run_lock)
        raise
    current_stage = "planned"
    try:
        record, reused = _ensure_run(conn, day=day, config=config)
        stages = record["stages"]
        if normalized_source_lineage is not None and "evidence" in stages:
            _validate_evidence_source_lineage(
                expected=normalized_source_lineage,
                evidence=stages["evidence"],
            )
        if "routing" in stages:
            if "evidence" not in stages:
                _raise_source_lineage_mismatch(["evidence"])
            try:
                routing_checkpoint = _routing_checkpoint(
                    stages["routing"],
                    day=day,
                )
            except ValueError as error:
                _raise_source_lineage_mismatch([str(error)])
            checkpoint_lineage = _require_checkpoint_source_lineage(
                day=day,
                evidence=stages["evidence"],
                routing=routing_checkpoint,
            )
            if (
                normalized_source_lineage is not None
                and checkpoint_lineage != normalized_source_lineage
            ):
                _raise_source_lineage_mismatch(
                    [
                        key
                        for key, value in checkpoint_lineage.items()
                        if value != normalized_source_lineage[key]
                    ]
                )
        if record["status"] == "complete":
            if "evidence" not in stages or "routing" not in stages:
                _raise_source_lineage_mismatch(["evidence/routing checkpoint"])
            return {**record, "reused": reused}

        if "evidence" not in stages:
            current_stage = "evidence"
            if progress:
                progress("evidence", "running")
            raw_evidence = evidence_runner(
                through=day,
                days=resolved_evidence_days,
                collection_days=collection_days,
                workers=workers,
                progress=(
                    (lambda stage, status: progress(f"evidence.{stage}", status))
                    if progress
                    else None
                ),
            )
            if normalized_source_lineage is not None:
                _validate_evidence_source_lineage(
                    expected=normalized_source_lineage,
                    evidence=raw_evidence,
                )
            stages["evidence"] = _compact_evidence(raw_evidence)
            record = _save_record(
                conn, record, status="running", stage="evidence", error=None
            )
            stages = record["stages"]
            if progress:
                progress("evidence", "complete")
        if stop_after == "evidence":
            return {
                **_save_record(
                    conn, record, status="prepared", stage="evidence", error=None
                ),
                "reused": reused,
            }

        if "routing" not in stages:
            current_stage = "routing"
            if progress:
                progress("routing", "running")
            routing_output = sys.stderr if progress else io.StringIO()
            with redirect_stdout(routing_output):
                raw_routing = routing_runner(
                    through=day,
                    days=1,
                    top_ranked=top_ranked,
                    model=routing_model.DEFAULT_MODEL,
                    effort=routing_model.DEFAULT_REASONING_EFFORT,
                    workers=routing_workers,
                    day_workers=routing_day_workers,
                    replace=False,
                    dry_run=False,
                )
            routing_checkpoint = _routing_checkpoint(raw_routing, day=day)
            evidence = stages["evidence"]
            if str(routing_checkpoint["source_event_run_id"]) != _event_run_id(
                evidence
            ):
                raise DailyRunError(
                    code="E_SOURCE_CHANGED",
                    message="Audience routing used a different Event publication.",
                    hint="Resume the same command so evidence and routing can be frozen again.",
                    retryable=True,
                    exit_code=4,
                )
            if str(routing_checkpoint["source_feed_run_id"]) != _feed_run_id(
                evidence
            ):
                raise DailyRunError(
                    code="E_SOURCE_CHANGED",
                    message="Audience routing used a different Feed publication.",
                    hint="Resume the same command so evidence and routing can be frozen again.",
                    retryable=True,
                    exit_code=4,
                )
            if normalized_source_lineage is not None:
                _validate_source_lineage(
                    day=day,
                    expected=normalized_source_lineage,
                    evidence=evidence,
                    routing=routing_checkpoint,
                )
            stages["routing"] = routing_checkpoint
            record = _save_record(
                conn, record, status="running", stage="routing", error=None
            )
            stages = record["stages"]
            if progress:
                progress("routing", "complete")
        if stop_after == "routing":
            return {
                **_save_record(
                    conn, record, status="prepared", stage="routing", error=None
                ),
                "reused": reused,
            }

        if "prepare" in stages:
            try:
                _validate_prepared_workspace(
                    checkpoint=stages["prepare"],
                    day=day,
                    evidence=stages["evidence"],
                    routing=stages["routing"],
                    workspace_loader=workspace_loader,
                    template_loader=workspace_template_loader,
                )
            except (FileNotFoundError, OSError, ValueError) as error:
                started_codex = bool(
                    record.get("codex_thread_id")
                    or record.get("editorial_run_id")
                    or stages.get("codex")
                )
                if started_codex:
                    raise DailyRunError(
                        code="E_WORKSPACE_OBSOLETE_TASK",
                        message=(
                            "The persisted Codex task is bound to an obsolete or "
                            "invalid workspace."
                        ),
                        hint=(
                            "Stop and archive that task, remove its unimported "
                            "orchestration checkpoint, then start one clean run."
                        ),
                        retryable=False,
                        exit_code=4,
                    ) from error
                stages.pop("prepare", None)
                stages.pop("codex", None)
                record["codex_thread_id"] = None
                record["editorial_run_id"] = None
                record = _save_record(
                    conn,
                    record,
                    status="running",
                    stage="routing",
                    error=None,
                )
                stages = record["stages"]

        if "prepare" not in stages:
            current_stage = "prepare"
            if progress:
                progress("prepare", "running")
            workspace = workspace_preparer(day=day)
            workspace = {
                **workspace,
                "workspace_schema_version": editorial_runs.WORKSPACE_SCHEMA_VERSION,
                "draft_schema_version": editorial.DRAFT_SCHEMA_VERSION,
            }
            expected_routing_id = _expected_routing_run_id(stages["routing"], day)
            actual_routing_id = str((workspace.get("source") or {}).get("routing_run_id") or "")
            if expected_routing_id and actual_routing_id != expected_routing_id:
                raise DailyRunError(
                    code="E_ROUTING_CHANGED",
                    message="Workspace preparation selected a different routing run.",
                    hint="Inspect the routing store and resume the same command.",
                    retryable=True,
                    exit_code=4,
                )
            workspace_source = workspace.get("source") or {}
            if str(workspace_source.get("event_run_id") or "") != _event_run_id(
                stages["evidence"]
            ):
                raise DailyRunError(
                    code="E_EVENT_CHANGED",
                    message="Workspace preparation selected a different Event publication.",
                    hint="Inspect the published Event pointer and resume the same command.",
                    retryable=True,
                    exit_code=4,
                )
            if str(workspace_source.get("feed_run_id") or "") != _feed_run_id(
                stages["evidence"]
            ):
                raise DailyRunError(
                    code="E_FEED_CHANGED",
                    message="Workspace preparation selected a different Feed publication.",
                    hint="Inspect the published Feed pointer and resume the same command.",
                    retryable=True,
                    exit_code=4,
                )
            stages["prepare"] = workspace
            record = _save_record(
                conn, record, status="prepared", stage="prepare", error=None
            )
            stages = record["stages"]
            if progress:
                progress("prepare", "complete")
        if stop_after == "prepare":
            if not launch_codex:
                return {**record, "reused": reused}

        current_stage = "codex"
        workspace = stages["prepare"]
        workspace_path = REPO_ROOT / str(workspace["workspace"])
        editorial_run_id = _latest_editorial_run(
            workspace_run_id=str(workspace["run_id"]), db_path=db_path
        )
        if editorial_run_id:
            record = _complete_from_editorial_run(
                conn, record, editorial_run_id=editorial_run_id
            )
            if progress:
                progress("codex", "complete")
            return {**record, "reused": reused}
        existing_codex = stages.get("codex") or {}
        existing_thread_id = str(
            record.get("codex_thread_id") or existing_codex.get("thread_id") or ""
        ) or None
        codex_settings, bound_requested_settings = _bound_codex_settings(
            existing_codex,
            requested_codex_settings,
            thread_id=existing_thread_id,
        )
        if existing_codex.get("requested_settings") != bound_requested_settings:
            stages["codex"] = {
                **existing_codex,
                "requested_settings": bound_requested_settings,
                "status": existing_codex.get("status") or "configured",
            }
            record = _save_record(
                conn,
                record,
                status="codex_running",
                stage="codex",
                error=None,
            )
            stages = record["stages"]
            existing_codex = stages["codex"]
        name = f"FLI Daily Brief — {day}"
        objective = (
            f"Produce, validate, import, and inspect the complete Frontier Lab "
            f"Intelligence daily brief for {day} from frozen workspace "
            f"{workspace['workspace']}. Before acting, read and follow "
            ".agents/skills/fli-daily-intelligence/SKILL.md. Use "
            f"{_display_path(db_path)} as the exact editorial database for indexing, "
            "import, and inspection. Review every candidate for both audiences, "
            "use web research when it "
            "materially resolves an unknown, and continue until the exact imported "
            "run is inspected. Do not modify product code or rerun Evidence/routing. "
            "Mark the goal blocked only after exhausting safe in-scope recovery."
        )
        prompt = (
            f"Pursue the active goal for {day}. The deterministic handoff is already "
            f"prepared at {workspace['workspace']}. Read both audience contexts and "
            "the frozen manifest, follow the attached skill exactly, validate the full "
            "cohort, import it through the client, inspect the durable run, and then "
            f"mark the goal complete. Use {_display_path(db_path)} as the exact "
            "editorial database for index, import, and inspection commands."
        )
        feedback_path = _agent_feedback_path(day)
        feedback_prompt = _agent_feedback_prompt(day, feedback_path)

        def checkpoint(codex: dict[str, Any]) -> None:
            nonlocal record, stages, codex_settings
            reported_settings = codex.get("settings")
            if reported_settings is not None:
                codex_settings = _checkpoint_codex_settings(
                    reported_settings, require_resolved=True
                )
            elif codex.get("thread_id") and existing_codex.get("settings") is None:
                raise DailyRunError(
                    code="E_CODEX_SETTINGS_INVALID",
                    message="Codex created a task without effective model settings.",
                    hint="Inspect the App Server response before resuming this task.",
                    retryable=False,
                    exit_code=4,
                )
            stage = {
                **codex,
                "requested_settings": bound_requested_settings,
            }
            if reported_settings is not None or existing_codex.get("settings") is not None:
                stage["settings"] = codex_settings
            stages["codex"] = stage
            record["codex_thread_id"] = codex.get("thread_id")
            record = _save_record(
                conn,
                record,
                status="codex_running",
                stage="codex",
                error=None,
            )
            stages = record["stages"]

        existing_codex = stages.get("codex") or {}
        if (
            existing_codex.get("status") == "thread_starting"
            and existing_thread_id is None
        ):
            raise DailyRunError(
                code="E_CODEX_THREAD_UNKNOWN",
                message=(
                    "A prior launch stopped while the Codex task identity was unknown."
                ),
                hint=(
                    "Inspect Codex Desktop and the App Server task store; do not create "
                    "a replacement task automatically."
                ),
                retryable=False,
                exit_code=4,
            )
        if progress:
            progress("codex", "resuming" if existing_thread_id else "launching")
        try:
            if codex_runner is None:
                client = CodexAppServerClient(
                    repo_root=REPO_ROOT,
                    codex_binary=codex_binary,
                )
                import asyncio

                codex = asyncio.run(
                    client.run_task(
                        name=name,
                        objective=objective,
                        prompt=prompt,
                        skill_path=skill_path,
                        timeout_seconds=codex_timeout_seconds,
                        model=codex_settings["model"],
                        reasoning_effort=codex_settings["reasoning_effort"],
                        service_tier=codex_settings["service_tier"],
                        thread_id=existing_thread_id,
                        post_completion_prompt=feedback_prompt,
                        post_completion_output_path=feedback_path,
                        progress=progress,
                        checkpoint=checkpoint,
                    )
                )
            else:
                codex = codex_runner(
                    name=name,
                    objective=objective,
                    prompt=prompt,
                    skill_path=skill_path,
                    timeout_seconds=codex_timeout_seconds,
                    model=codex_settings["model"],
                    reasoning_effort=codex_settings["reasoning_effort"],
                    service_tier=codex_settings["service_tier"],
                    thread_id=existing_thread_id,
                    post_completion_prompt=feedback_prompt,
                    post_completion_output_path=feedback_path,
                    progress=progress,
                    checkpoint=checkpoint,
                )
        except CodexTaskError:
            editorial_run_id = _latest_editorial_run(
                workspace_run_id=str(workspace["run_id"]), db_path=db_path
            )
            if not editorial_run_id:
                raise
            record = _complete_from_editorial_run(
                conn, record, editorial_run_id=editorial_run_id
            )
            if progress:
                progress("codex", "complete")
            return {**record, "reused": reused}
        reported_settings = codex.get("settings")
        if reported_settings is not None:
            codex_settings = _checkpoint_codex_settings(
                reported_settings, require_resolved=True
            )
        elif existing_thread_id or codex.get("thread_id"):
            if existing_codex.get("settings") is None:
                raise DailyRunError(
                    code="E_CODEX_SETTINGS_INVALID",
                    message="Codex finished without effective model settings.",
                    hint="Inspect the App Server response before resuming this task.",
                    retryable=False,
                    exit_code=4,
                )
        stages["codex"] = {
            **codex,
            "requested_settings": bound_requested_settings,
            "settings": codex_settings,
        }
        record["codex_thread_id"] = codex.get("thread_id")
        if codex.get("goal_status") != "complete":
            retryable = codex.get("goal_status") not in {
                "budgetLimited",
                "usageLimited",
            }
            record = _save_record(
                conn,
                record,
                status="blocked",
                stage="codex",
                error={
                    "code": "E_CODEX_GOAL_INCOMPLETE",
                    "message": f"Codex goal ended as {codex.get('goal_status')!r}.",
                    "retryable": retryable,
                    "hint": "Open the persisted Codex task or resume the same daily run.",
                },
            )
            raise DailyRunError(
                code="E_CODEX_GOAL_INCOMPLETE",
                message=f"Codex goal ended as {codex.get('goal_status')!r}.",
                hint="Open the persisted Codex task or resume the same daily run.",
                retryable=retryable,
                exit_code=4,
            )
        editorial_run_id = _latest_editorial_run(
            workspace_run_id=str(workspace["run_id"]), db_path=db_path
        )
        if not editorial_run_id:
            raise DailyRunError(
                code="E_EDITORIAL_RUN_MISSING",
                message="Codex completed without importing this workspace.",
                hint="Resume the persisted task and complete validation, import, and inspection.",
                retryable=True,
                exit_code=4,
            )
        record = _complete_from_editorial_run(
            conn, record, editorial_run_id=editorial_run_id
        )
        if progress:
            progress("codex", "complete")
        return {**record, "reused": reused}
    except (CodexTaskError, DailyRunError) as error:
        if "record" in locals():
            _save_record(
                conn,
                record,
                status="failed",
                stage=current_stage,
                error={
                    "code": error.code,
                    "message": error.message,
                    "retryable": error.retryable,
                    "hint": error.hint,
                },
            )
        raise
    except Exception as error:
        if "record" in locals():
            _save_record(
                conn,
                record,
                status="failed",
                stage=current_stage,
                error={
                    "code": "E_INTERNAL",
                    "message": f"{type(error).__name__}: {error}",
                    "retryable": True,
                    "hint": "Inspect the recorded stage and resume the same command.",
                },
            )
        raise
    finally:
        conn.close()
        _release_day_lock(run_lock)


def _current_inputs(day: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Describe the already-published Evidence and current ranked routing."""
    from fli.web import developments as development_store

    rank_identity = development_store.current_rank_identity(day=day)
    routing_path = routing_view.latest_complete_run(
        day,
        expected_rank_input_sha256=rank_identity["rank_input_sha256"],
        expected_event_run_id=rank_identity["event_run_id"],
        expected_feed_run_id=rank_identity["feed_run_id"],
    )
    if routing_path is None:
        raise ValueError(
            f"no complete {development_attention.DAILY_RANK_VERSION} routing for {day}"
        )
    conn = sqlite3.connect(
        f"file:{routing_path.resolve().as_posix()}?mode=ro",
        uri=True,
    )
    conn.row_factory = sqlite3.Row
    try:
        meta = conn.execute(
            "SELECT * FROM run_meta WHERE singleton = 1"
        ).fetchone()
    finally:
        conn.close()
    if meta is None:
        raise ValueError(f"routing metadata is missing for {day}")
    source = {
        "event_run_id": str(meta["source_event_run_id"]),
        "feed_run_id": str(meta["source_feed_run_id"]),
    }
    evidence = {
        "range": {"from": day, "through": day, "days": 1},
        "collection_range": None,
        "feed": {"run_id": source["feed_run_id"], "reused": True},
        "events": {"run_id": source["event_run_id"], "reused": True},
        "publication": {
            "event_run_id": source["event_run_id"],
            "feed_run_id": source["feed_run_id"],
        },
    }
    routing = {
        "source_event_run_id": source["event_run_id"],
        "source_feed_run_id": source["feed_run_id"],
        "through": day,
        "days": 1,
        "top_ranked": int(meta["selection_limit"] or 0),
        "model": str(meta["model"]),
        "reasoning_effort": str(meta["reasoning_effort"]),
        "rank_version": str(meta["rank_version"]),
        "routing_cohort_sha256": str(meta["cohort_sha256"]),
        "source_rank_input_sha256": str(meta["source_rank_input_sha256"]),
        "plan": [{"day": day, "run_id": str(meta["run_id"])}],
        "reuse_policy": "already-complete-current-routing",
        "resumed_complete_count": int(meta["expected_count"]),
        "reused_exact_count": 0,
        "model_requests": 0,
        "will_call_model": False,
    }
    return evidence, routing


def run_batch(
    *,
    through: str,
    days: int,
    db_path: Path = DEFAULT_DB,
    day_workers: int = 3,
    codex_timeout_seconds: float = DEFAULT_CODEX_TIMEOUT_SECONDS,
    codex_binary: str = "codex",
    codex_model: str | None = None,
    codex_reasoning_effort: str | None = None,
    codex_service_tier: str | None = DEFAULT_CODEX_SERVICE_TIER,
    skill_path: Path = DEFAULT_SKILL_PATH,
    dry_run: bool = False,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Launch revised historical briefs from one frozen routing lineage."""
    if days < 1 or days > 90:
        raise ValueError("days must be between 1 and 90")
    if day_workers < 1 or day_workers > 4:
        raise ValueError("day-workers must be between 1 and 4")
    end = date.fromisoformat(through)
    selected_days = [
        (end - timedelta(days=offset)).isoformat()
        for offset in range(days - 1, -1, -1)
    ]
    frozen = {day: _current_inputs(day) for day in selected_days}
    plan = {
        "through": through,
        "days": days,
        "selected_days": selected_days,
        "day_workers": min(day_workers, days),
        "rank_version": development_attention.DAILY_RANK_VERSION,
        "will_collect_external_evidence": False,
        "will_call_routing_model": False,
        "will_launch_codex": not dry_run,
        "codex_settings": _codex_settings(
            model=codex_model,
            reasoning_effort=codex_reasoning_effort,
            service_tier=codex_service_tier,
        ),
    }
    if dry_run:
        return {"dry_run": True, "plan": plan}

    # Perform the one-time orchestration-store migration before workers open it.
    migration_conn = connect(db_path)
    migration_conn.close()

    def execute(day: str) -> dict[str, Any]:
        evidence, routing = frozen[day]
        source_lineage = _normalize_source_lineage(
            {
                "event_run_id": _event_run_id(evidence),
                "feed_run_id": _feed_run_id(evidence),
                "routing_run_id": _expected_routing_run_id(routing, day),
                "routing_cohort_sha256": routing.get(
                    "routing_cohort_sha256"
                ),
                "source_rank_input_sha256": routing.get(
                    "source_rank_input_sha256"
                ),
            }
        )
        return run_day(
            day=day,
            db_path=db_path,
            evidence_days=1,
            collection_days=1,
            top_ranked=int(routing["top_ranked"]),
            launch_codex=True,
            codex_timeout_seconds=codex_timeout_seconds,
            codex_binary=codex_binary,
            codex_model=codex_model,
            codex_reasoning_effort=codex_reasoning_effort,
            codex_service_tier=codex_service_tier,
            skill_path=skill_path,
            progress=(
                (lambda stage, status: progress(f"{day}.{stage}", status))
                if progress
                else None
            ),
            source_lineage=source_lineage,
            evidence_runner=lambda **_: evidence,
            routing_runner=lambda **_: routing,
        )

    results: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=min(day_workers, days)) as executor:
        futures = {executor.submit(execute, day): day for day in selected_days}
        for future in as_completed(futures):
            day = futures[future]
            try:
                results[day] = future.result()
            except Exception as error:
                errors[day] = f"{type(error).__name__}: {error}"
    result = {
        "dry_run": False,
        "plan": plan,
        "complete": len(results),
        "failed": len(errors),
        "runs": [results[day] for day in sorted(results)],
        "errors": errors,
    }
    if errors:
        raise DailyRunError(
            code="E_BATCH_INCOMPLETE",
            message=_canonical_json(result),
            hint="Rerun the same batch; completed days resume and only failed days continue.",
            retryable=True,
            exit_code=4,
        )
    return result


def add_cli_parsers(sub: Any) -> None:
    """Register orchestration actions on the daily-intelligence client."""

    run = sub.add_parser("run-day", help="Prepare or resume one complete daily workflow.")
    run.add_argument("--day", required=True)
    run.add_argument("--db", type=Path, default=DEFAULT_DB)
    run.add_argument("--evidence-days", type=int)
    run.add_argument("--collection-days", type=int, default=1)
    run.add_argument("--workers", type=int, default=32)
    run.add_argument(
        "--top-ranked", type=int, default=routing_runs.DEFAULT_REFRESH_TOP_RANKED
    )
    run.add_argument(
        "--routing-workers", type=int, default=routing_runs.DEFAULT_REFRESH_WORKERS
    )
    run.add_argument("--routing-day-workers", type=int, default=1)
    run.add_argument(
        "--stop-after",
        choices=PREPARATION_STAGES,
        default="prepare",
        help="Stop at this preparation boundary (default: prepare).",
    )
    run.add_argument(
        "--launch-codex",
        action="store_true",
        help="After preparation, create or resume the one persisted Codex task.",
    )
    run.add_argument(
        "--codex-timeout-seconds",
        type=float,
        default=DEFAULT_CODEX_TIMEOUT_SECONDS,
    )
    run.add_argument("--codex-binary", default="codex")
    run.add_argument(
        "--codex-model",
        help="Override the Codex model; omit to inherit the normal Codex default.",
    )
    run.add_argument(
        "--codex-reasoning-effort",
        help=(
            "Override model reasoning effort (for example high, xhigh, max, or "
            "ultra); omit to inherit."
        ),
    )
    run.add_argument(
        "--codex-service-tier",
        default=DEFAULT_CODEX_SERVICE_TIER,
        help=(
            "Set the App Server service tier (default: standard). 'normal' and "
            "'default' alias standard; 'fast' aliases the canonical priority tier."
        ),
    )
    run.add_argument("--skill-path", type=Path, default=DEFAULT_SKILL_PATH)
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--progress", choices=("off", "plain"), default="plain")
    run.add_argument("--no-input", action="store_true")
    mode = run.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true")
    mode.add_argument("--plain", action="store_true")

    batch = sub.add_parser(
        "run-batch",
        help="Launch revised briefs from already-complete current routing.",
    )
    batch.add_argument("--through", required=True)
    batch.add_argument("--days", type=int, required=True)
    batch.add_argument("--db", type=Path, default=DEFAULT_DB)
    batch.add_argument("--day-workers", type=int, default=3)
    batch.add_argument(
        "--codex-timeout-seconds",
        type=float,
        default=DEFAULT_CODEX_TIMEOUT_SECONDS,
    )
    batch.add_argument("--codex-binary", default="codex")
    batch.add_argument("--codex-model")
    batch.add_argument("--codex-reasoning-effort")
    batch.add_argument(
        "--codex-service-tier",
        default=DEFAULT_CODEX_SERVICE_TIER,
    )
    batch.add_argument("--skill-path", type=Path, default=DEFAULT_SKILL_PATH)
    batch.add_argument("--dry-run", action="store_true")
    batch.add_argument("--progress", choices=("off", "plain"), default="plain")
    batch.add_argument("--no-input", action="store_true")
    batch_mode = batch.add_mutually_exclusive_group()
    batch_mode.add_argument("--json", action="store_true")
    batch_mode.add_argument("--plain", action="store_true")

    inspect = sub.add_parser(
        "inspect-day-run", help="Inspect one durable daily orchestration run."
    )
    selector = inspect.add_mutually_exclusive_group(required=True)
    selector.add_argument("--day")
    selector.add_argument("--run-id")
    inspect.add_argument("--db", type=Path, default=DEFAULT_DB)
    inspect.add_argument("--no-input", action="store_true")
    inspect_mode = inspect.add_mutually_exclusive_group()
    inspect_mode.add_argument("--json", action="store_true")
    inspect_mode.add_argument("--plain", action="store_true")


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="fli daily-intelligence",
        description=(
            "Prepare one complete FLI date and optionally launch its persisted "
            "Codex daily-intelligence task."
        ),
    )
    sub = parser.add_subparsers(dest="action", required=True)
    add_cli_parsers(sub)
    return parser


def _success(command: str, data: Any, *, request_id: str, started: float) -> dict[str, Any]:
    return {
        "schema_version": CLI_SCHEMA_VERSION,
        "command": command,
        "status": "ok",
        "data": data,
        "error": None,
        "meta": {
            "request_id": request_id,
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
            "timestamp_utc": _now(),
        },
    }


def _failure(
    command: str,
    *,
    code: str,
    message: str,
    hint: str,
    retryable: bool,
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
        "meta": {
            "request_id": request_id,
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
            "timestamp_utc": _now(),
        },
    }


def _plain(payload: dict[str, Any]) -> str:
    if payload["status"] == "error":
        error = payload["error"]
        return f"{error['code']}: {error['message']}"
    data = payload["data"]
    if data.get("dry_run"):
        return _canonical_json(data["plan"], pretty=True)
    if "runs" in data and "complete" in data:
        return (
            f"days={data['complete']} complete "
            f"failed={data['failed']} rank={data['plan']['rank_version']}"
        )
    return " ".join(
        (
            f"run_id={data['run_id']}",
            f"day={data['day']}",
            f"status={data['status']}",
            f"stage={data['stage']}",
            f"thread_id={data.get('codex_thread_id') or ''}",
            f"editorial_run_id={data.get('editorial_run_id') or ''}",
        )
    )


def main(argv: list[str] | None = None) -> int:
    started = time.monotonic()
    request_id = str(uuid4())
    args: argparse.Namespace | None = None
    command = "daily-intelligence"
    exit_code = 0
    try:
        args = _parser().parse_args(argv)
        command = f"daily-intelligence.{args.action}"
        if args.action == "inspect-day-run":
            data = inspect_run(db_path=args.db, run_id=args.run_id, day=args.day)
        elif args.action == "run-batch":
            progress = None
            if args.progress == "plain":
                progress = lambda stage, status: print(
                    f"stage={stage} status={status}", file=sys.stderr, flush=True
                )
            data = run_batch(
                through=args.through,
                days=args.days,
                db_path=args.db,
                day_workers=args.day_workers,
                codex_timeout_seconds=args.codex_timeout_seconds,
                codex_binary=args.codex_binary,
                codex_model=args.codex_model,
                codex_reasoning_effort=args.codex_reasoning_effort,
                codex_service_tier=args.codex_service_tier,
                skill_path=args.skill_path,
                dry_run=args.dry_run,
                progress=progress,
            )
        else:
            progress = None
            if args.progress == "plain":
                progress = lambda stage, status: print(
                    f"stage={stage} status={status}", file=sys.stderr, flush=True
                )
            data = run_day(
                day=args.day,
                db_path=args.db,
                evidence_days=args.evidence_days,
                collection_days=args.collection_days,
                workers=args.workers,
                top_ranked=args.top_ranked,
                routing_workers=args.routing_workers,
                routing_day_workers=args.routing_day_workers,
                stop_after=args.stop_after,
                launch_codex=args.launch_codex,
                codex_timeout_seconds=args.codex_timeout_seconds,
                codex_binary=args.codex_binary,
                codex_model=args.codex_model,
                codex_reasoning_effort=args.codex_reasoning_effort,
                codex_service_tier=args.codex_service_tier,
                skill_path=args.skill_path,
                dry_run=args.dry_run,
                progress=progress,
            )
        payload = _success(command, data, request_id=request_id, started=started)
    except (DailyRunError, CodexTaskError) as error:
        exit_code = error.exit_code
        payload = _failure(
            command,
            code=error.code,
            message=error.message,
            hint=error.hint,
            retryable=error.retryable,
            request_id=request_id,
            started=started,
        )
    except (ValueError, FileNotFoundError) as error:
        exit_code = 2
        payload = _failure(
            command,
            code="E_INVALID_INPUT",
            message=str(error),
            hint="Correct the command arguments or missing local dependency and retry.",
            retryable=False,
            request_id=request_id,
            started=started,
        )
    except KeyboardInterrupt:
        exit_code = 5
        payload = _failure(
            command,
            code="E_INTERRUPTED",
            message="Daily run was interrupted.",
            hint="Resume the identical command; completed stages and task id are retained.",
            retryable=True,
            request_id=request_id,
            started=started,
        )
    except Exception as error:
        exit_code = 1
        payload = _failure(
            command,
            code="E_INTERNAL",
            message=f"{type(error).__name__}: {error}",
            hint="Inspect the durable run and resume the identical command.",
            retryable=True,
            request_id=request_id,
            started=started,
        )
    print(_plain(payload) if bool(args and args.plain) else _canonical_json(payload))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
