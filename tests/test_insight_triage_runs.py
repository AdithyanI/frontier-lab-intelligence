import json
import sqlite3

from fli import insight_triage_runs


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
