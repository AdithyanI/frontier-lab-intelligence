import json
from pathlib import Path

import pytest

from fli.insights import engineering_agent_runs


DAY = "2026-07-21"
DEVELOPMENT_ID = "d" * 64


def _trace(
    *,
    day: str = DAY,
    development_id: str = DEVELOPMENT_ID,
    daily_rank: int = 1,
) -> dict:
    return {
        "schema_version": "engineering-agent-trace-v1",
        "prompt_version": "engineering-agent-v2",
        "prompt_cache_key": "fli:engineering-agent:v2",
        "date": day,
        "daily_rank": daily_rank,
        "development_id": development_id,
        "model": "gpt-5.6-sol",
        "reasoning_effort": "high",
        "surface_count": 7,
        "surfaces_sha256": "a" * 64,
        "evidence_sha256": "b" * 64,
        "input_sha256": "c" * 64,
        "turns": [
            {
                "input_tokens": 10_000,
                "cached_tokens": 2_000,
                "output_tokens": 500,
                "reasoning_tokens": 100,
                "reported_cost_usd": 0.04,
            }
        ],
        "final_result": {
            "headline": "Agent telemetry creates a concrete operations decision",
            "what_changed": (
                "The release adds production telemetry for agent runs."
            ),
            "decision": "surface",
            "lands": [
                {
                    "surface_id": "OPS",
                    "why": "Operators can use it to debug failed agent runs.",
                }
            ],
            "no_match_reason": None,
        },
    }


def _import(
    tmp_path: Path,
    trace: dict,
    *,
    db_path: Path,
) -> None:
    path = tmp_path / (
        f"{trace['date']}-{trace['development_id'][:4]}-"
        f"{trace['daily_rank']}.json"
    )
    path.write_text(json.dumps(trace), encoding="utf-8")
    engineering_agent_runs.import_trace(path, db_path=db_path)


def test_import_publish_and_read_surface_linked_engineering_result(
    tmp_path: Path,
):
    db_path = tmp_path / "engineering-agent.db"
    _import(tmp_path, _trace(), db_path=db_path)

    engineering_agent_runs.publish_day(
        day=DAY,
        candidates=[
            {"development_id": DEVELOPMENT_ID, "daily_rank": 1}
        ],
        selection_limit=1,
        db_path=db_path,
    )
    payload = engineering_agent_runs.insights_payload(
        day=DAY,
        status="kept",
        db_path=db_path,
    )

    assert payload["content_kind"] == "engineering_agent"
    assert payload["run"]["development_count"] == 1
    assert payload["run"]["surface_landing_count"] == 1
    assert payload["run"]["cached_tokens"] == 2_000
    assert payload["items"][0]["lands"] == [
        {
            "surface_id": "OPS",
            "surface_name": "Operations",
            "why": "Operators can use it to debug failed agent runs.",
        }
    ]


def test_publication_hides_completed_rows_outside_selected_cohort(
    tmp_path: Path,
):
    db_path = tmp_path / "engineering-agent.db"
    _import(tmp_path, _trace(), db_path=db_path)
    _import(
        tmp_path,
        _trace(development_id="e" * 64, daily_rank=3),
        db_path=db_path,
    )

    engineering_agent_runs.publish_day(
        day=DAY,
        candidates=[
            {"development_id": DEVELOPMENT_ID, "daily_rank": 1}
        ],
        selection_limit=1,
        db_path=db_path,
    )
    payload = engineering_agent_runs.insights_payload(
        day=DAY,
        status="all",
        db_path=db_path,
    )

    assert [item["development_id"] for item in payload["items"]] == [
        DEVELOPMENT_ID
    ]


def test_publication_rejects_cross_day_development_reuse(tmp_path: Path):
    db_path = tmp_path / "engineering-agent.db"
    _import(tmp_path, _trace(), db_path=db_path)
    engineering_agent_runs.publish_day(
        day=DAY,
        candidates=[
            {"development_id": DEVELOPMENT_ID, "daily_rank": 1}
        ],
        selection_limit=1,
        db_path=db_path,
    )
    next_day = "2026-07-22"
    _import(
        tmp_path,
        _trace(day=next_day, daily_rank=2),
        db_path=db_path,
    )

    with pytest.raises(ValueError, match="more than one day"):
        engineering_agent_runs.publish_day(
            day=next_day,
            candidates=[
                {"development_id": DEVELOPMENT_ID, "daily_rank": 2}
            ],
            selection_limit=1,
            db_path=db_path,
        )

