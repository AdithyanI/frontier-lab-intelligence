"""Strict draft contract for agent-authored daily audience intelligence.

The agent is free to research and reason.  This module owns the narrow boundary
between that work and durable product state: audience-specific reader fields,
evidence links, citations, and complete disposition of the frozen routed cohort.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
import re
from typing import Any


DRAFT_SCHEMA_VERSION = "daily-intelligence-draft-v4"
AUDIENCES = ("investment", "ai_engineering")
EVENT_ROLES = ("primary", "supporting", "context", "counterevidence")
CITATION_KINDS = ("event", "artifact", "web", "context")
ENTITY_SCOPES = ("portfolio", "outside_portfolio")
IMPACT_DIRECTIONS = ("positive", "negative", "mixed", "uncertain")

_LOCAL_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")


def output_contract() -> dict[str, Any]:
    """Return the stable, machine-readable authoring contract."""
    return {
        "schema_version": DRAFT_SCHEMA_VERSION,
        "audiences": list(AUDIENCES),
        "max_insights_per_audience": None,
        "event_roles": list(EVENT_ROLES),
        "citation_kinds": list(CITATION_KINDS),
        "entity_scopes": list(ENTITY_SCOPES),
        "impact_directions": list(IMPACT_DIRECTIONS),
        "analysis_shapes": {
            "investment": investment_analysis_template(),
            "ai_engineering": engineering_analysis_template(),
        },
        "coverage_rule": (
            "Every positively routed Event/audience pair must appear exactly once "
            "in an insight event_links list or in not_selected."
        ),
        "draft_shape": {
            "schema_version": DRAFT_SCHEMA_VERSION,
            "workspace_run_id": "<from manifest>",
            "workspace_manifest_sha256": "<from manifest>",
            "agent": {
                "skill_version": "fli-daily-intelligence-v3",
                "model": "codex",
                "notes": None,
            },
            "insights": [
                {
                    "local_id": "investment-example",
                    "audience": "investment",
                    "rank": 1,
                    "rank_rationale": (
                        "Why this Insight has this audience decision priority "
                        "relative to the rest of the daily brief."
                    ),
                    "title": "Judgment-led headline",
                    "what_changed": "Evidence-grounded factual synthesis.",
                    "interpretation": (
                        "One audience-specific argument connecting the evidence to "
                        "an operating, financial, or engineering decision."
                    ),
                    "next_step": "One concrete diligence or engineering action.",
                    "analysis": investment_analysis_template(),
                    "event_links": [
                        {
                            "event_id": "<event id>",
                            "role": "primary",
                            "reason": "Why this Event supports the Insight.",
                        }
                    ],
                    "citation_ids": ["source-1"],
                }
            ],
            "not_selected": [
                {
                    "event_id": "<event id>",
                    "audience": "investment",
                    "reason": "Why it does not clear the final daily brief.",
                }
            ],
            "citations": [citation_template()],
        },
    }


def investment_analysis_template() -> dict[str, Any]:
    return {
        "affected_entities": [],
        "key_uncertainty": "The strongest reason the interpretation may be wrong or fail to matter.",
        "watchpoints": ["A measurable confirmation or falsification signal."],
    }


def engineering_analysis_template() -> dict[str, Any]:
    return {
        "decision_rule": (
            "The measurable result that would justify proceeding, together with "
            "the result that would reject or pause the idea."
        ),
    }


def citation_template() -> dict[str, Any]:
    return {
        "local_id": "source-1",
        "kind": "event",
        "url": "https://example.com/source",
        "title": "Source title",
        "event_id": None,
        "artifact_id": None,
        "published_at": None,
        "retrieved_at": None,
        "supports": "The exact claim this source supports.",
        "excerpt": None,
    }


def draft_template(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": DRAFT_SCHEMA_VERSION,
        "workspace_run_id": str(manifest["run_id"]),
        "workspace_manifest_sha256": str(manifest["manifest_sha256"]),
        "agent": {
            "skill_version": "fli-daily-intelligence-v3",
            "model": "codex",
            "notes": None,
        },
        "insights": [],
        "not_selected": [],
        "citations": [],
    }


def _object(value: Any, path: str, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object")
    actual = set(value)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        detail = []
        if missing:
            detail.append(f"missing {missing}")
        if extra:
            detail.append(f"unexpected {extra}")
        raise ValueError(f"{path} has the wrong fields: {'; '.join(detail)}")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be an array")
    return value


def _text(value: Any, path: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a non-empty string")
    return " ".join(value.split())


def _texts(
    value: Any,
    path: str,
    *,
    minimum: int = 0,
    maximum: int = 8,
) -> list[str]:
    values = _list(value, path)
    if not minimum <= len(values) <= maximum:
        raise ValueError(f"{path} must contain between {minimum} and {maximum} items")
    return [str(_text(item, f"{path}[{index}]")) for index, item in enumerate(values)]


def _enum(value: Any, path: str, choices: tuple[str, ...]) -> str:
    selected = _text(value, path)
    assert selected is not None
    if selected not in choices:
        raise ValueError(f"{path} must be one of {list(choices)}")
    return selected


def _optional_date(value: Any, path: str) -> str | None:
    selected = _text(value, path, nullable=True)
    if selected is None:
        return None
    try:
        date.fromisoformat(selected)
    except ValueError as error:
        raise ValueError(f"{path} must be an ISO date or null") from error
    return selected


def _optional_datetime(value: Any, path: str) -> str | None:
    selected = _text(value, path, nullable=True)
    if selected is None:
        return None
    try:
        datetime.fromisoformat(selected.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{path} must be an ISO datetime or null") from error
    return selected


def _local_id(value: Any, path: str) -> str:
    selected = _text(value, path)
    assert selected is not None
    if _LOCAL_ID.fullmatch(selected) is None:
        raise ValueError(f"{path} must be a 2-64 character lowercase slug")
    return selected


def _validate_investment_analysis(value: Any, path: str) -> dict[str, Any]:
    analysis = _object(
        value,
        path,
        {
            "affected_entities",
            "key_uncertainty",
            "watchpoints",
        },
    )
    entities = []
    for index, raw in enumerate(_list(analysis["affected_entities"], f"{path}.affected_entities")):
        entity_path = f"{path}.affected_entities[{index}]"
        entity = _object(raw, entity_path, {"name", "scope", "impact", "mechanism"})
        entities.append(
            {
                "name": _text(entity["name"], f"{entity_path}.name"),
                "scope": _enum(entity["scope"], f"{entity_path}.scope", ENTITY_SCOPES),
                "impact": _enum(
                    entity["impact"], f"{entity_path}.impact", IMPACT_DIRECTIONS
                ),
                "mechanism": _text(entity["mechanism"], f"{entity_path}.mechanism"),
            }
        )
    return {
        "affected_entities": entities,
        "key_uncertainty": _text(analysis["key_uncertainty"], f"{path}.key_uncertainty"),
        "watchpoints": _texts(analysis["watchpoints"], f"{path}.watchpoints", minimum=1, maximum=3),
    }


def _validate_engineering_analysis(value: Any, path: str) -> dict[str, Any]:
    analysis = _object(value, path, {"decision_rule"})
    return {
        "decision_rule": _text(analysis["decision_rule"], f"{path}.decision_rule"),
    }


def validate_draft(draft: Any, manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate and normalize one complete agent result against its frozen cohort."""
    value = _object(
        draft,
        "draft",
        {
            "schema_version",
            "workspace_run_id",
            "workspace_manifest_sha256",
            "agent",
            "insights",
            "not_selected",
            "citations",
        },
    )
    if value["schema_version"] != DRAFT_SCHEMA_VERSION:
        raise ValueError(f"draft.schema_version must be {DRAFT_SCHEMA_VERSION!r}")
    if value["workspace_run_id"] != manifest.get("run_id"):
        raise ValueError("draft.workspace_run_id does not match the workspace")
    if value["workspace_manifest_sha256"] != manifest.get("manifest_sha256"):
        raise ValueError("draft.workspace_manifest_sha256 does not match the frozen manifest")

    agent = _object(value["agent"], "draft.agent", {"skill_version", "model", "notes"})
    normalized_agent = {
        "skill_version": _text(agent["skill_version"], "draft.agent.skill_version"),
        "model": _text(agent["model"], "draft.agent.model"),
        "notes": _text(agent["notes"], "draft.agent.notes", nullable=True),
    }

    events = {str(event["event_id"]): event for event in manifest.get("events", [])}
    if not events:
        raise ValueError("workspace manifest has no Events")
    expected_pairs = {
        (event_id, audience)
        for event_id, event in events.items()
        for audience in event.get("audiences", [])
    }
    handled_pairs: set[tuple[str, str]] = set()

    citations: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(_list(value["citations"], "draft.citations")):
        path = f"draft.citations[{index}]"
        citation = _object(
            raw,
            path,
            {
                "local_id",
                "kind",
                "url",
                "title",
                "event_id",
                "artifact_id",
                "published_at",
                "retrieved_at",
                "supports",
                "excerpt",
            },
        )
        local_id = _local_id(citation["local_id"], f"{path}.local_id")
        if local_id in citations:
            raise ValueError(f"duplicate citation local_id {local_id!r}")
        kind = _enum(citation["kind"], f"{path}.kind", CITATION_KINDS)
        event_id = _text(citation["event_id"], f"{path}.event_id", nullable=True)
        artifact_id = _text(citation["artifact_id"], f"{path}.artifact_id", nullable=True)
        url = _text(citation["url"], f"{path}.url")
        assert url is not None
        if kind in {"event", "artifact"}:
            if event_id is None or event_id not in events:
                raise ValueError(f"{path}.event_id must name a workspace Event for {kind} citations")
            source_urls = set(events[event_id].get("source_urls", []))
            if url not in source_urls:
                raise ValueError(f"{path}.url is not frozen evidence for Event {event_id}")
        if kind == "artifact" and artifact_id is None:
            raise ValueError(f"{path}.artifact_id is required for artifact citations")
        retrieved_at = _optional_datetime(citation["retrieved_at"], f"{path}.retrieved_at")
        excerpt = _text(citation["excerpt"], f"{path}.excerpt", nullable=True)
        if kind == "web" and (retrieved_at is None or excerpt is None):
            raise ValueError(f"{path} web citations require retrieved_at and excerpt")
        published_at = _optional_date(
            citation["published_at"], f"{path}.published_at"
        )
        if kind == "event" and event_id is not None:
            source_dates = events[event_id].get("source_dates", {})
            expected_date = (
                str(source_dates.get(url) or "")
                if isinstance(source_dates, dict)
                else ""
            )
            if expected_date:
                if published_at is not None and published_at != expected_date:
                    raise ValueError(
                        f"{path}.published_at must match frozen source date "
                        f"{expected_date!r}"
                    )
                published_at = expected_date
        citations[local_id] = {
            "local_id": local_id,
            "kind": kind,
            "url": url,
            "title": _text(citation["title"], f"{path}.title"),
            "event_id": event_id,
            "artifact_id": artifact_id,
            "published_at": published_at,
            "retrieved_at": retrieved_at,
            "supports": _text(citation["supports"], f"{path}.supports"),
            "excerpt": excerpt,
        }

    normalized_insights: list[dict[str, Any]] = []
    insight_ids: set[str] = set()
    ranks: dict[str, set[int]] = {audience: set() for audience in AUDIENCES}
    used_citations: set[str] = set()
    for index, raw in enumerate(_list(value["insights"], "draft.insights")):
        path = f"draft.insights[{index}]"
        insight = _object(
            raw,
            path,
            {
                "local_id",
                "audience",
                "rank",
                "rank_rationale",
                "title",
                "what_changed",
                "interpretation",
                "next_step",
                "analysis",
                "event_links",
                "citation_ids",
            },
        )
        local_id = _local_id(insight["local_id"], f"{path}.local_id")
        if local_id in insight_ids:
            raise ValueError(f"duplicate insight local_id {local_id!r}")
        insight_ids.add(local_id)
        audience = _enum(insight["audience"], f"{path}.audience", AUDIENCES)
        rank = insight["rank"]
        if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1:
            raise ValueError(f"{path}.rank must be a positive integer")
        if rank in ranks[audience]:
            raise ValueError(f"duplicate {audience} rank {rank}")
        ranks[audience].add(rank)
        event_links = []
        for link_index, raw_link in enumerate(_list(insight["event_links"], f"{path}.event_links")):
            link_path = f"{path}.event_links[{link_index}]"
            link = _object(raw_link, link_path, {"event_id", "role", "reason"})
            event_id = _text(link["event_id"], f"{link_path}.event_id")
            assert event_id is not None
            pair = (event_id, audience)
            if pair not in expected_pairs:
                raise ValueError(f"{link_path} is not positively routed for {audience}")
            if pair in handled_pairs:
                raise ValueError(f"Event {event_id} is assigned more than once for {audience}")
            handled_pairs.add(pair)
            event_links.append(
                {
                    "event_id": event_id,
                    "role": _enum(link["role"], f"{link_path}.role", EVENT_ROLES),
                    "reason": _text(link["reason"], f"{link_path}.reason"),
                }
            )
        if not event_links:
            raise ValueError(f"{path}.event_links must contain at least one Event")
        citation_ids = [
            _local_id(item, f"{path}.citation_ids[{citation_index}]")
            for citation_index, item in enumerate(_list(insight["citation_ids"], f"{path}.citation_ids"))
        ]
        if not citation_ids:
            raise ValueError(f"{path}.citation_ids must contain at least one citation")
        if len(citation_ids) != len(set(citation_ids)):
            raise ValueError(f"{path}.citation_ids contains duplicates")
        unknown = sorted(set(citation_ids) - set(citations))
        if unknown:
            raise ValueError(f"{path}.citation_ids references unknown citations {unknown}")
        used_citations.update(citation_ids)
        analysis = (
            _validate_investment_analysis(insight["analysis"], f"{path}.analysis")
            if audience == "investment"
            else _validate_engineering_analysis(insight["analysis"], f"{path}.analysis")
        )
        normalized_insights.append(
            {
                "local_id": local_id,
                "audience": audience,
                "rank": rank,
                "rank_rationale": _text(
                    insight["rank_rationale"], f"{path}.rank_rationale"
                ),
                "title": _text(insight["title"], f"{path}.title"),
                "what_changed": _text(insight["what_changed"], f"{path}.what_changed"),
                "interpretation": _text(insight["interpretation"], f"{path}.interpretation"),
                "next_step": _text(insight["next_step"], f"{path}.next_step"),
                "analysis": analysis,
                "event_links": event_links,
                "citation_ids": citation_ids,
            }
        )

    for audience in AUDIENCES:
        expected_ranks = set(range(1, len(ranks[audience]) + 1))
        if ranks[audience] != expected_ranks:
            raise ValueError(f"{audience} ranks must be contiguous starting at 1")

    normalized_not_selected = []
    for index, raw in enumerate(_list(value["not_selected"], "draft.not_selected")):
        path = f"draft.not_selected[{index}]"
        item = _object(raw, path, {"event_id", "audience", "reason"})
        event_id = _text(item["event_id"], f"{path}.event_id")
        audience = _enum(item["audience"], f"{path}.audience", AUDIENCES)
        assert event_id is not None
        pair = (event_id, audience)
        if pair not in expected_pairs:
            raise ValueError(f"{path} is not a positively routed Event/audience pair")
        if pair in handled_pairs:
            raise ValueError(f"Event {event_id} is disposed more than once for {audience}")
        handled_pairs.add(pair)
        normalized_not_selected.append(
            {
                "event_id": event_id,
                "audience": audience,
                "reason": _text(item["reason"], f"{path}.reason"),
            }
        )

    missing_pairs = sorted(expected_pairs - handled_pairs)
    if missing_pairs:
        preview = [f"{event_id}/{audience}" for event_id, audience in missing_pairs[:8]]
        suffix = "..." if len(missing_pairs) > len(preview) else ""
        raise ValueError(f"draft does not dispose every routed candidate: {preview}{suffix}")
    if handled_pairs - expected_pairs:
        raise ValueError("draft contains non-cohort Event/audience dispositions")
    unused_citations = sorted(set(citations) - used_citations)
    if unused_citations:
        raise ValueError(f"draft contains unused citations {unused_citations}")

    event_rank = {event_id: int(event["feed_rank"]) for event_id, event in events.items()}
    normalized = {
        "schema_version": DRAFT_SCHEMA_VERSION,
        "workspace_run_id": str(value["workspace_run_id"]),
        "workspace_manifest_sha256": str(value["workspace_manifest_sha256"]),
        "agent": normalized_agent,
        "insights": sorted(normalized_insights, key=lambda item: (AUDIENCES.index(item["audience"]), item["rank"])),
        "not_selected": sorted(
            normalized_not_selected,
            key=lambda item: (AUDIENCES.index(item["audience"]), event_rank[item["event_id"]]),
        ),
        "citations": [citations[key] for key in sorted(citations)],
    }
    report = {
        "event_count": len(events),
        "candidate_pair_count": len(expected_pairs),
        "insight_count": len(normalized_insights),
        "insights_by_audience": {
            audience: sum(item["audience"] == audience for item in normalized_insights)
            for audience in AUDIENCES
        },
        "included_candidate_pairs": sum(len(item["event_links"]) for item in normalized_insights),
        "not_selected_candidate_pairs": len(normalized_not_selected),
        "citation_count": len(citations),
    }
    return deepcopy(normalized), report
