"""Registry-aware read model for exact structural event groups."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from fli import signal_events, signal_feed
from fli.web import feed as feed_store


DEFAULT_EVENTS_DB = signal_events.DEFAULT_EVENTS_DB
DEFAULT_FEED_DB = signal_feed.DEFAULT_FEED_DB


def _open_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _latest_run(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM event_run ORDER BY created_at DESC, run_id DESC LIMIT 1"
    ).fetchone()


def _event_rows(
    events: sqlite3.Connection, run_id: str, day: str
) -> tuple[list[sqlite3.Row], list[sqlite3.Row], list[sqlite3.Row]]:
    clusters = events.execute(
        """SELECT cluster.*
           FROM event_day day
           JOIN event_cluster cluster
             ON cluster.run_id = day.run_id AND cluster.event_id = day.event_id
           WHERE day.run_id = ? AND day.day = ?
           ORDER BY cluster.event_id""",
        (run_id, day),
    ).fetchall()
    if not clusters:
        return [], [], []
    event_ids = [row["event_id"] for row in clusters]
    placeholders = ",".join("?" for _ in event_ids)
    parameters = (run_id, *event_ids)
    members = events.execute(
        f"""SELECT * FROM event_member
            WHERE run_id = ? AND event_id IN ({placeholders})
            ORDER BY event_id, is_representative DESC, post_id""",
        parameters,
    ).fetchall()
    links = events.execute(
        f"""SELECT * FROM event_link
            WHERE run_id = ? AND event_id IN ({placeholders})
            ORDER BY event_id, link_type, source_post_id, target_post_id""",
        parameters,
    ).fetchall()
    return clusters, members, links


def events_payload(
    *,
    day: str,
    lane: str,
    sort: str,
    query: str,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    if not DEFAULT_EVENTS_DB.is_file():
        return {
            "available": False,
            "reason": "No Event store found. Run `fli signal-events refresh` first.",
        }
    if not DEFAULT_FEED_DB.is_file():
        return {"available": False, "reason": "No Feed store found."}

    events = _open_readonly(DEFAULT_EVENTS_DB)
    run = _latest_run(events)
    if run is None:
        events.close()
        return {"available": False, "reason": "Event store has no materialized run."}
    clusters, member_rows, link_rows = _event_rows(events, run["run_id"], day)
    events.close()

    feed_result = feed_store.feed_payload(
        day=day,
        lane="all",
        sort="attention",
        query="",
        limit=5000,
        offset=0,
    )
    if not feed_result.get("available"):
        return feed_result
    feed_items = feed_result.get("items") or []
    candidates = {item["post_id"]: item for item in feed_items}

    feed = _open_readonly(DEFAULT_FEED_DB)
    post_rows = feed.execute(
        """SELECT post.*
           FROM feed_post post
           WHERE post.run_id = ?""",
        (run["feed_run_id"],),
    ).fetchall()
    feed.close()
    posts = {(row["provider"], row["post_id"]): row for row in post_rows}
    by_handle, by_x_id = feed_store._registry_maps()

    members_by_event: dict[str, list[sqlite3.Row]] = {}
    for member in member_rows:
        members_by_event.setdefault(member["event_id"], []).append(member)
    links_by_event: dict[str, list[sqlite3.Row]] = {}
    for link in link_rows:
        links_by_event.setdefault(link["event_id"], []).append(link)

    items: list[dict[str, Any]] = []
    for cluster in clusters:
        event_id = cluster["event_id"]
        raw_members = members_by_event.get(event_id, [])
        visible_members: list[dict[str, Any]] = []
        visible_keys: set[tuple[str, str]] = set()
        for member in raw_members:
            row = posts.get((member["provider"], member["post_id"]))
            if row is None:
                continue
            account = feed_store._registry_account(
                row["author_x_id"], row["author_handle"], by_handle, by_x_id
            )
            if account and account["registry_state"] == "rejected":
                continue
            visible_keys.add((member["provider"], member["post_id"]))
            visible_members.append(
                {
                    "post_id": row["post_id"],
                    "author": {
                        "handle": row["author_handle"],
                        "name": row["author_name"] or row["author_handle"],
                        "entity_id": account["entity_id"] if account else None,
                        "entity_name": account["entity_name"] if account else None,
                    },
                    "published_at": row["published_at"],
                    "text": row["text"],
                    "url": row["url"],
                    "post_type": row["post_type"],
                    "observed_directly": bool(member["observed_directly"]),
                    "is_representative": bool(member["is_representative"]),
                }
            )
        current_links = [
            link
            for link in links_by_event.get(event_id, [])
            if (link["provider"], link["source_post_id"]) in visible_keys
            and (link["provider"], link["target_post_id"]) in visible_keys
        ]
        event_candidates = [
            candidates[member["post_id"]]
            for member in raw_members
            if member["post_id"] in candidates
        ]
        if len(visible_members) < 2 or not current_links or not event_candidates:
            continue

        configured_id = cluster["representative_post_id"]
        representative = candidates.get(configured_id)
        if representative is None:
            representative = max(
                event_candidates,
                key=lambda item: (
                    item["attention_score"],
                    item["published_at"],
                    item["post_id"],
                ),
            )
        anchor_types = sorted(
            {
                "same_target"
                if link["link_type"] in ("quote", "retweet")
                else "same_conversation"
                for link in current_links
            }
        )
        why_grouped = [
            label
            for anchor, label in (
                ("same_target", "Exact same quoted or reposted post"),
                ("same_conversation", "Exact same conversation or reply parent"),
            )
            if anchor in anchor_types
        ]
        registry_entity_ids = {
            member["author"]["entity_id"]
            for member in visible_members
            if member["author"]["entity_id"] is not None
        }
        amplifiers: dict[int, dict[str, Any]] = {}
        for candidate in event_candidates:
            for amplifier in candidate["amplifiers"]:
                amplifiers[amplifier["entity_id"]] = amplifier
                registry_entity_ids.add(amplifier["entity_id"])
        visible_members.sort(
            key=lambda member: (
                not member["is_representative"],
                {"original": 0, "reply": 1, "quote": 2, "retweet": 3}.get(
                    member["post_type"], 9
                ),
                member["published_at"],
                member["post_id"],
            )
        )
        peak_attention = max(item["attention_score"] for item in event_candidates)
        peak_interactions = max(
            item["score_components"]["public_interactions"]
            for item in event_candidates
        )
        latest_evidence_at = max(
            item["published_at"] for item in event_candidates
        )
        items.append(
            {
                "event_id": event_id,
                "representative": representative,
                "why_grouped": why_grouped,
                "anchor_types": anchor_types,
                "member_count": len(visible_members),
                "link_count": len(current_links),
                "author_count": len(
                    {member["author"]["handle"] for member in visible_members}
                ),
                "registry_account_count": len(registry_entity_ids),
                "first_hand_count": sum(
                    1 for item in event_candidates if item["observed_directly"]
                ),
                "amplifiers": sorted(
                    amplifiers.values(),
                    key=lambda amplifier: (
                        -amplifier["network_support"], amplifier["entity_name"]
                    ),
                ),
                "peak_attention_score": peak_attention,
                "peak_public_interactions": peak_interactions,
                "latest_evidence_at": latest_evidence_at,
                "evidence": visible_members,
            }
        )

    needle = query.strip().lower()
    items = [
        item
        for item in items
        if (lane != "network" or item["amplifiers"])
        and (lane != "firsthand" or item["first_hand_count"] > 0)
        and (
            not needle
            or needle
            in " ".join(
                f"{member['author']['name']} {member['author']['entity_name'] or ''} "
                f"{member['author']['handle']} {member['text']}"
                for member in item["evidence"]
            ).lower()
        )
    ]
    if sort == "recent":
        items.sort(
            key=lambda item: (item["latest_evidence_at"], item["event_id"]),
            reverse=True,
        )
    elif sort == "engagement":
        items.sort(
            key=lambda item: (
                item["peak_public_interactions"],
                item["latest_evidence_at"],
                item["event_id"],
            ),
            reverse=True,
        )
    else:
        items.sort(
            key=lambda item: (
                item["peak_attention_score"],
                item["registry_account_count"],
                item["member_count"],
                item["latest_evidence_at"],
                item["event_id"],
            ),
            reverse=True,
        )
    total = len(items)
    return {
        "available": True,
        "date": day,
        "lane": lane,
        "sort": sort,
        "query": query,
        "total": total,
        "limit": limit,
        "offset": offset,
        "run": {
            "run_id": run["run_id"],
            "feed_run_id": run["feed_run_id"],
            "clustering_contract": run["clustering_contract"],
            "cluster_count": run["cluster_count"],
            "member_count": run["member_count"],
            "link_count": run["link_count"],
        },
        "score_formula": {
            **feed_result["score_formula"],
            "note": (
                "Groups use exact structural links only. Peak attention is the "
                "highest unchanged Feed attention score among visible evidence."
            ),
        },
        "items": items[offset : offset + limit],
    }


def dates_payload() -> dict[str, Any]:
    feed_dates = feed_store.dates_payload()
    if not feed_dates.get("available"):
        return feed_dates
    if not DEFAULT_EVENTS_DB.is_file():
        return {
            "available": False,
            "reason": "No Event store found. Run `fli signal-events refresh` first.",
        }
    events = _open_readonly(DEFAULT_EVENTS_DB)
    run = _latest_run(events)
    if run is None:
        events.close()
        return {"available": False, "reason": "Event store has no materialized run."}
    members = events.execute(
        "SELECT * FROM event_member WHERE run_id = ?", (run["run_id"],)
    ).fetchall()
    links = events.execute(
        "SELECT * FROM event_link WHERE run_id = ?", (run["run_id"],)
    ).fetchall()
    event_days = events.execute(
        "SELECT event_id, day FROM event_day WHERE run_id = ?", (run["run_id"],)
    ).fetchall()
    events.close()

    feed = _open_readonly(DEFAULT_FEED_DB)
    post_rows = feed.execute(
        "SELECT * FROM feed_post WHERE run_id = ?", (run["feed_run_id"],)
    ).fetchall()
    feed.close()
    posts = {(row["provider"], row["post_id"]): row for row in post_rows}
    by_handle, by_x_id = feed_store._registry_maps()
    account_by_post: dict[tuple[str, str], dict[str, Any] | None] = {}
    for key, post in posts.items():
        account_by_post[key] = feed_store._registry_account(
            post["author_x_id"], post["author_handle"], by_handle, by_x_id
        )

    visible_by_event: dict[str, set[tuple[str, str]]] = {}
    active_days_by_event: dict[str, set[str]] = {}
    observed_directly: set[tuple[str, str]] = set()
    for member in members:
        key = (member["provider"], member["post_id"])
        post = posts.get(key)
        if post is None:
            continue
        account = account_by_post[key]
        if account and account["registry_state"] == "rejected":
            continue
        visible_by_event.setdefault(member["event_id"], set()).add(key)
        if member["observed_directly"]:
            observed_directly.add(key)
        if (
            member["observed_directly"]
            and post["post_type"] != "retweet"
            and account
            and account["registry_state"] == "active"
        ):
            active_days_by_event.setdefault(member["event_id"], set()).add(post["day"])

    current_links_by_event: dict[str, int] = {}
    for link in links:
        visible = visible_by_event.get(link["event_id"], set())
        source = (link["provider"], link["source_post_id"])
        target = (link["provider"], link["target_post_id"])
        if source not in visible or target not in visible:
            continue
        current_links_by_event[link["event_id"]] = (
            current_links_by_event.get(link["event_id"], 0) + 1
        )
        if link["link_type"] in ("quote", "retweet"):
            source_post = posts[source]
            source_account = account_by_post[source]
            target_account = account_by_post[target]
            target_is_active_direct = bool(
                target in observed_directly
                and target_account
                and target_account["registry_state"] == "active"
            )
            self_amplification = bool(
                source_account
                and target_account
                and source_account["entity_id"] == target_account["entity_id"]
            )
            source_is_active_amplifier = bool(
                source_account
                and source_account["registry_state"] == "active"
                and not self_amplification
            )
            if target_is_active_direct or source_is_active_amplifier:
                active_days_by_event.setdefault(link["event_id"], set()).add(
                    source_post["day"]
                )

    counts = {item["day"]: 0 for item in feed_dates.get("dates") or []}
    for event_day in event_days:
        event_id = event_day["event_id"]
        day = event_day["day"]
        if (
            len(visible_by_event.get(event_id, set())) >= 2
            and current_links_by_event.get(event_id, 0) > 0
            and day in active_days_by_event.get(event_id, set())
        ):
            counts[day] = counts.get(day, 0) + 1
    rows = [
        {"day": item["day"], "item_count": counts.get(item["day"], 0)}
        for item in feed_dates.get("dates") or []
    ]
    return {
        "available": True,
        "latest_complete_date": feed_dates["latest_complete_date"],
        "date_from": feed_dates["date_from"],
        "date_to": feed_dates["date_to"],
        "run_id": run["run_id"],
        "dates": rows,
    }
