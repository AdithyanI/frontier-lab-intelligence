"""Registry-aware unified Feed envelopes over exact structural relationships."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any

from fli import signal_events, signal_feed
from fli.web import audience_routing as audience_routing_store
from fli.web import feed as feed_store


DEFAULT_EVENTS_DB = signal_events.DEFAULT_EVENTS_DB
DEFAULT_FEED_DB = signal_feed.DEFAULT_FEED_DB

FeedKey = tuple[str, str]
_dates_payload_lock = Lock()


def _open_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _latest_run(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return signal_events.published_run(conn)


def _feed_key(item: dict[str, Any]) -> FeedKey:
    """Return the provider-qualified identity of one Feed candidate."""
    return (str(item.get("provider", "twitterapi_io")), str(item["post_id"]))


def _all_feed_candidates(*, day: str, run_id: str) -> dict[str, Any]:
    """Read every ranked candidate once without an API pagination ceiling."""
    result = feed_store.feed_payload(
        day=day,
        lane="all",
        sort="attention",
        query="",
        limit=2**31 - 1,
        offset=0,
        run_id=run_id,
    )
    return {**result, "limit": len(result.get("items") or []), "offset": 0}


def _event_rows(
    events: sqlite3.Connection, run_id: str, day: str
) -> tuple[list[sqlite3.Row], list[sqlite3.Row], list[sqlite3.Row]]:
    clusters = events.execute(
        """SELECT cluster.*,
                  active.direct_member_count AS selected_day_member_count,
                  (SELECT MIN(first.day) FROM event_day first
                   WHERE first.run_id = cluster.run_id
                     AND first.event_id = cluster.event_id)
                      AS first_activity_day,
                  (SELECT MAX(previous.day) FROM event_day previous
                   WHERE previous.run_id = cluster.run_id
                     AND previous.event_id = cluster.event_id
                     AND previous.day < active.day)
                      AS previous_activity_day
           FROM event_day day
           JOIN event_cluster cluster
             ON cluster.run_id = day.run_id AND cluster.event_id = day.event_id
           JOIN event_day active
             ON active.run_id = day.run_id AND active.event_id = day.event_id
            AND active.day = day.day
           WHERE day.run_id = ? AND day.day = ?
           ORDER BY cluster.event_id""",
        (run_id, day),
    ).fetchall()
    if not clusters:
        return [], [], []
    members = events.execute(
        """SELECT member.*
           FROM event_member member
           JOIN event_day day
             ON day.run_id = member.run_id AND day.event_id = member.event_id
           WHERE member.run_id = ? AND day.day = ?
           ORDER BY member.event_id, member.provider, member.post_id""",
        (run_id, day),
    ).fetchall()
    links = events.execute(
        """SELECT link.*
           FROM event_link link
           JOIN event_day day
             ON day.run_id = link.run_id AND day.event_id = link.event_id
           WHERE link.run_id = ? AND day.day = ?
           ORDER BY link.event_id, link.link_type, link.provider,
                    link.source_post_id, link.target_post_id""",
        (run_id, day),
    ).fetchall()
    return clusters, members, links


def _root_post_id(
    members: list[dict[str, Any]], links: list[sqlite3.Row], candidates: set[FeedKey]
) -> str:
    """Choose the exact relationship root, constrained to ranked Feed candidates."""
    inbound: dict[str, int] = {}
    outbound: dict[str, list[str]] = {}
    for link in links:
        inbound[link["target_post_id"]] = inbound.get(link["target_post_id"], 0) + 1
        outbound.setdefault(link["source_post_id"], []).append(link["link_type"])
    type_priority = {"original": 0, "reply": 1, "quote": 2, "retweet": 3}
    eligible = [
        member
        for member in members
        if (str(member["provider"]), str(member["post_id"])) in candidates
    ]
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
    link_priority = {
        "reply_parent": 0,
        "primary_thread": 0,
        "quote": 1,
        "retweet": 2,
    }
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
        if member["post_type"] == "reply" or link_type in {
            "reply_parent",
            "primary_thread",
        }:
            relationship = "reply"
            parent_post_id = member.get("in_reply_to_post_id") or (
                target_post_id
                if link_type in {"reply_parent", "primary_thread"}
                else None
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


def _canonical_event_id(provider: str, identity_value: str) -> str:
    return hashlib.sha256(
        json.dumps(
            [provider, identity_value],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _singleton(item: dict[str, Any]) -> dict[str, Any]:
    provider = str(item.get("provider", "twitterapi_io"))
    singleton_id = _canonical_event_id(provider, str(item["post_id"]))
    snapshot_hash = hashlib.sha256(
        json.dumps(
            [
                singleton_id,
                item.get("provider", "twitterapi_io"),
                item["post_id"],
                item.get("raw_sha256"),
                item["published_at"],
            ],
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return {
        "event_id": singleton_id,
        "canonical_root_post_id": item["post_id"],
        "presentation_root_post_id": item["post_id"],
        "snapshot_cutoff": f"{item['published_at'][:10]}T23:59:59.999999+00:00",
        "snapshot_content_sha256": snapshot_hash,
        "first_activity_day": item["published_at"][:10],
        "previous_activity_day": None,
        "is_continuation": False,
        "is_grouped": False,
        "root": item,
        "why_grouped": [],
        "anchor_types": [],
        "member_count": 1,
        "lifetime_member_count": 1,
        "day_member_count": 1,
        "prior_context_count": 0,
        "link_count": 0,
        "author_count": 1,
        "registry_account_count": 1 if item["author"]["entity_id"] is not None else 0,
        "first_hand_count": int(item["observed_directly"]),
        "amplifiers": item["amplifiers"],
        "peak_attention_score": item["attention_score"],
        "daily_score_basis": _daily_score_basis(item),
        "peak_public_interactions": item["score_components"]["public_interactions"],
        "latest_evidence_at": item["published_at"],
        "evidence": [],
    }


def _daily_score_basis(item: dict[str, Any]) -> dict[str, Any]:
    """Preserve the exact post and components behind an envelope's peak score."""
    return {
        "post_id": item["post_id"],
        "author": dict(item["author"]),
        "published_at": item["published_at"],
        "attention_score": item["attention_score"],
        "score_components": dict(item["score_components"]),
    }


def _root_feed_item(
    row: sqlite3.Row,
    member: dict[str, Any],
    template: dict[str, Any],
    account: dict[str, Any] | None,
) -> dict[str, Any]:
    """Project the stable canonical root with the selected day's score."""
    return {
        **template,
        "provider": str(row["provider"]),
        "post_id": str(row["post_id"]),
        "raw_sha256": str(row["raw_sha256"]),
        "author": {
            "x_id": row["author_x_id"],
            "handle": row["author_handle"],
            "name": row["author_name"] or row["author_handle"],
            "entity_id": account["entity_id"] if account else None,
            "entity_name": account["entity_name"] if account else None,
            "entity_kind": account["entity_kind"] if account else None,
        },
        "published_at": row["published_at"],
        "text": row["text"],
        "url": row["url"],
        "post_type": row["post_type"],
        "observed_directly": bool(member["observed_directly"]),
        "context": None,
        "metrics": {
            "likes": row["like_count"],
            "replies": row["reply_count"],
            "reposts": row["retweet_count"],
            "quotes": row["quote_count"],
            "views": row["view_count"],
            "bookmarks": row["bookmark_count"],
        },
        "score_components": dict(template["score_components"]),
    }


def _cache_token(day: str) -> tuple[tuple[str, int, int, int, int], ...]:
    paths = [DEFAULT_EVENTS_DB, DEFAULT_FEED_DB, feed_store.DEFAULT_REGISTRY_DB]
    analysis = feed_store._latest_analysis_db()
    if analysis is not None:
        paths.append(analysis)
    return (
        *(feed_store._db_version(path) for path in paths),
        *audience_routing_store.cache_token(day),
    )


def _dates_cache_token() -> tuple[tuple[str, int, int, int, int], ...]:
    """Invalidate date counts only when their structural inputs change."""
    return tuple(
        feed_store._db_version(path)
        for path in (
            DEFAULT_EVENTS_DB,
            DEFAULT_FEED_DB,
            feed_store.DEFAULT_REGISTRY_DB,
        )
    )


def _visible_components(
    visible_keys: set[tuple[str, str]],
    cutoff_keys: set[tuple[str, str]],
    links: list[sqlite3.Row],
    posts: dict[tuple[str, str], sqlite3.Row],
) -> list[tuple[set[tuple[str, str]], list[sqlite3.Row]]]:
    """Re-componentize after Registry rejection without losing opaque anchors."""
    adjacency: dict[tuple[str, str], set[tuple[str, str]]] = {
        key: set() for key in visible_keys
    }
    eligible_links: list[sqlite3.Row] = []
    for link in links:
        source = (str(link["provider"]), str(link["source_post_id"]))
        target = (str(link["provider"]), str(link["target_post_id"]))
        # A rejected renderable source cannot silently bridge two surviving
        # groups. A target that is not renderable *at this cutoff* remains an
        # opaque structural anchor even if a later row exists in the full-run
        # post index. Otherwise a future disclosure would rewrite history.
        if source not in visible_keys:
            continue
        if target in cutoff_keys and target not in visible_keys and target in posts:
            continue
        adjacency.setdefault(source, set()).add(target)
        adjacency.setdefault(target, set()).add(source)
        eligible_links.append(link)

    remaining = set(adjacency)
    components: list[tuple[set[tuple[str, str]], list[sqlite3.Row]]] = []
    while remaining:
        seed = min(remaining)
        connected: set[tuple[str, str]] = set()
        frontier = [seed]
        while frontier:
            node = frontier.pop()
            if node in connected:
                continue
            connected.add(node)
            frontier.extend(adjacency.get(node, set()) - connected)
        remaining -= connected
        renderable = connected & visible_keys
        if not renderable:
            continue
        component_links = [
            link
            for link in eligible_links
            if (str(link["provider"]), str(link["source_post_id"])) in connected
            and (str(link["provider"]), str(link["target_post_id"])) in connected
        ]
        components.append((renderable, component_links))
    return components


def _component_root(
    *,
    component_keys: set[tuple[str, str]],
    links: list[sqlite3.Row],
    posts: dict[tuple[str, str], sqlite3.Row],
    canonical_root_key: tuple[str, str],
) -> tuple[str, str]:
    structural = {"quote", "retweet", "reply_parent", "primary_thread"}
    identity_provider, _, identity_value = _component_identity(
        component_keys=component_keys,
        links=links,
    )
    identity_key = (identity_provider, identity_value)
    if identity_key in component_keys:
        return identity_key
    identity_children = {
        (str(link["provider"]), str(link["source_post_id"]))
        for link in links
        if str(link["link_type"]) in structural
        and (str(link["provider"]), str(link["target_post_id"])) == identity_key
    }
    if identity_children:
        return min(
            identity_children,
            key=lambda key: (
                str(posts[key]["first_discovered_at"]),
                str(posts[key]["published_at"]),
                key,
            ),
        )
    if canonical_root_key in component_keys:
        return canonical_root_key
    return min(
        component_keys,
        key=lambda key: (
            str(posts[key]["first_discovered_at"]),
            str(posts[key]["published_at"]),
            key,
        ),
    )


def _component_identity(
    *,
    component_keys: set[tuple[str, str]],
    links: list[sqlite3.Row],
) -> tuple[str, str, str]:
    """Return the cutoff component's own provider identity.

    Full-run clusters are only an index. Deriving the public identity from the
    visible cutoff structure prevents a later bridge from rewriting an older
    day's event IDs and snapshot hashes.
    """
    structural = {"quote", "retweet", "reply_parent", "primary_thread"}
    nodes = set(component_keys)
    outbound: set[tuple[str, str]] = set()
    thread_roots: set[tuple[str, str]] = set()
    for link in links:
        provider = str(link["provider"])
        source = (provider, str(link["source_post_id"]))
        target = (provider, str(link["target_post_id"]))
        nodes.update((source, target))
        if str(link["link_type"]) in structural:
            outbound.add(source)
        if str(link["link_type"]) == "primary_thread":
            thread_roots.add(target)
    terminal_thread_roots = thread_roots - outbound
    identity_node = min(terminal_thread_roots or nodes - outbound or nodes)
    return identity_node[0], "post", identity_node[1]


def _project_component(
    *,
    cluster: sqlite3.Row,
    visible_members: list[dict[str, Any]],
    current_links: list[sqlite3.Row],
    presentation_root_key: tuple[str, str],
    canonical_root_key: tuple[str, str],
    candidates: dict[FeedKey, dict[str, Any]],
    posts: dict[tuple[str, str], sqlite3.Row],
    by_handle: dict[str, dict[str, Any]],
    by_x_id: dict[str, dict[str, Any]],
    day: str,
    consumed: set[FeedKey],
) -> dict[str, Any] | None:
    if len(visible_members) == 1 and not current_links:
        singleton_key = (
            str(visible_members[0]["provider"]),
            str(visible_members[0]["post_id"]),
        )
        singleton_candidate = candidates.get(singleton_key)
        if singleton_candidate is not None:
            consumed.add(singleton_key)
            return _singleton(singleton_candidate)
    event_candidates = [
        candidates[(str(member["provider"]), str(member["post_id"]))]
        for member in visible_members
        if (str(member["provider"]), str(member["post_id"])) in candidates
    ]
    root_member = next(
        (
            member
            for member in visible_members
            if (member["provider"], member["post_id"]) == presentation_root_key
        ),
        None,
    )
    root_row = posts.get(presentation_root_key)
    if not visible_members or not event_candidates or root_member is None or root_row is None:
        return None
    root_account = feed_store._registry_account(
        root_row["author_x_id"], root_row["author_handle"], by_handle, by_x_id
    )
    if root_account and root_account["registry_state"] == "rejected":
        return None

    template = max(
        event_candidates,
        key=lambda item: (
            item["attention_score"],
            item["published_at"],
            item["post_id"],
        ),
    )
    root_key = (str(presentation_root_key[0]), str(presentation_root_key[1]))
    root_post_id = root_key[1]
    root = (
        {
            **candidates[root_key],
            "author": dict(candidates[root_key]["author"]),
            "metrics": dict(candidates[root_key]["metrics"]),
            "score_components": dict(candidates[root_key]["score_components"]),
        }
        if root_key in candidates
        else _root_feed_item(root_row, root_member, template, root_account)
    )
    related = _relationship_rows(visible_members, current_links, root_post_id)
    anchor_types = sorted(
        {
            "same_target"
            if link["link_type"] in ("quote", "retweet")
            else (
                "conversation_root"
                if link["link_type"] == "primary_thread"
                else "reply_parent"
            )
            for link in current_links
        }
    )
    why_grouped = [
        label
        for anchor, label in (
            ("same_target", "Exact same quoted or reposted post"),
            ("reply_parent", "Exact same reply parent"),
            ("conversation_root", "Same author and conversation root"),
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
        consumed.add(_feed_key(candidate))
        for amplifier in candidate["amplifiers"]:
            amplifiers[amplifier["entity_id"]] = amplifier
            registry_entity_ids.add(amplifier["entity_id"])
    sorted_amplifiers = sorted(
        amplifiers.values(),
        key=lambda amplifier: (-amplifier["network_support"], amplifier["entity_name"]),
    )
    root["amplifiers"] = sorted_amplifiers
    root["attention_score"] = max(item["attention_score"] for item in event_candidates)

    identity_provider, identity_type, identity_value = _component_identity(
        component_keys={
            (member["provider"], member["post_id"]) for member in visible_members
        },
        links=current_links,
    )
    projected_event_id = _canonical_event_id(identity_provider, identity_value)
    # The structural identity may be an opaque provider target that has no
    # renderable row at this cutoff. Keep that stable canonical post ID
    # separate from the visible presentation root used by the card.
    canonical_root_post_id = identity_value

    visible_identity = sorted(
        (
            member["provider"],
            member["post_id"],
            member["raw_sha256"],
            member["published_at"],
            member["first_discovered_at"],
            member["disclosure_post_id"],
            int(member["observed_directly"]),
        )
        for member in visible_members
    )
    visible_topology = sorted(
        (
            str(link["provider"]),
            str(link["source_post_id"]),
            str(link["target_post_id"]),
            str(link["link_type"]),
        )
        for link in current_links
    )
    snapshot_content_sha256 = hashlib.sha256(
        json.dumps(
            [
                projected_event_id,
                day,
                identity_type,
                identity_value,
                root_post_id,
                visible_identity,
                visible_topology,
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    direct_days = sorted(
        {
            str(member["day"])
            for member in visible_members
            if member["observed_directly"]
        }
    )
    first_activity_day = direct_days[0] if direct_days else str(cluster["first_activity_day"])
    previous_days = [value for value in direct_days if value < day]
    previous_activity_day = previous_days[-1] if previous_days else None
    day_member_count = sum(int(member["is_new_on_day"]) for member in visible_members)
    prior_context_count = sum(
        1
        for member in visible_members
        if member["post_id"] != root_post_id and str(member["day"]) < day
    )
    return {
        "event_id": projected_event_id,
        "canonical_root_post_id": canonical_root_post_id,
        "presentation_root_post_id": root_post_id,
        "snapshot_cutoff": f"{day}T23:59:59.999999+00:00",
        "snapshot_content_sha256": snapshot_content_sha256,
        "first_activity_day": first_activity_day,
        "previous_activity_day": previous_activity_day,
        "is_continuation": previous_activity_day is not None,
        "is_grouped": len(visible_members) > 1,
        "root": root,
        "why_grouped": why_grouped,
        "anchor_types": anchor_types,
        "member_count": len(visible_members),
        "lifetime_member_count": len(visible_members),
        "day_member_count": day_member_count,
        "prior_context_count": prior_context_count,
        "link_count": len(current_links),
        "author_count": len({member["author"]["handle"] for member in visible_members}),
        "registry_account_count": len(registry_entity_ids),
        "first_hand_count": sum(1 for item in event_candidates if item["observed_directly"]),
        "amplifiers": sorted_amplifiers,
        "peak_attention_score": max(item["attention_score"] for item in event_candidates),
        "daily_score_basis": _daily_score_basis(template),
        "peak_public_interactions": max(
            item["score_components"]["public_interactions"] for item in event_candidates
        ),
        "latest_evidence_at": max(member["published_at"] for member in visible_members),
        "evidence": related,
    }


@lru_cache(maxsize=16)
def _events_day_cached(
    *,
    day: str,
    cache_token: tuple[tuple[str, int, int, int, int], ...],
) -> dict[str, Any]:
    """Build one cutoff-correct day projection over exact relationships."""
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

    feed_result = _all_feed_candidates(day=day, run_id=run["feed_run_id"])
    if not feed_result.get("available"):
        return feed_result
    feed_items = feed_result.get("items") or []
    candidates = {_feed_key(item): item for item in feed_items}

    member_post_keys = sorted(
        {(str(row["provider"]), str(row["post_id"])) for row in member_rows}
    )
    feed = _open_readonly(DEFAULT_FEED_DB)
    if member_post_keys:
        feed.execute(
            "CREATE TEMP TABLE selected_event_post "
            "(provider TEXT NOT NULL, post_id TEXT NOT NULL, "
            "PRIMARY KEY (provider, post_id)) WITHOUT ROWID"
        )
        feed.executemany(
            "INSERT INTO selected_event_post (provider, post_id) VALUES (?, ?)",
            member_post_keys,
        )
        post_rows = feed.execute(
            """SELECT post.*
               FROM selected_event_post selected
               JOIN feed_post post
                 ON post.provider = selected.provider
                AND post.post_id = selected.post_id
               WHERE post.run_id = ?""",
            (run["feed_run_id"],),
        ).fetchall()
    else:
        post_rows = []
    feed.close()
    posts = {(row["provider"], row["post_id"]): row for row in post_rows}
    by_handle, by_x_id = feed_store._registry_maps()

    members_by_event: dict[str, list[sqlite3.Row]] = {}
    for member in member_rows:
        members_by_event.setdefault(member["event_id"], []).append(member)
    links_by_event: dict[str, list[sqlite3.Row]] = {}
    for link in link_rows:
        links_by_event.setdefault(link["event_id"], []).append(link)

    routing_payload = audience_routing_store.routing_payload(day)
    routing_items = routing_payload["items"]
    items: list[dict[str, Any]] = []
    consumed: set[FeedKey] = set()
    for cluster in clusters:
        event_id = cluster["event_id"]
        visible_members: list[dict[str, Any]] = []
        cutoff_keys: set[tuple[str, str]] = set()
        visible_keys: set[tuple[str, str]] = set()
        for member in members_by_event.get(event_id, []):
            row = posts.get((member["provider"], member["post_id"]))
            if (
                row is None
                or str(row["day"]) > day
                or str(row["first_discovered_day"]) > day
            ):
                continue
            member_key = (member["provider"], member["post_id"])
            cutoff_keys.add(member_key)
            account = feed_store._registry_account(
                row["author_x_id"], row["author_handle"], by_handle, by_x_id
            )
            if account and account["registry_state"] == "rejected":
                continue
            visible_keys.add(member_key)
            visible_members.append(
                {
                    "provider": row["provider"],
                    "post_id": row["post_id"],
                    "author": {
                        "x_id": row["author_x_id"],
                        "handle": row["author_handle"],
                        "name": row["author_name"] or row["author_handle"],
                        "entity_id": account["entity_id"] if account else None,
                        "entity_name": account["entity_name"] if account else None,
                        "entity_kind": account["entity_kind"] if account else None,
                    },
                    "published_at": row["published_at"],
                    "day": row["day"],
                    "text": row["text"],
                    "url": row["url"],
                    "post_type": row["post_type"],
                    "conversation_id": row["conversation_id"],
                    "in_reply_to_post_id": row["in_reply_to_post_id"],
                    "raw_sha256": row["raw_sha256"],
                    "first_discovered_at": row["first_discovered_at"],
                    "first_discovered_day": row["first_discovered_day"],
                    "disclosure_post_id": row["disclosure_post_id"],
                    "observed_directly": bool(member["observed_directly"]),
                    "is_new_on_day": bool(
                        member["observed_directly"] and str(row["day"]) == day
                    ),
                }
            )
        current_links = [
            link
            for link in links_by_event.get(event_id, [])
            if str(link["discovered_day"]) <= day
            and (link["provider"], link["source_post_id"]) in cutoff_keys
        ]
        canonical_root_key = (
            str(cluster["representative_provider"]),
            str(cluster["representative_post_id"]),
        )
        member_by_key = {
            (member["provider"], member["post_id"]): member
            for member in visible_members
        }
        for component_keys, component_links in _visible_components(
            visible_keys, cutoff_keys, current_links, posts
        ):
            component_members = [member_by_key[key] for key in sorted(component_keys)]
            presentation_root_key = _component_root(
                component_keys=component_keys,
                links=component_links,
                posts=posts,
                canonical_root_key=canonical_root_key,
            )
            item = _project_component(
                cluster=cluster,
                visible_members=component_members,
                current_links=component_links,
                presentation_root_key=presentation_root_key,
                canonical_root_key=canonical_root_key,
                candidates=candidates,
                posts=posts,
                by_handle=by_handle,
                by_x_id=by_x_id,
                day=day,
                consumed=consumed,
            )
            if item is not None:
                items.append(item)

    items.extend(
        _singleton(item) for item in feed_items if _feed_key(item) not in consumed
    )
    for item in items:
        route = routing_items.get(item["event_id"])
        item["audience_routing"] = (
            route
            if route
            and route.get("snapshot_content_sha256")
            == item["snapshot_content_sha256"]
            else None
        )
    return {
        "available": True,
        "date": day,
        "audience_routing_run": routing_payload["run"],
        "run": {
            "run_id": run["run_id"],
            "feed_run_id": run["feed_run_id"],
            "clustering_contract": run["clustering_contract"],
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


def _events_week_cached(
    *,
    through: str,
) -> dict[str, Any]:
    """Roll the same canonical events through a seven-day UTC window.

    The final daily revision supplies cumulative evidence through week-end;
    attention remains a property of daily activity and is aggregated as the
    highest daily score rather than recomputed from duplicated members.
    """
    end = date.fromisoformat(through)
    start = end - timedelta(days=6)
    # A later exact relationship can merge two components that were separate
    # earlier in the week. Event IDs intentionally remain cutoff-local, so an
    # ID-keyed ``latest revision`` map would retain the superseded component
    # and double-count its posts. Instead, carry a disjoint set of weekly
    # states forward by their provider-qualified visible members. A new daily
    # revision supersedes every earlier state it overlaps and inherits their
    # activity/peak metadata.
    weekly_states: list[dict[str, Any]] = []
    base: dict[str, Any] | None = None
    for offset in range(7):
        day = (start + timedelta(days=offset)).isoformat()
        payload = _events_day_cached(day=day, cache_token=_cache_token(day))
        if not payload.get("available"):
            continue
        base = payload
        for item in payload["items"]:
            member_keys = {
                (
                    str(member.get("provider", "twitterapi_io")),
                    str(member["post_id"]),
                )
                for member in [item["root"], *item["evidence"]]
            }
            overlapping = [
                state
                for state in weekly_states
                if state["member_keys"] & member_keys
            ]
            inherited_days = {
                active_day
                for state in overlapping
                for active_day in state["active_days"]
            }
            peak_state = max(
                [
                    {
                        "peak_attention_score": item["peak_attention_score"],
                        "daily_score_basis": item["daily_score_basis"],
                    }
                ]
                + [
                    {
                        "peak_attention_score": state["peak_attention_score"],
                        "daily_score_basis": state["daily_score_basis"],
                    }
                    for state in overlapping
                ],
                key=lambda state: (
                    state["peak_attention_score"],
                    state["daily_score_basis"]["published_at"],
                    state["daily_score_basis"]["post_id"],
                ),
            )
            peak_score = peak_state["peak_attention_score"]
            peak_interaction = max(
                [item["peak_public_interactions"]]
                + [state["peak_public_interactions"] for state in overlapping]
            )
            if overlapping:
                weekly_states = [
                    state for state in weekly_states if state not in overlapping
                ]
            weekly_states.append(
                {
                    "item": item,
                    "member_keys": member_keys,
                    "active_days": {*inherited_days, day},
                    "peak_attention_score": peak_score,
                    "daily_score_basis": peak_state["daily_score_basis"],
                    "peak_public_interactions": peak_interaction,
                }
            )
    if base is None:
        return {"available": False, "reason": "No complete Feed days in window."}
    items: list[dict[str, Any]] = []
    for state in weekly_states:
        item = state["item"]
        event_id = item["event_id"]
        active_days = sorted(state["active_days"])
        revision = {
            **item,
            "snapshot_cutoff": f"{end.isoformat()}T23:59:59.999999+00:00",
            "snapshot_content_sha256": hashlib.sha256(
                json.dumps(
                    [
                        "week",
                        event_id,
                        start.isoformat(),
                        end.isoformat(),
                        item["snapshot_content_sha256"],
                        active_days,
                    ],
                    separators=(",", ":"),
                ).encode()
            ).hexdigest(),
            "audience_routing": None,
            "active_days": active_days,
            "weekly_active_day_count": len(active_days),
            "peak_attention_score": state["peak_attention_score"],
            "daily_score_basis": state["daily_score_basis"],
            "peak_public_interactions": state["peak_public_interactions"],
            "projection": "week",
            "window_from": start.isoformat(),
            "window_to": end.isoformat(),
        }
        items.append(revision)
    return {
        **{key: value for key, value in base.items() if key != "items"},
        "date": through,
        "projection": "week",
        "window_from": start.isoformat(),
        "window_to": end.isoformat(),
        "audience_routing_run": None,
        "items": items,
    }


def _score_order_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        item["peak_attention_score"],
        item["registry_account_count"],
        item["member_count"],
        item["latest_evidence_at"],
        item["event_id"],
    )


def _daily_rank_by_event_id(items: list[dict[str, Any]]) -> dict[str, int]:
    return {
        str(item["event_id"]): rank
        for rank, item in enumerate(
            sorted(items, key=_score_order_key, reverse=True), start=1
        )
    }


def current_daily_rank_by_event_id(*, day: str) -> dict[str, int]:
    """Return the authoritative displayed Feed rank for every event on one day."""
    payload = _events_day_cached(day=day, cache_token=_cache_token(day))
    if not payload.get("available"):
        return {}
    return _daily_rank_by_event_id(payload["items"])


def _relationship_counts(item: dict[str, Any]) -> dict[str, int]:
    counts = {
        "continuations": 0,
        "replies": 0,
        "quotes": 0,
        "retweets": 0,
        "related": 0,
    }
    for evidence in item["evidence"]:
        relationship = evidence["relationship"]
        if relationship == "reply":
            key = "continuations" if evidence["same_author_as_root"] else "replies"
        elif relationship == "quote":
            key = "quotes"
        elif relationship == "retweet":
            key = "retweets"
        else:
            key = "related"
        counts[key] += 1
    return counts


def events_payload(
    *,
    day: str,
    lane: str,
    sort: str,
    query: str,
    event_id: str = "",
    routing_filter: str = "all",
    limit: int,
    offset: int,
    projection: str = "day",
    include_evidence: bool = True,
) -> dict[str, Any]:
    """Return a state-aware view over one cached day projection."""
    token = _cache_token(day)
    payload = (
        _events_week_cached(through=day)
        if projection == "week"
        else _events_day_cached(day=day, cache_token=token)
    )
    if not payload.get("available"):
        return payload

    # Search is a visibility control, not a separate competition. Freeze one
    # score rank over the complete projection before applying it.
    daily_rank_by_event_id = _daily_rank_by_event_id(payload["items"])
    daily_rank_total = len(daily_rank_by_event_id)
    needle = query.strip().lower()
    items = [
        {**item, "daily_rank": daily_rank_by_event_id[item["event_id"]]}
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

    def audiences(item: dict[str, Any]) -> tuple[bool, bool] | None:
        route = item.get("audience_routing")
        if route is None:
            return None
        return (
            bool(route["ai_engineering"]["relevant"]),
            bool(route["investment"]["relevant"]),
        )

    routing_counts = {
        "all": len(items),
        "relevant": sum(
            result is not None and (result[0] or result[1])
            for result in map(audiences, items)
        ),
        "not_relevant": sum(
            result == (False, False) for result in map(audiences, items)
        ),
        "not_evaluated": sum(
            result is None for result in map(audiences, items)
        ),
    }
    if routing_filter == "relevant":
        items = [
            item
            for item in items
            if (result := audiences(item)) is not None
            and (result[0] or result[1])
        ]
    elif routing_filter == "not_relevant":
        items = [item for item in items if audiences(item) == (False, False)]
    elif routing_filter == "not_evaluated":
        items = [item for item in items if audiences(item) is None]
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
        items.sort(key=_score_order_key, reverse=True)

    if event_id:
        items = [item for item in items if item["event_id"] == event_id]
    total = len(items)
    page_items = []
    for item in items[offset : offset + limit]:
        projected = {**item, "relationship_counts": _relationship_counts(item)}
        if not include_evidence:
            projected["evidence"] = []
        page_items.append(projected)
    return {
        **{key: value for key, value in payload.items() if key != "items"},
        "lane": lane,
        "sort": sort,
        "query": query,
        "event_id": event_id,
        "routing_filter": routing_filter,
        "projection": projection,
        "routing_counts": routing_counts,
        "daily_rank_total": daily_rank_total,
        "total": total,
        "limit": limit,
        "offset": offset,
        "include_evidence": include_evidence,
        "items": page_items,
    }


@lru_cache(maxsize=8)
def _dates_payload_cached(
    cache_token: tuple[tuple[str, int, int, int, int], ...],
) -> dict[str, Any]:
    """Expose fast evidence-ledger counts for each complete Feed day."""
    del cache_token
    if not DEFAULT_EVENTS_DB.is_file():
        return {
            "available": False,
            "reason": "No Event store found. Run `fli signal-events refresh` first.",
        }
    events = _open_readonly(DEFAULT_EVENTS_DB)
    run = _latest_run(events)
    events.close()
    if run is None:
        return {
            "available": False,
            "reason": "Event store has no published Feed/Event pair.",
        }
    feed_dates = feed_store.dates_payload(run_id=run["feed_run_id"])
    if not feed_dates.get("available"):
        return feed_dates
    dates = []
    for row in feed_dates["dates"]:
        day = row["day"]
        projection = _events_day_cached(day=day, cache_token=_cache_token(day))
        dates.append(
            {
                "day": day,
                "item_count": (
                    len(projection.get("items") or [])
                    if projection.get("available")
                    else 0
                ),
            }
        )
    return {**feed_dates, "dates": dates, "run_id": run["run_id"]}


def dates_payload() -> dict[str, Any]:
    """Expose event counts without rebuilding every day on repeat reads."""
    cache_token = _dates_cache_token()
    with _dates_payload_lock:
        return _dates_payload_cached(cache_token)
