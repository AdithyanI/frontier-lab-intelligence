"""Content-addressed exact structural groups over one deterministic Feed run.

Version one performs no topical inference. It connects posts only when the
provider supplies the same quote/retweet target, reply parent, or conversation
identifier. The post-level Feed remains the complete evidence ledger.
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


SCHEMA_VERSION = "signal-events-v1"
CLUSTERING_CONTRACT = "exact-structural-v1"
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

CREATE TABLE IF NOT EXISTS event_link (
    run_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    source_post_id TEXT NOT NULL,
    target_post_id TEXT NOT NULL,
    link_type TEXT NOT NULL CHECK (
        link_type IN ('quote', 'retweet', 'reply_parent', 'same_conversation')
    ),
    anchor_value TEXT NOT NULL,
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

CREATE TABLE IF NOT EXISTS event_anchor (
    run_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    anchor_type TEXT NOT NULL CHECK (
        anchor_type IN ('same_target', 'same_conversation', 'reply_parent')
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
"""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def connect(path: Path | str = DEFAULT_EVENTS_DB) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
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
        """SELECT provider, source_post_id, target_post_id, relation_type
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
        tuple[str, str, str, str, str], dict[str, str]
    ] = {}

    def add_link(
        provider: str,
        source_post_id: str,
        target_post_id: str,
        link_type: str,
        anchor_type: str,
        anchor_value: str,
    ) -> None:
        source = (provider, source_post_id)
        target = (provider, target_post_id)
        if source == target or source not in posts or target not in posts:
            return
        union.union(source, target)
        links[(provider, source_post_id, target_post_id, link_type, anchor_value)] = {
            "provider": provider,
            "source_post_id": source_post_id,
            "target_post_id": target_post_id,
            "link_type": link_type,
            "anchor_type": anchor_type,
            "anchor_value": anchor_value,
        }

    for relation in relation_rows:
        add_link(
            relation["provider"],
            relation["source_post_id"],
            relation["target_post_id"],
            relation["relation_type"],
            "same_target",
            relation["target_post_id"],
        )

    replies_by_conversation: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for key, row in posts.items():
        if row["post_type"] != "reply":
            continue
        conversation_id = str(row["conversation_id"] or "")
        parent_id = str(row["in_reply_to_post_id"] or "")
        if conversation_id:
            replies_by_conversation[conversation_id].append(key)
        if parent_id and (row["provider"], parent_id) in posts:
            add_link(
                row["provider"],
                row["post_id"],
                parent_id,
                "reply_parent",
                "reply_parent",
                parent_id,
            )

    for conversation_id, replies in replies_by_conversation.items():
        ordered = sorted(set(replies))
        provider = ordered[0][0]
        root = (provider, conversation_id)
        anchor = root if root in posts else ordered[0]
        for reply in ordered:
            if reply != anchor:
                add_link(
                    provider,
                    reply[1],
                    anchor[1],
                    "same_conversation",
                    "same_conversation",
                    conversation_id,
                )

    groups: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    for node in union.parent:
        groups[union.find(node)].add(node)

    link_values = list(links.values())
    clusters: list[dict[str, Any]] = []
    for members in groups.values():
        if len(members) < 2:
            continue
        member_links = [
            link
            for link in link_values
            if (link["provider"], link["source_post_id"]) in members
            and (link["provider"], link["target_post_id"]) in members
        ]
        if not member_links:
            continue
        inbound: dict[tuple[str, str], int] = defaultdict(int)
        for link in member_links:
            inbound[(link["provider"], link["target_post_id"])] += 1
        type_priority = {"original": 0, "reply": 1, "quote": 2, "retweet": 3}
        representative = sorted(
            members,
            key=lambda key: (
                -inbound[key],
                type_priority.get(str(posts[key]["post_type"]), 9),
                -int(posts[key]["observed_directly"] or 0),
                str(posts[key]["published_at"]),
                key,
            ),
        )[0]
        event_id = _sha256(_canonical_json(sorted(members)))
        direct_rows = [row for key in members if (row := posts[key])["observed_directly"]]
        activity_rows = direct_rows or [posts[key] for key in members]
        days: dict[str, int] = defaultdict(int)
        for row in direct_rows:
            days[str(row["day"])] += 1
        clusters.append(
            {
                "event_id": event_id,
                "representative": representative,
                "members": sorted(members),
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
                    representative_post_id, anchor_types_json, started_at,
                    last_activity_at, member_count, link_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    cluster["event_id"],
                    representative[0],
                    representative[1],
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
                        target_post_id, link_type, anchor_value)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        cluster["event_id"],
                        link["provider"],
                        link["source_post_id"],
                        link["target_post_id"],
                        link["link_type"],
                        link["anchor_value"],
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
    args = parser.parse_args(argv)
    result = materialize(
        feed_db=args.feed_db,
        events_db=args.events_db,
        feed_run_id=args.feed_run_id,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
