import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from fli import audience_insight_publication_audit, audience_insight_runs
from fli.web import insights as insight_store
from fli.web.app import app


client = TestClient(app)


def _audit_result(row, meta, **overrides):
    output = {
        "audit_item_id": str(row["audit_item_id"]),
        "citation_fidelity": "pass",
        "attribution_fidelity": "pass",
        "epistemic_discipline": "pass",
        "audience_usefulness": "pass",
        "actionability": "pass",
        "specificity": "pass",
        "failure_codes": [],
        "rationale": "The frozen item passes every audit dimension.",
    }
    output.update(overrides)
    return {
        **output,
        "raw_output_text": json.dumps(output, sort_keys=True),
        "response_id": "resp-audit",
        "response_model": "gpt-5.6-luna",
        "input_tokens": 1_200,
        "cached_tokens": 800,
        "cache_write_tokens": 0,
        "output_tokens": 100,
        "reported_cost_usd": 0.01,
        "request_tags": list(
            audience_insight_publication_audit.request_tags(
                audience=str(meta["audience"]),
                audit_id=str(meta["audit_id"]),
                day=str(meta["day"]),
            )
        ),
    }


def _passing_audit(path, *, failed_selected_ids=None):
    audit_db = path.parent / "publication-audit-v1" / "audit.db"
    conn = audience_insight_publication_audit.connect(audit_db)
    audience_insight_publication_audit.freeze_audit(
        conn,
        audit_id="test-publication-audit",
        source_run_db=path,
    )
    meta = conn.execute("SELECT * FROM audit_run WHERE singleton = 1").fetchone()
    rows = conn.execute("SELECT * FROM audit_item ORDER BY audit_item_id").fetchall()
    for row in rows:
        overrides = {}
        if (
            row["sample_kind"] == "selected"
            and str(row["source_candidate_id"]) in (failed_selected_ids or set())
        ):
            overrides = {
                "actionability": "fail",
                "specificity": "fail",
                "failure_codes": [
                    "generic_investment_watchpoint",
                    "vague_or_promotional",
                ],
                "rationale": "The selected item is too generic to publish.",
            }
        audience_insight_publication_audit._store_success(
            conn, row, meta, _audit_result(row, meta, **overrides)
        )
    conn.close()
    return audit_db


def _failing_selected_audit(path):
    audit_db = path.parent / "publication-audit-v1" / "audit.db"
    conn = audience_insight_publication_audit.connect(audit_db)
    audience_insight_publication_audit.freeze_audit(
        conn,
        audit_id="test-failed-publication-audit",
        source_run_db=path,
    )
    meta = conn.execute("SELECT * FROM audit_run WHERE singleton = 1").fetchone()
    rows = conn.execute("SELECT * FROM audit_item ORDER BY audit_item_id").fetchall()
    for row in rows:
        if row["sample_kind"] == "selected":
            overrides = {
                "actionability": "fail",
                "specificity": "fail",
                "failure_codes": [
                    "generic_investment_watchpoint",
                    "vague_or_promotional",
                ],
                "rationale": "The selected item is too generic to publish.",
            }
        else:
            overrides = {
                "audience_usefulness": "fail",
                "failure_codes": ["not_decision_relevant"],
                "rationale": "The reject would not enter the final set.",
            }
        audience_insight_publication_audit._store_success(
            conn, row, meta, _audit_result(row, meta, **overrides)
        )
    conn.close()
    return audit_db


def _make_finalizable_run(path):
    _fixture(path, audit=False)
    _add_review_reject(path)
    conn = audience_insight_runs.connect_run(path)
    now = "2026-07-14T12:06:00+00:00"
    original_input = json.dumps(
        {
            "selected": [
                {"candidate_id": "candidate-1"},
                {"candidate_id": "candidate-2"},
            ]
        }
    )
    active_input = json.dumps(
        {"selected": [{"candidate_id": "candidate-1"}]}
    )
    with conn:
        conn.execute(
            """INSERT INTO daily_selection
               (editorial_rank, candidate_id, decision_value, audit_reason)
               VALUES (2, 'candidate-2', 'watchlist_or_exposure',
                       'The original editor selected this tail.')"""
        )
        conn.execute("UPDATE editor_run SET selected_count = 2 WHERE singleton = 1")
        conn.execute(
            """INSERT INTO day_set_review
               (singleton, status, attempts, input_text, input_sha256,
                prompt_cache_key, duplicate_pairs_json, padding_detected,
                thin_day_honest, set_rationale, updated_at)
               VALUES (1, 'complete', 1, ?, 'original-review-sha',
                       'review-cache', '[]', 1, 1,
                       'The second item is padding on an honest thin day.', ?)""",
            (original_input, now),
        )
        conn.execute(
            """INSERT INTO selection_reconciliation
               (singleton, status, reason_code, source_review_input_sha256,
                source_review_response_id, original_selected_ids_json,
                active_selected_ids_json, removed_candidate_id,
                removed_editorial_rank, created_at, completed_at, updated_at)
               VALUES (1, 'complete', 'padding_tail_trim',
                       'original-review-sha', 'review-response', ?, ?,
                       'candidate-2', 2, ?, ?, ?)""",
            (
                json.dumps(["candidate-1", "candidate-2"]),
                json.dumps(["candidate-1"]),
                now,
                now,
                now,
            ),
        )
        conn.execute(
            """INSERT INTO reconciled_day_set_review
               (singleton, status, attempts, reconciliation_reason,
                source_review_input_sha256, input_text, input_sha256,
                prompt_cache_key, duplicate_pairs_json, padding_detected,
                thin_day_honest, set_rationale, updated_at)
               VALUES (1, 'complete', 1, 'padding_tail_trim',
                       'original-review-sha', ?, 'active-review-sha',
                       'active-review-cache', '[]', 0, 1,
                       'The survivor is honest and not padding.', ?)""",
            (active_input, now),
        )
    conn.close()
    audit_db = _failing_selected_audit(path)
    audience_insight_publication_audit.create_publication_finalization(
        source_run_db=path,
        audit_db=audit_db,
    )


def _fixture(
    path,
    *,
    audience="investment",
    run_id="test-run",
    updated_at="now",
    audit=True,
):
    conn = audience_insight_runs.connect_run(path)
    now = "2026-07-14T12:00:00+00:00"
    audience_fields = (
        {
            "investment_implication": "A concrete implication.",
            "what_to_watch": "A concrete watchpoint.",
        }
        if audience == "investment"
        else {
            "action_type": "benchmark",
            "engineering_action": "Benchmark this on the production workload.",
            "validation_boundary": "The report covers only one workload.",
        }
    )
    prompt = f"{audience}-insight-v2.0"
    editor_prompt = f"{audience}-daily-editor-v2.0"
    with conn:
        conn.execute(
            """INSERT INTO run_meta
               (singleton, run_id, audience, day, model, reasoning_effort,
                prompt_version, prompt_sha256, input_render_version,
                schema_version,
                editor_model, editor_reasoning_effort, editor_prompt_version,
                editor_prompt_sha256, editor_schema_version,
                review_model, review_reasoning_effort,
                item_review_prompt_version, item_review_prompt_sha256,
                item_review_schema_version, day_review_prompt_version,
                day_review_prompt_sha256, day_review_schema_version,
                source_triage_db, source_artifact_db, rank_limit,
                event_ids_json, cohort_sha256, expected_count,
                created_at, updated_at)
               VALUES (1, ?, ?, '2026-07-11', 'gpt-test', 'medium', ?,
                       'prompt-sha', 'provider-safe-v2', 'schema-v2',
                       'gpt-test', 'high', ?,
                       'editor-prompt-sha', 'editor-schema-v2', 'gpt-test', 'high',
                       'item-review-v2', 'item-review-sha', 'item-review-schema',
                       'day-review-v2', 'day-review-sha', 'day-review-schema',
                       'triage.db',
                       'artifacts.db', 50, '["event-1","event-2"]', 'cohort',
                       2, ?, ?)""",
            (run_id, audience, prompt, editor_prompt, now, updated_at),
        )
        common = (
            "2026-07-11",
            4,
            json.dumps(
                {
                    "sources": [
                        {
                            "source_type": "x_post",
                            "author": "@a",
                            "title": None,
                            "relation": "origin",
                            "text": "Exact quote",
                        }
                    ]
                }
            ),
            "input",
            "sha",
            "cache",
            "Claim",
            "first_party_report",
            "Why it matters.",
            json.dumps(audience_fields),
            "Exact quote",
            1,
            "x_post",
            "post-1",
            "https://x.com/a/status/1",
            "@a",
            None,
            "source-sha",
            0,
            11,
            1,
            1500,
            1280,
            100,
            0.01,
            now,
            now,
        )
        conn.execute(
            """INSERT INTO candidate_item
               (candidate_id, event_id, day, feed_rank, packet_json, input_text,
                input_sha256, prompt_cache_key, status, attempts, outcome,
                claim, claim_posture, why_it_matters, audience_fields_json,
                supporting_quote, citation_block_index, citation_source_type,
                citation_source_id, citation_source_url, citation_source_author,
                citation_source_title, citation_source_sha256,
                citation_char_start, citation_char_end,
                citation_global_matching_block_count, input_tokens, cached_tokens,
                output_tokens, reported_cost_usd, completed_at, updated_at)
               VALUES ('candidate-1', 'event-1', ?, ?, ?, ?, ?, ?, 'complete', 1,
                       'insight', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?, ?)""",
            common,
        )
        conn.execute(
            """INSERT INTO candidate_item
               (candidate_id, event_id, day, feed_rank, packet_json, input_text,
                input_sha256, prompt_cache_key, status, attempts, outcome,
                claim, input_tokens, cached_tokens, reported_cost_usd, updated_at)
               VALUES ('candidate-2', 'event-2', '2026-07-11', 5, '{}', 'input',
                       'sha2', 'cache', 'failed', 1, 'insight', 'Rejected claim',
                       1500, 0, 0.02, ?)""",
            (now,),
        )
        conn.execute(
            """INSERT INTO editor_run
               (singleton, status, attempts, candidate_set_sha256,
                history_sha256, prior_selected_json, input_text,
                prompt_cache_key, selected_count, response_id, response_model,
                input_tokens, cached_tokens, output_tokens, reported_cost_usd,
                request_tags_json, raw_output_text, completed_at, updated_at)
               VALUES (1, 'complete', 1, 'candidates', 'history', '[]', 'editor',
                       'editor-cache', 1, 'resp-editor', 'gpt-test', 1000, 0, 100,
                       0.005, '[]', '{}', ?, ?)""",
            (now, now),
        )
        conn.execute(
            """INSERT INTO daily_selection
               (editorial_rank, candidate_id, decision_value, audit_reason)
               VALUES (1, 'candidate-1', ?, 'Most decision-relevant item.')""",
            (
                "thesis_or_model"
                if audience == "investment"
                else "experiment_or_benchmark",
            ),
        )
        conn.execute(
            """INSERT INTO publication_selection
               (publication_rank, original_editorial_rank,
                candidate_id, activated_at)
               VALUES (1, 1, 'candidate-1', ?)""",
            (now,),
        )
        conn.execute(
            """INSERT INTO quality_gate
               (singleton, passed, result_json, computed_at)
               VALUES (1, 1, '{"passed":true,"selected_count":1}', ?)""",
            (now,),
        )
    conn.close()
    if audit:
        _passing_audit(path)


def _add_review_reject(path):
    conn = audience_insight_runs.connect_run(path)
    now = "2026-07-14T12:05:00+00:00"
    quote = "A second exact quote."
    with conn:
        conn.execute(
            """UPDATE candidate_item
               SET status = 'complete', outcome = 'insight',
                   packet_json = ?, claim = 'A rejected bounded claim.',
                   claim_posture = 'third_party_observation',
                   why_it_matters = 'It could matter if independently verified.',
                   audience_fields_json = ?, supporting_quote = ?,
                   citation_block_index = 1, citation_source_type = 'x_post',
                   citation_source_id = 'post-2',
                   citation_source_url = 'https://x.com/a/status/2',
                   citation_source_author = '@a',
                   citation_source_sha256 = 'source-sha-2',
                   citation_char_start = 0, citation_char_end = ?
               WHERE candidate_id = 'candidate-2'""",
            (
                json.dumps(
                    {
                        "sources": [
                            {
                                "source_type": "x_post",
                                "author": "@a",
                                "title": None,
                                "relation": "origin",
                                "text": quote,
                            }
                        ]
                    }
                ),
                json.dumps(
                    {
                        "investment_implication": "Test the bounded claim.",
                        "what_to_watch": "Watch for independent replication.",
                    }
                ),
                quote,
                len(quote),
            ),
        )
        conn.execute(
            """INSERT INTO item_review
               (candidate_id, status, attempts, input_text, input_sha256,
                prompt_cache_key, claim_fidelity, epistemic_discipline,
                audience_usefulness, actionability, specificity,
                failure_codes_json, rationale, completed_at, updated_at)
               VALUES ('candidate-2', 'complete', 1, 'review', 'review-sha',
                       'review-cache', 'pass', 'pass', 'fail', 'pass', 'pass',
                       '["not_decision_relevant"]', 'The filter rejected it.',
                       ?, ?)""",
            (now, now),
        )
    conn.close()


def _write_false_negative_adjudications(audit_db, *, verdict="would_not_enter"):
    conn = sqlite3.connect(audit_db)
    conn.row_factory = sqlite3.Row
    meta = conn.execute("SELECT * FROM audit_run WHERE singleton = 1").fetchone()
    rows = conn.execute(
        """SELECT audit_item_id, source_candidate_id
           FROM audit_item
           WHERE sample_kind = 'review_reject' AND status = 'complete'
             AND mechanical_citation_valid = 1
             AND citation_fidelity = 'pass' AND attribution_fidelity = 'pass'
             AND epistemic_discipline = 'pass'
             AND audience_usefulness = 'pass' AND actionability = 'pass'
             AND specificity = 'pass'
           ORDER BY audit_item_id"""
    ).fetchall()
    payload = {
        "schema_version": audience_insight_publication_audit.ADJUDICATION_SCHEMA_VERSION,
        "source_run_id": str(meta["source_run_id"]),
        "source_contract_sha256": str(meta["source_contract_sha256"]),
        "audit_id": str(meta["audit_id"]),
        "audit_cohort_sha256": str(meta["cohort_sha256"]),
        "audit_result_sha256": audience_insight_publication_audit.audit_result_sha256(
            conn
        ),
        "adjudications": [
            {
                "audit_item_id": str(row["audit_item_id"]),
                "source_candidate_id": str(row["source_candidate_id"]),
                "verdict": verdict,
                "rationale": "This same-story reject would not displace or diversify the final set.",
            }
            for row in rows
        ],
    }
    conn.close()
    path = audit_db.parent / audience_insight_publication_audit.ADJUDICATION_FILENAME
    path.write_text(json.dumps(payload, sort_keys=True))
    return path


def test_insights_api_returns_only_selected_verified_audience_rows(
    tmp_path, monkeypatch
):
    db = tmp_path / "2026-07-11" / "investment" / "run" / "insights.db"
    engineering = (
        tmp_path / "2026-07-11" / "ai_engineering" / "run" / "insights.db"
    )
    _fixture(db)
    _fixture(engineering, audience="ai_engineering")
    _, report = _write_reconciliation_report(tmp_path, [db, engineering])
    monkeypatch.setattr(insight_store, "DEFAULT_INSIGHTS_ROOT", tmp_path)
    monkeypatch.setattr(
        insight_store.audience_insight_production_reconciliation,
        "evaluate_manifest",
        lambda _path: report,
    )

    response = client.get("/api/insights?audience=investment&date=2026-07-11")
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["audience"] == "investment"
    assert payload["run"]["candidate_count"] == 2
    assert payload["run"]["selected_count"] == 1
    assert payload["run"]["editor_selected_count"] == 1
    assert payload["run"]["selection_reconciliation"] is None
    assert payload["run"]["failed_count"] == 1
    assert payload["run"]["reported_cost_usd"] == 0.035
    assert [item["event_id"] for item in payload["items"]] == ["event-1"]
    assert payload["items"][0]["editorial_rank"] == 1
    assert payload["items"][0]["feed_rank"] == 4
    assert payload["items"][0]["citation"]["quote"] == "Exact quote"


def test_web_publishes_active_prefix_and_discloses_original_trim(tmp_path):
    db = tmp_path / "2026-07-11" / "investment" / "trimmed" / "insights.db"
    _fixture(db, run_id="trimmed", audit=False)
    conn = audience_insight_runs.connect_run(db)
    now = "2026-07-14T12:05:00+00:00"
    with conn:
        conn.execute(
            """UPDATE candidate_item
               SET status = 'complete', outcome = 'insight',
                   claim = 'Original editor tail.',
                   claim_posture = 'first_party_report',
                   why_it_matters = 'It was selected by the editor.',
                   audience_fields_json = ?, supporting_quote = 'Exact quote',
                   citation_block_index = 1, citation_source_type = 'x_post',
                   citation_source_id = 'post-2',
                   citation_source_url = 'https://x.com/a/status/2',
                   citation_source_author = '@a',
                   citation_source_sha256 = 'source-sha-2',
                   citation_char_start = 0, citation_char_end = 11
               WHERE candidate_id = 'candidate-2'""",
            (
                json.dumps(
                    {
                        "investment_implication": "Another implication.",
                        "what_to_watch": "Another watchpoint.",
                    }
                ),
            ),
        )
        conn.execute(
            """INSERT INTO daily_selection
               (editorial_rank, candidate_id, decision_value, audit_reason)
               VALUES (2, 'candidate-2', 'thesis_or_model',
                       'The original editor selected this tail.')"""
        )
        conn.execute(
            "UPDATE editor_run SET selected_count = 2 WHERE singleton = 1"
        )
        conn.execute(
            """INSERT INTO selection_reconciliation
               (singleton, status, reason_code, source_review_input_sha256,
                source_review_response_id, original_selected_ids_json,
                active_selected_ids_json, removed_candidate_id,
                removed_editorial_rank, created_at, completed_at, updated_at)
               VALUES (1, 'complete', 'padding_tail_trim', 'first-sha',
                       'first-review', ?, ?, 'candidate-2', 2, ?, ?, ?)""",
            (
                json.dumps(["candidate-1", "candidate-2"]),
                json.dumps(["candidate-1"]),
                now,
                now,
                now,
            ),
        )
    conn.close()
    _passing_audit(db)

    payload = insight_store.insights_payload(
        audience="investment", db_path=db
    )
    assert payload["available"] is True
    assert [item["candidate_id"] for item in payload["items"]] == ["candidate-1"]
    assert payload["run"]["selected_count"] == 1
    assert payload["run"]["editor_selected_count"] == 2
    assert payload["run"]["selection_reconciliation"] == {
        "reason_code": "padding_tail_trim",
        "status": "complete",
        "removed_candidate_id": "candidate-2",
        "removed_editorial_rank": 2,
        "original_selected_count": 2,
        "active_selected_count": 1,
    }
    audit_rows = sqlite3.connect(db).execute(
        "SELECT candidate_id FROM daily_selection ORDER BY editorial_rank"
    ).fetchall()
    assert audit_rows == [("candidate-1",), ("candidate-2",)]


def test_insights_read_model_is_honest_when_missing(tmp_path):
    payload = insight_store.insights_payload(
        audience="ai_engineering", db_path=tmp_path / "missing.db"
    )
    assert payload["available"] is False
    assert payload["audience"] == "ai_engineering"
    assert payload["items"] == []


def test_feed_ranked_extraction_view_reads_existing_candidate_rows(tmp_path):
    db = tmp_path / "2026-07-11" / "investment" / "run" / "insights.db"
    _fixture(
        db,
        run_id="audience-insights-v2-production-investment-2026-07-11-test",
    )

    dates = insight_store.extraction_dates_payload(
        audience="investment", run_root=tmp_path
    )
    payload = insight_store.extraction_insights_payload(
        audience="investment", day="2026-07-11", run_root=tmp_path
    )

    assert dates["dates"] == [{"day": "2026-07-11", "item_count": 1}]
    assert payload["available"] is True
    assert payload["run"]["complete_count"] == 1
    assert [item["feed_rank"] for item in payload["items"]] == [4]
    assert "editorial_rank" not in payload["items"][0]
    assert payload["items"][0]["citation"]["quote"] == "Exact quote"


def test_feed_ranked_extraction_api_uses_existing_run_databases(tmp_path, monkeypatch):
    db = tmp_path / "2026-07-11" / "ai_engineering" / "run" / "insights.db"
    _fixture(
        db,
        audience="ai_engineering",
        run_id="audience-insights-v2-production-ai-engineering-2026-07-11-test",
    )
    monkeypatch.setattr(insight_store, "DEFAULT_INSIGHTS_ROOT", tmp_path)

    dates = client.get(
        "/api/insights/extracted/dates?audience=ai_engineering"
    ).json()
    payload = client.get(
        "/api/insights/extracted?audience=ai_engineering&date=2026-07-11"
    ).json()

    assert dates["latest_date"] == "2026-07-11"
    assert payload["items"][0]["audience_fields"]["action_type"] == "benchmark"


def test_zero_item_day_uses_application_owned_quality_bar_copy(tmp_path):
    db = tmp_path / "run" / "investment" / "insights.db"
    _fixture(db, audit=False)
    conn = audience_insight_runs.connect_run(db)
    with conn:
        conn.execute("DELETE FROM publication_selection")
        conn.execute("UPDATE editor_run SET selected_count = 0 WHERE singleton = 1")
        conn.execute(
            "UPDATE quality_gate SET result_json = ? WHERE singleton = 1",
            (json.dumps({"passed": True, "selected_count": 0}),),
        )
    conn.close()
    _passing_audit(db)

    payload = insight_store.insights_payload(audience="investment", db_path=db)

    assert payload["available"] is False
    assert payload["items"] == []
    assert payload["reason"] == (
        "No candidate cleared this audience's publication quality bar for this day."
    )


def test_dates_and_latest_run_are_isolated_by_audience(tmp_path):
    _fixture(
        tmp_path / "older" / "investment" / "old" / "insights.db",
        audience="investment",
        run_id="older",
        updated_at="2026-07-14T01:00:00+00:00",
    )
    _fixture(
        tmp_path / "newer" / "investment" / "new" / "insights.db",
        audience="investment",
        run_id="newer",
        updated_at="2026-07-14T02:00:00+00:00",
    )
    _fixture(
        tmp_path / "newer" / "ai_engineering" / "run" / "insights.db",
        audience="ai_engineering",
        run_id="engineering",
        updated_at="2026-07-14T03:00:00+00:00",
    )

    dates = insight_store.insight_dates_payload(
        audience="investment", run_root=tmp_path
    )
    assert dates == {
        "available": True,
        "reason": None,
        "audience": "investment",
        "latest_date": "2026-07-11",
        "dates": [{"day": "2026-07-11", "item_count": 1}],
    }
    investment = insight_store.insights_payload(
        audience="investment", day="2026-07-11", run_root=tmp_path
    )
    engineering = insight_store.insights_payload(
        audience="ai_engineering", day="2026-07-11", run_root=tmp_path
    )
    assert investment["run"]["run_id"] == "newer"
    assert engineering["run"]["run_id"] == "engineering"


def _write_reconciliation_report(root, paths, *, passed=True):
    expected = {"investment": [], "ai_engineering": []}
    runs = []
    for path in paths:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT run_id, audience, day FROM run_meta WHERE singleton = 1"
        ).fetchone()
        conn.close()
        expected[str(row["audience"])].append(str(row["day"]))
        runs.append(
            {
                "source_run_id": str(row["run_id"]),
                "audience": str(row["audience"]),
                "day": str(row["day"]),
                "source_run_db": str(path.resolve()),
            }
        )
    report = {
        "schema_version": insight_store.PRODUCTION_RECONCILIATION_SCHEMA,
        "mode": "partial",
        "passed": passed,
        "checks": {
            "all_manifest_runs_validated": passed,
            "mode_scope_validated": passed,
            "x_article_cohort_requirement_satisfied": passed,
        },
        "expected_audience_days": expected,
        "runs": runs,
    }
    target = (
        root
        / insight_store.PRODUCTION_RECONCILIATION_DIR
        / insight_store.PRODUCTION_RECONCILIATION_REPORT
    )
    target.parent.mkdir(parents=True)
    target.write_text(
        insight_store.audience_insight_production_reconciliation.canonical_report_text(
            report
        )
    )
    manifest = target.parent / insight_store.PRODUCTION_RECONCILIATION_MANIFEST
    manifest.write_text("{}")
    return target, report


def test_default_web_uses_exact_reconciliation_allowlist_not_newest_run(
    tmp_path, monkeypatch
):
    approved_investment = tmp_path / "approved" / "investment" / "insights.db"
    experimental_investment = (
        tmp_path / "experimental" / "investment" / "insights.db"
    )
    approved_engineering = tmp_path / "approved" / "engineering" / "insights.db"
    _fixture(
        approved_investment,
        audience="investment",
        run_id="approved-investment",
        updated_at="2026-07-14T01:00:00+00:00",
    )
    _fixture(
        experimental_investment,
        audience="investment",
        run_id="newer-experimental-investment",
        updated_at="2026-07-14T09:00:00+00:00",
    )
    _fixture(
        approved_engineering,
        audience="ai_engineering",
        run_id="approved-engineering",
        updated_at="2026-07-14T02:00:00+00:00",
    )
    _, report = _write_reconciliation_report(
        tmp_path, [approved_investment, approved_engineering]
    )
    monkeypatch.setattr(insight_store, "DEFAULT_INSIGHTS_ROOT", tmp_path)
    monkeypatch.setattr(
        insight_store.audience_insight_production_reconciliation,
        "evaluate_manifest",
        lambda _path: report,
    )

    investment = insight_store.insights_payload(
        audience="investment", day="2026-07-11"
    )
    engineering = insight_store.insights_payload(
        audience="ai_engineering", day="2026-07-11"
    )

    assert investment["run"]["run_id"] == "approved-investment"
    assert engineering["run"]["run_id"] == "approved-engineering"


def test_existing_invalid_reconciliation_report_fails_closed(tmp_path, monkeypatch):
    investment = tmp_path / "approved" / "investment" / "insights.db"
    engineering = tmp_path / "approved" / "engineering" / "insights.db"
    _fixture(investment, audience="investment", run_id="investment")
    _fixture(engineering, audience="ai_engineering", run_id="engineering")
    _, report = _write_reconciliation_report(
        tmp_path, [investment, engineering], passed=False
    )
    monkeypatch.setattr(insight_store, "DEFAULT_INSIGHTS_ROOT", tmp_path)
    monkeypatch.setattr(
        insight_store.audience_insight_production_reconciliation,
        "evaluate_manifest",
        lambda _path: report,
    )

    assert insight_store.insight_dates_payload(audience="investment")["dates"] == []
    assert insight_store.insights_payload(audience="investment")["available"] is False


def test_default_web_without_reconciliation_pair_never_guesses_by_recency(
    tmp_path, monkeypatch
):
    _fixture(
        tmp_path / "newest-experiment" / "investment" / "insights.db",
        audience="investment",
        run_id="newest-experiment",
        updated_at="2026-07-14T09:00:00+00:00",
    )
    monkeypatch.setattr(insight_store, "DEFAULT_INSIGHTS_ROOT", tmp_path)

    assert insight_store.insight_dates_payload(audience="investment")["dates"] == []
    assert insight_store.insights_payload(audience="investment")["available"] is False


def test_reconciliation_report_binding_drift_fails_closed(tmp_path, monkeypatch):
    investment = tmp_path / "approved" / "investment" / "insights.db"
    engineering = tmp_path / "approved" / "engineering" / "insights.db"
    _fixture(investment, audience="investment", run_id="investment")
    _fixture(engineering, audience="ai_engineering", run_id="engineering")
    target, evaluated_report = _write_reconciliation_report(
        tmp_path, [investment, engineering]
    )
    stored_report = json.loads(target.read_text())
    stored_report["runs"][0]["selection"] = {
        "base_ids_sha256": "0" * 64,
        "effective_ids_sha256": "0" * 64,
    }
    target.write_text(json.dumps(stored_report))
    monkeypatch.setattr(insight_store, "DEFAULT_INSIGHTS_ROOT", tmp_path)
    monkeypatch.setattr(
        insight_store.audience_insight_production_reconciliation,
        "evaluate_manifest",
        lambda _path: evaluated_report,
    )

    assert insight_store.insight_dates_payload(audience="investment")["dates"] == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda text: text.replace('"passed":true', '"passed":1'),
        lambda text: "  " + text,
    ],
)
def test_reconciliation_report_requires_exact_canonical_bytes(
    tmp_path, monkeypatch, mutate
):
    investment = tmp_path / "approved" / "investment" / "insights.db"
    engineering = tmp_path / "approved" / "engineering" / "insights.db"
    _fixture(investment, audience="investment", run_id="investment")
    _fixture(engineering, audience="ai_engineering", run_id="engineering")
    target, evaluated_report = _write_reconciliation_report(
        tmp_path, [investment, engineering]
    )
    target.write_text(mutate(target.read_text()))
    monkeypatch.setattr(insight_store, "DEFAULT_INSIGHTS_ROOT", tmp_path)
    monkeypatch.setattr(
        insight_store.audience_insight_production_reconciliation,
        "evaluate_manifest",
        lambda _path: evaluated_report,
    )

    assert insight_store.insight_dates_payload(audience="investment")["dates"] == []


def test_insight_dates_api_validates_and_filters_audience(tmp_path, monkeypatch):
    investment = tmp_path / "run" / "investment" / "insights.db"
    engineering = tmp_path / "run" / "ai_engineering" / "insights.db"
    _fixture(investment, audience="investment")
    _fixture(
        engineering,
        audience="ai_engineering",
    )
    _, report = _write_reconciliation_report(
        tmp_path, [investment, engineering]
    )
    monkeypatch.setattr(insight_store, "DEFAULT_INSIGHTS_ROOT", tmp_path)
    monkeypatch.setattr(
        insight_store.audience_insight_production_reconciliation,
        "evaluate_manifest",
        lambda _path: report,
    )

    response = client.get("/api/insights/dates?audience=ai_engineering")
    assert response.status_code == 200
    assert response.json()["dates"] == [
        {"day": "2026-07-11", "item_count": 1}
    ]
    assert client.get("/api/insights?audience=wrong").status_code == 422


def test_web_fails_closed_without_complete_exact_publication_audit(tmp_path):
    db = tmp_path / "run" / "investment" / "insights.db"
    _fixture(db, audit=False)

    assert insight_store.insight_dates_payload(
        audience="investment", run_root=tmp_path
    )["dates"] == []
    missing = insight_store.insights_payload(
        audience="investment", db_path=db
    )
    assert missing["available"] is False
    assert missing["items"] == []
    assert missing["reason"] == "The independent publication audit has not passed."

    audit_db = _passing_audit(db)
    audit_conn = sqlite3.connect(audit_db)
    audit_conn.execute(
        "UPDATE audit_item SET status = 'pending' WHERE sample_kind = 'selected'"
    )
    audit_conn.commit()
    audit_conn.close()
    assert insight_store.insights_payload(
        audience="investment", db_path=db
    )["available"] is False


def test_web_rejects_stale_or_mismatched_publication_audit(tmp_path):
    db = tmp_path / "run" / "investment" / "insights.db"
    _fixture(db)
    conn = audience_insight_runs.connect_run(db)
    with conn:
        conn.execute(
            "UPDATE candidate_item SET claim = 'Mutated after audit' "
            "WHERE candidate_id = 'candidate-1'"
        )
    conn.close()

    assert insight_store.insight_dates_payload(
        audience="investment", run_root=tmp_path
    )["dates"] == []
    payload = insight_store.insights_payload(audience="investment", db_path=db)
    assert payload["available"] is False
    assert payload["items"] == []


def test_web_and_dates_consume_validated_finalized_zero_projection(tmp_path):
    db = tmp_path / "run" / "investment" / "finalized" / "insights.db"
    _make_finalizable_run(db)

    dates = insight_store.insight_dates_payload(
        audience="investment", run_root=tmp_path
    )
    assert dates["dates"] == [{"day": "2026-07-11", "item_count": 0}]
    payload = insight_store.insights_payload(
        audience="investment", db_path=db
    )
    assert payload["available"] is False
    assert payload["items"] == []
    assert payload["run"]["selected_count"] == 0
    assert payload["run"]["editor_selected_count"] == 2
    assert payload["run"]["publication_finalization"]["reason_code"] == (
        "publication_audit_disqualification"
    )
    assert payload["run"]["publication_finalization"]["removed_candidate_ids"] == [
        "candidate-1"
    ]

    finalization = audience_insight_publication_audit.default_finalization_path(db)
    sidecar = json.loads(finalization.read_text())
    sidecar["audit_result_sha256"] = "stale"
    finalization.write_text(json.dumps(sidecar))
    assert insight_store.insight_dates_payload(
        audience="investment", run_root=tmp_path
    )["dates"] == []
    stale = insight_store.insights_payload(audience="investment", db_path=db)
    assert stale["available"] is False
    assert stale["items"] == []


def test_web_publishes_survivor_from_validated_nonzero_finalization(tmp_path):
    db = tmp_path / "run" / "investment" / "finalized-trim" / "insights.db"
    _fixture(db, audit=False)
    _add_review_reject(db)
    conn = audience_insight_runs.connect_run(db)
    now = "2026-07-14T12:06:00+00:00"
    original_input = json.dumps(
        {
            "selected": [
                {"candidate_id": "candidate-1"},
                {"candidate_id": "candidate-2"},
                {"candidate_id": "candidate-3"},
            ]
        }
    )
    active_input = json.dumps(
        {
            "selected": [
                {"candidate_id": "candidate-1"},
                {"candidate_id": "candidate-2"},
            ]
        }
    )
    with conn:
        conn.execute(
            """INSERT INTO candidate_item
               (candidate_id, event_id, day, feed_rank, packet_json, input_text,
                input_sha256, prompt_cache_key, status, attempts, outcome,
                claim, input_tokens, cached_tokens, reported_cost_usd, updated_at)
               VALUES ('candidate-3', 'event-3', '2026-07-11', 6, '{}', 'input',
                       'sha3', 'cache', 'failed', 1, 'insight', 'Trimmed tail',
                       1500, 0, 0.0, ?)""",
            (now,),
        )
        conn.execute(
            """INSERT INTO daily_selection
               (editorial_rank, candidate_id, decision_value, audit_reason)
               VALUES (2, 'candidate-2', 'watchlist_or_exposure',
                       'The editor selected this second item.')"""
        )
        conn.execute(
            """INSERT INTO daily_selection
               (editorial_rank, candidate_id, decision_value, audit_reason)
               VALUES (3, 'candidate-3', 'watchlist_or_exposure',
                       'The original editor selected this padding tail.')"""
        )
        conn.execute(
            """INSERT INTO publication_selection
               (publication_rank, original_editorial_rank,
                candidate_id, activated_at)
               VALUES (2, 2, 'candidate-2', ?)""",
            (now,),
        )
        conn.execute("UPDATE editor_run SET selected_count = 3 WHERE singleton = 1")
        conn.execute(
            "UPDATE quality_gate SET result_json = ? WHERE singleton = 1",
            (json.dumps({"passed": True, "selected_count": 2}),),
        )
        conn.execute(
            """INSERT INTO day_set_review
               (singleton, status, attempts, input_text, input_sha256,
                prompt_cache_key, duplicate_pairs_json, padding_detected,
                thin_day_honest, set_rationale, updated_at)
               VALUES (1, 'complete', 1, ?, 'original-review-sha',
                       'review-cache', '[]', 1, 1,
                       'The third item is padding on an honest thin day.', ?)""",
            (original_input, now),
        )
        conn.execute(
            """INSERT INTO selection_reconciliation
               (singleton, status, reason_code, source_review_input_sha256,
                source_review_response_id, original_selected_ids_json,
                active_selected_ids_json, removed_candidate_id,
                removed_editorial_rank, created_at, completed_at, updated_at)
               VALUES (1, 'complete', 'padding_tail_trim',
                       'original-review-sha', 'review-response', ?, ?,
                       'candidate-3', 3, ?, ?, ?)""",
            (
                json.dumps(["candidate-1", "candidate-2", "candidate-3"]),
                json.dumps(["candidate-1", "candidate-2"]),
                now,
                now,
                now,
            ),
        )
        conn.execute(
            """INSERT INTO reconciled_day_set_review
               (singleton, status, attempts, reconciliation_reason,
                source_review_input_sha256, input_text, input_sha256,
                prompt_cache_key, duplicate_pairs_json, padding_detected,
                thin_day_honest, set_rationale, updated_at)
               VALUES (1, 'complete', 1, 'padding_tail_trim',
                       'original-review-sha', ?, 'active-review-sha',
                       'active-review-cache', '[]', 0, 1,
                       'The two survivors are honest and not padding.', ?)""",
            (active_input, now),
        )
    conn.close()

    audit_db = _passing_audit(db, failed_selected_ids={"candidate-1"})
    audience_insight_publication_audit.create_publication_finalization(
        source_run_db=db,
        audit_db=audit_db,
    )

    dates = insight_store.insight_dates_payload(
        audience="investment", run_root=tmp_path
    )
    assert dates["dates"] == [{"day": "2026-07-11", "item_count": 1}]
    payload = insight_store.insights_payload(audience="investment", db_path=db)

    assert payload["available"] is True
    assert [item["candidate_id"] for item in payload["items"]] == ["candidate-2"]
    assert payload["items"][0]["editorial_rank"] == 2
    assert payload["items"][0]["original_editorial_rank"] == 2
    assert payload["run"]["selected_count"] == 1
    assert payload["run"]["editor_selected_count"] == 3
    assert payload["run"]["selection_reconciliation"] == {
        "reason_code": "padding_tail_trim",
        "status": "complete",
        "removed_candidate_id": "candidate-3",
        "removed_editorial_rank": 3,
        "original_selected_count": 3,
        "active_selected_count": 2,
    }
    assert payload["run"]["publication_finalization"]["reason_code"] == (
        "publication_audit_disqualification"
    )
    assert payload["run"]["publication_finalization"]["removed_candidate_ids"] == [
        "candidate-1"
    ]
    assert payload["run"]["publication_finalization"]["finalization_sha256"]

    projection = audience_insight_publication_audit.validated_publication_projection(
        source_run_db=db,
        audit_db=audit_db,
    )
    assert projection["mode"] == "audit_disqualified_trim"
    assert projection["effective_selected_ids"] == ["candidate-2"]
    source_conn = sqlite3.connect(db)
    source_rows = source_conn.execute(
        "SELECT candidate_id FROM publication_selection ORDER BY publication_rank"
    ).fetchall()
    source_conn.close()
    assert source_rows == [("candidate-1",), ("candidate-2",)]


def test_false_negative_requires_exact_would_not_enter_adjudication(tmp_path):
    db = tmp_path / "run" / "investment" / "insights.db"
    _fixture(db, audit=False)
    _add_review_reject(db)
    audit_db = _passing_audit(db)

    unresolved = insight_store.insights_payload(
        audience="investment", db_path=db
    )
    assert unresolved["available"] is False
    assert unresolved["items"] == []

    adjudications = _write_false_negative_adjudications(audit_db)
    cleared = insight_store.insights_payload(
        audience="investment", db_path=db
    )
    assert cleared["available"] is True
    assert [item["candidate_id"] for item in cleared["items"]] == ["candidate-1"]

    payload = json.loads(adjudications.read_text())
    payload["audit_result_sha256"] = "stale"
    adjudications.write_text(json.dumps(payload))
    assert insight_store.insights_payload(
        audience="investment", db_path=db
    )["available"] is False

    _write_false_negative_adjudications(audit_db, verdict="would_enter")
    assert insight_store.insights_payload(
        audience="investment", db_path=db
    )["available"] is False
