import json
import sqlite3

from fli import insight_triage, insight_triage_runs


def test_provider_artifacts_preserve_x_article_and_link_card_metadata():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE x_post (post_id TEXT PRIMARY KEY, raw_json TEXT)")
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
        "INSERT INTO x_post (post_id, raw_json) VALUES (?, ?)",
        ("post-1", json.dumps(payload)),
    )

    artifacts = insight_triage_runs._provider_artifacts(conn, ["post-1"])

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
            input_text, input_sha256, status, decision, input_tokens,
            cached_tokens, cache_write_tokens, output_tokens,
            reported_cost_usd, updated_at)
           VALUES ('event-1', 1, 'post-1', 'https://x.com/a/status/1', '{}',
                   'input', 'hash', 'complete', 'keep', 2000, 1280, 0, 80,
                   0.0042, ?)""",
        (now,),
    )

    result = insight_triage_runs.summary(conn)

    assert result["counts"]["complete"] == 1
    assert result["counts"]["kept"] == 1
    assert result["counts"]["cache_read_ratio"] == 0.64
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
            input_text, input_sha256, updated_at)
           VALUES ('event-1', 1, 'post-1', 'https://x.com/a/status/1', ?, ?, ?, ?)""",
        (
            insight_triage_runs._canonical_json(
                insight_triage_runs._envelope_payload(envelope)
            ),
            insight_triage.render_input(envelope),
            envelope.input_sha256,
            now,
        ),
    )
    calls = []

    def fake_evaluate_one(client, supplied_envelope, **kwargs):
        calls.append((client, supplied_envelope, kwargs))
        return {
            "decision": "keep",
            "category": "technical_development",
            "signal_post_ids": ["post-1"],
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
    assert payload["data"]["model"] == "gpt-5.4-mini"
    assert payload["data"]["will_call_model"] is False
