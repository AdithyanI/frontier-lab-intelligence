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
        "headline": "Agent risk strengthens demand for independent controls",
        "what_changed": "The Development establishes a new control risk.",
        "decision": "surface",
        "connections": [
            {
                "mechanism": "Agent activity needs an independent control layer.",
                "companies": [
                    {
                        "ticker": "PANW",
                        "bet_id": "PANW-B1",
                        "threshold_met": False,
                        "impact": "Placeholder impact sentence for the exposure.",
                    }
                ],
            }
        ],
        "no_match_reason": None,
    }
    return {
        "schema_version": "investment-agent-trace-v1",
        "prompt_version": "investment-agent-v14",
        "prompt_cache_key": "fli:investment-agent:v14",
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


def test_import_trace_preserves_company_connections_and_telemetry(
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

    assert imported["company_connections"] == 1
    assert imported["memos_rejected"] == 1
    assert dates["dates"] == [
        {
            "day": DAY,
            "content_kind": "investment_agent",
            "item_count": 1,
            "development_count": 1,
            "surfaced_development_count": 1,
            "suppressed_development_count": 0,
        }
    ]
    assert payload["content_kind"] == "investment_agent"
    assert payload["run"]["cached_tokens"] == 8_000
    assert payload["run"]["reported_cost_usd"] == 0.12
    assert payload["run"]["audience"] == "investment"
    assert payload["run"]["selection_kind"] == "top_investment_routed"
    assert payload["run"]["selection_limit"] == 1
    assert payload["items"][0]["headline"] == (
        "Agent risk strengthens demand for independent controls"
    )
    connection = payload["items"][0]["connections"][0]
    assert connection["mechanism"] == (
        "Agent activity needs an independent control layer."
    )
    assert connection["companies"] == [
        {
            "ticker": "PANW",
            "bet_id": "PANW-B1",
            "threshold_met": False,
            "impact": "Placeholder impact sentence for the exposure.",
        }
    ]
    assert payload["run"]["company_connection_count"] == 1
    assert payload["run"]["memo_rejected_count"] == 1


def test_publication_hides_completed_rows_outside_the_selected_cohort(
    tmp_path: Path,
):
    db_path = tmp_path / "investment-agent.db"
    selected = _trace()
    excluded = _trace()
    excluded["development_id"] = "e" * 64
    excluded["daily_rank"] = 3
    excluded["final_result"]["headline"] = (
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


def test_publication_rejects_cross_day_development_reuse(tmp_path: Path):
    db_path = tmp_path / "investment-agent.db"
    first = _trace()
    first_path = tmp_path / "first.json"
    first_path.write_text(json.dumps(first), encoding="utf-8")
    investment_agent_runs.import_trace(first_path, db_path=db_path)
    investment_agent_runs.publish_day(
        day=DAY,
        candidates=[
            {"development_id": DEVELOPMENT_ID, "daily_rank": 1}
        ],
        selection_limit=1,
        db_path=db_path,
    )

    next_day = "2026-07-22"
    second = _trace()
    second["date"] = next_day
    second["daily_rank"] = 2
    second_path = tmp_path / "second.json"
    second_path.write_text(json.dumps(second), encoding="utf-8")
    investment_agent_runs.import_trace(second_path, db_path=db_path)

    with pytest.raises(ValueError, match="more than one day"):
        investment_agent_runs.publish_day(
            day=next_day,
            candidates=[
                {"development_id": DEVELOPMENT_ID, "daily_rank": 2}
            ],
            selection_limit=1,
            db_path=db_path,
        )

    conn = investment_agent_runs.connect(db_path)
    with conn:
        conn.execute(
            """INSERT INTO investment_agent_day_publication (
                   day, audience, selection_kind, selection_limit,
                   selection_sha256, candidate_count, published_at
               ) VALUES (?, 'investment', 'top_investment_routed', 1, ?, 1, ?)""",
            (next_day, "legacy-selection", "2026-07-22T12:00:00+00:00"),
        )
        conn.execute(
            """INSERT INTO investment_agent_day_publication_item (
                   day, development_id, daily_rank
               ) VALUES (?, ?, 2)""",
            (next_day, DEVELOPMENT_ID),
        )
    conn.close()

    assert [
        item["day"]
        for item in investment_agent_runs.dates_payload(db_path=db_path)["dates"]
    ] == [DAY]


def test_import_trace_requires_every_retained_company_to_have_an_opened_memo(
    tmp_path: Path,
):
    trace = _trace()
    trace["memo_calls"] = [
        {"turn": 1, "call_id": "ddog", "arguments": {"ticker": "DDOG"}}
    ]
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(trace), encoding="utf-8")

    with pytest.raises(ValueError, match="every retained company"):
        investment_agent_runs.import_trace(
            trace_path,
            db_path=tmp_path / "investment-agent.db",
        )


def test_import_trace_requires_a_concise_headline(tmp_path: Path):
    trace = _trace()
    trace["final_result"]["headline"] = ""
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(trace), encoding="utf-8")

    with pytest.raises(ValueError, match="invalid headline"):
        investment_agent_runs.import_trace(
            trace_path,
            db_path=tmp_path / "investment-agent.db",
        )


def test_import_trace_rejects_the_superseded_dense_company_schema(tmp_path: Path):
    trace = _trace()
    trace["final_result"]["connections"][0]["companies"][0]["confidence"] = "medium"
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(trace), encoding="utf-8")

    with pytest.raises(ValueError, match="v14 schema"):
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
                    "development_count": 1,
                    "surfaced_development_count": 1,
                    "suppressed_development_count": 0,
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
    assert payload["schema_version"] == "investment-agent-read-v8"
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
