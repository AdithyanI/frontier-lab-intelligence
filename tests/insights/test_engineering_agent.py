import pytest

from fli.insights import engineering_agent


def test_validate_final_enforces_surface_decision_contract():
    result = {
        "headline": "Agent telemetry creates a concrete operations decision",
        "what_changed": "The release adds production telemetry for agent runs.",
        "decision": "surface",
        "lands": [
            {
                "surface_id": "OPS",
                "why": "Operators can use the telemetry to debug failed runs.",
            }
        ],
        "no_match_reason": None,
    }

    assert engineering_agent._validate_final(
        result,
        surface_ids={"OPS"},
    ) == result

    result["lands"][0]["surface_id"] = "UNKNOWN"
    with pytest.raises(ValueError, match="unknown surface"):
        engineering_agent._validate_final(result, surface_ids={"OPS"})


def test_run_days_dry_run_selects_only_engineering_routed_candidates(monkeypatch):
    monkeypatch.setattr(
        engineering_agent,
        "_engineering_candidates",
        lambda **_kwargs: [
            {"development_id": "a" * 64, "daily_rank": 2},
            {"development_id": "b" * 64, "daily_rank": 5},
        ],
    )

    payload = engineering_agent.run_days(
        through="2026-07-21",
        days=1,
        top_ranked=1,
        dry_run=True,
    )

    assert payload["complete"] is True
    assert payload["selection"] == {
        "audience": "ai_engineering",
        "routing_state": "evaluated",
        "relevant": True,
        "order": "daily_rank",
    }
    assert payload["targets"] == [
        {
            "day": "2026-07-21",
            "daily_rank": 2,
            "development_id": "a" * 64,
        }
    ]

