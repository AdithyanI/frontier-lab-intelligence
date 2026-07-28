import json
import sqlite3

import pytest

from fli.evidence.artifacts import store as artifacts
from fli.routing import runs as routing_runs
from fli.scoring import attention
from fli.web import developments as development_store


def test_connect_run_rejects_legacy_storage_without_rank_lineage(tmp_path):
    db = tmp_path / "routing-v1.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        routing_runs.RUN_SCHEMA.replace(
            "semantic_snapshot_sha256", "snapshot_content_sha256"
        )
        .replace("    rank_version TEXT NOT NULL,\n", "")
        .replace(
            "    source_rank_input_sha256 TEXT NOT NULL\n"
            "        CHECK (length(source_rank_input_sha256) = 64),\n",
            "",
        )
    )
    conn.execute(
        """INSERT INTO run_meta (
               singleton, run_id, day, model, reasoning_effort,
               prompt_version, prompt_sha256, schema_version,
               source_event_run_id, source_feed_run_id, source_artifact_db,
               selection_kind, selection_limit, requested_event_id,
               cohort_sha256, expected_count, created_at, updated_at)
           VALUES (1, 'run-1', '2026-07-15', 'model', 'high',
                   'prompt', 'prompt-sha', 'schema', 'events', 'feed',
                   'artifacts.db', 'top_ranked', 1, NULL,
                   'legacy-cohort', 1, 'created', 'updated')"""
    )
    conn.execute(
        """INSERT INTO routing_item (
               event_id, feed_rank, root_url, snapshot_content_sha256,
               packet_json, evidence_sha256, input_text, input_sha256,
               updated_at)
           VALUES ('event-1', 1, 'https://x.com/a/status/1', 'snapshot-sha',
                   '{}', 'evidence-sha', 'input', 'input-sha', 'updated')"""
    )
    conn.commit()
    conn.close()

    assert routing_runs.migrate_run_storage(db) is False
    with pytest.raises(RuntimeError, match="predates rank-input lineage"):
        routing_runs.connect_run(db)


def test_freeze_run_reads_ranked_evidence_without_triage(tmp_path, monkeypatch):
    artifact_db = tmp_path / "artifacts.db"
    artifacts.connect(artifact_db).close()
    item = {
        "development_id": "development-1",
        "source_event_ids": ["event-1"],
        "daily_rank": 3,
        "semantic_snapshot_sha256": "snapshot-1",
        "source_events": [
            {
                "event_id": "event-1",
                "is_primary": True,
                "post": {
                    "post_id": "post-1",
                    "author": {"handle": "alice"},
                    "text": "A concrete primary-source result.",
                    "url": "https://x.com/alice/status/post-1",
                    "published_at": "2026-07-12T08:00:00+00:00",
                },
                "evidence": [
                    {
                        "post_id": "post-2",
                        "author": {"handle": "bob"},
                        "text": "An independently authored reaction.",
                        "relationship": "quote",
                        "published_at": "2026-07-12T09:00:00+00:00",
                    },
                    {
                        "post_id": "post-3",
                        "author": {"handle": "alice"},
                        "text": "RT @bob: An independently authored reaction.",
                        "relationship": "retweet",
                        "published_at": "2026-07-12T10:00:00+00:00",
                    },
                    {
                        "post_id": "post-4",
                        "author": {"handle": "alice"},
                        "text": "My additional first-party interpretation.",
                        "relationship": "quote",
                        "published_at": "2026-07-12T11:00:00+00:00",
                    },
                ],
            },
        ],
    }
    event_requests = []

    def developments_payload(**kwargs):
        event_requests.append(kwargs)
        return {
            "available": True,
            "run": {"run_id": "event-run-1", "feed_run_id": "feed-run-1"},
            "rank_contract": {"input_sha256": "a" * 64},
            "items": [item],
        }

    monkeypatch.setattr(
        development_store,
        "developments_payload",
        developments_payload,
    )

    conn = routing_runs.connect_run(tmp_path / "routing.db")
    count = routing_runs.freeze_run(
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
    assert meta["source_rank_input_sha256"] == "a" * 64
    assert meta["selection_kind"] == "top_ranked"
    assert meta["selection_limit"] == 1
    assert "source_triage_db" not in columns
    assert "source_triage_run_id" not in columns
    assert "prompt_cache_key" not in item_columns
    assert frozen["event_id"] == "development-1"
    assert frozen["feed_rank"] == 3
    assert frozen["status"] == "pending"
    assert event_requests[0]["limit"] == 1
    packet = json.loads(frozen["packet_json"])
    assert [source["relation"] for source in packet["sources"]] == [
        "root",
        "same_author_continuation",
    ]


def test_freeze_run_completes_short_unsupported_text_without_model(
    tmp_path, monkeypatch
):
    artifact_db = tmp_path / "artifacts.db"
    artifacts.connect(artifact_db).close()
    item = {
        "development_id": "development-short",
        "source_event_ids": ["event-short"],
        "daily_rank": 7,
        "semantic_snapshot_sha256": "snapshot-short",
        "source_events": [
            {
                "event_id": "event-short",
                "is_primary": True,
                "post": {
                    "post_id": "post-short",
                    "author": {"handle": "alice"},
                    "text": "GPT-5.6 admitted that it lied to me.",
                    "published_at": "2026-07-12T08:00:00+00:00",
                },
                "evidence": [],
            },
        ],
    }

    monkeypatch.setattr(
        development_store,
        "developments_payload",
        lambda **_kwargs: {
            "available": True,
            "run": {"run_id": "event-run-1", "feed_run_id": "feed-run-1"},
            "rank_contract": {"input_sha256": "a" * 64},
            "items": [item],
        },
    )

    conn = routing_runs.connect_run(tmp_path / "routing.db")
    routing_runs.freeze_run(
        conn,
        run_id="direct-run-short",
        day="2026-07-12",
        top_ranked=1,
        event_id=None,
        artifact_db=artifact_db,
        model="gpt-5.6-luna",
        effort="medium",
    )
    frozen = conn.execute("SELECT * FROM routing_item").fetchone()
    result = routing_runs.summary(conn)
    conn.close()

    assert frozen["status"] == "complete"
    assert frozen["attempts"] == 0
    assert frozen["ai_engineering_relevant"] == 0
    assert frozen["investment_relevant"] == 0
    assert frozen["ai_engineering_reason"].startswith("Suppressed —")
    assert frozen["investment_reason"] == frozen["ai_engineering_reason"]
    assert frozen["response_id"] is None
    assert frozen["response_model"] == (
        "deterministic-evidence-gate-v1:short_unsupported_text"
    )
    assert frozen["input_tokens"] == 0
    assert frozen["output_tokens"] == 0
    assert result["counts"]["deterministic_short_text_filtered"] == 1
    assert result["counts"]["deterministic_unavailable_evidence_filtered"] == 0
    assert result["counts"]["deterministic_filtered"] == 1


def test_packet_promotes_a_current_author_update_when_root_is_old(tmp_path):
    artifact_db = tmp_path / "artifacts.db"
    artifact_conn = artifacts.connect(artifact_db)
    item = {
        "development_id": "development-current-update",
        "source_event_ids": ["event-current-update"],
        "source_events": [{
            "event_id": "event-current-update",
            "is_primary": True,
            "post": {
                "post_id": "old-root",
                "author": {
                    "handle": "alice",
                    "entity_name": "Alice Example",
                },
                "text": "A year-old announcement.",
                "published_at": "2025-07-15T12:00:00+00:00",
            },
            "evidence": [
            {
                "post_id": "current-update",
                "author": {
                    "handle": "alice",
                    "entity_name": "Alice Example",
                },
                "text": "Here is what changed today.",
                "relationship": "quote",
                "same_author_as_root": True,
                "published_at": "2026-07-10T12:00:00+00:00",
            },
            {
                "post_id": "current-reaction",
                "author": {"handle": "bob"},
                "text": "A current reaction.",
                "relationship": "quote",
                "same_author_as_root": False,
                "published_at": "2026-07-10T13:00:00+00:00",
            },
            ],
        }],
    }

    packet = routing_runs.packet_from_development(
        item,
        day="2026-07-10",
        artifact_conn=artifact_conn,
    )
    artifact_conn.close()

    assert packet is not None
    assert [source.source_id for source in packet.sources] == ["current-update"]
    assert packet.sources[0].relation == "root"
    assert packet.sources[0].author == "Alice Example"
    assert packet.sources[0].url == "https://x.com/alice/status/current-update"


def test_packet_excludes_an_event_with_only_an_old_first_party_source(tmp_path):
    artifact_conn = artifacts.connect(tmp_path / "artifacts.db")
    packet = routing_runs.packet_from_development(
        {
            "development_id": "development-old-only",
            "source_event_ids": ["event-old-only"],
            "source_events": [{
                "event_id": "event-old-only",
                "is_primary": True,
                "post": {
                    "post_id": "old-root",
                    "author": {"handle": "alice"},
                    "text": "Old announcement.",
                    "published_at": "2025-11-19T12:00:00+00:00",
                },
                "evidence": [],
            }],
        },
        day="2026-07-14",
        artifact_conn=artifact_conn,
    )
    artifact_conn.close()

    assert packet is None


def test_selective_refresh_reuses_only_exact_complete_inputs(tmp_path):
    source = routing_runs.connect_run(tmp_path / "source.db")
    target = routing_runs.connect_run(tmp_path / "target.db")
    now = "2026-07-17T00:00:00+00:00"

    def seed_meta(conn, run_id, cohort_sha):
        conn.execute(
            """INSERT INTO run_meta
               (singleton, run_id, day, model, reasoning_effort,
                prompt_version, prompt_sha256, schema_version, rank_version,
                source_rank_input_sha256,
                source_event_run_id, source_feed_run_id, source_artifact_db,
                selection_kind, selection_limit, requested_event_id,
                cohort_sha256, expected_count, created_at, updated_at)
               VALUES (1, ?, '2026-07-15', 'model', 'high', 'prompt',
                       'prompt-sha', 'schema', ?, ?, 'events', 'feed', 'artifacts.db',
                       'top_ranked', 2, NULL, ?, 2, ?, ?)""",
            (
                run_id,
                attention.DAILY_RANK_VERSION,
                "a" * 64,
                cohort_sha,
                now,
                now,
            ),
        )

    def seed_item(conn, event_id, input_sha, *, complete=False):
        conn.execute(
            """INSERT INTO routing_item
               (event_id, feed_rank, root_url, semantic_snapshot_sha256,
                packet_json, evidence_sha256, input_text, input_sha256,
                status, attempts, ai_engineering_relevant,
                ai_engineering_reason, investment_relevant,
                investment_reason, raw_output_text, response_id,
                response_model, input_tokens, cached_tokens,
                cache_write_tokens, output_tokens, reported_cost_usd,
                request_tags_json, completed_at, updated_at)
               VALUES (?, ?, 'https://x.com/a/status/1', 'snapshot', '{}',
                       'evidence', 'input', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?, ?, ?)""",
            (
                event_id,
                1 if event_id == "same" else 2,
                input_sha,
                "complete" if complete else "pending",
                1 if complete else 0,
                1 if complete else None,
                "engineering" if complete else None,
                0 if complete else None,
                "investment" if complete else None,
                "raw" if complete else None,
                "response" if complete else None,
                "model" if complete else None,
                100 if complete else None,
                20 if complete else None,
                0 if complete else None,
                10 if complete else None,
                0.01 if complete else None,
                '{"run":"source"}' if complete else None,
                now if complete else None,
                now,
            ),
        )

    seed_meta(source, "source", "old-cohort")
    seed_meta(target, "target", "new-cohort")
    seed_item(source, "same", "same-input", complete=True)
    seed_item(source, "changed", "old-input", complete=True)
    seed_item(target, "same", "same-input")
    seed_item(target, "changed", "new-input")

    assert routing_runs.reuse_exact_results(target, source) == 1
    same = target.execute(
        "SELECT * FROM routing_item WHERE event_id = 'same'"
    ).fetchone()
    changed = target.execute(
        "SELECT * FROM routing_item WHERE event_id = 'changed'"
    ).fetchone()
    source.close()
    target.close()

    assert same["status"] == "complete"
    assert same["reused_from_run_id"] == "source"
    assert same["response_id"] == "response"
    assert changed["status"] == "pending"
    assert changed["reused_from_run_id"] is None


def test_exact_reuse_crosses_publications_and_keeps_target_provenance(tmp_path):
    source = routing_runs.connect_run(tmp_path / "source.db")
    target = routing_runs.connect_run(tmp_path / "target.db")
    now = "2026-07-18T00:00:00+00:00"

    def seed_meta(
        conn,
        *,
        run_id,
        event_run_id,
        feed_run_id,
        expected_count,
    ):
        conn.execute(
            """INSERT INTO run_meta
               (singleton, run_id, day, model, reasoning_effort,
                prompt_version, prompt_sha256, schema_version, rank_version,
                source_rank_input_sha256,
                source_event_run_id, source_feed_run_id, source_artifact_db,
                selection_kind, selection_limit, requested_event_id,
                cohort_sha256, expected_count, created_at, updated_at)
               VALUES (1, ?, '2026-07-16', 'model', 'high', 'prompt',
                       'prompt-sha', 'schema', ?, ?, ?, ?, 'artifacts.db',
                       'top_ranked', 100, NULL, ?, ?, ?, ?)""",
            (
                run_id,
                attention.DAILY_RANK_VERSION,
                "a" * 64,
                event_run_id,
                feed_run_id,
                f"cohort-{run_id}",
                expected_count,
                now,
                now,
            ),
        )

    def seed_item(
        conn,
        *,
        event_id,
        rank,
        evidence_sha,
        input_sha,
        complete=False,
        semantic_sha="target-semantic",
    ):
        conn.execute(
            """INSERT INTO routing_item
               (event_id, feed_rank, root_url, semantic_snapshot_sha256,
                packet_json, evidence_sha256, input_text, input_sha256,
                status, attempts, ai_engineering_relevant,
                ai_engineering_reason, investment_relevant,
                investment_reason, raw_output_text, response_id,
                response_model, input_tokens, cached_tokens,
                cache_write_tokens, output_tokens, reported_cost_usd,
                request_tags_json, completed_at, updated_at)
               VALUES (?, ?, 'https://x.com/a/status/1', ?, '{}', ?, 'input', ?,
                       ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event_id,
                rank,
                semantic_sha,
                evidence_sha,
                input_sha,
                "complete" if complete else "pending",
                1 if complete else 0,
                1 if complete else None,
                "engineering" if complete else None,
                0 if complete else None,
                "investment" if complete else None,
                "raw" if complete else None,
                "response" if complete else None,
                "model" if complete else None,
                100 if complete else None,
                20 if complete else None,
                0 if complete else None,
                10 if complete else None,
                0.01 if complete else None,
                '{"run":"source"}' if complete else None,
                now if complete else None,
                now,
            ),
        )

    seed_meta(
        source,
        run_id="source",
        event_run_id="events-old",
        feed_run_id="feed-old",
        expected_count=2,
    )
    seed_meta(
        target,
        run_id="target",
        event_run_id="events-new",
        feed_run_id="feed-new",
        expected_count=3,
    )
    seed_item(
        source,
        event_id="same",
        rank=9,
        evidence_sha="evidence-same",
        input_sha="input-same",
        complete=True,
        semantic_sha="source-semantic",
    )
    seed_item(
        source,
        event_id="changed",
        rank=10,
        evidence_sha="evidence-old",
        input_sha="input-same",
        complete=True,
    )
    seed_item(
        target,
        event_id="same",
        rank=1,
        evidence_sha="evidence-same",
        input_sha="input-same",
        semantic_sha="target-semantic",
    )
    seed_item(
        target,
        event_id="changed",
        rank=2,
        evidence_sha="evidence-new",
        input_sha="input-same",
    )
    seed_item(
        target,
        event_id="new",
        rank=3,
        evidence_sha="evidence-new-event",
        input_sha="input-new-event",
    )

    assert routing_runs.reuse_exact_results(target, source) == 1
    reused = target.execute(
        "SELECT * FROM routing_item WHERE event_id = 'same'"
    ).fetchone()
    changed = target.execute(
        "SELECT * FROM routing_item WHERE event_id = 'changed'"
    ).fetchone()
    target_meta = target.execute("SELECT * FROM run_meta").fetchone()

    assert reused["status"] == "complete"
    assert reused["reused_from_run_id"] == "source"
    assert reused["feed_rank"] == 1
    assert reused["semantic_snapshot_sha256"] == "target-semantic"
    assert changed["status"] == "pending"
    assert target_meta["source_event_run_id"] == "events-new"
    assert target_meta["source_feed_run_id"] == "feed-new"

    target.execute("UPDATE run_meta SET prompt_sha256 = 'different-prompt'")
    with pytest.raises(ValueError, match="metadata differ: prompt_sha256"):
        routing_runs.reuse_exact_results(target, source)
    source.close()
    target.close()


def test_automatic_reuse_ignores_partial_and_incompatible_runs(
    tmp_path, monkeypatch
):
    run_root = tmp_path / "routing"
    target_db = run_root / "target" / "routing.db"
    source_db = run_root / "source" / "routing.db"
    partial_db = run_root / "partial" / "routing.db"
    incompatible_db = run_root / "incompatible" / "routing.db"
    now = "2026-07-18T00:00:00+00:00"

    def seed(path, *, run_id, prompt_sha="prompt-sha", complete=True):
        conn = routing_runs.connect_run(path)
        conn.execute(
            """INSERT INTO run_meta
               (singleton, run_id, day, model, reasoning_effort,
                prompt_version, prompt_sha256, schema_version, rank_version,
                source_rank_input_sha256,
                source_event_run_id, source_feed_run_id, source_artifact_db,
                selection_kind, selection_limit, requested_event_id,
                cohort_sha256, expected_count, created_at, updated_at)
               VALUES (1, ?, '2026-07-16', 'model', 'high', 'prompt', ?,
                       'schema', ?, ?, ?, ?, 'artifacts.db', 'top_ranked', 100, NULL,
                       ?, 1, ?, ?)""",
            (
                run_id,
                prompt_sha,
                attention.DAILY_RANK_VERSION,
                "a" * 64,
                f"events-{run_id}",
                f"feed-{run_id}",
                f"cohort-{run_id}",
                now,
                now,
            ),
        )
        conn.execute(
            """INSERT INTO routing_item
               (event_id, feed_rank, root_url, semantic_snapshot_sha256,
                packet_json, evidence_sha256, input_text, input_sha256,
                status, attempts, ai_engineering_relevant,
                ai_engineering_reason, investment_relevant,
                investment_reason, raw_output_text, response_id,
                response_model, input_tokens, cached_tokens,
                cache_write_tokens, output_tokens, reported_cost_usd,
                request_tags_json, completed_at, updated_at)
               VALUES ('event-1', 1, 'https://x.com/a/status/1', ?, '{}',
                       'evidence', 'input', 'input-sha', ?, ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                f"semantic-{run_id}",
                "complete" if complete else "pending",
                1 if complete else 0,
                1 if complete else None,
                "engineering" if complete else None,
                0 if complete else None,
                "investment" if complete else None,
                "raw" if complete else None,
                "response" if complete else None,
                "model" if complete else None,
                100 if complete else None,
                20 if complete else None,
                0 if complete else None,
                10 if complete else None,
                0.01 if complete else None,
                '{"run":"source"}' if complete else None,
                now if complete else None,
                now,
            ),
        )
        conn.commit()
        return conn

    source = seed(source_db, run_id="source")
    source.close()
    partial = seed(partial_db, run_id="partial", complete=False)
    partial.close()
    incompatible = seed(
        incompatible_db,
        run_id="incompatible",
        prompt_sha="other-prompt",
    )
    incompatible.close()
    target = seed(target_db, run_id="target", complete=False)
    target.close()
    monkeypatch.setattr(
        routing_runs.entity_kinds,
        "create_litellm_client",
        lambda: pytest.fail("exact reuse must avoid creating a model client"),
    )

    result = routing_runs._execute_refresh_day(
        {"run_id": "target", "day": "2026-07-16"},
        workers=4,
        run_root=run_root,
        packaging_duration_ms=3.0,
    )
    target = routing_runs.connect_run(target_db)
    row = target.execute("SELECT * FROM routing_item").fetchone()
    target.close()

    assert result["reused_exact_count"] == 1
    assert result["reuse_source_run_ids"] == ["source"]
    assert result["model_requests"] == 0
    assert result["incremental_telemetry"] == {
        "input_tokens": 0,
        "cached_tokens": 0,
        "cache_write_tokens": 0,
        "output_tokens": 0,
        "reported_cost_count": 0,
        "reported_cost_usd": 0.0,
    }
    assert result["counts"]["complete"] == 1
    assert row["status"] == "complete"
    assert row["reused_from_run_id"] == "source"


def test_artifact_sources_deduplicate_one_artifact_across_source_posts(
    tmp_path, monkeypatch
):
    artifact_db = tmp_path / "artifacts.db"
    text_ref = "text/artifact.txt"
    snapshot = tmp_path / text_ref
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text(
        "A substantive primary artifact that should appear exactly once.",
        encoding="utf-8",
    )
    conn = artifacts.connect(artifact_db)
    now = "2026-07-15T00:00:00+00:00"
    with conn:
        conn.execute(
            """INSERT INTO artifact_import_run
               (import_run_id, schema_version, canonicalization_contract,
                source_feed_run_id, source_event_run_id, triage_runs_json,
                selection_policy, input_fingerprint, expected_candidate_count,
                accepted_count, excluded_count, failed_count, created_at,
                completed_at)
               VALUES ('import', ?, 'test', 'feed', 'events', '[]', ?,
                       'fingerprint', 2, 2, 0, 0, ?, ?)""",
            (
                artifacts.SCHEMA_VERSION,
                artifacts.PRIMARY_AUTHOR_SELECTION_POLICY,
                now,
                now,
            ),
        )
        conn.execute(
            """INSERT INTO artifact
               (artifact_id, canonical_url, canonicalization_contract, host,
                artifact_kind, title, first_seen_at, last_seen_at, created_at,
                updated_at)
               VALUES ('artifact-1', 'https://example.com/research', 'test',
                       'example.com', 'article', 'Research result', ?, ?, ?, ?)""",
            (now, now, now, now),
        )
        for candidate_id, source_id, relation in (
            ("candidate-linked", "post-linked", "links_to"),
            ("candidate-self", "post-self", "self_publishes"),
        ):
            conn.execute(
                """INSERT INTO artifact_import_candidate
                   (candidate_id, import_run_id, event_day, event_id,
                    source_rank, day_candidate_count, source_kind,
                    source_provider, source_external_id,
                    source_snapshot_sha256, source_url,
                    disclosure_external_id, disclosure_snapshot_sha256,
                    disclosure_url, disclosure_published_at, observed_url,
                    expanded_url, candidate_source, relation, decision,
                    reason_code, artifact_id, created_at)
                   VALUES (?, 'import', '2026-07-15', 'event-1', 1, 100,
                           'x_post', 'twitterapi_io', ?, ?, ?, ?, ?, ?, ?,
                           'https://example.com/research',
                           'https://example.com/research', 'entity', ?,
                           'accepted', 'external_http_url', 'artifact-1', ?)""",
                (
                    candidate_id,
                    source_id,
                    f"snapshot-{source_id}",
                    f"https://x.com/alice/status/{source_id}",
                    source_id,
                    f"snapshot-{source_id}",
                    f"https://x.com/alice/status/{source_id}",
                    now,
                    relation,
                    now,
                ),
            )
        conn.execute(
            """INSERT INTO artifact_fetch_run
               (fetch_run_id, schema_version, fetch_policy, selection_policy,
                input_fingerprint, expected_count, success_count,
                failed_retryable_count, failed_terminal_count, started_at,
                completed_at, status)
               VALUES ('fetch-run', ?, 'test', 'test', 'fetch-fingerprint',
                       1, 1, 0, 0, ?, ?, 'complete')""",
            (artifacts.SCHEMA_VERSION, now, now),
        )
        conn.execute(
            """INSERT INTO artifact_fetch
               (fetch_id, fetch_run_id, artifact_id, fetch_policy,
                requested_url, request_key, status, attempt_number, started_at,
                completed_at, text_sha256, text_snapshot_ref, text_char_count,
                text_truncated, retryable)
               VALUES ('fetch', 'fetch-run', 'artifact-1', 'test',
                       'https://example.com/research', 'request', 'success', 1,
                       ?, ?, 'text-sha', ?, 63, 0, 0)""",
            (now, now, text_ref),
        )
    monkeypatch.setattr(routing_runs, "REPO_ROOT", tmp_path)

    sources = routing_runs._artifact_sources(
        conn,
        event_ids=["event-1"],
        post_authors={"post-self": "@alice", "post-linked": "@alice"},
        primary_author="@alice",
    )
    conn.close()

    assert len(sources) == 1
    assert sources[0].source_id == "artifact-1"
    assert sources[0].relation == "self_published_artifact"
    assert sources[0].author == "@alice"


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


def _stub_rank_identities(monkeypatch, source: dict[str, str]) -> None:
    monkeypatch.setattr(
        routing_runs,
        "_current_rank_identities",
        lambda days: {
            day: {
                "day": day,
                "rank_version": attention.DAILY_RANK_VERSION,
                "rank_input_sha256": "a" * 64,
                "event_run_id": source["event_run_id"],
                "feed_run_id": source["feed_run_id"],
            }
            for day in days
        },
    )


def test_refresh_dry_run_freezes_one_published_source_without_writes(
    tmp_path, monkeypatch
):
    source = {"event_run_id": "event-run-abcdef", "feed_run_id": "feed-run-1"}
    monkeypatch.setattr(
        routing_runs,
        "_published_event_source",
        lambda: source,
    )
    _stub_rank_identities(monkeypatch, source)
    monkeypatch.setattr(
        routing_runs,
        "_execute_refresh_day",
        lambda *args, **kwargs: pytest.fail("dry-run must not execute routing"),
    )
    monkeypatch.setattr(
        routing_runs,
        "_freeze_refresh_day",
        lambda *args, **kwargs: pytest.fail("dry-run must not freeze packets"),
    )

    result = routing_runs.refresh_all_days(
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
    monkeypatch.setattr(routing_runs, "_published_event_source", lambda: source)
    _stub_rank_identities(monkeypatch, source)
    frozen_days = []

    def freeze(item, **_kwargs):
        frozen_days.append(item["day"])
        return 4.0

    monkeypatch.setattr(routing_runs, "_freeze_refresh_day", freeze)

    def execute(item, **kwargs):
        assert frozen_days == ["2026-07-05", "2026-07-06"]
        (kwargs["run_root"] / item["run_id"]).mkdir(parents=True)
        return {
            **_refresh_summary(item["day"]),
            "packaging_duration_ms": kwargs["packaging_duration_ms"],
            "model_requests": 2,
        }

    monkeypatch.setattr(routing_runs, "_execute_refresh_day", execute)

    result = routing_runs.refresh_all_days(
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
    assert result["packaging"] == {
        "total_duration_ms": 8.0,
        "max_day_duration_ms": 4.0,
    }
    assert result["will_call_model"] is True
    assert result["model_requests"] == 4
    assert frozen_days == ["2026-07-05", "2026-07-06"]
    assert result["pruned_runs"] == ["old-run"]
    assert not (run_root / "old-run").exists()
    assert {path.name for path in run_root.iterdir()} == {
        item["run_id"] for item in result["plan"]
    }


def test_refresh_reports_zero_model_requests_for_complete_resumed_runs(
    tmp_path, monkeypatch
):
    source = {"event_run_id": "event-run-abcdef", "feed_run_id": "feed-run-1"}
    monkeypatch.setattr(routing_runs, "_published_event_source", lambda: source)
    _stub_rank_identities(monkeypatch, source)
    monkeypatch.setattr(
        routing_runs,
        "_freeze_refresh_day",
        lambda *args, **kwargs: 3.0,
    )

    def execute(item, **kwargs):
        return {
            **_refresh_summary(item["day"]),
            "packaging_duration_ms": kwargs["packaging_duration_ms"],
            "model_requests": 0,
        }

    monkeypatch.setattr(routing_runs, "_execute_refresh_day", execute)

    result = routing_runs.refresh_all_days(
        through="2026-07-05",
        days=1,
        top_ranked=1,
        run_root=tmp_path / "runs",
    )

    assert result["will_call_model"] is False
    assert result["model_requests"] == 0
    assert result["packaging"]["total_duration_ms"] == 3.0


def test_refresh_failure_retains_old_runs_for_retry(tmp_path, monkeypatch):
    run_root = tmp_path / "routing"
    (run_root / "old-run").mkdir(parents=True)
    source = {"event_run_id": "event-run-abcdef", "feed_run_id": "feed-run-1"}
    monkeypatch.setattr(
        routing_runs,
        "_published_event_source",
        lambda: source,
    )
    _stub_rank_identities(monkeypatch, source)
    monkeypatch.setattr(
        routing_runs,
        "_freeze_refresh_day",
        lambda *args, **kwargs: 4.0,
    )

    def execute(item, **kwargs):
        if item["day"] == "2026-07-06":
            raise RuntimeError("model call failed")
        (kwargs["run_root"] / item["run_id"]).mkdir(parents=True)
        return _refresh_summary(item["day"])

    monkeypatch.setattr(routing_runs, "_execute_refresh_day", execute)

    with pytest.raises(RuntimeError, match="2026-07-06.*model call failed"):
        routing_runs.refresh_all_days(
            through="2026-07-06",
            days=2,
            top_ranked=1,
            workers=1,
            day_workers=2,
            replace=True,
            run_root=run_root,
        )

    assert (run_root / "old-run").is_dir()
