import json
import sqlite3
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from fli.insights import daily_runner, editorial, editorial_runs
from fli.routing import model as routing_model
from fli.routing import runs as routing_runs
from fli.scoring import development_attention


DAY = "2026-07-16"
EVIDENCE_DAYS = 9
EVENT_RUN_ID = "event-run-1"
FEED_RUN_ID = "feed-run-1"
ROUTING_RUN_ID = "routing-run-1"
WORKSPACE_RUN_ID = "workspace-run-1"
ROUTING_COHORT_SHA256 = "routing-cohort-sha-1"
SOURCE_RANK_INPUT_SHA256 = "source-rank-input-sha-1"


def _evidence_result(
    *,
    event_run_id: str = EVENT_RUN_ID,
    feed_run_id: str = FEED_RUN_ID,
) -> dict[str, Any]:
    result = {
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
            "run_id": feed_run_id,
            "date_from": "2026-07-08",
            "date_to": DAY,
            "normalized_post_count": 41,
            "relation_count": 7,
            "reused": False,
            "discarded_detail": "not persisted in the compact checkpoint",
        },
        "events": {
            "run_id": event_run_id,
            "cluster_count": 8,
            "member_count": 19,
            "link_count": 6,
            "reused": False,
            "discarded_detail": "not persisted in the compact checkpoint",
        },
        "publication": {
            "event_run_id": event_run_id,
            "feed_run_id": feed_run_id,
        },
        "artifacts": {"counts": {"fetched": 5, "failed": 0}},
        "view_cache": {"refreshed": True},
        "discarded_detail": "not persisted in the compact checkpoint",
    }
    return result


def _routing_result(
    *,
    event_run_id: str = EVENT_RUN_ID,
    feed_run_id: str = FEED_RUN_ID,
    routing_run_id: str = ROUTING_RUN_ID,
    routing_cohort_sha256: str = ROUTING_COHORT_SHA256,
    source_rank_input_sha256: str = SOURCE_RANK_INPUT_SHA256,
) -> dict[str, Any]:
    return {
        "source_event_run_id": event_run_id,
        "source_feed_run_id": feed_run_id,
        "through": DAY,
        "days": 1,
        "top_ranked": routing_runs.DEFAULT_REFRESH_TOP_RANKED,
        "model": routing_model.DEFAULT_MODEL,
        "reasoning_effort": routing_model.DEFAULT_REASONING_EFFORT,
        "rank_version": development_attention.DAILY_RANK_VERSION,
        "routing_cohort_sha256": routing_cohort_sha256,
        "source_rank_input_sha256": source_rank_input_sha256,
        "plan": [{"day": DAY, "run_id": routing_run_id, "reused": False}],
        "reuse_policy": "exact-event-evidence-input",
        "resumed_complete_count": 0,
        "reused_exact_count": 7,
        "days_with_exact_reuse": 1,
        "model_requests": 1,
        "counts": {"complete": 8},
        "runs": [{"day": DAY, "run_id": routing_run_id}],
        "will_call_model": True,
        "discarded_detail": "not persisted in the compact checkpoint",
    }


def _production_routing_result() -> dict[str, Any]:
    result = _routing_result()
    result.pop("routing_cohort_sha256")
    result.pop("source_rank_input_sha256")
    result["plan"][0]["source_rank_input_sha256"] = SOURCE_RANK_INPUT_SHA256
    result["runs"] = [
        {
            "run": {
                "run_id": ROUTING_RUN_ID,
                "source_event_run_id": EVENT_RUN_ID,
                "source_feed_run_id": FEED_RUN_ID,
                "source_rank_input_sha256": SOURCE_RANK_INPUT_SHA256,
                "cohort_sha256": ROUTING_COHORT_SHA256,
            },
            "counts": {"complete": 8},
        }
    ]
    return result


def _workspace_result(
    *,
    run_id: str = WORKSPACE_RUN_ID,
    event_run_id: str = EVENT_RUN_ID,
    feed_run_id: str = FEED_RUN_ID,
    routing_run_id: str = ROUTING_RUN_ID,
    source_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = {
        "routing_run_id": routing_run_id,
        "event_run_id": event_run_id,
        "feed_run_id": feed_run_id,
    }
    source.update(source_overrides or {})
    return {
        "workspace": f"tmp/daily-intelligence/{run_id}",
        "manifest": f"tmp/daily-intelligence/{run_id}/manifest.json",
        "draft_template": (
            f"tmp/daily-intelligence/{run_id}/draft.template.json"
        ),
        "run_id": run_id,
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
        evidence: dict[str, Any] | None = None,
        routing: dict[str, Any] | None = None,
    ) -> None:
        self.order: list[str] = []
        self.evidence_calls: list[dict[str, Any]] = []
        self.routing_calls: list[dict[str, Any]] = []
        self.workspace_calls: list[dict[str, Any]] = []
        self.workspace_loads: list[Path] = []
        self.template_loads: list[Path] = []
        self.codex_calls: list[dict[str, Any]] = []
        self.workspace = workspace or _workspace_result()
        self.evidence_result = evidence or _evidence_result()
        self.routing_result = routing or _routing_result()
        self.workspace_obsolete = False
        self.template_obsolete = False

    def evidence(self, **kwargs: Any) -> dict[str, Any]:
        self.order.append("evidence")
        self.evidence_calls.append(kwargs)
        return deepcopy(self.evidence_result)

    def routing(self, **kwargs: Any) -> dict[str, Any]:
        self.order.append("routing")
        self.routing_calls.append(kwargs)
        return deepcopy(self.routing_result)

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
        settings = {
            "model": kwargs["model"] or "gpt-5.6-sol",
            "reasoning_effort": kwargs["reasoning_effort"] or "xhigh",
            "service_tier": (
                "default"
                if kwargs["service_tier"]
                == daily_runner.DEFAULT_CODEX_SERVICE_TIER
                else kwargs["service_tier"]
            ),
        }
        kwargs["checkpoint"](
            {
                "status": "thread_started",
                "thread_id": "thread-1",
                "goal_status": "active",
                "settings": settings,
            }
        )
        return {
            "status": "complete",
            "thread_id": "thread-1",
            "goal_status": "complete",
            "settings": settings,
        }


def _run(
    *,
    db_path: Path,
    pipeline: _Pipeline,
    launch_codex: bool = False,
    codex_runner: Any | None = None,
    codex_model: str | None = None,
    codex_reasoning_effort: str | None = None,
    codex_service_tier: str | None = daily_runner.DEFAULT_CODEX_SERVICE_TIER,
    source_lineage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return daily_runner.run_day(
        day=DAY,
        db_path=db_path,
        evidence_days=EVIDENCE_DAYS,
        launch_codex=launch_codex,
        codex_model=codex_model,
        codex_reasoning_effort=codex_reasoning_effort,
        codex_service_tier=codex_service_tier,
        evidence_runner=pipeline.evidence,
        routing_runner=pipeline.routing,
        workspace_preparer=pipeline.prepare,
        workspace_loader=pipeline.load_workspace,
        workspace_template_loader=pipeline.load_template,
        codex_runner=codex_runner,
        source_lineage=source_lineage,
    )


def _source_lineage(
    *,
    event_run_id: str = EVENT_RUN_ID,
    feed_run_id: str = FEED_RUN_ID,
    routing_run_id: str = ROUTING_RUN_ID,
    routing_cohort_sha256: str = ROUTING_COHORT_SHA256,
    source_rank_input_sha256: str = SOURCE_RANK_INPUT_SHA256,
) -> dict[str, str]:
    return {
        "event_run_id": event_run_id,
        "feed_run_id": feed_run_id,
        "routing_run_id": routing_run_id,
        "routing_cohort_sha256": routing_cohort_sha256,
        "source_rank_input_sha256": source_rank_input_sha256,
    }


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
        "rank_version": development_attention.DAILY_RANK_VERSION,
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


def test_run_day_normalizes_production_routing_refresh_lineage(tmp_path):
    pipeline = _Pipeline(routing=_production_routing_result())

    result = _run(db_path=tmp_path / "editorial.db", pipeline=pipeline)

    assert result["stages"]["routing"]["routing_cohort_sha256"] == (
        ROUTING_COHORT_SHA256
    )
    assert result["stages"]["routing"]["source_rank_input_sha256"] == (
        SOURCE_RANK_INPUT_SHA256
    )


def test_v3_resume_fails_closed_when_checkpoint_rank_lineage_is_missing(tmp_path):
    pipeline = _Pipeline()
    db_path = tmp_path / "editorial.db"
    first = _run(db_path=db_path, pipeline=pipeline)
    stages = deepcopy(first["stages"])
    stages["routing"].pop("source_rank_input_sha256")
    conn = daily_runner.connect(db_path)
    with conn:
        conn.execute(
            """UPDATE daily_orchestration_run
               SET state_json = ?
               WHERE run_id = ?""",
            (
                daily_runner._canonical_json({"stages": stages}),
                first["run_id"],
            ),
        )
    conn.close()

    with pytest.raises(daily_runner.DailyRunError) as raised:
        _run(db_path=db_path, pipeline=pipeline)

    assert raised.value.code == "E_SOURCE_LINEAGE_MISMATCH"
    assert "source_rank_input_sha256" in raised.value.message


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
                "settings": {
                    "model": kwargs["model"] or "gpt-5.6-sol",
                    "reasoning_effort": kwargs["reasoning_effort"] or "xhigh",
                    "service_tier": (
                        "default"
                        if kwargs["service_tier"]
                        == daily_runner.DEFAULT_CODEX_SERVICE_TIER
                        else kwargs["service_tier"]
                    ),
                },
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


def test_same_day_supports_a_second_versioned_contract_lineage(tmp_path):
    pipeline = _Pipeline()
    db_path = tmp_path / "editorial.db"
    first = _run(db_path=db_path, pipeline=pipeline)

    second = daily_runner.run_day(
        day=DAY,
        db_path=db_path,
        evidence_days=EVIDENCE_DAYS,
        workers=16,
        evidence_runner=pipeline.evidence,
        routing_runner=pipeline.routing,
        workspace_preparer=pipeline.prepare,
    )

    assert second["run_id"] != first["run_id"]
    assert second["config"]["workers"] == 16
    assert (
        second["config"]["rank_version"]
        == development_attention.DAILY_RANK_VERSION
    )
    conn = daily_runner.connect(db_path)
    try:
        assert conn.execute(
            "SELECT COUNT(*) FROM daily_orchestration_run WHERE day = ?", (DAY,)
        ).fetchone()[0] == 2
    finally:
        conn.close()


def test_same_source_lineage_reuses_the_exact_daily_run(tmp_path):
    pipeline = _Pipeline()
    db_path = tmp_path / "editorial.db"
    lineage = _source_lineage()

    first = _run(
        db_path=db_path,
        pipeline=pipeline,
        source_lineage=lineage,
    )
    resumed = _run(
        db_path=db_path,
        pipeline=pipeline,
        source_lineage=dict(reversed(list(lineage.items()))),
    )

    assert resumed["run_id"] == first["run_id"]
    assert resumed["reused"] is True
    assert resumed["config"]["source_lineage"] == lineage
    conn = daily_runner.connect(db_path)
    try:
        assert conn.execute(
            "SELECT COUNT(*) FROM daily_orchestration_run WHERE day = ?", (DAY,)
        ).fetchone()[0] == 1
    finally:
        conn.close()


def test_new_source_lineage_cannot_be_short_circuited_by_complete_prior_run(
    tmp_path,
):
    db_path = tmp_path / "editorial.db"
    first_pipeline = _Pipeline()
    first = _run(
        db_path=db_path,
        pipeline=first_pipeline,
        source_lineage=_source_lineage(),
    )
    conn = daily_runner.connect(db_path)
    with conn:
        conn.execute(
            """UPDATE daily_orchestration_run
               SET status = 'complete', stage = 'codex'
               WHERE run_id = ?""",
            (first["run_id"],),
        )
    conn.close()

    second_ids = {
        "event": "event-run-2",
        "feed": "feed-run-2",
        "routing": "routing-run-2",
        "workspace": "workspace-run-2",
        "cohort": "routing-cohort-sha-2",
        "rank_input": "source-rank-input-sha-2",
    }
    second_pipeline = _Pipeline(
        evidence=_evidence_result(
            event_run_id=second_ids["event"],
            feed_run_id=second_ids["feed"],
        ),
        routing=_routing_result(
            event_run_id=second_ids["event"],
            feed_run_id=second_ids["feed"],
            routing_run_id=second_ids["routing"],
            routing_cohort_sha256=second_ids["cohort"],
            source_rank_input_sha256=second_ids["rank_input"],
        ),
        workspace=_workspace_result(
            run_id=second_ids["workspace"],
            event_run_id=second_ids["event"],
            feed_run_id=second_ids["feed"],
            routing_run_id=second_ids["routing"],
        ),
    )

    second = _run(
        db_path=db_path,
        pipeline=second_pipeline,
        source_lineage=_source_lineage(
            event_run_id=second_ids["event"],
            feed_run_id=second_ids["feed"],
            routing_run_id=second_ids["routing"],
            routing_cohort_sha256=second_ids["cohort"],
            source_rank_input_sha256=second_ids["rank_input"],
        ),
    )

    assert second["run_id"] != first["run_id"]
    assert second["reused"] is False
    assert second["status"] == "prepared"
    assert second["stages"]["prepare"]["run_id"] == second_ids["workspace"]
    assert (
        second["stages"]["prepare"]["run_id"]
        != first["stages"]["prepare"]["run_id"]
    )
    assert second_pipeline.order == ["evidence", "routing", "prepare"]
    conn = daily_runner.connect(db_path)
    try:
        assert conn.execute(
            "SELECT COUNT(*) FROM daily_orchestration_run WHERE day = ?", (DAY,)
        ).fetchone()[0] == 2
    finally:
        conn.close()


def test_injected_routing_checkpoint_must_match_config_source_lineage(tmp_path):
    pipeline = _Pipeline(
        routing=_routing_result(
            source_rank_input_sha256="different-rank-input-sha",
        )
    )
    db_path = tmp_path / "editorial.db"

    with pytest.raises(daily_runner.DailyRunError) as raised:
        _run(
            db_path=db_path,
            pipeline=pipeline,
            source_lineage=_source_lineage(),
        )

    assert raised.value.code == "E_SOURCE_LINEAGE_MISMATCH"
    assert raised.value.retryable is False
    stored = daily_runner.inspect_run(db_path=db_path, day=DAY)
    assert set(stored["stages"]) == {"evidence"}
    assert stored["error"]["code"] == "E_SOURCE_LINEAGE_MISMATCH"


def test_resumed_routing_checkpoint_must_match_config_source_lineage(tmp_path):
    pipeline = _Pipeline()
    db_path = tmp_path / "editorial.db"
    first = _run(
        db_path=db_path,
        pipeline=pipeline,
        source_lineage=_source_lineage(),
    )
    stages = deepcopy(first["stages"])
    stages["routing"]["routing_cohort_sha256"] = "different-cohort-sha"
    conn = daily_runner.connect(db_path)
    with conn:
        conn.execute(
            """UPDATE daily_orchestration_run
               SET state_json = ?
               WHERE run_id = ?""",
            (
                daily_runner._canonical_json({"stages": stages}),
                first["run_id"],
            ),
        )
    conn.close()

    with pytest.raises(daily_runner.DailyRunError) as raised:
        _run(
            db_path=db_path,
            pipeline=pipeline,
            source_lineage=_source_lineage(),
        )

    assert raised.value.code == "E_SOURCE_LINEAGE_MISMATCH"
    assert pipeline.order == ["evidence", "routing", "prepare"]
    stored = daily_runner.inspect_run(db_path=db_path, run_id=first["run_id"])
    assert stored["status"] == "failed"
    assert stored["error"]["code"] == "E_SOURCE_LINEAGE_MISMATCH"


def test_current_inputs_exposes_exact_routing_source_hashes(
    tmp_path, monkeypatch
):
    from fli.web import developments as development_store

    routing_path = tmp_path / "routing.db"
    conn = sqlite3.connect(routing_path)
    conn.execute(
        """CREATE TABLE run_meta (
               singleton INTEGER PRIMARY KEY,
               run_id TEXT NOT NULL,
               source_event_run_id TEXT NOT NULL,
               source_feed_run_id TEXT NOT NULL,
               selection_limit INTEGER NOT NULL,
               model TEXT NOT NULL,
               reasoning_effort TEXT NOT NULL,
               rank_version TEXT NOT NULL,
               cohort_sha256 TEXT NOT NULL,
               source_rank_input_sha256 TEXT NOT NULL,
               expected_count INTEGER NOT NULL
           )"""
    )
    conn.execute(
        """INSERT INTO run_meta VALUES (
               1, ?, ?, ?, 100, ?, ?, ?, ?, ?, 100
           )""",
        (
            ROUTING_RUN_ID,
            EVENT_RUN_ID,
            FEED_RUN_ID,
            routing_model.DEFAULT_MODEL,
            routing_model.DEFAULT_REASONING_EFFORT,
            development_attention.DAILY_RANK_VERSION,
            ROUTING_COHORT_SHA256,
            SOURCE_RANK_INPUT_SHA256,
        ),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(
        daily_runner.routing_view,
        "latest_complete_run",
        lambda day, **_kwargs: routing_path if day == DAY else None,
    )
    monkeypatch.setattr(
        development_store,
        "current_rank_identity",
        lambda *, day: {
            "day": day,
            "rank_version": development_attention.DAILY_RANK_VERSION,
            "rank_input_sha256": SOURCE_RANK_INPUT_SHA256,
            "event_run_id": EVENT_RUN_ID,
            "feed_run_id": FEED_RUN_ID,
        },
    )
    monkeypatch.setattr(
        daily_runner.routing_runs,
        "_published_event_source",
        lambda: pytest.fail("lineage must come from the frozen routing store"),
    )

    evidence, routing = daily_runner._current_inputs(DAY)

    assert evidence["publication"] == {
        "event_run_id": EVENT_RUN_ID,
        "feed_run_id": FEED_RUN_ID,
    }
    assert routing["routing_cohort_sha256"] == ROUTING_COHORT_SHA256
    assert routing["source_rank_input_sha256"] == SOURCE_RANK_INPUT_SHA256


def test_run_batch_dry_run_plans_current_rank_without_touching_store(
    tmp_path, monkeypatch
):
    selected = []

    def current_inputs(day):
        selected.append(day)
        return ({"day": day}, {"day": day, "top_ranked": 100})

    monkeypatch.setattr(daily_runner, "_current_inputs", current_inputs)
    db_path = tmp_path / "must-not-exist.db"

    result = daily_runner.run_batch(
        through=DAY,
        days=2,
        db_path=db_path,
        day_workers=4,
        dry_run=True,
    )

    assert selected == ["2026-07-15", DAY]
    assert result["plan"]["selected_days"] == selected
    assert result["plan"]["day_workers"] == 2
    assert (
        result["plan"]["rank_version"]
        == development_attention.DAILY_RANK_VERSION
    )
    assert result["plan"]["will_collect_external_evidence"] is False
    assert result["plan"]["will_call_routing_model"] is False
    assert result["plan"]["will_launch_codex"] is False
    assert not db_path.exists()


def test_run_batch_injects_frozen_inputs_into_each_daily_v3_lineage(
    tmp_path, monkeypatch
):
    calls = []

    def current_inputs(day):
        return (
            {
                "feed": {"run_id": f"feed-{day}"},
                "publication": {
                    "event_run_id": f"events-{day}",
                    "feed_run_id": f"feed-{day}",
                },
            },
            {
                "source_event_run_id": f"events-{day}",
                "source_feed_run_id": f"feed-{day}",
                "top_ranked": 100,
                "routing_cohort_sha256": f"cohort-{day}",
                "source_rank_input_sha256": f"rank-input-{day}",
                "plan": [{"day": day, "run_id": f"routing-{day}"}],
            },
        )

    def run_day(**kwargs):
        evidence = kwargs["evidence_runner"]()
        routing = kwargs["routing_runner"]()
        calls.append(
            {
                "day": kwargs["day"],
                "launch_codex": kwargs["launch_codex"],
                "evidence": evidence,
                "routing": routing,
                "source_lineage": kwargs["source_lineage"],
            }
        )
        return {
            "run_id": f"daily-v3-{kwargs['day']}",
            "day": kwargs["day"],
            "contract_version": daily_runner.RUN_CONTRACT_VERSION,
        }

    monkeypatch.setattr(daily_runner, "_current_inputs", current_inputs)
    monkeypatch.setattr(daily_runner, "run_day", run_day)

    result = daily_runner.run_batch(
        through=DAY,
        days=2,
        db_path=tmp_path / "editorial.db",
        day_workers=2,
    )

    assert result["complete"] == 2
    assert result["failed"] == 0
    assert [item["day"] for item in result["runs"]] == ["2026-07-15", DAY]
    assert {item["contract_version"] for item in result["runs"]} == {
        daily_runner.RUN_CONTRACT_VERSION
    }
    assert {item["day"] for item in calls} == {"2026-07-15", DAY}
    assert all(item["launch_codex"] is True for item in calls)
    assert all(
        item["evidence"]["publication"]["event_run_id"]
        == item["routing"]["source_event_run_id"]
        for item in calls
    )
    assert all(
        item["source_lineage"]
        == {
            "event_run_id": f"events-{item['day']}",
            "feed_run_id": f"feed-{item['day']}",
            "routing_run_id": f"routing-{item['day']}",
            "routing_cohort_sha256": f"cohort-{item['day']}",
            "source_rank_input_sha256": f"rank-input-{item['day']}",
        }
        for item in calls
    )


def test_prepare_then_launch_reuses_stages_and_creates_only_one_task(
    tmp_path, monkeypatch
):
    pipeline = _Pipeline()
    db_path = tmp_path / "editorial.db"
    editorial_lookups: list[str] = []

    def latest_editorial_run(*, workspace_run_id: str, **_: Any) -> str:
        editorial_lookups.append(workspace_run_id)
        return "editorial-run-1" if pipeline.codex_calls else None

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
    assert codex_call["model"] is None
    assert codex_call["reasoning_effort"] is None
    assert codex_call["service_tier"] == daily_runner.DEFAULT_CODEX_SERVICE_TIER
    assert codex_call["thread_id"] is None
    assert codex_call["post_completion_output_path"] == (
        daily_runner.AGENT_FEEDBACK_DIR / f"{DAY}.md"
    )
    assert "Anything else" in codex_call["post_completion_prompt"]
    assert "Do not modify the brief" in codex_call["post_completion_prompt"]
    assert codex_call["progress"] is None
    assert callable(codex_call["checkpoint"])
    assert str(db_path) in codex_call["prompt"]
    assert editorial_lookups == [WORKSPACE_RUN_ID, WORKSPACE_RUN_ID]
    assert launched["status"] == "complete"
    assert launched["stage"] == "codex"
    assert launched["codex_thread_id"] == "thread-1"
    assert launched["editorial_run_id"] == "editorial-run-1"
    assert repeated["reused"] is True
    assert repeated["stages"]["codex"] == {
        "status": "complete",
        "thread_id": "thread-1",
        "completion_source": "editorial_run",
        "requested_settings": {
            "model": None,
            "reasoning_effort": None,
            "service_tier": daily_runner.DEFAULT_CODEX_SERVICE_TIER,
        },
        "settings": {
            "model": "gpt-5.6-sol",
            "reasoning_effort": "xhigh",
            "service_tier": "default",
        },
    }


def test_launch_binds_explicit_codex_settings_and_normalizes_fast_alias(
    tmp_path, monkeypatch
) -> None:
    pipeline = _Pipeline()
    db_path = tmp_path / "editorial.db"

    monkeypatch.setattr(
        daily_runner,
        "_latest_editorial_run",
        lambda **_: "editorial-run-1" if pipeline.codex_calls else None,
    )

    _run(db_path=db_path, pipeline=pipeline)
    result = _run(
        db_path=db_path,
        pipeline=pipeline,
        launch_codex=True,
        codex_runner=pipeline.codex,
        codex_model="gpt-5.6-terra",
        codex_reasoning_effort="ultra",
        codex_service_tier="fast",
    )

    codex_call = pipeline.codex_calls[0]
    assert codex_call["model"] == "gpt-5.6-terra"
    assert codex_call["reasoning_effort"] == "ultra"
    assert codex_call["service_tier"] == "priority"
    assert result["stages"]["codex"]["settings"] == {
        "model": "gpt-5.6-terra",
        "reasoning_effort": "ultra",
        "service_tier": "priority",
    }


def test_standard_tier_binds_default_effective_value_for_safe_resume() -> None:
    requested = {
        "model": None,
        "reasoning_effort": None,
        "service_tier": daily_runner.DEFAULT_CODEX_SERVICE_TIER,
    }
    existing = {
        "requested_settings": requested,
        "settings": {
            "model": "gpt-5.6-sol",
            "reasoning_effort": "xhigh",
            "service_tier": "default",
        },
    }

    launch, bound = daily_runner._bound_codex_settings(
        existing,
        requested,
        thread_id="thread-1",
    )

    assert bound == requested
    assert launch == {
        "model": "gpt-5.6-sol",
        "reasoning_effort": "xhigh",
        "service_tier": daily_runner.DEFAULT_CODEX_SERVICE_TIER,
    }


def test_resume_rejects_different_explicit_codex_settings_before_runner(
    tmp_path,
) -> None:
    pipeline = _Pipeline()
    db_path = tmp_path / "editorial.db"

    def interrupted(**kwargs: Any) -> None:
        kwargs["checkpoint"](
            {
                "status": "running",
                "thread_id": "thread-1",
                "settings": {
                    "model": kwargs["model"],
                    "reasoning_effort": kwargs["reasoning_effort"],
                    "service_tier": (
                        "default"
                        if kwargs["service_tier"]
                        == daily_runner.DEFAULT_CODEX_SERVICE_TIER
                        else kwargs["service_tier"]
                    ),
                },
            }
        )
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        _run(
            db_path=db_path,
            pipeline=pipeline,
            launch_codex=True,
            codex_runner=interrupted,
            codex_model="gpt-5.6-sol",
            codex_reasoning_effort="xhigh",
            codex_service_tier="fast",
        )

    with pytest.raises(daily_runner.DailyRunError) as raised:
        _run(
            db_path=db_path,
            pipeline=pipeline,
            launch_codex=True,
            codex_runner=lambda **_: pytest.fail("must not touch the existing task"),
            codex_model="gpt-5.6-terra",
        )

    assert raised.value.code == "E_CODEX_CONFIG_MISMATCH"
    assert pipeline.order == ["evidence", "routing", "prepare"]


def test_top_level_thread_without_settings_fails_before_resume(tmp_path) -> None:
    pipeline = _Pipeline()
    db_path = tmp_path / "editorial.db"
    prepared = _run(db_path=db_path, pipeline=pipeline)
    conn = daily_runner.connect(db_path)
    with conn:
        conn.execute(
            "UPDATE daily_orchestration_run SET codex_thread_id = ? WHERE run_id = ?",
            ("legacy-thread", prepared["run_id"]),
        )
    conn.close()

    with pytest.raises(daily_runner.DailyRunError) as raised:
        _run(
            db_path=db_path,
            pipeline=pipeline,
            launch_codex=True,
            codex_runner=lambda **_: pytest.fail("must not resume unknown settings"),
        )

    assert raised.value.code == "E_CODEX_SETTINGS_UNKNOWN"
    assert pipeline.order == ["evidence", "routing", "prepare"]


def test_partial_final_codex_settings_fail_closed(tmp_path) -> None:
    pipeline = _Pipeline()
    db_path = tmp_path / "editorial.db"

    def partial_result(**_: Any) -> dict[str, Any]:
        return {
            "status": "complete",
            "thread_id": "thread-1",
            "goal_status": "complete",
            "settings": {"model": "gpt-5.6-sol"},
        }

    with pytest.raises(daily_runner.DailyRunError) as raised:
        _run(
            db_path=db_path,
            pipeline=pipeline,
            launch_codex=True,
            codex_runner=partial_result,
        )

    assert raised.value.code == "E_CODEX_SETTINGS_INVALID"
    stored = daily_runner.inspect_run(db_path=db_path, day=DAY)
    assert stored["status"] == "failed"
    assert stored["error"]["code"] == "E_CODEX_SETTINGS_INVALID"


def test_imported_run_closes_checkpoint_without_resuming_reused_task(
    tmp_path, monkeypatch
) -> None:
    pipeline = _Pipeline()
    db_path = tmp_path / "editorial.db"
    imported_run_id: str | None = None

    def latest_editorial_run(*, workspace_run_id: str, **_: Any) -> str | None:
        assert workspace_run_id == WORKSPACE_RUN_ID
        return imported_run_id

    monkeypatch.setattr(daily_runner, "_latest_editorial_run", latest_editorial_run)

    def interrupted_task(**kwargs: Any) -> None:
        kwargs["checkpoint"](
            {
                "status": "running",
                "thread_id": "thread-reused-by-user",
                "goal_status": "active",
                "turn_id": "turn-original",
                "settings": {
                    "model": kwargs["model"] or "gpt-5.6-sol",
                    "reasoning_effort": kwargs["reasoning_effort"] or "xhigh",
                    "service_tier": (
                        "default"
                        if kwargs["service_tier"]
                        == daily_runner.DEFAULT_CODEX_SERVICE_TIER
                        else kwargs["service_tier"]
                    ),
                },
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

    imported_run_id = "editorial-run-imported"
    resumed = _run(
        db_path=db_path,
        pipeline=pipeline,
        launch_codex=True,
        codex_runner=lambda **_: pytest.fail("must not resume a reused task"),
    )

    assert resumed["status"] == "complete"
    assert resumed["editorial_run_id"] == imported_run_id
    assert resumed["codex_thread_id"] == "thread-reused-by-user"
    assert resumed["stages"]["codex"] == {
        "status": "complete",
        "thread_id": "thread-reused-by-user",
        "completion_source": "editorial_run",
        "requested_settings": {
            "model": None,
            "reasoning_effort": None,
            "service_tier": daily_runner.DEFAULT_CODEX_SERVICE_TIER,
        },
        "settings": {
            "model": "gpt-5.6-sol",
            "reasoning_effort": "xhigh",
            "service_tier": "default",
        },
    }


def test_custom_store_import_closes_run_without_opening_codex(tmp_path) -> None:
    pipeline = _Pipeline()
    db_path = tmp_path / "custom-editorial.db"
    _run(db_path=db_path, pipeline=pipeline)

    conn = editorial_runs.connect(db_path)
    with conn:
        conn.execute(
            """INSERT INTO editorial_run (
                   run_id, schema_version, draft_schema_version, day,
                   workspace_run_id, workspace_manifest_sha256,
                   source_routing_run_id, source_routing_db,
                   source_cohort_sha256, source_event_run_id,
                   source_feed_run_id, skill_version, executor_model,
                   executor_notes, result_sha256, result_json,
                   candidate_count, candidate_pair_count, insight_count,
                   citation_count, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, 'complete', ?)""",
            (
                "editorial-custom",
                editorial_runs.STORE_SCHEMA_VERSION,
                editorial.DRAFT_SCHEMA_VERSION,
                DAY,
                WORKSPACE_RUN_ID,
                "manifest-sha-1",
                ROUTING_RUN_ID,
                "routing.db",
                "cohort-sha",
                EVENT_RUN_ID,
                FEED_RUN_ID,
                "skill-v1",
                "codex-test",
                None,
                "result-sha",
                "{}",
                8,
                11,
                1,
                1,
                "2026-07-18T10:00:00+00:00",
            ),
        )
    conn.close()

    result = _run(
        db_path=db_path,
        pipeline=pipeline,
        launch_codex=True,
        codex_runner=lambda **_: pytest.fail("must not open Codex"),
    )

    assert result["status"] == "complete"
    assert result["editorial_run_id"] == "editorial-custom"
    assert result["codex_thread_id"] is None
    assert result["stages"]["codex"] == {
        "status": "complete",
        "completion_source": "editorial_run",
    }


def test_day_lock_rejects_concurrent_runner_before_any_stage(tmp_path) -> None:
    pipeline = _Pipeline()
    db_path = tmp_path / "editorial.db"
    lock = daily_runner._acquire_day_lock(db_path, DAY)
    try:
        with pytest.raises(daily_runner.DailyRunError) as raised:
            _run(db_path=db_path, pipeline=pipeline)
    finally:
        daily_runner._release_day_lock(lock)

    assert raised.value.code == "E_RUN_BUSY"
    assert raised.value.retryable is True
    assert pipeline.order == []


def test_day_locks_allow_different_dates_to_run_independently(tmp_path) -> None:
    db_path = tmp_path / "editorial.db"
    first = daily_runner._acquire_day_lock(db_path, "2026-07-16")
    try:
        second = daily_runner._acquire_day_lock(db_path, "2026-07-17")
        daily_runner._release_day_lock(second)
    finally:
        daily_runner._release_day_lock(first)


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
            "requested_settings": {
                "model": None,
                "reasoning_effort": None,
                "service_tier": daily_runner.DEFAULT_CODEX_SERVICE_TIER,
        },
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
                "codex_settings": {
                    "model": None,
                    "reasoning_effort": None,
                    "service_tier": daily_runner.DEFAULT_CODEX_SERVICE_TIER,
                },
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
