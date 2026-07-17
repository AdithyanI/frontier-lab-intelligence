"""Read-only ranking queries for the web API.

Reads the derived analysis store (data/derived/following/<snapshot-id>/
analysis.db) and the frozen following snapshot (data/raw/following/
<snapshot-id>/snapshot.db). Both are opened read-only; nothing here writes.
If either file is absent the API reports an unavailable state instead of
failing, so the UI can render an honest empty state.
"""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any

from fli.network.rankings import DEFAULT_DERIVED_ROOT, OVERLAP_ALGORITHM

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_FOLLOWING_ROOT = REPO_ROOT / "data" / "raw" / "following"


def _open_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
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


def latest_analysis_db(root: Path = DEFAULT_DERIVED_ROOT) -> Path | None:
    """Newest completed entity-overlap analysis, independent of directory names."""
    if not root.is_dir():
        return None
    candidates: list[tuple[str, str, Path]] = []
    for directory in root.iterdir():
        path = directory / "analysis.db"
        if not path.is_file():
            continue
        conn: sqlite3.Connection | None = None
        try:
            conn = _open_readonly(path)
            has_entity_support = conn.execute(
                """SELECT 1 FROM sqlite_master
                   WHERE type = 'table' AND name = 'entity_support_result'"""
            ).fetchone()
            run = _latest_run(conn) if has_entity_support else None
        except sqlite3.Error:
            run = None
        finally:
            if conn is not None:
                conn.close()
        if run is not None:
            candidates.append((run["completed_at"], directory.name, path))
    return max(candidates)[2] if candidates else None


def _latest_analysis_db() -> Path | None:
    return latest_analysis_db(DEFAULT_DERIVED_ROOT)


def _latest_run(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        """SELECT r.run_id, r.context_id, r.algorithm,
                  r.eligible_source_account_count,
                  r.eligible_source_entity_count, r.eligible_edge_count,
                  r.ranked_node_count, r.completed_at,
                  c.snapshot_id
           FROM ranking_run r
           JOIN analysis_context c ON c.context_id = r.context_id
           WHERE r.algorithm = ?
           ORDER BY r.completed_at DESC, r.run_id DESC
           LIMIT 1""",
        [OVERLAP_ALGORITHM],
    ).fetchone()


@lru_cache(maxsize=32)
def _rankings_payload_cached(
    limit: int,
    state: str,
    query: str,
    version: tuple[str, int, int, int, int],
) -> dict[str, Any]:
    analysis_db = Path(version[0])
    if not analysis_db.is_file():
        return {
            "available": False,
            "reason": "No derived ranking found. Run `fli following-ranking overlap` first.",
        }
    conn = _open_readonly(analysis_db)
    try:
        run = _latest_run(conn)
        if run is None:
            return {
                "available": False,
                "reason": "Analysis store has no entity-overlap ranking.",
            }

        conditions = ["rr.run_id = ?", "gn.registry_state != 'rejected'"]
        params: list[Any] = [run["run_id"]]
        if state in ("active", "unknown"):
            conditions.append("gn.registry_state = ?")
            params.append(state)
        needle = query.strip().lower()
        if needle:
            conditions.append(
                "(lower(gn.handle) LIKE ? OR lower(COALESCE(gn.display_name,'')) LIKE ?"
                " OR lower(COALESCE(gn.entity_name,'')) LIKE ?)"
            )
            like = f"%{needle}%"
            params.extend([like, like, like])

        rows = conn.execute(
            f"""SELECT rr.position AS rank, rr.cohort_follow_count,
                       rr.cohort_follow_share,
                       gn.x_id, gn.handle, gn.display_name, gn.followers_count,
                       gn.registry_state, gn.entity_id, gn.entity_kind,
                       gn.entity_name
                FROM ranking_result rr
                JOIN graph_node gn
                  ON gn.context_id = ? AND gn.x_id = rr.x_id
                WHERE {' AND '.join(conditions)}
                ORDER BY rr.position
                LIMIT ?""",
            [run["context_id"], *params, limit],
        ).fetchall()

        state_counts = {
            r["registry_state"]: r["n"]
            for r in conn.execute(
                """SELECT registry_state, COUNT(*) AS n
                   FROM graph_node
                   WHERE context_id = ?
                   GROUP BY registry_state""",
                [run["context_id"]],
            )
        }

        return {
            "available": True,
            "run": {
                "algorithm": run["algorithm"],
                "snapshot_id": run["snapshot_id"],
                "completed_at": run["completed_at"],
                "source_accounts": run["eligible_source_account_count"],
                "source_entities": run["eligible_source_entity_count"],
                "edges": run["eligible_edge_count"],
                "ranked_accounts": run["ranked_node_count"],
                "active_accounts": state_counts.get("active", 0),
                "unknown_accounts": state_counts.get("unknown", 0),
            },
            "nodes": [dict(r) for r in rows],
        }
    finally:
        conn.close()


def rankings_payload(limit: int, state: str, query: str) -> dict[str, Any]:
    analysis_db = _latest_analysis_db()
    if analysis_db is None:
        return {
            "available": False,
            "reason": "No derived ranking found. Run `fli following-ranking overlap` first.",
        }
    return _rankings_payload_cached(limit, state, query, _db_version(analysis_db))


@lru_cache(maxsize=32)
def _entity_network_ranks_cached(
    version: tuple[str, int, int, int, int],
) -> dict[int, dict[str, Any]]:
    """Tie-aware entity-union support within the active X Registry."""
    analysis_db = Path(version[0])
    if not analysis_db.is_file():
        return {}
    conn = _open_readonly(analysis_db)
    try:
        run = _latest_run(conn)
        if run is None:
            return {}
        rows = conn.execute(
            """SELECT support.entity_id,
                      support.support_rank AS network_rank,
                      support.support_count AS cohort_follow_count,
                      support.support_share AS cohort_follow_share,
                      support.channel_count,
                      run.eligible_source_entity_count AS network_source_total,
                      COUNT(*) OVER () AS network_rank_total
               FROM entity_support_result support
               JOIN ranking_run run ON run.run_id = support.run_id
               WHERE support.run_id = ?
               ORDER BY support.support_rank, support.entity_id""",
            [run["run_id"]],
        ).fetchall()
        return {int(row["entity_id"]): dict(row) for row in rows}
    finally:
        conn.close()


def entity_network_ranks() -> dict[int, dict[str, Any]]:
    """Map each X-addressable entity to union support and Registry rank."""
    analysis_db = _latest_analysis_db()
    if analysis_db is None:
        return {}
    return _entity_network_ranks_cached(_db_version(analysis_db))


@lru_cache(maxsize=32)
def _entity_network_context_cached(
    version: tuple[str, int, int, int, int],
) -> dict[str, Any] | None:
    analysis_db = Path(version[0])
    if not analysis_db.is_file():
        return None
    conn = _open_readonly(analysis_db)
    try:
        run = _latest_run(conn)
        if run is None:
            return None
        ranked_entities = conn.execute(
            "SELECT COUNT(*) FROM entity_support_result WHERE run_id = ?",
            [run["run_id"]],
        ).fetchone()[0]
    finally:
        conn.close()
    snapshot_db = RAW_FOLLOWING_ROOT / run["snapshot_id"] / "snapshot.db"
    snapshot_completed_at = None
    parent_snapshot_id = None
    if snapshot_db.is_file():
        snapshot = _open_readonly(snapshot_db)
        try:
            snapshot_completed_at = snapshot.execute(
                "SELECT completed_at FROM snapshot_run"
            ).fetchone()[0]
            has_lineage = snapshot.execute(
                """SELECT 1 FROM sqlite_master
                   WHERE type = 'table' AND name = 'snapshot_lineage'"""
            ).fetchone()
            if has_lineage:
                parent = snapshot.execute(
                    "SELECT parent_snapshot_id FROM snapshot_lineage LIMIT 1"
                ).fetchone()
                parent_snapshot_id = parent[0] if parent else None
        finally:
            snapshot.close()
    return {
        "snapshot_id": run["snapshot_id"],
        "snapshot_completed_at": snapshot_completed_at,
        "network_source_total": run["eligible_source_entity_count"],
        "network_rank_total": ranked_entities,
        "parent_snapshot_id": parent_snapshot_id,
        "incremental": parent_snapshot_id is not None,
    }


def entity_network_context() -> dict[str, Any] | None:
    """Describe the exact evidence snapshot behind Registry support."""
    analysis_db = _latest_analysis_db()
    if analysis_db is None:
        return None
    return _entity_network_context_cached(_db_version(analysis_db))


@lru_cache(maxsize=128)
def _followers_payload_cached(
    x_id: str,
    limit: int,
    version: tuple[str, int, int, int, int],
) -> dict[str, Any]:
    """Which screened cohort sources follow this account, best-ranked first."""
    analysis_db = Path(version[0])
    if not analysis_db.is_file():
        return {"available": False, "reason": "No derived ranking found."}
    conn = _open_readonly(analysis_db)
    try:
        run = _latest_run(conn)
        if run is None:
            return {
                "available": False,
                "reason": "Analysis store has no entity-overlap ranking.",
            }
        snapshot_db = RAW_FOLLOWING_ROOT / run["snapshot_id"] / "snapshot.db"
        if not snapshot_db.is_file():
            return {
                "available": False,
                "reason": f"Snapshot {run['snapshot_id']} is not present locally.",
            }
        conn.execute(
            "ATTACH DATABASE ? AS snap",
            [f"file:{snapshot_db.as_posix()}?mode=ro"],
        )
        rows = conn.execute(
            """WITH eligible AS (
                   SELECT gn.x_id, gn.handle, gn.display_name, gn.entity_name,
                          gn.entity_id, rr.position AS rank,
                          rr.cohort_follow_count,
                          ROW_NUMBER() OVER (
                              PARTITION BY gn.entity_id
                              ORDER BY rr.position IS NULL, rr.position,
                                       lower(gn.handle), gn.x_id
                          ) AS entity_account_order
                   FROM snap.edge edge
                   JOIN snap.source_fetch source
                     ON source.source_x_id = edge.source_x_id
                    AND source.status = 'complete'
                   JOIN graph_node gn
                     ON gn.context_id = ? AND gn.x_id = edge.source_x_id
                    AND gn.registry_state = 'active'
                    AND gn.entity_id IS NOT NULL
                   LEFT JOIN ranking_result rr
                     ON rr.run_id = ? AND rr.x_id = edge.source_x_id
                   WHERE edge.target_x_id = ?
               )
               SELECT x_id, handle, display_name, entity_name, rank,
                      cohort_follow_count
               FROM eligible
               WHERE entity_account_order = 1
               ORDER BY rank IS NULL, rank, lower(handle), x_id
               LIMIT ?""",
            [run["context_id"], run["run_id"], x_id, limit],
        ).fetchall()
        total = conn.execute(
            """SELECT COUNT(DISTINCT gn.entity_id)
               FROM snap.edge edge
               JOIN snap.source_fetch source
                 ON source.source_x_id = edge.source_x_id
                AND source.status = 'complete'
               JOIN graph_node gn
                 ON gn.context_id = ? AND gn.x_id = edge.source_x_id
                AND gn.registry_state = 'active'
                AND gn.entity_id IS NOT NULL
               WHERE edge.target_x_id = ?""",
            [run["context_id"], x_id],
        ).fetchone()[0]
        return {
            "available": True,
            "x_id": x_id,
            "total": total,
            "followers": [dict(r) for r in rows],
        }
    finally:
        conn.close()


def followers_payload(x_id: str, limit: int) -> dict[str, Any]:
    analysis_db = _latest_analysis_db()
    if analysis_db is None:
        return {"available": False, "reason": "No derived ranking found."}
    return _followers_payload_cached(x_id, limit, _db_version(analysis_db))
