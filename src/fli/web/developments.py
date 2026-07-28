"""Ranked Development projection over artifact-linked exact Events."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any

from fli.evidence import developments as development_groups
from fli.evidence.artifacts import store as artifact_store
from fli.routing import view as audience_routing_store
from fli.scoring import attention
from fli.scoring import development_attention
from fli.web import events as event_store
from fli.web import feed as feed_store


DEFAULT_ARTIFACT_DB = artifact_store.DEFAULT_DB


def _cache_token(day: str) -> tuple[tuple[str, int, int, int, int], ...]:
    return (
        *event_store._cache_token(day),
        feed_store._db_version(DEFAULT_ARTIFACT_DB),
    )


def _rank_input_sha256(*, day: str, items: list[dict[str, Any]]) -> str:
    developments = []
    for item in sorted(items, key=lambda value: str(value["development_id"])):
        components = item["rank_components"]
        developments.append(
            {
                "development_id": str(item["development_id"]),
                "source_event_ids": sorted(item["source_event_ids"]),
                "participants": sorted(
                    [
                        [
                            int(participant["entity_id"]),
                            f"{float(participant['position']):.6f}",
                            sorted(participant["roles"]),
                        ]
                        for participant in components["participants"]
                    ],
                    key=lambda value: value[0],
                ),
                "public_interactions": int(components["public_interactions"]),
            }
        )
    return hashlib.sha256(
        json.dumps(
            {
                "day": day,
                "rank_version": development_attention.DAILY_RANK_VERSION,
                "bundle_contract": development_groups.BUNDLE_CONTRACT,
                "developments": developments,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _development_run_id(
    *,
    day: str,
    source_event_run_id: str,
    artifact_import_run_id: str | None,
) -> str:
    return hashlib.sha256(
        json.dumps(
            [
                development_groups.BUNDLE_CONTRACT,
                day,
                source_event_run_id,
                artifact_import_run_id,
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


@lru_cache(maxsize=16)
def _developments_day_cached(
    *,
    day: str,
    cache_token: tuple[tuple[str, int, int, int, int], ...],
) -> dict[str, Any]:
    del cache_token
    exact = event_store._events_day_cached(
        day=day,
        cache_token=event_store._cache_token(day),
    )
    if not exact.get("available"):
        return exact
    source_run = dict(exact.get("run") or {})
    source_event_run_id = str(source_run.get("run_id") or "")
    source_feed_run_id = str(source_run.get("feed_run_id") or "")
    if not source_event_run_id or not source_feed_run_id:
        return {
            "available": False,
            "reason": "The exact Event projection is missing run provenance.",
        }

    network_context = feed_store.rankings_store.entity_network_context()
    entity_ranks = feed_store.rankings_store.entity_network_ranks()
    if network_context is None or not entity_ranks:
        return {
            "available": False,
            "reason": (
                "The Development rank is unavailable because no completed "
                "Registry network analysis is present."
            ),
        }
    entity_positions = attention.entity_positions(entity_ranks)
    artifact_import_run_id = development_groups.artifact_import_run_id(
        artifact_db=DEFAULT_ARTIFACT_DB,
        source_event_run_id=source_event_run_id,
    )
    event_artifacts = development_groups.load_event_artifacts(
        artifact_db=DEFAULT_ARTIFACT_DB,
        day=day,
        source_event_run_id=source_event_run_id,
    )
    candidates = development_groups.bundle_events(
        items=list(exact.get("items") or []),
        event_artifacts=event_artifacts,
        entity_positions=entity_positions,
        day=day,
    )
    items = development_attention.rank_developments(
        [
            (
                {
                    key: value
                    for key, value in item.items()
                    if key != "_rank_inputs"
                },
                item["_rank_inputs"],
            )
            for item in candidates
        ]
    )
    rank_input_sha256 = _rank_input_sha256(day=day, items=items)
    routing_payload = audience_routing_store.routing_payload(
        day,
        expected_rank_input_sha256=rank_input_sha256,
        expected_event_run_id=source_event_run_id,
        expected_feed_run_id=source_feed_run_id,
    )
    routing_items = routing_payload["items"]
    for item in items:
        route = routing_items.get(item["development_id"])
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

    development_run_id = _development_run_id(
        day=day,
        source_event_run_id=source_event_run_id,
        artifact_import_run_id=artifact_import_run_id,
    )
    return {
        "available": True,
        "date": day,
        "audience_routing_run": routing_payload["run"],
        "run": {
            "run_id": source_event_run_id,
            "feed_run_id": source_feed_run_id,
            "development_run_id": development_run_id,
            "bundle_contract": development_groups.BUNDLE_CONTRACT,
            "source_event_clustering_contract": source_run.get(
                "clustering_contract"
            ),
            "artifact_import_run_id": artifact_import_run_id,
        },
        "rank_contract": {
            "version": development_attention.DAILY_RANK_VERSION,
            "kind": "daily_development_lexicographic",
            "layers": list(development_attention.LAYER_NAMES),
            "input_sha256": rank_input_sha256,
            "network": network_context,
            "development_run_id": development_run_id,
            "bundle_contract": development_groups.BUNDLE_CONTRACT,
            "note": (
                "Exact Events sharing an eligible canonical artifact on the "
                "same day form one Development. Distinct Registry entities "
                "that authored, quoted, or reposted any source count once."
            ),
        },
        "items": items,
    }


def _daily_rank_by_development_id(
    items: list[dict[str, Any]],
) -> dict[str, int]:
    return {
        str(item["development_id"]): int(item["daily_rank"])
        for item in items
    }


def current_rank_identity(*, day: str) -> dict[str, str]:
    payload = _developments_day_cached(day=day, cache_token=_cache_token(day))
    if not payload.get("available"):
        raise RuntimeError(str(payload.get("reason") or "Development rank unavailable"))
    rank_contract = dict(payload.get("rank_contract") or {})
    run = dict(payload.get("run") or {})
    return {
        "rank_version": str(rank_contract.get("version") or ""),
        "rank_input_sha256": str(rank_contract.get("input_sha256") or ""),
        "event_run_id": str(run.get("run_id") or ""),
        "feed_run_id": str(run.get("feed_run_id") or ""),
        "development_run_id": str(run.get("development_run_id") or ""),
    }


def analysis_packet_payload(
    *,
    day: str,
    development_id: str,
    artifact_db: Path | None = None,
) -> dict[str, Any]:
    """Preview the exact deterministic evidence packet without calling a model."""
    from fli.routing import model as routing_model
    from fli.routing import runs as routing_runs

    if not development_id:
        return {
            "available": False,
            "reason": "A Development ID is required to assemble an analysis packet.",
        }
    artifact_db = artifact_db or DEFAULT_ARTIFACT_DB
    projection = developments_payload(
        day=day,
        lane="all",
        sort="rank",
        query="",
        development_id=development_id,
        routing_filter="all",
        limit=1,
        offset=0,
        include_evidence=True,
    )
    if not projection.get("available"):
        return projection
    items = list(projection.get("items") or [])
    if not items:
        return {
            "available": False,
            "reason": "This Development is not available on the selected date.",
        }
    if not artifact_db.is_file():
        return {
            "available": False,
            "reason": "The source-artifact store needed to assemble this packet is unavailable.",
        }

    item = items[0]
    conn = sqlite3.connect(
        f"file:{artifact_db.resolve().as_posix()}?mode=ro",
        uri=True,
    )
    conn.row_factory = sqlite3.Row
    try:
        packet = routing_runs.packet_from_development(
            item,
            day=day,
            artifact_conn=conn,
        )
    finally:
        conn.close()
    if packet is None:
        return {
            "available": False,
            "reason": (
                "This Development has no current source post eligible for "
                "audience analysis."
            ),
        }

    visible_sources = [
        source for source in packet.sources if routing_model.is_model_visible(source)
    ]
    included_x_ids = {
        source.source_id
        for source in visible_sources
        if source.source_type == "x_post"
    }
    excluded_activity_ids = {
        str(evidence["post_id"])
        for evidence in item.get("evidence") or []
        if str(evidence["post_id"]) not in included_x_ids
    }
    source_posts = [
        source
        for source in visible_sources
        if source.relation in {"root", "independent_original"}
    ]
    author_updates = [
        source
        for source in visible_sources
        if source.relation == "same_author_continuation"
    ]
    artifacts = [
        source
        for source in visible_sources
        if source.source_type == "artifact"
    ]
    model_input = routing_model.render_input(packet)
    return {
        "available": True,
        "date": day,
        "development_id": development_id,
        "prompt_version": routing_model.PROMPT_VERSION,
        "evidence_sha256": packet.evidence_sha256,
        "input_sha256": packet.input_sha256,
        "input_tokens": routing_model.input_token_count(model_input),
        "calls_model": False,
        "counts": {
            "source_posts": len(source_posts),
            "author_updates": len(author_updates),
            "artifacts": len(artifacts),
            "trusted_participants": int(
                item["rank_components"]["trusted_attention"]
            ),
            "activity_posts_excluded": len(excluded_activity_ids),
        },
        "sources": [
            {
                "source_type": source.source_type,
                "source_id": source.source_id,
                "relation": source.relation,
                "author": source.author,
                "title": source.title,
                "url": source.url,
            }
            for source in visible_sources
        ],
        "model_input": model_input,
        "note": (
            "Source posts, current same-author updates, and retrieved artifacts "
            "establish meaning. Trusted reactions help rank the Development, but "
            "their text is not sent for audience analysis."
        ),
    }


def current_development_rank_by_event_id(*, day: str) -> dict[str, dict[str, Any]]:
    payload = _developments_day_cached(day=day, cache_token=_cache_token(day))
    if not payload.get("available"):
        return {}
    mapping: dict[str, dict[str, Any]] = {}
    for item in payload["items"]:
        value = {
            "development_id": str(item["development_id"]),
            "daily_rank": int(item["daily_rank"]),
        }
        for event_id in item["source_event_ids"]:
            mapping[str(event_id)] = value
    return mapping


def developments_payload(
    *,
    day: str,
    lane: str,
    sort: str,
    query: str,
    development_id: str = "",
    event_id: str = "",
    routing_filter: str = "all",
    limit: int,
    offset: int,
    include_evidence: bool = True,
) -> dict[str, Any]:
    if sort not in {"rank", "recent", "engagement"}:
        raise ValueError("sort must be 'rank', 'recent', or 'engagement'")
    payload = _developments_day_cached(day=day, cache_token=_cache_token(day))
    if not payload.get("available"):
        return payload

    daily_rank_by_id = _daily_rank_by_development_id(payload["items"])
    daily_rank_total = len(daily_rank_by_id)
    needle = query.strip().lower()
    items = [
        {
            **item,
            "daily_rank": daily_rank_by_id[item["development_id"]],
        }
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
                        f"{source['post']['author']['name']} "
                        f"{source['post']['author']['entity_name'] or ''} "
                        f"{source['post']['author']['handle']} "
                        f"{source['post']['text']}"
                        for source in item["source_events"]
                    ],
                    *[
                        str(artifact.get("title") or "")
                        + " "
                        + str(artifact["canonical_url"])
                        for artifact in item["development_artifacts"]
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
            key=lambda item: (
                item["latest_evidence_at"],
                item["development_id"],
            ),
            reverse=True,
        )
    elif sort == "engagement":
        items.sort(
            key=lambda item: (
                item["rank_components"]["public_interactions"],
                item["latest_evidence_at"],
                item["development_id"],
            ),
            reverse=True,
        )
    else:
        items.sort(
            key=lambda item: (
                item["daily_rank"],
                item["development_id"],
            )
        )

    if development_id or event_id:
        items = [
            item
            for item in items
            if (
                development_id
                and item["development_id"] == development_id
            )
            or (
                event_id
                and (
                    event_id == item["development_id"]
                    or event_id in item["source_event_ids"]
                )
            )
        ]
    total = len(items)
    page_items = []
    for item in items[offset : offset + limit]:
        projected = {
            **item,
            "relationship_counts": event_store._relationship_counts(item),
        }
        if not include_evidence:
            projected["evidence"] = []
            projected["amplifiers"] = []
            projected["root"] = {**item["root"], "amplifiers": []}
            projected["source_events"] = [
                {**source, "evidence": []}
                for source in item["source_events"]
            ]
        page_items.append(projected)
    return {
        **{key: value for key, value in payload.items() if key != "items"},
        "lane": lane,
        "sort": sort,
        "query": query,
        "development_id": development_id,
        "event_id": event_id,
        "routing_filter": routing_filter,
        "routing_counts": routing_counts,
        "daily_rank_total": daily_rank_total,
        "total": total,
        "limit": limit,
        "offset": offset,
        "include_evidence": include_evidence,
        "items": page_items,
    }


@lru_cache(maxsize=1)
def _dates_payload_cached(
    cache_token: tuple[tuple[str, int, int, int, int], ...],
) -> dict[str, Any]:
    del cache_token
    exact_dates = event_store.dates_payload()
    if not exact_dates.get("available"):
        return exact_dates
    dates = []
    for row in exact_dates.get("dates") or []:
        day = str(row["day"])
        projection = _developments_day_cached(
            day=day,
            cache_token=_cache_token(day),
        )
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
    return {
        **{
            key: value
            for key, value in exact_dates.items()
            if key not in {"dates", "run_id"}
        },
        "run_id": (
            _developments_day_cached(
                day=str(exact_dates["latest_complete_date"]),
                cache_token=_cache_token(
                    str(exact_dates["latest_complete_date"])
                ),
            )
            .get("run", {})
            .get("development_run_id")
        ),
        "dates": dates,
    }


def dates_payload() -> dict[str, Any]:
    return _dates_payload_cached(
        (
            *event_store._dates_cache_token(),
            feed_store._db_version(DEFAULT_ARTIFACT_DB),
        )
    )
