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

import csv
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

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

CREATE TABLE IF NOT EXISTS entity_merge_audit (
    id INTEGER PRIMARY KEY,
    canonical_entity_id INTEGER NOT NULL REFERENCES entities (id),
    removed_entity_id INTEGER NOT NULL,
    removed_slug TEXT NOT NULL,
    removed_name TEXT NOT NULL,
    removed_kind TEXT NOT NULL,
    reason TEXT NOT NULL,
    source TEXT NOT NULL,
    evidence_url TEXT NOT NULL,
    merged_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entity_merge_audit_canonical
ON entity_merge_audit (canonical_entity_id, merged_at);
"""

DEFAULT_ORGANIZATION_GROUPS_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "registry"
    / "organization-groups.json"
)
DEFAULT_RELEVANCE_REMOVALS_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "registry"
    / "relevance-removals.csv"
)


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
    reason: str | None = None,
    source: str | None = None,
    evidence_url: str | None = None,
) -> dict[str, int]:
    """Move every channel to one canonical entity and remove the duplicate.

    Accounts, channel observations, and source facts stay attached to their
    existing account/channel rows. Only the redundant real-world identity is
    removed. Callers must make the ownership decision explicitly.
    """
    if canonical_entity_id == duplicate_entity_id:
        raise ValueError("canonical and duplicate entities must differ")
    canonical = conn.execute(
        "SELECT id, kind, slug, name FROM entities WHERE id = ?",
        (canonical_entity_id,),
    ).fetchone()
    duplicate = conn.execute(
        "SELECT id, kind, slug, name FROM entities WHERE id = ?",
        (duplicate_entity_id,),
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

    audit_values = (reason, source, evidence_url)
    if any(value is not None for value in audit_values) and not all(audit_values):
        raise ValueError(
            "reason, source, and evidence_url must be supplied together"
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
    if reason is not None and source is not None and evidence_url is not None:
        conn.execute(
            """INSERT INTO entity_merge_audit
               (canonical_entity_id, removed_entity_id, removed_slug,
                removed_name, removed_kind, reason, source, evidence_url,
                merged_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                canonical_entity_id,
                duplicate["id"],
                duplicate["slug"],
                duplicate["name"],
                duplicate["kind"],
                reason,
                source,
                evidence_url,
                observed_at,
            ),
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


def load_organization_groups(path: Path | str) -> list[dict]:
    groups = json.loads(Path(path).read_text())
    if not isinstance(groups, list):
        raise ValueError("organization groups manifest must be a JSON list")
    canonical_handles: set[str] = set()
    member_handles: set[str] = set()
    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            raise ValueError(f"organization group {index} must be an object")
        canonical = group.get("canonical_handle")
        members = group.get("member_handles")
        reason = group.get("reason")
        evidence_url = group.get("evidence_url")
        if not isinstance(canonical, str) or not canonical.strip():
            raise ValueError(f"organization group {index} needs canonical_handle")
        if not isinstance(members, list) or not members:
            raise ValueError(f"organization group {index} needs member_handles")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"organization group {index} needs a reason")
        if not isinstance(evidence_url, str) or not evidence_url.startswith("https://"):
            raise ValueError(
                f"organization group {index} needs an HTTPS evidence_url"
            )
        canonical = canonical.removeprefix("@").lower()
        normalized_members = []
        for member in members:
            if not isinstance(member, str) or not member.strip():
                raise ValueError(
                    f"organization group {index} has an invalid member handle"
                )
            normalized = member.removeprefix("@").lower()
            if normalized == canonical:
                raise ValueError(f"organization group {index} contains its canonical")
            if normalized in member_handles:
                raise ValueError(f"member handle @{normalized} appears more than once")
            member_handles.add(normalized)
            normalized_members.append(normalized)
        if canonical in canonical_handles:
            raise ValueError(f"canonical handle @{canonical} appears more than once")
        canonical_handles.add(canonical)
        group["canonical_handle"] = canonical
        group["member_handles"] = normalized_members
    overlap = canonical_handles & member_handles
    if overlap:
        raise ValueError(
            "canonical handles cannot also be members: "
            + ", ".join(f"@{handle}" for handle in sorted(overlap))
        )
    return groups


def _entity_for_x_handle(conn: sqlite3.Connection, handle: str) -> sqlite3.Row:
    rows = conn.execute(
        """SELECT e.id, e.kind, e.slug, e.name, c.id AS channel_id
           FROM channels c
           JOIN entity_channels ec ON ec.channel_id = c.id
           JOIN entities e ON e.id = ec.entity_id
           WHERE c.kind = 'x' AND lower(c.key) = lower(?)""",
        (handle.removeprefix("@"),),
    ).fetchall()
    if not rows:
        raise ValueError(f"X handle @{handle.removeprefix('@')} has no entity")
    if len(rows) != 1:
        raise ValueError(
            f"X handle @{handle.removeprefix('@')} resolves to {len(rows)} entities"
        )
    return rows[0]


def _preflight_organization_groups(
    conn: sqlite3.Connection, groups: list[dict]
) -> list[dict]:
    """Resolve and validate the complete manifest before the first mutation."""
    resolved = []
    for group in groups:
        canonical = _entity_for_x_handle(conn, group["canonical_handle"])
        members = [
            _entity_for_x_handle(conn, handle)
            for handle in group["member_handles"]
        ]
        for role, entity in [("canonical", canonical), *[("member", x) for x in members]]:
            if entity["kind"] != "organization":
                raise ValueError(
                    f"{role} entity {entity['name']!r} is {entity['kind']}, "
                    "not organization"
                )
            rejection = conn.execute(
                "SELECT 1 FROM entity_registry_rejections WHERE entity_id = ?",
                (entity["id"],),
            ).fetchone()
            if rejection:
                raise ValueError(
                    f"{role} entity {entity['name']!r} is Registry-rejected"
                )
        resolved.append({"group": group, "canonical": canonical, "members": members})
    return resolved


def apply_organization_groups(
    conn: sqlite3.Connection,
    groups: list[dict],
    *,
    observed_at: str | None = None,
) -> dict:
    """Apply explicit same-organization mappings without fuzzy inference."""
    observed_at = observed_at or _now()
    merged_entities = 0
    moved_channels = 0
    already_grouped = 0
    results = []
    resolved_groups = _preflight_organization_groups(conn, groups)
    for resolved in resolved_groups:
        group = resolved["group"]
        canonical = resolved["canonical"]
        group_merged = 0
        for member_handle, member in zip(group["member_handles"], resolved["members"]):
            if member["id"] == canonical["id"]:
                already_grouped += 1
                continue
            merged = merge_entity_into(
                conn,
                canonical_entity_id=canonical["id"],
                duplicate_entity_id=member["id"],
                observed_at=observed_at,
                reason=group["reason"],
                source="organization-groups-manifest",
                evidence_url=group["evidence_url"],
            )
            conn.execute(
                """UPDATE entity_channels
                   SET relationship = 'official',
                       evidence_url = ?,
                       notes = ?
                   WHERE entity_id = ? AND channel_id = ?""",
                (
                    group["evidence_url"],
                    group["reason"],
                    canonical["id"],
                    member["channel_id"],
                ),
            )
            merged_entities += 1
            group_merged += 1
            moved_channels += merged["moved_channels"]
        results.append(
            {
                "canonical_handle": group["canonical_handle"],
                "canonical_entity_id": canonical["id"],
                "merged_entities": group_merged,
                "member_handles": group["member_handles"],
            }
        )
    return {
        "groups": len(groups),
        "merged_entities": merged_entities,
        "moved_channels": moved_channels,
        "already_grouped": already_grouped,
        "results": results,
    }


def load_relevance_removals(path: Path | str) -> list[dict]:
    """Load the explicit human-approved relevance removal boundary."""
    with Path(path).open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    if not rows:
        raise ValueError("relevance removal manifest is empty")
    required = {
        "entity_id",
        "name",
        "kind",
        "model_decision",
        "review_basis",
        "reason",
    }
    if not required.issubset(rows[0]):
        missing = sorted(required - set(rows[0]))
        raise ValueError(
            "relevance removal manifest is missing columns: " + ", ".join(missing)
        )
    seen: set[int] = set()
    removals = []
    for index, row in enumerate(rows, start=2):
        try:
            entity_id = int(row["entity_id"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"row {index} has an invalid entity_id") from exc
        if entity_id in seen:
            raise ValueError(f"entity {entity_id} appears more than once")
        seen.add(entity_id)
        if row["kind"] not in channels.ENTITY_KINDS:
            raise ValueError(f"row {index} has invalid kind {row['kind']!r}")
        if row["model_decision"] not in {"remove", "review"}:
            raise ValueError(f"row {index} has an invalid model_decision")
        if row["review_basis"] not in {"model_remove", "manual_add_from_review"}:
            raise ValueError(f"row {index} has an invalid review_basis")
        if not row["name"].strip() or not row["reason"].strip():
            raise ValueError(f"row {index} needs a name and reason")
        removals.append(
            {
                "entity_id": entity_id,
                "name": row["name"],
                "kind": row["kind"],
                "model_decision": row["model_decision"],
                "review_basis": row["review_basis"],
                "reason": row["reason"],
            }
        )
    return removals


def _preflight_relevance_removals(
    conn: sqlite3.Connection, removals: list[dict]
) -> tuple[list[dict], int]:
    """Validate the whole deletion manifest before changing any row."""
    resolved = []
    already_removed = 0
    for removal in removals:
        entity = conn.execute(
            "SELECT id, slug, name, kind FROM entities WHERE id = ?",
            (removal["entity_id"],),
        ).fetchone()
        if entity is None:
            already_removed += 1
            continue
        if entity["name"] != removal["name"] or entity["kind"] != removal["kind"]:
            raise ValueError(
                f"entity {entity['id']} does not match manifest identity "
                f"{removal['name']!r} ({removal['kind']})"
            )
        if conn.execute(
            "SELECT 1 FROM entity_registry_rejections WHERE entity_id = ?",
            (entity["id"],),
        ).fetchone():
            raise ValueError(f"entity {entity['id']} is already Registry-rejected")
        if conn.execute(
            "SELECT 1 FROM entity_merge_audit WHERE canonical_entity_id = ?",
            (entity["id"],),
        ).fetchone():
            raise ValueError(f"entity {entity['id']} is a merge canonical")
        channel_rows = conn.execute(
            """SELECT c.id, c.kind, c.key
               FROM entity_channels ec
               JOIN channels c ON c.id = ec.channel_id
               WHERE ec.entity_id = ?
               ORDER BY c.id""",
            (entity["id"],),
        ).fetchall()
        if len(channel_rows) != 1 or channel_rows[0]["kind"] != "x":
            raise ValueError(
                f"entity {entity['id']} must own exactly one X channel"
            )
        channel = channel_rows[0]
        account = conn.execute(
            """SELECT id, handle FROM accounts
               WHERE platform = 'x' AND lower(handle) = lower(?)""",
            (channel["key"],),
        ).fetchone()
        if account is None:
            raise ValueError(
                f"entity {entity['id']} channel @{channel['key']} has no account"
            )
        has_labs = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'labs'"
        ).fetchone()
        if has_labs and conn.execute(
            "SELECT 1 FROM labs WHERE x_account_id = ?", (account["id"],)
        ).fetchone():
            raise ValueError(f"entity {entity['id']} is a seeded lab")
        if conn.execute(
            """SELECT 1 FROM graph_edges
               WHERE from_account_id = ? OR to_account_id = ? LIMIT 1""",
            (account["id"], account["id"]),
        ).fetchone():
            raise ValueError(f"entity {entity['id']} participates in graph edges")
        resolved.append(
            {
                "removal": removal,
                "entity": entity,
                "channel": channel,
                "account": account,
            }
        )
    return resolved, already_removed


def apply_relevance_removals(conn: sqlite3.Connection, removals: list[dict]) -> dict:
    """Delete only the exact, reviewed one-account identities in a manifest."""
    resolved, already_removed = _preflight_relevance_removals(conn, removals)
    removed_entities = 0
    removed_channels = 0
    removed_accounts = 0
    for item in resolved:
        entity_id = item["entity"]["id"]
        channel_id = item["channel"]["id"]
        account_id = item["account"]["id"]
        conn.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
        conn.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
        conn.execute(
            "DELETE FROM account_source_facts WHERE account_id = ?", (account_id,)
        )
        conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        removed_entities += 1
        removed_channels += 1
        removed_accounts += 1
    return {
        "requested": len(removals),
        "removed_entities": removed_entities,
        "removed_channels": removed_channels,
        "removed_accounts": removed_accounts,
        "already_removed": already_removed,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="fli registry")
    parser.add_argument(
        "action",
        choices=["apply-organization-groups", "apply-relevance-removals"],
    )
    parser.add_argument("--db", default=None)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    conn = channels.connect(args.db) if args.db else channels.connect()
    ensure_schema(conn)
    conn.commit()
    if args.action == "apply-organization-groups":
        manifest_path = args.manifest or DEFAULT_ORGANIZATION_GROUPS_PATH
        manifest = load_organization_groups(manifest_path)
        apply = apply_organization_groups
    else:
        manifest_path = args.manifest or DEFAULT_RELEVANCE_REMOVALS_PATH
        manifest = load_relevance_removals(manifest_path)
        apply = apply_relevance_removals
    try:
        conn.execute("BEGIN IMMEDIATE")
        result = apply(conn, manifest)
        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    print(
        json.dumps(
            {"status": "ok", "dry_run": args.dry_run, **result},
            sort_keys=True,
        )
    )
    return 0


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
               SELECT e.id, e.slug, e.kind, e.name,
                      (
                          SELECT SUM(a.followers_count)
                          FROM accounts a
                          WHERE a.platform = 'x'
                            AND lower(a.handle) IN (
                                SELECT lower(xc.key)
                                FROM entity_channels xec
                                JOIN channels xc ON xc.id = xec.channel_id
                                WHERE xec.entity_id = e.id
                                  AND xc.kind = 'x'
                            )
                      ) AS followers_count
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
           SELECT e.id, e.slug, e.kind, e.name, e.followers_count,
                  CASE WHEN rejected.entity_id IS NULL
                       THEN 'active' ELSE 'rejected' END AS registry_state,
                  rejected.reason_code AS rejection_reason_code,
                  rejected.reason AS rejection_reason,
                  rejected.source AS rejection_source,
                  rejected.evidence_url AS rejection_evidence_url,
                  {kind_reason_sql} AS kind_reason,
                  c.id AS channel_id, c.kind AS channel_kind, c.key AS channel_key,
                  c.label AS channel_label, c.url AS channel_url,
                  ec.relationship AS channel_relationship,
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
                    e.name COLLATE NOCASE,
                    CASE ec.relationship WHEN 'identity' THEN 0
                                         WHEN 'official' THEN 1
                                         ELSE 2 END,
                    c.kind, c.key""",
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
                "followers_count": row["followers_count"],
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
