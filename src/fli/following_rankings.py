"""Recomputable rankings over one immutable outgoing-follow snapshot.

This module may read the frozen snapshot and the Registry identity tables. It
cannot read the legacy ``graph_edges`` table: a SQLite authorizer limits reads
from the attached Registry database to the exact identity tables needed for
stable-X-ID mapping. All results live in a separate derived SQLite database.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
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

from fli import following_snapshots


RESULT_SCHEMA_VERSION = "1.0"
ANALYSIS_SCHEMA_VERSION = "following-analysis-v2"
OVERLAP_ALGORITHM = "entity-overlap-v2"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_DB = REPO_ROOT / "data" / "fli.db"
DEFAULT_DERIVED_ROOT = REPO_ROOT / "data" / "derived" / "following"

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
) -> None:
    inputs = {
        snapshot_db.expanduser().resolve(),
        registry_db.expanduser().resolve(),
    }
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
    run_columns = {row[1] for row in conn.execute("PRAGMA table_info(ranking_run)")}
    required_ranking = {"position", "score_rank"}
    required_run = {
        "eligible_source_account_count",
        "eligible_source_entity_count",
        "eligible_vote_count",
    }
    if (
        versions - {ANALYSIS_SCHEMA_VERSION}
        or not required_ranking <= ranking_columns
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


def _run_id(context_id: str, parameters_json: str) -> str:
    return _sha256_text(
        _canonical_json(
            {
                "context_id": context_id,
                "algorithm": OVERLAP_ALGORITHM,
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
    counts = conn.execute(
        """SELECT COUNT(*) AS ranked_nodes,
                  COALESCE(SUM(cohort_follow_count), 0) AS eligible_votes
           FROM ranking_result WHERE run_id = ?""",
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
        """SELECT rr.position, rr.score_rank, rr.x_id,
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
        "position",
        "score_rank",
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
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
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
        run_id = _run_id(context_id, parameters_json)
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
                _validate_ranking_run(conn, existing_run)
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
        data = run_overlap(
            snapshot_db=args.snapshot_db,
            registry_db=args.registry_db,
            analysis_db=args.analysis_db,
            top_k=args.top_k,
            export_csv=args.export_csv,
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
