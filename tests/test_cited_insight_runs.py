import json
import sqlite3

import pytest

from fli import cited_insight_runs, cited_insights


class FakeClient:
    pass


def seed_frozen_run(conn: sqlite3.Connection):
    packet = cited_insights.InsightInput(
        event_id="event-1",
        day="2026-07-11",
        current_rank=1,
        sources=(
            cited_insights.EvidenceSource(
                source_type="x_post",
                source_id="post-1",
                url="https://x.com/author/status/post-1",
                author="@author",
                relation="root",
                text="A concrete source statement.",
            ),
        ),
    )
    payload = cited_insight_runs._packet_payload(packet)
    now = "2026-07-14T12:00:00+00:00"
    conn.execute(
        """INSERT INTO run_meta
           (singleton, run_id, day, model, reasoning_effort,
            prompt_version, prompt_sha256, schema_version,
            source_triage_db, source_artifact_db, event_ids_json,
            cohort_sha256, expected_count, created_at, updated_at)
           VALUES (1, 'oracle', '2026-07-11', 'gpt-5.4-mini', 'medium',
                   ?, ?, ?, 'triage.db', 'artifacts.db', '["event-1"]',
                   'cohort', 1, ?, ?)""",
        (
            cited_insights.PROMPT_VERSION,
            cited_insights.prompt_sha256(),
            cited_insights.SCHEMA_VERSION,
            now,
            now,
        ),
    )
    conn.execute(
        """INSERT INTO insight_item
           (event_id, day, current_rank, packet_json, input_text,
            input_sha256, prompt_cache_key, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            packet.event_id,
            packet.day,
            packet.current_rank,
            json.dumps(payload),
            cited_insights.render_input(packet),
            packet.input_sha256,
            cited_insights.prompt_cache_key(packet.event_id),
            now,
        ),
    )
    conn.commit()


def test_run_is_resumable_and_persists_application_bound_citation(tmp_path, monkeypatch):
    conn = cited_insight_runs.connect_run(tmp_path / "insights.db")
    seed_frozen_run(conn)
    calls = []

    def fake_evaluate(_client, packet, **_kwargs):
        calls.append(packet.event_id)
        return {
            "outcome": "insight",
            "claim": "The author made a concrete statement.",
            "why_it_matters": "It is inspectable.",
            "investment_implication": "It may matter if validated.",
            "engineering_implication": "Engineers can inspect it.",
            "supporting_quote": "A concrete source statement.",
            "citation": cited_insights.bind_citation(
                packet, "A concrete source statement."
            ),
            "response_id": "resp-1",
            "response_model": "gpt-5.4-mini",
            "input_tokens": 1_500,
            "cached_tokens": 1_024,
            "cache_write_tokens": 0,
            "output_tokens": 100,
            "reported_cost_usd": 0.01,
            "request_tags": ["app:frontier-lab-intelligence"],
        }

    monkeypatch.setattr(cited_insights, "evaluate_one", fake_evaluate)

    first = cited_insight_runs.run_pending(conn, client=FakeClient())
    second = cited_insight_runs.run_pending(conn, client=FakeClient())
    row = conn.execute("SELECT * FROM insight_item").fetchone()

    assert calls == ["event-1"]
    assert first["counts"]["complete"] == 1
    assert second["counts"]["complete"] == 1
    assert row["citation_source_id"] == "post-1"
    assert row["citation_source_url"] == "https://x.com/author/status/post-1"
    assert row["supporting_quote"] == "A concrete source statement."


def test_freeze_is_idempotent_and_refuses_changed_source_cohort(tmp_path):
    triage_db = tmp_path / "triage.db"
    triage = sqlite3.connect(triage_db)
    triage.execute(
        """CREATE TABLE triage_item (
               event_id TEXT PRIMARY KEY, current_rank INTEGER,
               envelope_json TEXT, status TEXT, decision TEXT
           )"""
    )
    envelope = {
        "day": "2026-07-11",
        "event_id": "event-1",
        "root": {
            "post_id": "post-1",
            "author": "@author",
            "text": "A source statement.",
        },
        "related_posts": [],
    }
    triage.execute(
        "INSERT INTO triage_item VALUES (?, 1, ?, 'complete', 'keep')",
        ("event-1", json.dumps(envelope)),
    )
    triage.commit()
    triage.close()

    artifact_db = tmp_path / "artifacts.db"
    artifact = sqlite3.connect(artifact_db)
    artifact.executescript(
        """CREATE TABLE artifact_import_candidate (
               event_id TEXT, decision TEXT, artifact_id TEXT
           );
           CREATE TABLE artifact (
               artifact_id TEXT, canonical_url TEXT, title TEXT
           );
           CREATE TABLE artifact_fetch (
               fetch_id TEXT, artifact_id TEXT, status TEXT,
               text_snapshot_ref TEXT, completed_at TEXT
           );"""
    )
    artifact.commit()
    artifact.close()

    conn = cited_insight_runs.connect_run(tmp_path / "run" / "insights.db")
    assert cited_insight_runs.freeze_run(
        conn,
        run_id="oracle",
        event_ids=("event-1",),
        triage_db=triage_db,
        artifact_db=artifact_db,
    ) == 1
    assert cited_insight_runs.freeze_run(
        conn,
        run_id="oracle",
        event_ids=("event-1",),
        triage_db=triage_db,
        artifact_db=artifact_db,
    ) == 1
    assert conn.execute("SELECT COUNT(*) FROM insight_item").fetchone()[0] == 1

    triage = sqlite3.connect(triage_db)
    changed = {**envelope, "root": {**envelope["root"], "text": "Changed."}}
    triage.execute(
        "UPDATE triage_item SET envelope_json = ? WHERE event_id = 'event-1'",
        (json.dumps(changed),),
    )
    triage.commit()
    triage.close()
    with pytest.raises(ValueError, match="cohort_sha256"):
        cited_insight_runs.freeze_run(
            conn,
            run_id="oracle",
            event_ids=("event-1",),
            triage_db=triage_db,
            artifact_db=artifact_db,
        )
