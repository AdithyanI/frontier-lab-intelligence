"""Frozen workspaces, vector retrieval, and durable daily editorial runs."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Callable

import numpy as np

from fli.insights import consolidation
from fli.insights import editorial
from fli.insights import runs as insight_runs
from fli.evidence.artifacts import store as artifact_store
from fli.routing import model as routing_model
from fli.routing import freshness
from fli.routing import runs as routing_runs
from fli.routing import view as routing_view
from fli.scoring import development_attention


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ROOT = REPO_ROOT / "data" / "derived" / "daily-intelligence"
DEFAULT_WORKSPACE_ROOT = DEFAULT_ROOT / "workspaces"
DEFAULT_DB = DEFAULT_ROOT / "editorial.db"
DEFAULT_ROUTING_ROOT = routing_runs.DEFAULT_RUN_ROOT
DEFAULT_INSIGHTS_DB = insight_runs.DEFAULT_DB
DEFAULT_MODEL = consolidation.DEFAULT_MODEL
WORKSPACE_SCHEMA_VERSION = "daily-intelligence-workspace-v3"
STORE_SCHEMA_VERSION = "daily-intelligence-store-v4"
READ_SCHEMA_VERSION = "daily-intelligence-read-v4"
INVESTMENT_CONTEXT_SCHEMA_VERSION = "bit-investment-context-v5"
BIT_PUBLIC_VIEW_GRADES = {"explicit_thesis", "commentary", "none"}
BIT_PUBLIC_VIEW_SOURCE_SCOPES = {"firm", "flagship", "other_product", "mixed", "none"}
EVENT_COMPANY_CONNECTION_TYPES = {"direct", "indirect", "none"}
EVENT_COMPANY_THESIS_EFFECTS = {
    "supports",
    "challenges",
    "mixed",
    "unclear",
    "no_public_thesis",
}

CONTEXT_PATHS = {
    "investment": (
        REPO_ROOT
        / ".agents"
        / "skills"
        / "fli-daily-intelligence"
        / "references"
        / "bit-investment-context.json"
    ),
    "ai_engineering": REPO_ROOT / "docs" / "references" / "ai-engineering-editorial-context.md",
}


class CompanyProfileNotFound(ValueError):
    """The exact company name, ticker, or alias is absent from the packet."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS editorial_run (
    run_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    draft_schema_version TEXT NOT NULL,
    day TEXT NOT NULL,
    workspace_run_id TEXT NOT NULL,
    workspace_manifest_sha256 TEXT NOT NULL,
    source_routing_run_id TEXT NOT NULL,
    source_routing_db TEXT NOT NULL,
    source_cohort_sha256 TEXT NOT NULL,
    source_event_run_id TEXT NOT NULL,
    source_feed_run_id TEXT NOT NULL,
    skill_version TEXT NOT NULL,
    executor_model TEXT NOT NULL,
    executor_notes TEXT,
    result_sha256 TEXT NOT NULL,
    result_json TEXT NOT NULL,
    candidate_count INTEGER NOT NULL,
    candidate_pair_count INTEGER NOT NULL,
    insight_count INTEGER NOT NULL,
    citation_count INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status = 'complete'),
    created_at TEXT NOT NULL,
    UNIQUE(workspace_run_id, result_sha256)
);

CREATE TABLE IF NOT EXISTS editorial_candidate (
    run_id TEXT NOT NULL REFERENCES editorial_run(run_id) ON DELETE CASCADE,
    event_id TEXT NOT NULL,
    feed_rank INTEGER NOT NULL,
    root_url TEXT NOT NULL,
    semantic_snapshot_sha256 TEXT NOT NULL,
    evidence_sha256 TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    packet_json TEXT NOT NULL,
    ai_engineering_relevant INTEGER NOT NULL CHECK (ai_engineering_relevant IN (0, 1)),
    ai_engineering_reason TEXT NOT NULL,
    investment_relevant INTEGER NOT NULL CHECK (investment_relevant IN (0, 1)),
    investment_reason TEXT NOT NULL,
    PRIMARY KEY (run_id, event_id),
    UNIQUE (run_id, feed_rank)
);

CREATE TABLE IF NOT EXISTS editorial_insight (
    run_id TEXT NOT NULL REFERENCES editorial_run(run_id) ON DELETE CASCADE,
    insight_id TEXT NOT NULL,
    local_id TEXT NOT NULL,
    audience TEXT NOT NULL CHECK (audience IN ('investment', 'ai_engineering')),
    display_rank INTEGER NOT NULL CHECK (display_rank >= 1),
    rank_rationale TEXT NOT NULL,
    title TEXT NOT NULL,
    what_changed TEXT NOT NULL,
    interpretation TEXT NOT NULL,
    next_step TEXT NOT NULL,
    analysis_json TEXT NOT NULL,
    PRIMARY KEY (run_id, insight_id),
    UNIQUE (run_id, local_id),
    UNIQUE (run_id, audience, display_rank)
);

CREATE TABLE IF NOT EXISTS editorial_insight_event (
    run_id TEXT NOT NULL,
    insight_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('primary', 'supporting', 'context', 'counterevidence')),
    reason TEXT NOT NULL,
    PRIMARY KEY (run_id, insight_id, event_id),
    UNIQUE (run_id, event_id, insight_id),
    FOREIGN KEY (run_id, insight_id)
        REFERENCES editorial_insight(run_id, insight_id) ON DELETE CASCADE,
    FOREIGN KEY (run_id, event_id)
        REFERENCES editorial_candidate(run_id, event_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS editorial_event_disposition (
    run_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    audience TEXT NOT NULL CHECK (audience IN ('investment', 'ai_engineering')),
    status TEXT NOT NULL CHECK (status IN ('included', 'not_selected')),
    insight_id TEXT,
    reason TEXT NOT NULL,
    PRIMARY KEY (run_id, event_id, audience),
    FOREIGN KEY (run_id, event_id)
        REFERENCES editorial_candidate(run_id, event_id) ON DELETE CASCADE,
    FOREIGN KEY (run_id, insight_id)
        REFERENCES editorial_insight(run_id, insight_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS editorial_citation (
    run_id TEXT NOT NULL REFERENCES editorial_run(run_id) ON DELETE CASCADE,
    citation_id TEXT NOT NULL,
    local_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('event', 'artifact', 'web', 'context')),
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    event_id TEXT,
    artifact_id TEXT,
    published_at TEXT,
    retrieved_at TEXT,
    supports TEXT NOT NULL,
    excerpt TEXT,
    source_sha256 TEXT NOT NULL,
    PRIMARY KEY (run_id, citation_id),
    UNIQUE (run_id, local_id)
);

CREATE TABLE IF NOT EXISTS editorial_insight_citation (
    run_id TEXT NOT NULL,
    insight_id TEXT NOT NULL,
    citation_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    PRIMARY KEY (run_id, insight_id, citation_id),
    UNIQUE (run_id, insight_id, ordinal),
    FOREIGN KEY (run_id, insight_id)
        REFERENCES editorial_insight(run_id, insight_id) ON DELETE CASCADE,
    FOREIGN KEY (run_id, citation_id)
        REFERENCES editorial_citation(run_id, citation_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS event_embedding (
    event_id TEXT NOT NULL,
    model TEXT NOT NULL,
    input_contract TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    vector_f32 BLOB NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (event_id, model, input_contract, input_sha256)
);

CREATE INDEX IF NOT EXISTS idx_editorial_run_day_created
    ON editorial_run(day, created_at DESC, run_id);
CREATE INDEX IF NOT EXISTS idx_editorial_insight_audience_rank
    ON editorial_insight(run_id, audience, display_rank);
CREATE INDEX IF NOT EXISTS idx_editorial_disposition_event
    ON editorial_event_disposition(event_id, audience, run_id);
"""


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


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical_json(value, pretty=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _migrate_editorial_insight_v2(conn: sqlite3.Connection) -> None:
    """Collapse the first editorial memo shape into the smaller durable contract."""
    columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(editorial_insight)").fetchall()
    }
    if not {"impact_chain_json", "evidence_limitations_json"} <= columns:
        return

    rows = conn.execute(
        """SELECT run_id, insight_id, local_id, audience, display_rank,
                  title, what_changed, interpretation, evidence_limitations_json,
                  next_step, analysis_json
           FROM editorial_insight"""
    ).fetchall()
    with conn:
        conn.execute(
            """CREATE TABLE editorial_insight_v2 (
                   run_id TEXT NOT NULL REFERENCES editorial_run(run_id) ON DELETE CASCADE,
                   insight_id TEXT NOT NULL,
                   local_id TEXT NOT NULL,
                   audience TEXT NOT NULL CHECK (audience IN ('investment', 'ai_engineering')),
                   display_rank INTEGER NOT NULL CHECK (display_rank >= 1),
                   title TEXT NOT NULL,
                   what_changed TEXT NOT NULL,
                   interpretation TEXT NOT NULL,
                   next_step TEXT NOT NULL,
                   analysis_json TEXT NOT NULL,
                   PRIMARY KEY (run_id, insight_id),
                   UNIQUE (run_id, local_id),
                   UNIQUE (run_id, audience, display_rank)
               )"""
        )
        for row in rows:
            analysis = json.loads(str(row["analysis_json"]))
            if row["audience"] == "investment" and "key_uncertainty" not in analysis:
                limitations = json.loads(str(row["evidence_limitations_json"]))
                counter_case = str(analysis.get("counter_case") or "").strip()
                limitation = str(limitations[0]).strip() if limitations else ""
                uncertainty_parts = [counter_case]
                if limitation and limitation.casefold() not in counter_case.casefold():
                    uncertainty_parts.append(limitation)
                analysis = {
                    "affected_entities": analysis.get("affected_entities", []),
                    "key_uncertainty": " ".join(
                        part for part in uncertainty_parts if part
                    )
                    or "The available evidence does not yet establish the financial effect.",
                    "watchpoints": analysis.get("watchpoints", [])[:3],
                }
            conn.execute(
                """INSERT INTO editorial_insight_v2 (
                       run_id, insight_id, local_id, audience, display_rank,
                       title, what_changed, interpretation, next_step, analysis_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    row["run_id"],
                    row["insight_id"],
                    row["local_id"],
                    row["audience"],
                    row["display_rank"],
                    row["title"],
                    row["what_changed"],
                    row["interpretation"],
                    row["next_step"],
                    _canonical_json(analysis),
                ),
            )
        conn.execute("DROP TABLE editorial_insight")
        conn.execute("ALTER TABLE editorial_insight_v2 RENAME TO editorial_insight")


def _migrate_editorial_insight_v3(conn: sqlite3.Connection) -> None:
    """Add explicit editorial reasoning for each audience priority position."""
    columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(editorial_insight)").fetchall()
    }
    if not columns or "rank_rationale" in columns:
        return
    conn.execute(
        """ALTER TABLE editorial_insight
           ADD COLUMN rank_rationale TEXT NOT NULL DEFAULT
           'This historical run predates item-specific rank explanations. Its position reflects the editorial priority rubric across the complete daily brief.'"""
    )


def _migrate_engineering_analysis_v3(conn: sqlite3.Connection) -> None:
    """Collapse the original experiment scaffold into one measurable decision rule."""
    columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(editorial_insight)").fetchall()
    }
    if "analysis_json" not in columns:
        return
    rows = conn.execute(
        """SELECT run_id, insight_id, analysis_json
           FROM editorial_insight
           WHERE audience = 'ai_engineering'"""
    ).fetchall()
    updates: list[tuple[str, str, str]] = []
    for row in rows:
        analysis = json.loads(str(row["analysis_json"]))
        if set(analysis) == {"decision_rule"}:
            continue
        experiment = analysis.get("experiment")
        experiment = experiment if isinstance(experiment, dict) else {}
        success = str(experiment.get("success_metric") or "").strip().rstrip(".")
        stop = str(experiment.get("stop_condition") or "").strip().rstrip(".")
        if success and stop:
            decision_rule = (
                f"Proceed if the success criterion is met: {success}. "
                f"Stop or revise if: {stop}."
            )
        else:
            decision_rule = (
                "Proceed only when a bounded test demonstrates a measurable benefit; "
                "stop when it fails the stated quality, safety, cost, or reliability limit."
            )
        updates.append(
            (
                _canonical_json({"decision_rule": decision_rule}),
                str(row["run_id"]),
                str(row["insight_id"]),
            )
        )
    if updates:
        with conn:
            conn.executemany(
                """UPDATE editorial_insight SET analysis_json = ?
                   WHERE run_id = ? AND insight_id = ?""",
                updates,
            )


def migrate_editorial_store(path: Path | str = DEFAULT_DB) -> bool:
    """Migrate the editorial candidate table to semantic Event hash naming."""
    path = Path(path)
    if not path.is_file():
        return False
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 60000")
    changed = False
    try:
        columns = {
            str(row["name"])
            for row in conn.execute("PRAGMA table_info(editorial_candidate)").fetchall()
        }
        if "snapshot_content_sha256" not in columns:
            return False
        if "semantic_snapshot_sha256" in columns:
            raise RuntimeError(
                "editorial_candidate contains both legacy and Event-native snapshot columns"
            )
        with conn:
            conn.execute(
                "ALTER TABLE editorial_candidate RENAME COLUMN "
                "snapshot_content_sha256 TO semantic_snapshot_sha256"
            )
            conn.execute("PRAGMA user_version = 4")
        changed = True
        integrity = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity != "ok":
            raise RuntimeError(f"editorial storage integrity check failed: {integrity}")
        return changed
    finally:
        conn.close()


def connect(path: Path = DEFAULT_DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA foreign_keys = OFF")
    _migrate_editorial_insight_v2(conn)
    _migrate_editorial_insight_v3(conn)
    _migrate_engineering_analysis_v3(conn)
    conn.executescript(SCHEMA)
    conn.execute("PRAGMA user_version = 4")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _open_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _manifest_digest(manifest: dict[str, Any]) -> str:
    value = dict(manifest)
    value.pop("manifest_sha256", None)
    return _sha256(_canonical_json(value))


def load_manifest(workspace: Path) -> dict[str, Any]:
    path = workspace / "manifest.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    manifest = _read_json(path)
    if not isinstance(manifest, dict):
        raise ValueError("workspace manifest must be an object")
    recorded = manifest.get("manifest_sha256")
    if recorded != _manifest_digest(manifest):
        raise ValueError("workspace manifest hash does not match its content")
    if manifest.get("schema_version") != WORKSPACE_SCHEMA_VERSION:
        raise ValueError("workspace uses an unsupported schema version")
    return manifest


def _current_routing_lineage(
    day: str, routing_root: Path
) -> tuple[Path, dict[str, Any], dict[str, str]]:
    from fli.web import developments as development_store

    identity = development_store.current_rank_identity(day=day)
    if str(identity["rank_version"]) != development_attention.DAILY_RANK_VERSION:
        raise ValueError(f"current Development rank version is invalid for {day}")
    path = routing_view.latest_complete_run(
        day,
        expected_rank_input_sha256=identity["rank_input_sha256"],
        expected_event_run_id=identity["event_run_id"],
        expected_feed_run_id=identity["feed_run_id"],
        root=routing_root,
    )
    if path is None:
        raise ValueError(f"no complete current routing run found for {day}")
    conn = _open_readonly(path)
    try:
        meta_row = conn.execute(
            "SELECT * FROM run_meta WHERE singleton = 1"
        ).fetchone()
    finally:
        conn.close()
    if meta_row is None:
        raise ValueError(f"routing metadata is missing for {day}")
    meta = dict(meta_row)
    if (
        str(meta["rank_version"]) != str(identity["rank_version"])
        or str(meta["source_rank_input_sha256"])
        != str(identity["rank_input_sha256"])
        or str(meta["source_event_run_id"]) != str(identity["event_run_id"])
        or str(meta["source_feed_run_id"]) != str(identity["feed_run_id"])
    ):
        raise ValueError(f"routing lineage is not current for {day}")
    return path, meta, {
        "rank_version": str(identity["rank_version"]),
        "rank_input_sha256": str(identity["rank_input_sha256"]),
        "event_run_id": str(identity["event_run_id"]),
        "feed_run_id": str(identity["feed_run_id"]),
    }


def _current_routing_run(day: str, routing_root: Path) -> tuple[Path, dict[str, Any]]:
    path, meta, _ = _current_routing_lineage(day, routing_root)
    return path, meta


def _db_version(path: Path) -> tuple[str, int, int, int, int]:
    """Return a compact invalidation token for one SQLite source."""
    try:
        stat = path.stat()
        main_mtime, main_size = stat.st_mtime_ns, stat.st_size
    except FileNotFoundError:
        main_mtime, main_size = 0, 0
    wal = Path(f"{path}-wal")
    try:
        wal_stat = wal.stat()
        wal_size = wal_stat.st_size
        wal_mtime = wal_stat.st_mtime_ns if wal_size else 0
    except FileNotFoundError:
        wal_mtime, wal_size = 0, 0
    return str(path.resolve()), main_mtime, main_size, wal_mtime, wal_size


def _editorial_lineage_source_token(
    routing_root: Path,
) -> tuple[tuple[str, int, int, int, int], ...]:
    """Track every source whose replacement can stale an editorial run."""
    from fli.web import events as event_store

    paths = [
        event_store.DEFAULT_EVENTS_DB,
        event_store.DEFAULT_FEED_DB,
        event_store.feed_store.DEFAULT_REGISTRY_DB,
    ]
    analysis = event_store.feed_store._latest_analysis_db()
    if analysis is not None:
        paths.append(analysis)
    paths.extend(sorted(routing_root.glob("*/routing.db")))
    return tuple(_db_version(path) for path in paths)


def _root_source(packet: dict[str, Any]) -> dict[str, Any]:
    sources = packet.get("sources", [])
    for source in sources if isinstance(sources, list) else []:
        if isinstance(source, dict) and source.get("relation") == "root":
            return source
    return {}


def _source_index(packet: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    urls: list[str] = []
    artifacts: list[dict[str, Any]] = []
    for source in packet.get("sources", []):
        if not isinstance(source, dict):
            continue
        url = str(source.get("url") or "").strip()
        if url and url not in urls:
            urls.append(url)
        if source.get("source_type") == "artifact" and url:
            artifacts.append(
                {
                    "artifact_id": str(source.get("source_id") or ""),
                    "url": url,
                    "title": str(source.get("title") or "Primary artifact"),
                    "disclosures": list(source.get("disclosures") or []),
                }
            )
    return urls, artifacts


def _event_x_publication_times(
    *, day: str, routing_meta: dict[str, Any]
) -> dict[str, dict[str, str]]:
    """Resolve X publication times from the Development projection bound to routing."""
    from fli.web import developments as development_store

    payload = development_store.developments_payload(
        day=day,
        lane="all",
        sort="rank",
        query="",
        routing_filter="all",
        limit=1_000_000,
        offset=0,
        include_evidence=True,
    )
    if not payload.get("available"):
        raise ValueError(str(payload.get("reason") or "Evidence is unavailable"))
    source = dict(payload.get("run") or {})
    if (
        str(source.get("run_id") or "")
        != str(routing_meta["source_event_run_id"])
        or str(source.get("feed_run_id") or "")
        != str(routing_meta["source_feed_run_id"])
    ):
        raise ValueError(
            "Development source publication changed after routing was frozen"
        )
    result: dict[str, dict[str, str]] = {}
    for item in payload.get("items") or []:
        development_id = str(item["development_id"])
        times: dict[str, str] = {}
        for source_event in item.get("source_events") or []:
            for source in [
                source_event["post"],
                *(source_event.get("evidence") or []),
            ]:
                source_id = str(source.get("post_id") or "")
                published_at = str(source.get("published_at") or "")
                if source_id and published_at:
                    times[source_id] = published_at
        result[development_id] = times
    return result


def _event_artifact_disclosures(
    *,
    day: str,
    artifact_db: Path,
    event_ids: set[str],
) -> dict[str, dict[str, list[dict[str, str]]]]:
    """Resolve exact Event disclosures under their parent Developments."""
    if not event_ids:
        return {}
    if not artifact_db.is_file():
        raise FileNotFoundError(artifact_db)
    from fli.web import developments as development_store

    payload = development_store.developments_payload(
        day=day,
        lane="all",
        sort="rank",
        query="",
        routing_filter="all",
        limit=1_000_000,
        offset=0,
        include_evidence=False,
    )
    exact_to_development = {
        str(source_event_id): str(item["development_id"])
        for item in payload.get("items") or []
        if str(item["development_id"]) in event_ids
        for source_event_id in item["source_event_ids"]
    }
    exact_event_ids = set(exact_to_development)
    if not exact_event_ids:
        return {}
    placeholders = ",".join("?" for _ in exact_event_ids)
    conn = _open_readonly(artifact_db)
    try:
        rows = conn.execute(
            f"""SELECT candidate.event_id, candidate.artifact_id,
                       candidate.disclosure_external_id,
                       candidate.disclosure_url,
                       candidate.disclosure_published_at,
                       candidate.relation
                FROM artifact_import_candidate AS candidate
                JOIN artifact_import_run AS import_run USING (import_run_id)
                WHERE candidate.decision = 'accepted'
                  AND candidate.artifact_id IS NOT NULL
                  AND import_run.selection_policy = ?
                  AND candidate.event_id IN ({placeholders})
                ORDER BY candidate.event_id, candidate.artifact_id,
                         candidate.disclosure_published_at,
                         candidate.disclosure_external_id""",
            (
                artifact_store.PRIMARY_AUTHOR_SELECTION_POLICY,
                *sorted(exact_event_ids),
            ),
        ).fetchall()
    finally:
        conn.close()
    result: dict[str, dict[str, list[dict[str, str]]]] = {}
    seen: set[tuple[str, str, str, str]] = set()
    for row in rows:
        event_id = exact_to_development[str(row["event_id"])]
        artifact_id = str(row["artifact_id"])
        source_id = str(row["disclosure_external_id"])
        published_at = str(row["disclosure_published_at"])
        identity = (event_id, artifact_id, source_id, published_at)
        if identity in seen:
            continue
        seen.add(identity)
        result.setdefault(event_id, {}).setdefault(artifact_id, []).append(
            {
                "source_id": source_id,
                "source_url": str(row["disclosure_url"]),
                "published_at": published_at,
                "relation": str(row["relation"]),
            }
        )
    return result


def _prior_insights(day: str, path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    if not path.is_file():
        return {}
    conn = _open_readonly(path)
    try:
        rows = conn.execute(
            """WITH ranked AS (
                   SELECT item.*, run.source_routing_db,
                          ROW_NUMBER() OVER (
                              PARTITION BY item.event_id, item.audience
                              ORDER BY item.completed_at DESC, item.run_id DESC
                          ) AS recency
                   FROM insight_item AS item
                   JOIN insight_run AS run ON run.run_id = item.run_id
                   WHERE item.day = ? AND item.status = 'complete'
               )
               SELECT * FROM ranked WHERE recency = 1""",
            (day,),
        ).fetchall()
    except sqlite3.DatabaseError:
        rows = []
    finally:
        conn.close()
    return {
        (str(row["event_id"]), str(row["audience"])): {
            "decision": str(row["decision"]),
            "title": str(row["title"]),
            "summary": row["summary"],
            "why_it_matters": row["why_it_matters"],
            "action": row["action"],
            "suppression_reason": row["suppression_reason"],
            "prompt_version": str(row["prompt_version"]),
            "input_sha256": str(row["input_sha256"]),
            "source_routing_db": str(row["source_routing_db"]),
        }
        for row in rows
    }


def _context_files() -> dict[str, dict[str, str]]:
    result = {}
    for audience, path in CONTEXT_PATHS.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        text = path.read_text(encoding="utf-8")
        result[audience] = {"path": _display_path(path), "sha256": _sha256(text)}
    return result


def investment_context() -> dict[str, Any]:
    """Load the skill-owned, structured BIT Investment reference packet."""
    path = CONTEXT_PATHS["investment"]
    value = _read_json(path)
    if not isinstance(value, dict):
        raise ValueError("Investment context packet must be an object")
    if value.get("schema_version") != INVESTMENT_CONTEXT_SCHEMA_VERSION:
        raise ValueError("Investment context packet uses an unsupported schema version")
    _validate_company_profiles(value)
    return value


def company_context(query: str) -> dict[str, Any]:
    """Return one exact reusable company lens by canonical name, ticker, or alias."""
    normalized = " ".join(query.split()).casefold()
    if not normalized:
        raise ValueError("company query must not be empty")
    context = investment_context()
    matches: list[tuple[dict[str, Any], str]] = []
    for profile in context["company_profiles"]:
        candidates = {
            "name": [profile["name"]],
            "ticker": [profile["ticker"]],
            "alias": profile["aliases"],
        }
        for match_type, values in candidates.items():
            if any(" ".join(value.split()).casefold() == normalized for value in values):
                matches.append((profile, match_type))
                break
    if not matches:
        raise CompanyProfileNotFound(f"no company profile matches {query!r}")
    if len(matches) != 1:
        raise ValueError(f"company query {query!r} is ambiguous")
    profile, match_type = matches[0]
    holding = next(
        item for item in _covered_holdings(context) if item["name"] == profile["name"]
    )
    current = context.get("portfolio_current_top_ten")
    current_holding = None
    if isinstance(current, dict) and isinstance(current.get("holdings"), list):
        current_holding = next(
            (
                item
                for item in current["holdings"]
                if isinstance(item, dict) and item.get("name") == profile["name"]
            ),
            None,
        )
    return {
        "context_schema_version": context["schema_version"],
        "company_profiles_reviewed_at": context["company_profiles_reviewed_at"],
        "query": query,
        "matched_by": match_type,
        "portfolio_holding": holding,
        "current_top_ten_holding": current_holding,
        "profile": profile,
    }


def _covered_holdings(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Audited baseline holdings plus later-disclosed positions, in disclosure order.

    The 31 December 2025 annual report is the last complete public portfolio. The
    monthly factsheet discloses only a current top ten, so positions opened during
    2026 appear there and nowhere else. Both are kept with their own provenance
    rather than merged into one undated list.
    """
    holdings = [item for item in context["portfolio"]["holdings"] if isinstance(item, dict)]
    seen = {item.get("name") for item in holdings}
    current = context.get("portfolio_current_top_ten")
    if isinstance(current, dict) and isinstance(current.get("holdings"), list):
        for item in current["holdings"]:
            if isinstance(item, dict) and item.get("name") not in seen:
                holdings.append(item)
                seen.add(item.get("name"))
    return holdings


def _validate_company_profiles(context: dict[str, Any]) -> None:
    """Require one source-graded reusable lens for every working holding."""
    portfolio = context.get("portfolio")
    if not isinstance(portfolio, dict) or not isinstance(portfolio.get("holdings"), list):
        raise ValueError("Investment context packet is missing portfolio holdings")
    mapping_policy = context.get("event_company_mapping")
    if not isinstance(mapping_policy, dict) or set(mapping_policy) != {
        "candidate_universe",
        "connection_types",
        "thesis_effects",
        "shortlist_rule",
        "publication_rule",
    }:
        raise ValueError(
            "Investment context packet is missing event_company_mapping"
        )
    if mapping_policy["candidate_universe"] != "all_profiles":
        raise ValueError("event_company_mapping.candidate_universe must be all_profiles")
    _validate_string_list(
        mapping_policy["connection_types"],
        "event_company_mapping.connection_types",
        allow_empty=False,
    )
    if set(mapping_policy["connection_types"]) != EVENT_COMPANY_CONNECTION_TYPES:
        raise ValueError(
            "event_company_mapping.connection_types must define direct, indirect, and none"
        )
    _validate_string_list(
        mapping_policy["thesis_effects"],
        "event_company_mapping.thesis_effects",
        allow_empty=False,
    )
    if set(mapping_policy["thesis_effects"]) != EVENT_COMPANY_THESIS_EFFECTS:
        raise ValueError(
            "event_company_mapping.thesis_effects must define the complete thesis-effect set"
        )
    for key in ("shortlist_rule", "publication_rule"):
        if not isinstance(mapping_policy[key], str) or not mapping_policy[key].strip():
            raise ValueError(f"event_company_mapping.{key} must be non-empty")
    profiles = context.get("company_profiles")
    if not isinstance(profiles, list):
        raise ValueError("Investment context packet is missing company_profiles")
    reviewed_at = context.get("company_profiles_reviewed_at")
    if not isinstance(reviewed_at, str):
        raise ValueError("Investment context packet is missing company_profiles_reviewed_at")
    try:
        datetime.strptime(reviewed_at, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("company_profiles_reviewed_at must be an ISO date") from exc

    covered = _covered_holdings(context)
    holding_names = [item.get("name") for item in covered]
    profile_names = [item.get("name") for item in profiles if isinstance(item, dict)]
    if len(holding_names) != len(covered) or any(
        not isinstance(name, str) or not name for name in holding_names
    ):
        raise ValueError("Investment context portfolio contains an invalid holding name")
    if profile_names != holding_names:
        raise ValueError("Investment company_profiles must match portfolio holding order exactly")

    tickers: set[str] = set()
    lookup_owners: dict[str, str] = {}
    for index, profile in enumerate(profiles):
        path = f"company_profiles[{index}]"
        if not isinstance(profile, dict):
            raise ValueError(f"{path} must be an object")
        required = {
            "name",
            "ticker",
            "aliases",
            "listing_status",
            "bit_public_view",
            "analyst_context",
            "identity_sources",
        }
        if set(profile) != required:
            raise ValueError(f"{path} must contain exactly {sorted(required)}")
        ticker = profile["ticker"]
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError(f"{path}.ticker must be a non-empty string")
        if ticker in tickers:
            raise ValueError(f"{path}.ticker duplicates {ticker}")
        tickers.add(ticker)
        if profile["listing_status"] != "public":
            raise ValueError(f"{path}.listing_status must be public")
        _validate_string_list(profile["aliases"], f"{path}.aliases", allow_empty=True)
        for lookup_value in (profile["name"], profile["ticker"], *profile["aliases"]):
            lookup_key = " ".join(lookup_value.split()).casefold()
            prior_owner = lookup_owners.get(lookup_key)
            if prior_owner is not None and prior_owner != profile["name"]:
                raise ValueError(
                    f"{path} lookup value {lookup_value!r} duplicates {prior_owner}"
                )
            lookup_owners[lookup_key] = profile["name"]

        bit_view = profile["bit_public_view"]
        if not isinstance(bit_view, dict) or set(bit_view) != {
            "grade",
            "source_scope",
            "thesis",
            "edge",
            "signals",
            "countercase",
            "sources",
        }:
            raise ValueError(f"{path}.bit_public_view has an invalid shape")
        if bit_view["grade"] not in BIT_PUBLIC_VIEW_GRADES:
            raise ValueError(f"{path}.bit_public_view.grade is invalid")
        if bit_view["source_scope"] not in BIT_PUBLIC_VIEW_SOURCE_SCOPES:
            raise ValueError(f"{path}.bit_public_view.source_scope is invalid")
        for key in ("thesis", "edge", "countercase"):
            value = bit_view[key]
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{path}.bit_public_view.{key} must be null or text")
        _validate_string_list(
            bit_view["signals"],
            f"{path}.bit_public_view.signals",
            allow_empty=True,
        )
        _validate_source_refs(
            bit_view["sources"],
            f"{path}.bit_public_view.sources",
            allow_empty=True,
        )
        if bit_view["grade"] == "none" and any(
            bit_view[key] not in (None, [], "")
            for key in ("thesis", "edge", "signals", "countercase", "sources")
        ):
            raise ValueError(f"{path}.bit_public_view must be empty when grade is none")
        if (bit_view["grade"] == "none") != (bit_view["source_scope"] == "none"):
            raise ValueError(f"{path}.bit_public_view none grade and scope must match")
        if bit_view["grade"] != "none" and not bit_view["sources"]:
            raise ValueError(f"{path}.bit_public_view requires a BIT source")

        analyst = profile["analyst_context"]
        if not isinstance(analyst, dict) or set(analyst) != {
            "business_summary",
            "operating_drivers",
            "frontier_ai_channels",
            "cautions",
        }:
            raise ValueError(f"{path}.analyst_context has an invalid shape")
        if not isinstance(analyst["business_summary"], str) or not analyst[
            "business_summary"
        ].strip():
            raise ValueError(f"{path}.analyst_context.business_summary is required")
        _validate_string_list(
            analyst["operating_drivers"],
            f"{path}.analyst_context.operating_drivers",
        )
        _validate_string_list(
            analyst["cautions"],
            f"{path}.analyst_context.cautions",
            allow_empty=True,
        )
        channels = analyst["frontier_ai_channels"]
        if not isinstance(channels, list) or not channels:
            raise ValueError(f"{path}.analyst_context.frontier_ai_channels is required")
        for channel_index, channel in enumerate(channels):
            channel_path = f"{path}.analyst_context.frontier_ai_channels[{channel_index}]"
            if not isinstance(channel, dict) or set(channel) != {
                "channel",
                "potential_upside",
                "potential_downside",
                "watchpoints",
            }:
                raise ValueError(f"{channel_path} has an invalid shape")
            for key in ("channel", "potential_upside", "potential_downside"):
                if not isinstance(channel[key], str) or not channel[key].strip():
                    raise ValueError(f"{channel_path}.{key} is required")
            _validate_string_list(
                channel["watchpoints"],
                f"{channel_path}.watchpoints",
            )
        _validate_source_refs(profile["identity_sources"], f"{path}.identity_sources")


def _validate_string_list(value: Any, path: str, *, allow_empty: bool = False) -> None:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValueError(f"{path} must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{path} must contain only non-empty strings")


def _validate_source_refs(value: Any, path: str, *, allow_empty: bool = False) -> None:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValueError(f"{path} must be a non-empty list")
    for index, source in enumerate(value):
        if not isinstance(source, dict) or set(source) != {"label", "url"}:
            raise ValueError(f"{path}[{index}] must contain label and url")
        if any(
            not isinstance(source[key], str) or not source[key].strip()
            for key in ("label", "url")
        ):
            raise ValueError(f"{path}[{index}] must contain non-empty strings")


def portfolio_reference_payload() -> dict[str, Any]:
    """Return the compact reader disclosure derived from the canonical packet."""
    context = investment_context()
    portfolio = context.get("portfolio")
    if not isinstance(portfolio, dict):
        raise ValueError("Investment context packet is missing portfolio")
    source = portfolio.get("source")
    if not isinstance(source, dict):
        raise ValueError("Investment context packet is missing portfolio.source")
    return {
        "basis": str(portfolio["basis"]),
        "as_of": str(portfolio["as_of"]),
        "source_label": str(source["label"]),
        "source_url": str(source["url"]),
        "reader_note": str(context["reader_note"]),
    }


def investment_company_universe_payload() -> dict[str, Any]:
    """Return the complete, dated company-context read model for BIT Lens."""
    context = investment_context()
    audited = context["portfolio"]
    current = context["portfolio_current_top_ten"]
    audited_by_name = {
        item["name"]: item
        for item in audited["holdings"]
        if isinstance(item, dict)
    }
    current_by_name = {
        item["name"]: {**item, "rank": rank}
        for rank, item in enumerate(current["holdings"], start=1)
        if isinstance(item, dict)
    }

    companies = []
    for profile in context["company_profiles"]:
        name = profile["name"]
        audited_holding = audited_by_name.get(name)
        current_holding = current_by_name.get(name)
        reference_holding = current_holding or audited_holding
        reference_basis = (
            "current_top_ten" if current_holding else "audited_baseline"
        )
        companies.append(
            {
                **profile,
                "portfolio_context": {
                    "reference_holding": {
                        "as_of": (
                            current["as_of"]
                            if current_holding
                            else audited["as_of"]
                        ),
                        "weight_pct": reference_holding["weight_pct"],
                        "basis": reference_basis,
                        "currently_confirmed": current_holding is not None,
                    },
                    "current_top_ten": (
                        {
                            "as_of": current["as_of"],
                            "rank": current_holding["rank"],
                            "weight_pct": current_holding["weight_pct"],
                        }
                        if current_holding
                        else None
                    ),
                    "audited_baseline": (
                        {
                            "as_of": audited["as_of"],
                            "weight_pct": audited_holding["weight_pct"],
                        }
                        if audited_holding
                        else None
                    ),
                },
            }
        )

    grade_counts = {
        grade: sum(
            profile["bit_public_view"]["grade"] == grade
            for profile in context["company_profiles"]
        )
        for grade in ("explicit_thesis", "commentary", "none")
    }
    channel_count = sum(
        len(profile["analyst_context"]["frontier_ai_channels"])
        for profile in context["company_profiles"]
    )
    later_additions = sum(
        company["portfolio_context"]["current_top_ten"] is not None
        and company["portfolio_context"]["audited_baseline"] is None
        for company in companies
    )
    return {
        "schema_version": "investment-company-universe-v4",
        "source_context_schema_version": context["schema_version"],
        "profiles_reviewed_at": context["company_profiles_reviewed_at"],
        "mapping_policy": context["event_company_mapping"],
        "disclosures": {
            "current_top_ten": {
                "as_of": current["as_of"],
                "position_count": current["position_count"],
                "visible_holding_count": len(current["holdings"]),
                "source": {
                    "label": current["source"]["label"],
                    "url": current["source"]["url"],
                },
            },
            "audited_baseline": {
                "as_of": audited["as_of"],
                "visible_holding_count": len(audited["holdings"]),
                "source": {
                    "label": audited["source"]["label"],
                    "url": audited["source"]["url"],
                },
            },
        },
        "counts": {
            "companies": len(companies),
            "current_top_ten": len(current["holdings"]),
            "audited_baseline": len(audited["holdings"]),
            "later_top_ten_additions": later_additions,
            "frontier_ai_channels": channel_count,
            "bit_public_views": grade_counts["explicit_thesis"]
            + grade_counts["commentary"],
            "bit_public_view_grades": grade_counts,
        },
        "companies": companies,
    }


def prepare_workspace(
    *,
    day: str,
    routing_root: Path = DEFAULT_ROUTING_ROOT,
    insights_db: Path = DEFAULT_INSIGHTS_DB,
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Freeze the union-positive routing cohort into one agent-readable workspace."""
    datetime.strptime(day, "%Y-%m-%d")
    routing_path, meta = _current_routing_run(day, routing_root)
    prior = _prior_insights(day, insights_db)
    conn = _open_readonly(routing_path)
    try:
        rows = conn.execute(
            """SELECT * FROM routing_item
               WHERE status = 'complete'
                 AND (ai_engineering_relevant = 1 OR investment_relevant = 1)
               ORDER BY feed_rank, event_id"""
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        raise ValueError(f"routing run for {day} has no positively routed Events")

    context_files = _context_files()
    x_publication_times = _event_x_publication_times(
        day=day,
        routing_meta=meta,
    )
    artifact_disclosures = _event_artifact_disclosures(
        day=day,
        artifact_db=_resolve_path(str(meta["source_artifact_db"])),
        event_ids={str(row["event_id"]) for row in rows},
    )
    identity = {
        "schema_version": WORKSPACE_SCHEMA_VERSION,
        "day": day,
        "routing_run_id": str(meta["run_id"]),
        "cohort_sha256": str(meta["cohort_sha256"]),
        "context_files": context_files,
        "source_window_policy": freshness.POLICY_VERSION,
    }
    run_id = f"daily-intelligence-{day}-{_sha256(_canonical_json(identity))[:12]}"
    workspace = workspace_root / run_id
    event_payloads: list[dict[str, Any]] = []
    event_index: list[dict[str, Any]] = []
    artifact_events: dict[str, list[dict[str, Any]]] = {}
    audience_counts = {audience: 0 for audience in editorial.AUDIENCES}
    candidate_pair_count = 0
    stale_event_count = 0
    stale_x_source_count = 0
    for row in rows:
        packet = json.loads(str(row["packet_json"]))
        if not isinstance(packet, dict):
            raise ValueError(f"routing packet is not an object: {row['event_id']}")
        event_id = str(row["event_id"])
        packet, source_window = freshness.prune_packet_payload(
            packet,
            evaluation_day=day,
            published_at_by_source_id=x_publication_times.get(event_id, {}),
            artifact_disclosures_by_id=artifact_disclosures.get(event_id, {}),
        )
        stale_x_source_count += int(source_window["stale_x_source_count"])
        if packet is None:
            stale_event_count += 1
            continue
        audiences = [
            audience
            for audience in editorial.AUDIENCES
            if int(row[f"{audience}_relevant"] or 0) == 1
        ]
        for audience in audiences:
            audience_counts[audience] += 1
        candidate_pair_count += len(audiences)
        root = _root_source(packet)
        source_urls, artifacts = _source_index(packet)
        source_dates = {
            str(source["url"]): str(source["posted"])[:10]
            for source in packet.get("sources", [])
            if isinstance(source, dict)
            and source.get("source_type") == "x_post"
            and source.get("url")
            and source.get("posted")
        }
        packet_was_pruned = int(source_window["stale_x_source_count"]) > 0
        prior_items = (
            {}
            if packet_was_pruned
            else {
                audience: prior[(event_id, audience)]
                for audience in audiences
                if (event_id, audience) in prior
                and str(prior[(event_id, audience)]["input_sha256"])
                == str(row["input_sha256"])
            }
        )
        event_payload = {
            "event_id": event_id,
            "day": day,
            "feed_rank": int(row["feed_rank"]),
            "root_url": str(root.get("url") or row["root_url"]),
            "semantic_snapshot_sha256": str(row["semantic_snapshot_sha256"]),
            "evidence_sha256": str(row["evidence_sha256"]),
            "input_sha256": str(row["input_sha256"]),
            "audiences": audiences,
            "routing": {
                audience: {
                    "relevant": True,
                    "reason": (
                        "Positive route inherited from the original packet; "
                        "re-evaluate against the retained seven-day evidence."
                        if packet_was_pruned
                        else str(row[f"{audience}_reason"])
                    ),
                }
                for audience in audiences
            },
            "packet": packet,
            "source_window": source_window,
            "prior_per_event_insights": prior_items,
        }
        event_payloads.append(event_payload)
        search_text = consolidation.render_embedding_input(packet)
        event_index.append(
            {
                "event_id": event_id,
                "feed_rank": int(row["feed_rank"]),
                "audiences": audiences,
                "root_url": str(root.get("url") or row["root_url"]),
                "semantic_snapshot_sha256": str(row["semantic_snapshot_sha256"]),
                "evidence_sha256": str(row["evidence_sha256"]),
                "input_sha256": str(row["input_sha256"]),
                "root_author": str(root.get("author") or ""),
                "root_text": str(root.get("text") or ""),
                "artifacts": artifacts,
                "source_urls": source_urls,
                "source_dates": source_dates,
                "source_window": source_window,
                "search_text": search_text,
                "file": f"events/{int(row['feed_rank']):03d}-{event_id[:12]}.json",
            }
        )
        for artifact in artifacts:
            artifact_events.setdefault(str(artifact["url"]), []).append(
                {"event_id": event_id, "feed_rank": int(row["feed_rank"])}
            )

    if not event_index:
        raise ValueError(
            f"routing run for {day} has no positive Events with first-party X "
            f"evidence inside the {freshness.MAX_SOURCE_AGE_DAYS}-day window"
        )

    exact_artifact_groups = [
        {"url": url, "members": sorted(members, key=lambda item: item["feed_rank"])}
        for url, members in sorted(artifact_events.items())
        if len(members) > 1
    ]
    manifest = {
        "schema_version": WORKSPACE_SCHEMA_VERSION,
        "run_id": run_id,
        "day": day,
        "source": {
            "routing_run_id": str(meta["run_id"]),
            "routing_db": _display_path(routing_path),
            "routing_cohort_sha256": str(meta["cohort_sha256"]),
            "event_run_id": str(meta["source_event_run_id"]),
            "feed_run_id": str(meta["source_feed_run_id"]),
            "artifact_db": str(meta["source_artifact_db"]),
        },
        "counts": {
            "events": len(event_index),
            "candidate_pairs": candidate_pair_count,
            "stale_events_excluded": stale_event_count,
            "stale_x_sources_excluded": stale_x_source_count,
            **audience_counts,
        },
        "source_window": {
            "policy_version": freshness.POLICY_VERSION,
            "max_source_age_days": freshness.MAX_SOURCE_AGE_DAYS,
            "boundary": "0 <= brief_day - x_publication_day <= 7",
            "raw_evidence_retained": True,
        },
        "context_files": context_files,
        "events": event_index,
        "exact_artifact_groups": exact_artifact_groups,
        "retrieval": {
            "text_search": ".venv/bin/fli daily-intelligence search --workspace <path> --query <text>",
            "vector_index": ".venv/bin/fli daily-intelligence index --workspace <path>",
            "similar": ".venv/bin/fli daily-intelligence similar --workspace <path> --event-id <id>",
        },
    }
    manifest["manifest_sha256"] = _manifest_digest(manifest)
    result = {
        "workspace": _display_path(workspace),
        "manifest": _display_path(workspace / "manifest.json"),
        "draft_template": _display_path(workspace / "draft.template.json"),
        "run_id": run_id,
        "manifest_sha256": manifest["manifest_sha256"],
        "day": day,
        "counts": manifest["counts"],
        "exact_artifact_group_count": len(exact_artifact_groups),
        "source": manifest["source"],
        "dry_run": dry_run,
    }
    if dry_run:
        return result

    if (workspace / "manifest.json").is_file():
        existing = load_manifest(workspace)
        if existing != manifest:
            raise ValueError(f"workspace {run_id} already exists with different frozen content")
        template_path = workspace / "draft.template.json"
        template = editorial.draft_template(manifest)
        if not template_path.is_file() or _read_json(template_path) != template:
            _write_json(template_path, template)
        return {**result, "reused": True}
    workspace.mkdir(parents=True, exist_ok=True)
    for event, payload in zip(event_index, event_payloads, strict=True):
        _write_json(workspace / str(event["file"]), payload)
    _write_json(workspace / "manifest.json", manifest)
    _write_json(workspace / "draft.template.json", editorial.draft_template(manifest))
    return {**result, "reused": False}


def inspect_event(workspace: Path, event_id: str) -> dict[str, Any]:
    manifest = load_manifest(workspace)
    matches = [event for event in manifest["events"] if event["event_id"] == event_id]
    if not matches:
        raise ValueError(f"Event {event_id!r} is not in this workspace")
    event = matches[0]
    return {"workspace_run_id": manifest["run_id"], "event": _read_json(workspace / event["file"])}


def _compact_text(value: Any, *, limit: int = 280) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"


def preflight_workspace(
    workspace: Path,
    *,
    draft_path: Path | None = None,
) -> dict[str, Any]:
    """Return one read-only coverage row per routed Event/audience pair."""

    manifest = load_manifest(workspace)
    draft: dict[str, Any] | None = None
    if draft_path is not None:
        if not draft_path.is_file():
            raise FileNotFoundError(draft_path)
        loaded = _read_json(draft_path)
        if not isinstance(loaded, dict):
            raise ValueError("draft must be an object")
        if loaded.get("workspace_run_id") != manifest["run_id"]:
            raise ValueError("draft workspace_run_id does not match the workspace")
        if loaded.get("workspace_manifest_sha256") != manifest["manifest_sha256"]:
            raise ValueError(
                "draft workspace_manifest_sha256 does not match the workspace"
            )
        draft = loaded

    expected_pairs = {
        (str(event["event_id"]), str(audience))
        for event in manifest["events"]
        for audience in event["audiences"]
    }
    assignments: dict[tuple[str, str], list[dict[str, Any]]] = {}
    if draft is not None:
        insights = draft.get("insights", [])
        not_selected = draft.get("not_selected", [])
        if not isinstance(insights, list):
            raise ValueError("draft.insights must be an array")
        if not isinstance(not_selected, list):
            raise ValueError("draft.not_selected must be an array")
        for insight in insights:
            if not isinstance(insight, dict):
                raise ValueError("each draft insight must be an object")
            audience = str(insight.get("audience") or "")
            analysis = insight.get("analysis")
            entities = (
                analysis.get("affected_entities", [])
                if isinstance(analysis, dict)
                else []
            )
            affected_entities = [
                str(entity.get("name"))
                for entity in entities
                if isinstance(entity, dict) and entity.get("name")
            ]
            citation_ids = [
                str(value) for value in insight.get("citation_ids", [])
            ]
            event_links = insight.get("event_links", [])
            if not isinstance(event_links, list):
                raise ValueError("each insight.event_links must be an array")
            for link in event_links:
                if not isinstance(link, dict):
                    raise ValueError("each insight Event link must be an object")
                pair = (str(link.get("event_id") or ""), audience)
                assignments.setdefault(pair, []).append(
                    {
                        "status": "included",
                        "insight": {
                            "local_id": str(insight.get("local_id") or ""),
                            "rank": insight.get("rank"),
                            "title": str(insight.get("title") or ""),
                        },
                        "event_role": str(link.get("role") or ""),
                        "reason": str(link.get("reason") or ""),
                        "citation_ids": citation_ids,
                        "affected_entities": affected_entities,
                    }
                )
        for item in not_selected:
            if not isinstance(item, dict):
                raise ValueError("each draft not_selected item must be an object")
            pair = (
                str(item.get("event_id") or ""),
                str(item.get("audience") or ""),
            )
            assignments.setdefault(pair, []).append(
                {
                    "status": "not_selected",
                    "insight": None,
                    "event_role": None,
                    "reason": str(item.get("reason") or ""),
                    "citation_ids": [],
                    "affected_entities": [],
                }
            )

    pairs: list[dict[str, Any]] = []
    counts = {
        "events": len(manifest["events"]),
        "candidate_pairs": len(expected_pairs),
        "included": 0,
        "not_selected": 0,
        "missing": 0,
        "duplicate": 0,
        "unexpected": 0,
    }
    audience_order = {value: index for index, value in enumerate(editorial.AUDIENCES)}
    events = sorted(
        manifest["events"],
        key=lambda event: (int(event["feed_rank"]), str(event["event_id"])),
    )
    for event in events:
        event_payload = _read_json(workspace / str(event["file"]))
        for audience in sorted(
            event["audiences"], key=lambda value: audience_order[str(value)]
        ):
            pair = (str(event["event_id"]), str(audience))
            pair_assignments = assignments.get(pair, [])
            if not pair_assignments:
                status = "missing"
                selected: dict[str, Any] | None = None
            elif len(pair_assignments) > 1:
                status = "duplicate"
                selected = None
            else:
                selected = pair_assignments[0]
                status = str(selected["status"])
            counts[status] += 1
            routing = event_payload.get("routing", {}).get(audience, {})
            artifacts = [
                {
                    "artifact_id": str(artifact.get("artifact_id") or ""),
                    "title": str(artifact.get("title") or ""),
                    "url": str(artifact.get("url") or ""),
                    "disclosure_dates": sorted(
                        {
                            str(disclosure.get("published_at") or "")[:10]
                            for disclosure in artifact.get("disclosures", [])
                            if isinstance(disclosure, dict)
                            and disclosure.get("published_at")
                        }
                    ),
                }
                for artifact in event.get("artifacts", [])
                if isinstance(artifact, dict)
            ]
            pairs.append(
                {
                    "event_id": pair[0],
                    "feed_rank": int(event["feed_rank"]),
                    "audience": pair[1],
                    "root_author": str(event.get("root_author") or ""),
                    "root_text": _compact_text(event.get("root_text")),
                    "root_url": str(event.get("root_url") or ""),
                    "source_dates": dict(event.get("source_dates") or {}),
                    "routing_reason": str(routing.get("reason") or ""),
                    "artifacts": artifacts,
                    "status": status,
                    "insight": selected["insight"] if selected else None,
                    "event_role": selected["event_role"] if selected else None,
                    "reason": selected["reason"] if selected else None,
                    "citation_ids": selected["citation_ids"] if selected else [],
                    "affected_entities": (
                        selected["affected_entities"] if selected else []
                    ),
                    "assignments": pair_assignments if len(pair_assignments) > 1 else [],
                }
            )

    unexpected = []
    for pair, pair_assignments in sorted(assignments.items()):
        if pair in expected_pairs:
            continue
        unexpected.append(
            {
                "event_id": pair[0],
                "audience": pair[1],
                "assignments": pair_assignments,
            }
        )
    counts["unexpected"] = len(unexpected)
    return {
        "workspace_run_id": str(manifest["run_id"]),
        "workspace_manifest_sha256": str(manifest["manifest_sha256"]),
        "day": str(manifest["day"]),
        "draft": _display_path(draft_path) if draft_path is not None else None,
        "complete": (
            draft is not None
            and counts["missing"] == 0
            and counts["duplicate"] == 0
            and counts["unexpected"] == 0
        ),
        "counts": counts,
        "pairs": pairs,
        "unexpected": unexpected,
    }


def _terms(value: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9][a-z0-9._+-]+", value.lower()) if len(term) > 1}


def search_workspace(
    workspace: Path,
    *,
    query: str,
    audience: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    manifest = load_manifest(workspace)
    if audience is not None and audience not in editorial.AUDIENCES:
        raise ValueError(f"audience must be one of {list(editorial.AUDIENCES)}")
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    query = " ".join(query.split())
    if len(query) < 2:
        raise ValueError("query must contain at least two characters")
    query_terms = _terms(query)
    results = []
    for event in manifest["events"]:
        if audience is not None and audience not in event["audiences"]:
            continue
        text = str(event["search_text"])
        text_terms = _terms(text)
        overlap = len(query_terms & text_terms)
        phrase = query.lower() in text.lower()
        if not overlap and not phrase:
            continue
        score = round((overlap / max(len(query_terms), 1)) + (1.0 if phrase else 0.0), 6)
        results.append(
            {
                "event_id": event["event_id"],
                "feed_rank": event["feed_rank"],
                "audiences": event["audiences"],
                "root_url": event["root_url"],
                "root_author": event["root_author"],
                "root_text": event["root_text"],
                "artifacts": event["artifacts"],
                "score": score,
            }
        )
    results.sort(key=lambda item: (-item["score"], item["feed_rank"], item["event_id"]))
    return {
        "workspace_run_id": manifest["run_id"],
        "query": query,
        "audience": audience,
        "match_count": len(results),
        "items": results[:limit],
    }


def _embedding_rows(workspace: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for event in manifest["events"]:
        payload = _read_json(workspace / event["file"])
        text = consolidation.render_embedding_input(payload["packet"])
        if not text:
            raise ValueError(f"Event {event['event_id']} has no embeddable text")
        rows.append(
            {
                "event_id": str(event["event_id"]),
                "feed_rank": int(event["feed_rank"]),
                "input_text": text,
                "input_sha256": _sha256(text),
                "artifact_urls": [str(item["url"]) for item in event["artifacts"]],
            }
        )
    return rows


def index_workspace(
    workspace: Path,
    *,
    db_path: Path = DEFAULT_DB,
    model: str = DEFAULT_MODEL,
    client_factory: Callable[[], Any],
    timeout_seconds: float = 180.0,
) -> dict[str, Any]:
    manifest = load_manifest(workspace)
    if timeout_seconds <= 0:
        raise ValueError("timeout must be positive")
    rows = _embedding_rows(workspace, manifest)
    conn = connect(db_path)
    try:
        missing = []
        for row in rows:
            stored = conn.execute(
                """SELECT 1 FROM event_embedding
                   WHERE event_id = ? AND model = ? AND input_contract = ? AND input_sha256 = ?""",
                (row["event_id"], model, consolidation.INPUT_CONTRACT, row["input_sha256"]),
            ).fetchone()
            if stored is None:
                missing.append(row)
        usage = {"input_tokens": 0, "reported_cost_usd": 0.0, "request_count": 0}
        if missing:
            client = client_factory()
            if hasattr(client, "with_options"):
                client = client.with_options(max_retries=0, timeout=timeout_seconds)
            vectors, usage = consolidation._embed(
                client,
                missing,
                model=model,
                tags=(
                    "app:frontier-lab-intelligence",
                    "pipeline:daily-intelligence",
                    "job:event-index",
                    f"scope:{manifest['day']}",
                    f"prompt:{consolidation.INPUT_CONTRACT}",
                    f"run:{manifest['run_id']}",
                ),
            )
            now = _now()
            with conn:
                for row in missing:
                    vector = vectors[row["event_id"]]
                    conn.execute(
                        """INSERT INTO event_embedding (
                               event_id, model, input_contract, input_sha256,
                               dimensions, vector_f32, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            row["event_id"],
                            model,
                            consolidation.INPUT_CONTRACT,
                            row["input_sha256"],
                            int(vector.size),
                            vector.astype(np.float32, copy=False).tobytes(),
                            now,
                        ),
                    )
        return {
            "workspace_run_id": manifest["run_id"],
            "db": _display_path(db_path),
            "model": model,
            "input_contract": consolidation.INPUT_CONTRACT,
            "event_count": len(rows),
            "indexed_count": len(missing),
            "reused_count": len(rows) - len(missing),
            "input_tokens": int(usage.get("input_tokens") or 0),
            "reported_cost_usd": usage.get("reported_cost_usd"),
            "request_count": int(usage.get("request_count") or 0),
            "will_call_model": bool(missing),
        }
    finally:
        conn.close()


def similar_events(
    workspace: Path,
    *,
    event_id: str,
    db_path: Path = DEFAULT_DB,
    model: str = DEFAULT_MODEL,
    limit: int = 10,
    min_score: float = 0.0,
) -> dict[str, Any]:
    manifest = load_manifest(workspace)
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    if not -1 <= min_score <= 1:
        raise ValueError("min_score must be between -1 and 1")
    rows = _embedding_rows(workspace, manifest)
    by_id = {row["event_id"]: row for row in rows}
    if event_id not in by_id:
        raise ValueError(f"Event {event_id!r} is not in this workspace")
    if not db_path.is_file():
        raise ValueError("embedding index is missing; run daily-intelligence index first")
    conn = _open_readonly(db_path)
    try:
        vectors: dict[str, np.ndarray] = {}
        for row in rows:
            stored = conn.execute(
                """SELECT dimensions, vector_f32 FROM event_embedding
                   WHERE event_id = ? AND model = ? AND input_contract = ? AND input_sha256 = ?""",
                (row["event_id"], model, consolidation.INPUT_CONTRACT, row["input_sha256"]),
            ).fetchone()
            if stored is None:
                continue
            vector = np.frombuffer(stored["vector_f32"], dtype=np.float32).copy()
            if vector.size == int(stored["dimensions"]):
                vectors[row["event_id"]] = vector
    finally:
        conn.close()
    if event_id not in vectors:
        raise ValueError("seed Event is not indexed for this model; run daily-intelligence index first")
    seed = vectors[event_id]
    seed_artifacts = set(by_id[event_id]["artifact_urls"])
    items = []
    for candidate_id, vector in vectors.items():
        if candidate_id == event_id:
            continue
        score = float(seed @ vector)
        if score < min_score:
            continue
        row = by_id[candidate_id]
        items.append(
            {
                "event_id": candidate_id,
                "feed_rank": row["feed_rank"],
                "cosine_similarity": round(score, 6),
                "shared_artifact_urls": sorted(seed_artifacts & set(row["artifact_urls"])),
            }
        )
    items.sort(key=lambda item: (-item["cosine_similarity"], item["feed_rank"], item["event_id"]))
    return {
        "workspace_run_id": manifest["run_id"],
        "event_id": event_id,
        "model": model,
        "indexed_event_count": len(vectors),
        "items": items[:limit],
    }


def validate_result(workspace: Path, draft_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = load_manifest(workspace)
    if not draft_path.is_file():
        raise FileNotFoundError(draft_path)
    draft = _read_json(draft_path)
    normalized, report = editorial.validate_draft(draft, manifest)
    event_payloads = {
        str(event["event_id"]): _read_json(workspace / str(event["file"]))
        for event in manifest["events"]
    }
    for citation in normalized["citations"]:
        if citation["kind"] != "artifact":
            continue
        event_id = str(citation["event_id"])
        artifact_id = str(citation["artifact_id"])
        sources = event_payloads[event_id]["packet"].get("sources", [])
        matches = [
            source
            for source in sources
            if isinstance(source, dict)
            and source.get("source_type") == "artifact"
            and str(source.get("source_id") or "") == artifact_id
            and str(source.get("url") or "") == citation["url"]
        ]
        if len(matches) != 1:
            raise ValueError(
                f"citation {citation['local_id']!r} must identify one exact frozen "
                f"artifact for Event {event_id}"
            )
        artifact_text = " ".join(str(matches[0].get("text") or "").split())
        excerpt = " ".join(str(citation["excerpt"] or "").split())
        if excerpt.casefold() not in artifact_text.casefold():
            raise ValueError(
                f"citation {citation['local_id']!r} excerpt does not occur in the "
                "frozen artifact text"
            )
    result_sha256 = _sha256(_canonical_json(normalized))
    return normalized, report, {"result_sha256": result_sha256, "manifest": manifest}


def _derived_id(*values: str) -> str:
    return hashlib.sha256("|".join(values).encode()).hexdigest()


def _insight_ids_for_import(
    conn: sqlite3.Connection,
    *,
    day: str,
    insights: list[dict[str, Any]],
) -> dict[str, str]:
    """Keep same-day Insight permalinks stable across editorial revisions."""
    previous_by_key: dict[tuple[str, str], str] = {}
    rows = conn.execute(
        """SELECT insight.audience, insight.local_id, insight.insight_id
           FROM editorial_run AS run
           JOIN editorial_insight AS insight ON insight.run_id = run.run_id
           WHERE run.day = ? AND run.status = 'complete'
           ORDER BY run.created_at DESC, run.rowid DESC""",
        (day,),
    ).fetchall()
    for row in rows:
        previous_by_key.setdefault(
            (str(row["audience"]), str(row["local_id"])),
            str(row["insight_id"]),
        )
    return {
        str(insight["local_id"]): previous_by_key.get(
            (str(insight["audience"]), str(insight["local_id"])),
            _derived_id(day, str(insight["audience"]), str(insight["local_id"])),
        )
        for insight in insights
    }


def import_result(
    workspace: Path,
    draft_path: Path,
    *,
    db_path: Path = DEFAULT_DB,
    dry_run: bool = False,
) -> dict[str, Any]:
    normalized, report, context = validate_result(workspace, draft_path)
    manifest = context["manifest"]
    result_sha256 = context["result_sha256"]
    run_id = f"daily-brief-{manifest['day']}-{result_sha256[:16]}"
    base = {
        "run_id": run_id,
        "day": manifest["day"],
        "db": _display_path(db_path),
        "workspace": _display_path(workspace),
        "draft": _display_path(draft_path),
        "result_sha256": result_sha256,
        "report": report,
        "dry_run": dry_run,
    }
    if dry_run:
        return {**base, "reused": False}
    conn = connect(db_path)
    try:
        existing = conn.execute("SELECT result_sha256 FROM editorial_run WHERE run_id = ?", (run_id,)).fetchone()
        if existing is not None:
            if str(existing["result_sha256"]) != result_sha256:
                raise ValueError(f"editorial run {run_id} already contains a different result")
            return {**base, "reused": True, "run": run_payload(conn, run_id)}
        now = _now()
        source = manifest["source"]
        events = {event["event_id"]: event for event in manifest["events"]}
        event_payloads = {
            event_id: _read_json(workspace / event["file"])
            for event_id, event in events.items()
        }
        insight_ids = _insight_ids_for_import(
            conn,
            day=str(manifest["day"]),
            insights=normalized["insights"],
        )
        citation_ids = {
            citation["local_id"]: _derived_id(run_id, "citation", citation["local_id"])
            for citation in normalized["citations"]
        }
        with conn:
            conn.execute(
                """INSERT INTO editorial_run (
                       run_id, schema_version, draft_schema_version, day,
                       workspace_run_id, workspace_manifest_sha256,
                       source_routing_run_id, source_routing_db,
                       source_cohort_sha256, source_event_run_id,
                       source_feed_run_id, skill_version, executor_model,
                       executor_notes, result_sha256, result_json,
                       candidate_count, candidate_pair_count, insight_count,
                       citation_count, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'complete', ?)""",
                (
                    run_id,
                    STORE_SCHEMA_VERSION,
                    editorial.DRAFT_SCHEMA_VERSION,
                    manifest["day"],
                    manifest["run_id"],
                    manifest["manifest_sha256"],
                    source["routing_run_id"],
                    source["routing_db"],
                    source["routing_cohort_sha256"],
                    source["event_run_id"],
                    source["feed_run_id"],
                    normalized["agent"]["skill_version"],
                    normalized["agent"]["model"],
                    normalized["agent"]["notes"],
                    result_sha256,
                    _canonical_json(normalized),
                    report["event_count"],
                    report["candidate_pair_count"],
                    report["insight_count"],
                    report["citation_count"],
                    now,
                ),
            )
            for event_id, event in events.items():
                payload = event_payloads[event_id]
                routing = payload["routing"]
                conn.execute(
                    """INSERT INTO editorial_candidate (
                           run_id, event_id, feed_rank, root_url,
                           semantic_snapshot_sha256, evidence_sha256, input_sha256,
                           packet_json, ai_engineering_relevant,
                           ai_engineering_reason, investment_relevant,
                           investment_reason)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        event_id,
                        event["feed_rank"],
                        event["root_url"],
                        event["semantic_snapshot_sha256"],
                        event["evidence_sha256"],
                        event["input_sha256"],
                        _canonical_json(payload["packet"]),
                        int("ai_engineering" in event["audiences"]),
                        str(routing.get("ai_engineering", {}).get("reason") or "Not routed for this audience."),
                        int("investment" in event["audiences"]),
                        str(routing.get("investment", {}).get("reason") or "Not routed for this audience."),
                    ),
                )
            for insight in normalized["insights"]:
                insight_id = insight_ids[insight["local_id"]]
                conn.execute(
                    """INSERT INTO editorial_insight (
                           run_id, insight_id, local_id, audience, display_rank,
                           rank_rationale, title, what_changed, interpretation,
                           next_step, analysis_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        insight_id,
                        insight["local_id"],
                        insight["audience"],
                        insight["rank"],
                        insight["rank_rationale"],
                        insight["title"],
                        insight["what_changed"],
                        insight["interpretation"],
                        insight["next_step"],
                        _canonical_json(insight["analysis"]),
                    ),
                )
                for link in insight["event_links"]:
                    conn.execute(
                        """INSERT INTO editorial_insight_event
                           (run_id, insight_id, event_id, role, reason)
                           VALUES (?, ?, ?, ?, ?)""",
                        (run_id, insight_id, link["event_id"], link["role"], link["reason"]),
                    )
                    conn.execute(
                        """INSERT INTO editorial_event_disposition
                           (run_id, event_id, audience, status, insight_id, reason)
                           VALUES (?, ?, ?, 'included', ?, ?)""",
                        (run_id, link["event_id"], insight["audience"], insight_id, link["reason"]),
                    )
            for item in normalized["not_selected"]:
                conn.execute(
                    """INSERT INTO editorial_event_disposition
                       (run_id, event_id, audience, status, insight_id, reason)
                       VALUES (?, ?, ?, 'not_selected', NULL, ?)""",
                    (run_id, item["event_id"], item["audience"], item["reason"]),
                )
            for citation in normalized["citations"]:
                citation_id = citation_ids[citation["local_id"]]
                source_identity = citation["excerpt"] or citation["url"]
                conn.execute(
                    """INSERT INTO editorial_citation (
                           run_id, citation_id, local_id, kind, url, title,
                           event_id, artifact_id, published_at, retrieved_at,
                           supports, excerpt, source_sha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        citation_id,
                        citation["local_id"],
                        citation["kind"],
                        citation["url"],
                        citation["title"],
                        citation["event_id"],
                        citation["artifact_id"],
                        citation["published_at"],
                        citation["retrieved_at"],
                        citation["supports"],
                        citation["excerpt"],
                        _sha256(source_identity),
                    ),
                )
            for insight in normalized["insights"]:
                insight_id = insight_ids[insight["local_id"]]
                for ordinal, local_citation_id in enumerate(insight["citation_ids"], start=1):
                    conn.execute(
                        """INSERT INTO editorial_insight_citation
                           (run_id, insight_id, citation_id, ordinal)
                           VALUES (?, ?, ?, ?)""",
                        (run_id, insight_id, citation_ids[local_citation_id], ordinal),
                    )
        return {**base, "reused": False, "run": run_payload(conn, run_id)}
    finally:
        conn.close()


def run_payload(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    run = conn.execute(
        """SELECT run_id, schema_version, draft_schema_version, day,
                  workspace_run_id, workspace_manifest_sha256,
                  source_routing_run_id, source_routing_db,
                  source_cohort_sha256, source_event_run_id,
                  source_feed_run_id, skill_version, executor_model,
                  executor_notes, result_sha256, candidate_count,
                  candidate_pair_count, insight_count, citation_count,
                  status, created_at
           FROM editorial_run WHERE run_id = ?""",
        (run_id,),
    ).fetchone()
    if run is None:
        raise ValueError(f"editorial run {run_id!r} does not exist")
    insights = conn.execute(
        """SELECT insight_id, local_id, audience, display_rank, rank_rationale, title,
                  what_changed, interpretation, next_step, analysis_json
           FROM editorial_insight WHERE run_id = ?
           ORDER BY audience, display_rank""",
        (run_id,),
    ).fetchall()
    items = []
    for row in insights:
        item = dict(row)
        item["analysis"] = json.loads(str(item.pop("analysis_json")))
        item["events"] = [
            dict(value)
            for value in conn.execute(
                """SELECT link.event_id, candidate.feed_rank, link.role, link.reason,
                          candidate.root_url
                   FROM editorial_insight_event AS link
                   JOIN editorial_candidate AS candidate
                     ON candidate.run_id = link.run_id AND candidate.event_id = link.event_id
                   WHERE link.run_id = ? AND link.insight_id = ?
                   ORDER BY candidate.feed_rank""",
                (run_id, row["insight_id"]),
            ).fetchall()
        ]
        item["citations"] = [
            dict(value)
            for value in conn.execute(
                """SELECT citation.citation_id, citation.local_id,
                          citation.kind, citation.url, citation.title,
                          citation.event_id, citation.artifact_id,
                          citation.published_at, citation.retrieved_at,
                          citation.supports, citation.excerpt
                   FROM editorial_insight_citation AS link
                   JOIN editorial_citation AS citation
                     ON citation.run_id = link.run_id AND citation.citation_id = link.citation_id
                   WHERE link.run_id = ? AND link.insight_id = ?
                   ORDER BY link.ordinal""",
                (run_id, row["insight_id"]),
            ).fetchall()
        ]
        items.append(item)
    dispositions = conn.execute(
        """SELECT audience, status, COUNT(*) AS count
           FROM editorial_event_disposition WHERE run_id = ?
           GROUP BY audience, status ORDER BY audience, status""",
        (run_id,),
    ).fetchall()
    return {
        **dict(run),
        "insights": items,
        "dispositions": [dict(row) for row in dispositions],
    }


RUN_PROJECTIONS = ("full", "summary", "insights", "citations", "dispositions")


def _run_projection_base(payload: dict[str, Any]) -> dict[str, Any]:
    disposition_counts: dict[str, int] = {}
    for row in payload["dispositions"]:
        status = str(row["status"])
        disposition_counts[status] = (
            disposition_counts.get(status, 0) + int(row["count"])
        )
    return {
        "run_id": str(payload["run_id"]),
        "day": str(payload["day"]),
        "status": str(payload["status"]),
        "created_at": str(payload["created_at"]),
        "schema_version": str(payload["schema_version"]),
        "draft_schema_version": str(payload["draft_schema_version"]),
        "workspace": {
            "run_id": str(payload["workspace_run_id"]),
            "manifest_sha256": str(payload["workspace_manifest_sha256"]),
        },
        "source": {
            "routing_run_id": str(payload["source_routing_run_id"]),
            "cohort_sha256": str(payload["source_cohort_sha256"]),
            "event_run_id": str(payload["source_event_run_id"]),
            "feed_run_id": str(payload["source_feed_run_id"]),
        },
        "agent": {
            "skill_version": str(payload["skill_version"]),
            "model": str(payload["executor_model"]),
        },
        "result_sha256": str(payload["result_sha256"]),
        "counts": {
            "candidate_events": int(payload["candidate_count"]),
            "candidate_pairs": int(payload["candidate_pair_count"]),
            "insights": int(payload["insight_count"]),
            "citations": int(payload["citation_count"]),
            "included": disposition_counts.get("included", 0),
            "not_selected": disposition_counts.get("not_selected", 0),
        },
    }


def run_projection(
    conn: sqlite3.Connection,
    run_id: str,
    *,
    projection: str = "full",
) -> dict[str, Any]:
    """Return one additive, bounded projection of a durable editorial run."""

    if projection not in RUN_PROJECTIONS:
        raise ValueError(f"projection must be one of {list(RUN_PROJECTIONS)}")
    payload = run_payload(conn, run_id)
    if projection == "full":
        return payload
    result = _run_projection_base(payload)
    if projection == "summary":
        return result
    if projection == "insights":
        result["insights"] = [
            {
                "insight_id": str(insight["insight_id"]),
                "local_id": str(insight["local_id"]),
                "audience": str(insight["audience"]),
                "display_rank": int(insight["display_rank"]),
                "title": str(insight["title"]),
                "event_ids": [str(event["event_id"]) for event in insight["events"]],
                "citation_ids": [
                    str(citation["citation_id"])
                    for citation in insight["citations"]
                ],
            }
            for insight in payload["insights"]
        ]
        return result
    if projection == "citations":
        citations: dict[str, dict[str, Any]] = {}
        for insight in payload["insights"]:
            for citation in insight["citations"]:
                citations.setdefault(str(citation["citation_id"]), dict(citation))
        result["citations"] = sorted(
            citations.values(),
            key=lambda citation: (
                str(citation["local_id"]),
                str(citation["citation_id"]),
            ),
        )
        return result

    rows = conn.execute(
        """SELECT disposition.event_id, candidate.feed_rank,
                  disposition.audience, disposition.status,
                  disposition.insight_id, insight.local_id,
                  insight.display_rank, insight.title, disposition.reason
           FROM editorial_event_disposition AS disposition
           JOIN editorial_candidate AS candidate
             ON candidate.run_id = disposition.run_id
            AND candidate.event_id = disposition.event_id
           LEFT JOIN editorial_insight AS insight
             ON insight.run_id = disposition.run_id
            AND insight.insight_id = disposition.insight_id
           WHERE disposition.run_id = ?
           ORDER BY candidate.feed_rank, disposition.audience""",
        (run_id,),
    ).fetchall()
    result["dispositions"] = [dict(row) for row in rows]
    return result


@lru_cache(maxsize=128)
def _current_editorial_lineage_cached(
    *,
    day: str,
    source_routing_db: str,
    source_routing_run_id: str,
    source_cohort_sha256: str,
    source_event_run_id: str,
    source_feed_run_id: str,
    source_token: tuple[tuple[str, int, int, int, int], ...],
) -> tuple[str, str] | None:
    """Validate one immutable editorial lineage once per exact source state."""
    del source_token
    try:
        source_routing_path = _resolve_path(source_routing_db)
        current_path, routing_meta, rank_identity = _current_routing_lineage(
            day,
            source_routing_path.parent.parent,
        )
        exact_matches = (
            current_path.resolve() == source_routing_path.resolve(),
            source_routing_run_id == str(routing_meta["run_id"]),
            source_cohort_sha256 == str(routing_meta["cohort_sha256"]),
            source_event_run_id == rank_identity["event_run_id"],
            source_feed_run_id == rank_identity["feed_run_id"],
            str(routing_meta["rank_version"]) == rank_identity["rank_version"],
            str(routing_meta["source_rank_input_sha256"])
            == rank_identity["rank_input_sha256"],
        )
    except (FileNotFoundError, KeyError, OSError, sqlite3.Error, ValueError):
        return None
    if not all(exact_matches):
        return None
    return rank_identity["rank_version"], rank_identity["rank_input_sha256"]


def _current_editorial_lineage(
    row: sqlite3.Row,
    *,
    source_token: tuple[tuple[str, int, int, int, int], ...] | None = None,
) -> dict[str, str] | None:
    """Return authoritative source lineage only when an editorial is current."""
    source_routing_path = _resolve_path(str(row["source_routing_db"]))
    token = (
        source_token
        if source_token is not None
        else _editorial_lineage_source_token(source_routing_path.parent.parent)
    )
    lineage = _current_editorial_lineage_cached(
        day=str(row["day"]),
        source_routing_db=str(source_routing_path),
        source_routing_run_id=str(row["source_routing_run_id"]),
        source_cohort_sha256=str(row["source_cohort_sha256"]),
        source_event_run_id=str(row["source_event_run_id"]),
        source_feed_run_id=str(row["source_feed_run_id"]),
        source_token=token,
    )
    if lineage is None:
        return None
    return {
        "rank_version": lineage[0],
        "rank_input_sha256": lineage[1],
    }


def _current_editorial_rows(
    conn: sqlite3.Connection,
    *,
    day: str | None = None,
) -> list[tuple[sqlite3.Row, dict[str, str]]]:
    parameters: tuple[str, ...] = ()
    day_filter = ""
    if day is not None:
        day_filter = " AND day = ?"
        parameters = (day,)
    rows = conn.execute(
        f"""SELECT rowid AS import_ordinal, run_id, day, created_at,
                   candidate_count, candidate_pair_count,
                   source_routing_run_id, source_routing_db,
                   source_cohort_sha256, source_event_run_id,
                   source_feed_run_id
            FROM editorial_run
            WHERE status = 'complete'{day_filter}
            ORDER BY day DESC, created_at DESC, rowid DESC""",
        parameters,
    ).fetchall()
    current: list[tuple[sqlite3.Row, dict[str, str]]] = []
    selected_days: set[str] = set()
    source_tokens: dict[Path, tuple[tuple[str, int, int, int, int], ...]] = {}
    for row in rows:
        selected_day = str(row["day"])
        if selected_day in selected_days:
            continue
        source_routing_path = _resolve_path(str(row["source_routing_db"]))
        routing_root = source_routing_path.parent.parent
        source_token = source_tokens.get(routing_root)
        if source_token is None:
            source_token = _editorial_lineage_source_token(routing_root)
            source_tokens[routing_root] = source_token
        lineage = _current_editorial_lineage(row, source_token=source_token)
        if lineage is None:
            continue
        current.append((row, lineage))
        selected_days.add(selected_day)
    return current


def editorial_insights_payload(
    *,
    audience: str = "investment",
    day: str | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return one audience from the latest complete imported run for a day.

    A complete run supersedes older runs for the same day even when it selects
    no Insights for the requested audience. The function never creates the
    editorial database while serving a read.
    """
    if audience not in editorial.AUDIENCES:
        raise ValueError(f"audience must be one of {list(editorial.AUDIENCES)}")
    path = DEFAULT_DB if db_path is None else _resolve_path(db_path)

    def unavailable(reason: str) -> dict[str, Any]:
        return {
            "schema_version": READ_SCHEMA_VERSION,
            "content_kind": "daily_editorial",
            "available": False,
            "reason": reason,
            "status": "kept",
            "requested_date": day,
            "date": day,
            "audience": audience,
            "portfolio_reference": (
                portfolio_reference_payload() if audience == "investment" else None
            ),
            "run": None,
            "items": [],
            "declined": [],
        }

    if not path.is_file():
        return unavailable("No complete daily editorial run has been imported.")

    conn = _open_readonly(path)
    try:
        table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'editorial_run'"
        ).fetchone()
        if table is None:
            return unavailable("No complete daily editorial run has been imported.")
        current_rows = _current_editorial_rows(conn, day=day)
        if not current_rows:
            scope = f" for {day}" if day is not None else ""
            return unavailable(
                f"No current complete daily editorial run is available{scope}."
            )
        selected, current_lineage = current_rows[0]

        payload = run_payload(conn, str(selected["run_id"]))
        items = []
        for stored in payload["insights"]:
            if stored["audience"] != audience:
                continue
            item = dict(stored)
            item["rank"] = int(item.pop("display_rank"))
            item["day"] = str(payload["day"])
            item["events"] = [
                {key: value for key, value in event.items() if key != "root_url"}
                for event in item["events"]
            ]
            items.append(item)

        declined = []
        declined_rows = conn.execute(
            """SELECT disposition.event_id, disposition.reason,
                      candidate.feed_rank, candidate.packet_json
               FROM editorial_event_disposition AS disposition
               JOIN editorial_candidate AS candidate
                 ON candidate.run_id = disposition.run_id
                AND candidate.event_id = disposition.event_id
               WHERE disposition.run_id = ?
                 AND disposition.audience = ?
                 AND disposition.status = 'not_selected'
               ORDER BY candidate.feed_rank""",
            (str(selected["run_id"]), audience),
        ).fetchall()
        for row in declined_rows:
            packet = json.loads(str(row["packet_json"]))
            root = next(
                (
                    source
                    for source in packet.get("sources", [])
                    if source.get("relation") == "root"
                ),
                None,
            )
            excerpt = ""
            if root:
                without_links = re.sub(r"https?://\S+", "", str(root.get("text", "")))
                excerpt = " ".join(without_links.split())
            if len(excerpt) > 220:
                excerpt = excerpt[:220].rstrip() + "…"
            declined.append(
                {
                    "event_id": str(row["event_id"]),
                    "feed_rank": int(row["feed_rank"]),
                    "author": str(root.get("author", "")) if root else "",
                    "excerpt": excerpt,
                    "reason": str(row["reason"]),
                }
            )

        disposition_counts = {
            str(row["status"]): int(row["count"])
            for row in payload["dispositions"]
            if row["audience"] == audience
        }
        run = {
            "run_id": payload["run_id"],
            "date": payload["day"],
            "status": payload["status"],
            "created_at": payload["created_at"],
            "schema_version": payload["schema_version"],
            "draft_schema_version": payload["draft_schema_version"],
            "workspace": {
                "run_id": payload["workspace_run_id"],
                "manifest_sha256": payload["workspace_manifest_sha256"],
            },
            "source": {
                "routing_run_id": payload["source_routing_run_id"],
                "cohort_sha256": payload["source_cohort_sha256"],
                "event_run_id": payload["source_event_run_id"],
                "feed_run_id": payload["source_feed_run_id"],
                "rank_version": current_lineage["rank_version"],
                "rank_input_sha256": current_lineage["rank_input_sha256"],
            },
            "agent": {
                "skill_version": payload["skill_version"],
                "model": payload["executor_model"],
                "notes": payload["executor_notes"],
            },
            "result_sha256": payload["result_sha256"],
            "counts": {
                "candidate_events": int(payload["candidate_count"]),
                "candidate_pairs": int(payload["candidate_pair_count"]),
                "insights_all_audiences": int(payload["insight_count"]),
                "citations_all_audiences": int(payload["citation_count"]),
                "insights": len(items),
                "included_candidates": disposition_counts.get("included", 0),
                "not_selected_candidates": disposition_counts.get("not_selected", 0),
            },
        }
        reason = None
        if not items:
            label = "Investment" if audience == "investment" else "AI Engineering"
            reason = f"The complete daily editorial run selected no {label} Insights."
        return {
            "schema_version": READ_SCHEMA_VERSION,
            "content_kind": "daily_editorial",
            "available": True,
            "reason": reason,
            "status": "kept",
            "requested_date": day,
            "date": str(payload["day"]),
            "audience": audience,
            "portfolio_reference": (
                portfolio_reference_payload() if audience == "investment" else None
            ),
            "run": run,
            "items": items,
            "declined": declined,
        }
    finally:
        conn.close()


def editorial_insight_dates_payload(
    *,
    audience: str = "investment",
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return canonical Insight counts from the latest complete run per day."""
    if audience not in editorial.AUDIENCES:
        raise ValueError(f"audience must be one of {list(editorial.AUDIENCES)}")
    path = DEFAULT_DB if db_path is None else _resolve_path(db_path)
    empty = {
        "schema_version": READ_SCHEMA_VERSION,
        "available": False,
        "reason": "No complete daily editorial run has been imported.",
        "audience": audience,
        "latest_date": None,
        "dates": [],
    }
    if not path.is_file():
        return empty
    conn = _open_readonly(path)
    try:
        table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'editorial_run'"
        ).fetchone()
        if table is None:
            return empty
        rows = _current_editorial_rows(conn)
        run_ids = [str(row["run_id"]) for row, _lineage in rows]
        insight_counts: dict[str, int] = {}
        disposition_counts: dict[str, dict[str, int]] = {}
        if run_ids:
            placeholders = ",".join("?" for _ in run_ids)
            insight_counts = {
                str(value["run_id"]): int(value["count"])
                for value in conn.execute(
                    f"""SELECT run_id, COUNT(*) AS count
                        FROM editorial_insight
                        WHERE audience = ?
                          AND run_id IN ({placeholders})
                        GROUP BY run_id""",
                    (audience, *run_ids),
                ).fetchall()
            }
            for value in conn.execute(
                f"""SELECT run_id, status, COUNT(*) AS count
                    FROM editorial_event_disposition
                    WHERE audience = ?
                      AND run_id IN ({placeholders})
                    GROUP BY run_id, status""",
                (audience, *run_ids),
            ).fetchall():
                disposition_counts.setdefault(str(value["run_id"]), {})[
                    str(value["status"])
                ] = int(value["count"])
        dates = []
        for row, _lineage in sorted(rows, key=lambda item: str(item[0]["day"])):
            selected_day = str(row["day"])
            run_id = str(row["run_id"])
            insight_count = insight_counts.get(run_id, 0)
            dispositions = disposition_counts.get(run_id, {})
            dates.append(
                {
                    "day": selected_day,
                    "item_count": insight_count,
                    "candidate_count": sum(dispositions.values()),
                    "included_candidate_count": dispositions.get("included", 0),
                    "not_selected_candidate_count": dispositions.get("not_selected", 0),
                    "run_id": str(row["run_id"]),
                    "created_at": str(row["created_at"]),
                }
            )
        return {
            "schema_version": READ_SCHEMA_VERSION,
            "available": bool(dates),
            "reason": None if dates else empty["reason"],
            "audience": audience,
            "latest_date": dates[-1]["day"] if dates else None,
            "dates": dates,
        }
    finally:
        conn.close()


def warm_editorial_read_views() -> dict[str, Any]:
    """Warm current date-lineage validation without blocking static responses."""
    payloads = [
        editorial_insight_dates_payload(audience=audience)
        for audience in editorial.AUDIENCES
    ]
    return {
        "available": any(payload["available"] for payload in payloads),
        "audiences_warmed": len(payloads),
        "days_warmed": max((len(payload["dates"]) for payload in payloads), default=0),
    }


def summary_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute(
        """SELECT COUNT(*) AS runs, COUNT(DISTINCT day) AS days,
                  COALESCE(SUM(insight_count), 0) AS insights,
                  MAX(day) AS latest_day
           FROM editorial_run"""
    ).fetchone()
    assert row is not None
    return dict(row)
