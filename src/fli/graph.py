"""SQLite backing schema for X accounts and observed source relationships.

Digg rankings are retained only as an offline comparison artifact. This module
does not import Digg edges or compute rankings; the trusted-following project
will introduce an isolated, provenance-complete snapshot and ranking boundary.
"""

import sqlite3
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
    source TEXT NOT NULL,              -- 'smol_ai' | 'ai_high_signal' | ...
    fact TEXT NOT NULL,                -- 'list_member' | 'followed_by' | ...
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
    relationship TEXT NOT NULL,        -- 'follows'
    source TEXT NOT NULL,              -- one observed following source
    observed_at TEXT NOT NULL,
    evidence_url TEXT,
    UNIQUE (from_account_id, to_account_id, relationship, source)
);
CREATE INDEX IF NOT EXISTS idx_edges_from ON graph_edges (from_account_id, relationship);
CREATE INDEX IF NOT EXISTS idx_edges_to ON graph_edges (to_account_id, relationship);
"""

def connect(db_path: Path | str = store.DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = store.connect(db_path)
    conn.executescript(SCHEMA)
    return conn
