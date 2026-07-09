"""Modeled graph import layer: X accounts, source facts, and directed edges.

Normalizes the redundant raw Digg CSVs (where every edge row repeats both
endpoint profiles) into three tables:

- accounts:             one row per platform account (node)
- account_source_facts: per-source observations about an account (rank, role,
                        bio, github_url, ...) — one row per (account, source)
- graph_edges:          directed observed relationships (edge), pointing at
                        accounts by id, with evidence URL

Raw files stay as evidence; this layer is rebuildable from them at any time
(`fli graph load` is idempotent: it wipes and reloads digg-sourced rows).
The product model now lives in `fli.channels`: entities, channels,
entity_channels, and channel_observations. This module remains the legacy
X-graph import backing layer so the Digg/PageRank pull stays reproducible.
"""

import csv
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from fli import store

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY,
    platform TEXT NOT NULL,            -- 'x' for now
    handle TEXT NOT NULL,              -- lowercased platform handle
    display_name TEXT,
    x_id TEXT,
    bio TEXT,
    followers_count INTEGER,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    UNIQUE (platform, handle)
);
CREATE INDEX IF NOT EXISTS idx_accounts_x_id ON accounts (platform, x_id);

CREATE TABLE IF NOT EXISTS account_source_facts (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts (id),
    source TEXT NOT NULL,              -- 'digg' | 'smol_ai' | ...
    fact TEXT NOT NULL,                -- 'rank' | 'role' | 'cohort' | 'github_url' | 'list_member' | ...
    value TEXT,
    observed_at TEXT NOT NULL,
    evidence_url TEXT,
    UNIQUE (account_id, source, fact)
);
CREATE INDEX IF NOT EXISTS idx_facts_source_fact ON account_source_facts (source, fact);

CREATE TABLE IF NOT EXISTS graph_edges (
    id INTEGER PRIMARY KEY,
    from_account_id INTEGER NOT NULL REFERENCES accounts (id),
    to_account_id INTEGER NOT NULL REFERENCES accounts (id),
    relationship TEXT NOT NULL,        -- 'top_follower_of'
    source TEXT NOT NULL,              -- 'digg'
    observed_at TEXT NOT NULL,
    evidence_url TEXT,
    UNIQUE (from_account_id, to_account_id, relationship, source)
);
CREATE INDEX IF NOT EXISTS idx_edges_from ON graph_edges (from_account_id, relationship);
CREATE INDEX IF NOT EXISTS idx_edges_to ON graph_edges (to_account_id, relationship);
"""

DEFAULT_RAW_DIR = Path("data/raw/digg-full-2026-07-08")


def connect(db_path: Path | str = store.DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = store.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class _AccountCache:
    """Upsert accounts by (platform, handle), keeping richer values."""

    def __init__(self, conn: sqlite3.Connection, observed_at: str):
        self.conn = conn
        self.observed_at = observed_at
        self.ids: dict[str, int] = {}

    def upsert(
        self,
        handle: str,
        *,
        display_name: str | None = None,
        x_id: str | None = None,
        bio: str | None = None,
        followers_count: int | None = None,
    ) -> int:
        handle = handle.strip().lower()
        if handle in self.ids:
            account_id = self.ids[handle]
            self.conn.execute(
                """UPDATE accounts SET
                       display_name = COALESCE(?, display_name),
                       x_id = COALESCE(?, x_id),
                       bio = COALESCE(?, bio),
                       followers_count = COALESCE(?, followers_count),
                       last_seen_at = ?
                   WHERE id = ?""",
                (display_name, x_id, bio, followers_count, self.observed_at, account_id),
            )
            return account_id
        row = self.conn.execute(
            "SELECT id FROM accounts WHERE platform = 'x' AND handle = ?", (handle,)
        ).fetchone()
        if row:
            account_id = row["id"]
            self.conn.execute(
                """UPDATE accounts SET
                       display_name = COALESCE(?, display_name),
                       x_id = COALESCE(?, x_id),
                       bio = COALESCE(?, bio),
                       followers_count = COALESCE(?, followers_count),
                       last_seen_at = ?
                   WHERE id = ?""",
                (display_name, x_id, bio, followers_count, self.observed_at, account_id),
            )
        else:
            cur = self.conn.execute(
                """INSERT INTO accounts
                   (platform, handle, display_name, x_id, bio, followers_count,
                    first_seen_at, last_seen_at)
                   VALUES ('x', ?, ?, ?, ?, ?, ?, ?)""",
                (handle, display_name, x_id, bio, followers_count,
                 self.observed_at, self.observed_at),
            )
            account_id = cur.lastrowid
        self.ids[handle] = account_id
        return account_id


def load_digg(
    conn: sqlite3.Connection,
    raw_dir: Path = DEFAULT_RAW_DIR,
    observed_at: str | None = None,
) -> dict[str, int]:
    """Wipe and reload all digg-sourced modeled rows from the raw CSVs."""
    observed_at = observed_at or _now()
    rankings_csv = raw_dir / "rankings.csv"
    edges_csv = raw_dir / "top_follower_edges.csv"
    if not rankings_csv.exists() or not edges_csv.exists():
        raise FileNotFoundError(f"expected rankings.csv and top_follower_edges.csv in {raw_dir}")

    conn.execute("DELETE FROM graph_edges WHERE source = 'digg'")
    conn.execute("DELETE FROM account_source_facts WHERE source = 'digg'")

    cache = _AccountCache(conn, observed_at)
    n_facts = 0

    with rankings_csv.open() as f:
        for row in csv.DictReader(f):
            account_id = cache.upsert(
                row["username"],
                display_name=row.get("display_name") or None,
                x_id=row.get("x_id") or None,
                bio=row.get("bio") or None,
                followers_count=int(row["followers_count"]) if row.get("followers_count") else None,
            )
            facts = {
                "rank": row.get("rank"),
                "role": row.get("role"),
                "cohort": row.get("cohort"),
                "score": row.get("score"),
                "tech_ranked_followers": row.get("tech_ranked_followers"),
                "github_url": row.get("github_url"),
                "category_rank": row.get("category_rank"),
            }
            for fact, value in facts.items():
                if value:
                    conn.execute(
                        """INSERT OR REPLACE INTO account_source_facts
                           (account_id, source, fact, value, observed_at, evidence_url)
                           VALUES (?, 'digg', ?, ?, ?, ?)""",
                        (account_id, fact, value, observed_at, row.get("digg_url")),
                    )
                    n_facts += 1

    n_edges = 0
    with edges_csv.open() as f:
        for row in csv.DictReader(f):
            from_id = cache.upsert(
                row["from_username"],
                display_name=row.get("from_display_name") or None,
                x_id=row.get("from_x_id") or None,
                followers_count=int(row["from_followers_count"]) if row.get("from_followers_count") else None,
            )
            to_id = cache.upsert(
                row["to_username"],
                display_name=row.get("to_display_name") or None,
                x_id=row.get("to_x_id") or None,
            )
            conn.execute(
                """INSERT OR IGNORE INTO graph_edges
                   (from_account_id, to_account_id, relationship, source,
                    observed_at, evidence_url)
                   VALUES (?, ?, 'top_follower_of', 'digg', ?, ?)""",
                (from_id, to_id, observed_at, row.get("evidence_url")),
            )
            n_edges += 1

    conn.commit()
    from fli import channels

    channels.sync_all(conn)
    return {
        "accounts": conn.execute("SELECT COUNT(*) AS n FROM accounts").fetchone()["n"],
        "facts": n_facts,
        "edges": conn.execute(
            "SELECT COUNT(*) AS n FROM graph_edges WHERE source = 'digg'"
        ).fetchone()["n"],
    }


def compute_pagerank(
    conn: sqlite3.Connection,
    damping: float = 0.85,
    max_iter: int = 100,
    tol: float = 1e-10,
) -> dict[str, int]:
    """PageRank over the follow graph, stored as a second attention signal.

    Edges mean "from is a top follower of to", so rank flows along the edge:
    being followed by accounts that are themselves heavily followed is worth
    more than raw follower count. Independent of Digg's own rank — where the
    two signals disagree, that account deserves human review.

    Pure-Python power iteration; 361K edges over ~2.3K nodes converges in
    well under a second. Dangling nodes (no out-edges) redistribute uniformly.
    """
    edges = conn.execute(
        "SELECT from_account_id, to_account_id FROM graph_edges"
    ).fetchall()
    nodes: set[int] = set()
    out_links: dict[int, list[int]] = {}
    for e in edges:
        nodes.add(e["from_account_id"])
        nodes.add(e["to_account_id"])
        out_links.setdefault(e["from_account_id"], []).append(e["to_account_id"])

    n = len(nodes)
    if n == 0:
        return {"nodes": 0, "iterations": 0}
    rank = {node: 1.0 / n for node in nodes}
    iterations = 0
    for iterations in range(1, max_iter + 1):
        dangling = sum(rank[node] for node in nodes if node not in out_links)
        base = (1.0 - damping) / n + damping * dangling / n
        new_rank = {node: base for node in nodes}
        for node, targets in out_links.items():
            share = damping * rank[node] / len(targets)
            for target in targets:
                new_rank[target] += share
        delta = sum(abs(new_rank[node] - rank[node]) for node in nodes)
        rank = new_rank
        if delta < tol:
            break

    observed_at = _now()
    conn.execute("DELETE FROM account_source_facts WHERE source = 'graph'")
    ordered = sorted(rank.items(), key=lambda kv: kv[1], reverse=True)
    for position, (account_id, value) in enumerate(ordered, start=1):
        for fact, val in (("pagerank", f"{value:.10f}"), ("pagerank_rank", str(position))):
            conn.execute(
                """INSERT OR REPLACE INTO account_source_facts
                   (account_id, source, fact, value, observed_at, evidence_url)
                   VALUES (?, 'graph', ?, ?, ?, NULL)""",
                (account_id, fact, val, observed_at),
            )
    conn.commit()
    from fli import channels

    channels.sync_all(conn)
    return {"nodes": n, "iterations": iterations}


def summary(conn: sqlite3.Connection) -> list[str]:
    lines = []
    for table in ("accounts", "account_source_facts", "graph_edges"):
        n = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
        lines.append(f"{table}: {n}")
    top = conn.execute(
        """SELECT a.handle, COUNT(*) AS n FROM graph_edges e
           JOIN accounts a ON a.id = e.to_account_id
           GROUP BY e.to_account_id ORDER BY n DESC LIMIT 5"""
    ).fetchall()
    lines.append("most-followed targets: " + ", ".join(f"{r['handle']}({r['n']})" for r in top))
    return lines


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="fli graph")
    parser.add_argument("action", choices=["load", "summary", "pagerank"])
    parser.add_argument("--db", default=None)
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    args = parser.parse_args(argv)

    conn = connect(args.db) if args.db else connect()
    if args.action == "load":
        counts = load_digg(conn, Path(args.raw_dir))
        for k, v in counts.items():
            print(f"{k}: {v}")
    if args.action == "pagerank":
        result = compute_pagerank(conn)
        print(f"pagerank: {result['nodes']} nodes, converged in {result['iterations']} iterations")
        top = conn.execute(
            """SELECT a.handle, f.value FROM account_source_facts f
               JOIN accounts a ON a.id = f.account_id
               WHERE f.source = 'graph' AND f.fact = 'pagerank_rank'
               ORDER BY CAST(f.value AS INTEGER) LIMIT 10"""
        ).fetchall()
        print("top 10: " + ", ".join(f"{r['handle']}(#{r['value']})" for r in top))
    for line in summary(conn):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
