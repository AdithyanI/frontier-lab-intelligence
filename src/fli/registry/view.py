"""Read-only Registry projection for API and operator inspection."""

from __future__ import annotations

import sqlite3

from fli.registry import channels, store


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
    store.ensure_schema(conn)
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
    store.ensure_schema(conn)
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
    store.ensure_schema(conn)
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
