"""Registry-aware unified Feed envelopes over exact structural relationships."""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any

from fli import signal_events, signal_feed
from fli.web import feed as feed_store, triage as triage_store


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
            ORDER BY event_id, post_id""",
        parameters,
    ).fetchall()
    links = events.execute(
        f"""SELECT * FROM event_link
            WHERE run_id = ? AND event_id IN ({placeholders})
            ORDER BY event_id, link_type, source_post_id, target_post_id""",
        parameters,
    ).fetchall()
    return clusters, members, links


def _root_post_id(
    members: list[dict[str, Any]], links: list[sqlite3.Row], candidates: set[str]
) -> str:
    """Choose the exact relationship root, constrained to ranked Feed candidates."""
    inbound: dict[str, int] = {}
    outbound: dict[str, list[str]] = {}
    for link in links:
        inbound[link["target_post_id"]] = inbound.get(link["target_post_id"], 0) + 1
        outbound.setdefault(link["source_post_id"], []).append(link["link_type"])
    type_priority = {"original": 0, "reply": 1, "quote": 2, "retweet": 3}
    eligible = [member for member in members if member["post_id"] in candidates]
    return min(
        eligible,
        key=lambda member: (
            -inbound.get(member["post_id"], 0),
            bool(outbound.get(member["post_id"])),
            type_priority.get(member["post_type"], 9),
            not member["observed_directly"],
            member["published_at"],
            member["post_id"],
        ),
    )["post_id"]


def _relationship_rows(
    members: list[dict[str, Any]], links: list[sqlite3.Row], root_post_id: str
) -> list[dict[str, Any]]:
    """Return exact related evidence in parent-before-child display order."""
    root = next(member for member in members if member["post_id"] == root_post_id)
    link_priority = {"reply_parent": 0, "quote": 1, "retweet": 2, "same_conversation": 3}
    source_links: dict[str, list[sqlite3.Row]] = {}
    for link in links:
        source_links.setdefault(link["source_post_id"], []).append(link)
    for values in source_links.values():
        values.sort(key=lambda link: link_priority.get(link["link_type"], 9))

    payloads: list[dict[str, Any]] = []
    for member in members:
        if member["post_id"] == root_post_id:
            continue
        link = source_links.get(member["post_id"], [None])[0]
        link_type = link["link_type"] if link is not None else None
        target_post_id = link["target_post_id"] if link is not None else None
        if member["post_type"] == "reply" or link_type in (
            "reply_parent",
            "same_conversation",
        ):
            relationship = "reply"
            parent_post_id = member.get("in_reply_to_post_id") or (
                target_post_id if link_type == "reply_parent" else None
            )
        elif member["post_type"] == "quote" or link_type == "quote":
            relationship = "quote"
            parent_post_id = target_post_id
        elif member["post_type"] == "retweet" or link_type == "retweet":
            relationship = "retweet"
            parent_post_id = None
        else:
            relationship = "related"
            parent_post_id = None
        payloads.append(
            {
                **member,
                "relationship": relationship,
                "relation_type": link_type,
                "target_post_id": target_post_id,
                "parent_post_id": parent_post_id,
                "parent_missing": False,
                "same_author_as_root": (
                    member["author"]["handle"].lower()
                    == root["author"]["handle"].lower()
                ),
            }
        )

    narrative = [payload for payload in payloads if payload["relationship"] != "retweet"]
    narrative_by_id = {payload["post_id"]: payload for payload in narrative}
    captured_parent_ids = {root_post_id, *narrative_by_id}
    children: dict[str, list[dict[str, Any]]] = {}
    unparented: list[dict[str, Any]] = []
    for payload in narrative:
        parent_id = payload["parent_post_id"]
        if parent_id == root_post_id or parent_id in narrative_by_id:
            children.setdefault(parent_id, []).append(payload)
            continue
        payload["parent_missing"] = bool(
            payload["relationship"] == "reply"
            and parent_id not in captured_parent_ids
        )
        unparented.append(payload)

    order_key = lambda payload: (payload["published_at"], payload["post_id"])
    for siblings in children.values():
        siblings.sort(key=order_key)
    unparented.sort(key=order_key)

    ordered: list[dict[str, Any]] = []
    visited: set[str] = set()

    def visit(parent_id: str, depth: int) -> None:
        for child in children.get(parent_id, []):
            post_id = child["post_id"]
            if post_id in visited:
                continue
            visited.add(post_id)
            child["depth"] = depth
            ordered.append(child)
            visit(post_id, depth + 1)

    visit(root_post_id, 1)
    for payload in unparented:
        if payload["post_id"] in visited:
            continue
        visited.add(payload["post_id"])
        payload["depth"] = 1
        ordered.append(payload)
        visit(payload["post_id"], 2)
    for payload in sorted(narrative, key=order_key):
        if payload["post_id"] in visited:
            continue
        payload["parent_missing"] = payload["relationship"] == "reply"
        payload["depth"] = 1
        visited.add(payload["post_id"])
        ordered.append(payload)
        visit(payload["post_id"], 2)

    retweets = [payload for payload in payloads if payload["relationship"] == "retweet"]
    for payload in retweets:
        payload["depth"] = 0
    retweets.sort(key=order_key)
    return [*ordered, *retweets]


def _singleton(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": f"post:{item['post_id']}",
        "is_grouped": False,
        "root": item,
        "why_grouped": [],
        "anchor_types": [],
        "member_count": 1,
        "link_count": 0,
        "author_count": 1,
        "registry_account_count": 1 if item["author"]["entity_id"] is not None else 0,
        "first_hand_count": int(item["observed_directly"]),
        "amplifiers": item["amplifiers"],
        "peak_attention_score": item["attention_score"],
        "peak_public_interactions": item["score_components"]["public_interactions"],
        "latest_evidence_at": item["published_at"],
        "evidence": [],
    }


def _cache_token(day: str) -> tuple[tuple[str, int, int, int, int], ...]:
    paths = [DEFAULT_EVENTS_DB, DEFAULT_FEED_DB, feed_store.DEFAULT_REGISTRY_DB]
    analysis = feed_store._latest_analysis_db()
    if analysis is not None:
        paths.append(analysis)
    return (
        *(feed_store._db_version(path) for path in paths),
        *triage_store.cache_token(day),
    )


@lru_cache(maxsize=16)
def _events_day_cached(
    *,
    day: str,
    cache_token: tuple[tuple[str, int, int, int, int], ...],
) -> dict[str, Any]:
    """Build one reusable day projection over exact Feed relationships."""
    del cache_token  # used only to invalidate this read-model cache
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
        "SELECT * FROM feed_post WHERE run_id = ?", (run["feed_run_id"],)
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

    triage_payload = triage_store.triage_payload(day)
    triage_items = triage_payload["items"]
    items: list[dict[str, Any]] = []
    consumed: set[str] = set()
    for cluster in clusters:
        event_id = cluster["event_id"]
        visible_members: list[dict[str, Any]] = []
        visible_keys: set[tuple[str, str]] = set()
        for member in members_by_event.get(event_id, []):
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
                    "conversation_id": row["conversation_id"],
                    "in_reply_to_post_id": row["in_reply_to_post_id"],
                    "observed_directly": bool(member["observed_directly"]),
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
            for member in visible_members
            if member["post_id"] in candidates
        ]
        if len(visible_members) < 2 or not current_links or not event_candidates:
            continue

        root_post_id = _root_post_id(
            visible_members, current_links, {item["post_id"] for item in event_candidates}
        )
        root = candidates[root_post_id]
        related = _relationship_rows(visible_members, current_links, root_post_id)
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
            consumed.add(candidate["post_id"])
            for amplifier in candidate["amplifiers"]:
                amplifiers[amplifier["entity_id"]] = amplifier
                registry_entity_ids.add(amplifier["entity_id"])
        items.append(
            {
                "event_id": event_id,
                "is_grouped": True,
                "root": root,
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
                "peak_attention_score": max(
                    item["attention_score"] for item in event_candidates
                ),
                "peak_public_interactions": max(
                    item["score_components"]["public_interactions"]
                    for item in event_candidates
                ),
                "latest_evidence_at": max(
                    member["published_at"] for member in visible_members
                ),
                "evidence": related,
            }
        )

    items.extend(
        _singleton(item) for item in feed_items if item["post_id"] not in consumed
    )
    for item in items:
        item["triage"] = triage_items.get(item["event_id"])
    return {
        "available": True,
        "date": day,
        "triage_run": triage_payload["run"],
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
                "Every Feed candidate is an envelope. Provider-declared exact "
                "relationships combine evidence; all other posts remain singletons."
            ),
        },
        "items": items,
    }


def events_payload(
    *,
    day: str,
    lane: str,
    sort: str,
    query: str,
    triage_filter: str = "all",
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """Return a state-aware view over one cached day projection."""
    payload = _events_day_cached(
        day=day,
        cache_token=_cache_token(day),
    )
    if not payload.get("available"):
        return payload

    needle = query.strip().lower()
    items = [
        item
        for item in payload["items"]
        if (lane != "network" or item["amplifiers"])
        and (lane != "firsthand" or item["first_hand_count"] > 0)
        and (
            not needle
            or needle
            in " ".join(
                [
                    item["root"]["author"]["name"],
                    item["root"]["author"]["entity_name"] or "",
                    item["root"]["author"]["handle"],
                    item["root"]["text"],
                    *[
                        f"{member['author']['name']} "
                        f"{member['author']['entity_name'] or ''} "
                        f"{member['author']['handle']} {member['text']}"
                        for member in item["evidence"]
                    ],
                ]
            ).lower()
        )
    ]
    triage_counts = {
        "all": len(items),
        "keep": sum(
            item["triage"] is not None
            and item["triage"]["decision"] == "keep"
            for item in items
        ),
        "drop": sum(
            item["triage"] is not None
            and item["triage"]["decision"] == "drop"
            for item in items
        ),
        "not_evaluated": sum(item["triage"] is None for item in items),
    }
    if triage_filter == "keep":
        items = [
            item
            for item in items
            if item["triage"] and item["triage"]["decision"] == "keep"
        ]
    elif triage_filter == "drop":
        items = [
            item
            for item in items
            if item["triage"] and item["triage"]["decision"] == "drop"
        ]
    elif triage_filter == "not_evaluated":
        items = [item for item in items if item["triage"] is None]

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
        **{key: value for key, value in payload.items() if key != "items"},
        "lane": lane,
        "sort": sort,
        "query": query,
        "triage_filter": triage_filter,
        "triage_counts": triage_counts,
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items[offset : offset + limit],
    }


def dates_payload() -> dict[str, Any]:
    """Expose fast evidence-ledger counts for each complete Feed day."""
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
    events.close()
    if run is None:
        return {"available": False, "reason": "Event store has no materialized run."}
    return {**feed_dates, "run_id": run["run_id"]}
