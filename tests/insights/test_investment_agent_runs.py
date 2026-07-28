import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from fli.insights import investment_agent_runs
from fli.web import app as web_app


DAY = "2026-07-21"
DEVELOPMENT_ID = "d" * 64


def _trace() -> dict:
    result = {
        "investment_headline": "Agent risk strengthens demand for independent controls",
        "development_summary": "The Development establishes a new control risk.",
        "decision": "surface",
        "portfolio_readthrough": "Security demand may move before revenue does.",
        "prior_assumption": "Independent controls matter more after this incident.",
        "company_assessments": [
            {
                "mechanism_title": "Independent agent controls",
                "mechanism": "Agent activity needs an independent control layer.",
                "splits": False,
                "exposures": [
                    {
                        "ticker": "PANW",
                        "affected_driver": "AI security product attachment",
                        "direction": "positive",
                        "materiality": "unknown",
                        "size_basis": None,
                        "note": "The incident could increase demand for AI controls.",
                    }
                ],
                "main_uncertainty": "No disclosed revenue contribution.",
                "next_check": "Track PANW attach and customer references.",
            }
        ],
        "rejected_after_memo": [
            {"ticker": "DDOG", "reason": "The link remained generic after review."}
        ],
        "no_match_reason": None,
    }
    return {
        "schema_version": "investment-agent-trace-v1",
        "prompt_version": "investment-agent-v9",
        "prompt_cache_key": "fli:investment-agent:v9",
        "date": DAY,
        "daily_rank": 1,
        "development_id": DEVELOPMENT_ID,
        "model": "gpt-5.6-terra",
        "reasoning_effort": "high",
        "company_count": 37,
        "company_cards_sha256": "a" * 64,
        "evidence_sha256": "b" * 64,
        "input_sha256": "c" * 64,
        "memo_calls": [
            {"turn": 1, "call_id": "panw", "arguments": {"ticker": "PANW"}},
            {"turn": 1, "call_id": "ddog", "arguments": {"ticker": "DDOG"}},
        ],
        "memo_packets": {},
        "citation_repairs": [],
        "turns": [
            {
                "input_tokens": 10_000,
                "cached_tokens": 0,
                "output_tokens": 500,
                "reasoning_tokens": 100,
                "reported_cost_usd": 0.04,
            },
            {
                "input_tokens": 20_000,
                "cached_tokens": 8_000,
                "output_tokens": 1_500,
                "reasoning_tokens": 300,
                "reported_cost_usd": 0.08,
            },
        ],
        "final_result": result,
    }


def test_import_trace_preserves_company_assessments_rejections_and_telemetry(
    tmp_path: Path,
):
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(_trace()), encoding="utf-8")
    db_path = tmp_path / "investment-agent.db"

    imported = investment_agent_runs.import_trace(trace_path, db_path=db_path)
    investment_agent_runs.publish_day(
        day=DAY,
        candidates=[
            {"development_id": DEVELOPMENT_ID, "daily_rank": 1}
        ],
        selection_limit=1,
        db_path=db_path,
    )
    dates = investment_agent_runs.dates_payload(db_path=db_path)
    payload = investment_agent_runs.insights_payload(
        day=DAY,
        status="kept",
        db_path=db_path,
    )

    assert imported["company_assessments"] == 1
    assert imported["rejected_after_memo"] == 1
    assert dates["dates"] == [
        {
            "day": DAY,
            "content_kind": "investment_agent",
            "item_count": 1,
            "candidate_count": 1,
            "included_candidate_count": 1,
            "not_selected_candidate_count": 0,
        }
    ]
    assert payload["content_kind"] == "investment_agent"
    assert payload["run"]["cached_tokens"] == 8_000
    assert payload["run"]["reported_cost_usd"] == 0.12
    assert payload["run"]["audience"] == "investment"
    assert payload["run"]["selection_kind"] == "top_investment_routed"
    assert payload["run"]["selection_limit"] == 1
    assert payload["items"][0]["investment_headline"] == (
        "Agent risk strengthens demand for independent controls"
    )
    assessment = payload["items"][0]["company_assessments"][0]
    assert assessment["mechanism_title"] == "Independent agent controls"
    assert assessment["exposures"][0]["ticker"] == "PANW"
    assert assessment["exposures"][0]["direction"] == "positive"
    assert payload["items"][0]["prior_assumption"] == (
        "Independent controls matter more after this incident."
    )
    assert payload["items"][0]["rejected_after_memo"] == [
        {"ticker": "DDOG", "reason": "The link remained generic after review."}
    ]


def test_publication_hides_completed_rows_outside_the_selected_cohort(
    tmp_path: Path,
):
    db_path = tmp_path / "investment-agent.db"
    selected = _trace()
    excluded = _trace()
    excluded["development_id"] = "e" * 64
    excluded["daily_rank"] = 3
    excluded["final_result"]["investment_headline"] = (
        "Excluded engineering-only Development must stay hidden"
    )
    for name, trace in [("selected", selected), ("excluded", excluded)]:
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(trace), encoding="utf-8")
        investment_agent_runs.import_trace(path, db_path=db_path)

    investment_agent_runs.publish_day(
        day=DAY,
        candidates=[
            {"development_id": DEVELOPMENT_ID, "daily_rank": 1}
        ],
        selection_limit=1,
        db_path=db_path,
    )
    payload = investment_agent_runs.insights_payload(
        day=DAY,
        status="all",
        db_path=db_path,
    )

    assert payload["run"]["development_count"] == 1
    assert [item["development_id"] for item in payload["items"]] == [
        DEVELOPMENT_ID
    ]


def test_import_trace_requires_every_opened_memo_to_be_resolved(tmp_path: Path):
    trace = _trace()
    trace["final_result"]["rejected_after_memo"] = []
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(trace), encoding="utf-8")

    with pytest.raises(ValueError, match="every opened memo"):
        investment_agent_runs.import_trace(
            trace_path,
            db_path=tmp_path / "investment-agent.db",
        )


def test_import_trace_requires_a_concise_investment_headline(tmp_path: Path):
    trace = _trace()
    trace["final_result"]["investment_headline"] = ""
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(trace), encoding="utf-8")

    with pytest.raises(ValueError, match="invalid headline"):
        investment_agent_runs.import_trace(
            trace_path,
            db_path=tmp_path / "investment-agent.db",
        )


def test_import_trace_rejects_the_superseded_dense_company_schema(tmp_path: Path):
    trace = _trace()
    trace["final_result"]["company_assessments"][0]["confidence"] = "medium"
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(trace), encoding="utf-8")

    with pytest.raises(ValueError, match="minimal schema"):
        investment_agent_runs.import_trace(
            trace_path,
            db_path=tmp_path / "investment-agent.db",
        )


def test_investment_api_prefers_company_aware_successor(monkeypatch):
    monkeypatch.setattr(
        web_app.investment_agent_store,
        "dates_payload",
        lambda: {
            "available": True,
            "latest_date": DAY,
            "dates": [
                {
                    "day": DAY,
                    "content_kind": "investment_agent",
                    "item_count": 1,
                    "candidate_count": 1,
                    "included_candidate_count": 1,
                    "not_selected_candidate_count": 0,
                }
            ],
        },
    )
    monkeypatch.setattr(
        web_app.investment_agent_store,
        "insights_payload",
        lambda **_kwargs: {
            "schema_version": investment_agent_runs.READ_SCHEMA_VERSION,
            "available": True,
            "reason": None,
            "requested_date": DAY,
            "date": DAY,
            "audience": "investment",
            "status": "kept",
            "content_kind": "investment_agent",
            "run": {},
            "items": [
                {
                    "day": DAY,
                    "development_id": DEVELOPMENT_ID,
                }
            ],
        },
    )
    monkeypatch.setattr(
        web_app,
        "_investment_agent_provenance",
        lambda **_kwargs: {
            "primary_event_id": "event-id",
            "source_event_count": 1,
            "original_post": {
                "url": "https://x.com/example/status/1",
                "author": "Example",
            },
            "artifacts": [
                {
                    "artifact_id": "artifact-id",
                    "title": "Source document",
                    "url": "https://example.com/source",
                }
            ],
        },
    )
    client = TestClient(web_app.app)

    dates = client.get("/api/insights/dates?audience=investment").json()
    payload = client.get(
        f"/api/insights?audience=investment&date={DAY}&status=kept"
    ).json()

    assert dates["dates"][-1]["content_kind"] == "investment_agent"
    assert payload["content_kind"] == "investment_agent"
    assert payload["schema_version"] == "investment-agent-read-v6"
    assert payload["items"][0]["provenance"] == {
        "primary_event_id": "event-id",
        "source_event_count": 1,
        "original_post": {
            "url": "https://x.com/example/status/1",
            "author": "Example",
        },
        "artifacts": [
            {
                "artifact_id": "artifact-id",
                "title": "Source document",
                "url": "https://example.com/source",
            }
        ],
    }


def test_investment_provenance_keeps_feed_post_and_artifacts_distinct(monkeypatch):
    monkeypatch.setattr(
        web_app.development_store,
        "developments_payload",
        lambda **_kwargs: {
            "items": [
                {
                    "primary_event_id": "event-id",
                    "source_event_count": 2,
                    "root": {
                        "url": "https://x.com/example/status/1",
                        "author": {
                            "entity_name": "Example Author",
                            "handle": "example",
                        },
                    },
                    "development_artifacts": [
                        {
                            "artifact_id": "artifact-id",
                            "title": "Research paper",
                            "canonical_url": "https://example.com/paper",
                        },
                        {
                            "artifact_id": "duplicate-root",
                            "title": "Original post",
                            "canonical_url": "https://x.com/example/status/1",
                        },
                    ],
                }
            ]
        },
    )

    provenance = web_app._investment_agent_provenance(
        day=DAY,
        development_id=DEVELOPMENT_ID,
    )

    assert provenance == {
        "primary_event_id": "event-id",
        "source_event_count": 2,
        "original_post": {
            "url": "https://x.com/example/status/1",
            "author": "Example Author",
        },
        "artifacts": [
            {
                "artifact_id": "artifact-id",
                "title": "Research paper",
                "url": "https://example.com/paper",
            }
        ],
    }
