"""Deterministic freshness policy for first-party X evidence."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping


POLICY_VERSION = "x-artifact-source-window-v2"
MAX_SOURCE_AGE_DAYS = 7


def _date(value: str) -> date:
    text = value.strip()
    if not text:
        raise ValueError("source publication time is empty")
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise ValueError(f"invalid source publication time: {value!r}") from exc


def is_current(*, published_at: str, evaluation_day: str) -> bool:
    """Return whether a source is no more than seven days old on the brief day."""
    source_day = _date(published_at)
    brief_day = datetime.strptime(evaluation_day, "%Y-%m-%d").date()
    age_days = (brief_day - source_day).days
    return 0 <= age_days <= MAX_SOURCE_AGE_DAYS


def prune_packet_payload(
    packet: Mapping[str, Any],
    *,
    evaluation_day: str,
    published_at_by_source_id: Mapping[str, str],
    artifact_disclosures_by_id: Mapping[str, list[Mapping[str, str]]] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Project one packet onto current X evidence and its disclosed artifacts."""
    raw_sources = packet.get("sources")
    if not isinstance(raw_sources, list):
        raise ValueError("routing packet sources must be a list")

    retained_x: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    stale_source_ids: list[str] = []
    root_was_current = False
    for raw_source in raw_sources:
        if not isinstance(raw_source, dict):
            raise ValueError("routing packet source must be an object")
        source = dict(raw_source)
        if source.get("source_type") != "x_post":
            artifacts.append(source)
            continue
        source_id = str(source.get("source_id") or "")
        published_at = str(published_at_by_source_id.get(source_id) or "")
        if not published_at:
            raise ValueError(
                f"X source {source_id!r} has no application-owned publication time"
            )
        source["posted"] = published_at
        if not is_current(
            published_at=published_at,
            evaluation_day=evaluation_day,
        ):
            stale_source_ids.append(source_id)
            continue
        if source.get("relation") == "root":
            root_was_current = True
        retained_x.append(source)

    summary = {
        "policy_version": POLICY_VERSION,
        "max_source_age_days": MAX_SOURCE_AGE_DAYS,
        "stale_x_source_ids": stale_source_ids,
        "stale_x_source_count": len(stale_source_ids),
        "excluded_artifact_ids": [],
        "excluded_artifact_count": 0,
        "root_replaced": False,
    }
    if not retained_x:
        return None, {**summary, "excluded": True}

    if not root_was_current:
        retained_x[0]["relation"] = "root"
        for source in retained_x[1:]:
            source["relation"] = "same_author_continuation"
        summary["root_replaced"] = True

    retained_source_ids = {
        str(source.get("source_id") or "") for source in retained_x
    }
    disclosure_index = artifact_disclosures_by_id or {}
    retained_artifacts: list[dict[str, Any]] = []
    excluded_artifact_ids: list[str] = []
    for artifact in artifacts:
        artifact_id = str(artifact.get("source_id") or "")
        disclosures = disclosure_index.get(artifact_id, [])
        eligible_disclosures = [
            dict(disclosure)
            for disclosure in disclosures
            if str(disclosure.get("source_id") or "") in retained_source_ids
            and str(disclosure.get("published_at") or "")
            and is_current(
                published_at=str(disclosure["published_at"]),
                evaluation_day=evaluation_day,
            )
        ]
        if not eligible_disclosures:
            excluded_artifact_ids.append(artifact_id)
            continue
        retained_artifacts.append(
            {
                **artifact,
                "disclosures": eligible_disclosures,
            }
        )
    summary["excluded_artifact_ids"] = excluded_artifact_ids
    summary["excluded_artifact_count"] = len(excluded_artifact_ids)

    return (
        {
            **dict(packet),
            "sources": [*retained_x, *retained_artifacts],
        },
        {**summary, "excluded": False},
    )
