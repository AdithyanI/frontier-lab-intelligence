import json
from pathlib import Path
from threading import Lock
from types import SimpleNamespace

import httpx
import openai
import pytest

from fli.insights import investment_agent


def _result(*, day: str, rank: int) -> dict:
    decision = "surface" if rank % 2 else "suppress"
    assessments = (
        [
            {
                "mechanism_title": "Independent agent controls",
                "mechanism": "A direct mechanism.",
                "splits": False,
                "exposures": [
                    {
                        "ticker": "PANW",
                        "affected_driver": "paid adoption",
                        "direction": "positive",
                        "materiality": "unknown",
                        "size_basis": None,
                        "impact": "Placeholder impact sentence for the exposure.",
                    }
                ],
                "main_uncertainty": "Demand is not measured.",
                "next_check": "PANW paid production customers.",
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
            "prior_assumption": (
                "Independent controls matter more after this Development."
                if assessments
                else None
            ),
            "company_assessments": assessments,
            "rejected_after_memo": [],
            "no_match_reason": None if assessments else "No company connection.",
        },
        "imported": {
            "day": day,
            "run_id": f"run-{day}-{rank}",
        },
    }


def _status_error(status_code: int, *, retry_after: str | None = None):
    request = httpx.Request("POST", "http://litellm.test/v1/responses")
    headers = {"retry-after": retry_after} if retry_after is not None else {}
    response = httpx.Response(
        status_code,
        request=request,
        headers=headers,
        json={"error": {"message": "provider failed"}},
    )
    return openai.APIStatusError(
        "provider failed",
        response=response,
        body={"error": {"message": "provider failed"}},
    )


def test_response_retry_recovers_499_and_preserves_failed_attempt(
    monkeypatch, tmp_path: Path
):
    calls = 0
    sleeps: list[float] = []

    def fake_create_response(_client, _request):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise _status_error(499, retry_after="0.25")
        return (
            SimpleNamespace(id="resp-ok"),
            {"id": "resp-ok", "status": "completed"},
            0.01,
        )

    monkeypatch.setattr(
        investment_agent,
        "_create_response",
        fake_create_response,
    )
    trace_path = tmp_path / "trace.json"
    trace = {"request_failures": []}

    response, response_data, cost, _duration = (
        investment_agent._create_response_with_retry(
            object(),
            request={"model": "gpt-5.6-sol", "input": "same logical turn"},
            trace=trace,
            trace_path=trace_path,
            turn=1,
            sleep=sleeps.append,
        )
    )

    assert response.id == "resp-ok"
    assert response_data["status"] == "completed"
    assert cost == 0.01
    assert calls == 2
    assert sleeps == [0.25]
    assert trace["request_failures"] == [
        {
            "turn": 1,
            "attempt": 1,
            "error_type": "APIStatusError",
            "status_code": 499,
            "message": "provider failed",
            "response_body": {"error": {"message": "provider failed"}},
            "request_id": None,
            "duration_ms": trace["request_failures"][0]["duration_ms"],
            "retryable": True,
            "retry_delay_seconds": 0.25,
            "response_headers": {"retry-after": "0.25"},
            "request": {
                "model": "gpt-5.6-sol",
                "input": "same logical turn",
            },
        }
    ]
    assert json.loads(trace_path.read_text())["request_failures"][0][
        "status_code"
    ] == 499


def test_response_retry_does_not_retry_permanent_400(monkeypatch, tmp_path: Path):
    calls = 0

    def fake_create_response(_client, _request):
        nonlocal calls
        calls += 1
        raise _status_error(400)

    monkeypatch.setattr(
        investment_agent,
        "_create_response",
        fake_create_response,
    )
    trace_path = tmp_path / "trace.json"
    trace = {"request_failures": []}

    with pytest.raises(openai.APIStatusError):
        investment_agent._create_response_with_retry(
            object(),
            request={"model": "gpt-5.6-sol"},
            trace=trace,
            trace_path=trace_path,
            turn=2,
            sleep=lambda _seconds: None,
        )

    assert calls == 1
    assert trace["request_failures"][0]["retryable"] is False
    assert trace["request_failures"][0]["retry_delay_seconds"] is None


def test_run_range_warms_one_target_then_fans_out(monkeypatch, tmp_path: Path):
    calls: list[tuple[str, int]] = []
    lock = Lock()

    def fake_run_one(**kwargs):
        with lock:
            calls.append((kwargs["day"], kwargs["rank"]))
        return _result(day=kwargs["day"], rank=kwargs["rank"])

    monkeypatch.setattr(investment_agent, "run_one", fake_run_one)
    monkeypatch.setattr(
        investment_agent,
        "_investment_candidates",
        lambda **kwargs: [
            {
                "daily_rank": rank,
                "development_id": f"{rank:064d}",
            }
            for rank in range(1, kwargs["limit"] + 1)
        ],
    )
    monkeypatch.setattr(
        investment_agent.investment_agent_runs,
        "publish_day",
        lambda **kwargs: {
            "day": kwargs["day"],
            "candidate_count": len(kwargs["candidates"]),
        },
    )

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
    assert result["telemetry"]["request_retries"] == 0
    assert result["selection"]["audience"] == "investment"
    assert result["schema_version"] == "investment-agent-batch-v2"
    assert result["dry_run"] is False
    assert result["publications"] == [
        {"day": "2026-07-19", "candidate_count": 3},
        {"day": "2026-07-20", "candidate_count": 3},
    ]


def test_run_range_dry_run_resolves_targets_without_writes_or_model_calls(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setattr(
        investment_agent,
        "_investment_candidates",
        lambda **_kwargs: [
            {"daily_rank": 1, "development_id": "a" * 64},
            {"daily_rank": 4, "development_id": "b" * 64},
        ],
    )
    monkeypatch.setattr(
        investment_agent,
        "run_one",
        lambda **_kwargs: pytest.fail("dry-run started a model call"),
    )
    monkeypatch.setattr(
        investment_agent.investment_agent_runs,
        "publish_day",
        lambda **_kwargs: pytest.fail("dry-run published a day"),
    )
    trace_root = tmp_path / "traces"
    db_path = tmp_path / "investment-agent.db"

    result = investment_agent.run_range(
        through="2026-07-21",
        top_ranked=2,
        dry_run=True,
        trace_root=trace_root,
        db_path=db_path,
    )

    assert result["complete"] is True
    assert result["dry_run"] is True
    assert result["counts"]["requested"] == 2
    assert result["counts"]["complete"] == 0
    assert result["telemetry"]["reported_cost_usd"] == 0
    assert [item["daily_rank"] for item in result["targets"]] == [1, 4]
    assert result["items"] == []
    assert result["publications"] == []
    assert not trace_root.exists()
    assert not db_path.exists()


def test_run_range_preserves_individual_failures(monkeypatch, tmp_path: Path):
    def fake_run_one(**kwargs):
        if kwargs["rank"] == 2:
            raise RuntimeError("provider failed")
        return _result(day=kwargs["day"], rank=kwargs["rank"])

    monkeypatch.setattr(investment_agent, "run_one", fake_run_one)
    monkeypatch.setattr(
        investment_agent,
        "_investment_candidates",
        lambda **kwargs: [
            {
                "daily_rank": rank,
                "development_id": f"{rank:064d}",
            }
            for rank in range(1, kwargs["limit"] + 1)
        ],
    )
    monkeypatch.setattr(
        investment_agent.investment_agent_runs,
        "publish_day",
        lambda **kwargs: {
            "day": kwargs["day"],
            "candidate_count": len(kwargs["candidates"]),
        },
    )

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
    assert result["publications"] == []


def test_run_range_selects_top_investment_routes_not_raw_daily_ranks(
    monkeypatch, tmp_path: Path
):
    calls: list[tuple[str, int, str]] = []
    candidates = [
        {"daily_rank": 1, "development_id": "a" * 64},
        {"daily_rank": 4, "development_id": "b" * 64},
        {"daily_rank": 9, "development_id": "c" * 64},
    ]

    monkeypatch.setattr(
        investment_agent,
        "_investment_candidates",
        lambda **_kwargs: candidates,
    )

    def fake_run_one(**kwargs):
        calls.append(
            (kwargs["day"], kwargs["rank"], kwargs["development_id"])
        )
        return _result(day=kwargs["day"], rank=kwargs["rank"])

    monkeypatch.setattr(investment_agent, "run_one", fake_run_one)
    monkeypatch.setattr(
        investment_agent.investment_agent_runs,
        "publish_day",
        lambda **kwargs: {
            "day": kwargs["day"],
            "candidates": kwargs["candidates"],
        },
    )

    result = investment_agent.run_range(
        through="2026-07-19",
        top_ranked=2,
        workers=2,
        trace_root=tmp_path / "traces",
        db_path=tmp_path / "investment-agent.db",
    )

    assert calls == [
        ("2026-07-19", 1, "a" * 64),
        ("2026-07-19", 4, "b" * 64),
    ]
    assert [item["daily_rank"] for item in result["targets"]] == [1, 4]


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
    assert "rank-001-5-6-sol-xhigh-investment-agent-v12" in first.name
