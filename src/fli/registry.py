"""Entity materialization and the lean Registry read model.

Every observed channel belongs to exactly one entity. Known lab channels are
claimed by the seeded lab entity. Any channel that cannot yet be resolved gets
one provisional entity with kind ``unknown``. Structural classification can
promote it to ``person``, ``organization``, or ``unsure``. Registry rejection
is a separate, reason-bearing curation state; it never masquerades as a
structural kind. The curated labs source remains an internal channel seed and
is not part of the Registry kind contract.
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

CREATE TABLE IF NOT EXISTS entity_registry_rejections (
    entity_id INTEGER PRIMARY KEY REFERENCES entities (id) ON DELETE CASCADE,
    reason_code TEXT NOT NULL,
    reason TEXT NOT NULL,
    source TEXT NOT NULL,
    evidence_url TEXT,
    rejected_at TEXT NOT NULL
);
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


def reject_entity(
    conn: sqlite3.Connection,
    *,
    entity_id: int,
    reason_code: str,
    reason: str,
    source: str,
    evidence_url: str | None = None,
    rejected_at: str | None = None,
) -> None:
    """Record a deterministic Registry rejection without changing entity kind."""
    ensure_schema(conn)
    rejected_at = rejected_at or _now()
    conn.execute(
        """INSERT INTO entity_registry_rejections
           (entity_id, reason_code, reason, source, evidence_url, rejected_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT (entity_id) DO UPDATE SET
               reason_code = excluded.reason_code,
               reason = excluded.reason,
               source = excluded.source,
               evidence_url = excluded.evidence_url,
               rejected_at = excluded.rejected_at""",
        (
            entity_id,
            reason_code,
            reason,
            source,
            evidence_url,
            rejected_at,
        ),
    )


def clear_rejection(conn: sqlite3.Connection, *, entity_id: int) -> None:
    """Remove a rejection after a correction or fresh public evidence."""
    ensure_schema(conn)
    conn.execute(
        "DELETE FROM entity_registry_rejections WHERE entity_id = ?",
        (entity_id,),
    )


def merge_entity_into(
    conn: sqlite3.Connection,
    *,
    canonical_entity_id: int,
    duplicate_entity_id: int,
    observed_at: str | None = None,
) -> dict[str, int]:
    """Move every channel to one canonical entity and remove the duplicate.

    Accounts, channel observations, and source facts stay attached to their
    existing account/channel rows. Only the redundant real-world identity is
    removed. Callers must make the ownership decision explicitly.
    """
    ensure_schema(conn)
    if canonical_entity_id == duplicate_entity_id:
        raise ValueError("canonical and duplicate entities must differ")
    canonical = conn.execute(
        "SELECT id, kind FROM entities WHERE id = ?", (canonical_entity_id,)
    ).fetchone()
    duplicate = conn.execute(
        "SELECT id, kind FROM entities WHERE id = ?", (duplicate_entity_id,)
    ).fetchone()
    if canonical is None:
        raise ValueError(f"canonical entity {canonical_entity_id} does not exist")
    if duplicate is None:
        raise ValueError(f"duplicate entity {duplicate_entity_id} does not exist")
    if canonical["kind"] != duplicate["kind"]:
        raise ValueError(
            "entity merge requires matching structural kinds: "
            f"{canonical['kind']} != {duplicate['kind']}"
        )

    observed_at = observed_at or _now()
    moved_channels = conn.execute(
        "SELECT COUNT(*) AS n FROM entity_channels WHERE entity_id = ?",
        (duplicate_entity_id,),
    ).fetchone()["n"]
    conn.execute(
        "UPDATE entity_channels SET entity_id = ? WHERE entity_id = ?",
        (canonical_entity_id, duplicate_entity_id),
    )
    conn.execute(
        "DELETE FROM entities WHERE id = ?", (duplicate_entity_id,)
    )
    conn.execute(
        "UPDATE entities SET updated_at = ? WHERE id = ?",
        (observed_at, canonical_entity_id),
    )
    return {
        "canonical_entity_id": canonical_entity_id,
        "removed_entity_id": duplicate_entity_id,
        "moved_channels": moved_channels,
    }


def read_entities(conn: sqlite3.Connection, *, limit: int = 5000) -> list[dict]:
    """Return identity fields, structural-kind reason, and curation state."""
    ensure_schema(conn)
    has_classifications = bool(
        conn.execute(
            """SELECT 1 FROM sqlite_master
               WHERE type = 'table'
                 AND name = 'entity_kind_classifications'"""
        ).fetchone()
    )
    kind_reason_sql = (
        """(SELECT k.reason FROM entity_kind_classifications k
             WHERE k.entity_id = e.id AND k.classification = e.kind
             ORDER BY k.classified_at DESC, k.run_id DESC
             LIMIT 1)"""
        if has_classifications
        else "NULL"
    )
    rows = conn.execute(
        f"""WITH selected AS (
               SELECT e.id, e.slug, e.kind, e.name
               FROM entities e
               LEFT JOIN entity_registry_rejections rejected
                 ON rejected.entity_id = e.id
               ORDER BY CASE WHEN rejected.entity_id IS NOT NULL THEN 3
                             WHEN e.kind = 'organization' THEN 0
                             WHEN e.kind = 'person' THEN 1
                             WHEN e.kind = 'unsure' THEN 2
                             ELSE 4
                        END,
                        e.name COLLATE NOCASE
               LIMIT ?
           )
           SELECT e.id, e.slug, e.kind, e.name,
                  CASE WHEN rejected.entity_id IS NULL
                       THEN 'active' ELSE 'rejected' END AS registry_state,
                  rejected.reason_code AS rejection_reason_code,
                  rejected.reason AS rejection_reason,
                  rejected.source AS rejection_source,
                  rejected.evidence_url AS rejection_evidence_url,
                  {kind_reason_sql} AS kind_reason,
                  c.id AS channel_id, c.kind AS channel_kind, c.key AS channel_key,
                  c.label AS channel_label, c.url AS channel_url,
                  (SELECT o.value FROM channel_observations o
                   WHERE o.channel_id = c.id
                     AND o.source = 'x_profile' AND o.metric = 'bio'
                   ORDER BY o.observed_at DESC LIMIT 1) AS bio
           FROM selected e
           LEFT JOIN entity_registry_rejections rejected
             ON rejected.entity_id = e.id
           LEFT JOIN entity_channels ec ON ec.entity_id = e.id
           LEFT JOIN channels c ON c.id = ec.channel_id
           ORDER BY CASE WHEN rejected.entity_id IS NOT NULL THEN 3
                         WHEN e.kind = 'organization' THEN 0
                         WHEN e.kind = 'person' THEN 1
                         WHEN e.kind = 'unsure' THEN 2
                         ELSE 4
                    END,
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
                "kind_reason": row["kind_reason"],
                "registry_state": row["registry_state"],
                "rejection_reason_code": row["rejection_reason_code"],
                "rejection_reason": row["rejection_reason"],
                "rejection_source": row["rejection_source"],
                "rejection_evidence_url": row["rejection_evidence_url"],
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
    """Return disjoint Registry-view counts, including rejected entities."""
    ensure_schema(conn)
    counts = {kind: 0 for kind in channels.ENTITY_KINDS}
    counts["rejected"] = 0
    for row in conn.execute(
        """SELECT CASE WHEN rejected.entity_id IS NOT NULL
                        THEN 'rejected' ELSE e.kind END AS registry_kind,
                  COUNT(*) AS n
           FROM entities e
           LEFT JOIN entity_registry_rejections rejected
             ON rejected.entity_id = e.id
           GROUP BY registry_kind"""
    ).fetchall():
        counts[row["registry_kind"]] = row["n"]
    return counts
