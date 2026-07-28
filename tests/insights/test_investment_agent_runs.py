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
        "development_summary": "The Development establishes a new control risk.",
        "decision": "surface",
        "portfolio_readthrough": "Security demand may move before revenue does.",
        "company_assessments": [
            {
                "ticker": "PANW",
                "relevance": "direct",
                "mechanism": "Agent activity needs an independent control layer.",
                "affected_operating_driver": "AI security attach",
                "economic_direction": "positive",
                "time_horizon": "medium_term",
                "thesis_effect": "supports",
                "analyst_takeaway": "Watch adoption rather than treating the event as revenue.",
                "confidence": "medium",
                "evidence": [
                    {
                        "claim": "The product mediates agent traffic.",
                        "source_urls": ["https://example.com/panw"],
                    }
                ],
                "uncertainties": ["No disclosed revenue contribution."],
                "next_checks": ["Track attach and customer references."],
            }
        ],
        "rejected_after_memo": [
            {"ticker": "DDOG", "reason": "The link remained generic after review."}
        ],
        "no_match_reason": None,
    }
    return {
        "schema_version": "investment-insight-loop-pilot-trace-v1",
        "prompt_version": "investment-insight-loop-pilot-v1",
        "prompt_cache_key": "fli:investment-insight-loop:pilot-v1",
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
    assert payload["items"][0]["company_assessments"][0]["ticker"] == "PANW"
    assert payload["items"][0]["rejected_after_memo"] == [
        {"ticker": "DDOG", "reason": "The link remained generic after review."}
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
        "_investment_agent_source",
        lambda **_kwargs: {"title": "Primary source", "url": "https://example.com"},
    )
    client = TestClient(web_app.app)

    dates = client.get("/api/insights/dates?audience=investment").json()
    payload = client.get(
        f"/api/insights?audience=investment&date={DAY}&status=kept"
    ).json()

    assert dates["dates"][-1]["content_kind"] == "investment_agent"
    assert payload["content_kind"] == "investment_agent"
    assert payload["items"][0]["source"]["title"] == "Primary source"
