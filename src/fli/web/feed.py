"""Registry-aware read model for the deterministic X signal Feed."""

from __future__ import annotations

import bisect
import math
import sqlite3
from collections import defaultdict
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from fli import following_rankings, signal_feed
from fli.web import rankings as rankings_store


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FEED_DB = signal_feed.DEFAULT_FEED_DB
DEFAULT_REGISTRY_DB = REPO_ROOT / "data" / "fli.db"
DEFAULT_DERIVED_ROOT = following_rankings.DEFAULT_DERIVED_ROOT

SCORE_FORMULA = {
    "version": "attention-v1.1",
    "network_attention_weight": 0.55,
    "originator_support_weight": 0.25,
    "public_engagement_weight": 0.20,
    "note": (
        "Experimental daily ordering aid, not an importance or quality judgment. "
        "Tracked amplification counts each active Registry entity once — people "
        "and organizations alike; public engagement is a tie-breaker."
    ),
}


def _open_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _db_version(path: Path) -> tuple[str, int, int, int, int]:
    """Return a cheap cache token that also notices uncheckpointed WAL writes."""
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


def _latest_analysis_db() -> Path | None:
    return rankings_store.latest_analysis_db(DEFAULT_DERIVED_ROOT)


def _latest_run(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        """SELECT * FROM feed_run
           ORDER BY created_at DESC, run_id DESC LIMIT 1"""
    ).fetchone()


@lru_cache(maxsize=8)
def _registry_maps_cached(
    version: tuple[str, int, int, int, int],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    path = Path(version[0])
    if not path.is_file():
        return {}, {}
    conn = _open_readonly(path)
    rows = conn.execute(
        """SELECT e.id AS entity_id, e.name AS entity_name, e.kind AS entity_kind,
                  c.key AS handle, a.x_id,
                  CASE WHEN rejected.entity_id IS NULL THEN 'active' ELSE 'rejected' END
                      AS registry_state
           FROM entities e
           JOIN entity_channels ec ON ec.entity_id = e.id
           JOIN channels c ON c.id = ec.channel_id AND c.kind = 'x'
           LEFT JOIN accounts a ON a.platform = 'x' AND a.handle = c.key
           LEFT JOIN entity_registry_rejections rejected ON rejected.entity_id = e.id"""
    ).fetchall()
    conn.close()
    by_handle: dict[str, dict[str, Any]] = {}
    by_x_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = dict(row)
        handle = str(row["handle"] or "").lower()
        if handle:
            by_handle[handle] = item
        x_id = str(row["x_id"] or "")
        if x_id:
            by_x_id[x_id] = item
    return by_handle, by_x_id


def _registry_maps() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    return _registry_maps_cached(_db_version(DEFAULT_REGISTRY_DB))


def _registry_account(
    x_id: str | None,
    handle: str,
    by_handle: dict[str, dict[str, Any]],
    by_x_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    return (by_x_id.get(x_id or "") if x_id else None) or by_handle.get(handle.lower())


@lru_cache(maxsize=8)
def _network_support_cached(
    version: tuple[str, int, int, int, int],
) -> tuple[dict[str, int], dict[str, int], dict[str, Any] | None]:
    path = Path(version[0])
    if not path.is_file():
        return {}, {}, None
    conn = _open_readonly(path)
    run = conn.execute(
        """SELECT r.run_id, r.context_id, r.algorithm, r.completed_at,
                  c.snapshot_id
           FROM ranking_run r
           JOIN analysis_context c ON c.context_id = r.context_id
           WHERE r.algorithm = ?
           ORDER BY r.completed_at DESC, r.run_id DESC LIMIT 1""",
        (following_rankings.OVERLAP_ALGORITHM,),
    ).fetchone()
    if run is None:
        conn.close()
        return {}, {}, None
    rows = conn.execute(
        """SELECT rr.x_id, rr.cohort_follow_count, rr.position
           FROM ranking_result rr WHERE rr.run_id = ?""",
        (run["run_id"],),
    ).fetchall()
    conn.close()
    return (
        {row["x_id"]: row["cohort_follow_count"] for row in rows},
        {row["x_id"]: row["position"] for row in rows},
        dict(run),
    )


def _network_support() -> tuple[dict[str, int], dict[str, int], dict[str, Any] | None]:
    path = _latest_analysis_db()
    if path is None:
        return {}, {}, None
    return _network_support_cached(_db_version(path))


def _candidate_rows(
    conn: sqlite3.Connection, run_id: str, day: str
) -> list[sqlite3.Row]:
    return conn.execute(
        """WITH candidate(provider, post_id) AS (
               SELECT rp.provider, rp.post_id
               FROM feed_run_post rp
               JOIN feed_post direct INDEXED BY idx_feed_post_day
                 ON direct.run_id = rp.run_id
                AND direct.provider = rp.provider AND direct.post_id = rp.post_id
               WHERE rp.run_id = ? AND rp.role = 'direct'
                 AND direct.day = ? AND direct.first_discovered_day <= ?
                 AND direct.post_type != 'retweet'
               UNION
               SELECT relation.provider, relation.target_post_id
               FROM feed_relation relation
               JOIN feed_post source
                 ON source.run_id = relation.run_id
                AND source.provider = relation.provider
                AND source.post_id = relation.source_post_id
               JOIN feed_run_post source_membership
                 ON source_membership.run_id = relation.run_id
                AND source_membership.provider = relation.provider
                AND source_membership.post_id = relation.source_post_id
                AND source_membership.role = 'direct'
               WHERE relation.run_id = ? AND source.day = ?
                 AND relation.discovered_day <= ?
           )
           SELECT post.*,
                  EXISTS (
                      SELECT 1 FROM feed_run_post rp
                      WHERE rp.run_id = ? AND rp.provider = post.provider
                        AND rp.post_id = post.post_id AND rp.role = 'direct'
                  ) AS observed_directly
           FROM candidate
           JOIN feed_post post
             ON post.run_id = ? AND post.provider = candidate.provider
            AND post.post_id = candidate.post_id""",
        (run_id, day, day, run_id, day, day, run_id, run_id),
    ).fetchall()


def _relation_rows(
    conn: sqlite3.Connection, run_id: str, day: str
) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT relation.*, source.day AS source_day,
                  source.url AS source_url, source.text AS source_text,
                  target.author_handle AS target_handle
           FROM feed_relation relation
           JOIN feed_post source
             ON source.run_id = relation.run_id
            AND source.provider = relation.provider
            AND source.post_id = relation.source_post_id
           JOIN feed_run_post source_membership
             ON source_membership.run_id = relation.run_id
            AND source_membership.provider = relation.provider
            AND source_membership.post_id = relation.source_post_id
            AND source_membership.role = 'direct'
           JOIN feed_post target
             ON target.run_id = relation.run_id
            AND target.provider = relation.provider
            AND target.post_id = relation.target_post_id
           WHERE relation.run_id = ? AND source.day = ?
             AND relation.discovered_day <= ?
             AND target.first_discovered_day <= ?""",
        (run_id, day, day, day),
    ).fetchall()


def _percentiles(values: list[float]) -> dict[float, float]:
    ordered = sorted(values)
    if not ordered or ordered[-1] <= 0:
        return {value: 0.0 for value in values}
    denominator = max(len(ordered) - 1, 1)
    # bisect_left: a value's percentile counts only items strictly below it,
    # so the large one-amplifier tie block sits at the bottom instead of the
    # top of its range.
    return {
        value: bisect.bisect_left(ordered, value) / denominator
        for value in set(values)
    }


def _public_engagement(row: sqlite3.Row) -> int:
    return sum(
        int(row[key] or 0)
        for key in ("like_count", "reply_count", "retweet_count", "quote_count")
    )


def _apply_attention_scores(items: list[dict[str, Any]]) -> None:
    """Apply attention-v1.1 without weighting one Registry vote by prestige."""
    network_pct = _percentiles([float(item["_network_raw"]) for item in items])
    origin_pct = _percentiles([float(item["_originator_support"]) for item in items])
    engagement_pct = _percentiles([math.log1p(item["_engagement"]) for item in items])
    for item in items:
        n = network_pct[float(item["_network_raw"])]
        o = origin_pct[float(item["_originator_support"])]
        e = engagement_pct[math.log1p(item["_engagement"])]
        item["attention_score"] = round(100 * (0.55 * n + 0.25 * o + 0.20 * e), 1)
        item["score_components"] = {
            "registry_amplifiers": item.pop("_amplifier_count"),
            "originator_network_support": item.pop("_originator_support"),
            "originator_network_rank": item.pop("_originator_rank"),
            "public_interactions": item.pop("_engagement"),
            "network_attention_percentile": round(n, 3),
            "originator_support_percentile": round(o, 3),
            "public_engagement_percentile": round(e, 3),
        }
        item.pop("_network_raw")


def _iso_day(value: str) -> str:
    return date.fromisoformat(value).isoformat()


def dates_payload(*, run_id: str | None = None) -> dict[str, Any]:
    if not DEFAULT_FEED_DB.is_file():
        return {
            "available": False,
            "reason": "No Feed store found. Run `fli signal-feed refresh` first.",
        }
    conn = _open_readonly(DEFAULT_FEED_DB)
    run = (
        conn.execute("SELECT * FROM feed_run WHERE run_id = ?", (run_id,)).fetchone()
        if run_id
        else _latest_run(conn)
    )
    if run is None:
        conn.close()
        return {"available": False, "reason": "Feed store has no materialized run."}
    days = [
        row[0]
        for row in conn.execute(
            """SELECT DISTINCT post.day
               FROM feed_run_post rp
               JOIN feed_post post
                 ON post.run_id = rp.run_id AND post.provider = rp.provider
                AND post.post_id = rp.post_id
               WHERE rp.run_id = ? AND rp.role = 'direct'
               ORDER BY post.day""",
            (run["run_id"],),
        )
    ]
    by_handle, by_x_id = _registry_maps()
    rows = []
    for day in days:
        relations = _relation_rows(conn, run["run_id"], day)
        amplifier_entities: dict[tuple[str, str], set[int]] = defaultdict(set)
        for relation in relations:
            account = _registry_account(
                relation["source_author_x_id"],
                relation["source_author_handle"],
                by_handle,
                by_x_id,
            )
            if account and account["registry_state"] == "active":
                amplifier_entities[
                    (str(relation["provider"]), str(relation["target_post_id"]))
                ].add(
                    int(account["entity_id"])
                )
        item_count = 0
        for candidate in _candidate_rows(conn, run["run_id"], day):
            author = _registry_account(
                candidate["author_x_id"],
                candidate["author_handle"],
                by_handle,
                by_x_id,
            )
            if author and author["registry_state"] == "rejected":
                continue
            direct_active = bool(
                candidate["observed_directly"]
                and author
                and author["registry_state"] == "active"
            )
            author_id = int(author["entity_id"]) if author else None
            active_amplifiers = {
                entity_id
                for entity_id in amplifier_entities.get(
                    (str(candidate["provider"]), str(candidate["post_id"])), set()
                )
                if entity_id != author_id
            }
            if direct_active or active_amplifiers:
                item_count += 1
        rows.append({"day": day, "item_count": item_count})
    conn.close()
    return {
        "available": True,
        "latest_complete_date": run["date_to"],
        "date_from": run["date_from"],
        "date_to": run["date_to"],
        "run_id": run["run_id"],
        "dates": rows,
    }


def feed_payload(
    *,
    day: str,
    lane: str,
    sort: str,
    query: str,
    limit: int,
    offset: int,
    run_id: str | None = None,
) -> dict[str, Any]:
    requested_day = _iso_day(day)
    if not DEFAULT_FEED_DB.is_file():
        return {"available": False, "reason": "No Feed store found."}
    conn = _open_readonly(DEFAULT_FEED_DB)
    run = (
        conn.execute("SELECT * FROM feed_run WHERE run_id = ?", (run_id,)).fetchone()
        if run_id
        else _latest_run(conn)
    )
    if run is None:
        conn.close()
        return {"available": False, "reason": "Feed store has no materialized run."}
    candidates = _candidate_rows(conn, run["run_id"], requested_day)
    relations = _relation_rows(conn, run["run_id"], requested_day)

    by_handle, by_x_id = _registry_maps()
    support, positions, ranking_run = _network_support()
    active_entity_support: dict[int, int] = defaultdict(int)
    for account in by_handle.values():
        if account["registry_state"] != "active":
            continue
        x_id = str(account.get("x_id") or "")
        active_entity_support[int(account["entity_id"])] = max(
            active_entity_support[int(account["entity_id"])], support.get(x_id, 0)
        )

    amplifiers: dict[tuple[str, str], dict[int, dict[str, Any]]] = defaultdict(dict)
    contexts: dict[tuple[str, str], dict[str, Any]] = {}
    for relation in relations:
        account = _registry_account(
            relation["source_author_x_id"],
            relation["source_author_handle"],
            by_handle,
            by_x_id,
        )
        if account and account["registry_state"] == "active":
            entity_id = int(account["entity_id"])
            target_key = (
                str(relation["provider"]),
                str(relation["target_post_id"]),
            )
            existing = amplifiers[target_key].get(entity_id)
            candidate = {
                "entity_id": entity_id,
                "entity_name": account["entity_name"],
                "entity_kind": account["entity_kind"],
                "handle": relation["source_author_handle"],
                "relation_type": relation["relation_type"],
                "network_support": active_entity_support.get(entity_id, 0),
                "source_url": relation["source_url"],
            }
            if existing is None or candidate["relation_type"] == "quote":
                amplifiers[target_key][entity_id] = candidate
        if relation["relation_type"] == "quote":
            contexts[
                (str(relation["provider"]), str(relation["source_post_id"]))
            ] = {
                "target_post_id": relation["target_post_id"],
                "target_handle": relation["target_handle"],
            }

    items: list[dict[str, Any]] = []
    for row in candidates:
        author_account = _registry_account(
            row["author_x_id"], row["author_handle"], by_handle, by_x_id
        )
        if author_account and author_account["registry_state"] == "rejected":
            continue
        direct_active = bool(
            row["observed_directly"]
            and author_account
            and author_account["registry_state"] == "active"
        )
        candidate_key = (str(row["provider"]), str(row["post_id"]))
        amp_values = sorted(
            (
                amplifier
                for entity_id, amplifier in amplifiers.get(candidate_key, {}).items()
                if not author_account or entity_id != int(author_account["entity_id"])
            ),
            key=lambda item: (-item["network_support"], item["entity_name"]),
        )
        if not direct_active and not amp_values:
            continue
        author_support = support.get(str(row["author_x_id"] or ""), 0)
        items.append(
            {
                "provider": row["provider"],
                "post_id": row["post_id"],
                "raw_sha256": row["raw_sha256"],
                "author": {
                    "x_id": row["author_x_id"],
                    "handle": row["author_handle"],
                    "name": row["author_name"] or row["author_handle"],
                    "entity_id": author_account["entity_id"] if author_account else None,
                    "entity_name": author_account["entity_name"] if author_account else None,
                    "entity_kind": author_account["entity_kind"] if author_account else None,
                },
                "published_at": row["published_at"],
                "text": row["text"],
                "url": row["url"],
                "post_type": row["post_type"],
                "observed_directly": direct_active,
                "context": contexts.get(candidate_key),
                "amplifiers": amp_values,
                "metrics": {
                    "likes": row["like_count"],
                    "replies": row["reply_count"],
                    "reposts": row["retweet_count"],
                    "quotes": row["quote_count"],
                    "views": row["view_count"],
                    "bookmarks": row["bookmark_count"],
                },
                "_network_raw": len(amp_values),
                "_amplifier_count": len(amp_values),
                "_originator_support": author_support,
                "_originator_rank": positions.get(str(row["author_x_id"] or "")),
                "_engagement": _public_engagement(row),
            }
        )
    conn.close()

    _apply_attention_scores(items)

    # Scores are calibrated against the complete visible day so switching a
    # lane or searching never changes an item's score.
    needle = query.strip().lower()
    items = [
        item
        for item in items
        if (lane != "network" or item["amplifiers"])
        and (lane != "firsthand" or item["observed_directly"])
        and (
            not needle
            or needle
            in (
                f"{item['author']['name']} {item['author']['entity_name'] or ''} "
                f"{item['author']['handle']} {item['text']}"
            ).lower()
        )
    ]

    if sort == "recent":
        items.sort(key=lambda item: (item["published_at"], item["post_id"]), reverse=True)
    elif sort == "engagement":
        items.sort(
            key=lambda item: (
                item["score_components"]["public_interactions"],
                item["published_at"],
                item["post_id"],
            ),
            reverse=True,
        )
    else:
        items.sort(
            key=lambda item: (
                item["attention_score"],
                item["score_components"]["registry_amplifiers"],
                item["score_components"]["originator_network_support"],
                item["score_components"]["public_interactions"],
                item["published_at"],
                item["post_id"],
            ),
            reverse=True,
        )
    total = len(items)
    visible = items[offset : offset + limit]
    return {
        "available": True,
        "date": requested_day,
        "lane": lane,
        "sort": sort,
        "query": query,
        "total": total,
        "limit": limit,
        "offset": offset,
        "run": {
            "run_id": run["run_id"],
            "date_from": run["date_from"],
            "date_to": run["date_to"],
            "source_post_count": run["source_post_count"],
            "normalized_post_count": run["normalized_post_count"],
            "relation_count": run["relation_count"],
            "ranking": ranking_run,
        },
        "score_formula": SCORE_FORMULA,
        "items": visible,
    }
