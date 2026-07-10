"""Entity/channel model.

Simple mental model:

- entities: observed identities (`person`, `organization`, `unsure`, or
  unresolved `unknown`); lab membership comes from the curated `labs` table
- channels: where we observe them (X, GitHub, blog, arXiv, website)
- entity_channels: evidence that a channel belongs to an entity
- channel_observations: measured facts about a channel at a time

The legacy `accounts` table remains the X graph import backing table for now.
This module mirrors those rows into canonical `channels` so product/API code
can move to the source-agnostic model without rewriting the graph loader first.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fli import store

ENTITY_KINDS = frozenset({"person", "organization", "unsure", "unknown"})

SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,                -- person | organization | unsure | unknown
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entities_kind ON entities (kind);

CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,                -- 'x' | 'github' | 'blog' | 'website'
    key TEXT NOT NULL,                 -- normalized handle/url/query
    label TEXT,
    url TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    UNIQUE (kind, key)
);
CREATE INDEX IF NOT EXISTS idx_channels_kind ON channels (kind, key);

CREATE TABLE IF NOT EXISTS entity_channels (
    entity_id INTEGER NOT NULL REFERENCES entities (id) ON DELETE CASCADE,
    channel_id INTEGER NOT NULL REFERENCES channels (id) ON DELETE CASCADE,
    relationship TEXT NOT NULL,        -- 'official' | 'identity' | 'candidate'
    confidence REAL NOT NULL DEFAULT 1.0,
    evidence_url TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (entity_id, channel_id, relationship)
);
CREATE INDEX IF NOT EXISTS idx_entity_channels_channel ON entity_channels (channel_id);

CREATE TABLE IF NOT EXISTS channel_observations (
    id INTEGER PRIMARY KEY,
    channel_id INTEGER NOT NULL REFERENCES channels (id) ON DELETE CASCADE,
    source TEXT NOT NULL,              -- 'digg_bootstrap' | 'x_profile' | ...
    metric TEXT NOT NULL,              -- 'candidate_origin' | 'followers_count' | ...
    value TEXT,
    observed_at TEXT NOT NULL,
    evidence_url TEXT,
    UNIQUE (channel_id, source, metric, observed_at)
);
CREATE INDEX IF NOT EXISTS idx_channel_obs_lookup
ON channel_observations (channel_id, source, metric, observed_at);
CREATE INDEX IF NOT EXISTS idx_channel_obs_metric
ON channel_observations (source, metric);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db_path: Path | str = store.DEFAULT_DB_PATH) -> sqlite3.Connection:
    from fli import graph

    conn = graph.connect(db_path)
    ensure_schema(conn)
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    _migrate_entities_drop_status(conn)
    _migrate_entity_kinds(conn)


def _migrate_entity_kinds(conn: sqlite3.Connection) -> None:
    if conn.execute(
        "SELECT 1 FROM entities WHERE kind = 'lab' LIMIT 1"
    ).fetchone():
        conn.execute(
            """UPDATE entities
               SET kind = 'organization'
               WHERE kind = 'lab'"""
        )


def _migrate_entities_drop_status(conn: sqlite3.Connection) -> None:
    columns = [
        row["name"]
        for row in conn.execute("PRAGMA table_info(entities)").fetchall()
    ]
    if "status" not in columns:
        return
    conn.execute("DROP INDEX IF EXISTS idx_entities_kind")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS entities_new (
               id INTEGER PRIMARY KEY,
               kind TEXT NOT NULL,
               slug TEXT NOT NULL UNIQUE,
               name TEXT NOT NULL,
               notes TEXT,
               created_at TEXT NOT NULL,
               updated_at TEXT NOT NULL
           )"""
    )
    conn.execute(
        """INSERT OR REPLACE INTO entities_new
           (id, kind, slug, name, notes, created_at, updated_at)
           SELECT id, kind, slug, name, notes, created_at, updated_at
           FROM entities"""
    )
    conn.execute("DROP TABLE entities")
    conn.execute("ALTER TABLE entities_new RENAME TO entities")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_kind ON entities (kind)")


def _channel_key(kind: str, value: str) -> str:
    value = value.strip()
    if kind in {"x", "github"}:
        return value.removeprefix("@").removeprefix("https://github.com/").lower()
    return value


def _channel_url(kind: str, key: str) -> str | None:
    if kind == "x":
        return f"https://x.com/{key}"
    if kind == "github":
        return f"https://github.com/{key}"
    if kind in {"blog", "website"}:
        return key
    return None


def upsert_entity(
    conn: sqlite3.Connection,
    *,
    kind: str,
    slug: str,
    name: str,
    notes: str | None = None,
    observed_at: str | None = None,
) -> int:
    if kind not in ENTITY_KINDS:
        raise ValueError(f"unsupported entity kind: {kind}")
    ensure_schema(conn)
    observed_at = observed_at or _now()
    row = conn.execute("SELECT * FROM entities WHERE slug = ?", (slug,)).fetchone()
    if row:
        entity_id = row["id"]
        if (
            row["kind"] != kind
            or row["name"] != name
            or row["notes"] != notes
        ):
            conn.execute(
                """UPDATE entities SET
                       kind = ?, name = ?, notes = ?, updated_at = ?
                   WHERE id = ?""",
                (kind, name, notes, observed_at, entity_id),
            )
        return entity_id
    cur = conn.execute(
        """INSERT INTO entities
           (kind, slug, name, notes, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (kind, slug, name, notes, observed_at, observed_at),
    )
    return cur.lastrowid


def upsert_channel(
    conn: sqlite3.Connection,
    *,
    kind: str,
    key: str,
    label: str | None = None,
    url: str | None = None,
    observed_at: str | None = None,
) -> int:
    ensure_schema(conn)
    observed_at = observed_at or _now()
    key = _channel_key(kind, key)
    url = url or _channel_url(kind, key)
    row = conn.execute(
        "SELECT * FROM channels WHERE kind = ? AND key = ?", (kind, key)
    ).fetchone()
    if row:
        channel_id = row["id"]
        next_label = label or row["label"]
        next_url = url or row["url"]
        next_seen = max(row["last_seen_at"], observed_at)
        if (
            row["label"] != next_label
            or row["url"] != next_url
            or row["last_seen_at"] != next_seen
        ):
            conn.execute(
                """UPDATE channels SET
                       label = ?,
                       url = ?,
                       last_seen_at = ?
                   WHERE id = ?""",
                (next_label, next_url, next_seen, channel_id),
            )
        return channel_id
    cur = conn.execute(
        """INSERT INTO channels
           (kind, key, label, url, first_seen_at, last_seen_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (kind, key, label, url, observed_at, observed_at),
    )
    return cur.lastrowid


def link_entity_channel(
    conn: sqlite3.Connection,
    *,
    entity_id: int,
    channel_id: int,
    relationship: str,
    confidence: float = 1.0,
    evidence_url: str | None = None,
    notes: str | None = None,
    observed_at: str | None = None,
) -> None:
    observed_at = observed_at or _now()
    conn.execute(
        """INSERT INTO entity_channels
           (entity_id, channel_id, relationship, confidence, evidence_url, notes, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT (entity_id, channel_id, relationship) DO UPDATE SET
               confidence = excluded.confidence,
               evidence_url = COALESCE(excluded.evidence_url, entity_channels.evidence_url),
               notes = COALESCE(excluded.notes, entity_channels.notes)
           WHERE entity_channels.confidence IS NOT excluded.confidence
              OR COALESCE(entity_channels.evidence_url, '') IS NOT COALESCE(excluded.evidence_url, entity_channels.evidence_url, '')
              OR COALESCE(entity_channels.notes, '') IS NOT COALESCE(excluded.notes, entity_channels.notes, '')""",
        (entity_id, channel_id, relationship, confidence, evidence_url, notes, observed_at),
    )


def observe_channel(
    conn: sqlite3.Connection,
    *,
    channel_id: int,
    source: str,
    metric: str,
    value: str | int | float | None,
    observed_at: str,
    evidence_url: str | None = None,
) -> None:
    if value is None:
        return
    conn.execute(
        """INSERT INTO channel_observations
           (channel_id, source, metric, value, observed_at, evidence_url)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT (channel_id, source, metric, observed_at) DO UPDATE SET
               value = excluded.value,
               evidence_url = COALESCE(excluded.evidence_url, channel_observations.evidence_url)
           WHERE channel_observations.value IS NOT excluded.value
              OR COALESCE(channel_observations.evidence_url, '') IS NOT COALESCE(excluded.evidence_url, channel_observations.evidence_url, '')""",
        (channel_id, source, metric, str(value), observed_at, evidence_url),
    )


def sync_x_channels_from_accounts(conn: sqlite3.Connection) -> dict[str, int]:
    """Mirror evidenced X accounts into canonical channels/observations.

    A legacy account with no source facts may exist only to anchor graph edges
    (for example the owner of an imported following snapshot). Keep that node
    in the graph, but do not materialize it as a public Registry channel.
    """
    ensure_schema(conn)
    accounts = conn.execute(
        """SELECT id, handle, display_name, bio, followers_count, first_seen_at, last_seen_at
           FROM accounts a
           WHERE EXISTS (
               SELECT 1 FROM account_source_facts f WHERE f.account_id = a.id
           )"""
    ).fetchall()
    by_account_id: dict[int, int] = {}
    for account in accounts:
        channel_id = upsert_channel(
            conn,
            kind="x",
            key=account["handle"],
            label=account["display_name"],
            observed_at=account["last_seen_at"],
        )
        by_account_id[account["id"]] = channel_id
        observe_channel(
            conn,
            channel_id=channel_id,
            source="x_profile",
            metric="followers_count",
            value=account["followers_count"],
            observed_at=account["last_seen_at"],
            evidence_url=f"https://x.com/{account['handle']}",
        )
        observe_channel(
            conn,
            channel_id=channel_id,
            source="x_profile",
            metric="bio",
            value=account["bio"],
            observed_at=account["last_seen_at"],
            evidence_url=f"https://x.com/{account['handle']}",
        )

    facts = conn.execute(
        """SELECT account_id, source, fact, value, observed_at, evidence_url
           FROM account_source_facts"""
    ).fetchall()
    for fact in facts:
        channel_id = by_account_id.get(fact["account_id"])
        if channel_id is None:
            continue
        observe_channel(
            conn,
            channel_id=channel_id,
            source=fact["source"],
            metric=fact["fact"],
            value=fact["value"],
            observed_at=fact["observed_at"],
            evidence_url=fact["evidence_url"],
        )

    conn.commit()
    return {
        "x_channels": conn.execute(
            "SELECT COUNT(*) AS n FROM channels WHERE kind = 'x'"
        ).fetchone()["n"],
        "observations": conn.execute(
            "SELECT COUNT(*) AS n FROM channel_observations"
        ).fetchone()["n"],
    }


def seed_lab_entities(conn: sqlite3.Connection) -> dict[str, int]:
    """Create lab entities and official channels from the `labs` seed table."""
    ensure_schema(conn)
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'labs'"
    ).fetchone():
        return {
            "entities": conn.execute(
                "SELECT COUNT(*) AS n FROM entities"
            ).fetchone()["n"],
            "linked_channels": conn.execute(
                "SELECT COUNT(*) AS n FROM entity_channels"
            ).fetchone()["n"],
        }
    rows = conn.execute("SELECT * FROM labs ORDER BY slug").fetchall()
    for lab in rows:
        observed_at = lab["seeded_at"]
        entity_id = upsert_entity(
            conn,
            kind="organization",
            slug=lab["slug"],
            name=lab["name"],
            notes=lab["notes"],
            observed_at=observed_at,
        )
        channel_specs = []
        if lab["x_handle"]:
            channel_specs.append(("x", lab["x_handle"], None, "official X account"))
        if lab["blog_feed"]:
            channel_specs.append(("blog", lab["blog_feed"], "Blog feed", "official blog/feed"))
        if lab["github_org"]:
            channel_specs.append(("github", lab["github_org"], lab["github_org"], "official GitHub org"))
        if lab["website"]:
            channel_specs.append(("website", lab["website"], "Website", "official website"))

        for kind, key, label, notes in channel_specs:
            channel_id = upsert_channel(
                conn, kind=kind, key=key, label=label, observed_at=observed_at
            )
            from fli import registry

            registry.claim_channel(
                conn,
                entity_id=entity_id,
                channel_id=channel_id,
                relationship="official",
                confidence=1.0,
                evidence_url=_channel_url(kind, _channel_key(kind, key)),
                notes=notes,
                observed_at=observed_at,
            )

    conn.commit()
    return {
        "entities": conn.execute(
            "SELECT COUNT(*) AS n FROM entities"
        ).fetchone()["n"],
        "linked_channels": conn.execute(
            "SELECT COUNT(*) AS n FROM entity_channels"
        ).fetchone()["n"],
    }


def sync_all(conn: sqlite3.Connection) -> dict[str, int]:
    """Sync all currently available legacy/model data into the channel model."""
    ensure_schema(conn)
    x_counts = sync_x_channels_from_accounts(conn)
    lab_counts = seed_lab_entities(conn)
    from fli import registry

    registry_counts = registry.materialize_unlinked_channels(conn)
    return {**x_counts, **lab_counts, **registry_counts}


def summary(conn: sqlite3.Connection) -> list[str]:
    ensure_schema(conn)
    rows = conn.execute(
        """SELECT kind, COUNT(*) AS n FROM channels GROUP BY kind ORDER BY kind"""
    ).fetchall()
    lines = ["channels:"]
    lines.extend(f"  {row['kind']:8s} {row['n']}" for row in rows)
    entity_rows = conn.execute(
        """SELECT kind, COUNT(*) AS n
           FROM entities GROUP BY kind ORDER BY kind"""
    ).fetchall()
    lines.append("entities:")
    lines.extend(
        f"  {row['kind']:8s} {row['n']}" for row in entity_rows
    )
    observations = conn.execute(
        "SELECT COUNT(*) AS n FROM channel_observations"
    ).fetchone()["n"]
    lines.append(f"observations: {observations}")
    return lines


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="fli channels")
    parser.add_argument("action", choices=["sync", "summary"])
    parser.add_argument("--db", default=None)
    args = parser.parse_args(argv)

    conn = connect(args.db) if args.db else connect()
    if args.action == "sync":
        counts = sync_all(conn)
        print(
            "x_channels: {x_channels}, entities: {entities}, "
            "unknown_entities: {unknown_entities}, unlinked_channels: {unlinked_channels}, "
            "observations: {observations}".format(**counts)
        )
    for line in summary(conn):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
