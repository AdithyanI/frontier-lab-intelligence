import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from fli.insights import daily_runner, editorial, editorial_runs
from fli.routing import model as routing_model
from fli.routing import runs as routing_runs


DAY = "2026-07-16"
EVIDENCE_DAYS = 9
EVENT_RUN_ID = "event-run-1"
FEED_RUN_ID = "feed-run-1"
ROUTING_RUN_ID = "routing-run-1"
WORKSPACE_RUN_ID = "workspace-run-1"


def _evidence_result() -> dict[str, Any]:
    return {
        "range": {"date_from": "2026-07-08", "date_to": DAY},
        "collection_range": {"date_from": DAY, "date_to": DAY},
        "collection": {
            "run_id": "collection-run-1",
            "status": "complete",
            "provider_requests": 3,
            "accounts_complete": 12,
            "failures": [],
            "unfinished_accounts": [],
            "discarded_detail": "not persisted in the compact checkpoint",
        },
        "collection_coverage": {"complete": True},
        "feed": {
            "run_id": FEED_RUN_ID,
            "date_from": "2026-07-08",
            "date_to": DAY,
            "normalized_post_count": 41,
            "relation_count": 7,
            "reused": False,
            "discarded_detail": "not persisted in the compact checkpoint",
        },
        "events": {
            "run_id": EVENT_RUN_ID,
            "cluster_count": 8,
            "member_count": 19,
            "link_count": 6,
            "reused": False,
            "discarded_detail": "not persisted in the compact checkpoint",
        },
        "publication": {
            "event_run_id": EVENT_RUN_ID,
            "feed_run_id": FEED_RUN_ID,
        },
        "artifacts": {"counts": {"fetched": 5, "failed": 0}},
        "view_cache": {"refreshed": True},
        "discarded_detail": "not persisted in the compact checkpoint",
    }


def _routing_result() -> dict[str, Any]:
    return {
        "source_event_run_id": EVENT_RUN_ID,
        "source_feed_run_id": FEED_RUN_ID,
        "through": DAY,
        "days": 1,
        "top_ranked": routing_runs.DEFAULT_REFRESH_TOP_RANKED,
        "model": routing_model.DEFAULT_MODEL,
        "reasoning_effort": routing_model.DEFAULT_REASONING_EFFORT,
        "plan": [{"day": DAY, "run_id": ROUTING_RUN_ID, "reused": False}],
        "model_requests": 8,
        "counts": {"complete": 8},
        "runs": [{"day": DAY, "run_id": ROUTING_RUN_ID}],
        "will_call_model": True,
        "discarded_detail": "not persisted in the compact checkpoint",
    }


def _workspace_result(*, source_overrides: dict[str, str] | None = None) -> dict[str, Any]:
    source = {
        "routing_run_id": ROUTING_RUN_ID,
        "event_run_id": EVENT_RUN_ID,
        "feed_run_id": FEED_RUN_ID,
    }
    source.update(source_overrides or {})
    return {
        "workspace": f"tmp/daily-intelligence/{WORKSPACE_RUN_ID}",
        "manifest": f"tmp/daily-intelligence/{WORKSPACE_RUN_ID}/manifest.json",
        "draft_template": (
            f"tmp/daily-intelligence/{WORKSPACE_RUN_ID}/draft.template.json"
        ),
        "run_id": WORKSPACE_RUN_ID,
        "manifest_sha256": "manifest-sha-1",
        "day": DAY,
        "counts": {"events": 8, "candidate_pairs": 11},
        "source": source,
        "dry_run": False,
        "reused": False,
        "workspace_schema_version": editorial_runs.WORKSPACE_SCHEMA_VERSION,
        "draft_schema_version": editorial.DRAFT_SCHEMA_VERSION,
    }


class _Pipeline:
    def __init__(
        self,
        *,
        workspace: dict[str, Any] | None = None,
    ) -> None:
        self.order: list[str] = []
        self.evidence_calls: list[dict[str, Any]] = []
        self.routing_calls: list[dict[str, Any]] = []
        self.workspace_calls: list[dict[str, Any]] = []
        self.workspace_loads: list[Path] = []
        self.template_loads: list[Path] = []
        self.codex_calls: list[dict[str, Any]] = []
        self.workspace = workspace or _workspace_result()
        self.workspace_obsolete = False
        self.template_obsolete = False

    def evidence(self, **kwargs: Any) -> dict[str, Any]:
        self.order.append("evidence")
        self.evidence_calls.append(kwargs)
        return deepcopy(_evidence_result())

    def routing(self, **kwargs: Any) -> dict[str, Any]:
        self.order.append("routing")
        self.routing_calls.append(kwargs)
        return deepcopy(_routing_result())

    def prepare(self, **kwargs: Any) -> dict[str, Any]:
        self.order.append("prepare")
        self.workspace_calls.append(kwargs)
        return deepcopy(self.workspace)

    def load_workspace(self, path: Path) -> dict[str, Any]:
        self.workspace_loads.append(path)
        if self.workspace_obsolete:
            raise ValueError("workspace uses an unsupported schema version")
        return {
            "schema_version": editorial_runs.WORKSPACE_SCHEMA_VERSION,
            "day": DAY,
            "run_id": WORKSPACE_RUN_ID,
            "manifest_sha256": "manifest-sha-1",
            "source": {
                "routing_run_id": ROUTING_RUN_ID,
                "event_run_id": EVENT_RUN_ID,
                "feed_run_id": FEED_RUN_ID,
            },
        }

    def load_template(self, path: Path) -> dict[str, Any]:
        self.template_loads.append(path)
        manifest = {
            "schema_version": editorial_runs.WORKSPACE_SCHEMA_VERSION,
            "day": DAY,
            "run_id": WORKSPACE_RUN_ID,
            "manifest_sha256": "manifest-sha-1",
            "source": {
                "routing_run_id": ROUTING_RUN_ID,
                "event_run_id": EVENT_RUN_ID,
                "feed_run_id": FEED_RUN_ID,
            },
        }
        template = editorial.draft_template(manifest)
        if self.template_obsolete:
            template["workspace_manifest_sha256"] = "obsolete"
        return template

    def codex(self, **kwargs: Any) -> dict[str, Any]:
        self.order.append("codex")
        self.codex_calls.append(kwargs)
        kwargs["checkpoint"](
            {
                "status": "thread_started",
                "thread_id": "thread-1",
                "goal_status": "active",
            }
        )
        return {
            "status": "complete",
            "thread_id": "thread-1",
            "goal_status": "complete",
        }


def _run(
    *,
    db_path: Path,
    pipeline: _Pipeline,
    launch_codex: bool = False,
    codex_runner: Any | None = None,
) -> dict[str, Any]:
    return daily_runner.run_day(
        day=DAY,
        db_path=db_path,
        evidence_days=EVIDENCE_DAYS,
        launch_codex=launch_codex,
        evidence_runner=pipeline.evidence,
        routing_runner=pipeline.routing,
        workspace_preparer=pipeline.prepare,
        workspace_loader=pipeline.load_workspace,
        workspace_template_loader=pipeline.load_template,
        codex_runner=codex_runner,
    )


def _expected_config() -> dict[str, Any]:
    return {
        "contract_version": daily_runner.RUN_CONTRACT_VERSION,
        "day": DAY,
        "evidence_days": EVIDENCE_DAYS,
        "collection_days": 1,
        "workers": 32,
        "routing_days": 1,
        "top_ranked": routing_runs.DEFAULT_REFRESH_TOP_RANKED,
        "routing_model": routing_model.DEFAULT_MODEL,
        "routing_reasoning_effort": routing_model.DEFAULT_REASONING_EFFORT,
        "routing_workers": routing_runs.DEFAULT_REFRESH_WORKERS,
        "routing_day_workers": 1,
        "repo_root": str(daily_runner.REPO_ROOT),
        "skill_path": str(daily_runner.DEFAULT_SKILL_PATH.resolve()),
    }


def test_default_run_prepares_in_order_with_exact_stage_args_and_lineage(tmp_path):
    pipeline = _Pipeline()

    result = _run(db_path=tmp_path / "editorial.db", pipeline=pipeline)

    assert pipeline.order == ["evidence", "routing", "prepare"]
    assert pipeline.evidence_calls == [
        {
            "through": DAY,
            "days": EVIDENCE_DAYS,
            "collection_days": 1,
            "workers": 32,
            "progress": None,
        }
    ]
    assert pipeline.routing_calls == [
        {
            "through": DAY,
            "days": 1,
            "top_ranked": routing_runs.DEFAULT_REFRESH_TOP_RANKED,
            "model": routing_model.DEFAULT_MODEL,
            "effort": routing_model.DEFAULT_REASONING_EFFORT,
            "workers": routing_runs.DEFAULT_REFRESH_WORKERS,
            "day_workers": 1,
            "replace": False,
            "dry_run": False,
        }
    ]
    assert pipeline.workspace_calls == [{"day": DAY}]
    assert pipeline.codex_calls == []

    expected_evidence = daily_runner._compact_evidence(_evidence_result())
    expected_routing = daily_runner._compact_routing(_routing_result())
    assert result["config"] == _expected_config()
    assert result["config_sha256"] == daily_runner._sha256(_expected_config())
    assert result["run_id"] == (
        f"daily-run-{DAY}-{daily_runner._sha256(_expected_config())[:12]}"
    )
    assert result["status"] == "prepared"
    assert result["stage"] == "prepare"
    assert result["codex_thread_id"] is None
    assert result["editorial_run_id"] is None
    assert result["stages"] == {
        "evidence": expected_evidence,
        "routing": expected_routing,
        "prepare": _workspace_result(),
    }
    assert result["stages"]["routing"]["source_event_run_id"] == EVENT_RUN_ID
    assert result["stages"]["routing"]["source_feed_run_id"] == FEED_RUN_ID
    assert result["stages"]["prepare"]["source"] == {
        "routing_run_id": ROUTING_RUN_ID,
        "event_run_id": EVENT_RUN_ID,
        "feed_run_id": FEED_RUN_ID,
    }


def test_resume_reuses_all_prepared_stages(tmp_path):
    pipeline = _Pipeline()
    db_path = tmp_path / "editorial.db"

    first = _run(db_path=db_path, pipeline=pipeline)
    resumed = _run(db_path=db_path, pipeline=pipeline)

    assert resumed["run_id"] == first["run_id"]
    assert resumed["reused"] is True
    assert resumed["status"] == "prepared"
    assert resumed["stage"] == "prepare"
    assert resumed["stages"] == first["stages"]
    assert pipeline.order == ["evidence", "routing", "prepare"]
    assert pipeline.workspace_loads == [
        daily_runner.REPO_ROOT / f"tmp/daily-intelligence/{WORKSPACE_RUN_ID}"
    ]
    assert pipeline.template_loads == [
        daily_runner.REPO_ROOT
        / f"tmp/daily-intelligence/{WORKSPACE_RUN_ID}/draft.template.json"
    ]


def test_resume_reprepares_an_obsolete_workspace_before_codex_starts(tmp_path):
    pipeline = _Pipeline()
    db_path = tmp_path / "editorial.db"
    first = _run(db_path=db_path, pipeline=pipeline)
    pipeline.workspace_obsolete = True

    resumed = _run(db_path=db_path, pipeline=pipeline)

    assert resumed["run_id"] == first["run_id"]
    assert resumed["status"] == "prepared"
    assert pipeline.order == ["evidence", "routing", "prepare", "prepare"]
    assert len(pipeline.workspace_loads) == 1
    assert resumed["codex_thread_id"] is None


def test_resume_reprepares_a_stale_draft_template_before_codex_starts(tmp_path):
    pipeline = _Pipeline()
    db_path = tmp_path / "editorial.db"
    _run(db_path=db_path, pipeline=pipeline)
    pipeline.template_obsolete = True

    resumed = _run(db_path=db_path, pipeline=pipeline)

    assert resumed["status"] == "prepared"
    assert pipeline.order == ["evidence", "routing", "prepare", "prepare"]
    assert len(pipeline.template_loads) == 1
    assert resumed["codex_thread_id"] is None


def test_obsolete_workspace_with_started_task_fails_closed(tmp_path):
    pipeline = _Pipeline()
    db_path = tmp_path / "editorial.db"

    def interrupted_task(**kwargs: Any) -> None:
        pipeline.order.append("codex-interrupted")
        kwargs["checkpoint"](
            {
                "status": "thread_started",
                "thread_id": "obsolete-thread",
                "goal_status": "active",
            }
        )
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        _run(
            db_path=db_path,
            pipeline=pipeline,
            launch_codex=True,
            codex_runner=interrupted_task,
        )

    pipeline.workspace_obsolete = True
    with pytest.raises(daily_runner.DailyRunError) as exc_info:
        _run(
            db_path=db_path,
            pipeline=pipeline,
            launch_codex=True,
            codex_runner=lambda **_: pytest.fail("must not create a replacement task"),
        )

    assert exc_info.value.code == "E_WORKSPACE_OBSOLETE_TASK"
    assert exc_info.value.retryable is False
    stored = daily_runner.inspect_run(db_path=db_path, day=DAY)
    assert stored["codex_thread_id"] == "obsolete-thread"
    assert stored["error"]["code"] == "E_WORKSPACE_OBSOLETE_TASK"


def test_same_day_rejects_a_different_contract_instead_of_creating_second_run(
    tmp_path,
):
    pipeline = _Pipeline()
    db_path = tmp_path / "editorial.db"
    _run(db_path=db_path, pipeline=pipeline)

    with pytest.raises(daily_runner.DailyRunError) as exc_info:
        daily_runner.run_day(
            day=DAY,
            db_path=db_path,
            evidence_days=EVIDENCE_DAYS,
            workers=16,
            evidence_runner=pipeline.evidence,
            routing_runner=pipeline.routing,
            workspace_preparer=pipeline.prepare,
        )

    assert exc_info.value.code == "E_RUN_CONFIG_MISMATCH"
    conn = daily_runner.connect(db_path)
    try:
        assert conn.execute(
            "SELECT COUNT(*) FROM daily_orchestration_run WHERE day = ?", (DAY,)
        ).fetchone()[0] == 1
    finally:
        conn.close()


def test_prepare_then_launch_reuses_stages_and_creates_only_one_task(
    tmp_path, monkeypatch
):
    pipeline = _Pipeline()
    db_path = tmp_path / "editorial.db"
    editorial_lookups: list[str] = []

    def latest_editorial_run(*, workspace_run_id: str, **_: Any) -> str:
        editorial_lookups.append(workspace_run_id)
        return "editorial-run-1"

    monkeypatch.setattr(daily_runner, "_latest_editorial_run", latest_editorial_run)

    prepared = _run(db_path=db_path, pipeline=pipeline)
    launched = _run(
        db_path=db_path,
        pipeline=pipeline,
        launch_codex=True,
        codex_runner=pipeline.codex,
    )
    repeated = _run(
        db_path=db_path,
        pipeline=pipeline,
        launch_codex=True,
        codex_runner=pipeline.codex,
    )

    assert prepared["run_id"] == launched["run_id"] == repeated["run_id"]
    assert pipeline.order == ["evidence", "routing", "prepare", "codex"]
    assert len(pipeline.codex_calls) == 1
    codex_call = pipeline.codex_calls[0]
    assert codex_call["name"] == f"FLI Daily Brief — {DAY}"
    assert WORKSPACE_RUN_ID in codex_call["objective"]
    assert DAY in codex_call["prompt"]
    assert codex_call["skill_path"] == daily_runner.DEFAULT_SKILL_PATH
    assert codex_call["timeout_seconds"] == daily_runner.DEFAULT_CODEX_TIMEOUT_SECONDS
    assert codex_call["thread_id"] is None
    assert codex_call["progress"] is None
    assert callable(codex_call["checkpoint"])
    assert editorial_lookups == [WORKSPACE_RUN_ID]
    assert launched["status"] == "complete"
    assert launched["stage"] == "codex"
    assert launched["codex_thread_id"] == "thread-1"
    assert launched["editorial_run_id"] == "editorial-run-1"
    assert repeated["reused"] is True
    assert repeated["stages"]["codex"] == {
        "status": "complete",
        "thread_id": "thread-1",
        "goal_status": "complete",
    }


def test_thread_starting_without_id_fails_closed_instead_of_launching_replacement(
    tmp_path,
):
    pipeline = _Pipeline()
    db_path = tmp_path / "editorial.db"

    def interrupted_start(**kwargs: Any) -> None:
        pipeline.order.append("codex-start-interrupted")
        kwargs["checkpoint"]({"status": "thread_starting", "thread_id": None})
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        _run(
            db_path=db_path,
            pipeline=pipeline,
            launch_codex=True,
            codex_runner=interrupted_start,
        )

    def replacement_task(**_: Any) -> None:
        raise AssertionError("an unknown prior task must not be replaced")

    with pytest.raises(daily_runner.DailyRunError) as exc_info:
        _run(
            db_path=db_path,
            pipeline=pipeline,
            launch_codex=True,
            codex_runner=replacement_task,
        )

    error = exc_info.value
    assert error.code == "E_CODEX_THREAD_UNKNOWN"
    assert error.retryable is False
    assert error.exit_code == 4
    assert pipeline.order == [
        "evidence",
        "routing",
        "prepare",
        "codex-start-interrupted",
    ]
    stored = daily_runner.inspect_run(db_path=db_path, day=DAY)
    assert stored["status"] == "failed"
    assert stored["stage"] == "codex"
    assert stored["codex_thread_id"] is None
    assert stored["stages"]["codex"] == {
        "status": "thread_starting",
        "thread_id": None,
    }
    assert stored["error"]["code"] == "E_CODEX_THREAD_UNKNOWN"
    assert stored["error"]["retryable"] is False


@pytest.mark.parametrize(
    ("source_field", "error_code"),
    [
        ("routing_run_id", "E_ROUTING_CHANGED"),
        ("event_run_id", "E_EVENT_CHANGED"),
        ("feed_run_id", "E_FEED_CHANGED"),
    ],
)
def test_workspace_must_preserve_exact_frozen_source_ids(
    tmp_path, source_field, error_code
):
    pipeline = _Pipeline(
        workspace=_workspace_result(source_overrides={source_field: "different-run"})
    )
    db_path = tmp_path / "editorial.db"

    with pytest.raises(daily_runner.DailyRunError) as exc_info:
        _run(db_path=db_path, pipeline=pipeline)

    assert exc_info.value.code == error_code
    assert exc_info.value.retryable is True
    assert exc_info.value.exit_code == 4
    assert pipeline.order == ["evidence", "routing", "prepare"]
    stored = daily_runner.inspect_run(db_path=db_path, day=DAY)
    assert stored["status"] == "failed"
    assert stored["stage"] == "prepare"
    assert set(stored["stages"]) == {"evidence", "routing"}
    assert stored["error"]["code"] == error_code


def test_cli_dry_run_defaults_to_stable_json_without_touching_store(
    tmp_path, monkeypatch, capsys
):
    db_path = tmp_path / "must-not-be-created.db"
    ticks = iter((100.0, 100.125))
    monkeypatch.setattr(daily_runner.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(daily_runner, "uuid4", lambda: "request-1")
    monkeypatch.setattr(
        daily_runner, "_now", lambda: "2026-07-18T10:00:00+00:00"
    )

    exit_code = daily_runner.main(
        [
            "run-day",
            "--day",
            DAY,
            "--db",
            str(db_path),
            "--evidence-days",
            str(EVIDENCE_DAYS),
            "--dry-run",
            "--progress",
            "off",
            "--no-input",
        ]
    )
    captured = capsys.readouterr()
    expected = {
        "schema_version": daily_runner.CLI_SCHEMA_VERSION,
        "command": "daily-intelligence.run-day",
        "status": "ok",
        "data": {
            "dry_run": True,
            "plan": {
                "day": DAY,
                "stop_after": "prepare",
                "will_collect_external_evidence": True,
                "will_call_routing_model": True,
                "will_launch_codex": False,
                "config": _expected_config(),
            },
        },
        "error": None,
        "meta": {
            "request_id": "request-1",
            "duration_ms": 125.0,
            "timestamp_utc": "2026-07-18T10:00:00+00:00",
        },
    }

    assert exit_code == 0
    assert captured.err == ""
    assert captured.out == daily_runner._canonical_json(expected) + "\n"
    assert json.loads(captured.out) == expected
    assert not db_path.exists()


def test_nested_routing_progress_is_redirected_off_stdout(tmp_path, capsys):
    pipeline = _Pipeline()

    def noisy_routing(**kwargs: Any) -> dict[str, Any]:
        print('{"processed":1,"status":"complete"}')
        return pipeline.routing(**kwargs)

    daily_runner.run_day(
        day=DAY,
        db_path=tmp_path / "editorial.db",
        evidence_days=EVIDENCE_DAYS,
        progress=lambda *_args: None,
        evidence_runner=pipeline.evidence,
        routing_runner=noisy_routing,
        workspace_preparer=pipeline.prepare,
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert '"processed":1' in captured.err
