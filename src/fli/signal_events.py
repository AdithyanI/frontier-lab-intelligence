"""Content-addressed exact structural groups over one deterministic Feed run.

This stage performs no topical inference. It connects posts only when the
provider supplies an exact quote/retweet target or reply parent. A conversation
identifier remains useful metadata, but is deliberately not a clustering edge:
one X thread can contain several unrelated branches. The post-level Feed
remains the complete evidence ledger.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fli import signal_feed


SCHEMA_VERSION = "signal-events-v4"
CLUSTERING_CONTRACT = "exact-structural-v6-primary-author-threads"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FEED_DB = signal_feed.DEFAULT_FEED_DB
DEFAULT_EVENTS_DB = REPO_ROOT / "data" / "derived" / "signal-events" / "events.db"

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS event_run (
    run_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL CHECK (schema_version = '{SCHEMA_VERSION}'),
    clustering_contract TEXT NOT NULL,
    feed_run_id TEXT NOT NULL,
    feed_schema_version TEXT NOT NULL,
    input_fingerprint TEXT NOT NULL,
    cluster_count INTEGER NOT NULL,
    member_count INTEGER NOT NULL,
    link_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (clustering_contract, feed_run_id, input_fingerprint)
);

CREATE TABLE IF NOT EXISTS event_cluster (
    run_id TEXT NOT NULL REFERENCES event_run(run_id) ON DELETE CASCADE,
    event_id TEXT NOT NULL,
    representative_provider TEXT NOT NULL,
    representative_post_id TEXT NOT NULL,
    canonical_identity_type TEXT NOT NULL CHECK (
        canonical_identity_type IN ('post')
    ),
    canonical_identity_value TEXT NOT NULL,
    anchor_types_json TEXT NOT NULL,
    started_at TEXT NOT NULL,
    last_activity_at TEXT NOT NULL,
    member_count INTEGER NOT NULL,
    link_count INTEGER NOT NULL,
    PRIMARY KEY (run_id, event_id)
);

CREATE TABLE IF NOT EXISTS event_member (
    run_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    post_id TEXT NOT NULL,
    post_type TEXT NOT NULL,
    observed_directly INTEGER NOT NULL CHECK (observed_directly IN (0, 1)),
    is_representative INTEGER NOT NULL CHECK (is_representative IN (0, 1)),
    PRIMARY KEY (run_id, event_id, provider, post_id),
    FOREIGN KEY (run_id, event_id)
        REFERENCES event_cluster(run_id, event_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_event_member_post
    ON event_member(run_id, provider, post_id, event_id);
CREATE INDEX IF NOT EXISTS idx_event_member_event
    ON event_member(run_id, event_id, observed_directly, post_id);

CREATE TABLE IF NOT EXISTS event_link (
    run_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    source_post_id TEXT NOT NULL,
    target_post_id TEXT NOT NULL,
    link_type TEXT NOT NULL CHECK (
        link_type IN ('quote', 'retweet', 'reply_parent', 'primary_thread')
    ),
    anchor_value TEXT NOT NULL,
    discovered_at TEXT NOT NULL,
    discovered_day TEXT NOT NULL,
    disclosure_post_id TEXT NOT NULL,
    PRIMARY KEY (
        run_id, event_id, provider, source_post_id, target_post_id, link_type
    ),
    FOREIGN KEY (run_id, event_id)
        REFERENCES event_cluster(run_id, event_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_event_link_source
    ON event_link(
        run_id, event_id, source_post_id, link_type, target_post_id
    );
CREATE INDEX IF NOT EXISTS idx_event_link_discovery
    ON event_link(
        run_id, event_id, discovered_day, provider, source_post_id,
        target_post_id
    );

CREATE TABLE IF NOT EXISTS event_anchor (
    run_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    anchor_type TEXT NOT NULL CHECK (
        anchor_type IN ('same_target', 'reply_parent', 'conversation_root')
    ),
    anchor_value TEXT NOT NULL,
    PRIMARY KEY (run_id, event_id, anchor_type, anchor_value),
    FOREIGN KEY (run_id, event_id)
        REFERENCES event_cluster(run_id, event_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS event_day (
    run_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    day TEXT NOT NULL,
    direct_member_count INTEGER NOT NULL,
    PRIMARY KEY (run_id, event_id, day),
    FOREIGN KEY (run_id, event_id)
        REFERENCES event_cluster(run_id, event_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_event_day
    ON event_day(run_id, day, event_id);

CREATE TABLE IF NOT EXISTS signal_publication (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    event_run_id TEXT NOT NULL REFERENCES event_run(run_id),
    published_at TEXT NOT NULL
);
"""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def connect(path: Path | str = DEFAULT_EVENTS_DB) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        probe = sqlite3.connect(path)
        try:
            has_run = probe.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'event_run'"
            ).fetchone()
            versions = (
                {
                    row[0]
                    for row in probe.execute(
                        "SELECT DISTINCT schema_version FROM event_run"
                    ).fetchall()
                }
                if has_run
                else set()
            )
        finally:
            probe.close()
        if versions and versions != {SCHEMA_VERSION}:
            found = ", ".join(sorted(versions))
            raise RuntimeError(
                f"Event store uses {found}; rebuild the derived store for {SCHEMA_VERSION}."
            )
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[tuple[str, str], tuple[str, str]] = {}

    def add(self, value: tuple[str, str]) -> None:
        self.parent.setdefault(value, value)

    def find(self, value: tuple[str, str]) -> tuple[str, str]:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: tuple[str, str], right: tuple[str, str]) -> None:
        self.add(left)
        self.add(right)
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[max(left_root, right_root)] = min(left_root, right_root)


def _canonical_identity(
    members: set[tuple[str, str]],
    member_links: list[dict[str, str]],
    posts: dict[tuple[str, str], sqlite3.Row],
) -> tuple[tuple[str, str], str, str]:
    """Choose one structural root and stable identity for an exact component.

    Quote, retweet, and reply-parent edges point from a wrapper/child toward
    the provider-declared target. Their terminal target is therefore the
    canonical post. Missing provider-declared targets remain opaque component
    members. Multiple children of the same uncaptured parent therefore share a
    stable identity without treating every branch in the conversation as one
    event.
    """
    structural_types = {"quote", "retweet", "reply_parent", "primary_thread"}
    outbound: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    inbound: dict[tuple[str, str], int] = defaultdict(int)
    for link in member_links:
        source = (link["provider"], link["source_post_id"])
        target = (link["provider"], link["target_post_id"])
        if link["link_type"] in structural_types:
            outbound[source].add(target)
            inbound[target] += 1

    renderable = [member for member in members if member in posts]
    if not renderable:
        raise ValueError("an event component must contain a renderable post")
    terminal = sorted(member for member in members if not outbound.get(member))
    identity_node = (terminal or sorted(members))[0]
    has_structural_edges = bool(outbound)
    identity_children = [
        member
        for member in renderable
        if identity_node in outbound.get(member, set())
    ]
    representative = (
        identity_node
        if has_structural_edges and identity_node in posts
        else min(
            identity_children or renderable,
            key=lambda key: (
                str(posts[key]["first_discovered_at"]),
                str(posts[key]["published_at"]),
                -int(posts[key]["observed_directly"] or 0),
                key,
            ),
        )
    )

    return representative, "post", identity_node[1]


def _latest_feed_run(conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM feed_run ORDER BY created_at DESC, run_id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        raise RuntimeError("Feed store has no materialized run.")
    if row["schema_version"] != signal_feed.SCHEMA_VERSION:
        raise RuntimeError(
            "Feed schema does not expose exact conversation metadata; rebuild it "
            f"for {signal_feed.SCHEMA_VERSION}."
        )
    return row


def published_run(conn: sqlite3.Connection) -> sqlite3.Row | None:
    """Return the one Event run explicitly published to readers."""
    return conn.execute(
        """SELECT run.*
           FROM signal_publication publication
           JOIN event_run run ON run.run_id = publication.event_run_id
           WHERE publication.singleton = 1"""
    ).fetchone()


def publish(
    *,
    events_db: Path | str = DEFAULT_EVENTS_DB,
    feed_db: Path | str = DEFAULT_FEED_DB,
    event_run_id: str,
) -> dict[str, Any]:
    """Atomically move the live pointer to one validated Feed/Event pair."""
    conn = connect(events_db)
    run = conn.execute(
        "SELECT * FROM event_run WHERE run_id = ?", (event_run_id,)
    ).fetchone()
    if run is None:
        conn.close()
        raise ValueError(f"Unknown Event run: {event_run_id}")
    feed_path = Path(feed_db).resolve()
    if not feed_path.is_file():
        conn.close()
        raise FileNotFoundError(feed_path)
    feed = sqlite3.connect(f"file:{feed_path.as_posix()}?mode=ro", uri=True)
    matching_feed = feed.execute(
        "SELECT 1 FROM feed_run WHERE run_id = ?", (run["feed_run_id"],)
    ).fetchone()
    feed.close()
    if matching_feed is None:
        conn.close()
        raise RuntimeError(
            f"Event run {event_run_id} references missing Feed run "
            f"{run['feed_run_id']}."
        )
    published_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn:
        conn.execute(
            """INSERT INTO signal_publication
               (singleton, event_run_id, published_at)
               VALUES (1, ?, ?)
               ON CONFLICT(singleton) DO UPDATE SET
                   event_run_id = excluded.event_run_id,
                   published_at = excluded.published_at""",
            (event_run_id, published_at),
        )
    result = dict(run)
    result["published_at"] = published_at
    conn.close()
    return result


def materialize(
    *,
    feed_db: Path | str = DEFAULT_FEED_DB,
    events_db: Path | str = DEFAULT_EVENTS_DB,
    feed_run_id: str | None = None,
) -> dict[str, Any]:
    """Materialize exact multi-post structural groups for one Feed run."""
    feed_path = Path(feed_db).resolve()
    if not feed_path.is_file():
        raise FileNotFoundError(feed_path)
    feed = sqlite3.connect(f"file:{feed_path.as_posix()}?mode=ro", uri=True)
    feed.row_factory = sqlite3.Row
    feed_run = (
        feed.execute("SELECT * FROM feed_run WHERE run_id = ?", (feed_run_id,)).fetchone()
        if feed_run_id
        else _latest_feed_run(feed)
    )
    if feed_run is None:
        feed.close()
        raise ValueError(f"Unknown Feed run: {feed_run_id}")
    if feed_run["schema_version"] != signal_feed.SCHEMA_VERSION:
        feed.close()
        raise RuntimeError(
            f"Feed run uses {feed_run['schema_version']}; expected {signal_feed.SCHEMA_VERSION}."
        )
    run_feed_id = str(feed_run["run_id"])

    post_rows = feed.execute(
        """SELECT post.*,
                  MAX(CASE WHEN membership.role = 'direct' THEN 1 ELSE 0 END)
                      AS observed_directly
           FROM feed_post post
           LEFT JOIN feed_run_post membership
             ON membership.run_id = post.run_id
            AND membership.provider = post.provider
            AND membership.post_id = post.post_id
           WHERE post.run_id = ?
           GROUP BY post.run_id, post.provider, post.post_id
           ORDER BY post.provider, post.post_id""",
        (run_feed_id,),
    ).fetchall()
    relation_rows = feed.execute(
        """SELECT provider, source_post_id, target_post_id, relation_type,
                  discovered_at, discovered_day, disclosure_post_id
           FROM feed_relation WHERE run_id = ?
           ORDER BY provider, source_post_id, relation_type, target_post_id""",
        (run_feed_id,),
    ).fetchall()
    feed.close()

    posts = {(row["provider"], row["post_id"]): row for row in post_rows}
    fingerprint = _sha256(
        _canonical_json(
            {
                "feed_run_id": run_feed_id,
                "posts": [
                    (
                        row["provider"],
                        row["post_id"],
                        row["raw_sha256"],
                        row["conversation_id"],
                        row["in_reply_to_post_id"],
                        row["first_discovered_at"],
                        row["disclosure_post_id"],
                    )
                    for row in post_rows
                ],
                "relations": [tuple(row) for row in relation_rows],
            }
        )
    )
    run_id = _sha256(
        _canonical_json([SCHEMA_VERSION, CLUSTERING_CONTRACT, run_feed_id, fingerprint])
    )
    conn = connect(events_db)
    existing = conn.execute(
        "SELECT * FROM event_run WHERE run_id = ?", (run_id,)
    ).fetchone()
    if existing is not None:
        result = dict(existing)
        result["reused"] = True
        conn.close()
        return result

    union = _UnionFind()
    links: dict[
        tuple[str, str, str, str, str], dict[str, Any]
    ] = {}

    def add_link(
        provider: str,
        source_post_id: str,
        target_post_id: str,
        link_type: str,
        anchor_type: str,
        anchor_value: str,
        discovered_at: str,
        discovered_day: str,
        disclosure_post_id: str,
    ) -> None:
        source = (provider, source_post_id)
        target = (provider, target_post_id)
        if source == target or source not in posts:
            return
        union.union(source, target)
        links[(provider, source_post_id, target_post_id, link_type, anchor_value)] = {
            "provider": provider,
            "source_post_id": source_post_id,
            "target_post_id": target_post_id,
            "link_type": link_type,
            "anchor_type": anchor_type,
            "anchor_value": anchor_value,
            "discovered_at": discovered_at,
            "discovered_day": discovered_day,
            "disclosure_post_id": disclosure_post_id,
        }

    for relation in relation_rows:
        add_link(
            relation["provider"],
            relation["source_post_id"],
            relation["target_post_id"],
            relation["relation_type"],
            "same_target",
            relation["target_post_id"],
            relation["discovered_at"],
            relation["discovered_day"],
            relation["disclosure_post_id"],
        )

    for row in posts.values():
        if row["post_type"] != "reply":
            continue
        parent_id = str(row["in_reply_to_post_id"] or "")
        if parent_id:
            add_link(
                row["provider"],
                row["post_id"],
                parent_id,
                "reply_parent",
                "reply_parent",
                parent_id,
                row["first_discovered_at"],
                row["first_discovered_day"],
                row["disclosure_post_id"],
            )
        # A later first-party continuation can survive even when its immediate
        # parent was deleted or omitted by the provider. Keep the exact parent
        # metadata, but bridge that orphaned continuation to the captured root
        # so one authored thread does not split into separate envelopes.
        conversation_id = str(row["conversation_id"] or "")
        root = posts.get((row["provider"], conversation_id))
        parent_present = (row["provider"], parent_id) in posts
        if root is None or parent_present:
            continue
        same_author = (
            bool(row["author_x_id"] and root["author_x_id"])
            and row["author_x_id"] == root["author_x_id"]
        ) or (
            not (row["author_x_id"] and root["author_x_id"])
            and row["author_handle"] == root["author_handle"]
        )
        if same_author and conversation_id != row["post_id"]:
            add_link(
                row["provider"],
                row["post_id"],
                conversation_id,
                "primary_thread",
                "conversation_root",
                conversation_id,
                row["first_discovered_at"],
                row["first_discovered_day"],
                row["disclosure_post_id"],
            )

    groups: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    for node in union.parent:
        groups[union.find(node)].add(node)

    link_values = list(links.values())
    clusters: list[dict[str, Any]] = []
    for members in groups.values():
        renderable_members = {member for member in members if member in posts}
        member_links = [
            link
            for link in link_values
            if (link["provider"], link["source_post_id"]) in members
            and (link["provider"], link["target_post_id"]) in members
        ]
        if not member_links:
            continue
        has_opaque_anchor = any(
            (link["provider"], link["source_post_id"]) in renderable_members
            and (link["provider"], link["target_post_id"]) not in posts
            for link in member_links
        )
        if not renderable_members or (
            len(renderable_members) == 1 and not has_opaque_anchor
        ):
            continue
        representative, identity_kind, identity_value = _canonical_identity(
            members, member_links, posts
        )
        # The provider identity value is deliberately independent of its
        # current evidence type. A captured root post and a later-discovered
        # conversation anchor normally share the same provider ID; adding the
        # reply must not manufacture a new event ID on the next rebuild.
        event_id = _sha256(_canonical_json([representative[0], identity_value]))
        direct_rows = [
            row
            for key in renderable_members
            if (row := posts[key])["observed_directly"]
        ]
        activity_rows = direct_rows or [posts[key] for key in renderable_members]
        days: dict[str, int] = defaultdict(int)
        for row in direct_rows:
            days[str(row["day"])] += 1
        clusters.append(
            {
                "event_id": event_id,
                "representative": representative,
                "identity_kind": identity_kind,
                "identity_value": identity_value,
                "members": sorted(renderable_members),
                "links": member_links,
                "anchor_types": sorted({link["anchor_type"] for link in member_links}),
                "started_at": min(str(row["published_at"]) for row in activity_rows),
                "last_activity_at": max(
                    str(row["published_at"]) for row in activity_rows
                ),
                "days": dict(days),
            }
        )

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn:
        conn.execute(
            """INSERT INTO event_run
               (run_id, schema_version, clustering_contract, feed_run_id,
                feed_schema_version, input_fingerprint, cluster_count,
                member_count, link_count, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                SCHEMA_VERSION,
                CLUSTERING_CONTRACT,
                run_feed_id,
                feed_run["schema_version"],
                fingerprint,
                len(clusters),
                sum(len(cluster["members"]) for cluster in clusters),
                sum(len(cluster["links"]) for cluster in clusters),
                now,
            ),
        )
        for cluster in clusters:
            representative = cluster["representative"]
            conn.execute(
                """INSERT INTO event_cluster
                   (run_id, event_id, representative_provider,
                    representative_post_id, canonical_identity_type,
                    canonical_identity_value, anchor_types_json, started_at,
                    last_activity_at, member_count, link_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    cluster["event_id"],
                    representative[0],
                    representative[1],
                    cluster["identity_kind"],
                    cluster["identity_value"],
                    _canonical_json(cluster["anchor_types"]),
                    cluster["started_at"],
                    cluster["last_activity_at"],
                    len(cluster["members"]),
                    len(cluster["links"]),
                ),
            )
            for member in cluster["members"]:
                row = posts[member]
                conn.execute(
                    """INSERT INTO event_member
                       (run_id, event_id, provider, post_id, post_type,
                        observed_directly, is_representative)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        cluster["event_id"],
                        member[0],
                        member[1],
                        row["post_type"],
                        int(row["observed_directly"] or 0),
                        int(member == representative),
                    ),
                )
            for link in cluster["links"]:
                conn.execute(
                    """INSERT INTO event_link
                       (run_id, event_id, provider, source_post_id,
                        target_post_id, link_type, anchor_value, discovered_at,
                        discovered_day, disclosure_post_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        cluster["event_id"],
                        link["provider"],
                        link["source_post_id"],
                        link["target_post_id"],
                        link["link_type"],
                        link["anchor_value"],
                        link["discovered_at"],
                        link["discovered_day"],
                        link["disclosure_post_id"],
                    ),
                )
                conn.execute(
                    """INSERT OR IGNORE INTO event_anchor
                       (run_id, event_id, anchor_type, anchor_value)
                       VALUES (?, ?, ?, ?)""",
                    (
                        run_id,
                        cluster["event_id"],
                        link["anchor_type"],
                        link["anchor_value"],
                    ),
                )
            for day, direct_count in sorted(cluster["days"].items()):
                conn.execute(
                    """INSERT INTO event_day
                       (run_id, event_id, day, direct_member_count)
                       VALUES (?, ?, ?, ?)""",
                    (run_id, cluster["event_id"], day, direct_count),
                )
    result = dict(
        conn.execute("SELECT * FROM event_run WHERE run_id = ?", (run_id,)).fetchone()
    )
    result["reused"] = False
    conn.close()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fli signal-events")
    parser.add_argument("action", choices=("refresh",))
    parser.add_argument("--feed-db", type=Path, default=DEFAULT_FEED_DB)
    parser.add_argument("--events-db", type=Path, default=DEFAULT_EVENTS_DB)
    parser.add_argument("--feed-run-id")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Atomically make the validated Feed/Event pair live.",
    )
    args = parser.parse_args(argv)
    result = materialize(
        feed_db=args.feed_db,
        events_db=args.events_db,
        feed_run_id=args.feed_run_id,
    )
    if args.publish:
        result = {
            **result,
            "publication": publish(
                events_db=args.events_db,
                feed_db=args.feed_db,
                event_run_id=result["run_id"],
            ),
        }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
