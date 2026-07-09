"""SQLite storage.

Data-first approach: a raw layer (`raw_items`) that stores fetched payloads
as-is, with no claims about their shape. The modeled schema (entities,
insights, scores) gets designed later, from evidence in this layer.
Raw is immutable and append-only; dedup is by (source, external_id).
"""

import json
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("data/fli.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_items (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,          -- 'blog' | 'arxiv' | 'github'
    lab TEXT NOT NULL,             -- lab slug the fetch ran for
    external_id TEXT NOT NULL,     -- URL or source-native id, for dedup
    fetched_at TEXT NOT NULL,      -- ISO timestamp
    payload TEXT NOT NULL,         -- JSON, as close to as-fetched as possible
    UNIQUE (source, external_id)
);
"""


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def insert_raw(
    conn: sqlite3.Connection,
    *,
    source: str,
    lab: str,
    external_id: str,
    fetched_at: str,
    payload: dict,
) -> bool:
    """Insert one raw item. Returns False if already present (deduped)."""
    try:
        conn.execute(
            "INSERT INTO raw_items (source, lab, external_id, fetched_at, payload)"
            " VALUES (?, ?, ?, ?, ?)",
            (source, lab, external_id, fetched_at, json.dumps(payload)),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def raw_counts(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT lab, source, COUNT(*) AS n FROM raw_items"
        " GROUP BY lab, source ORDER BY lab, source"
    ).fetchall()
