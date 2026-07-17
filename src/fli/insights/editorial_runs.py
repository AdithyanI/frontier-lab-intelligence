"""Frozen workspaces, vector retrieval, and durable daily editorial runs."""

from __future__ import annotations

from datetime import datetime, timezone
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
from fli.routing import model as routing_model
from fli.routing import runs as routing_runs


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ROOT = REPO_ROOT / "data" / "derived" / "daily-intelligence"
DEFAULT_WORKSPACE_ROOT = DEFAULT_ROOT / "workspaces"
DEFAULT_DB = DEFAULT_ROOT / "editorial.db"
DEFAULT_ROUTING_ROOT = routing_runs.DEFAULT_RUN_ROOT
DEFAULT_INSIGHTS_DB = insight_runs.DEFAULT_DB
DEFAULT_MODEL = consolidation.DEFAULT_MODEL
WORKSPACE_SCHEMA_VERSION = "daily-intelligence-workspace-v1"
STORE_SCHEMA_VERSION = "daily-intelligence-store-v3"
READ_SCHEMA_VERSION = "daily-intelligence-read-v4"

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
    snapshot_content_sha256 TEXT NOT NULL,
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


def connect(path: Path = DEFAULT_DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA foreign_keys = OFF")
    _migrate_editorial_insight_v2(conn)
    _migrate_editorial_insight_v3(conn)
    conn.executescript(SCHEMA)
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


def _current_routing_run(day: str, routing_root: Path) -> tuple[Path, dict[str, Any]]:
    try:
        published = routing_runs._published_event_source()
    except (FileNotFoundError, ValueError):
        published = None
    candidates: list[tuple[str, str, Path, dict[str, Any]]] = []
    for path in sorted(routing_root.glob("*/routing.db")):
        try:
            conn = _open_readonly(path)
            meta_row = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
            if meta_row is None:
                conn.close()
                continue
            meta = dict(meta_row)
            counts = conn.execute(
                """SELECT COUNT(*) AS total,
                          SUM(status = 'complete') AS complete,
                          MAX(COALESCE(completed_at, updated_at)) AS latest
                   FROM routing_item"""
            ).fetchone()
            conn.close()
        except (sqlite3.Error, OSError):
            continue
        if (
            str(meta["day"]) != day
            or str(meta["prompt_version"]) != routing_model.PROMPT_VERSION
            or str(meta["prompt_sha256"]) != routing_model.prompt_sha256()
            or str(meta["schema_version"]) != routing_model.SCHEMA_VERSION
            or int(counts["total"] or 0) != int(meta["expected_count"])
            or int(counts["complete"] or 0) != int(meta["expected_count"])
            or (
                published is not None
                and (
                    str(meta["source_event_run_id"]) != published["event_run_id"]
                    or str(meta["source_feed_run_id"]) != published["feed_run_id"]
                )
            )
        ):
            continue
        candidates.append(
            (
                str(counts["latest"] or meta["updated_at"]),
                str(meta["run_id"]),
                path,
                meta,
            )
        )
    if not candidates:
        raise ValueError(f"no complete current routing run found for {day}")
    _, _, path, meta = max(candidates, key=lambda item: (item[0], item[1]))
    return path, meta


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
                }
            )
    return urls, artifacts


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
    if value.get("schema_version") != "bit-investment-context-v1":
        raise ValueError("Investment context packet uses an unsupported schema version")
    return value


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
    identity = {
        "schema_version": WORKSPACE_SCHEMA_VERSION,
        "day": day,
        "routing_run_id": str(meta["run_id"]),
        "cohort_sha256": str(meta["cohort_sha256"]),
        "context_files": context_files,
    }
    run_id = f"daily-intelligence-{day}-{_sha256(_canonical_json(identity))[:12]}"
    workspace = workspace_root / run_id
    event_payloads: list[dict[str, Any]] = []
    event_index: list[dict[str, Any]] = []
    artifact_events: dict[str, list[dict[str, Any]]] = {}
    audience_counts = {audience: 0 for audience in editorial.AUDIENCES}
    candidate_pair_count = 0
    for row in rows:
        packet = json.loads(str(row["packet_json"]))
        if not isinstance(packet, dict):
            raise ValueError(f"routing packet is not an object: {row['event_id']}")
        event_id = str(row["event_id"])
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
        prior_items = {
            audience: prior[(event_id, audience)]
            for audience in audiences
            if (event_id, audience) in prior
        }
        event_payload = {
            "event_id": event_id,
            "day": day,
            "feed_rank": int(row["feed_rank"]),
            "root_url": str(row["root_url"]),
            "snapshot_content_sha256": str(row["snapshot_content_sha256"]),
            "evidence_sha256": str(row["evidence_sha256"]),
            "input_sha256": str(row["input_sha256"]),
            "audiences": audiences,
            "routing": {
                audience: {
                    "relevant": True,
                    "reason": str(row[f"{audience}_reason"]),
                }
                for audience in audiences
            },
            "packet": packet,
            "prior_per_event_insights": prior_items,
        }
        event_payloads.append(event_payload)
        search_text = consolidation.render_embedding_input(packet)
        event_index.append(
            {
                "event_id": event_id,
                "feed_rank": int(row["feed_rank"]),
                "audiences": audiences,
                "root_url": str(row["root_url"]),
                "snapshot_content_sha256": str(row["snapshot_content_sha256"]),
                "evidence_sha256": str(row["evidence_sha256"]),
                "input_sha256": str(row["input_sha256"]),
                "root_author": str(root.get("author") or ""),
                "root_text": str(root.get("text") or ""),
                "artifacts": artifacts,
                "source_urls": source_urls,
                "search_text": search_text,
                "file": f"events/{int(row['feed_rank']):03d}-{event_id[:12]}.json",
            }
        )
        for artifact in artifacts:
            artifact_events.setdefault(str(artifact["url"]), []).append(
                {"event_id": event_id, "feed_rank": int(row["feed_rank"])}
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
            **audience_counts,
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
    result_sha256 = _sha256(_canonical_json(normalized))
    return normalized, report, {"result_sha256": result_sha256, "manifest": manifest}


def _derived_id(*values: str) -> str:
    return hashlib.sha256("|".join(values).encode()).hexdigest()


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
        insight_ids = {
            insight["local_id"]: _derived_id(run_id, insight["audience"], insight["local_id"])
            for insight in normalized["insights"]
        }
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
                           snapshot_content_sha256, evidence_sha256, input_sha256,
                           packet_json, ai_engineering_relevant,
                           ai_engineering_reason, investment_relevant,
                           investment_reason)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        event_id,
                        event["feed_rank"],
                        event["root_url"],
                        event["snapshot_content_sha256"],
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
        if day is None:
            selected = conn.execute(
                """SELECT run_id FROM editorial_run
                   WHERE status = 'complete'
                   ORDER BY day DESC, created_at DESC, rowid DESC
                   LIMIT 1"""
            ).fetchone()
        else:
            selected = conn.execute(
                """SELECT run_id FROM editorial_run
                   WHERE status = 'complete' AND day = ?
                   ORDER BY created_at DESC, rowid DESC
                   LIMIT 1""",
                (day,),
            ).fetchone()
        if selected is None:
            scope = f" for {day}" if day is not None else ""
            return unavailable(f"No complete daily editorial run is available{scope}.")

        payload = run_payload(conn, str(selected["run_id"]))
        items = []
        for stored in payload["insights"]:
            if stored["audience"] != audience:
                continue
            item = dict(stored)
            item["rank"] = int(item.pop("display_rank"))
            item["day"] = str(payload["day"])
            items.append(item)

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
        rows = conn.execute(
            """SELECT rowid AS import_ordinal, run_id, day, created_at,
                      candidate_count, candidate_pair_count
               FROM editorial_run
               WHERE status = 'complete'
               ORDER BY day, created_at DESC, rowid DESC"""
        ).fetchall()
        latest_by_day: dict[str, sqlite3.Row] = {}
        for row in rows:
            latest_by_day.setdefault(str(row["day"]), row)
        dates = []
        for selected_day, row in sorted(latest_by_day.items()):
            insight_count = int(
                conn.execute(
                    """SELECT COUNT(*) FROM editorial_insight
                       WHERE run_id = ? AND audience = ?""",
                    (row["run_id"], audience),
                ).fetchone()[0]
            )
            dispositions = {
                str(value["status"]): int(value["count"])
                for value in conn.execute(
                    """SELECT status, COUNT(*) AS count
                       FROM editorial_event_disposition
                       WHERE run_id = ? AND audience = ?
                       GROUP BY status""",
                    (row["run_id"], audience),
                ).fetchall()
            }
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


def summary_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute(
        """SELECT COUNT(*) AS runs, COUNT(DISTINCT day) AS days,
                  COALESCE(SUM(insight_count), 0) AS insights,
                  MAX(day) AS latest_day
           FROM editorial_run"""
    ).fetchone()
    assert row is not None
    return dict(row)
