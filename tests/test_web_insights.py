import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from fli import audience_routing, insight_generation, insight_runs
from fli.web import insights as insight_store
from fli.web.app import app


client = TestClient(app)


def _packet() -> audience_routing.RoutingPacket:
    return audience_routing.RoutingPacket(
        event_id="event-insight-1",
        day="2026-07-13",
        sources=(
            audience_routing.EvidenceSource(
                source_type="x_post",
                source_id="post-1",
                url="https://x.com/alice/status/post-1",
                text="We measured a bounded harness-improvement loop.",
                author="@alice",
                relation="root",
            ),
        ),
    )


def _evaluation(candidate, result):
    prompt = insight_generation.contract(candidate.audience)
    return {
        "audience": candidate.audience.value,
        "event_id": candidate.packet.event_id,
        "day": candidate.packet.day,
        "feed_rank": candidate.feed_rank,
        "candidate_id": candidate.candidate_id,
        "result": result,
        "published": None,
        "raw_output_text": json.dumps(result),
        "model": "gpt-5.6-terra",
        "reasoning_effort": "high",
        "prompt_version": prompt.version,
        "prompt_sha256": prompt.sha256,
        "schema_version": insight_generation.SCHEMA_VERSION,
        "input_sha256": candidate.input_sha256,
        "response_id": f"response-{candidate.audience.value}",
        "response_model": "gpt-5.6-terra",
        "input_tokens": 2_400,
        "cached_tokens": 0,
        "cache_write_tokens": 0,
        "output_tokens": 120,
        "reported_cost_usd": 0.0125,
        "request_tags": [],
    }


def _insight_db(tmp_path):
    path = tmp_path / "insights.db"
    conn = insight_runs.connect(path)
    packet = _packet()
    candidates = {
        audience: insight_generation.InsightCandidate.create(
            audience=audience, packet=packet, feed_rank=45
        )
        for audience in ("ai_engineering", "investment")
    }
    insight_runs.prepare_run(
        conn,
        run_id="test-terra-run",
        event_id=packet.event_id,
        day=packet.day,
        feed_rank=45,
        source_routing_run_id="routing-run",
        source_routing_db="routing.db",
        model="gpt-5.6-terra",
        reasoning_effort="high",
        items=(
            {
                "audience": audience,
                "candidate_id": candidate.candidate_id,
                "request": insight_generation.build_request(
                    candidate,
                    model="gpt-5.6-terra",
                    effort="high",
                    run="test-terra-run",
                ),
            }
            for audience, candidate in candidates.items()
        ),
    )
    insight_runs.complete_item(
        conn,
        run_id="test-terra-run",
        evaluation=_evaluation(
            candidates["ai_engineering"],
            {
                "decision": "surface",
                "suppression_reason": None,
                "title": "Test harness changes against held-out failures",
                "summary": "A bounded harness-improvement loop improved held-out tasks.",
                "implication": "The method is concrete and testable on an internal workflow.",
                "next_step": "Run it on one frozen held-in and held-out split.",
            },
        ),
    )
    insight_runs.complete_item(
        conn,
        run_id="test-terra-run",
        evaluation=_evaluation(
            candidates["investment"],
            {
                "decision": "suppress",
                "suppression_reason": "No company adoption or public-equity transmission path is evidenced.",
                "title": None,
                "summary": None,
                "implication": None,
                "next_step": None,
            },
        ),
    )
    conn.close()
    return path


def test_dates_include_evaluated_days_and_count_kept_items(tmp_path):
    db = _insight_db(tmp_path)

    engineering = insight_store.insight_dates_payload(
        audience="ai_engineering", db_path=db
    )
    investment = insight_store.insight_dates_payload(
        audience="investment", db_path=db
    )

    assert engineering["latest_date"] == "2026-07-13"
    assert engineering["dates"] == [
        {
            "day": "2026-07-13",
            "item_count": 1,
            "suppressed_count": 0,
            "evaluated_count": 1,
        }
    ]
    assert investment["dates"][0]["item_count"] == 0
    assert investment["dates"][0]["suppressed_count"] == 1


def test_status_views_expose_kept_and_suppressed_rationales(tmp_path):
    db = _insight_db(tmp_path)

    kept = insight_store.insights_payload(
        audience="ai_engineering", day="2026-07-13", status="kept", db_path=db
    )
    suppressed = insight_store.insights_payload(
        audience="investment", day="2026-07-13", status="suppressed", db_path=db
    )
    empty_kept = insight_store.insights_payload(
        audience="investment", day="2026-07-13", status="kept", db_path=db
    )

    assert kept["items"][0]["decision"] == "surface"
    assert kept["items"][0]["title"] == "Test harness changes against held-out failures"
    assert kept["items"][0]["root_source_url"] is None
    assert kept["items"][0]["artifacts"] == []
    assert kept["items"][0]["decision_reason"].startswith("The method is concrete")
    assert suppressed["items"][0]["decision"] == "suppress"
    assert suppressed["items"][0]["decision_reason"].startswith("No company adoption")
    assert suppressed["run"]["counts"] == {"all": 1, "kept": 0, "suppressed": 1}
    assert empty_kept["available"] is True
    assert empty_kept["items"] == []
    assert "final editorial gate" in empty_kept["reason"]


def test_items_link_the_frozen_root_source_and_primary_artifacts(tmp_path):
    db = _insight_db(tmp_path)
    routing_db = tmp_path / "routing.db"
    routing = sqlite3.connect(routing_db)
    routing.execute(
        "CREATE TABLE routing_item (event_id TEXT PRIMARY KEY, packet_json TEXT NOT NULL)"
    )
    routing.execute(
        "INSERT INTO routing_item VALUES (?, ?)",
        (
            "event-insight-1",
            json.dumps(
                {
                    "sources": [
                        {
                            "source_type": "x_post",
                            "relation": "root",
                            "url": "https://x.com/alice/status/post-1",
                        },
                        {
                            "source_type": "artifact",
                            "relation": "linked_artifact",
                            "title": "Recovery evaluation",
                            "url": "https://example.com/recovery-evaluation",
                        },
                    ]
                }
            ),
        ),
    )
    routing.commit()
    routing.close()
    conn = insight_runs.connect(db)
    conn.execute(
        "UPDATE insight_run SET source_routing_db = ?",
        (str(routing_db),),
    )
    conn.commit()
    conn.close()
    insight_store._routing_packets.cache_clear()

    kept = insight_store.insights_payload(
        audience="ai_engineering", day="2026-07-13", status="kept", db_path=db
    )

    assert kept["items"][0]["root_source_url"] == "https://x.com/alice/status/post-1"
    assert kept["items"][0]["artifacts"] == [
        {
            "title": "Recovery evaluation",
            "url": "https://example.com/recovery-evaluation",
        }
    ]


def test_current_ui_routes_read_the_durable_store(tmp_path, monkeypatch):
    db = _insight_db(tmp_path)
    monkeypatch.setattr(insight_runs, "DEFAULT_DB", db)

    dates = client.get(
        "/api/insights/extracted/dates?audience=ai_engineering"
    ).json()
    items = client.get(
        "/api/insights/extracted?audience=investment&date=2026-07-13&status=suppressed"
    ).json()

    assert dates["available"] is True
    assert items["available"] is True
    assert items["status"] == "suppressed"
    assert items["items"][0]["decision"] == "suppress"


def test_invalid_audiences_and_statuses_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="unsupported Insight audience"):
        insight_store.insight_dates_payload(audience="general", db_path=tmp_path)
    with pytest.raises(ValueError, match="unsupported Insight status"):
        insight_store.insights_payload(status="maybe", db_path=tmp_path)

    response = client.get("/api/insights/dates?audience=general")
    assert response.status_code == 422
    response = client.get("/api/insights?status=maybe")
    assert response.status_code == 422
