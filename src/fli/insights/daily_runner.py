"""Date-keyed orchestration from Evidence refresh to one Codex daily brief."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
import sqlite3
import sys
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fli.evidence import events as signal_events
from fli.evidence import feed as signal_feed
from fli.evidence import refresh as evidence_refresh
from fli.insights import editorial, editorial_runs
from fli.insights.codex_app_server import CodexAppServerClient, CodexTaskError
from fli.routing import model as routing_model
from fli.routing import runs as routing_runs


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = editorial_runs.DEFAULT_DB
DEFAULT_SKILL_PATH = REPO_ROOT / ".agents/skills/fli-daily-intelligence/SKILL.md"
CLI_SCHEMA_VERSION = "1.0"
STORE_SCHEMA_VERSION = "daily-orchestration-store-v1"
RUN_CONTRACT_VERSION = "daily-orchestration-v1"
DEFAULT_CODEX_TIMEOUT_SECONDS = 4 * 60 * 60
DEFAULT_EVIDENCE_WINDOW_DAYS = 9
PREPARATION_STAGES = ("evidence", "routing", "prepare")


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
            day TEXT NOT NULL UNIQUE,
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
        "SELECT * FROM daily_orchestration_run WHERE day = ?", (day,)
    ).fetchone()
    if row is not None:
        if str(row["config_sha256"]) != config_sha256:
            raise DailyRunError(
                code="E_RUN_CONFIG_MISMATCH",
                message=f"Daily orchestration for {day} already uses another contract.",
                hint=(
                    "Inspect the existing day run and resume it with identical options; "
                    "never create a second task for the same date implicitly."
                ),
                retryable=False,
                exit_code=2,
            )
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
            "plan",
            "model_requests",
            "counts",
            "runs",
            "will_call_model",
        )
        if key in value
    }


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
        row = conn.execute(
            """SELECT run_id FROM editorial_run
               WHERE workspace_run_id = ? AND status = 'complete'
               ORDER BY created_at DESC, run_id DESC LIMIT 1""",
            (workspace_run_id,),
        ).fetchone()
    finally:
        conn.close()
    return str(row[0]) if row else None


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
    skill_path: Path = DEFAULT_SKILL_PATH,
    dry_run: bool = False,
    progress: ProgressCallback | None = None,
    evidence_runner: EvidenceRunner = evidence_refresh.refresh_evidence,
    routing_runner: RoutingRunner = routing_runs.refresh_all_days,
    workspace_preparer: WorkspacePreparer = editorial_runs.prepare_workspace,
    workspace_loader: WorkspaceLoader = editorial_runs.load_manifest,
    workspace_template_loader: WorkspaceTemplateLoader = _load_json_object,
    codex_runner: CodexRunner | None = None,
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
        "routing_workers": routing_workers,
        "routing_day_workers": routing_day_workers,
        "repo_root": str(REPO_ROOT),
        "skill_path": str(skill_path.resolve()),
    }
    plan = {
        "day": day,
        "stop_after": "codex" if launch_codex else stop_after,
        "will_collect_external_evidence": True,
        "will_call_routing_model": True,
        "will_launch_codex": launch_codex,
        "config": config,
    }
    if dry_run:
        return {"dry_run": True, "plan": plan}

    conn = connect(db_path)
    current_stage = "planned"
    try:
        record, reused = _ensure_run(conn, day=day, config=config)
        stages = record["stages"]
        if record["status"] == "complete":
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
            evidence = stages["evidence"]
            if str(raw_routing.get("source_event_run_id") or "") != _event_run_id(evidence):
                raise DailyRunError(
                    code="E_SOURCE_CHANGED",
                    message="Audience routing used a different Event publication.",
                    hint="Resume the same command so evidence and routing can be frozen again.",
                    retryable=True,
                    exit_code=4,
                )
            if str(raw_routing.get("source_feed_run_id") or "") != _feed_run_id(evidence):
                raise DailyRunError(
                    code="E_SOURCE_CHANGED",
                    message="Audience routing used a different Feed publication.",
                    hint="Resume the same command so evidence and routing can be frozen again.",
                    retryable=True,
                    exit_code=4,
                )
            stages["routing"] = _compact_routing(raw_routing)
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
            workspace_run_id=str(workspace["run_id"])
        )
        if editorial_run_id:
            existing_codex = stages.get("codex") or {}
            stages["codex"] = {
                **existing_codex,
                "status": "complete",
                "completion_source": "editorial_run",
            }
            record["editorial_run_id"] = editorial_run_id
            record = _save_record(
                conn, record, status="complete", stage="codex", error=None
            )
            if progress:
                progress("codex", "complete")
            return {**record, "reused": reused}
        name = f"FLI Daily Brief — {day}"
        objective = (
            f"Produce, validate, import, and inspect the complete Frontier Lab "
            f"Intelligence daily brief for {day} from frozen workspace "
            f"{workspace['workspace']}. Follow the fli-daily-intelligence skill, "
            "review every candidate for both audiences, use web research when it "
            "materially resolves an unknown, and continue until the exact imported "
            "run is inspected. Do not modify product code or rerun Evidence/routing. "
            "Mark the goal blocked only after exhausting safe in-scope recovery."
        )
        prompt = (
            f"Pursue the active goal for {day}. The deterministic handoff is already "
            f"prepared at {workspace['workspace']}. Read both audience contexts and "
            "the frozen manifest, follow the attached skill exactly, validate the full "
            "cohort, import it through the client, inspect the durable run, and then "
            "mark the goal complete."
        )

        def checkpoint(codex: dict[str, Any]) -> None:
            nonlocal record, stages
            stages["codex"] = codex
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
        existing_thread_id = str(
            record.get("codex_thread_id") or existing_codex.get("thread_id") or ""
        ) or None
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
                    thread_id=existing_thread_id,
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
                thread_id=existing_thread_id,
                progress=progress,
                checkpoint=checkpoint,
            )
        stages["codex"] = codex
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
            workspace_run_id=str(workspace["run_id"])
        )
        if not editorial_run_id:
            raise DailyRunError(
                code="E_EDITORIAL_RUN_MISSING",
                message="Codex completed without importing this workspace.",
                hint="Resume the persisted task and complete validation, import, and inspection.",
                retryable=True,
                exit_code=4,
            )
        record["editorial_run_id"] = editorial_run_id
        record = _save_record(
            conn, record, status="complete", stage="codex", error=None
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
    run.add_argument("--skill-path", type=Path, default=DEFAULT_SKILL_PATH)
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--progress", choices=("off", "plain"), default="plain")
    run.add_argument("--no-input", action="store_true")
    mode = run.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true")
    mode.add_argument("--plain", action="store_true")

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
