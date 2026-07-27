"""Read-only projection of completed audience-routing runs for Feed audit UI."""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any

from fli.routing import model
from fli.scoring import attention


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ROUTING_ROOT = REPO_ROOT / "data" / "derived" / "audience-routing"


def _open_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _db_version(path: Path) -> tuple[str, int, int, int, int]:
    try:
        stat = path.stat()
        main_mtime, main_size = stat.st_mtime_ns, stat.st_size
    except FileNotFoundError:
        main_mtime, main_size = 0, 0
    wal = Path(f"{path}-wal")
    try:
        wal_stat = wal.stat()
        wal_mtime, wal_size = wal_stat.st_mtime_ns, wal_stat.st_size
    except FileNotFoundError:
        wal_mtime, wal_size = 0, 0
    return str(path.resolve()), main_mtime, main_size, wal_mtime, wal_size


def _complete_run(
    path: Path,
    day: str,
    expected_rank_input_sha256: str | None,
    expected_event_run_id: str | None = None,
    expected_feed_run_id: str | None = None,
) -> tuple[str, str] | None:
    try:
        conn = _open_readonly(path)
        meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
        meta_columns = {
            str(row["name"])
            for row in conn.execute("PRAGMA table_info(run_meta)").fetchall()
        }
        rank_version = (
            str(meta["rank_version"])
            if meta is not None and "rank_version" in meta_columns
            else ""
        )
        if (
            meta is None
            or "source_rank_input_sha256" not in meta_columns
            or str(meta["day"]) != day
            or rank_version != attention.DAILY_RANK_VERSION
            or (
                expected_rank_input_sha256 is not None
                and str(meta["source_rank_input_sha256"])
                != expected_rank_input_sha256
            )
            or (
                expected_event_run_id is not None
                and str(meta["source_event_run_id"]) != expected_event_run_id
            )
            or (
                expected_feed_run_id is not None
                and str(meta["source_feed_run_id"]) != expected_feed_run_id
            )
            or str(meta["prompt_version"]) != model.PROMPT_VERSION
            or str(meta["prompt_sha256"]) != model.prompt_sha256()
            or str(meta["schema_version"]) != model.SCHEMA_VERSION
        ):
            conn.close()
            return None
        status = conn.execute(
            """SELECT COUNT(*) AS completed,
                      MAX(completed_at) AS latest_completion
               FROM routing_item
               WHERE status = 'complete'"""
        ).fetchone()
        conn.close()
    except (sqlite3.Error, OSError):
        return None
    if int(status["completed"]) != int(meta["expected_count"]):
        return None
    return str(status["latest_completion"] or meta["updated_at"]), str(meta["run_id"])


def latest_complete_run(
    day: str,
    *,
    expected_rank_input_sha256: str | None = None,
    expected_event_run_id: str | None = None,
    expected_feed_run_id: str | None = None,
    root: Path | None = None,
) -> Path | None:
    """Select the newest fully completed run for the current routing contract."""
    routing_root = DEFAULT_ROUTING_ROOT if root is None else root
    if not routing_root.is_dir():
        return None
    candidates: list[tuple[str, str, Path]] = []
    for path in routing_root.glob("*/routing.db"):
        identity = _complete_run(
            path,
            day,
            expected_rank_input_sha256,
            expected_event_run_id,
            expected_feed_run_id,
        )
        if identity is not None:
            candidates.append((*identity, path))
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: (candidate[0], candidate[1]))[2]


def cache_token(
    day: str,
    *,
    expected_rank_input_sha256: str | None = None,
    expected_event_run_id: str | None = None,
    expected_feed_run_id: str | None = None,
) -> tuple[tuple[str, int, int, int, int], ...]:
    """Invalidate when a matching run becomes complete or is replaced."""
    return tuple(
        _db_version(path)
        for path in sorted(DEFAULT_ROUTING_ROOT.glob("*/routing.db"))
        if _complete_run(
            path,
            day,
            expected_rank_input_sha256,
            expected_event_run_id,
            expected_feed_run_id,
        )
        is not None
    )


@lru_cache(maxsize=16)
def _routing_payload_cached(
    day: str,
    expected_rank_input_sha256: str,
    expected_event_run_id: str,
    expected_feed_run_id: str,
    token: tuple[tuple[str, int, int, int, int], ...],
) -> dict[str, Any]:
    del token
    path = latest_complete_run(
        day,
        expected_rank_input_sha256=expected_rank_input_sha256,
        expected_event_run_id=expected_event_run_id,
        expected_feed_run_id=expected_feed_run_id,
    )
    if path is None:
        return {"available": False, "run": None, "items": {}}
    conn = _open_readonly(path)
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    rows = conn.execute(
        """SELECT event_id, feed_rank, semantic_snapshot_sha256,
                  evidence_sha256, input_sha256,
                  ai_engineering_relevant, ai_engineering_reason,
                  investment_relevant, investment_reason
           FROM routing_item
           WHERE status = 'complete'
           ORDER BY feed_rank, event_id"""
    ).fetchall()
    conn.close()
    if meta is None:
        return {"available": False, "run": None, "items": {}}
    items = {
        str(row["event_id"]): {
            "feed_rank": int(row["feed_rank"]),
            "semantic_snapshot_sha256": str(row["semantic_snapshot_sha256"]),
            "evidence_sha256": str(row["evidence_sha256"]),
            "input_sha256": str(row["input_sha256"]),
            "ai_engineering": {
                "relevant": bool(row["ai_engineering_relevant"]),
                "reason": str(row["ai_engineering_reason"]),
            },
            "investment": {
                "relevant": bool(row["investment_relevant"]),
                "reason": str(row["investment_reason"]),
            },
        }
        for row in rows
    }
    return {
        "available": True,
        "run": {
            "run_id": str(meta["run_id"]),
            "model": str(meta["model"]),
            "reasoning_effort": str(meta["reasoning_effort"]),
            "prompt_version": str(meta["prompt_version"]),
            "rank_version": str(meta["rank_version"]),
            "source_rank_input_sha256": str(
                meta["source_rank_input_sha256"]
            ),
            "source_event_run_id": str(meta["source_event_run_id"]),
            "source_feed_run_id": str(meta["source_feed_run_id"]),
            "selection_kind": str(meta["selection_kind"]),
            "selection_limit": (
                int(meta["selection_limit"])
                if meta["selection_limit"] is not None
                else None
            ),
            "expected_count": int(meta["expected_count"]),
            "completed_count": len(items),
            "updated_at": str(meta["updated_at"]),
        },
        "items": items,
    }


def routing_payload(
    day: str,
    *,
    expected_rank_input_sha256: str,
    expected_event_run_id: str,
    expected_feed_run_id: str,
) -> dict[str, Any]:
    """Return only routing bound to the exact current full-day rank inputs."""
    return _routing_payload_cached(
        day,
        expected_rank_input_sha256,
        expected_event_run_id,
        expected_feed_run_id,
        cache_token(
            day,
            expected_rank_input_sha256=expected_rank_input_sha256,
            expected_event_run_id=expected_event_run_id,
            expected_feed_run_id=expected_feed_run_id,
        ),
    )
