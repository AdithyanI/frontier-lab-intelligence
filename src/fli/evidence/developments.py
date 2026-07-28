"""Artifact-anchored Developments over immutable exact X Events."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fli.scoring import development_attention


BUNDLE_CONTRACT = "canonical-artifact-development-v1"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


def artifact_is_merge_anchor(canonical_url: str) -> bool:
    """Reject generic host roots while retaining release-specific documents."""
    parsed = urlsplit(canonical_url)
    return bool(parsed.hostname and parsed.path.rstrip("/"))


def artifact_import_run_id(
    *,
    artifact_db: Path,
    source_event_run_id: str,
) -> str | None:
    if not artifact_db.is_file():
        return None
    conn = sqlite3.connect(
        f"file:{artifact_db.resolve().as_posix()}?mode=ro",
        uri=True,
    )
    try:
        row = conn.execute(
            """SELECT import_run_id
               FROM artifact_import_run
               WHERE source_event_run_id = ?
               ORDER BY completed_at DESC, import_run_id DESC
               LIMIT 1""",
            (source_event_run_id,),
        ).fetchone()
    finally:
        conn.close()
    return str(row[0]) if row is not None else None


def load_event_artifacts(
    *,
    artifact_db: Path,
    day: str,
    source_event_run_id: str,
) -> dict[str, list[dict[str, Any]]]:
    """Return current accepted canonical artifacts keyed by exact Event ID."""
    if not artifact_db.is_file():
        return {}
    conn = sqlite3.connect(
        f"file:{artifact_db.resolve().as_posix()}?mode=ro",
        uri=True,
    )
    conn.row_factory = sqlite3.Row
    try:
        import_run = conn.execute(
            """SELECT import_run_id
               FROM artifact_import_run
               WHERE source_event_run_id = ?
               ORDER BY completed_at DESC, import_run_id DESC
               LIMIT 1""",
            (source_event_run_id,),
        ).fetchone()
        if import_run is None:
            return {}
        rows = conn.execute(
            """SELECT DISTINCT candidate.event_id, candidate.source_rank,
                              artifact.artifact_id, artifact.canonical_url,
                              artifact.artifact_kind, artifact.title
               FROM artifact_import_candidate AS candidate
               JOIN artifact USING (artifact_id)
               WHERE candidate.import_run_id = ?
                 AND candidate.event_day = ?
                 AND candidate.decision = 'accepted'
                 AND candidate.artifact_id IS NOT NULL
               ORDER BY candidate.event_id, candidate.source_rank,
                        artifact.canonical_url""",
            (str(import_run["import_run_id"]), day),
        ).fetchall()
        tables = {
            str(row["name"])
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        supplement_rows: list[sqlite3.Row] = []
        if "artifact_event_supplement" in tables:
            supplement_rows = conn.execute(
                """SELECT DISTINCT supplement.event_id,
                                  supplement.source_rank,
                                  artifact.artifact_id,
                                  artifact.canonical_url,
                                  artifact.artifact_kind,
                                  artifact.title
                   FROM artifact_event_supplement AS supplement
                   JOIN artifact USING (artifact_id)
                   WHERE supplement.event_day = ?
                   ORDER BY supplement.event_id, supplement.source_rank,
                            artifact.canonical_url""",
                (day,),
            ).fetchall()
    finally:
        conn.close()

    by_event: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in [*rows, *supplement_rows]:
        artifact_id = str(row["artifact_id"])
        by_event[str(row["event_id"])][artifact_id] = {
            "artifact_id": artifact_id,
            "canonical_url": str(row["canonical_url"]),
            "artifact_kind": str(row["artifact_kind"]),
            "title": str(row["title"] or "") or None,
            "source_rank": int(row["source_rank"]),
            "merge_anchor": artifact_is_merge_anchor(str(row["canonical_url"])),
        }
    return {
        event_id: sorted(
            artifacts.values(),
            key=lambda artifact: (
                int(artifact["source_rank"]),
                str(artifact["canonical_url"]),
            ),
        )
        for event_id, artifacts in by_event.items()
    }


def _components(
    event_ids: list[str],
    event_artifacts: dict[str, list[dict[str, Any]]],
) -> list[list[str]]:
    parent = {event_id: event_id for event_id in event_ids}

    def find(event_id: str) -> str:
        while parent[event_id] != event_id:
            parent[event_id] = parent[parent[event_id]]
            event_id = parent[event_id]
        return event_id

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return
        low, high = sorted((left_root, right_root))
        parent[high] = low

    events_by_artifact: dict[str, list[str]] = defaultdict(list)
    event_id_set = set(event_ids)
    for event_id, artifacts in event_artifacts.items():
        if event_id not in event_id_set:
            continue
        for artifact in artifacts:
            if artifact["merge_anchor"]:
                events_by_artifact[str(artifact["artifact_id"])].append(event_id)
    for linked_event_ids in events_by_artifact.values():
        linked = sorted(set(linked_event_ids))
        for event_id in linked[1:]:
            union(linked[0], event_id)

    grouped: dict[str, list[str]] = defaultdict(list)
    for event_id in event_ids:
        grouped[find(event_id)].append(event_id)
    return sorted(
        (sorted(values) for values in grouped.values()),
        key=lambda values: values[0],
    )


def _primary_key(item: dict[str, Any]) -> tuple[Any, ...]:
    author = item["root"]["author"]
    return (
        str(author.get("entity_kind") or "") != "organization",
        int(item["daily_rank"]),
        str(item["event_id"]),
    )


def _source_summary(
    item: dict[str, Any],
    artifacts: list[dict[str, Any]],
    *,
    is_primary: bool,
) -> dict[str, Any]:
    root = item["root"]
    return {
        "event_id": str(item["event_id"]),
        "semantic_snapshot_sha256": str(item["semantic_snapshot_sha256"]),
        "is_primary": is_primary,
        "member_count": int(item["member_count"]),
        "why_grouped": list(item["why_grouped"]),
        "evidence": list(item["evidence"]),
        "post": {
            **root,
            "amplifiers": [],
        },
        "artifacts": [
            {key: value for key, value in artifact.items() if key != "source_rank"}
            for artifact in artifacts
        ],
    }


def _evidence_from_root(item: dict[str, Any], primary: dict[str, Any]) -> dict[str, Any]:
    root = item["root"]
    return {
        "post_id": str(root["post_id"]),
        "author": {
            "handle": str(root["author"]["handle"]),
            "name": str(root["author"]["name"]),
            "entity_id": root["author"].get("entity_id"),
            "entity_name": root["author"].get("entity_name"),
        },
        "published_at": str(root["published_at"]),
        "text": str(root.get("text") or ""),
        "url": str(root["url"]),
        "post_type": str(root["post_type"]),
        "observed_directly": bool(root["observed_directly"]),
        "day": str(root["published_at"])[:10],
        "relationship": "related",
        "relation_type": None,
        "target_post_id": None,
        "parent_post_id": None,
        "parent_missing": False,
        "depth": 0,
        "same_author_as_root": (
            str(root["author"]["handle"]).lower()
            == str(primary["root"]["author"]["handle"]).lower()
        ),
        "source_event_id": str(item["event_id"]),
        "is_development_source": True,
    }


def _participants(
    items: list[dict[str, Any]],
    entity_positions: dict[int, float],
) -> tuple[development_attention.Participant, ...]:
    values: dict[int, dict[str, Any]] = {}

    def add(
        *,
        entity_id: int,
        position: float,
        entity_name: str,
        entity_kind: str,
        handle: str,
        role: str,
        source_url: str,
    ) -> None:
        current = values.setdefault(
            entity_id,
            {
                "position": position,
                "entity_name": entity_name,
                "entity_kind": entity_kind,
                "handle": handle,
                "roles": set(),
                "source_urls": set(),
            },
        )
        current["roles"].add(role)
        if source_url:
            current["source_urls"].add(source_url)

    for item in items:
        root = item["root"]
        author = root["author"]
        entity_id = author.get("entity_id")
        if entity_id is not None:
            add(
                entity_id=int(entity_id),
                position=float(entity_positions.get(int(entity_id), 0.0)),
                entity_name=str(author.get("entity_name") or author.get("name") or ""),
                entity_kind=str(author.get("entity_kind") or ""),
                handle=str(author.get("handle") or ""),
                role="source",
                source_url=str(root.get("url") or ""),
            )
        for voter in item["rank_components"]["voters"]:
            voter_id = int(voter["entity_id"])
            add(
                entity_id=voter_id,
                position=float(voter["position"]),
                entity_name=str(voter.get("entity_name") or ""),
                entity_kind=str(voter.get("entity_kind") or ""),
                handle=str(voter.get("handle") or ""),
                role=str(voter.get("relation_type") or "retweet"),
                source_url=str(voter.get("source_url") or ""),
            )
    return tuple(
        development_attention.Participant(
            entity_id=entity_id,
            position=value["position"],
            entity_name=value["entity_name"],
            entity_kind=value["entity_kind"],
            handle=value["handle"],
            roles=tuple(value["roles"]),
            source_urls=tuple(value["source_urls"]),
        )
        for entity_id, value in sorted(values.items())
    )


def bundle_events(
    *,
    items: list[dict[str, Any]],
    event_artifacts: dict[str, list[dict[str, Any]]],
    entity_positions: dict[int, float],
    day: str,
) -> list[dict[str, Any]]:
    """Return Development candidates with exact Event provenance preserved."""
    by_id = {str(item["event_id"]): item for item in items}
    output: list[dict[str, Any]] = []
    for event_ids in _components(sorted(by_id), event_artifacts):
        source_items = [by_id[event_id] for event_id in event_ids]
        primary = min(source_items, key=_primary_key)
        primary_event_id = str(primary["event_id"])
        shared_artifacts: dict[str, dict[str, Any]] = {}
        artifact_event_ids: dict[str, set[str]] = defaultdict(set)
        for event_id in event_ids:
            for artifact in event_artifacts.get(event_id, []):
                artifact_id = str(artifact["artifact_id"])
                shared_artifacts[artifact_id] = artifact
                artifact_event_ids[artifact_id].add(event_id)
        merge_artifacts = [
            shared_artifacts[artifact_id]
            for artifact_id, linked_ids in artifact_event_ids.items()
            if len(linked_ids) > 1 and shared_artifacts[artifact_id]["merge_anchor"]
        ]
        if merge_artifacts:
            anchor = min(
                merge_artifacts,
                key=lambda artifact: (
                    int(artifact["source_rank"]),
                    str(artifact["canonical_url"]),
                ),
            )
            development_id = _sha256(
                [BUNDLE_CONTRACT, "artifact", str(anchor["artifact_id"])]
            )
        else:
            development_id = _sha256(
                [BUNDLE_CONTRACT, "event", primary_event_id]
            )

        amplifiers: dict[int, dict[str, Any]] = {}
        for item in source_items:
            for amplifier in item["amplifiers"]:
                amplifiers[int(amplifier["entity_id"])] = amplifier
        sorted_amplifiers = sorted(
            amplifiers.values(),
            key=lambda amplifier: (
                -float(amplifier["network_position"]),
                int(amplifier["entity_id"]),
            ),
        )
        root = {
            **primary["root"],
            "author": dict(primary["root"]["author"]),
            "metrics": dict(primary["root"]["metrics"]),
            "amplifiers": sorted_amplifiers,
        }

        evidence: list[dict[str, Any]] = []
        seen_posts = {str(root["post_id"])}
        for item in sorted(source_items, key=_primary_key):
            if item is not primary and str(item["root"]["post_id"]) not in seen_posts:
                evidence.append(_evidence_from_root(item, primary))
                seen_posts.add(str(item["root"]["post_id"]))
            for row in item["evidence"]:
                post_id = str(row["post_id"])
                if post_id in seen_posts:
                    continue
                evidence.append(
                    {
                        **row,
                        "source_event_id": str(item["event_id"]),
                        "is_development_source": False,
                    }
                )
                seen_posts.add(post_id)

        participants = _participants(source_items, entity_positions)
        source_events = [
            _source_summary(
                item,
                event_artifacts.get(str(item["event_id"]), []),
                is_primary=str(item["event_id"]) == primary_event_id,
            )
            for item in sorted(source_items, key=_primary_key)
        ]
        development_artifacts = [
            {
                **{
                    key: value
                    for key, value in artifact.items()
                    if key not in {"source_rank", "merge_anchor"}
                },
                "source_event_ids": sorted(artifact_event_ids[artifact_id]),
                "is_merge_basis": len(artifact_event_ids[artifact_id]) > 1
                and bool(artifact["merge_anchor"]),
            }
            for artifact_id, artifact in sorted(
                shared_artifacts.items(),
                key=lambda value: (
                    int(value[1]["source_rank"]),
                    str(value[1]["canonical_url"]),
                ),
            )
        ]
        semantic_snapshot_sha256 = _sha256(
            {
                "contract": BUNDLE_CONTRACT,
                "day": day,
                "development_id": development_id,
                "primary_event_id": primary_event_id,
                "source_events": [
                    [
                        str(item["event_id"]),
                        str(item["semantic_snapshot_sha256"]),
                    ]
                    for item in sorted(source_items, key=lambda row: str(row["event_id"]))
                ],
                "artifacts": [
                    [
                        artifact["artifact_id"],
                        artifact["canonical_url"],
                        artifact["source_event_ids"],
                    ]
                    for artifact in development_artifacts
                ],
            }
        )
        activity_days = sorted(
            {
                activity_day
                for item in source_items
                for activity_day in item["activity_days"]
            }
        )
        participant_ids = {participant.entity_id for participant in participants}
        output.append(
            {
                "development_id": development_id,
                "semantic_snapshot_sha256": semantic_snapshot_sha256,
                "bundle_contract": BUNDLE_CONTRACT,
                "primary_event_id": primary_event_id,
                "source_event_ids": event_ids,
                "source_event_count": len(event_ids),
                "source_events": source_events,
                "development_artifacts": development_artifacts,
                "root": root,
                "is_grouped": len(event_ids) > 1 or any(
                    bool(item["is_grouped"]) for item in source_items
                ),
                "why_grouped": [
                    f"Shared canonical artifact: {artifact['canonical_url']}"
                    for artifact in development_artifacts
                    if artifact["is_merge_basis"]
                ],
                "anchor_types": (
                    ["shared_artifact"] if len(event_ids) > 1 else []
                ),
                "member_count": sum(int(item["member_count"]) for item in source_items),
                "lifetime_member_count": sum(
                    int(item["lifetime_member_count"]) for item in source_items
                ),
                "day_member_count": sum(
                    int(item["day_member_count"]) for item in source_items
                ),
                "activity_days": activity_days,
                "first_activity_day": min(
                    str(item["first_activity_day"]) for item in source_items
                ),
                "link_count": sum(int(item["link_count"]) for item in source_items),
                "author_count": len(
                    {
                        str(source["post"]["author"]["handle"]).lower()
                        for source in source_events
                    }
                ),
                "registry_entity_count": len(participant_ids),
                "first_hand_count": sum(
                    int(item["first_hand_count"]) for item in source_items
                ),
                "original_poster_count": sum(
                    1
                    for participant in participants
                    if "source" in participant.roles
                ),
                "amplifier_count": sum(
                    1
                    for participant in participants
                    if {"quote", "retweet"} & set(participant.roles)
                ),
                "amplifiers": sorted_amplifiers,
                "latest_evidence_at": max(
                    str(item["latest_evidence_at"]) for item in source_items
                ),
                "evidence": evidence,
                "_rank_inputs": development_attention.RankInputs(
                    participants=participants,
                    public_interactions=max(
                        int(item["rank_components"]["public_interactions"])
                        for item in source_items
                    ),
                    development_id=development_id,
                ),
            }
        )
    return output
