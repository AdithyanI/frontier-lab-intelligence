"""Recomputable rankings over one immutable outgoing-follow snapshot.

This module may read the frozen snapshot and the Registry identity tables. It
cannot read the legacy ``graph_edges`` table: a SQLite authorizer limits reads
from the attached Registry database to the exact identity tables needed for
stable-X-ID mapping. All results live in a separate derived SQLite database.
"""

from __future__ import annotations

import argparse
from array import array
import csv
import hashlib
import json
import math
import os
import sqlite3
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from fli import following_snapshots


RESULT_SCHEMA_VERSION = "1.0"
ANALYSIS_SCHEMA_VERSION = "following-analysis-v4"
OVERLAP_ALGORITHM = "entity-overlap-v3"
PAGERANK_ALGORITHM = "personalized-pagerank-v1"
PERSONALIZATION_SCHEMA_VERSION = "following-personalization-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_DB = REPO_ROOT / "data" / "fli.db"
DEFAULT_DERIVED_ROOT = REPO_ROOT / "data" / "derived" / "following"
DEFAULT_PERSONALIZATION = (
    REPO_ROOT
    / "data"
    / "following"
    / "personalizations"
    / "trusted-personalization-2026-07-11-v1.json"
)

REGISTRY_READ_TABLES = frozenset(
    {
        "accounts",
        "channels",
        "entity_channels",
        "entities",
        "entity_registry_rejections",
    }
)
SNAPSHOT_READ_TABLES = frozenset(
    {"snapshot_run", "source_fetch", "account", "edge"}
)
SQLITE_WRITE_ACTIONS = frozenset(
    {
        sqlite3.SQLITE_INSERT,
        sqlite3.SQLITE_UPDATE,
        sqlite3.SQLITE_DELETE,
        sqlite3.SQLITE_CREATE_INDEX,
        sqlite3.SQLITE_CREATE_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_INDEX,
        sqlite3.SQLITE_CREATE_TEMP_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
        sqlite3.SQLITE_CREATE_TEMP_VIEW,
        sqlite3.SQLITE_CREATE_TRIGGER,
        sqlite3.SQLITE_CREATE_VIEW,
        sqlite3.SQLITE_DROP_INDEX,
        sqlite3.SQLITE_DROP_TABLE,
        sqlite3.SQLITE_DROP_TEMP_INDEX,
        sqlite3.SQLITE_DROP_TEMP_TABLE,
        sqlite3.SQLITE_DROP_TEMP_TRIGGER,
        sqlite3.SQLITE_DROP_TEMP_VIEW,
        sqlite3.SQLITE_DROP_TRIGGER,
        sqlite3.SQLITE_DROP_VIEW,
        sqlite3.SQLITE_ALTER_TABLE,
        sqlite3.SQLITE_REINDEX,
    }
)

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS analysis_context (
    context_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL
        CHECK (schema_version = '{ANALYSIS_SCHEMA_VERSION}'),
    snapshot_id TEXT NOT NULL,
    cohort_sha256 TEXT NOT NULL,
    snapshot_db_sha256 TEXT NOT NULL,
    snapshot_checkpoint_commit TEXT NOT NULL,
    snapshot_checkpoint_db_sha256 TEXT NOT NULL,
    registry_checkpoint_commit TEXT NOT NULL,
    registry_db_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS graph_node (
    context_id TEXT NOT NULL REFERENCES analysis_context(context_id)
        ON DELETE CASCADE,
    x_id TEXT NOT NULL,
    handle TEXT NOT NULL,
    display_name TEXT,
    bio TEXT,
    followers_count INTEGER,
    registry_state TEXT NOT NULL
        CHECK (registry_state IN ('active', 'rejected', 'unknown')),
    entity_id INTEGER,
    entity_kind TEXT,
    entity_name TEXT,
    PRIMARY KEY (context_id, x_id)
);
CREATE INDEX IF NOT EXISTS idx_graph_node_state
    ON graph_node(context_id, registry_state, x_id);

CREATE TABLE IF NOT EXISTS ranking_run (
    run_id TEXT PRIMARY KEY,
    context_id TEXT NOT NULL REFERENCES analysis_context(context_id)
        ON DELETE CASCADE,
    algorithm TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    eligible_source_account_count INTEGER NOT NULL,
    eligible_source_entity_count INTEGER NOT NULL,
    eligible_edge_count INTEGER NOT NULL,
    eligible_vote_count INTEGER NOT NULL,
    ranked_node_count INTEGER NOT NULL,
    completed_at TEXT NOT NULL,
    UNIQUE (context_id, algorithm, parameters_json)
);

CREATE TABLE IF NOT EXISTS ranking_result (
    run_id TEXT NOT NULL REFERENCES ranking_run(run_id) ON DELETE CASCADE,
    x_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    score_rank INTEGER NOT NULL,
    score REAL NOT NULL,
    cohort_follow_count INTEGER NOT NULL,
    cohort_follow_share REAL NOT NULL,
    PRIMARY KEY (run_id, x_id),
    UNIQUE (run_id, position)
);
CREATE INDEX IF NOT EXISTS idx_ranking_result_order
    ON ranking_result(run_id, position);

CREATE TABLE IF NOT EXISTS entity_support_result (
    run_id TEXT NOT NULL REFERENCES ranking_run(run_id) ON DELETE CASCADE,
    entity_id INTEGER NOT NULL,
    support_rank INTEGER NOT NULL,
    support_count INTEGER NOT NULL,
    support_share REAL NOT NULL,
    channel_count INTEGER NOT NULL,
    PRIMARY KEY (run_id, entity_id)
);
CREATE INDEX IF NOT EXISTS idx_entity_support_result_order
    ON entity_support_result(run_id, support_rank, entity_id);

CREATE TABLE IF NOT EXISTS ranking_diagnostics (
    run_id TEXT PRIMARY KEY REFERENCES ranking_run(run_id) ON DELETE CASCADE,
    iterations INTEGER NOT NULL,
    final_delta REAL NOT NULL,
    score_sum REAL NOT NULL,
    converged INTEGER NOT NULL CHECK (converged IN (0, 1)),
    seed_count INTEGER NOT NULL,
    personalization_id TEXT,
    personalization_sha256 TEXT
);

CREATE TABLE IF NOT EXISTS ranking_comparison (
    overlap_run_id TEXT NOT NULL REFERENCES ranking_run(run_id) ON DELETE CASCADE,
    pagerank_run_id TEXT NOT NULL REFERENCES ranking_run(run_id) ON DELETE CASCADE,
    x_id TEXT NOT NULL,
    overlap_position INTEGER NOT NULL,
    overlap_score_rank INTEGER NOT NULL,
    cohort_follow_count INTEGER NOT NULL,
    cohort_follow_share REAL NOT NULL,
    pagerank_position INTEGER NOT NULL,
    pagerank_score_rank INTEGER NOT NULL,
    pagerank_score REAL NOT NULL,
    pagerank_position_gain INTEGER NOT NULL,
    is_personalization_seed INTEGER NOT NULL CHECK (is_personalization_seed IN (0, 1)),
    PRIMARY KEY (overlap_run_id, pagerank_run_id, x_id)
);
CREATE INDEX IF NOT EXISTS idx_ranking_comparison_pagerank
    ON ranking_comparison(pagerank_run_id, pagerank_position);
"""


@dataclass
class RankingCliError(Exception):
    code: str
    message: str
    hint: str
    exit_code: int = 1
    retryable: bool = False

    def __str__(self) -> str:
        return self.message


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise RankingCliError(
            code="E_USAGE",
            message=message,
            hint=f"Run `{self.prog} --help` for valid arguments.",
            exit_code=2,
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _readonly_uri(path: Path) -> str:
    return f"file:{path.resolve()}?mode=ro&immutable=1"


def _live_readonly_uri(path: Path) -> str:
    return f"file:{path.resolve()}?mode=ro"


def _require_file(path: Path, *, label: str) -> None:
    if not path.is_file():
        raise RankingCliError(
            code="E_NOT_FOUND",
            message=f"{label} does not exist: {path}",
            hint="Pass the exact frozen snapshot and tracked Registry paths.",
            exit_code=3,
        )


def _open_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(_readonly_uri(path), uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _validate_output_paths(
    *,
    snapshot_db: Path,
    registry_db: Path,
    analysis_db: Path,
    export_paths: list[Path],
    additional_inputs: list[Path] | None = None,
) -> None:
    inputs = {
        snapshot_db.expanduser().resolve(),
        registry_db.expanduser().resolve(),
    }
    inputs.update(
        path.expanduser().resolve() for path in (additional_inputs or [])
    )
    outputs = [analysis_db.expanduser().resolve()]
    outputs.extend(path.expanduser().resolve() for path in export_paths)
    if any(path in inputs for path in outputs) or len(set(outputs)) != len(outputs):
        raise RankingCliError(
            code="E_PATH_CONFLICT",
            message="Ranking input and output paths must all be distinct.",
            hint="Use data/derived for analysis and project resources for CSV exports.",
            exit_code=2,
        )


def _snapshot_registry_database(registry_db: Path) -> Path:
    """Capture one transactionally consistent Registry image for hashing/joins."""
    tmp_dir = REPO_ROOT / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix="following-ranking-registry-", suffix=".db", dir=tmp_dir
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    source = sqlite3.connect(_live_readonly_uri(registry_db), uri=True)
    destination = sqlite3.connect(temporary)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    return temporary


def _snapshot_metadata(snapshot_db: Path) -> dict[str, Any]:
    conn = _open_readonly(snapshot_db)
    try:
        runs = conn.execute("SELECT * FROM snapshot_run").fetchall()
        validation = (
            following_snapshots.validate_snapshot(conn) if len(runs) == 1 else None
        )
    except sqlite3.Error as exc:
        raise RankingCliError(
            code="E_SNAPSHOT_INVALID",
            message="Snapshot database does not match the following-snapshot schema.",
            hint="Validate it with `fli following-snapshot validate`.",
            exit_code=2,
        ) from exc
    finally:
        conn.close()
    if len(runs) != 1:
        raise RankingCliError(
            code="E_SNAPSHOT_INVALID",
            message=f"Snapshot database must contain one run, found {len(runs)}.",
            hint="Use a finalized following snapshot.",
            exit_code=2,
        )
    run = runs[0]
    if run["schema_version"] != following_snapshots.SNAPSHOT_SCHEMA_VERSION:
        raise RankingCliError(
            code="E_SNAPSHOT_INVALID",
            message=f"Unsupported snapshot schema: {run['schema_version']!r}.",
            hint="Use a following-snapshot-v1 database.",
            exit_code=2,
        )
    if run["status"] != "complete":
        raise RankingCliError(
            code="E_SNAPSHOT_INCOMPLETE",
            message=f"Snapshot is {run['status']!r}, not complete.",
            hint="Finalize the snapshot before ranking it.",
            exit_code=2,
        )
    assert validation is not None
    if not validation["valid"]:
        failures = ", ".join(validation["validation_failures"][:5])
        raise RankingCliError(
            code="E_SNAPSHOT_INVALID",
            message=f"Snapshot validation failed: {failures}",
            hint="Repair only from cached raw evidence or restore the frozen snapshot.",
            exit_code=2,
        )
    return dict(run)


def _verify_tracked_snapshot_manifest(
    snapshot: dict[str, Any], snapshot_sha256: str
) -> str | None:
    path = (
        REPO_ROOT
        / "data"
        / "following"
        / "manifests"
        / f"{snapshot['snapshot_id']}.json"
    )
    if not path.exists():
        return None
    try:
        manifest = json.loads(path.read_text())
        expected_sha256 = manifest["artifact"]["database_sha256"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RankingCliError(
            code="E_SNAPSHOT_INVALID",
            message=f"Tracked snapshot manifest is invalid: {path}",
            hint="Repair the tracked manifest before ranking.",
            exit_code=2,
        ) from exc
    if manifest.get("snapshot_id") != snapshot["snapshot_id"]:
        raise RankingCliError(
            code="E_SNAPSHOT_INVALID",
            message="Tracked manifest snapshot id does not match the database.",
            hint="Use the manifest and database from the same frozen snapshot.",
            exit_code=2,
        )
    if expected_sha256 != snapshot_sha256:
        raise RankingCliError(
            code="E_SNAPSHOT_INVALID",
            message="Frozen snapshot checksum does not match its tracked manifest.",
            hint="Restore the verified snapshot artifact before ranking.",
            exit_code=2,
        )
    return str(path.relative_to(REPO_ROOT))


def _validate_registry_schema(registry_db: Path) -> None:
    conn = _open_readonly(registry_db)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    finally:
        conn.close()
    missing = sorted(REGISTRY_READ_TABLES - tables)
    if missing:
        raise RankingCliError(
            code="E_REGISTRY_SCHEMA",
            message=f"Registry database is missing required tables: {', '.join(missing)}",
            hint="Pass the current Frontier Lab Intelligence Registry database.",
            exit_code=2,
        )


def _attach_readonly(conn: sqlite3.Connection, path: Path, schema: str) -> None:
    conn.execute(f"ATTACH DATABASE ? AS {schema}", (_readonly_uri(path),))


def _validate_analysis_schema(conn: sqlite3.Connection) -> None:
    versions = {
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT schema_version FROM analysis_context"
        ).fetchall()
    }
    ranking_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(ranking_result)")
    }
    entity_support_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(entity_support_result)")
    }
    run_columns = {row[1] for row in conn.execute("PRAGMA table_info(ranking_run)")}
    required_ranking = {"position", "score_rank"}
    required_entity_support = {
        "entity_id",
        "support_rank",
        "support_count",
        "support_share",
        "channel_count",
    }
    required_run = {
        "eligible_source_account_count",
        "eligible_source_entity_count",
        "eligible_vote_count",
    }
    if (
        versions - {ANALYSIS_SCHEMA_VERSION}
        or not required_ranking <= ranking_columns
        or not required_entity_support <= entity_support_columns
        or not required_run <= run_columns
    ):
        raise RankingCliError(
            code="E_ANALYSIS_SCHEMA",
            message="Derived database uses an incompatible analysis schema.",
            hint="Delete the recomputable analysis database and rerun.",
            exit_code=2,
        )


def _analysis_authorizer(
    action: int,
    arg1: str | None,
    arg2: str | None,
    database: str | None,
    source: str | None,
) -> int:
    del arg2, source
    if database in {"registry", "snapshot"}:
        if action in SQLITE_WRITE_ACTIONS:
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_READ:
            allowed = (
                REGISTRY_READ_TABLES
                if database == "registry"
                else SNAPSHOT_READ_TABLES
            )
            if arg1 not in allowed:
                return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def _registry_identity_cte() -> str:
    return """
        WITH registry_x AS (
            SELECT a.x_id,
                   e.id AS entity_id,
                   e.kind AS entity_kind,
                   e.name AS entity_name,
                   CASE WHEN r.entity_id IS NULL
                        THEN 'active' ELSE 'rejected' END AS registry_state
            FROM registry.accounts a
            JOIN registry.channels c
              ON c.kind = 'x' AND lower(c.key) = lower(a.handle)
            JOIN registry.entity_channels ec ON ec.channel_id = c.id
            JOIN registry.entities e ON e.id = ec.entity_id
            LEFT JOIN registry.entity_registry_rejections r
              ON r.entity_id = e.id
            WHERE a.platform = 'x'
              AND trim(COALESCE(a.x_id, '')) != ''
        )
    """


def _eligible_source_cte() -> str:
    return _registry_identity_cte() + """, eligible_source AS (
        SELECT sf.source_x_id, source_identity.entity_id
        FROM snapshot.source_fetch sf
        JOIN registry_x source_identity
          ON source_identity.x_id = sf.source_x_id
        WHERE sf.status = 'complete'
          AND source_identity.registry_state = 'active'
    )
    """


def _preflight_identity_mapping(conn: sqlite3.Connection) -> None:
    duplicate_x_id = conn.execute(
        """SELECT a.x_id
           FROM registry.accounts a
           WHERE a.platform = 'x' AND trim(COALESCE(a.x_id, '')) != ''
           GROUP BY a.x_id HAVING COUNT(*) != 1 LIMIT 1"""
    ).fetchone()
    if duplicate_x_id:
        raise RankingCliError(
            code="E_REGISTRY_IDENTITY_CONFLICT",
            message=f"Registry X ID maps to multiple accounts: {duplicate_x_id[0]}",
            hint="Resolve the Registry identity conflict before ranking.",
            exit_code=2,
        )
    orphan = conn.execute(
        """SELECT a.x_id
           FROM registry.accounts a
           LEFT JOIN registry.channels c
             ON c.kind = 'x' AND lower(c.key) = lower(a.handle)
           LEFT JOIN registry.entity_channels ec ON ec.channel_id = c.id
           WHERE a.platform = 'x'
             AND trim(COALESCE(a.x_id, '')) != ''
           GROUP BY a.x_id HAVING COUNT(DISTINCT ec.entity_id) != 1
           LIMIT 1"""
    ).fetchone()
    if orphan:
        raise RankingCliError(
            code="E_REGISTRY_IDENTITY_CONFLICT",
            message=f"Registry X ID has no single entity owner: {orphan[0]}",
            hint="Synchronize Registry channel ownership before ranking.",
            exit_code=2,
        )
    conflict = conn.execute(
        _registry_identity_cte()
        + """SELECT x_id FROM registry_x
             GROUP BY x_id HAVING COUNT(DISTINCT entity_id) != 1 LIMIT 1"""
    ).fetchone()
    if conflict:
        raise RankingCliError(
            code="E_REGISTRY_IDENTITY_CONFLICT",
            message=f"Registry X ID maps to multiple entities: {conflict[0]}",
            hint="Resolve channel ownership before ranking.",
            exit_code=2,
        )


def _context_id(
    snapshot: dict[str, Any], snapshot_sha256: str, registry_sha256: str
) -> str:
    return _sha256_text(
        _canonical_json(
            {
                "schema_version": ANALYSIS_SCHEMA_VERSION,
                "snapshot_id": snapshot["snapshot_id"],
                "cohort_sha256": snapshot["cohort_sha256"],
                "snapshot_db_sha256": snapshot_sha256,
                "registry_db_sha256": registry_sha256,
            }
        )
    )


def _run_id(context_id: str, algorithm: str, parameters_json: str) -> str:
    return _sha256_text(
        _canonical_json(
            {
                "context_id": context_id,
                "algorithm": algorithm,
                "parameters": json.loads(parameters_json),
            }
        )
    )


def _default_analysis_path(snapshot_id: str) -> Path:
    return DEFAULT_DERIVED_ROOT / snapshot_id / "analysis.db"


def _insert_context_and_nodes(
    conn: sqlite3.Connection,
    *,
    context_id: str,
    snapshot: dict[str, Any],
    snapshot_sha256: str,
    registry_sha256: str,
    registry_checkpoint_commit: str,
) -> None:
    conn.execute(
        """INSERT INTO analysis_context
           (context_id, schema_version, snapshot_id, cohort_sha256,
            snapshot_db_sha256, snapshot_checkpoint_commit,
            snapshot_checkpoint_db_sha256, registry_checkpoint_commit,
            registry_db_sha256, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            context_id,
            ANALYSIS_SCHEMA_VERSION,
            snapshot["snapshot_id"],
            snapshot["cohort_sha256"],
            snapshot_sha256,
            snapshot["checkpoint_commit"],
            snapshot["checkpoint_db_sha256"],
            registry_checkpoint_commit,
            registry_sha256,
            _now(),
        ),
    )
    conn.execute(
        _registry_identity_cte()
        + """INSERT INTO graph_node
             (context_id, x_id, handle, display_name, bio, followers_count,
              registry_state, entity_id, entity_kind, entity_name)
             SELECT ?, sa.x_id, sa.handle, sa.display_name, sa.bio,
                    sa.followers_count,
                    COALESCE(rx.registry_state, 'unknown'),
                    rx.entity_id, rx.entity_kind, rx.entity_name
             FROM snapshot.account sa
             LEFT JOIN registry_x rx ON rx.x_id = sa.x_id""",
        (context_id,),
    )


def _insert_overlap(
    conn: sqlite3.Connection,
    *,
    context_id: str,
    run_id: str,
    parameters_json: str,
) -> dict[str, int]:
    source_counts = conn.execute(
        _eligible_source_cte()
        + """SELECT COUNT(*) AS source_accounts,
                    COUNT(DISTINCT entity_id) AS source_entities
             FROM eligible_source"""
    ).fetchone()
    source_accounts = int(source_counts["source_accounts"])
    source_entities = int(source_counts["source_entities"])
    if not source_entities:
        raise RankingCliError(
            code="E_SNAPSHOT_INVALID",
            message="Snapshot has no complete active Registry sources.",
            hint="Check the cohort and current Registry identity mapping.",
            exit_code=2,
        )
    conn.execute(
        """INSERT INTO ranking_run
           (run_id, context_id, algorithm, parameters_json,
            eligible_source_account_count, eligible_source_entity_count,
            eligible_edge_count, eligible_vote_count, ranked_node_count,
            completed_at)
           VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, ?)""",
        (
            run_id,
            context_id,
            OVERLAP_ALGORITHM,
            parameters_json,
            source_accounts,
            source_entities,
            _now(),
        ),
    )
    eligible_edges = conn.execute(
        _eligible_source_cte()
        + """SELECT COUNT(*) FROM snapshot.edge e
             JOIN eligible_source source
               ON source.source_x_id = e.source_x_id"""
    ).fetchone()[0]
    conn.execute(
        _eligible_source_cte()
        + """, overlap AS (
               SELECT e.target_x_id,
                      COUNT(DISTINCT source.entity_id) AS cohort_follow_count
               FROM snapshot.edge e
               JOIN eligible_source source
                 ON source.source_x_id = e.source_x_id
               GROUP BY e.target_x_id
           ), scored AS (
               SELECT node.x_id AS target_x_id,
                      COALESCE(overlap.cohort_follow_count, 0)
                        AS cohort_follow_count,
                      node.handle
               FROM graph_node node
               LEFT JOIN overlap ON overlap.target_x_id = node.x_id
               WHERE node.context_id = ?
           ), ranked AS (
               SELECT scored.target_x_id,
                      scored.cohort_follow_count,
                      DENSE_RANK() OVER (
                          ORDER BY scored.cohort_follow_count DESC
                      ) AS score_rank,
                      ROW_NUMBER() OVER (
                          ORDER BY scored.cohort_follow_count DESC,
                                   lower(node.handle) ASC,
                                   scored.target_x_id ASC
                      ) AS display_position
               FROM scored
               JOIN graph_node node
                 ON node.context_id = ? AND node.x_id = scored.target_x_id
           )
           INSERT INTO ranking_result
             (run_id, x_id, position, score_rank, score, cohort_follow_count,
              cohort_follow_share)
           SELECT ?, target_x_id, display_position, score_rank,
                  cohort_follow_count,
                  cohort_follow_count,
                  CAST(cohort_follow_count AS REAL) / ?
           FROM ranked""",
        (context_id, context_id, run_id, source_entities),
    )
    conn.execute(
        _eligible_source_cte()
        + """, active_target AS (
               SELECT DISTINCT entity_id, x_id
               FROM registry_x
               WHERE registry_state = 'active'
           ), support_pair AS (
               SELECT DISTINCT target.entity_id AS target_entity_id,
                               source.entity_id AS source_entity_id
               FROM snapshot.edge edge
               JOIN eligible_source source
                 ON source.source_x_id = edge.source_x_id
               JOIN active_target target ON target.x_id = edge.target_x_id
               WHERE source.entity_id != target.entity_id
           ), entity_score AS (
               SELECT target.entity_id,
                      COUNT(DISTINCT target.x_id) AS channel_count,
                      COUNT(DISTINCT pair.source_entity_id) AS support_count
               FROM active_target target
               LEFT JOIN support_pair pair
                 ON pair.target_entity_id = target.entity_id
               GROUP BY target.entity_id
           ), ranked AS (
               SELECT entity_id, channel_count, support_count,
                      DENSE_RANK() OVER (
                          ORDER BY support_count DESC
                      ) AS support_rank
               FROM entity_score
           )
           INSERT INTO entity_support_result
             (run_id, entity_id, support_rank, support_count, support_share,
              channel_count)
           SELECT ?, entity_id, support_rank, support_count,
                  CAST(support_count AS REAL) / ?, channel_count
           FROM ranked""",
        (run_id, source_entities),
    )
    counts = conn.execute(
        """SELECT COUNT(*) AS ranked_nodes,
                  COALESCE(SUM(cohort_follow_count), 0) AS eligible_votes
           FROM ranking_result WHERE run_id = ?""",
        (run_id,),
    ).fetchone()
    entity_counts = conn.execute(
        """SELECT COUNT(*) AS ranked_entities,
                  COALESCE(SUM(support_count), 0) AS support_votes
           FROM entity_support_result WHERE run_id = ?""",
        (run_id,),
    ).fetchone()
    conn.execute(
        """UPDATE ranking_run
           SET eligible_edge_count = ?, eligible_vote_count = ?,
               ranked_node_count = ?
           WHERE run_id = ?""",
        (
            eligible_edges,
            counts["eligible_votes"],
            counts["ranked_nodes"],
            run_id,
        ),
    )
    return {
        "eligible_source_accounts": source_accounts,
        "eligible_source_entities": source_entities,
        "eligible_edges": int(eligible_edges),
        "eligible_entity_votes": int(counts["eligible_votes"]),
        "ranked_accounts": int(counts["ranked_nodes"]),
        "ranked_registry_entities": int(entity_counts["ranked_entities"]),
        "registry_entity_support_votes": int(entity_counts["support_votes"]),
    }


def _mapping_counts(conn: sqlite3.Connection, context_id: str) -> dict[str, int]:
    counts = {"active": 0, "rejected": 0, "unknown": 0}
    for row in conn.execute(
        """SELECT registry_state, COUNT(*) AS n FROM graph_node
           WHERE context_id = ? GROUP BY registry_state""",
        (context_id,),
    ):
        counts[row["registry_state"]] = int(row["n"])
    return counts


def _validate_context(
    conn: sqlite3.Connection,
    *,
    context_id: str,
    snapshot: dict[str, Any],
    snapshot_sha256: str,
    registry_sha256: str,
) -> None:
    context = conn.execute(
        "SELECT * FROM analysis_context WHERE context_id = ?", (context_id,)
    ).fetchone()
    expected = {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "snapshot_id": snapshot["snapshot_id"],
        "cohort_sha256": snapshot["cohort_sha256"],
        "snapshot_db_sha256": snapshot_sha256,
        "snapshot_checkpoint_commit": snapshot["checkpoint_commit"],
        "snapshot_checkpoint_db_sha256": snapshot["checkpoint_db_sha256"],
        "registry_db_sha256": registry_sha256,
    }
    if context is None or any(context[key] != value for key, value in expected.items()):
        raise RankingCliError(
            code="E_ANALYSIS_RECONCILIATION",
            message="Derived analysis context does not match its input checksums.",
            hint="Delete the derived analysis database and rerun.",
            exit_code=2,
        )
    snapshot_nodes = conn.execute("SELECT COUNT(*) FROM snapshot.account").fetchone()[0]
    derived_nodes = conn.execute(
        "SELECT COUNT(*) FROM graph_node WHERE context_id = ?", (context_id,)
    ).fetchone()[0]
    if derived_nodes != snapshot_nodes:
        raise RankingCliError(
            code="E_ANALYSIS_RECONCILIATION",
            message=(
                "Derived node count does not match the frozen snapshot: "
                f"{derived_nodes} != {snapshot_nodes}."
            ),
            hint="Delete the derived analysis database and rerun.",
            exit_code=2,
        )
    missing_derived = conn.execute(
        """SELECT 1 FROM snapshot.account account
           LEFT JOIN graph_node node
             ON node.context_id = ? AND node.x_id = account.x_id
           WHERE node.x_id IS NULL LIMIT 1""",
        (context_id,),
    ).fetchone()
    extra_derived = conn.execute(
        """SELECT 1 FROM graph_node node
           LEFT JOIN snapshot.account account ON account.x_id = node.x_id
           WHERE node.context_id = ? AND account.x_id IS NULL LIMIT 1""",
        (context_id,),
    ).fetchone()
    if missing_derived or extra_derived:
        raise RankingCliError(
            code="E_ANALYSIS_RECONCILIATION",
            message="Derived node identities do not exactly match the snapshot.",
            hint="Delete the derived analysis database and rerun.",
            exit_code=2,
        )


def _validate_ranking_run(conn: sqlite3.Connection, run: sqlite3.Row) -> None:
    actual = conn.execute(
        """SELECT COUNT(*) AS ranked_nodes,
                  COALESCE(SUM(cohort_follow_count), 0) AS eligible_votes,
                  COALESCE(MIN(position), 0) AS min_position,
                  COALESCE(MAX(position), 0) AS max_position,
                  COUNT(DISTINCT position) AS distinct_positions,
                  COALESCE(MIN(score_rank), 0) AS min_score_rank
           FROM ranking_result WHERE run_id = ?""",
        (run["run_id"],),
    ).fetchone()
    ranked_nodes = int(run["ranked_node_count"])
    valid = (
        actual["ranked_nodes"] == ranked_nodes
        and actual["eligible_votes"] == run["eligible_vote_count"]
        and actual["min_position"] == (1 if ranked_nodes else 0)
        and actual["max_position"] == ranked_nodes
        and actual["distinct_positions"] == ranked_nodes
        and actual["min_score_rank"] == (1 if ranked_nodes else 0)
    )
    if not valid:
        raise RankingCliError(
            code="E_ANALYSIS_RECONCILIATION",
            message="Stored ranking rows do not match their run metadata.",
            hint="Delete the derived analysis database and rerun.",
            exit_code=2,
        )
    missing_result = conn.execute(
        """SELECT 1 FROM graph_node node
           LEFT JOIN ranking_result result
             ON result.run_id = ? AND result.x_id = node.x_id
           WHERE node.context_id = ? AND result.x_id IS NULL LIMIT 1""",
        (run["run_id"], run["context_id"]),
    ).fetchone()
    extra_result = conn.execute(
        """SELECT 1 FROM ranking_result result
           LEFT JOIN graph_node node
             ON node.context_id = ? AND node.x_id = result.x_id
           WHERE result.run_id = ? AND node.x_id IS NULL LIMIT 1""",
        (run["context_id"], run["run_id"]),
    ).fetchone()
    if missing_result or extra_result:
        raise RankingCliError(
            code="E_ANALYSIS_RECONCILIATION",
            message="Stored ranking identities do not exactly match the node map.",
            hint="Delete the derived analysis database and rerun.",
            exit_code=2,
        )
    if run["algorithm"] == OVERLAP_ALGORITHM:
        bad_metric = conn.execute(
            """SELECT 1 FROM ranking_result
               WHERE run_id = ? AND (
                   score != cohort_follow_count
                   OR abs(cohort_follow_share -
                          CAST(cohort_follow_count AS REAL) / ?) > 1e-15
               ) LIMIT 1""",
            (run["run_id"], run["eligible_source_entity_count"]),
        ).fetchone()
        if bad_metric:
            raise RankingCliError(
                code="E_ANALYSIS_RECONCILIATION",
                message="Stored overlap score or share is inconsistent.",
                hint="Delete the derived analysis database and rerun.",
                exit_code=2,
            )
        entity_support = conn.execute(
            """SELECT COUNT(*) AS rows,
                      COALESCE(MIN(support_rank), 0) AS min_rank
               FROM entity_support_result WHERE run_id = ?""",
            (run["run_id"],),
        ).fetchone()
        active_entities = conn.execute(
            _registry_identity_cte()
            + """SELECT COUNT(DISTINCT entity_id)
                 FROM registry_x
                 WHERE registry_state = 'active'"""
        ).fetchone()[0]
        bad_entity_metric = conn.execute(
            """SELECT 1 FROM entity_support_result
               WHERE run_id = ? AND (
                   support_count < 0 OR channel_count < 1
                   OR abs(support_share - CAST(support_count AS REAL) / ?) > 1e-15
               ) LIMIT 1""",
            (run["run_id"], run["eligible_source_entity_count"]),
        ).fetchone()
        bad_entity_rank = conn.execute(
            """SELECT 1 FROM (
                   SELECT support_rank,
                          DENSE_RANK() OVER (
                              ORDER BY support_count DESC
                          ) AS expected_rank
                   FROM entity_support_result
                   WHERE run_id = ?
               )
               WHERE support_rank != expected_rank
               LIMIT 1""",
            (run["run_id"],),
        ).fetchone()
        if (
            entity_support["rows"] != active_entities
            or entity_support["min_rank"] != (1 if active_entities else 0)
            or bad_entity_metric
            or bad_entity_rank
        ):
            raise RankingCliError(
                code="E_ANALYSIS_RECONCILIATION",
                message="Stored entity-union support rows are inconsistent.",
                hint="Delete the derived analysis database and rerun.",
                exit_code=2,
            )
    elif run["algorithm"] == PAGERANK_ALGORITHM:
        score_sum = conn.execute(
            "SELECT SUM(score) FROM ranking_result WHERE run_id = ?",
            (run["run_id"],),
        ).fetchone()[0]
        diagnostics = conn.execute(
            "SELECT * FROM ranking_diagnostics WHERE run_id = ?",
            (run["run_id"],),
        ).fetchone()
        if (
            diagnostics is None
            or not diagnostics["converged"]
            or not math.isclose(score_sum, 1.0, rel_tol=0.0, abs_tol=1e-10)
        ):
            raise RankingCliError(
                code="E_ANALYSIS_RECONCILIATION",
                message="Stored PageRank diagnostics or score mass is inconsistent.",
                hint="Delete the derived analysis database and rerun.",
                exit_code=2,
            )


def _top_results(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    context_id: str,
    top_k: int,
    registry_state: str | None = None,
) -> list[dict[str, Any]]:
    state_clause = ""
    parameters: list[Any] = [context_id, run_id]
    if registry_state is not None:
        state_clause = " AND node.registry_state = ?"
        parameters.append(registry_state)
    parameters.append(top_k)
    rows = conn.execute(
        """SELECT run.algorithm, rr.position, rr.score_rank, rr.score, rr.x_id,
                  node.handle, node.display_name,
                  node.followers_count, rr.cohort_follow_count,
                  rr.cohort_follow_share, node.registry_state,
                  node.entity_id, node.entity_kind, node.entity_name,
                  run.eligible_source_entity_count
           FROM ranking_result rr
           JOIN ranking_run run ON run.run_id = rr.run_id
           JOIN graph_node node
             ON node.context_id = ? AND node.x_id = rr.x_id
           WHERE rr.run_id = ?"""
        + state_clause
        + " ORDER BY rr.position LIMIT ?",
        parameters,
    ).fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        result = dict(row)
        source_entities = result.pop("eligible_source_entity_count")
        if row["algorithm"] == PAGERANK_ALGORITHM:
            result["explanation"] = (
                f"Personalized PageRank score {row['score']:.12g}; followed by "
                f"{row['cohort_follow_count']} of {source_entities} complete "
                "active Registry entities."
            )
        else:
            result["explanation"] = (
                f"Followed by {row['cohort_follow_count']} of {source_entities} "
                "complete active Registry entities."
            )
        results.append(result)
    return results


def _export_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    fieldnames = [
        "algorithm",
        "position",
        "score_rank",
        "score",
        "x_id",
        "handle",
        "display_name",
        "followers_count",
        "cohort_follow_count",
        "cohort_follow_share",
        "registry_state",
        "entity_id",
        "entity_kind",
        "entity_name",
        "explanation",
    ]
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fieldnames, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def run_overlap(
    *,
    snapshot_db: Path,
    registry_db: Path = DEFAULT_REGISTRY_DB,
    analysis_db: Path | None = None,
    top_k: int = 100,
    export_csv: Path | None = None,
    export_unknown_csv: Path | None = None,
    sqlite_timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """Build or reuse the deterministic screened-source overlap baseline."""
    _require_file(snapshot_db, label="Snapshot database")
    _require_file(registry_db, label="Registry database")
    snapshot = _snapshot_metadata(snapshot_db)
    snapshot_sha256 = _sha256_file(snapshot_db)
    tracked_manifest = _verify_tracked_snapshot_manifest(snapshot, snapshot_sha256)
    analysis_db = analysis_db or _default_analysis_path(snapshot["snapshot_id"])
    export_paths = [path for path in (export_csv, export_unknown_csv) if path]
    _validate_output_paths(
        snapshot_db=snapshot_db,
        registry_db=registry_db,
        analysis_db=analysis_db,
        export_paths=export_paths,
    )
    parameters_json = _canonical_json(
        {
            "eligible_source_status": "complete",
            "eligible_registry_state": "active",
            "vote_unit": "registry_entity",
            "score": "cohort_follow_count",
            "score_rank": "dense",
            "registry_entity_support": {
                "target_unit": "registry_entity_union_of_x_channels",
                "source_unit": "registry_entity",
                "self_edges": "excluded",
                "rank": "dense_within_active_x_addressable_registry",
            },
            "display_order": [
                "cohort_follow_count_desc",
                "handle_asc",
                "x_id_asc",
            ],
        }
    )
    registry_snapshot = _snapshot_registry_database(registry_db)
    try:
        _validate_registry_schema(registry_snapshot)
        registry_sha256 = _sha256_file(registry_snapshot)
        registry_checkpoint_commit = _git_head()
        context_id = _context_id(snapshot, snapshot_sha256, registry_sha256)
        run_id = _run_id(context_id, OVERLAP_ALGORITHM, parameters_json)
        analysis_db.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            analysis_db, timeout=sqlite_timeout_seconds, uri=True
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        _validate_analysis_schema(conn)
        _attach_readonly(conn, snapshot_db, "snapshot")
        _attach_readonly(conn, registry_snapshot, "registry")
        conn.set_authorizer(_analysis_authorizer)
        reused = False
        try:
            _preflight_identity_mapping(conn)
            existing_context = conn.execute(
                "SELECT 1 FROM analysis_context WHERE context_id = ?", (context_id,)
            ).fetchone()
            if existing_context is None:
                conn.execute("BEGIN IMMEDIATE")
                _insert_context_and_nodes(
                    conn,
                    context_id=context_id,
                    snapshot=snapshot,
                    snapshot_sha256=snapshot_sha256,
                    registry_sha256=registry_sha256,
                    registry_checkpoint_commit=registry_checkpoint_commit,
                )
                conn.commit()
            _validate_context(
                conn,
                context_id=context_id,
                snapshot=snapshot,
                snapshot_sha256=snapshot_sha256,
                registry_sha256=registry_sha256,
            )
            existing_run = conn.execute(
                "SELECT * FROM ranking_run WHERE run_id = ?", (run_id,)
            ).fetchone()
            if existing_run is None:
                conn.execute("BEGIN IMMEDIATE")
                counts = _insert_overlap(
                    conn,
                    context_id=context_id,
                    run_id=run_id,
                    parameters_json=parameters_json,
                )
                conn.commit()
            else:
                reused = True
                counts = {
                    "eligible_source_accounts": int(
                        existing_run["eligible_source_account_count"]
                    ),
                    "eligible_source_entities": int(
                        existing_run["eligible_source_entity_count"]
                    ),
                    "eligible_edges": int(existing_run["eligible_edge_count"]),
                    "eligible_entity_votes": int(
                        existing_run["eligible_vote_count"]
                    ),
                    "ranked_accounts": int(existing_run["ranked_node_count"]),
                }
                entity_counts = conn.execute(
                    """SELECT COUNT(*) AS ranked_entities,
                              COALESCE(SUM(support_count), 0) AS support_votes
                       FROM entity_support_result WHERE run_id = ?""",
                    (run_id,),
                ).fetchone()
                counts.update(
                    {
                        "ranked_registry_entities": int(
                            entity_counts["ranked_entities"]
                        ),
                        "registry_entity_support_votes": int(
                            entity_counts["support_votes"]
                        ),
                    }
                )
            stored_run = conn.execute(
                "SELECT * FROM ranking_run WHERE run_id = ?", (run_id,)
            ).fetchone()
            assert stored_run is not None
            _validate_ranking_run(conn, stored_run)
            states = _mapping_counts(conn, context_id)
            if counts["ranked_accounts"] != sum(states.values()):
                raise RankingCliError(
                    code="E_ANALYSIS_RECONCILIATION",
                    message="Ranked-account count does not match the derived node map.",
                    hint="Delete the derived analysis database and rerun.",
                    exit_code=2,
                )
            top = _top_results(
                conn, run_id=run_id, context_id=context_id, top_k=top_k
            )
            top_active = _top_results(
                conn,
                run_id=run_id,
                context_id=context_id,
                top_k=top_k,
                registry_state="active",
            )
            top_unknown = _top_results(
                conn,
                run_id=run_id,
                context_id=context_id,
                top_k=top_k,
                registry_state="unknown",
            )
            if export_csv is not None:
                _export_csv(export_csv, top)
            if export_unknown_csv is not None:
                _export_csv(export_unknown_csv, top_unknown)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.set_authorizer(None)
            conn.close()
    finally:
        registry_snapshot.unlink(missing_ok=True)
    return {
        "algorithm": OVERLAP_ALGORITHM,
        "analysis_db": str(analysis_db.resolve()),
        "context_id": context_id,
        "run_id": run_id,
        "reused": reused,
        "snapshot": {
            "snapshot_id": snapshot["snapshot_id"],
            "cohort_sha256": snapshot["cohort_sha256"],
            "database_sha256": snapshot_sha256,
            "status": snapshot["status"],
            "tracked_manifest": tracked_manifest,
        },
        "registry": {
            "checkpoint_commit": registry_checkpoint_commit,
            "database_sha256": registry_sha256,
        },
        "counts": {**counts, **states},
        "top": top,
        "top_active": top_active,
        "top_unknown": top_unknown,
        "export_csv": str(export_csv.resolve()) if export_csv else None,
        "export_unknown_csv": (
            str(export_unknown_csv.resolve()) if export_unknown_csv else None
        ),
    }


def load_personalization(path: Path) -> tuple[dict[str, Any], str]:
    try:
        manifest = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise RankingCliError(
            code="E_NOT_FOUND",
            message=f"Personalization manifest does not exist: {path}",
            hint="Pass a tracked following-personalization-v1 manifest.",
            exit_code=3,
        ) from exc
    except json.JSONDecodeError as exc:
        raise RankingCliError(
            code="E_PERSONALIZATION_INVALID",
            message=f"Personalization manifest is not valid JSON: {path}",
            hint="Repair the tracked manifest before ranking.",
            exit_code=2,
        ) from exc
    if not isinstance(manifest, dict) or manifest.get(
        "schema_version"
    ) != PERSONALIZATION_SCHEMA_VERSION:
        raise RankingCliError(
            code="E_PERSONALIZATION_INVALID",
            message="Unsupported personalization manifest schema.",
            hint=f"Use {PERSONALIZATION_SCHEMA_VERSION}.",
            exit_code=2,
        )
    for key in ("personalization_id", "snapshot_id", "selection_rule"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            raise RankingCliError(
                code="E_PERSONALIZATION_INVALID",
                message=f"Personalization manifest needs {key}.",
                hint="Record stable identity and a reviewable selection rule.",
                exit_code=2,
            )
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        raise RankingCliError(
            code="E_PERSONALIZATION_INVALID",
            message="Personalization manifest needs at least one source.",
            hint="Add reviewed active sources with exact X IDs.",
            exit_code=2,
        )
    seen_x_ids: set[str] = set()
    seen_handles: set[str] = set()
    canonical_sources = []
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise RankingCliError(
                code="E_PERSONALIZATION_INVALID",
                message=f"Personalization source {index} must be an object.",
                hint="Use exact x_id, handle, category, weight, and reason fields.",
                exit_code=2,
            )
        x_id = str(source.get("x_id") or "").strip()
        handle = str(source.get("handle") or "").strip().removeprefix("@").lower()
        reason = str(source.get("reason") or "").strip()
        category = str(source.get("category") or "").strip()
        try:
            weight = float(source.get("weight"))
        except (TypeError, ValueError) as exc:
            raise RankingCliError(
                code="E_PERSONALIZATION_INVALID",
                message=f"Personalization source @{handle or index} has invalid weight.",
                hint="Use a positive numeric relative weight.",
                exit_code=2,
            ) from exc
        if not x_id or not handle or not reason or not category or weight <= 0:
            raise RankingCliError(
                code="E_PERSONALIZATION_INVALID",
                message=f"Personalization source {index} is incomplete.",
                hint="Use exact identity, category, positive weight, and short reason.",
                exit_code=2,
            )
        if x_id in seen_x_ids or handle in seen_handles:
            raise RankingCliError(
                code="E_PERSONALIZATION_INVALID",
                message=f"Personalization source @{handle} is duplicated.",
                hint="Each stable X identity may appear once.",
                exit_code=2,
            )
        seen_x_ids.add(x_id)
        seen_handles.add(handle)
        canonical_sources.append(
            {
                "x_id": x_id,
                "handle": handle,
                "category": category,
                "weight": weight,
                "reason": reason,
            }
        )
    canonical_sources.sort(key=lambda item: item["x_id"])
    canonical = {
        "schema_version": PERSONALIZATION_SCHEMA_VERSION,
        "personalization_id": manifest["personalization_id"],
        "snapshot_id": manifest["snapshot_id"],
        "weighting": manifest.get("weighting", "relative"),
        "selection_rule": manifest["selection_rule"],
        "sources": canonical_sources,
    }
    return manifest, _sha256_text(_canonical_json(canonical))


def _preflight_personalization(
    conn: sqlite3.Connection,
    *,
    context_id: str,
    snapshot_id: str,
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    if manifest["snapshot_id"] != snapshot_id:
        raise RankingCliError(
            code="E_PERSONALIZATION_INVALID",
            message="Personalization snapshot id does not match the ranking snapshot.",
            hint="Freeze a new personalization manifest for this snapshot.",
            exit_code=2,
        )
    resolved = []
    seen_entity_ids: set[int] = set()
    total_weight = sum(float(source["weight"]) for source in manifest["sources"])
    for source in manifest["sources"]:
        row = conn.execute(
            _registry_identity_cte()
            + """SELECT sf.source_x_id, sf.source_handle, sf.status,
                        rx.registry_state, rx.entity_id, node.x_id AS node_x_id
                 FROM snapshot.source_fetch sf
                 LEFT JOIN registry_x rx ON rx.x_id = sf.source_x_id
                 LEFT JOIN graph_node node
                   ON node.context_id = ? AND node.x_id = sf.source_x_id
                 WHERE sf.source_x_id = ?""",
            (context_id, str(source["x_id"])),
        ).fetchone()
        handle = str(source["handle"]).lower()
        if row is None or row["source_handle"].lower() != handle:
            raise RankingCliError(
                code="E_PERSONALIZATION_INVALID",
                message=f"Snapshot identity mismatch for @{handle}.",
                hint="Verify the stable X ID and handle in the frozen snapshot.",
                exit_code=2,
            )
        if (
            row["status"] != "complete"
            or row["registry_state"] != "active"
            or row["node_x_id"] is None
        ):
            raise RankingCliError(
                code="E_PERSONALIZATION_INVALID",
                message=f"Personalization source @{handle} is not complete and active.",
                hint="Choose an active Registry source with a complete snapshot.",
                exit_code=2,
            )
        entity_id = int(row["entity_id"])
        if entity_id in seen_entity_ids:
            raise RankingCliError(
                code="E_PERSONALIZATION_INVALID",
                message=f"Multiple personalization channels resolve to entity {entity_id}.",
                hint="Choose one representative X channel per real-world entity.",
                exit_code=2,
            )
        seen_entity_ids.add(entity_id)
        resolved.append(
            {
                **source,
                "entity_id": entity_id,
                "normalized_weight": float(source["weight"]) / total_weight,
            }
        )
    return resolved


def _pagerank_source_vector(
    conn: sqlite3.Connection,
    *,
    seeds: list[dict[str, Any]],
    damping: float,
    tolerance: float,
    max_iterations: int,
) -> tuple[list[tuple[str, float]], int, float, float]:
    conn.execute(
        "CREATE TEMP TABLE pagerank_eligible_source AS "
        + _eligible_source_cte()
        + " SELECT source_x_id, entity_id FROM eligible_source"
    )
    conn.execute(
        """CREATE UNIQUE INDEX pagerank_eligible_source_x_id
           ON pagerank_eligible_source(source_x_id)"""
    )
    source_rows = conn.execute(
        """SELECT source.source_x_id,
                  COUNT(edge.target_x_id) AS outdegree
             FROM pagerank_eligible_source source
             LEFT JOIN snapshot.edge edge
               ON edge.source_x_id = source.source_x_id
             GROUP BY source.source_x_id
             ORDER BY source.source_x_id"""
    ).fetchall()
    source_index = {row["source_x_id"]: index for index, row in enumerate(source_rows)}
    outdegrees = np.asarray(
        [int(row["outdegree"]) for row in source_rows], dtype=np.float64
    )
    personalization = np.zeros(len(source_rows), dtype=np.float64)
    for seed in seeds:
        personalization[source_index[str(seed["x_id"])]] = float(
            seed["normalized_weight"]
        )
    source_edges = array("I")
    target_edges = array("I")
    for row in conn.execute(
        """SELECT edge.source_x_id, edge.target_x_id
           FROM snapshot.edge edge
           JOIN pagerank_eligible_source source
             ON source.source_x_id = edge.source_x_id
           JOIN pagerank_eligible_source target
             ON target.source_x_id = edge.target_x_id"""
    ):
        source_edges.append(source_index[row["source_x_id"]])
        target_edges.append(source_index[row["target_x_id"]])
    source_edge_indices = np.frombuffer(source_edges, dtype=np.uint32)
    target_edge_indices = np.frombuffer(target_edges, dtype=np.uint32)
    outgoing_mask = outdegrees > 0
    rank = personalization.copy()
    final_delta = math.inf
    base = 0.0
    for iteration in range(1, max_iterations + 1):
        outgoing_mass = float(rank[outgoing_mask].sum())
        dangling_mass = max(0.0, 1.0 - outgoing_mass)
        base = (1.0 - damping) + damping * dangling_mass
        next_rank = base * personalization
        edge_contributions = (
            damping
            * rank[source_edge_indices]
            / outdegrees[source_edge_indices]
        )
        next_rank += np.bincount(
            target_edge_indices,
            weights=edge_contributions,
            minlength=len(source_rows),
        )
        final_delta = float(np.abs(next_rank - rank).sum())
        rank = next_rank
        if final_delta <= tolerance:
            outgoing_mass = float(rank[outgoing_mask].sum())
            dangling_mass = max(0.0, 1.0 - outgoing_mass)
            base = (1.0 - damping) + damping * dangling_mass
            contributions = [
                (row["source_x_id"], float(rank[index] / outdegrees[index]))
                for index, row in enumerate(source_rows)
                if outdegrees[index]
            ]
            return contributions, iteration, final_delta, base
    raise RankingCliError(
        code="E_PAGERANK_DID_NOT_CONVERGE",
        message=(
            f"Personalized PageRank did not converge after {max_iterations} "
            f"iterations (L1 delta {final_delta:.3g})."
        ),
        hint="Increase --max-iterations or relax --tolerance; no partial run was stored.",
        exit_code=2,
    )


def _insert_pagerank(
    conn: sqlite3.Connection,
    *,
    context_id: str,
    run_id: str,
    overlap_run: sqlite3.Row,
    parameters_json: str,
    seeds: list[dict[str, Any]],
    personalization_id: str,
    personalization_sha256: str,
    contributions: list[tuple[str, float]],
    damping: float,
    base: float,
    iterations: int,
    final_delta: float,
) -> None:
    conn.execute(
        """CREATE TEMP TABLE pagerank_source_weight (
               x_id TEXT PRIMARY KEY,
               contribution REAL NOT NULL
           )"""
    )
    conn.executemany(
        "INSERT INTO pagerank_source_weight (x_id, contribution) VALUES (?, ?)",
        contributions,
    )
    conn.execute(
        """CREATE TEMP TABLE pagerank_personalization (
               x_id TEXT PRIMARY KEY,
               weight REAL NOT NULL
           )"""
    )
    conn.executemany(
        "INSERT INTO pagerank_personalization (x_id, weight) VALUES (?, ?)",
        [(str(seed["x_id"]), seed["normalized_weight"]) for seed in seeds],
    )
    conn.execute(
        """INSERT INTO ranking_run
           (run_id, context_id, algorithm, parameters_json,
            eligible_source_account_count, eligible_source_entity_count,
            eligible_edge_count, eligible_vote_count, ranked_node_count,
            completed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run_id,
            context_id,
            PAGERANK_ALGORITHM,
            parameters_json,
            overlap_run["eligible_source_account_count"],
            overlap_run["eligible_source_entity_count"],
            overlap_run["eligible_edge_count"],
            overlap_run["eligible_vote_count"],
            overlap_run["ranked_node_count"],
            _now(),
        ),
    )
    conn.execute(
        """WITH incoming AS (
               SELECT edge.target_x_id,
                      SUM(weight.contribution) AS incoming_score
               FROM snapshot.edge edge
               JOIN pagerank_source_weight weight
                 ON weight.x_id = edge.source_x_id
               GROUP BY edge.target_x_id
           ), scored AS (
               SELECT node.x_id,
                      (? * COALESCE(seed.weight, 0.0))
                        + (? * COALESCE(incoming.incoming_score, 0.0)) AS score,
                      node.handle,
                      overlap.cohort_follow_count,
                      overlap.cohort_follow_share
               FROM graph_node node
               JOIN ranking_result overlap
                 ON overlap.run_id = ? AND overlap.x_id = node.x_id
               LEFT JOIN incoming ON incoming.target_x_id = node.x_id
               LEFT JOIN pagerank_personalization seed ON seed.x_id = node.x_id
               WHERE node.context_id = ?
           ), ranked AS (
               SELECT x_id, score, cohort_follow_count, cohort_follow_share,
                      DENSE_RANK() OVER (ORDER BY score DESC) AS score_rank,
                      ROW_NUMBER() OVER (
                          ORDER BY score DESC, lower(handle) ASC, x_id ASC
                      ) AS display_position
               FROM scored
           )
           INSERT INTO ranking_result
             (run_id, x_id, position, score_rank, score,
              cohort_follow_count, cohort_follow_share)
           SELECT ?, x_id, display_position, score_rank, score,
                  cohort_follow_count, cohort_follow_share
           FROM ranked""",
        (base, damping, overlap_run["run_id"], context_id, run_id),
    )
    score_sum = float(
        conn.execute(
            "SELECT SUM(score) FROM ranking_result WHERE run_id = ?", (run_id,)
        ).fetchone()[0]
    )
    if not math.isclose(score_sum, 1.0, rel_tol=0.0, abs_tol=1e-10):
        raise RankingCliError(
            code="E_ANALYSIS_RECONCILIATION",
            message=f"Personalized PageRank score sum is {score_sum}, not 1.",
            hint="Do not retain this run; inspect dangling-mass handling.",
            exit_code=2,
        )
    conn.execute(
        """INSERT INTO ranking_diagnostics
           (run_id, iterations, final_delta, score_sum, converged, seed_count,
            personalization_id, personalization_sha256)
           VALUES (?, ?, ?, ?, 1, ?, ?, ?)""",
        (
            run_id,
            iterations,
            final_delta,
            score_sum,
            len(seeds),
            personalization_id,
            personalization_sha256,
        ),
    )
    conn.execute(
        """INSERT INTO ranking_comparison
           (overlap_run_id, pagerank_run_id, x_id, overlap_position,
            overlap_score_rank, cohort_follow_count, cohort_follow_share,
            pagerank_position, pagerank_score_rank, pagerank_score,
            pagerank_position_gain, is_personalization_seed)
           SELECT overlap.run_id, pagerank.run_id, overlap.x_id,
                  overlap.position, overlap.score_rank,
                  overlap.cohort_follow_count, overlap.cohort_follow_share,
                  pagerank.position, pagerank.score_rank, pagerank.score,
                  overlap.position - pagerank.position,
                  CASE WHEN seed.x_id IS NULL THEN 0 ELSE 1 END
           FROM ranking_result overlap
           JOIN ranking_result pagerank ON pagerank.x_id = overlap.x_id
           LEFT JOIN pagerank_personalization seed ON seed.x_id = overlap.x_id
           WHERE overlap.run_id = ? AND pagerank.run_id = ?""",
        (overlap_run["run_id"], run_id),
    )


def _comparison_rows(
    conn: sqlite3.Connection,
    *,
    overlap_run_id: str,
    pagerank_run_id: str,
    context_id: str,
    top_k: int,
    registry_state: str | None = None,
) -> list[dict[str, Any]]:
    state_clause = ""
    parameters: list[Any] = [context_id, overlap_run_id, pagerank_run_id]
    if registry_state is not None:
        state_clause = " AND node.registry_state = ?"
        parameters.append(registry_state)
    parameters.append(top_k)
    rows = conn.execute(
        """SELECT comparison.x_id, node.handle, node.display_name,
                  node.registry_state, node.entity_id, node.entity_kind,
                  node.entity_name, comparison.cohort_follow_count,
                  comparison.cohort_follow_share,
                  comparison.overlap_position, comparison.overlap_score_rank,
                  comparison.pagerank_score, comparison.pagerank_position,
                  comparison.pagerank_score_rank,
                  comparison.pagerank_position_gain,
                  comparison.is_personalization_seed
           FROM ranking_comparison comparison
           JOIN graph_node node
             ON node.context_id = ? AND node.x_id = comparison.x_id
           WHERE comparison.overlap_run_id = ?
             AND comparison.pagerank_run_id = ?"""
        + state_clause
        + " ORDER BY comparison.pagerank_position LIMIT ?",
        parameters,
    ).fetchall()
    return [dict(row) for row in rows]


def _export_comparison_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    fieldnames = [
        "x_id",
        "handle",
        "display_name",
        "registry_state",
        "entity_id",
        "entity_kind",
        "entity_name",
        "cohort_follow_count",
        "cohort_follow_share",
        "overlap_position",
        "overlap_score_rank",
        "pagerank_score",
        "pagerank_position",
        "pagerank_score_rank",
        "pagerank_position_gain",
        "is_personalization_seed",
    ]
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fieldnames, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def run_pagerank(
    *,
    snapshot_db: Path,
    registry_db: Path = DEFAULT_REGISTRY_DB,
    analysis_db: Path | None = None,
    personalization_path: Path = DEFAULT_PERSONALIZATION,
    damping: float = 0.85,
    tolerance: float = 1e-10,
    max_iterations: int = 200,
    top_k: int = 100,
    export_comparison_csv: Path | None = None,
    export_unknown_csv: Path | None = None,
    sqlite_timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """Build or reuse personalized PageRank and its overlap comparison."""
    manifest, personalization_sha256 = load_personalization(personalization_path)
    analysis_db = analysis_db or _default_analysis_path(manifest["snapshot_id"])
    export_paths = [
        path for path in (export_comparison_csv, export_unknown_csv) if path
    ]
    _validate_output_paths(
        snapshot_db=snapshot_db,
        registry_db=registry_db,
        analysis_db=analysis_db,
        export_paths=export_paths,
        additional_inputs=[personalization_path],
    )
    overlap = run_overlap(
        snapshot_db=snapshot_db,
        registry_db=registry_db,
        analysis_db=analysis_db,
        top_k=1,
        sqlite_timeout_seconds=sqlite_timeout_seconds,
    )
    analysis_db = Path(overlap["analysis_db"])
    registry_snapshot = _snapshot_registry_database(registry_db)
    try:
        registry_sha256 = _sha256_file(registry_snapshot)
        if registry_sha256 != overlap["registry"]["database_sha256"]:
            raise RankingCliError(
                code="E_REGISTRY_CHANGED",
                message="Registry changed while preparing personalized PageRank.",
                hint="Rerun after Registry writes finish.",
                exit_code=4,
                retryable=True,
            )
        conn = sqlite3.connect(
            analysis_db, timeout=sqlite_timeout_seconds, uri=True
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
        _validate_analysis_schema(conn)
        _attach_readonly(conn, snapshot_db, "snapshot")
        _attach_readonly(conn, registry_snapshot, "registry")
        conn.set_authorizer(_analysis_authorizer)
        try:
            _preflight_identity_mapping(conn)
            seeds = _preflight_personalization(
                conn,
                context_id=overlap["context_id"],
                snapshot_id=overlap["snapshot"]["snapshot_id"],
                manifest=manifest,
            )
            parameters_json = _canonical_json(
                {
                    "damping": damping,
                    "tolerance_l1": tolerance,
                    "max_iterations": max_iterations,
                    "dangling_distribution": "personalization",
                    "personalization_id": manifest["personalization_id"],
                    "personalization_sha256": personalization_sha256,
                    "eligible_source_status": "complete",
                    "eligible_registry_state": "active",
                    "display_order": ["score_desc", "handle_asc", "x_id_asc"],
                }
            )
            run_id = _run_id(
                overlap["context_id"], PAGERANK_ALGORITHM, parameters_json
            )
            overlap_run = conn.execute(
                "SELECT * FROM ranking_run WHERE run_id = ?",
                (overlap["run_id"],),
            ).fetchone()
            if overlap_run is None:
                raise RankingCliError(
                    code="E_ANALYSIS_RECONCILIATION",
                    message="Overlap baseline is missing from the derived database.",
                    hint="Rerun the overlap baseline before PageRank.",
                    exit_code=2,
                )
            existing_run = conn.execute(
                "SELECT * FROM ranking_run WHERE run_id = ?", (run_id,)
            ).fetchone()
            reused = existing_run is not None
            if existing_run is None:
                contributions, iterations, final_delta, base = (
                    _pagerank_source_vector(
                        conn,
                        seeds=seeds,
                        damping=damping,
                        tolerance=tolerance,
                        max_iterations=max_iterations,
                    )
                )
                conn.execute("BEGIN IMMEDIATE")
                _insert_pagerank(
                    conn,
                    context_id=overlap["context_id"],
                    run_id=run_id,
                    overlap_run=overlap_run,
                    parameters_json=parameters_json,
                    seeds=seeds,
                    personalization_id=manifest["personalization_id"],
                    personalization_sha256=personalization_sha256,
                    contributions=contributions,
                    damping=damping,
                    base=base,
                    iterations=iterations,
                    final_delta=final_delta,
                )
                conn.commit()
                existing_run = conn.execute(
                    "SELECT * FROM ranking_run WHERE run_id = ?", (run_id,)
                ).fetchone()
            assert existing_run is not None
            _validate_ranking_run(conn, existing_run)
            diagnostics = dict(
                conn.execute(
                    "SELECT * FROM ranking_diagnostics WHERE run_id = ?", (run_id,)
                ).fetchone()
            )
            top = _top_results(
                conn,
                run_id=run_id,
                context_id=overlap["context_id"],
                top_k=top_k,
            )
            top_active = _top_results(
                conn,
                run_id=run_id,
                context_id=overlap["context_id"],
                top_k=top_k,
                registry_state="active",
            )
            top_unknown = _top_results(
                conn,
                run_id=run_id,
                context_id=overlap["context_id"],
                top_k=top_k,
                registry_state="unknown",
            )
            comparison = _comparison_rows(
                conn,
                overlap_run_id=overlap["run_id"],
                pagerank_run_id=run_id,
                context_id=overlap["context_id"],
                top_k=top_k,
            )
            unknown_comparison = _comparison_rows(
                conn,
                overlap_run_id=overlap["run_id"],
                pagerank_run_id=run_id,
                context_id=overlap["context_id"],
                top_k=top_k,
                registry_state="unknown",
            )
            if export_comparison_csv is not None:
                _export_comparison_csv(export_comparison_csv, comparison)
            if export_unknown_csv is not None:
                _export_comparison_csv(export_unknown_csv, unknown_comparison)
            overlap_top_ids = {
                row["x_id"]
                for row in _top_results(
                    conn,
                    run_id=overlap["run_id"],
                    context_id=overlap["context_id"],
                    top_k=top_k,
                )
            }
            pagerank_top_ids = {row["x_id"] for row in top}
            union = overlap_top_ids | pagerank_top_ids
            jaccard = (
                len(overlap_top_ids & pagerank_top_ids) / len(union)
                if union
                else 1.0
            )
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.set_authorizer(None)
            conn.close()
    finally:
        registry_snapshot.unlink(missing_ok=True)
    return {
        "algorithm": PAGERANK_ALGORITHM,
        "analysis_db": str(analysis_db.resolve()),
        "context_id": overlap["context_id"],
        "run_id": run_id,
        "overlap_run_id": overlap["run_id"],
        "reused": reused,
        "personalization": {
            "id": manifest["personalization_id"],
            "sha256": personalization_sha256,
            "status": manifest.get("status"),
            "source_count": len(seeds),
            "path": str(personalization_path.resolve()),
        },
        "parameters": json.loads(parameters_json),
        "diagnostics": diagnostics,
        "counts": overlap["counts"],
        "comparison": {
            "top_k": top_k,
            "top_k_jaccard": jaccard,
        },
        "top": top,
        "top_active": top_active,
        "top_unknown": top_unknown,
        "export_comparison_csv": (
            str(export_comparison_csv.resolve()) if export_comparison_csv else None
        ),
        "export_unknown_csv": (
            str(export_unknown_csv.resolve()) if export_unknown_csv else None
        ),
    }


def _result(
    *,
    command: str,
    status: str,
    data: dict[str, Any] | None,
    error_obj: dict[str, Any] | None,
    started: float,
    request_id: str,
) -> dict[str, Any]:
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "command": command,
        "status": status,
        "data": data,
        "error": error_obj,
        "meta": {
            "request_id": request_id,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "timestamp_utc": _now(),
        },
    }


def _print_result(payload: dict[str, Any], *, plain: bool) -> None:
    if not plain:
        print(json.dumps(payload, sort_keys=True))
        return
    if payload["status"] == "error":
        error = payload["error"] or {}
        print(f"error: {error.get('code')}: {error.get('message')}")
        return
    data = payload["data"] or {}
    counts = data.get("counts") or {}
    print(
        f"{payload['command']}: algorithm={data.get('algorithm')} "
        f"source_entities={counts.get('eligible_source_entities', 0)} "
        f"source_accounts={counts.get('eligible_source_accounts', 0)} "
        f"edges={counts.get('eligible_edges', 0)} "
        f"accounts={counts.get('ranked_accounts', 0)} "
        f"reused={str(data.get('reused', False)).lower()}"
    )


def main(argv: list[str] | None = None) -> int:
    started = time.monotonic()
    request_id = str(uuid.uuid4())
    command = "following-ranking"
    parser = JsonArgumentParser(prog="fli following-ranking")
    sub = parser.add_subparsers(dest="action", required=True)
    overlap = sub.add_parser(
        "overlap", help="Rank accounts by distinct complete active sources."
    )
    overlap.add_argument("--snapshot-db", type=Path, required=True)
    overlap.add_argument("--registry-db", type=Path, default=DEFAULT_REGISTRY_DB)
    overlap.add_argument("--analysis-db", type=Path)
    overlap.add_argument("--top-k", type=int, default=100)
    overlap.add_argument("--export-csv", type=Path)
    overlap.add_argument("--export-unknown-csv", type=Path)
    overlap.add_argument("--sqlite-timeout-seconds", type=float, default=30.0)
    overlap.add_argument("--no-input", action="store_true")
    overlap.add_argument("--json", action="store_true", help="Emit JSON (default).")
    overlap.add_argument("--plain", action="store_true", help="Emit compact text.")
    pagerank = sub.add_parser(
        "pagerank", help="Run reviewed personalized PageRank and compare overlap."
    )
    pagerank.add_argument("--snapshot-db", type=Path, required=True)
    pagerank.add_argument("--registry-db", type=Path, default=DEFAULT_REGISTRY_DB)
    pagerank.add_argument("--analysis-db", type=Path)
    pagerank.add_argument(
        "--personalization", type=Path, default=DEFAULT_PERSONALIZATION
    )
    pagerank.add_argument("--damping", type=float, default=0.85)
    pagerank.add_argument("--tolerance", type=float, default=1e-10)
    pagerank.add_argument("--max-iterations", type=int, default=200)
    pagerank.add_argument("--top-k", type=int, default=100)
    pagerank.add_argument("--export-comparison-csv", type=Path)
    pagerank.add_argument("--export-unknown-csv", type=Path)
    pagerank.add_argument("--sqlite-timeout-seconds", type=float, default=30.0)
    pagerank.add_argument("--no-input", action="store_true")
    pagerank.add_argument("--json", action="store_true", help="Emit JSON (default).")
    pagerank.add_argument("--plain", action="store_true", help="Emit compact text.")
    try:
        args = parser.parse_args(argv)
        command = f"following-ranking {args.action}"
        if args.top_k < 1:
            raise RankingCliError(
                code="E_USAGE",
                message="--top-k must be at least 1.",
                hint="Pass a positive review-list size.",
                exit_code=2,
            )
        if args.sqlite_timeout_seconds <= 0:
            raise RankingCliError(
                code="E_USAGE",
                message="--sqlite-timeout-seconds must be positive.",
                hint="Pass a positive SQLite busy timeout.",
                exit_code=2,
            )
        if args.action == "overlap":
            data = run_overlap(
                snapshot_db=args.snapshot_db,
                registry_db=args.registry_db,
                analysis_db=args.analysis_db,
                top_k=args.top_k,
                export_csv=args.export_csv,
                export_unknown_csv=args.export_unknown_csv,
                sqlite_timeout_seconds=args.sqlite_timeout_seconds,
            )
        else:
            if not 0.0 < args.damping < 1.0:
                raise RankingCliError(
                    code="E_USAGE",
                    message="--damping must be between 0 and 1.",
                    hint="Use 0.85 for the baseline experiment.",
                    exit_code=2,
                )
            if args.tolerance <= 0 or args.max_iterations < 1:
                raise RankingCliError(
                    code="E_USAGE",
                    message="PageRank tolerance and iteration limit must be positive.",
                    hint="Use --tolerance 1e-10 --max-iterations 200.",
                    exit_code=2,
                )
            data = run_pagerank(
                snapshot_db=args.snapshot_db,
                registry_db=args.registry_db,
                analysis_db=args.analysis_db,
                personalization_path=args.personalization,
                damping=args.damping,
                tolerance=args.tolerance,
                max_iterations=args.max_iterations,
                top_k=args.top_k,
                export_comparison_csv=args.export_comparison_csv,
                export_unknown_csv=args.export_unknown_csv,
                sqlite_timeout_seconds=args.sqlite_timeout_seconds,
            )
        payload = _result(
            command=command,
            status="ok",
            data=data,
            error_obj=None,
            started=started,
            request_id=request_id,
        )
        _print_result(payload, plain=args.plain)
        return 0
    except KeyboardInterrupt:
        exc = RankingCliError(
            code="E_INTERRUPTED",
            message="Ranking was interrupted.",
            hint="Rerun the command; completed deterministic runs are reusable.",
            exit_code=5,
            retryable=True,
        )
    except RankingCliError as caught:
        exc = caught
    except sqlite3.OperationalError as caught:
        message = str(caught)
        busy = "locked" in message.lower() or "busy" in message.lower()
        exc = RankingCliError(
            code="E_DATABASE_BUSY" if busy else "E_ANALYSIS_WRITE",
            message=message,
            hint=(
                "Retry after the writer releases the derived database."
                if busy
                else "Check the snapshot, Registry, and derived database paths."
            ),
            exit_code=4 if busy else 3,
            retryable=busy,
        )
    except (sqlite3.Error, OSError, subprocess.SubprocessError) as caught:
        exc = RankingCliError(
            code="E_ANALYSIS_WRITE",
            message=str(caught),
            hint="Check the input files and derived database destination.",
            exit_code=3,
        )
    payload = _result(
        command=command,
        status="error",
        data=None,
        error_obj={
            "code": exc.code,
            "message": exc.message,
            "retryable": exc.retryable,
            "hint": exc.hint,
        },
        started=started,
        request_id=request_id,
    )
    _print_result(payload, plain="--plain" in (argv or []))
    return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
