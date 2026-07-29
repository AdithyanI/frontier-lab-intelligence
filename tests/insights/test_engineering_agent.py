import pytest

from fli.insights import engineering_agent


def _result(*, day: str, rank: int, development_id: str) -> dict:
    return {
        "day": day,
        "daily_rank": rank,
        "development_id": development_id,
        "decision": "suppress",
        "headline": "No surface decision",
        "lands": [],
        "no_match_reason": "No current implementation consequence.",
        "surface_count": 7,
        "input_tokens": 10,
        "cached_tokens": 0,
        "output_tokens": 2,
        "reasoning_tokens": 1,
        "request_retries": 0,
        "reported_cost_usd": 0.01,
        "run_id": f"run-{day}-{rank}",
        "trace_path": f"/tmp/{day}-{rank}.json",
    }


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


def test_run_days_dry_run_replaces_a_cross_day_duplicate(monkeypatch):
    duplicate = "a" * 64
    replacement = "b" * 64

    def candidates(*, day, **_kwargs):
        if day == "2026-07-20":
            return [{"development_id": duplicate, "daily_rank": 1}]
        return [
            {"development_id": duplicate, "daily_rank": 2},
            {"development_id": replacement, "daily_rank": 4},
        ]

    monkeypatch.setattr(engineering_agent, "_engineering_candidates", candidates)
    monkeypatch.setattr(
        engineering_agent.engineering_agent_runs,
        "published_development_days",
        lambda **_kwargs: {},
    )

    payload = engineering_agent.run_days(
        through="2026-07-21",
        days=2,
        top_ranked=1,
        dry_run=True,
    )

    assert payload["targets"] == [
        {
            "day": "2026-07-20",
            "daily_rank": 1,
            "development_id": duplicate,
        },
        {
            "day": "2026-07-21",
            "daily_rank": 4,
            "development_id": replacement,
        },
    ]


def test_run_days_publishes_the_complete_range_once(monkeypatch, tmp_path):
    candidates = {
        "2026-07-20": [{"development_id": "a" * 64, "daily_rank": 1}],
        "2026-07-21": [{"development_id": "b" * 64, "daily_rank": 2}],
    }
    monkeypatch.setattr(
        engineering_agent,
        "_engineering_candidates",
        lambda *, day, **_kwargs: candidates[day],
    )
    monkeypatch.setattr(
        engineering_agent.engineering_agent_runs,
        "published_development_days",
        lambda **_kwargs: {},
    )
    monkeypatch.setattr(
        engineering_agent,
        "run_one",
        lambda **kwargs: _result(
            day=kwargs["day"],
            rank=kwargs["rank"],
            development_id=kwargs["development_id"],
        ),
    )
    publications = []

    def publish_days(**kwargs):
        publications.append(kwargs["publications"])
        return kwargs["publications"]

    monkeypatch.setattr(
        engineering_agent.engineering_agent_runs,
        "publish_days",
        publish_days,
    )

    result = engineering_agent.run_days(
        through="2026-07-21",
        days=2,
        top_ranked=1,
        workers=1,
        trace_root=tmp_path / "traces",
        db_path=tmp_path / "engineering-agent.db",
    )

    assert result["complete"] is True
    assert len(publications) == 1
    assert [item["day"] for item in publications[0]] == [
        "2026-07-20",
        "2026-07-21",
    ]


def test_run_days_rank_does_not_replace_a_complete_publication(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        engineering_agent,
        "_engineering_candidates",
        lambda **_kwargs: [
            {"development_id": "a" * 64, "daily_rank": 2}
        ],
    )
    monkeypatch.setattr(
        engineering_agent.engineering_agent_runs,
        "published_development_days",
        lambda **_kwargs: {},
    )
    monkeypatch.setattr(
        engineering_agent,
        "run_one",
        lambda **kwargs: _result(
            day=kwargs["day"],
            rank=kwargs["rank"],
            development_id=kwargs["development_id"],
        ),
    )
    monkeypatch.setattr(
        engineering_agent.engineering_agent_runs,
        "publish_days",
        lambda **_kwargs: pytest.fail("a focused rank run must not publish"),
    )

    result = engineering_agent.run_days(
        through="2026-07-21",
        days=1,
        rank=2,
        workers=1,
        trace_root=tmp_path / "traces",
        db_path=tmp_path / "engineering-agent.db",
    )

    assert result["complete"] is True
    assert result["publications"] == []
