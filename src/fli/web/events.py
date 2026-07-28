"""Registry-aware Feed Events over exact structural relationships."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import sqlite3
import tempfile
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any

from fli.evidence import events as signal_events
from fli.evidence import feed as signal_feed
from fli.routing import view as audience_routing_store
from fli.scoring import attention
from fli.web import feed as feed_store


DEFAULT_EVENTS_DB = signal_events.DEFAULT_EVENTS_DB
DEFAULT_FEED_DB = signal_feed.DEFAULT_FEED_DB
DEFAULT_EVENT_VIEW_CACHE_ROOT: Path | None = (
    feed_store.REPO_ROOT / "data" / "derived" / "web-event-cache"
)

FeedKey = tuple[str, str]
_dates_payload_lock = Lock()


def _open_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _latest_run(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return signal_events.published_run(conn)


def _selected_run(
    conn: sqlite3.Connection, event_run_id: str, *, day: str
) -> sqlite3.Row | None:
    if not event_run_id:
        return signal_events.published_run(conn, day=day)
    return conn.execute(
        "SELECT * FROM event_run WHERE run_id = ?",
        (event_run_id,),
    ).fetchone()


def _feed_key(item: dict[str, Any]) -> FeedKey:
    """Return the provider-qualified identity of one Feed candidate."""
    return (str(item.get("provider", "twitterapi_io")), str(item["post_id"]))


def _all_feed_candidates(*, day: str, run_id: str) -> dict[str, Any]:
    """Read every raw Feed candidate once without an API pagination ceiling."""
    result = feed_store.feed_payload(
        day=day,
        lane="all",
        sort="recent",
        query="",
        limit=2**31 - 1,
        offset=0,
        run_id=run_id,
    )
    return {**result, "limit": len(result.get("items") or []), "offset": 0}


def _event_rows(
    events: sqlite3.Connection, run_id: str, day: str
) -> tuple[
    list[sqlite3.Row],
    list[sqlite3.Row],
    list[sqlite3.Row],
    set[FeedKey],
]:
    """Return Events published on their one canonical day.

    ``event_day`` remains the append-only activity ledger. Selecting clusters
    active on ``day`` lets the read model recover independently rooted
    components even when a later disclosure joined their storage cluster.
    """
    clusters = events.execute(
        """SELECT cluster.*,
                  active.direct_member_count AS selected_day_member_count,
                  (SELECT MIN(first.day) FROM event_day first
                   WHERE first.run_id = cluster.run_id
                     AND first.event_id = cluster.event_id)
                      AS first_activity_day
           FROM event_day active
           JOIN event_cluster cluster
             ON cluster.run_id = active.run_id
            AND cluster.event_id = active.event_id
           WHERE active.run_id = ? AND active.day = ?
           ORDER BY cluster.event_id""",
        (run_id, day),
    ).fetchall()
    claimed_members = {
        (str(row["provider"]), str(row["post_id"]))
        for row in events.execute(
            """SELECT provider, post_id FROM event_member
               WHERE run_id = ?""",
            (run_id,),
        ).fetchall()
    }
    if not clusters:
        return [], [], [], claimed_members
    selected_event_ids = [str(row["event_id"]) for row in clusters]
    placeholders = ",".join("?" for _ in selected_event_ids)
    members = events.execute(
        f"""SELECT member.*
           FROM event_member member
           WHERE member.run_id = ?
             AND member.event_id IN ({placeholders})
           ORDER BY member.event_id, member.provider, member.post_id""",
        (run_id, *selected_event_ids),
    ).fetchall()
    links = events.execute(
        f"""SELECT link.*
           FROM event_link link
           WHERE link.run_id = ?
             AND link.event_id IN ({placeholders})
           ORDER BY link.event_id, link.link_type, link.provider,
                    link.source_post_id, link.target_post_id""",
        (run_id, *selected_event_ids),
    ).fetchall()
    return clusters, members, links, claimed_members


def _root_post_id(
    members: list[dict[str, Any]], links: list[sqlite3.Row], candidates: set[FeedKey]
) -> str:
    """Choose the exact relationship root from renderable Feed candidates."""
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


def _public_interactions(item: dict[str, Any]) -> int:
    return sum(
        int(item["metrics"].get(key) or 0)
        for key in ("likes", "replies", "reposts", "quotes")
    )


def _voter(amplifier: dict[str, Any]) -> attention.Voter:
    return attention.Voter(
        entity_id=int(amplifier["entity_id"]),
        position=float(amplifier["network_position"]),
        entity_name=str(amplifier.get("entity_name") or ""),
        entity_kind=str(amplifier.get("entity_kind") or ""),
        handle=str(amplifier.get("handle") or ""),
        relation_type=str(amplifier.get("relation_type") or ""),
        source_url=str(amplifier.get("source_url") or ""),
    )


def _singleton(
    item: dict[str, Any],
    entity_positions: dict[int, float],
    day: str,
) -> dict[str, Any]:
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
    author_entity_id = item["author"]["entity_id"]
    voters = tuple(
        _voter(amplifier)
        for amplifier in item["amplifiers"]
        if author_entity_id is None
        or int(amplifier["entity_id"]) != int(author_entity_id)
    )
    return {
        "event_id": singleton_id,
        "canonical_root_post_id": item["post_id"],
        "presentation_root_post_id": item["post_id"],
        "semantic_snapshot_sha256": snapshot_hash,
        "first_activity_day": item["published_at"][:10],
        "is_grouped": False,
        "root": item,
        "why_grouped": [],
        "anchor_types": [],
        "member_count": 1,
        "lifetime_member_count": 1,
        "day_member_count": 1,
        "activity_days": [item["published_at"][:10]],
        "link_count": 0,
        "author_count": 1,
        "registry_entity_count": 1 if item["author"]["entity_id"] is not None else 0,
        "first_hand_count": int(item["observed_directly"]),
        "amplifiers": item["amplifiers"],
        "_rank_inputs": attention.RankInputs(
            voters=voters,
            author_position=(
                entity_positions.get(int(author_entity_id), 0.0)
                if author_entity_id is not None
                else 0.0
            ),
            public_interactions=(
                _public_interactions(item)
                if str(item["published_at"])[:10] == day
                else 0
            ),
            event_id=singleton_id,
        ),
        "latest_evidence_at": item["published_at"],
        "evidence": [],
    }


def _root_feed_item(
    row: sqlite3.Row,
    member: dict[str, Any],
    account: dict[str, Any] | None,
) -> dict[str, Any]:
    """Project the stable canonical root without inventing a member-post rank."""
    return {
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
        "amplifiers": [],
        "metrics": {
            "likes": row["like_count"],
            "replies": row["reply_count"],
            "reposts": row["retweet_count"],
            "quotes": row["quote_count"],
            "views": row["view_count"],
            "bookmarks": row["bookmark_count"],
        },
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


def _rank_input_sha256(*, day: str, items: list[dict[str, Any]]) -> str:
    """Bind a daily rank to every exact input, not only the selected top 100."""
    events = []
    for item in sorted(items, key=lambda value: str(value["event_id"])):
        components = item["rank_components"]
        events.append(
            {
                "event_id": str(item["event_id"]),
                "voters": sorted(
                    [
                        [
                            int(voter["entity_id"]),
                            f"{float(voter['position']):.6f}",
                        ]
                        for voter in components["voters"]
                    ],
                    key=lambda value: value[0],
                ),
                "author_position": (
                    f"{float(components['author_position']):.6f}"
                ),
                "public_interactions": int(
                    components["public_interactions"]
                ),
            }
        )
    return hashlib.sha256(
        json.dumps(
            {
                "day": day,
                "rank_version": attention.DAILY_RANK_VERSION,
                "events": events,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


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


@lru_cache(maxsize=1)
def _projection_code_sha256() -> str:
    """Bind persisted views to the code that defines their exact projection."""
    digest = hashlib.sha256()
    modules = (
        Path(__file__),
        Path(signal_events.__file__),
        Path(signal_feed.__file__),
        Path(feed_store.__file__),
        Path(audience_routing_store.__file__),
        Path(feed_store.attention.__file__),
    )
    for path in modules:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _persisted_cache_key(
    *,
    kind: str,
    cache_token: tuple[tuple[str, int, int, int, int], ...],
) -> str:
    stable_source_token = tuple(
        (path, main_mtime, main_size, wal_mtime if wal_size else 0, wal_size)
        for path, main_mtime, main_size, wal_mtime, wal_size in cache_token
    )
    value = {
        "kind": kind,
        "projection_code_sha256": _projection_code_sha256(),
        # SQLite may create a zero-byte WAL during a read. Its mtime carries no
        # state and must not invalidate a view that was exact before that read.
        "source_token": stable_source_token,
    }
    return hashlib.sha256(
        json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()


def _persisted_cache_path(name: str) -> Path | None:
    root = DEFAULT_EVENT_VIEW_CACHE_ROOT
    return None if root is None else root / name


def _read_persisted_payload(*, name: str, cache_key: str) -> dict[str, Any] | None:
    """Read an optional exact view cache; any cache fault falls back to sources."""
    path = _persisted_cache_path(name)
    if path is None:
        return None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            envelope = json.load(handle)
    except (EOFError, OSError, json.JSONDecodeError, UnicodeError):
        return None
    if not isinstance(envelope, dict) or envelope.get("cache_key") != cache_key:
        return None
    payload = envelope.get("payload")
    return payload if isinstance(payload, dict) else None


def _write_persisted_payload(
    *,
    name: str,
    cache_key: str,
    payload: dict[str, Any],
) -> None:
    """Atomically retain a rebuildable compressed view for the next process."""
    path = _persisted_cache_path(name)
    if path is None:
        return
    temporary_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        with gzip.open(
            temporary_path,
            "wt",
            encoding="utf-8",
            compresslevel=1,
        ) as handle:
            json.dump(
                {"cache_key": cache_key, "payload": payload},
                handle,
                separators=(",", ":"),
            )
        os.replace(temporary_path, path)
    except (OSError, TypeError, ValueError):
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


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
    entity_positions: dict[int, float],
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
            return _singleton(singleton_candidate, entity_positions, day)
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

    root_key = (str(presentation_root_key[0]), str(presentation_root_key[1]))
    root_post_id = root_key[1]
    root = (
        {
            **candidates[root_key],
            "author": dict(candidates[root_key]["author"]),
            "metrics": dict(candidates[root_key]["metrics"]),
        }
        if root_key in candidates
        else _root_feed_item(root_row, root_member, root_account)
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
    root_author_entity_id = root["author"]["entity_id"]
    if root_author_entity_id is not None:
        amplifiers.pop(int(root_author_entity_id), None)
    sorted_amplifiers = sorted(
        amplifiers.values(),
        key=lambda amplifier: (
            -float(amplifier["network_position"]),
            int(amplifier["entity_id"]),
        ),
    )
    root["amplifiers"] = sorted_amplifiers
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

    # The route/Insight freshness hash binds only first-party semantic
    # evidence. Independent reactions may append forever without invalidating
    # the one audience decision for this Event.
    root_author_handle = str(root["author"]["handle"]).lower()
    semantic_members = [
        member
        for member in visible_members
        if (
            member["post_id"] == root_post_id
            or (
                str(member["author"]["handle"]).lower() == root_author_handle
                and member["post_type"] != "retweet"
            )
        )
    ]
    semantic_keys = {
        (str(member["provider"]), str(member["post_id"]))
        for member in semantic_members
    }
    semantic_identity = sorted(
        (
            member["provider"],
            member["post_id"],
            member["raw_sha256"],
            member["published_at"],
            member["first_discovered_at"],
            member["disclosure_post_id"],
            int(member["observed_directly"]),
        )
        for member in semantic_members
    )
    semantic_topology = sorted(
        (
            str(link["provider"]),
            str(link["source_post_id"]),
            str(link["target_post_id"]),
            str(link["link_type"]),
        )
        for link in current_links
        if (str(link["provider"]), str(link["source_post_id"])) in semantic_keys
    )
    semantic_snapshot_sha256 = hashlib.sha256(
        json.dumps(
            [
                projected_event_id,
                day,
                identity_type,
                identity_value,
                root_post_id,
                semantic_identity,
                semantic_topology,
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
    day_member_count = sum(
        int(member["observed_directly"] and str(member["day"]) == day)
        for member in visible_members
    )
    return {
        "event_id": projected_event_id,
        "canonical_root_post_id": canonical_root_post_id,
        "presentation_root_post_id": root_post_id,
        "semantic_snapshot_sha256": semantic_snapshot_sha256,
        "first_activity_day": first_activity_day,
        "is_grouped": len(visible_members) > 1,
        "root": root,
        "why_grouped": why_grouped,
        "anchor_types": anchor_types,
        "member_count": len(visible_members),
        "lifetime_member_count": len(visible_members),
        "day_member_count": day_member_count,
        "activity_days": direct_days,
        "link_count": len(current_links),
        "author_count": len({member["author"]["handle"] for member in visible_members}),
        "registry_entity_count": len(registry_entity_ids),
        "first_hand_count": sum(1 for item in event_candidates if item["observed_directly"]),
        "amplifiers": sorted_amplifiers,
        "_rank_inputs": attention.RankInputs(
            voters=tuple(_voter(amplifier) for amplifier in sorted_amplifiers),
            author_position=(
                entity_positions.get(int(root_author_entity_id), 0.0)
                if root_author_entity_id is not None
                else 0.0
            ),
            public_interactions=max(
                (
                    _public_interactions(item)
                    for item in event_candidates
                    if str(item["published_at"])[:10] == day
                ),
                default=0,
            ),
            event_id=projected_event_id,
        ),
        "latest_evidence_at": max(member["published_at"] for member in visible_members),
        "evidence": related,
    }


@lru_cache(maxsize=16)
def _events_day_cached(
    *,
    day: str,
    cache_token: tuple[tuple[str, int, int, int, int], ...],
    event_run_id: str = "",
) -> dict[str, Any]:
    """Build the Events canonically published on one day.

    The card includes the Event's lifetime activity, while its rank inputs and
    position remain frozen from the canonical publication day.
    """
    if not DEFAULT_EVENTS_DB.is_file():
        return {
            "available": False,
            "reason": "No Event store found. Run `fli signal-events refresh` first.",
        }
    if not DEFAULT_FEED_DB.is_file():
        return {"available": False, "reason": "No Feed store found."}

    run_suffix = f"-{event_run_id[:12]}" if event_run_id else ""
    cache_name = f"events-{day}{run_suffix}.json.gz"
    cache_key = _persisted_cache_key(
        kind=f"events:{day}:{event_run_id or 'published'}",
        cache_token=cache_token,
    )
    persisted = _read_persisted_payload(name=cache_name, cache_key=cache_key)
    if persisted is not None:
        return persisted

    events = _open_readonly(DEFAULT_EVENTS_DB)
    run = _selected_run(events, event_run_id, day=day)
    if run is None:
        events.close()
        return {
            "available": False,
            "reason": (
                f"Event store has no run {event_run_id}."
                if event_run_id
                else "Event store has no materialized run."
            ),
        }
    clusters, member_rows, link_rows, claimed_member_keys = _event_rows(
        events, run["run_id"], day
    )
    events.close()

    feed_result = _all_feed_candidates(day=day, run_id=run["feed_run_id"])
    if not feed_result.get("available"):
        return feed_result
    feed_items = feed_result.get("items") or []
    candidates = {_feed_key(item): item for item in feed_items}

    member_post_keys = sorted(
        {(str(row["provider"]), str(row["post_id"])) for row in member_rows}
    )
    candidate_post_keys = sorted(candidates)
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
    if candidate_post_keys:
        feed.execute(
            "CREATE TEMP TABLE selected_feed_candidate "
            "(provider TEXT NOT NULL, post_id TEXT NOT NULL, "
            "PRIMARY KEY (provider, post_id)) WITHOUT ROWID"
        )
        feed.executemany(
            "INSERT INTO selected_feed_candidate (provider, post_id) VALUES (?, ?)",
            candidate_post_keys,
        )
        reply_candidate_rows = feed.execute(
            """SELECT post.provider, post.post_id
               FROM selected_feed_candidate selected
               JOIN feed_post post
                 ON post.provider = selected.provider
                AND post.post_id = selected.post_id
               WHERE post.run_id = ?
                 AND post.in_reply_to_post_id IS NOT NULL
                 AND post.in_reply_to_post_id != ''""",
            (run["feed_run_id"],),
        ).fetchall()
    else:
        reply_candidate_rows = []
    feed.close()
    posts = {(row["provider"], row["post_id"]): row for row in post_rows}
    reply_candidate_keys = {
        (str(row["provider"]), str(row["post_id"]))
        for row in reply_candidate_rows
    }
    by_handle, by_x_id = feed_store._registry_maps()
    network_context = feed_store.rankings_store.entity_network_context()
    entity_ranks = feed_store.rankings_store.entity_network_ranks()
    if network_context is None or not entity_ranks:
        return {
            "available": False,
            "reason": (
                "The Event rank is unavailable because no completed Registry "
                "network analysis is present."
            ),
        }
    entity_positions = attention.entity_positions(entity_ranks)

    members_by_event: dict[str, list[sqlite3.Row]] = {}
    for member in member_rows:
        members_by_event.setdefault(member["event_id"], []).append(member)
    links_by_event: dict[str, list[sqlite3.Row]] = {}
    for link in link_rows:
        links_by_event.setdefault(link["event_id"], []).append(link)

    items: list[dict[str, Any]] = []
    consumed: set[FeedKey] = set()
    for cluster in clusters:
        event_id = cluster["event_id"]
        visible_members: list[dict[str, Any]] = []
        cutoff_keys: set[tuple[str, str]] = set()
        visible_keys: set[tuple[str, str]] = set()
        all_member_keys: set[tuple[str, str]] = set()
        for member in members_by_event.get(event_id, []):
            row = posts.get((member["provider"], member["post_id"]))
            if row is None:
                continue
            member_key = (member["provider"], member["post_id"])
            all_member_keys.add(member_key)
            in_canonical_revision = (
                str(row["day"]) <= day
                and str(row["first_discovered_day"]) <= day
            )
            if in_canonical_revision:
                cutoff_keys.add(member_key)
            account = feed_store._registry_account(
                row["author_x_id"], row["author_handle"], by_handle, by_x_id
            )
            if account and account["registry_state"] == "rejected":
                continue
            if in_canonical_revision:
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
                }
            )
        all_links = [
            link
            for link in links_by_event.get(event_id, [])
            if (link["provider"], link["source_post_id"]) in all_member_keys
        ]
        canonical_links = [
            link
            for link in all_links
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
        canonical_components = _visible_components(
            visible_keys, cutoff_keys, canonical_links, posts
        )
        if not canonical_components:
            continue

        # Freeze the canonical components, then assign each later member to
        # the first canonical node reached by its one structural parent chain.
        # A future disclosure from an already-canonical post cannot merge or
        # reidentify those components.
        owner_by_node: dict[tuple[str, str], int] = {}
        extended_keys = [set(keys) for keys, _ in canonical_components]
        for index, (component_keys, component_links) in enumerate(
            canonical_components
        ):
            for key in component_keys:
                owner_by_node[key] = index
            for link in component_links:
                owner_by_node.setdefault(
                    (str(link["provider"]), str(link["target_post_id"])), index
                )
        parent_by_source = {
            (str(link["provider"]), str(link["source_post_id"])): (
                str(link["provider"]),
                str(link["target_post_id"]),
            )
            for link in all_links
        }

        def owner_for(key: tuple[str, str]) -> int | None:
            seen: set[tuple[str, str]] = set()
            current = key
            while current not in seen:
                seen.add(current)
                target = parent_by_source.get(current)
                if target is None:
                    return None
                owner = owner_by_node.get(target)
                if owner is not None:
                    return owner
                current = target
            return None

        later_keys = set(member_by_key) - visible_keys
        for key in later_keys:
            owner = owner_for(key)
            if owner is not None:
                extended_keys[owner].add(key)

        for index, (component_keys, component_links) in enumerate(
            canonical_components
        ):
            final_keys = extended_keys[index]
            component_members = [member_by_key[key] for key in sorted(final_keys)]
            direct_days = [
                str(member["day"])
                for member in component_members
                if member["observed_directly"]
            ]
            if not direct_days or min(direct_days) != day:
                continue
            canonical_link_keys = {
                (
                    str(link["provider"]),
                    str(link["source_post_id"]),
                    str(link["target_post_id"]),
                    str(link["link_type"]),
                )
                for link in component_links
            }
            final_links = [
                link
                for link in all_links
                if (
                    (
                        str(link["provider"]),
                        str(link["source_post_id"]),
                        str(link["target_post_id"]),
                        str(link["link_type"]),
                    )
                    in canonical_link_keys
                    or (
                        (str(link["provider"]), str(link["source_post_id"]))
                        in (final_keys - component_keys)
                        and owner_for(
                            (
                                str(link["provider"]),
                                str(link["source_post_id"]),
                            )
                        )
                        == index
                    )
                )
            ]
            presentation_root_key = _component_root(
                component_keys=component_keys,
                links=component_links,
                posts=posts,
                canonical_root_key=canonical_root_key,
            )
            item = _project_component(
                cluster=cluster,
                visible_members=component_members,
                current_links=final_links,
                presentation_root_key=presentation_root_key,
                canonical_root_key=canonical_root_key,
                candidates=candidates,
                posts=posts,
                by_handle=by_handle,
                by_x_id=by_x_id,
                entity_positions=entity_positions,
                day=day,
                consumed=consumed,
            )
            if item is not None:
                items.append(item)

    items.extend(
        _singleton(item, entity_positions, day)
        for item in feed_items
        if _feed_key(item) not in consumed
        and _feed_key(item) not in reply_candidate_keys
        and _feed_key(item) not in claimed_member_keys
    )
    items = attention.rank_events(
        [
            (
                {key: value for key, value in item.items() if key != "_rank_inputs"},
                item["_rank_inputs"],
            )
            for item in items
        ]
    )
    rank_input_sha256 = _rank_input_sha256(day=day, items=items)
    routing_payload = audience_routing_store.routing_payload(
        day,
        expected_rank_input_sha256=rank_input_sha256,
        expected_event_run_id=str(run["run_id"]),
        expected_feed_run_id=str(run["feed_run_id"]),
    )
    routing_items = routing_payload["items"]
    for item in items:
        route = routing_items.get(item["event_id"])
        route_matches = bool(
            route
            and route.get("semantic_snapshot_sha256")
            == item["semantic_snapshot_sha256"]
        )
        item["audience_routing"] = route if route_matches else None
        item["routing_state"] = (
            "evaluated"
            if route_matches
            else "stale"
            if route
            else "not_selected"
            if routing_payload["available"]
            else "unavailable"
        )
    payload = {
        "available": True,
        "date": day,
        "audience_routing_run": routing_payload["run"],
        "run": {
            "run_id": run["run_id"],
            "feed_run_id": run["feed_run_id"],
            "clustering_contract": run["clustering_contract"],
        },
        "rank_contract": {
            "version": attention.DAILY_RANK_VERSION,
            "kind": "daily_event_lexicographic",
            "layers": list(attention.LAYER_NAMES),
            "input_sha256": rank_input_sha256,
            "network": network_context,
            "note": (
                "Every Feed candidate is an Event. Provider-declared exact "
                "relationships group evidence; the complete canonical-day Event "
                "is ranked once and all other posts remain singleton Events."
            ),
        },
        "items": items,
    }
    _write_persisted_payload(
        name=cache_name,
        cache_key=cache_key,
        payload=payload,
    )
    return payload


def _events_week_cached(
    *,
    through: str,
) -> dict[str, Any]:
    """Roll the same canonical events through a seven-day UTC window.

    The final daily revision supplies cumulative evidence through week-end;
    rank remains a property of daily activity. A weekly row retains the Event's
    best canonical daily rank rather than inventing a cross-day score.
    """
    end = date.fromisoformat(through)
    start = end - timedelta(days=6)
    # Root-owned Event IDs are stable across daily projections. A later day can
    # surface only the root again (for example when a new excluded reply quotes
    # it), so retain the richest visible revision instead of replacing prior
    # evidence with a thinner daily snapshot.
    weekly_states: dict[str, dict[str, Any]] = {}
    base: dict[str, Any] | None = None
    for offset in range(7):
        day = (start + timedelta(days=offset)).isoformat()
        payload = _events_day_cached(day=day, cache_token=_cache_token(day))
        if not payload.get("available"):
            continue
        base = payload
        for item in payload["items"]:
            event_id = str(item["event_id"])
            previous = weekly_states.get(event_id)
            inherited_days = set(previous["active_days"]) if previous else set()
            rank_state = min(
                [
                    {
                        "daily_rank": item["daily_rank"],
                        "rank_components": item["rank_components"],
                        "rank_day": day,
                    }
                ]
                + ([
                    {
                        "daily_rank": previous["best_daily_rank"],
                        "rank_components": previous["rank_components"],
                        "rank_day": previous["rank_day"],
                    }
                ] if previous else []),
                key=lambda state: (
                    state["daily_rank"],
                    state["rank_day"],
                ),
            )
            richest_item = item
            if previous and previous["item"]["member_count"] > item["member_count"]:
                richest_item = previous["item"]
            weekly_states[event_id] = {
                "item": richest_item,
                "active_days": {
                    *inherited_days,
                    *(
                        activity_day
                        for activity_day in item.get("activity_days", [day])
                        if start.isoformat() <= activity_day <= end.isoformat()
                    ),
                },
                "best_daily_rank": rank_state["daily_rank"],
                "rank_components": rank_state["rank_components"],
                "rank_day": rank_state["rank_day"],
            }
    if base is None:
        return {"available": False, "reason": "No complete Feed days in window."}
    items: list[dict[str, Any]] = []
    for state in weekly_states.values():
        item = state["item"]
        event_id = item["event_id"]
        active_days = sorted(state["active_days"])
        revision = {
            **item,
            "semantic_snapshot_sha256": hashlib.sha256(
                json.dumps(
                    [
                        "week",
                        event_id,
                        start.isoformat(),
                        end.isoformat(),
                        item["semantic_snapshot_sha256"],
                        active_days,
                    ],
                    separators=(",", ":"),
                ).encode()
            ).hexdigest(),
            "audience_routing": None,
            "routing_state": "unavailable",
            "active_days": active_days,
            "weekly_active_day_count": len(active_days),
            "source_daily_rank": state["best_daily_rank"],
            "rank_components": state["rank_components"],
            "rank_day": state["rank_day"],
            "projection": "week",
            "window_from": start.isoformat(),
            "window_to": end.isoformat(),
        }
        items.append(revision)
    return {
        **{
            key: value
            for key, value in base.items()
            if key not in {"items", "rank_contract"}
        },
        "date": through,
        "projection": "week",
        "window_from": start.isoformat(),
        "window_to": end.isoformat(),
        "audience_routing_run": None,
        "rank_contract": {
            "version": attention.DAILY_RANK_VERSION,
            "kind": "weekly_inherited_daily_rank",
            "layers": ["best_daily_rank", "rank_day", "event_id"],
            "note": (
                "Weekly rows inherit each Event's best canonical daily rank, "
                "then use rank day and Event ID for deterministic ordering. "
                "This is not a new cross-day score or a single-day rank input."
            ),
        },
        "items": items,
    }


def _daily_rank_by_event_id(items: list[dict[str, Any]]) -> dict[str, int]:
    if all("source_daily_rank" in item for item in items):
        ordered = sorted(
            items,
            key=lambda item: (
                int(item["source_daily_rank"]),
                str(item["rank_day"]),
                str(item["event_id"]),
            ),
        )
        return {
            str(item["event_id"]): rank
            for rank, item in enumerate(ordered, start=1)
        }
    return {
        str(item["event_id"]): int(item["daily_rank"])
        for item in items
    }


def current_daily_rank_by_event_id(*, day: str) -> dict[str, int]:
    """Return the authoritative displayed Feed rank for every event on one day."""
    payload = _events_day_cached(day=day, cache_token=_cache_token(day))
    if not payload.get("available"):
        return {}
    return _daily_rank_by_event_id(payload["items"])


def current_rank_identity(*, day: str) -> dict[str, str]:
    """Return the immutable source identity for the authoritative daily rank."""
    payload = _events_day_cached(day=day, cache_token=_cache_token(day))
    if not payload.get("available"):
        raise ValueError(
            str(payload.get("reason") or f"Event rank is unavailable for {day}")
        )
    run = payload.get("run") or {}
    rank_contract = payload.get("rank_contract") or {}
    rank_input_sha256 = str(rank_contract.get("input_sha256") or "")
    if (
        not run.get("run_id")
        or not run.get("feed_run_id")
        or not rank_input_sha256
    ):
        raise ValueError(f"Event rank provenance is incomplete for {day}")
    return {
        "day": day,
        "rank_version": attention.DAILY_RANK_VERSION,
        "rank_input_sha256": rank_input_sha256,
        "event_run_id": str(run["run_id"]),
        "feed_run_id": str(run["feed_run_id"]),
    }


def _relationship_counts(item: dict[str, Any]) -> dict[str, int]:
    counts = {
        "author_updates": 0,
        "replies": 0,
        "quotes": 0,
        "retweets": 0,
        "related": 0,
    }
    for evidence in item["evidence"]:
        relationship = evidence["relationship"]
        if evidence["same_author_as_root"] and relationship != "retweet":
            key = "author_updates"
        elif relationship == "reply":
            key = "replies"
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
    event_run_id: str = "",
) -> dict[str, Any]:
    """Return a state-aware view over one cached day projection."""
    if sort not in {"rank", "recent", "engagement"}:
        raise ValueError("sort must be 'rank', 'recent', or 'engagement'")
    if projection == "week" and event_run_id:
        raise ValueError("An explicit Event run is supported only for a day projection")
    token = _cache_token(day)
    payload = (
        _events_week_cached(through=day)
        if projection == "week"
        else _events_day_cached(
            day=day,
            cache_token=token,
            event_run_id=event_run_id,
        )
    )
    if not payload.get("available"):
        return payload

    # Search is a visibility control, not a separate competition. Freeze one
    # daily rank over the complete projection before applying it.
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
                item["rank_components"]["public_interactions"],
                item["latest_evidence_at"],
                item["event_id"],
            ),
            reverse=True,
        )
    else:
        items.sort(key=lambda item: (item["daily_rank"], item["event_id"]))

    if event_id:
        items = [item for item in items if item["event_id"] == event_id]
    total = len(items)
    page_items = []
    for item in items[offset : offset + limit]:
        projected = {**item, "relationship_counts": _relationship_counts(item)}
        if not include_evidence:
            projected["evidence"] = []
            projected["amplifiers"] = []
            projected["root"] = {**item["root"], "amplifiers": []}
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
    if not DEFAULT_EVENTS_DB.is_file():
        return {
            "available": False,
            "reason": "No Event store found. Run `fli signal-events refresh` first.",
        }
    events = _open_readonly(DEFAULT_EVENTS_DB)
    publications = signal_events.published_days(events)
    events.close()
    if not publications:
        return {
            "available": False,
            "reason": "Event store has no published Feed/Event pair.",
        }
    cache_key = _persisted_cache_key(kind="dates", cache_token=cache_token)
    persisted = _read_persisted_payload(name="dates.json.gz", cache_key=cache_key)
    if persisted is not None:
        return persisted
    publication_feed_runs = {
        str(publication["feed_run_id"]) for publication in publications
    }
    feed_dates = feed_store.dates_payload(
        run_id=(
            next(iter(publication_feed_runs))
            if len(publication_feed_runs) == 1
            else None
        )
    )
    if not feed_dates.get("available"):
        return feed_dates
    dates = []
    for row in feed_dates["dates"]:
        day = str(row["day"])
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
    latest = publications[-1]
    payload = {
        **feed_dates,
        "run_id": str(latest["run_id"]),
        "feed_run_id": str(latest["feed_run_id"]),
        "dates": dates,
    }
    _write_persisted_payload(
        name="dates.json.gz",
        cache_key=cache_key,
        payload=payload,
    )
    return payload


def dates_payload() -> dict[str, Any]:
    """Expose event counts without rebuilding every day on repeat reads."""
    cache_token = _dates_cache_token()
    with _dates_payload_lock:
        return _dates_payload_cached(cache_token)


def warm_current_event_views() -> dict[str, Any]:
    """Warm every Event day in the published reviewer window.

    The date summary has a narrower structural cache token than each daily
    projection. A routing publication can therefore leave the summary valid
    while invalidating one or more day views. Warming the days explicitly
    keeps direct Event URLs fast after a service restart.
    """
    summary = dates_payload()
    if not summary.get("available"):
        return {
            "available": False,
            "reason": summary.get("reason") or "Event dates are unavailable.",
            "days_warmed": 0,
        }
    date_from = str(summary.get("date_from") or "")
    date_to = str(summary.get("date_to") or "")
    days = [
        str(row["day"])
        for row in summary.get("dates") or []
        if date_from <= str(row.get("day") or "") <= date_to
    ]
    for day in days:
        _events_day_cached(day=day, cache_token=_cache_token(day))
    return {
        "available": True,
        "run_id": summary.get("run_id"),
        "days_warmed": len(days),
    }
