import json
import sqlite3

import pytest

from fli import insight_triage, insight_triage_runs


def test_provider_artifacts_preserve_x_article_and_link_card_metadata():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE x_post_observation (
               provider TEXT NOT NULL,
               post_id TEXT NOT NULL,
               observed_at TEXT NOT NULL,
               raw_sha256 TEXT NOT NULL,
               raw_json TEXT NOT NULL,
               PRIMARY KEY (provider, post_id, observed_at, raw_sha256)
           )"""
    )
    payload = {
        "entities": {
            "urls": [
                {
                    "url": "https://t.co/article",
                    "expanded_url": "https://x.com/i/article/123",
                },
                {
                    "url": "https://t.co/card",
                    "expanded_url": "https://example.com/research",
                },
            ]
        },
        "article": {
            "title": "Concepts of a Plan",
            "preview_text": "An argument about an AI-policy monoculture.",
        },
        "card": {
            "url": "https://t.co/card",
            "binding_values": [
                {
                    "key": "title",
                    "value": {"string_value": "Research note"},
                },
                {
                    "key": "description",
                    "value": {"string_value": "A concrete research result."},
                },
                {
                    "key": "card_url",
                    "value": {"string_value": "https://t.co/card"},
                },
            ],
        },
    }
    conn.execute(
        """INSERT INTO x_post_observation
           (provider, post_id, observed_at, raw_sha256, raw_json)
           VALUES (?, ?, ?, ?, ?)""",
        (
            "twitterapi_io",
            "post-1",
            "2026-07-11T00:00:00+00:00",
            "raw-1",
            json.dumps(payload),
        ),
    )

    artifacts = insight_triage_runs._provider_artifacts(
        conn,
        [("twitterapi_io", "post-1", "raw-1")],
    )

    assert artifacts == [
        {
            "post_id": "post-1",
            "kind": "x_article",
            "title": "Concepts of a Plan",
            "preview": "An argument about an AI-policy monoculture.",
            "url": "https://x.com/i/article/123",
        },
        {
            "post_id": "post-1",
            "kind": "link_card",
            "title": "Research note",
            "preview": "A concrete research result.",
            "url": "https://example.com/research",
        },
    ]


def test_embedded_only_enrichment_falls_back_to_immutable_feed_snapshot():
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    raw_conn.execute(
        """CREATE TABLE x_post_observation (
               provider TEXT NOT NULL,
               post_id TEXT NOT NULL,
               observed_at TEXT NOT NULL,
               raw_sha256 TEXT NOT NULL,
               raw_json TEXT NOT NULL,
               PRIMARY KEY (provider, post_id, observed_at, raw_sha256)
           )"""
    )
    feed_conn = sqlite3.connect(":memory:")
    feed_conn.row_factory = sqlite3.Row
    feed_conn.execute(
        """CREATE TABLE feed_post (
               run_id TEXT NOT NULL,
               provider TEXT NOT NULL,
               post_id TEXT NOT NULL,
               raw_sha256 TEXT NOT NULL,
               raw_json TEXT NOT NULL,
               PRIMARY KEY (run_id, provider, post_id)
           )"""
    )
    payload = {
        "entities": {
            "urls": [
                {
                    "url": "https://t.co/embedded",
                    "expanded_url": "https://example.com/embedded-research",
                }
            ]
        },
        "card": {
            "url": "https://t.co/embedded",
            "binding_values": [
                {"key": "title", "value": {"string_value": "Embedded paper"}},
                {
                    "key": "description",
                    "value": {"string_value": "A result carried only in a quote."},
                },
                {
                    "key": "card_url",
                    "value": {"string_value": "https://t.co/embedded"},
                },
            ],
        },
    }
    feed_conn.execute(
        """INSERT INTO feed_post
           (run_id, provider, post_id, raw_sha256, raw_json)
           VALUES ('feed-run', 'twitterapi_io', 'embedded-post', 'embedded-sha', ?)""",
        (json.dumps(payload),),
    )
    post_refs = [("twitterapi_io", "embedded-post", "embedded-sha")]

    urls = insight_triage_runs._expanded_urls(
        raw_conn,
        post_refs,
        feed_conn=feed_conn,
        feed_run_id="feed-run",
    )
    artifacts = insight_triage_runs._provider_artifacts(
        raw_conn,
        post_refs,
        feed_conn=feed_conn,
        feed_run_id="feed-run",
    )

    assert urls == {
        ("twitterapi_io", "embedded-post"): [
            "https://example.com/embedded-research"
        ]
    }
    assert artifacts == [
        {
            "post_id": "embedded-post",
            "kind": "link_card",
            "title": "Embedded paper",
            "preview": "A result carried only in a quote.",
            "url": "https://example.com/embedded-research",
        }
    ]


def test_envelope_enrichment_is_pinned_to_the_event_observation():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE x_post_observation (
               provider TEXT NOT NULL,
               post_id TEXT NOT NULL,
               observed_at TEXT NOT NULL,
               raw_sha256 TEXT NOT NULL,
               raw_json TEXT NOT NULL,
               PRIMARY KEY (provider, post_id, observed_at, raw_sha256)
           )"""
    )
    original = {
        "entities": {
            "urls": [
                {
                    "url": "https://t.co/original",
                    "expanded_url": "https://example.com/original",
                }
            ]
        }
    }
    later = {
        "entities": {
            "urls": [
                {
                    "url": "https://t.co/later",
                    "expanded_url": "https://example.com/later",
                }
            ]
        }
    }
    conn.executemany(
        """INSERT INTO x_post_observation
           (provider, post_id, observed_at, raw_sha256, raw_json)
           VALUES (?, 'post-1', ?, ?, ?)""",
        [
            (
                "twitterapi_io",
                "2026-07-11T00:00:00+00:00",
                "raw-original",
                json.dumps(original),
            ),
            (
                "twitterapi_io",
                "2026-07-13T00:00:00+00:00",
                "raw-later",
                json.dumps(later),
            ),
        ],
    )
    item = {
        "event_id": "stable-event",
        "root": {
            "provider": "twitterapi_io",
            "post_id": "post-1",
            "raw_sha256": "raw-original",
            "author": {"handle": "researcher"},
            "post_type": "original",
            "text": "A concrete model result.",
        },
        "evidence": [],
    }

    envelope = insight_triage_runs.envelope_from_event(
        item,
        day="2026-07-11",
        raw_conn=conn,
    )

    assert envelope.urls == (
        {"post_id": "post-1", "url": "https://example.com/original"},
    )
    assert "https://example.com/later" not in insight_triage.render_input(envelope)


def test_run_summary_reports_cache_ratio_and_decisions(tmp_path):
    conn = insight_triage_runs.connect_run(tmp_path / "triage.db")
    now = "2026-07-13T10:00:00+00:00"
    conn.execute(
        """INSERT INTO run_meta
           (singleton, run_id, day, model, reasoning_effort, prompt_version,
            prompt_sha256, schema_version, candidate_limit, cohort_sha256,
            expected_count, created_at, updated_at)
           VALUES (1, 'run-1', '2026-07-11', 'gpt-5.4-mini', 'medium',
                   'prompt-v1', 'prompt-hash', 'schema-v1', 1, 'cohort-hash',
                   1, ?, ?)""",
        (now, now),
    )
    conn.execute(
        """INSERT INTO triage_item
           (event_id, current_rank, root_post_id, root_url, envelope_json,
            input_text, input_sha256, prompt_cache_key, status, decision, input_tokens,
            cached_tokens, cache_write_tokens, output_tokens,
            reported_cost_usd, updated_at)
           VALUES ('event-1', 1, 'post-1', 'https://x.com/a/status/1', '{}',
                   'input', 'hash', 'cache-key', 'complete', 'keep', 2000, 1280, 0, 80,
                   0.0042, ?)""",
        (now,),
    )

    result = insight_triage_runs.summary(conn)

    assert result["counts"]["complete"] == 1
    assert result["counts"]["kept"] == 1
    assert result["counts"]["cache_read_ratio"] == 0.64
    assert result["counts"]["prompt_cache_keys"] == 1
    assert result["counts"]["cache_hit_requests"] == 1
    assert result["counts"]["reported_cost_usd"] == 0.0042


def test_completed_item_is_resumable_without_a_duplicate_model_call(
    tmp_path, monkeypatch
):
    conn = insight_triage_runs.connect_run(tmp_path / "triage.db")
    now = "2026-07-13T10:00:00+00:00"
    envelope = insight_triage.EnvelopeInput(
        event_id="event-1",
        day="2026-07-11",
        root={
            "post_id": "post-1",
            "author": "@researcher",
            "post_type": "original",
            "text": "A concrete model evaluation result.",
        },
    )
    conn.execute(
        """INSERT INTO run_meta
           (singleton, run_id, day, model, reasoning_effort, prompt_version,
            prompt_sha256, schema_version, candidate_limit, cohort_sha256,
            expected_count, created_at, updated_at)
           VALUES (1, 'run-1', '2026-07-11', 'gpt-5.4-mini', 'medium',
                   ?, ?, ?, 1, 'cohort-hash', 1, ?, ?)""",
        (
            insight_triage.PROMPT_VERSION,
            insight_triage.prompt_sha256(),
            insight_triage.SCHEMA_VERSION,
            now,
            now,
        ),
    )
    conn.execute(
        """INSERT INTO triage_item
           (event_id, current_rank, root_post_id, root_url, envelope_json,
            input_text, input_sha256, prompt_cache_key, updated_at)
           VALUES ('event-1', 1, 'post-1', 'https://x.com/a/status/1', ?, ?, ?, ?, ?)""",
        (
            insight_triage_runs._canonical_json(
                insight_triage_runs._envelope_payload(envelope)
            ),
            insight_triage.render_input(envelope),
            envelope.input_sha256,
            insight_triage.prompt_cache_key(envelope.event_id),
            now,
        ),
    )
    calls = []

    def fake_evaluate_one(client, supplied_envelope, **kwargs):
        calls.append((client, supplied_envelope, kwargs))
        return {
            "decision": "keep",
            "reason": "The post reports a concrete model evaluation result.",
            "response_id": "resp-1",
            "response_model": "gpt-5.4-mini",
            "input_tokens": 2_000,
            "cached_tokens": 1_280,
            "cache_write_tokens": 0,
            "output_tokens": 80,
            "reported_cost_usd": 0.0042,
            "request_tags": ["app:frontier-lab-intelligence"],
        }

    monkeypatch.setattr(insight_triage, "evaluate_one", fake_evaluate_one)

    first = insight_triage_runs.run_pending(conn, client=object())
    second = insight_triage_runs.run_pending(conn, client=object())

    assert first["counts"]["complete"] == 1
    assert second["counts"]["complete"] == 1
    assert len(calls) == 1
    row = conn.execute(
        "SELECT status, attempts, decision, cached_tokens FROM triage_item"
    ).fetchone()
    assert tuple(row) == ("complete", 1, "keep", 1_280)


def test_cli_dry_run_emits_stable_json_without_calling_the_model(capsys):
    exit_code = insight_triage_runs.main(
        [
            "run",
            "--run-id",
            "dry-run-check",
            "--day",
            "2026-07-11",
            "--limit",
            "20",
            "--dry-run",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["schema_version"] == "1.0"
    assert payload["command"] == "insight-triage.run"
    assert payload["status"] == "ok"
    assert payload["data"]["model"] == insight_triage.DEFAULT_MODEL
    assert payload["data"]["reasoning_effort"] == "medium"
    assert payload["data"]["workers"] == insight_triage_runs.DEFAULT_WORKERS
    assert payload["data"]["prompt_cache_shards"] == 32
    assert payload["data"]["will_call_model"] is False


def _test_envelope(*, event_id="event-1", text="Concrete model result"):
    return insight_triage.EnvelopeInput(
        event_id=event_id,
        day="2026-07-11",
        root={
            "post_id": "post-1",
            "author": "@researcher",
            "post_type": "original",
            "text": text,
        },
    )


def _insert_run_meta(
    conn,
    *,
    run_id,
    expected_count=1,
    model="gpt-5.4-mini",
    effort="medium",
):
    now = "2026-07-13T10:00:00+00:00"
    conn.execute(
        """INSERT INTO run_meta
           (singleton, run_id, day, model, reasoning_effort, prompt_version,
            prompt_sha256, schema_version, candidate_limit, cohort_sha256,
            expected_count, created_at, updated_at)
           VALUES (1, ?, '2026-07-11', ?, ?, ?, ?, ?, ?, 'cohort-hash',
                   ?, ?, ?)""",
        (
            run_id,
            model,
            effort,
            insight_triage.PROMPT_VERSION,
            insight_triage.prompt_sha256(),
            insight_triage.SCHEMA_VERSION,
            expected_count,
            expected_count,
            now,
            now,
        ),
    )


def test_connect_run_migrates_old_rows_with_null_snapshot_hash(tmp_path):
    path = tmp_path / "legacy.db"
    legacy = sqlite3.connect(path)
    legacy.executescript(
        """
        CREATE TABLE triage_item (
            event_id TEXT PRIMARY KEY,
            current_rank INTEGER NOT NULL,
            root_post_id TEXT NOT NULL,
            root_url TEXT NOT NULL,
            envelope_json TEXT NOT NULL,
            input_text TEXT NOT NULL,
            input_sha256 TEXT NOT NULL,
            prompt_cache_key TEXT NOT NULL,
            status TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            decision TEXT,
            reason TEXT,
            response_id TEXT,
            response_model TEXT,
            input_tokens INTEGER,
            cached_tokens INTEGER,
            cache_write_tokens INTEGER,
            output_tokens INTEGER,
            reported_cost_usd REAL,
            request_tags_json TEXT,
            error_type TEXT,
            error_message TEXT,
            completed_at TEXT,
            updated_at TEXT NOT NULL
        );
        INSERT INTO triage_item
            (event_id, current_rank, root_post_id, root_url, envelope_json,
             input_text, input_sha256, prompt_cache_key, status, updated_at)
        VALUES (
            'legacy-event', 1, 'post-1', 'https://x.com/a/status/1', '{}',
            'input', 'input-hash', 'cache-key', 'complete', '2026-07-13'
        );
        """
    )
    legacy.close()

    conn = insight_triage_runs.connect_run(path)
    row = conn.execute(
        """SELECT snapshot_content_sha256, reused_from_run_id,
                  reused_from_event_id
           FROM triage_item WHERE event_id = 'legacy-event'"""
    ).fetchone()

    assert tuple(row) == (None, None, None)


def test_freeze_persists_snapshot_and_rejects_stale_existing_cohort(
    tmp_path, monkeypatch
):
    envelope = _test_envelope()
    item = {
        "event_id": envelope.event_id,
        "root": {"url": "https://x.com/a/status/1"},
        "snapshot_content_sha256": "snapshot-a",
    }
    current = {"snapshot": "snapshot-a"}

    def fake_candidates(*, day, limit):
        assert day == "2026-07-11"
        assert limit == 1
        item["snapshot_content_sha256"] = current["snapshot"]
        cohort = [
            {
                "rank": 1,
                "event_id": envelope.event_id,
                "root_post_id": envelope.root["post_id"],
                "input_sha256": envelope.input_sha256,
                "snapshot_content_sha256": current["snapshot"],
                "prompt_cache_key": insight_triage.prompt_cache_key(
                    envelope.event_id
                ),
            }
        ]
        return [(1, dict(item), envelope)], cohort

    monkeypatch.setattr(insight_triage_runs, "_freeze_candidates", fake_candidates)
    monkeypatch.setattr(
        insight_triage_runs, "_reuse_completed_inputs", lambda conn: 0
    )
    conn = insight_triage_runs.connect_run(tmp_path / "triage.db")

    assert insight_triage_runs.freeze_run(
        conn,
        run_id="run-1",
        day="2026-07-11",
        limit=1,
        model="gpt-5.4-mini",
        effort="medium",
    ) == 1
    assert conn.execute(
        "SELECT snapshot_content_sha256 FROM triage_item"
    ).fetchone()[0] == "snapshot-a"
    assert insight_triage_runs.freeze_run(
        conn,
        run_id="run-1",
        day="2026-07-11",
        limit=1,
        model="gpt-5.4-mini",
        effort="medium",
    ) == 1

    current["snapshot"] = "snapshot-b"
    with pytest.raises(ValueError, match="cohort no longer matches"):
        insight_triage_runs.freeze_run(
            conn,
            run_id="run-1",
            day="2026-07-11",
            limit=1,
            model="gpt-5.4-mini",
            effort="medium",
        )


def test_exact_input_reuse_requires_compatible_complete_prior_run(
    tmp_path, monkeypatch
):
    run_root = tmp_path / "runs"
    source = insight_triage_runs.connect_run(run_root / "source" / "triage.db")
    _insert_run_meta(source, run_id="source")
    envelope = _test_envelope(event_id="source-event")
    now = "2026-07-13T10:00:00+00:00"
    source.execute(
        """INSERT INTO triage_item
           (event_id, current_rank, root_post_id, root_url, envelope_json,
            input_text, input_sha256, snapshot_content_sha256,
            prompt_cache_key, status, decision, reason, response_id,
            reported_cost_usd, completed_at, updated_at)
           VALUES (?, 1, 'post-1', 'https://x.com/a/status/1', ?, ?, ?,
                   'old-snapshot', 'cache-key', 'complete', 'keep',
                   'Concrete model result.', 'resp-source', 0.0042, ?, ?)""",
        (
            envelope.event_id,
            insight_triage_runs._canonical_json(
                insight_triage_runs._envelope_payload(envelope)
            ),
            insight_triage.render_input(envelope),
            envelope.input_sha256,
            now,
            now,
        ),
    )
    source.commit()
    source.close()

    monkeypatch.setattr(insight_triage_runs, "DEFAULT_RUN_ROOT", run_root)
    target = insight_triage_runs.connect_run(run_root / "target" / "triage.db")
    _insert_run_meta(target, run_id="target", expected_count=3)
    matching = _test_envelope(event_id="new-event")
    changed = _test_envelope(event_id="changed-event", text="Different input")
    changed_topology = _test_envelope(event_id="changed-topology")
    for rank, candidate in enumerate(
        (matching, changed, changed_topology), start=1
    ):
        snapshot_hash = "old-snapshot" if rank == 1 else f"snapshot-{rank}"
        target.execute(
            """INSERT INTO triage_item
               (event_id, current_rank, root_post_id, root_url, envelope_json,
                input_text, input_sha256, snapshot_content_sha256,
                prompt_cache_key, updated_at)
               VALUES (?, ?, 'post-1', 'https://x.com/a/status/1', ?, ?, ?, ?,
                       'cache-key', ?)""",
            (
                candidate.event_id,
                rank,
                insight_triage_runs._canonical_json(
                    insight_triage_runs._envelope_payload(candidate)
                ),
                insight_triage.render_input(candidate),
                candidate.input_sha256,
                snapshot_hash,
                now,
            ),
        )
    target.commit()

    assert insight_triage_runs._reuse_completed_inputs(target) == 1
    reused = target.execute(
        "SELECT * FROM triage_item WHERE event_id = 'new-event'"
    ).fetchone()
    pending = target.execute(
        "SELECT * FROM triage_item WHERE event_id = 'changed-event'"
    ).fetchone()
    topology_pending = target.execute(
        "SELECT * FROM triage_item WHERE event_id = 'changed-topology'"
    ).fetchone()

    assert reused["status"] == "complete"
    assert reused["decision"] == "keep"
    assert reused["attempts"] == 0
    assert reused["reported_cost_usd"] == 0.0
    assert reused["reused_from_run_id"] == "source"
    assert reused["reused_from_event_id"] == "source-event"
    assert reused["reused_from_response_id"] == "resp-source"
    assert reused["reused_from_reported_cost_usd"] == 0.0042
    assert pending["status"] == "pending"
    assert topology_pending["input_sha256"] == matching.input_sha256
    assert topology_pending["status"] == "pending"


def test_exact_input_reuse_rejects_incompatible_or_incomplete_runs(
    tmp_path, monkeypatch
):
    run_root = tmp_path / "runs"
    envelope = _test_envelope()
    now = "2026-07-13T10:00:00+00:00"
    for run_id, model, status in (
        ("wrong-model", "gpt-5.5", "complete"),
        ("incomplete", "gpt-5.4-mini", "pending"),
    ):
        source = insight_triage_runs.connect_run(
            run_root / run_id / "triage.db"
        )
        _insert_run_meta(source, run_id=run_id, model=model)
        source.execute(
            """INSERT INTO triage_item
               (event_id, current_rank, root_post_id, root_url, envelope_json,
                input_text, input_sha256, snapshot_content_sha256,
                prompt_cache_key, status, decision, reason, updated_at)
               VALUES (?, 1, 'post-1', 'https://x.com/a/status/1', ?, ?, ?,
                       'snapshot', 'cache-key', ?, 'keep', 'Evidence.', ?)""",
            (
                f"{run_id}-event",
                insight_triage_runs._canonical_json(
                    insight_triage_runs._envelope_payload(envelope)
                ),
                insight_triage.render_input(envelope),
                envelope.input_sha256,
                status,
                now,
            ),
        )
        source.commit()
        source.close()

    monkeypatch.setattr(insight_triage_runs, "DEFAULT_RUN_ROOT", run_root)
    target = insight_triage_runs.connect_run(run_root / "target" / "triage.db")
    _insert_run_meta(target, run_id="target")
    target.execute(
        """INSERT INTO triage_item
           (event_id, current_rank, root_post_id, root_url, envelope_json,
            input_text, input_sha256, snapshot_content_sha256,
            prompt_cache_key, updated_at)
           VALUES ('target-event', 1, 'post-1', 'https://x.com/a/status/1',
                   ?, ?, ?, 'new-snapshot', 'cache-key', ?)""",
        (
            insight_triage_runs._canonical_json(
                insight_triage_runs._envelope_payload(envelope)
            ),
            insight_triage.render_input(envelope),
            envelope.input_sha256,
            now,
        ),
    )
    target.commit()

    assert insight_triage_runs._reuse_completed_inputs(target) == 0
    assert target.execute(
        "SELECT status FROM triage_item WHERE event_id = 'target-event'"
    ).fetchone()[0] == "pending"
