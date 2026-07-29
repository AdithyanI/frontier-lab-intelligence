import json

import pytest

from fli import cli as root_cli
from fli.insights import cli as insight_cli


def test_root_insights_help_exposes_domain_subcommands(capsys):
    with pytest.raises(SystemExit) as exc:
        root_cli.main(["insights", "--help"])

    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "run-investment-agent" in output
    assert "company-universe" in output
    assert "summary" in output


def test_run_investment_agent_forwards_dry_run(monkeypatch, capsys):
    captured = {}

    def fake_run_range(**kwargs):
        captured.update(kwargs)
        return {
            "schema_version": "investment-agent-batch-v2",
            "dry_run": True,
            "complete": True,
            "targets": [],
            "counts": {"requested": 0},
        }

    monkeypatch.setattr(insight_cli.investment_agent, "run_range", fake_run_range)

    exit_code = insight_cli.main(
        [
            "run-investment-agent",
            "--through",
            "2026-07-21",
            "--days",
            "3",
            "--top-ranked",
            "10",
            "--dry-run",
            "--no-input",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["dry_run"] is True
    assert captured["through"] == "2026-07-21"
    assert captured["days"] == 3
    assert payload["status"] == "ok"
    assert payload["data"]["dry_run"] is True
