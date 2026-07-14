import sqlite3

from fastapi.testclient import TestClient

from fli import cited_insight_runs
from fli.web import insights as insight_store
from fli.web.app import app


client = TestClient(app)


def _fixture(path):
    conn = cited_insight_runs.connect_run(path)
    with conn:
        conn.execute(
            """INSERT INTO run_meta
               (singleton, run_id, day, model, reasoning_effort,
                prompt_version, prompt_sha256, schema_version,
                source_triage_db, source_artifact_db, event_ids_json,
                cohort_sha256, expected_count, created_at, updated_at)
               VALUES (1, 'test-run', '2026-07-11', 'gpt-test', 'medium',
                       'insight-v1.1', 'prompt', 'schema', 'triage.db',
                       'artifacts.db', '[]', 'cohort', 2, 'now', 'now')"""
        )
        values = (
            "2026-07-11", 1, "{}", "input", "sha", "cache", 1,
            "insight", "Claim", "Why", "Investor", "Engineer", "Exact quote",
            "x_post", "post-1", "https://x.com/a/status/1", "@a", None,
            1, 1500, 1280, 100, 0.01, "now", "now",
        )
        conn.execute(
            """INSERT INTO insight_item
               (event_id, day, current_rank, packet_json, input_text,
                input_sha256, prompt_cache_key, status, attempts, outcome,
                claim, why_it_matters, investment_implication,
                engineering_implication, supporting_quote,
                citation_source_type, citation_source_id, citation_source_url,
                citation_source_author, citation_source_title,
                citation_matching_source_count, input_tokens, cached_tokens,
                output_tokens, reported_cost_usd, completed_at, updated_at)
               VALUES ('verified', ?, ?, ?, ?, ?, ?, 'complete', ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            values,
        )
        conn.execute(
            """INSERT INTO insight_item
               (event_id, day, current_rank, packet_json, input_text,
                input_sha256, prompt_cache_key, status, attempts, outcome,
                claim, input_tokens, cached_tokens, reported_cost_usd, updated_at)
               VALUES ('failed', '2026-07-11', 2, '{}', 'input', 'sha2',
                       'cache', 'failed', 1, 'insight', 'Rejected claim',
                       1500, 0, 0.02, 'now')"""
        )
    conn.close()


def test_insights_api_returns_only_citation_verified_rows(tmp_path, monkeypatch):
    db = tmp_path / "insights.db"
    _fixture(db)
    monkeypatch.setattr(insight_store, "DEFAULT_INSIGHTS_DB", db)

    response = client.get("/api/insights")
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["run"]["verified_count"] == 1
    assert payload["run"]["failed_count"] == 1
    assert payload["run"]["cache_hit_requests"] == 1
    assert payload["run"]["reported_cost_usd"] == 0.03
    assert [item["event_id"] for item in payload["items"]] == ["verified"]
    assert payload["items"][0]["citation"]["quote"] == "Exact quote"


def test_insights_read_model_is_honest_when_missing(tmp_path):
    payload = insight_store.insights_payload(db_path=tmp_path / "missing.db")
    assert payload["available"] is False
    assert payload["items"] == []


def test_insight_dates_and_day_selection_use_latest_run_per_day(tmp_path):
    older = tmp_path / "older" / "insights.db"
    newer = tmp_path / "newer" / "insights.db"
    _fixture(older)
    _fixture(newer)
    conn = sqlite3.connect(newer)
    conn.execute(
        "UPDATE run_meta SET run_id = 'newer-run', updated_at = 'tomorrow'"
    )
    conn.commit()
    conn.close()

    dates = insight_store.insight_dates_payload(
        run_root=tmp_path,
        default_db=tmp_path / "missing.db",
    )
    assert dates == {
        "available": True,
        "reason": None,
        "latest_date": "2026-07-11",
        "dates": [{"day": "2026-07-11", "item_count": 1}],
    }
    payload = insight_store.insights_payload(
        day="2026-07-11",
        run_root=tmp_path,
    )
    assert payload["run"]["run_id"] == "newer-run"


def test_insight_dates_api_uses_materialized_runs(tmp_path, monkeypatch):
    db = tmp_path / "run" / "insights.db"
    _fixture(db)
    monkeypatch.setattr(insight_store, "DEFAULT_INSIGHTS_ROOT", tmp_path)
    monkeypatch.setattr(
        insight_store, "DEFAULT_INSIGHTS_DB", tmp_path / "missing.db"
    )

    response = client.get("/api/insights/dates")
    assert response.status_code == 200
    assert response.json()["dates"] == [
        {"day": "2026-07-11", "item_count": 1}
    ]
