"""Entity materialization and the lean Registry read model.

Every observed channel belongs to exactly one entity. Known lab channels are
claimed by the seeded lab entity. Any channel that cannot yet be resolved gets
one provisional entity with kind ``unknown``. Classification and track/reject
curation are intentionally later, separate stages.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import datetime, timezone

from fli import channels

SCHEMA = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_entity_channels_one_owner
ON entity_channels (channel_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_schema(conn: sqlite3.Connection) -> None:
    channels.ensure_schema(conn)
    duplicate = conn.execute(
        """SELECT channel_id, COUNT(DISTINCT entity_id) AS owners
           FROM entity_channels
           GROUP BY channel_id
           HAVING owners > 1
           LIMIT 1"""
    ).fetchone()
    if duplicate:
        raise RuntimeError(
            f"channel {duplicate['channel_id']} belongs to multiple entities"
        )
    conn.executescript(SCHEMA)


def _slug_base(kind: str, key: str) -> str:
    readable = re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")
    if not readable:
        readable = hashlib.sha256(f"{kind}:{key}".encode()).hexdigest()[:12]
    return f"{kind}-{readable[:72]}"


def _available_slug(conn: sqlite3.Connection, *, kind: str, key: str) -> str:
    base = _slug_base(kind, key)
    if not conn.execute("SELECT 1 FROM entities WHERE slug = ?", (base,)).fetchone():
        return base
    digest = hashlib.sha256(f"{kind}:{key}".encode()).hexdigest()[:10]
    return f"{base[:69]}-{digest}"


def claim_channel(
    conn: sqlite3.Connection,
    *,
    entity_id: int,
    channel_id: int,
    relationship: str,
    confidence: float,
    evidence_url: str | None,
    notes: str | None,
    observed_at: str,
) -> None:
    """Give a known entity a channel, replacing only a one-channel unknown."""
    ensure_schema(conn)
    owner = conn.execute(
        """SELECT e.id, e.kind, ec.relationship,
                  (SELECT COUNT(*) FROM entity_channels owned
                   WHERE owned.entity_id = e.id) AS channel_count
           FROM entity_channels ec
           JOIN entities e ON e.id = ec.entity_id
           WHERE ec.channel_id = ?""",
        (channel_id,),
    ).fetchone()
    if owner and owner["id"] == entity_id:
        if owner["relationship"] == relationship:
            channels.link_entity_channel(
                conn,
                entity_id=entity_id,
                channel_id=channel_id,
                relationship=relationship,
                confidence=confidence,
                evidence_url=evidence_url,
                notes=notes,
                observed_at=observed_at,
            )
            return
        conn.execute(
            """UPDATE entity_channels
               SET relationship = ?, confidence = ?,
                   evidence_url = COALESCE(?, evidence_url),
                   notes = COALESCE(?, notes)
               WHERE entity_id = ? AND channel_id = ?
                 AND (relationship IS NOT ?
                      OR confidence IS NOT ?
                      OR COALESCE(evidence_url, '') IS NOT COALESCE(?, evidence_url, '')
                      OR COALESCE(notes, '') IS NOT COALESCE(?, notes, ''))""",
            (
                relationship,
                confidence,
                evidence_url,
                notes,
                entity_id,
                channel_id,
                relationship,
                confidence,
                evidence_url,
                notes,
            ),
        )
        return
    if owner:
        if owner["kind"] != "unknown" or owner["channel_count"] != 1:
            raise ValueError(
                f"channel {channel_id} already belongs to resolved entity {owner['id']}"
            )
        conn.execute(
            "DELETE FROM entity_channels WHERE entity_id = ?", (owner["id"],)
        )
        conn.execute("DELETE FROM entities WHERE id = ?", (owner["id"],))
    channels.link_entity_channel(
        conn,
        entity_id=entity_id,
        channel_id=channel_id,
        relationship=relationship,
        confidence=confidence,
        evidence_url=evidence_url,
        notes=notes,
        observed_at=observed_at,
    )


def materialize_unlinked_channels(
    conn: sqlite3.Connection,
    *,
    observed_at: str | None = None,
) -> dict[str, int]:
    """Create one provisional ``unknown`` entity for every unowned channel."""
    ensure_schema(conn)
    observed_at = observed_at or _now()
    unlinked = conn.execute(
        """SELECT c.*
           FROM channels c
           WHERE NOT EXISTS (
               SELECT 1 FROM entity_channels ec WHERE ec.channel_id = c.id
           )
           ORDER BY c.id"""
    ).fetchall()
    for channel in unlinked:
        label = channel["label"]
        name = label or (f"@{channel['key']}" if channel["kind"] == "x" else channel["key"])
        entity_id = channels.upsert_entity(
            conn,
            kind="unknown",
            slug=_available_slug(conn, kind=channel["kind"], key=channel["key"]),
            name=name,
            observed_at=observed_at,
        )
        channels.link_entity_channel(
            conn,
            entity_id=entity_id,
            channel_id=channel["id"],
            relationship="identity",
            confidence=1.0,
            evidence_url=channel["url"],
            notes="Provisional entity created from its first observed channel.",
            observed_at=observed_at,
        )
    conn.commit()
    return {
        "created_entities": len(unlinked),
        "entities": conn.execute("SELECT COUNT(*) AS n FROM entities").fetchone()["n"],
        "unknown_entities": conn.execute(
            "SELECT COUNT(*) AS n FROM entities WHERE kind = 'unknown'"
        ).fetchone()["n"],
        "unlinked_channels": conn.execute(
            """SELECT COUNT(*) AS n FROM channels c
               WHERE NOT EXISTS (
                   SELECT 1 FROM entity_channels ec WHERE ec.channel_id = c.id
               )"""
        ).fetchone()["n"],
    }


def read_entities(conn: sqlite3.Connection, *, limit: int = 5000) -> list[dict]:
    """Return only identity-bearing fields for the Registry UI."""
    ensure_schema(conn)
    rows = conn.execute(
        """WITH selected AS (
               SELECT id, slug, kind, name
               FROM entities
               ORDER BY CASE kind WHEN 'lab' THEN 0 WHEN 'person' THEN 1 ELSE 2 END,
                        name COLLATE NOCASE
               LIMIT ?
           )
           SELECT e.id, e.slug, e.kind, e.name,
                  c.id AS channel_id, c.kind AS channel_kind, c.key AS channel_key,
                  c.label AS channel_label, c.url AS channel_url,
                  (SELECT o.value FROM channel_observations o
                   WHERE o.channel_id = c.id
                     AND o.source = 'x_profile' AND o.metric = 'bio'
                   ORDER BY o.observed_at DESC LIMIT 1) AS bio
           FROM selected e
           LEFT JOIN entity_channels ec ON ec.entity_id = e.id
           LEFT JOIN channels c ON c.id = ec.channel_id
           ORDER BY CASE e.kind WHEN 'lab' THEN 0 WHEN 'person' THEN 1 ELSE 2 END,
                    e.name COLLATE NOCASE, c.kind, c.key""",
        (limit,),
    ).fetchall()
    grouped: dict[int, dict] = {}
    for row in rows:
        entity = grouped.setdefault(
            row["id"],
            {
                "id": row["id"],
                "slug": row["slug"],
                "kind": row["kind"],
                "name": row["name"],
                "bio": None,
                "channels": [],
            },
        )
        if row["bio"] and not entity["bio"]:
            entity["bio"] = row["bio"]
        if row["channel_id"] is not None:
            entity["channels"].append(
                {
                    "id": row["channel_id"],
                    "kind": row["channel_kind"],
                    "key": row["channel_key"],
                    "label": row["channel_label"],
                    "url": row["channel_url"],
                }
            )
    return list(grouped.values())


def kind_counts(conn: sqlite3.Connection) -> dict[str, int]:
    ensure_schema(conn)
    counts = {kind: 0 for kind in channels.ENTITY_KINDS}
    for row in conn.execute(
        "SELECT kind, COUNT(*) AS n FROM entities GROUP BY kind"
    ).fetchall():
        counts[row["kind"]] = row["n"]
    return counts
