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

CREATE TABLE IF NOT EXISTS entity_registry_intake_audit (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER REFERENCES entities (id) ON DELETE SET NULL,
    handle TEXT NOT NULL,
    profile_url TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('screen', 'direct')),
    override_reason TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    outcome TEXT,
    registry_decision TEXT,
    registry_decision_reason TEXT,
    kind TEXT,
    kind_reason TEXT,
    model TEXT,
    reasoning_effort TEXT,
    prompt_version TEXT,
    response_id TEXT,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    reported_cost_usd REAL,
    error_code TEXT,
    error_message TEXT,
    requested_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_entity_registry_intake_entity
ON entity_registry_intake_audit (entity_id, requested_at DESC, id DESC);

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

CREATE TABLE IF NOT EXISTS entity_override_audit (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER NOT NULL REFERENCES entities (id) ON DELETE CASCADE,
    old_name TEXT NOT NULL,
    new_name TEXT NOT NULL,
    old_kind TEXT NOT NULL,
    new_kind TEXT NOT NULL,
    reason TEXT NOT NULL,
    source TEXT NOT NULL,
    evidence_url TEXT NOT NULL,
    overridden_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_entity_override_audit_decision
ON entity_override_audit (entity_id, new_name, new_kind);
"""

DEFAULT_ORGANIZATION_GROUPS_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "registry"
    / "organization-groups.json"
)
DEFAULT_ORGANIZATION_COVERAGE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "registry"
    / "organization-coverage.json"
)
DEFAULT_RELEVANCE_REMOVALS_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "registry"
    / "relevance-removals.csv"
)
DEFAULT_ENTITY_OVERRIDES_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "registry"
    / "entity-overrides.json"
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
    if conn.in_transaction:
        required = {
            "entity_registry_rejections",
            "entity_registry_intake_audit",
            "entity_merge_audit",
            "entity_override_audit",
        }
        existing = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        missing = required - existing
        if missing:
            raise RuntimeError(
                "Registry schema must be initialized before a transaction: "
                + ", ".join(sorted(missing))
            )
        return
    conn.executescript(SCHEMA)
    if conn.execute(
        """SELECT 1 FROM sqlite_master
           WHERE type = 'table' AND name = 'entity_kind_classifications'"""
    ).fetchone():
        conn.execute(
            """CREATE INDEX IF NOT EXISTS
               idx_entity_kind_classifications_entity_label_latest
               ON entity_kind_classifications (
                   entity_id, classification, classified_at DESC, run_id DESC
               )"""
        )


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


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_organization_coverage(path: Path | str) -> dict:
    """Load the reviewed parent-organization coverage manifest."""
    manifest = json.loads(Path(path).read_text())
    if not isinstance(manifest, dict):
        raise ValueError("organization coverage manifest must be an object")
    if manifest.get("schema_version") != "organization-coverage-v1":
        raise ValueError("unsupported organization coverage schema_version")
    snapshot = manifest.get("snapshot")
    if not isinstance(snapshot, dict):
        raise ValueError("organization coverage manifest needs snapshot metadata")
    for key in ("snapshot_id", "cohort_sha256", "database_sha256"):
        if not isinstance(snapshot.get(key), str) or not snapshot[key].strip():
            raise ValueError(f"organization coverage snapshot needs {key}")

    organizations = manifest.get("organizations")
    if not isinstance(organizations, list) or not organizations:
        raise ValueError("organization coverage manifest needs organizations")
    slugs: set[str] = set()
    x_handles: set[str] = set()
    for index, organization in enumerate(organizations):
        if not isinstance(organization, dict):
            raise ValueError(f"organization coverage row {index} must be an object")
        slug = organization.get("slug")
        name = organization.get("name")
        reason = organization.get("reason")
        evidence_url = organization.get("evidence_url")
        if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9-]+", slug):
            raise ValueError(f"organization coverage row {index} has invalid slug")
        if slug in slugs:
            raise ValueError(f"organization coverage slug {slug!r} is duplicated")
        slugs.add(slug)
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"organization coverage row {index} needs name")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"organization coverage row {index} needs reason")
        if not isinstance(evidence_url, str) or not evidence_url.startswith("https://"):
            raise ValueError(
                f"organization coverage row {index} needs HTTPS evidence_url"
            )

        channels_manifest = organization.get("channels")
        if not isinstance(channels_manifest, list) or not channels_manifest:
            raise ValueError(f"organization coverage row {index} needs channels")
        organization_handles: set[str] = set()
        for channel_index, channel in enumerate(channels_manifest):
            if not isinstance(channel, dict):
                raise ValueError(
                    f"organization coverage row {index} channel {channel_index} "
                    "must be an object"
                )
            kind = channel.get("kind")
            key = channel.get("key")
            relationship = channel.get("relationship")
            channel_evidence = channel.get("evidence_url")
            if kind not in {"x", "website", "blog", "github"}:
                raise ValueError(
                    f"organization coverage row {index} channel {channel_index} "
                    "has unsupported kind"
                )
            if not isinstance(key, str) or not key.strip():
                raise ValueError(
                    f"organization coverage row {index} channel {channel_index} "
                    "needs key"
                )
            if relationship not in {"identity", "official"}:
                raise ValueError(
                    f"organization coverage row {index} channel {channel_index} "
                    "has invalid relationship"
                )
            if not isinstance(channel_evidence, str) or not channel_evidence.startswith(
                "https://"
            ):
                raise ValueError(
                    f"organization coverage row {index} channel {channel_index} "
                    "needs HTTPS evidence_url"
                )
            if kind == "x":
                handle = key.removeprefix("@").lower()
                expected_x_id = channel.get("expected_x_id")
                if not isinstance(expected_x_id, str) or not expected_x_id.strip():
                    raise ValueError(
                        f"organization coverage X channel @{handle} needs expected_x_id"
                    )
                if handle in x_handles:
                    raise ValueError(
                        f"organization coverage X handle @{handle} is duplicated"
                    )
                x_handles.add(handle)
                organization_handles.add(handle)
                channel["key"] = handle
            elif kind in {"website", "blog"} and not key.startswith("https://"):
                raise ValueError(
                    f"organization coverage {kind} channel needs an HTTPS key"
                )

        merges = organization.get("merge_handles", [])
        if not isinstance(merges, list):
            raise ValueError(f"organization coverage row {index} merge_handles invalid")
        merge_seen: set[str] = set()
        for merge_index, merge in enumerate(merges):
            if not isinstance(merge, dict):
                raise ValueError(
                    f"organization coverage row {index} merge {merge_index} invalid"
                )
            handle = merge.get("handle")
            expected_name = merge.get("expected_entity_name")
            if not isinstance(handle, str) or not handle.strip():
                raise ValueError(
                    f"organization coverage row {index} merge {merge_index} needs handle"
                )
            handle = handle.removeprefix("@").lower()
            if handle not in organization_handles:
                raise ValueError(
                    f"organization coverage merge @{handle} must also be a channel"
                )
            if handle in merge_seen:
                raise ValueError(f"organization coverage merge @{handle} is duplicated")
            if not isinstance(expected_name, str) or not expected_name.strip():
                raise ValueError(
                    f"organization coverage merge @{handle} needs expected_entity_name"
                )
            merge_seen.add(handle)
            merge["handle"] = handle
        legacy_lab_slug = organization.get("legacy_lab_slug")
        if legacy_lab_slug is not None and (
            not isinstance(legacy_lab_slug, str)
            or not re.fullmatch(r"[a-z0-9-]+", legacy_lab_slug)
            or legacy_lab_slug == slug
        ):
            raise ValueError(
                f"organization coverage row {index} has invalid legacy_lab_slug"
            )
    return manifest


def _open_coverage_snapshot(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ValueError(f"following snapshot does not exist: {path}")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _coverage_channel_owner(
    conn: sqlite3.Connection, *, kind: str, key: str
) -> sqlite3.Row | None:
    return conn.execute(
        """SELECT e.id, e.slug, e.name, e.kind,
                  EXISTS (
                      SELECT 1 FROM entity_registry_rejections r
                      WHERE r.entity_id = e.id
                  ) AS rejected
           FROM channels c
           JOIN entity_channels ec ON ec.channel_id = c.id
           JOIN entities e ON e.id = ec.entity_id
           WHERE c.kind = ? AND lower(c.key) = lower(?)""",
        (kind, key),
    ).fetchone()


def _preflight_organization_coverage(
    conn: sqlite3.Connection,
    manifest: dict,
    *,
    snapshot_path: Path,
) -> list[dict]:
    expected_snapshot = manifest["snapshot"]
    actual_sha256 = _file_sha256(snapshot_path)
    if actual_sha256 != expected_snapshot["database_sha256"]:
        raise ValueError(
            "following snapshot SHA-256 mismatch: "
            f"{actual_sha256} != {expected_snapshot['database_sha256']}"
        )
    snapshot = _open_coverage_snapshot(snapshot_path)
    try:
        run = snapshot.execute("SELECT * FROM snapshot_run").fetchone()
        if run is None or run["status"] != "complete":
            raise ValueError("organization coverage requires a complete snapshot")
        if run["snapshot_id"] != expected_snapshot["snapshot_id"]:
            raise ValueError("organization coverage snapshot_id mismatch")
        if run["cohort_sha256"] != expected_snapshot["cohort_sha256"]:
            raise ValueError("organization coverage cohort_sha256 mismatch")

        resolved: list[dict] = []
        for organization in manifest["organizations"]:
            canonical = conn.execute(
                "SELECT * FROM entities WHERE slug = ?", (organization["slug"],)
            ).fetchone()
            if canonical is not None:
                if canonical["kind"] != "organization":
                    raise ValueError(
                        f"canonical {organization['slug']!r} is not an organization"
                    )
                if canonical["name"] != organization["name"]:
                    raise ValueError(
                        f"canonical {organization['slug']!r} has unexpected name "
                        f"{canonical['name']!r}"
                    )
                if conn.execute(
                    "SELECT 1 FROM entity_registry_rejections WHERE entity_id = ?",
                    (canonical["id"],),
                ).fetchone():
                    raise ValueError(
                        f"canonical {organization['slug']!r} is Registry-rejected"
                    )

            merge_by_handle = {
                item["handle"]: item for item in organization.get("merge_handles", [])
            }
            merge_entity_ids: set[int] = set()
            for handle, merge in merge_by_handle.items():
                member = _entity_for_x_handle(conn, handle)
                if canonical is not None and member["id"] == canonical["id"]:
                    merge_entity_ids.add(member["id"])
                    continue
                if member["kind"] != "organization":
                    raise ValueError(f"merge handle @{handle} is not an organization")
                if member["name"] != merge["expected_entity_name"]:
                    raise ValueError(
                        f"merge handle @{handle} has unexpected entity name "
                        f"{member['name']!r}"
                    )
                if conn.execute(
                    "SELECT 1 FROM entity_registry_rejections WHERE entity_id = ?",
                    (member["id"],),
                ).fetchone():
                    raise ValueError(f"merge handle @{handle} is Registry-rejected")
                merge_entity_ids.add(member["id"])

            snapshot_accounts: dict[str, sqlite3.Row] = {}
            for channel in organization["channels"]:
                kind = channel["kind"]
                key = channel["key"]
                if kind == "x":
                    account = snapshot.execute(
                        "SELECT * FROM account WHERE lower(handle) = lower(?)", (key,)
                    ).fetchone()
                    if account is None:
                        raise ValueError(f"snapshot has no X account @{key}")
                    if str(account["x_id"]) != channel["expected_x_id"]:
                        raise ValueError(
                            f"snapshot X ID mismatch for @{key}: "
                            f"{account['x_id']} != {channel['expected_x_id']}"
                        )
                    snapshot_accounts[key] = account

                    existing = conn.execute(
                        "SELECT * FROM accounts WHERE platform = 'x' AND handle = ?",
                        (key,),
                    ).fetchone()
                    if existing is not None and str(existing["x_id"]) != str(
                        account["x_id"]
                    ):
                        raise ValueError(f"Registry X ID mismatch for @{key}")
                    x_id_owner = conn.execute(
                        """SELECT handle FROM accounts
                           WHERE platform = 'x' AND x_id = ? AND handle != ?""",
                        (str(account["x_id"]), key),
                    ).fetchone()
                    if x_id_owner is not None:
                        raise ValueError(
                            f"X ID {account['x_id']} already belongs to "
                            f"@{x_id_owner['handle']}"
                        )

                owner = _coverage_channel_owner(conn, kind=kind, key=key)
                if owner is None:
                    continue
                if owner["rejected"]:
                    raise ValueError(
                        f"{kind} channel {key!r} belongs to a rejected entity"
                    )
                if canonical is not None and owner["id"] == canonical["id"]:
                    continue
                if owner["id"] not in merge_entity_ids:
                    raise ValueError(
                        f"{kind} channel {key!r} is unexpectedly owned by "
                        f"{owner['name']!r}"
                    )

            legacy_lab_slug = organization.get("legacy_lab_slug")
            if legacy_lab_slug and conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'labs'"
            ).fetchone():
                legacy_lab = conn.execute(
                    "SELECT slug FROM labs WHERE slug IN (?, ?)",
                    (legacy_lab_slug, organization["slug"]),
                ).fetchall()
                if not legacy_lab:
                    raise ValueError(
                        f"legacy lab seed {legacy_lab_slug!r} is missing"
                    )
                if len(legacy_lab) > 1:
                    raise ValueError(
                        f"legacy and canonical lab seeds both exist for "
                        f"{organization['slug']!r}"
                    )
            resolved.append(
                {
                    "organization": organization,
                    "canonical": canonical,
                    "snapshot_accounts": snapshot_accounts,
                }
            )
        return resolved
    finally:
        snapshot.close()


def _upsert_coverage_account(
    conn: sqlite3.Connection,
    *,
    account: sqlite3.Row,
    snapshot_id: str,
    organization_slug: str,
) -> int:
    handle = account["handle"].lower()
    existing = conn.execute(
        "SELECT * FROM accounts WHERE platform = 'x' AND handle = ?", (handle,)
    ).fetchone()
    observed_at = account["last_observed_at"]
    if existing is None:
        cursor = conn.execute(
            """INSERT INTO accounts
               (platform, handle, display_name, x_id, bio, followers_count,
                first_seen_at, last_seen_at)
               VALUES ('x', ?, ?, ?, ?, ?, ?, ?)""",
            (
                handle,
                account["display_name"],
                str(account["x_id"]),
                account["bio"],
                account["followers_count"],
                account["first_observed_at"],
                observed_at,
            ),
        )
        account_id = cursor.lastrowid
    else:
        account_id = existing["id"]
        conn.execute(
            """UPDATE accounts SET
                   display_name = ?, x_id = ?, bio = ?, followers_count = ?,
                   first_seen_at = min(first_seen_at, ?),
                   last_seen_at = max(last_seen_at, ?)
               WHERE id = ?""",
            (
                account["display_name"],
                str(account["x_id"]),
                account["bio"],
                account["followers_count"],
                account["first_observed_at"],
                observed_at,
                account_id,
            ),
        )
    conn.execute(
        """INSERT INTO account_source_facts
           (account_id, source, fact, value, observed_at, evidence_url)
           VALUES (?, ?, 'organization_coverage', ?, ?, ?)
           ON CONFLICT (account_id, source, fact) DO UPDATE SET
               value = excluded.value,
               observed_at = excluded.observed_at,
               evidence_url = excluded.evidence_url""",
        (
            account_id,
            f"following-snapshot:{snapshot_id}",
            organization_slug,
            observed_at,
            f"https://x.com/{handle}",
        ),
    )
    return account_id


def apply_organization_coverage(
    conn: sqlite3.Connection,
    manifest: dict,
    *,
    snapshot_path: Path | str,
    observed_at: str | None = None,
) -> dict:
    """Create reviewed parent organizations and attach their exact channels."""
    ensure_schema(conn)
    observed_at = observed_at or _now()
    snapshot_path = Path(snapshot_path)
    resolved = _preflight_organization_coverage(
        conn, manifest, snapshot_path=snapshot_path
    )
    snapshot_id = manifest["snapshot"]["snapshot_id"]
    created_entities = 0
    merged_entities = 0
    imported_accounts = 0
    linked_channels = 0
    already_grouped = 0

    for item in resolved:
        organization = item["organization"]
        canonical = item["canonical"]
        if canonical is None:
            canonical_id = channels.upsert_entity(
                conn,
                kind="organization",
                slug=organization["slug"],
                name=organization["name"],
                notes=organization["reason"],
                observed_at=observed_at,
            )
            created_entities += 1
        else:
            canonical_id = canonical["id"]

        channel_ids: dict[tuple[str, str], int] = {}
        for channel in organization["channels"]:
            kind = channel["kind"]
            key = channel["key"]
            if kind == "x":
                account = item["snapshot_accounts"][key]
                existed = conn.execute(
                    "SELECT 1 FROM accounts WHERE platform = 'x' AND handle = ?",
                    (key,),
                ).fetchone()
                _upsert_coverage_account(
                    conn,
                    account=account,
                    snapshot_id=snapshot_id,
                    organization_slug=organization["slug"],
                )
                imported_accounts += existed is None
                channel_id = channels.upsert_channel(
                    conn,
                    kind="x",
                    key=key,
                    label=account["display_name"],
                    observed_at=account["last_observed_at"],
                )
                channels.observe_channel(
                    conn,
                    channel_id=channel_id,
                    source=f"following-snapshot:{snapshot_id}",
                    metric="followers_count",
                    value=account["followers_count"],
                    observed_at=account["last_observed_at"],
                    evidence_url=f"https://x.com/{key}",
                )
                channels.observe_channel(
                    conn,
                    channel_id=channel_id,
                    source=f"following-snapshot:{snapshot_id}",
                    metric="bio",
                    value=account["bio"],
                    observed_at=account["last_observed_at"],
                    evidence_url=f"https://x.com/{key}",
                )
            else:
                channel_id = channels.upsert_channel(
                    conn,
                    kind=kind,
                    key=key,
                    label=channel.get("label"),
                    observed_at=observed_at,
                )
            channel_ids[(kind, key)] = channel_id

        for merge in organization.get("merge_handles", []):
            member = _entity_for_x_handle(conn, merge["handle"])
            if member["id"] == canonical_id:
                already_grouped += 1
                continue
            result = merge_entity_into(
                conn,
                canonical_entity_id=canonical_id,
                duplicate_entity_id=member["id"],
                observed_at=observed_at,
                reason=organization["reason"],
                source="organization-coverage-manifest",
                evidence_url=organization["evidence_url"],
            )
            merged_entities += 1
            linked_channels += result["moved_channels"]

        legacy_lab_slug = organization.get("legacy_lab_slug")
        if legacy_lab_slug and conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'labs'"
        ).fetchone():
            conn.execute(
                """UPDATE labs SET slug = ?, name = ?, notes = ?
                   WHERE slug = ?""",
                (
                    organization["slug"],
                    organization["name"],
                    organization["reason"],
                    legacy_lab_slug,
                ),
            )

        for channel in organization["channels"]:
            channel_id = channel_ids[(channel["kind"], channel["key"])]
            registry_owner = _coverage_channel_owner(
                conn, kind=channel["kind"], key=channel["key"]
            )
            if registry_owner is None or registry_owner["id"] != canonical_id:
                linked_channels += 1
            claim_channel(
                conn,
                entity_id=canonical_id,
                channel_id=channel_id,
                relationship=channel["relationship"],
                confidence=1.0,
                evidence_url=channel["evidence_url"],
                notes=organization["reason"],
                observed_at=observed_at,
            )

    return {
        "organizations": len(resolved),
        "created_entities": created_entities,
        "merged_entities": merged_entities,
        "imported_accounts": imported_accounts,
        "linked_channels": linked_channels,
        "already_grouped": already_grouped,
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
        decision_pair = (row["model_decision"], row["review_basis"])
        allowed_pairs = {
            ("remove", "model_remove"),
            ("review", "manual_add_from_review"),
            ("keep", "manual_override_from_keep"),
        }
        if decision_pair not in allowed_pairs:
            raise ValueError(
                f"row {index} has an invalid model_decision/review_basis pair"
            )
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


def load_entity_overrides(path: Path | str) -> list[dict]:
    """Load exact human-reviewed name and structural-kind corrections."""
    with Path(path).open(encoding="utf-8") as source:
        overrides = json.load(source)
    if not isinstance(overrides, list) or not overrides:
        raise ValueError("entity override manifest must be a non-empty list")
    required = {
        "entity_id",
        "expected_name",
        "expected_kind",
        "target_name",
        "target_kind",
        "reason",
        "source",
        "evidence_url",
    }
    seen: set[int] = set()
    normalized = []
    for index, item in enumerate(overrides, start=1):
        if not isinstance(item, dict) or not required.issubset(item):
            missing = sorted(required - set(item if isinstance(item, dict) else ()))
            raise ValueError(
                f"entity override {index} is missing fields: {', '.join(missing)}"
            )
        try:
            entity_id = int(item["entity_id"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"entity override {index} has an invalid entity_id") from exc
        if entity_id in seen:
            raise ValueError(f"entity {entity_id} appears more than once")
        seen.add(entity_id)
        if item["expected_kind"] not in channels.ENTITY_KINDS:
            raise ValueError(f"entity override {index} has invalid expected_kind")
        if item["target_kind"] not in channels.ENTITY_KINDS:
            raise ValueError(f"entity override {index} has invalid target_kind")
        for field in ("expected_name", "target_name", "reason", "source"):
            if not isinstance(item[field], str) or not item[field].strip():
                raise ValueError(f"entity override {index} needs {field}")
        if not isinstance(item["evidence_url"], str) or not item[
            "evidence_url"
        ].startswith("https://"):
            raise ValueError(f"entity override {index} needs an HTTPS evidence_url")
        normalized.append({**item, "entity_id": entity_id})
    return normalized


def _preflight_entity_overrides(
    conn: sqlite3.Connection, overrides: list[dict]
) -> tuple[list[dict], int]:
    resolved = []
    already_overridden = 0
    for override in overrides:
        entity = conn.execute(
            "SELECT id, name, kind FROM entities WHERE id = ?",
            (override["entity_id"],),
        ).fetchone()
        if entity is None:
            raise ValueError(f"entity {override['entity_id']} does not exist")
        current = (entity["name"], entity["kind"])
        target = (override["target_name"], override["target_kind"])
        expected = (override["expected_name"], override["expected_kind"])
        if current == target:
            already_overridden += 1
            continue
        if current != expected:
            raise ValueError(
                f"entity {entity['id']} does not match override expectation "
                f"{expected[0]!r} ({expected[1]})"
            )
        if conn.execute(
            "SELECT 1 FROM entity_registry_rejections WHERE entity_id = ?",
            (entity["id"],),
        ).fetchone():
            raise ValueError(f"entity {entity['id']} is Registry-rejected")
        resolved.append({"override": override, "entity": entity})
    return resolved, already_overridden


def apply_entity_overrides(
    conn: sqlite3.Connection,
    overrides: list[dict],
    *,
    observed_at: str | None = None,
) -> dict:
    """Apply exact reviewed identity corrections with an idempotent audit trail."""
    observed_at = observed_at or _now()
    resolved, already_overridden = _preflight_entity_overrides(conn, overrides)
    for item in resolved:
        override = item["override"]
        entity = item["entity"]
        conn.execute(
            """UPDATE entities
               SET name = ?, kind = ?, updated_at = ?
               WHERE id = ?""",
            (
                override["target_name"],
                override["target_kind"],
                observed_at,
                entity["id"],
            ),
        )
        conn.execute(
            """INSERT OR IGNORE INTO entity_override_audit
               (entity_id, old_name, new_name, old_kind, new_kind,
                reason, source, evidence_url, overridden_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entity["id"],
                entity["name"],
                override["target_name"],
                entity["kind"],
                override["target_kind"],
                override["reason"],
                override["source"],
                override["evidence_url"],
                observed_at,
            ),
        )
    return {
        "requested": len(overrides),
        "overridden": len(resolved),
        "already_overridden": already_overridden,
    }


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
        choices=[
            "apply-organization-groups",
            "apply-organization-coverage",
            "apply-relevance-removals",
            "apply-entity-overrides",
        ],
    )
    parser.add_argument("--db", default=None)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--snapshot", type=Path, default=None)
    args = parser.parse_args(argv)

    conn = channels.connect(args.db) if args.db else channels.connect()
    ensure_schema(conn)
    conn.commit()
    if args.action == "apply-organization-groups":
        manifest_path = args.manifest or DEFAULT_ORGANIZATION_GROUPS_PATH
        manifest = load_organization_groups(manifest_path)
        apply = apply_organization_groups
    elif args.action == "apply-organization-coverage":
        manifest_path = args.manifest or DEFAULT_ORGANIZATION_COVERAGE_PATH
        manifest = load_organization_coverage(manifest_path)
        if args.snapshot is None:
            parser.error("apply-organization-coverage requires --snapshot")
        apply = lambda active_conn, active_manifest: apply_organization_coverage(
            active_conn,
            active_manifest,
            snapshot_path=args.snapshot,
        )
    elif args.action == "apply-relevance-removals":
        manifest_path = args.manifest or DEFAULT_RELEVANCE_REMOVALS_PATH
        manifest = load_relevance_removals(manifest_path)
        apply = apply_relevance_removals
    else:
        manifest_path = args.manifest or DEFAULT_ENTITY_OVERRIDES_PATH
        manifest = load_entity_overrides(manifest_path)
        apply = apply_entity_overrides
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


REGISTRY_GROUPS = frozenset({"all", *channels.ENTITY_KINDS, "rejected"})


def _registry_where(*, group: str, query: str) -> tuple[str, list[str]]:
    if group not in REGISTRY_GROUPS:
        raise ValueError(f"invalid Registry group: {group}")
    clauses: list[str] = []
    params: list[str] = []
    if group == "rejected":
        clauses.append("rejected.entity_id IS NOT NULL")
    elif group != "all":
        clauses.extend(("rejected.entity_id IS NULL", "e.kind = ?"))
        params.append(group)

    needle = query.strip().lower()
    if needle:
        pattern = f"%{needle}%"
        clauses.append(
            """(lower(e.name) LIKE ?
                 OR lower(COALESCE(rejected.reason, '')) LIKE ?
                 OR EXISTS (
                     SELECT 1
                     FROM entity_channels search_ec
                     JOIN channels search_c ON search_c.id = search_ec.channel_id
                     WHERE search_ec.entity_id = e.id
                       AND (
                           lower(search_c.key) LIKE ?
                           OR EXISTS (
                               SELECT 1 FROM channel_observations search_o
                               WHERE search_o.channel_id = search_c.id
                                 AND search_o.source = 'x_profile'
                                 AND search_o.metric = 'bio'
                                 AND lower(COALESCE(search_o.value, '')) LIKE ?
                           )
                       )
                 ))"""
        )
        params.extend((pattern, pattern, pattern, pattern))
    return (" AND ".join(clauses) if clauses else "1 = 1"), params


def count_entities(
    conn: sqlite3.Connection, *, group: str = "all", query: str = ""
) -> int:
    """Count entities in one server-side Registry search/filter view."""
    ensure_schema(conn)
    where_sql, params = _registry_where(group=group, query=query)
    return conn.execute(
        f"""SELECT COUNT(*)
            FROM entities e
            LEFT JOIN entity_registry_rejections rejected
              ON rejected.entity_id = e.id
            WHERE {where_sql}""",
        params,
    ).fetchone()[0]


def read_entities(
    conn: sqlite3.Connection,
    *,
    limit: int = 5000,
    offset: int = 0,
    group: str = "all",
    query: str = "",
    direction: str = "desc",
    entity_id: int | None = None,
) -> list[dict]:
    """Return identity fields, structural-kind reason, and curation state."""
    ensure_schema(conn)
    has_classifications = bool(
        conn.execute(
            """SELECT 1 FROM sqlite_master
               WHERE type = 'table'
                 AND name = 'entity_kind_classifications'"""
        ).fetchone()
    )
    has_overrides = bool(
        conn.execute(
            """SELECT 1 FROM sqlite_master
               WHERE type = 'table' AND name = 'entity_override_audit'"""
        ).fetchone()
    )
    has_intake_audit = bool(
        conn.execute(
            """SELECT 1 FROM sqlite_master
               WHERE type = 'table' AND name = 'entity_registry_intake_audit'"""
        ).fetchone()
    )
    override_reason_sql = (
        """(SELECT o.reason FROM entity_override_audit o
             WHERE o.entity_id = e.id
               AND o.old_kind <> o.new_kind
               AND o.new_kind = e.kind
             ORDER BY o.overridden_at DESC, o.id DESC
             LIMIT 1)"""
        if has_overrides
        else "NULL"
    )
    intake_reason_sql = (
        """(SELECT intake.kind_reason FROM entity_registry_intake_audit intake
             WHERE intake.entity_id = e.id
               AND intake.status = 'completed'
               AND intake.kind = e.kind
               AND intake.kind_reason IS NOT NULL
             ORDER BY intake.requested_at DESC, intake.id DESC
             LIMIT 1)"""
        if has_intake_audit
        else "NULL"
    )
    classification_reason_sql = (
        """(SELECT k.reason FROM entity_kind_classifications k
             WHERE k.entity_id = e.id AND k.classification = e.kind
             ORDER BY k.classified_at DESC, k.run_id DESC
             LIMIT 1)"""
        if has_classifications
        else "NULL"
    )
    kind_reason_sql = (
        f"COALESCE({override_reason_sql}, {intake_reason_sql}, "
        f"{classification_reason_sql})"
    )
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if offset < 0:
        raise ValueError("offset must be non-negative")
    if direction not in {"asc", "desc"}:
        raise ValueError(f"invalid follower sort direction: {direction}")
    where_sql, where_params = _registry_where(group=group, query=query)
    if entity_id is not None:
        where_sql = f"({where_sql}) AND e.id = ?"
        where_params = [*where_params, entity_id]
    follower_order = direction.upper()
    order_sql = (
        f"followers_count {follower_order} NULLS LAST, name COLLATE NOCASE"
        if group in {"all", "person", "organization"}
        else "name COLLATE NOCASE"
    )
    outer_order_sql = (
        f"e.followers_count {follower_order} NULLS LAST, e.name COLLATE NOCASE"
        if group in {"all", "person", "organization"}
        else "e.name COLLATE NOCASE"
    )
    rows = conn.execute(
        f"""WITH selected AS (
               SELECT e.id, e.slug, e.kind, e.name,
                      (
                          SELECT SUM(a.followers_count)
                          FROM accounts a
                          WHERE a.platform = 'x'
                            AND a.handle IN (
                                SELECT xc.key
                                FROM entity_channels xec
                                JOIN channels xc ON xc.id = xec.channel_id
                                WHERE xec.entity_id = e.id
                                  AND xc.kind = 'x'
                            )
                      ) AS followers_count
               FROM entities e
               LEFT JOIN entity_registry_rejections rejected
                 ON rejected.entity_id = e.id
               WHERE {where_sql}
               ORDER BY {order_sql}
               LIMIT ? OFFSET ?
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
           ORDER BY {outer_order_sql},
                    CASE ec.relationship WHEN 'identity' THEN 0
                                         WHEN 'official' THEN 1
                                         ELSE 2 END,
                    c.kind, c.key""",
        (*where_params, limit, offset),
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
