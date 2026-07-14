#!/usr/bin/env python3
"""Fail-closed audit for one published Feed/Event materialization pair."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from fli.web import events as web_events
from fli.web import feed as web_feed


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _configure(feed_db: Path, events_db: Path) -> None:
    web_events.DEFAULT_FEED_DB = feed_db
    web_events.DEFAULT_EVENTS_DB = events_db
    web_events.feed_store.DEFAULT_FEED_DB = feed_db
    web_feed.DEFAULT_FEED_DB = feed_db
    web_events._events_day_cached.cache_clear()


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _projection_value(value: Any) -> Any:
    """Strip mutable read-model annotations from structural projection proofs."""
    if isinstance(value, list):
        return [_projection_value(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _projection_value(item)
            for key, item in value.items()
            if key not in {"triage"}
        }
    return value


def audit(*, feed_db: Path, events_db: Path) -> dict[str, Any]:
    _configure(feed_db, events_db)
    feed = _connect(feed_db)
    events = _connect(events_db)
    events.execute("ATTACH DATABASE ? AS feed", (str(feed_db.resolve()),))
    failures: list[str] = []

    for label, conn in (("feed", feed), ("events", events)):
        integrity = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity != "ok":
            failures.append(f"{label} integrity_check: {integrity}")
        foreign_key_failures = conn.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_failures:
            failures.append(
                f"{label} foreign_key_check: {len(foreign_key_failures)} violations"
            )

    publication = events.execute(
        """SELECT run.*, publication.published_at
           FROM signal_publication publication
           JOIN event_run run ON run.run_id = publication.event_run_id
           WHERE publication.singleton = 1"""
    ).fetchone()
    if publication is None:
        raise RuntimeError("Event store has no explicit publication pointer.")
    run_id = str(publication["run_id"])
    feed_run_id = str(publication["feed_run_id"])

    post_provenance = {
        (str(row["provider"]), str(row["post_id"])): row
        for row in feed.execute(
            """SELECT provider, post_id, day, published_at,
                      first_discovered_day, first_discovered_at
               FROM feed_post WHERE run_id = ?""",
            (feed_run_id,),
        ).fetchall()
    }
    link_provenance: dict[tuple[str, str, str, str], str] = {}
    for row in events.execute(
        """SELECT provider, source_post_id, target_post_id, link_type,
                  MIN(discovered_day) AS discovered_day
           FROM event_link
           WHERE run_id = ?
           GROUP BY provider, source_post_id, target_post_id, link_type""",
        (run_id,),
    ).fetchall():
        link_provenance[
            (
                str(row["provider"]),
                str(row["source_post_id"]),
                str(row["target_post_id"]),
                str(row["link_type"]),
            )
        ] = str(row["discovered_day"])

    invalid_link_types = events.execute(
        """SELECT DISTINCT link_type FROM event_link
           WHERE run_id = ? AND link_type NOT IN ('quote', 'retweet', 'reply_parent')""",
        (run_id,),
    ).fetchall()
    if invalid_link_types:
        failures.append(
            "unexpected Event link types: "
            + ", ".join(str(row["link_type"]) for row in invalid_link_types)
        )

    duplicate_members = events.execute(
        """SELECT provider, post_id, COUNT(DISTINCT event_id) AS n
           FROM event_member WHERE run_id = ?
           GROUP BY provider, post_id HAVING n > 1""",
        (run_id,),
    ).fetchall()
    if duplicate_members:
        failures.append(f"{len(duplicate_members)} posts belong to multiple events")

    missing_relation_links = events.execute(
        """SELECT relation.provider, relation.source_post_id,
                  relation.target_post_id, relation.relation_type
           FROM feed.feed_relation relation
           WHERE relation.run_id = ?
             AND NOT EXISTS (
                 SELECT 1
                 FROM event_link link
                 WHERE link.run_id = ?
                   AND link.provider = relation.provider
                   AND link.source_post_id = relation.source_post_id
                   AND link.target_post_id = relation.target_post_id
                   AND link.link_type = relation.relation_type
             )""",
        (feed_run_id, run_id),
    ).fetchall()
    if missing_relation_links:
        failures.append(
            f"{len(missing_relation_links)} normalized provider relations are absent from Event links"
        )

    split_renderable_relations = events.execute(
        """SELECT relation.provider, relation.source_post_id,
                  relation.target_post_id
           FROM feed.feed_relation relation
           JOIN event_member source
             ON source.run_id = ? AND source.provider = relation.provider
            AND source.post_id = relation.source_post_id
           JOIN event_member target
             ON target.run_id = ? AND target.provider = relation.provider
            AND target.post_id = relation.target_post_id
           WHERE relation.run_id = ? AND source.event_id != target.event_id""",
        (run_id, run_id, feed_run_id),
    ).fetchall()
    if split_renderable_relations:
        failures.append(
            f"{len(split_renderable_relations)} renderable exact relations cross event boundaries"
        )

    day_rows = feed.execute(
        "SELECT date_from, date_to FROM feed_run WHERE run_id = ?", (feed_run_id,)
    ).fetchone()
    if day_rows is None:
        failures.append("published Event run references a missing Feed run")
        days: list[str] = []
    else:
        start = date.fromisoformat(str(day_rows["date_from"]))
        end = date.fromisoformat(str(day_rows["date_to"]))
        days = [
            date.fromordinal(ordinal).isoformat()
            for ordinal in range(start.toordinal(), end.toordinal() + 1)
        ]

    day_counts: dict[str, int] = {}
    canonical_roots: dict[str, set[str]] = defaultdict(set)
    daily_fingerprints: dict[str, str] = {}
    for day in days:
        payload = web_events.events_payload(
            day=day,
            lane="all",
            sort="attention",
            query="",
            triage_filter="all",
            limit=100_000,
            offset=0,
        )
        if not payload.get("available"):
            failures.append(f"{day} projection unavailable")
            continue
        items = payload["items"]
        day_counts[day] = len(items)
        event_ids = [str(item["event_id"]) for item in items]
        if len(event_ids) != len(set(event_ids)):
            failures.append(f"{day} contains duplicate event IDs")
        post_owners: dict[tuple[str, str], str] = {}
        cutoff = f"{day}T23:59:59.999999+00:00"
        for item in items:
            event_id = str(item["event_id"])
            canonical_roots[event_id].add(str(item["canonical_root_post_id"]))
            if str(item["latest_evidence_at"]) > cutoff:
                failures.append(f"{day} {event_id} leaks future latest_evidence_at")
            members = [item["root"], *item["evidence"]]
            for member in members:
                if str(member["published_at"]) > cutoff:
                    failures.append(
                        f"{day} {event_id} leaks future post {member['post_id']}"
                    )
                key = (str(member.get("provider") or ""), str(member["post_id"]))
                provenance = post_provenance.get(key)
                if provenance is None:
                    failures.append(f"{day} {event_id} references missing Feed post {key}")
                elif str(provenance["first_discovered_day"]) > day:
                    failures.append(
                        f"{day} {event_id} leaks post {key} first disclosed "
                        f"on {provenance['first_discovered_day']}"
                    )
                owner = post_owners.setdefault(key, event_id)
                if owner != event_id:
                    failures.append(
                        f"{day} post {key} appears in both {owner} and {event_id}"
                    )
            for evidence in item["evidence"]:
                relation_type = evidence.get("relation_type")
                target_post_id = evidence.get("target_post_id")
                if not relation_type or not target_post_id:
                    continue
                relation_key = (
                    str(evidence.get("provider") or ""),
                    str(evidence["post_id"]),
                    str(target_post_id),
                    str(relation_type),
                )
                discovered_day = link_provenance.get(relation_key)
                if discovered_day is None:
                    failures.append(
                        f"{day} {event_id} serializes missing relation {relation_key}"
                    )
                elif discovered_day > day:
                    failures.append(
                        f"{day} {event_id} leaks relation {relation_key} first "
                        f"disclosed on {discovered_day}"
                    )
        daily_fingerprints[day] = _fingerprint(_projection_value(items))

    unstable_roots = {
        event_id: sorted(roots)
        for event_id, roots in canonical_roots.items()
        if len(roots) > 1
    }
    if unstable_roots:
        failures.append(f"{len(unstable_roots)} event IDs changed canonical roots")

    if days:
        weekly = web_events.events_payload(
            day=days[-1],
            lane="all",
            sort="attention",
            query="",
            triage_filter="all",
            limit=100_000,
            offset=0,
            projection="week",
        )
        weekly_ids = [str(item["event_id"]) for item in weekly.get("items", [])]
        if len(weekly_ids) != len(set(weekly_ids)):
            failures.append("weekly projection contains duplicate event IDs")
        weekly_post_owners: dict[tuple[str, str], str] = {}
        for item in weekly.get("items", []):
            event_id = str(item["event_id"])
            for member in [item["root"], *item["evidence"]]:
                key = (str(member.get("provider") or ""), str(member["post_id"]))
                owner = weekly_post_owners.setdefault(key, event_id)
                if owner != event_id:
                    failures.append(
                        "weekly post "
                        f"{key} appears in both {owner} and {event_id}"
                    )
        weekly_count = len(weekly_ids)
        weekly_fingerprint = _fingerprint(
            _projection_value(weekly.get("items", []))
        )
    else:
        weekly_count = 0
        weekly_fingerprint = None

    result = {
        "ok": not failures,
        "feed_db": str(feed_db.resolve()),
        "events_db": str(events_db.resolve()),
        "feed_run_id": feed_run_id,
        "event_run_id": run_id,
        "date_from": days[0] if days else None,
        "date_to": days[-1] if days else None,
        "day_counts": day_counts,
        "daily_fingerprints": daily_fingerprints,
        "weekly_count": weekly_count,
        "weekly_fingerprint": weekly_fingerprint,
        "normalized_relation_count": int(
            feed.execute(
                "SELECT relation_count FROM feed_run WHERE run_id = ?", (feed_run_id,)
            ).fetchone()[0]
        ),
        "event_cluster_count": int(publication["cluster_count"]),
        "event_member_count": int(publication["member_count"]),
        "event_link_count": int(publication["link_count"]),
        "failures": failures,
    }
    feed.close()
    events.close()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed-db", type=Path, required=True)
    parser.add_argument("--events-db", type=Path, required=True)
    args = parser.parse_args()
    result = audit(feed_db=args.feed_db, events_db=args.events_db)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
