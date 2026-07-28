from pathlib import Path
from threading import Lock

from fli.insights import investment_agent


def _result(*, day: str, rank: int) -> dict:
    decision = "surface" if rank % 2 else "suppress"
    assessments = (
        [
            {
                "ticker": "PANW",
                "bottom_line": "A bounded implication.",
                "mechanism": "A direct mechanism.",
                "affected_driver": "paid adoption",
                "direction": "positive",
                "main_uncertainty": "Demand is not measured.",
                "next_check": "Paid production customers.",
            }
        ]
        if decision == "surface"
        else []
    )
    return {
        "trace_path": f"/tmp/{day}-{rank}.json",
        "development_id": f"{rank:064d}",
        "daily_rank": rank,
        "memo_tickers": ["PANW"] if assessments else [],
        "turns": [
            {
                "turn": 1,
                "response_id": f"resp-{day}-{rank}",
                "duration_ms": 10,
                "input_tokens": 1_000,
                "cached_tokens": 900,
                "output_tokens": 100,
                "reasoning_tokens": 50,
                "reported_cost_usd": 0.01,
            }
        ],
        "final_result": {
            "investment_headline": f"Investment implication for rank {rank}",
            "development_summary": "What changed.",
            "decision": decision,
            "portfolio_readthrough": "A bounded read-through.",
            "company_assessments": assessments,
            "rejected_after_memo": [],
            "no_match_reason": None if assessments else "No company connection.",
        },
        "imported": {
            "day": day,
            "run_id": f"run-{day}-{rank}",
        },
    }


def test_run_range_warms_one_target_then_fans_out(monkeypatch, tmp_path: Path):
    calls: list[tuple[str, int]] = []
    lock = Lock()

    def fake_run_one(**kwargs):
        with lock:
            calls.append((kwargs["day"], kwargs["rank"]))
        return _result(day=kwargs["day"], rank=kwargs["rank"])

    monkeypatch.setattr(investment_agent, "run_one", fake_run_one)

    result = investment_agent.run_range(
        through="2026-07-20",
        days=2,
        top_ranked=3,
        workers=5,
        trace_root=tmp_path / "traces",
        db_path=tmp_path / "investment-agent.db",
    )

    assert calls[0] == ("2026-07-19", 1)
    assert set(calls) == {
        ("2026-07-19", 1),
        ("2026-07-19", 2),
        ("2026-07-19", 3),
        ("2026-07-20", 1),
        ("2026-07-20", 2),
        ("2026-07-20", 3),
    }
    assert result["complete"] is True
    assert result["counts"] == {
        "requested": 6,
        "complete": 6,
        "failed": 0,
        "surfaced": 4,
        "suppressed": 2,
        "memo_calls": 4,
        "company_assessments": 4,
        "rejected_after_memo": 0,
    }
    assert result["telemetry"]["cached_tokens"] == 5_400
    assert result["telemetry"]["reported_cost_usd"] == 0.06


def test_run_range_preserves_individual_failures(monkeypatch, tmp_path: Path):
    def fake_run_one(**kwargs):
        if kwargs["rank"] == 2:
            raise RuntimeError("provider failed")
        return _result(day=kwargs["day"], rank=kwargs["rank"])

    monkeypatch.setattr(investment_agent, "run_one", fake_run_one)

    result = investment_agent.run_range(
        through="2026-07-20",
        top_ranked=3,
        workers=2,
        trace_root=tmp_path / "traces",
        db_path=tmp_path / "investment-agent.db",
    )

    assert result["complete"] is False
    assert result["counts"]["complete"] == 2
    assert result["counts"]["failed"] == 1
    assert result["failures"] == [
        {
            "day": "2026-07-20",
            "daily_rank": 2,
            "error_type": "RuntimeError",
            "message": "provider failed",
        }
    ]


def test_trace_path_is_durable_unique_and_versioned(tmp_path: Path):
    first = investment_agent._trace_path(
        trace_root=tmp_path,
        day="2026-07-20",
        rank=1,
        model="gpt-5.6-sol",
        effort="xhigh",
    )
    second = investment_agent._trace_path(
        trace_root=tmp_path,
        day="2026-07-20",
        rank=1,
        model="gpt-5.6-sol",
        effort="xhigh",
    )

    assert first.parent == tmp_path / "2026-07-20"
    assert first != second
    assert "rank-001-5-6-sol-xhigh-investment-agent-v8" in first.name
