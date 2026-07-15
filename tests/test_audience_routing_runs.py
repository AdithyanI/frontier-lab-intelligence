import json

import pytest

from fli import artifacts, audience_routing_runs
from fli.web import events as event_store


def test_freeze_run_reads_ranked_evidence_without_triage(tmp_path, monkeypatch):
    artifact_db = tmp_path / "artifacts.db"
    artifacts.connect(artifact_db).close()
    item = {
        "event_id": "event-1",
        "daily_rank": 3,
        "snapshot_content_sha256": "snapshot-1",
        "root": {
            "post_id": "post-1",
            "author": {"handle": "alice"},
            "text": "A concrete primary-source result.",
            "url": "https://x.com/alice/status/post-1",
        },
        "evidence": [
            {
                "post_id": "post-2",
                "author": {"handle": "bob"},
                "text": "An independently authored reaction.",
                "relationship": "quote",
                "same_author_as_root": False,
            },
            {
                "post_id": "post-3",
                "author": {"handle": "alice"},
                "text": "RT @bob: An independently authored reaction.",
                "relationship": "retweet",
                "same_author_as_root": True,
            },
        ],
    }
    monkeypatch.setattr(
        event_store,
        "events_payload",
        lambda **_: {
            "available": True,
            "run": {"run_id": "event-run-1", "feed_run_id": "feed-run-1"},
            "items": [item],
        },
    )

    conn = audience_routing_runs.connect_run(tmp_path / "routing.db")
    count = audience_routing_runs.freeze_run(
        conn,
        run_id="direct-run-1",
        day="2026-07-12",
        top_ranked=1,
        event_id=None,
        artifact_db=artifact_db,
        model="gpt-5.6-luna",
        effort="medium",
    )

    meta = conn.execute("SELECT * FROM run_meta").fetchone()
    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(run_meta)").fetchall()
    }
    item_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(routing_item)").fetchall()
    }
    frozen = conn.execute("SELECT * FROM routing_item").fetchone()
    conn.close()

    assert count == 1
    assert meta["source_event_run_id"] == "event-run-1"
    assert meta["source_feed_run_id"] == "feed-run-1"
    assert meta["selection_kind"] == "top_ranked"
    assert meta["selection_limit"] == 1
    assert "source_triage_db" not in columns
    assert "source_triage_run_id" not in columns
    assert "prompt_cache_key" not in item_columns
    assert frozen["event_id"] == "event-1"
    assert frozen["feed_rank"] == 3
    packet = json.loads(frozen["packet_json"])
    assert [source["relation"] for source in packet["sources"]] == ["root", "quote"]


def _refresh_summary(day: str) -> dict:
    return {
        "run": {"day": day},
        "counts": {
            "total": 1,
            "complete": 1,
            "failed": 0,
            "ai_engineering_only": 0,
            "investment_only": 0,
            "both": 1,
            "neither": 0,
            "input_tokens": 2_000,
            "cached_tokens": 1_024,
            "cache_write_tokens": 0,
            "output_tokens": 100,
            "reported_cost_usd": 0.01,
            "reported_cost_count": 1,
            "cache_eligible_requests": 1,
            "cache_hit_requests": 1,
        },
    }


def test_refresh_dry_run_freezes_one_published_source_without_writes(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        audience_routing_runs,
        "_published_event_source",
        lambda: {"event_run_id": "event-run-abcdef", "feed_run_id": "feed-run-1"},
    )
    monkeypatch.setattr(
        audience_routing_runs,
        "_execute_refresh_day",
        lambda *args, **kwargs: pytest.fail("dry-run must not execute routing"),
    )

    result = audience_routing_runs.refresh_all_days(
        through="2026-07-07",
        days=3,
        top_ranked=100,
        dry_run=True,
        run_root=tmp_path / "routing",
    )

    assert result["dry_run"] is True
    assert result["will_call_model"] is False
    assert [item["day"] for item in result["plan"]] == [
        "2026-07-05",
        "2026-07-06",
        "2026-07-07",
    ]
    assert all("event-run-ab" in item["run_id"] for item in result["plan"])
    assert not (tmp_path / "routing").exists()


def test_refresh_replaces_old_runs_only_after_every_day_completes(
    tmp_path, monkeypatch
):
    run_root = tmp_path / "routing"
    (run_root / "old-run").mkdir(parents=True)
    source = {"event_run_id": "event-run-abcdef", "feed_run_id": "feed-run-1"}
    monkeypatch.setattr(audience_routing_runs, "_published_event_source", lambda: source)

    def execute(item, **kwargs):
        (kwargs["run_root"] / item["run_id"]).mkdir(parents=True)
        return _refresh_summary(item["day"])

    monkeypatch.setattr(audience_routing_runs, "_execute_refresh_day", execute)

    result = audience_routing_runs.refresh_all_days(
        through="2026-07-06",
        days=2,
        top_ranked=1,
        workers=2,
        day_workers=2,
        replace=True,
        run_root=run_root,
    )

    assert result["counts"]["complete"] == 2
    assert result["counts"]["both"] == 2
    assert result["counts"]["cache_hit_requests"] == 2
    assert result["counts"]["reported_cost_usd"] == pytest.approx(0.02)
    assert result["pruned_runs"] == ["old-run"]
    assert not (run_root / "old-run").exists()
    assert {path.name for path in run_root.iterdir()} == {
        item["run_id"] for item in result["plan"]
    }


def test_refresh_failure_retains_old_runs_for_retry(tmp_path, monkeypatch):
    run_root = tmp_path / "routing"
    (run_root / "old-run").mkdir(parents=True)
    monkeypatch.setattr(
        audience_routing_runs,
        "_published_event_source",
        lambda: {"event_run_id": "event-run-abcdef", "feed_run_id": "feed-run-1"},
    )

    def execute(item, **kwargs):
        if item["day"] == "2026-07-06":
            raise RuntimeError("model call failed")
        (kwargs["run_root"] / item["run_id"]).mkdir(parents=True)
        return _refresh_summary(item["day"])

    monkeypatch.setattr(audience_routing_runs, "_execute_refresh_day", execute)

    with pytest.raises(RuntimeError, match="2026-07-06.*model call failed"):
        audience_routing_runs.refresh_all_days(
            through="2026-07-06",
            days=2,
            top_ranked=1,
            workers=1,
            day_workers=2,
            replace=True,
            run_root=run_root,
        )

    assert (run_root / "old-run").is_dir()
