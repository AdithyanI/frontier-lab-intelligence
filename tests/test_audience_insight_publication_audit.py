import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from fli import (
    audience_insight_evaluations,
    audience_insight_publication_audit as publication_audit,
    audience_insight_runs,
    llm_responses,
)


class FakeClient:
    pass


class FakeRawResponse:
    def __init__(self, response):
        self.response = response
        self.headers = {"x-litellm-response-cost": "0.004"}

    def parse(self):
        return self.response


class FakeRawAPI:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = SimpleNamespace(
            id="resp-independent-audit",
            model=kwargs["model"],
            status="completed",
            output_text=json.dumps(self.payload),
            usage=SimpleNamespace(
                input_tokens=1300,
                input_tokens_details=SimpleNamespace(
                    cached_tokens=900, cache_write_tokens=0
                ),
                output_tokens=80,
            ),
        )
        response.model_dump = lambda **_: {
            "id": response.id,
            "model": response.model,
            "status": response.status,
            "output_text": response.output_text,
        }
        return FakeRawResponse(response)


class FakeResponsesClient:
    def __init__(self, payload):
        self.responses = SimpleNamespace(with_raw_response=FakeRawAPI(payload))


def _packet(event_id: str, rank: int) -> str:
    text = f"Researcher reported a bounded result for {event_id}."
    return json.dumps(
        {
            "event_id": event_id,
            "day": "2026-07-11",
            "feed_rank": rank,
            "sources": [
                {
                    "source_type": "x_post",
                    "source_id": f"post-{event_id}",
                    "url": f"https://x.com/researcher/status/{event_id}",
                    "text": text,
                    "author": "@researcher",
                    "title": None,
                    "relation": "root",
                    "source_sha256": "sha-source",
                    "section_ordinal": None,
                    "source_char_start": None,
                    "source_char_end": None,
                }
            ],
        }
    )


def _source_run(path: Path) -> Path:
    conn = audience_insight_runs.connect_run(path)
    now = "2026-07-15T00:00:00+00:00"
    conn.execute(
        """INSERT INTO run_meta
           (singleton, run_id, audience, day, model, reasoning_effort,
            prompt_version, prompt_sha256, input_render_version,
            schema_version, editor_model,
            editor_reasoning_effort, editor_prompt_version,
            editor_prompt_sha256, editor_schema_version, review_model,
            review_reasoning_effort, item_review_prompt_version,
            item_review_prompt_sha256, item_review_schema_version,
            day_review_prompt_version, day_review_prompt_sha256,
            day_review_schema_version, source_triage_db, source_artifact_db,
            rank_limit, event_ids_json, cohort_sha256, expected_count,
            created_at, updated_at)
           VALUES (1, 'source-run', 'investment', '2026-07-11', 'luna', 'medium',
                   'investment-insight-v2.1', 'extract-sha', 'provider-safe-v2',
                   'extract-schema',
                   'luna', 'high', 'investment-daily-editor-v2.1', 'editor-sha',
                   'editor-schema', 'luna', 'high', 'filter-v2', 'filter-sha',
                   'filter-schema', 'day-v2', 'day-sha', 'day-schema',
                   'triage.db', 'artifact.db', 50, '[]', 'cohort', 4, ?, ?)""",
        (now, now),
    )
    rows = (
        ("selected", 8, True, True),
        ("reject-high", 2, False, False),
        ("reject-second", 5, False, False),
        ("unselected-pass", 1, False, True),
    )
    for candidate_id, rank, selected, review_pass in rows:
        event_id = f"event-{rank}"
        quote = f"Researcher reported a bounded result for {event_id}."
        conn.execute(
            """INSERT INTO candidate_item
               (candidate_id, event_id, day, feed_rank, packet_json, input_text,
                input_sha256, prompt_cache_key, status, outcome, claim,
                claim_posture, why_it_matters, audience_fields_json,
                supporting_quote, citation_block_index, citation_source_type,
                citation_source_id, citation_source_url, citation_source_author,
                citation_source_sha256, citation_char_start, citation_char_end,
                updated_at)
               VALUES (?, ?, '2026-07-11', ?, ?, 'source input', ?, ?, 'complete',
                       'insight', ?, 'third_party_observation', ?, ?, ?, 1,
                       'x_post', ?, ?, '@researcher', 'sha-source', 0, ?, ?)""",
            (
                candidate_id,
                event_id,
                rank,
                _packet(event_id, rank),
                f"sha-{candidate_id}",
                f"cache-{candidate_id}",
                f"Researcher reported a bounded result for {event_id}.",
                "If validated, the result could sharpen a product diligence question.",
                json.dumps(
                    {
                        "investment_implication": "If validated, compare the named product's execution risk.",
                        "what_to_watch": "Check whether an independent evaluation reproduces the bounded result.",
                    }
                ),
                quote,
                f"post-{event_id}",
                f"https://x.com/researcher/status/{event_id}",
                len(quote),
                now,
            ),
        )
        judgment = "pass" if review_pass or selected else "fail"
        conn.execute(
            """INSERT INTO item_review
               (candidate_id, status, attempts, input_text, input_sha256,
                prompt_cache_key, claim_fidelity, epistemic_discipline,
                audience_usefulness, actionability, specificity,
                failure_codes_json, rationale, updated_at)
               VALUES (?, 'complete', 1, 'review input', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                candidate_id,
                f"review-sha-{candidate_id}",
                f"review-cache-{candidate_id}",
                judgment,
                judgment,
                judgment,
                judgment,
                judgment,
                "[]" if judgment == "pass" else '["not_decision_relevant"]',
                "This rationale must never enter the independent audit input.",
                now,
            ),
        )
        if selected:
            conn.execute(
                """INSERT INTO daily_selection
                   (editorial_rank, candidate_id, decision_value, audit_reason,
                    updates_prior_id)
                   VALUES (1, ?, 'diligence_question', 'editor-only secret', NULL)""",
                (candidate_id,),
            )
            conn.execute(
                """INSERT INTO publication_selection
                   (publication_rank, original_editorial_rank,
                    candidate_id, activated_at)
                   VALUES (1, 1, ?, ?)""",
                (candidate_id, now),
            )
    conn.commit()
    conn.close()
    return path


def _finalizable_source_run(path: Path, *, active_count: int = 1) -> Path:
    if active_count not in {1, 2}:
        raise ValueError("test helper supports one or two active items")
    path = _source_run(path)
    conn = audience_insight_runs.connect_run(path)
    now = "2026-07-15T00:10:00+00:00"
    base_ids = ["selected"]
    original_ids = ["selected", "unselected-pass"]
    if active_count == 2:
        base_ids.append("unselected-pass")
        original_ids.append("reject-second")
    original_input = json.dumps(
        {"selected": [{"candidate_id": candidate_id} for candidate_id in original_ids]}
    )
    active_input = json.dumps(
        {"selected": [{"candidate_id": candidate_id} for candidate_id in base_ids]}
    )
    with conn:
        if active_count == 2:
            conn.execute(
                """UPDATE item_review
                   SET claim_fidelity = 'pass', epistemic_discipline = 'pass',
                       audience_usefulness = 'pass', actionability = 'pass',
                       specificity = 'pass', failure_codes_json = '[]'
                   WHERE candidate_id = 'reject-second'"""
            )
        conn.execute(
            """INSERT INTO editor_run
               (singleton, status, attempts, candidate_set_sha256,
                history_sha256, prior_selected_json, input_text,
                prompt_cache_key, selected_count, thin_day_reason, updated_at)
               VALUES (1, 'complete', 1, 'candidate-set', 'history', '[]',
                       'editor input', 'editor-cache', ?,
                       'Only a thin set cleared the editor bar.', ?)""",
            (len(original_ids), now),
        )
        conn.execute(
            """INSERT INTO daily_selection
               (editorial_rank, candidate_id, decision_value, audit_reason)
               VALUES (2, 'unselected-pass', 'watchlist_or_exposure',
                       'The editor selected this lower-ranked tail.')"""
        )
        if active_count == 2:
            conn.execute(
                """INSERT INTO daily_selection
                   (editorial_rank, candidate_id, decision_value, audit_reason)
                   VALUES (3, 'reject-second', 'implementation_choice',
                           'The editor selected this eventual padding tail.')"""
            )
            conn.execute(
                """INSERT INTO publication_selection
                   (publication_rank, original_editorial_rank,
                    candidate_id, activated_at)
                   VALUES (2, 2, 'unselected-pass', ?)""",
                (now,),
            )
        conn.execute(
            """INSERT INTO day_set_review
               (singleton, status, attempts, input_text, input_sha256,
                prompt_cache_key, duplicate_pairs_json, padding_detected,
                thin_day_honest, set_rationale, updated_at)
               VALUES (1, 'complete', 1, ?, 'original-review-sha',
                       'day-review-cache', '[]', 1, 1,
                       'The final item is padding on an honest thin day.', ?)""",
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
                       ?, ?, ?, ?, ?)""",
            (
                json.dumps(original_ids),
                json.dumps(base_ids),
                original_ids[-1],
                len(original_ids),
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
                       'reconciled-review-cache', '[]', 0, 1,
                       'The surviving set is honest and not padding.', ?)""",
            (active_input, now),
        )
        conn.execute(
            """INSERT INTO quality_gate
               (singleton, passed, result_json, computed_at)
               VALUES (1, 1, ?, ?)""",
            (json.dumps({"passed": True, "selected_count": len(base_ids)}), now),
        )
    conn.close()
    return path


def _complete_finalization_audit(
    source: Path,
    audit_db: Path,
    *,
    selected_passes: bool = False,
    failed_selected_ids: set[str] | None = None,
    unresolved_false_negative: bool = False,
) -> Path:
    conn = publication_audit.connect(audit_db)
    publication_audit.freeze_audit(
        conn,
        audit_id="finalization-audit",
        source_run_db=source,
        reject_sample_limit=2,
    )
    meta = conn.execute("SELECT * FROM audit_run WHERE singleton = 1").fetchone()
    rows = conn.execute("SELECT * FROM audit_item ORDER BY audit_item_id").fetchall()
    first_reject = True
    for row in rows:
        result = _passing_result(
            str(row["audit_item_id"]),
            request_tags_override=publication_audit.request_tags(
                audience=str(meta["audience"]),
                audit_id=str(meta["audit_id"]),
                day=str(meta["day"]),
            ),
        )
        should_fail_selected = (
            row["sample_kind"] == "selected"
            and not selected_passes
            and (
                failed_selected_ids is None
                or str(row["source_candidate_id"]) in failed_selected_ids
            )
        )
        if should_fail_selected:
            result.update(
                {
                    "actionability": "fail",
                    "specificity": "fail",
                    "failure_codes": [
                        "generic_investment_watchpoint",
                        "vague_or_promotional",
                    ],
                    "rationale": "The selected item is too generic to publish.",
                }
            )
        elif row["sample_kind"] == "review_reject":
            if unresolved_false_negative and first_reject:
                first_reject = False
            else:
                result.update(
                    {
                        "audience_usefulness": "fail",
                        "failure_codes": ["not_decision_relevant"],
                        "rationale": "The reject would not improve the daily set.",
                    }
                )
        result["raw_output_text"] = json.dumps(
            {
                field: result[field]
                for field in publication_audit.OUTPUT_FIELDS
            },
            sort_keys=True,
        )
        publication_audit._store_success(conn, row, meta, result)
    conn.close()
    return audit_db


def _passing_result(
    audit_item_id: str,
    *,
    request_tags_override: tuple[str, ...] | list[str] | None = None,
) -> dict:
    return {
        "audit_item_id": audit_item_id,
        "citation_fidelity": "pass",
        "attribution_fidelity": "pass",
        "epistemic_discipline": "pass",
        "audience_usefulness": "pass",
        "actionability": "pass",
        "specificity": "pass",
        "failure_codes": [],
        "rationale": "The bounded claim, implication, and watchpoint follow from the supplied evidence.",
        "raw_output_text": "{}",
        "response_id": "resp-audit",
        "response_model": "gpt-5.6-luna",
        "input_tokens": 1200,
        "cached_tokens": 800,
        "cache_write_tokens": 0,
        "output_tokens": 100,
        "reported_cost_usd": 0.01,
        "request_tags": list(
            request_tags_override or ["job:publication-calibration-audit"]
        ),
    }


def test_prompt_and_cache_namespace_are_independent():
    assert publication_audit.PROMPT_VERSION not in {
        *audience_insight_evaluations.ITEM_PROMPT_VERSIONS.values(),
        audience_insight_evaluations.DAY_SET_PROMPT_VERSION,
    }
    key = publication_audit.prompt_cache_key("investment", "audit-123")
    evaluation_key = audience_insight_evaluations.item_prompt_cache_key(
        "investment", "audit-123"
    )
    assert key != evaluation_key
    assert len(key) <= llm_responses.AZURE_PROMPT_CACHE_KEY_MAX_LENGTH
    assert publication_audit.DEFAULT_REASONING_EFFORT == "high"
    assert publication_audit.DEFAULT_MODEL == "gpt-5.6-luna"


def test_completed_audit_validation_is_characterization_not_permission(tmp_path):
    source = _finalizable_source_run(tmp_path / "run" / "insights.db")
    audit = _complete_finalization_audit(
        source,
        source.parent / "publication-audit-v1" / "audit.db",
        selected_passes=False,
    )

    with pytest.raises(ValueError, match="summary did not pass"):
        publication_audit.validate_readonly_publication_audit(
            source_run_db=source,
            audit_db=audit,
            expected_selected_count=1,
        )

    characterization = (
        publication_audit.validate_readonly_completed_publication_audit(
            source_run_db=source,
            audit_db=audit,
            expected_selected_count=1,
        )
    )
    assert characterization["passed"] is False
    assert characterization["selected_metrics"]["total"] == 1
    assert characterization["selected_metrics"]["full_quality_passes"] == 0


def test_validate_output_requires_exact_schema_and_consistent_failures():
    item_id = "audit-123"
    passing = _passing_result(item_id)
    model_payload = {field: passing[field] for field in publication_audit.OUTPUT_FIELDS}
    assert publication_audit.validate_output(
        json.dumps(model_payload), expected_audit_item_id=item_id
    )["specificity"] == "pass"

    model_payload["citation_fidelity"] = "fail"
    with pytest.raises(ValueError, match="failure_codes"):
        publication_audit.validate_output(
            json.dumps(model_payload), expected_audit_item_id=item_id
        )
    model_payload["failure_codes"] = ["claim_not_supported"]
    model_payload["extra"] = "forbidden"
    with pytest.raises(ValueError, match="exact"):
        publication_audit.validate_output(
            json.dumps(model_payload), expected_audit_item_id=item_id
        )


def test_evaluate_item_uses_independent_strict_luna_high_request():
    item_id = "audit-123"
    payload = {
        field: value
        for field, value in _passing_result(item_id).items()
        if field in publication_audit.OUTPUT_FIELDS
    }
    client = FakeResponsesClient(payload)
    result = publication_audit.evaluate_item(
        client,
        {
            "audit_item_id": item_id,
            "input_text": '{"audit_item_id":"audit-123"}',
            "prompt_cache_key": publication_audit.prompt_cache_key(
                "investment", item_id
            ),
        },
        meta={
            "audience": "investment",
            "audit_id": "audit-run",
            "day": "2026-07-11",
            "model": "gpt-5.6-luna",
            "reasoning_effort": "high",
        },
    )
    request = client.responses.with_raw_response.calls[0]
    assert request["reasoning"] == {"effort": "high"}
    assert request["text"]["format"]["schema"]["properties"]["audit_item_id"] == {
        "type": "string",
        "enum": [item_id],
    }
    assert request["store"] is False
    assert request["prompt_cache_key"] == publication_audit.prompt_cache_key(
        "investment", item_id
    )
    assert len(request["prompt_cache_key"]) <= 64
    assert "job:publication-calibration-audit" in request["extra_body"]["metadata"]["tags"]
    assert result["reported_cost_usd"] == 0.004
    assert result["cached_tokens"] == 900


def test_freeze_blinds_source_decisions_and_samples_highest_ranked_rejects(tmp_path):
    source = _source_run(tmp_path / "source.db")
    conn = publication_audit.connect(tmp_path / "audit.db")
    assert publication_audit.freeze_audit(
        conn,
        audit_id="calibration-audit",
        source_run_db=source,
        reject_sample_limit=2,
    ) == 3
    assert publication_audit.freeze_audit(
        conn,
        audit_id="calibration-audit",
        source_run_db=source,
        reject_sample_limit=2,
    ) == 3

    rows = conn.execute(
        """SELECT audit_item_id, source_candidate_id, sample_kind,
                  source_feed_rank, input_text
           FROM audit_item ORDER BY sample_kind, source_feed_rank"""
    ).fetchall()
    assert [(row["source_candidate_id"], row["source_feed_rank"]) for row in rows if row["sample_kind"] == "review_reject"] == [
        ("reject-high", 2),
        ("reject-second", 5),
    ]
    for row in rows:
        assert row["audit_item_id"] in {"audit-01", "audit-02", "audit-03"}
        rendered = row["input_text"]
        assert row["source_candidate_id"] not in rendered
        assert "feed_rank" not in rendered
        assert "sample_kind" not in rendered
        assert "editor-only secret" not in rendered
        assert "This rationale must never" not in rendered
        assert "failure_codes" not in rendered
        assert "audit-" in rendered
    frozen_summary = publication_audit.summary(conn)
    assert frozen_summary["run"]["audience"] == "investment"
    assert frozen_summary["passed"] is False
    assert frozen_summary["checks"]["audit_cohort_complete"] is False
    conn.close()


def test_new_short_ids_are_deterministic_blinded_and_bound_immutably(tmp_path):
    source = _source_run(tmp_path / "source.db")
    conn = publication_audit.connect(tmp_path / "audit.db")
    publication_audit.freeze_audit(
        conn,
        audit_id="calibration-audit",
        source_run_db=source,
        reject_sample_limit=2,
    )
    first = {
        row["source_candidate_id"]: row["audit_item_id"]
        for row in conn.execute(
            "SELECT source_candidate_id, audit_item_id FROM audit_item"
        )
    }
    expected = publication_audit._new_audit_item_ids(
        audit_id="calibration-audit",
        audience="investment",
        source_candidate_ids=first,
    )
    assert first == expected
    assert set(first.values()) == {"audit-01", "audit-02", "audit-03"}

    selected_id = conn.execute(
        "SELECT audit_item_id FROM audit_item WHERE sample_kind = 'selected'"
    ).fetchone()[0]
    # The blinded ordering is not a publication or Feed-rank sequence.
    assert selected_id != "audit-01"

    conn.execute(
        "UPDATE audit_item SET input_text = input_text || ' tampered' WHERE audit_item_id = ?",
        (selected_id,),
    )
    conn.commit()
    with pytest.raises(ValueError, match=r"audit_item\..*\.input_text"):
        publication_audit.freeze_audit(
            conn,
            audit_id="calibration-audit",
            source_run_db=source,
            reject_sample_limit=2,
        )
    conn.close()


def test_legacy_long_ids_remain_readable_and_resumable(
    tmp_path, monkeypatch
):
    source = _source_run(tmp_path / "source.db")
    conn = publication_audit.connect(tmp_path / "legacy-audit.db")

    def legacy_ids(*, audit_id, audience, source_candidate_ids):
        del audit_id
        return {
            candidate_id: publication_audit._legacy_audit_item_id(
                audience, candidate_id
            )
            for candidate_id in source_candidate_ids
        }

    with monkeypatch.context() as patch:
        patch.setattr(publication_audit, "_new_audit_item_ids", legacy_ids)
        publication_audit.freeze_audit(
            conn,
            audit_id="legacy-calibration-audit",
            source_run_db=source,
            reject_sample_limit=1,
        )

    legacy_ids_in_db = [
        row[0]
        for row in conn.execute("SELECT audit_item_id FROM audit_item")
    ]
    assert all(len(item_id) == 26 for item_id in legacy_ids_in_db)
    # Refreezing after the code upgrade reuses, rather than rewrites, IDs and inputs.
    assert publication_audit.freeze_audit(
        conn,
        audit_id="legacy-calibration-audit",
        source_run_db=source,
        reject_sample_limit=1,
    ) == 2

    recovering_id = legacy_ids_in_db[0]

    def identity_failure_then_pass(_client, row, *, meta):
        if row["audit_item_id"] == recovering_id and int(row["attempts"]) < 2:
            raise publication_audit.AuditValidationError(
                "auditor returned the wrong audit_item_id",
                result={"raw_output_text": "{}"},
            )
        return _passing_result(row["audit_item_id"])

    monkeypatch.setattr(
        publication_audit, "evaluate_item", identity_failure_then_pass
    )
    first = publication_audit.run_pending(conn, client=FakeClient(), workers=2)
    assert first["passed"] is False
    second = publication_audit.run_pending(
        conn, client=FakeClient(), workers=2, retry_failed=True
    )
    assert second["passed"] is False
    assert tuple(
        conn.execute(
            "SELECT status, attempts FROM audit_item WHERE audit_item_id = ?",
            (recovering_id,),
        ).fetchone()
    ) == ("rejected", 2)

    # The explicit retry path grants one migration recovery attempt only for a
    # legacy long ID terminally rejected by the historical echo-copy failure.
    report = publication_audit.run_pending(
        conn, client=FakeClient(), workers=2, retry_failed=True
    )
    assert report["passed"] is True
    assert tuple(
        conn.execute(
            "SELECT status, attempts FROM audit_item WHERE audit_item_id = ?",
            (recovering_id,),
        ).fetchone()
    ) == ("complete", 3)
    assert all(
        row[0] == "complete"
        for row in conn.execute("SELECT status FROM audit_item")
    )
    conn.close()


def test_run_is_resumable_and_attempts_keep_separate_provenance(tmp_path, monkeypatch):
    source = _source_run(tmp_path / "source.db")
    conn = publication_audit.connect(tmp_path / "audit.db")
    publication_audit.freeze_audit(
        conn,
        audit_id="calibration-audit",
        source_run_db=source,
        reject_sample_limit=1,
    )
    first_id = conn.execute(
        "SELECT audit_item_id FROM audit_item ORDER BY audit_item_id LIMIT 1"
    ).fetchone()[0]

    def first_pass(_client, row, *, meta):
        if row["audit_item_id"] == first_id:
            raise publication_audit.AuditValidationError(
                "schema drift",
                result={
                    "raw_output_text": "not-json",
                    "response_id": "resp-invalid",
                    "response_model": "gpt-5.6-luna",
                    "input_tokens": 1100,
                    "cached_tokens": 0,
                    "cache_write_tokens": 0,
                    "output_tokens": 20,
                    "reported_cost_usd": 0.005,
                    "request_tags": ["job:publication-calibration-audit"],
                },
            )
        return _passing_result(row["audit_item_id"])

    monkeypatch.setattr(publication_audit, "evaluate_item", first_pass)
    first = publication_audit.run_pending(conn, client=FakeClient(), workers=2)
    assert first["attempts"]["count"] == 2
    failed = conn.execute(
        "SELECT status, attempts FROM audit_item WHERE audit_item_id = ?", (first_id,)
    ).fetchone()
    assert tuple(failed) == ("failed", 1)

    monkeypatch.setattr(
        publication_audit,
        "evaluate_item",
        lambda _client, row, *, meta: _passing_result(row["audit_item_id"]),
    )
    final = publication_audit.run_pending(
        conn, client=FakeClient(), workers=2, retry_failed=True
    )
    assert final["passed"] is True
    assert final["attempts"]["count"] == 3
    attempts = conn.execute(
        """SELECT attempt_number, status, raw_output_text, prompt_version,
                  input_sha256, request_tags_json
           FROM audit_attempt WHERE audit_item_id = ? ORDER BY attempt_number""",
        (first_id,),
    ).fetchall()
    assert [(row["attempt_number"], row["status"]) for row in attempts] == [
        (1, "failed"),
        (2, "complete"),
    ]
    assert attempts[0]["raw_output_text"] == "not-json"
    assert all(row["prompt_version"] == publication_audit.PROMPT_VERSION for row in attempts)
    conn.close()


def test_summary_separates_selected_gate_from_reject_false_negatives(tmp_path):
    source = _source_run(tmp_path / "source.db")
    conn = publication_audit.connect(tmp_path / "audit.db")
    publication_audit.freeze_audit(
        conn,
        audit_id="calibration-audit",
        source_run_db=source,
        reject_sample_limit=2,
    )
    rows = conn.execute("SELECT * FROM audit_item ORDER BY audit_item_id").fetchall()
    meta = conn.execute("SELECT * FROM audit_run WHERE singleton = 1").fetchone()
    for row in rows:
        result = _passing_result(row["audit_item_id"])
        if row["source_candidate_id"] == "reject-second":
            result.update(
                {
                    "audience_usefulness": "fail",
                    "failure_codes": ["not_decision_relevant"],
                    "rationale": "The item does not sharpen an audience decision.",
                }
            )
        publication_audit._store_success(conn, row, meta, result)
    report = publication_audit.summary(conn)
    assert report["passed"] is True
    assert report["selected_metrics"]["full_quality_ratio"] == 1.0
    assert report["false_negative_review_rejects"]["count"] == 1
    assert report["duplicate_and_padding_scope"].startswith("evaluated separately")

    selected_id = conn.execute(
        "SELECT audit_item_id FROM audit_item WHERE sample_kind = 'selected'"
    ).fetchone()[0]
    conn.execute(
        "UPDATE audit_item SET attribution_fidelity = 'fail' WHERE audit_item_id = ?",
        (selected_id,),
    )
    conn.commit()
    assert publication_audit.summary(conn)["passed"] is False
    conn.close()


def test_validate_cli_routes_through_exact_readonly_boundary(
    tmp_path, monkeypatch, capsys
):
    source = tmp_path / "source.db"
    audit = tmp_path / "publication-audit-v1" / "audit.db"
    captured = {}

    def validate(*, source_run_db, audit_db, expected_selected_count):
        captured.update(
            {
                "source_run_db": source_run_db,
                "audit_db": audit_db,
                "expected_selected_count": expected_selected_count,
            }
        )
        return {"passed": True, "false_negative_adjudication": {"passed": True}}

    monkeypatch.setattr(
        publication_audit, "validate_readonly_publication_audit", validate
    )
    assert (
        publication_audit.main(
            [
                "validate",
                "--source-run-db",
                str(source),
                "--audit-db",
                str(audit),
                "--expected-selected-count",
                "2",
            ]
        )
        == 0
    )
    assert captured == {
        "source_run_db": source,
        "audit_db": audit,
        "expected_selected_count": 2,
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "audience-insight-audit.validate"
    assert payload["data"]["passed"] is True


def test_finalization_projects_exact_failed_one_to_zero_without_mutation(tmp_path):
    source = _finalizable_source_run(tmp_path / "run" / "insights.db")
    audit = _complete_finalization_audit(
        source, source.parent / "publication-audit-v1" / "audit.db"
    )
    source_conn = audience_insight_runs.connect_run(source)
    before_daily = [
        tuple(row)
        for row in source_conn.execute(
            "SELECT * FROM daily_selection ORDER BY editorial_rank"
        )
    ]
    before_publication = [
        tuple(row)
        for row in source_conn.execute(
            "SELECT * FROM publication_selection ORDER BY publication_rank"
        )
    ]
    before_reconciliation = tuple(
        source_conn.execute("SELECT * FROM selection_reconciliation").fetchone()
    )
    source_conn.close()
    audit_conn = publication_audit.connect(audit)
    before_audit_digest = publication_audit.audit_result_sha256(audit_conn)
    audit_conn.close()

    result = publication_audit.create_publication_finalization(
        source_run_db=source,
        audit_db=audit,
    )

    assert result["created"] is True
    assert result["effective_selected_ids"] == []
    validation = publication_audit.validate_readonly_publication_finalization(
        source_run_db=source,
        audit_db=audit,
    )
    assert validation["passed"] is True
    assert validation["base_selected_ids"] == ["selected"]
    assert validation["removed_candidate_ids"] == ["selected"]
    assert validation["failed_dimensions"] == {
        "selected": ["actionability", "specificity"]
    }
    projection = publication_audit.validated_publication_projection(
        source_run_db=source,
        audit_db=audit,
    )
    assert projection["mode"] == "audit_disqualified_zero"
    assert projection["effective_selected_ids"] == []

    source_conn = audience_insight_runs.connect_run(source)
    assert [
        tuple(row)
        for row in source_conn.execute(
            "SELECT * FROM daily_selection ORDER BY editorial_rank"
        )
    ] == before_daily
    assert [
        tuple(row)
        for row in source_conn.execute(
            "SELECT * FROM publication_selection ORDER BY publication_rank"
        )
    ] == before_publication
    assert tuple(
        source_conn.execute("SELECT * FROM selection_reconciliation").fetchone()
    ) == before_reconciliation
    source_conn.close()
    audit_conn = publication_audit.connect(audit)
    assert publication_audit.audit_result_sha256(audit_conn) == before_audit_digest
    audit_conn.close()
    with pytest.raises(ValueError, match="already exists"):
        publication_audit.create_publication_finalization(
            source_run_db=source,
            audit_db=audit,
        )


def test_finalization_removes_only_failed_item_from_multi_item_set(tmp_path):
    source = _finalizable_source_run(
        tmp_path / "run" / "insights.db", active_count=2
    )
    audit = _complete_finalization_audit(
        source,
        source.parent / "publication-audit-v1" / "audit.db",
        failed_selected_ids={"unselected-pass"},
    )

    result = publication_audit.create_publication_finalization(
        source_run_db=source,
        audit_db=audit,
    )

    assert result["created"] is True
    assert result["effective_selected_ids"] == ["selected"]
    validation = publication_audit.validate_readonly_publication_finalization(
        source_run_db=source,
        audit_db=audit,
    )
    assert validation["base_selected_ids"] == ["selected", "unselected-pass"]
    assert validation["removed_candidate_ids"] == ["unselected-pass"]
    assert validation["effective_selected_ids"] == ["selected"]
    assert validation["failed_dimensions"] == {
        "unselected-pass": ["actionability", "specificity"]
    }
    projection = publication_audit.validated_publication_projection(
        source_run_db=source,
        audit_db=audit,
    )
    assert projection["mode"] == "audit_disqualified_trim"
    assert projection["base_selected_ids"] == ["selected", "unselected-pass"]
    assert projection["effective_selected_ids"] == ["selected"]
    assert projection["selected_count"] == 1


def test_finalization_removes_failed_item_from_direct_reviewed_set(tmp_path):
    source = _finalizable_source_run(
        tmp_path / "run" / "insights.db", active_count=2
    )
    conn = audience_insight_runs.connect_run(source)
    direct_ids = ["selected", "unselected-pass"]
    with conn:
        conn.execute("DELETE FROM daily_selection WHERE editorial_rank = 3")
        conn.execute("UPDATE editor_run SET selected_count = 2 WHERE singleton = 1")
        conn.execute(
            """UPDATE day_set_review
               SET input_text = ?, input_sha256 = 'direct-review-sha',
                   padding_detected = 0, thin_day_honest = 0,
                   set_rationale = 'The direct two-item set is not padding.'
               WHERE singleton = 1""",
            (
                json.dumps(
                    {
                        "selected": [
                            {"candidate_id": candidate_id}
                            for candidate_id in direct_ids
                        ]
                    }
                ),
            ),
        )
        conn.execute("DELETE FROM selection_reconciliation")
        conn.execute("DELETE FROM reconciled_day_set_review")
    conn.close()
    audit = _complete_finalization_audit(
        source,
        source.parent / "publication-audit-v1" / "audit.db",
        failed_selected_ids={"unselected-pass"},
    )

    result = publication_audit.create_publication_finalization(
        source_run_db=source,
        audit_db=audit,
    )

    assert result["effective_selected_ids"] == ["selected"]
    validation = publication_audit.validate_readonly_publication_finalization(
        source_run_db=source,
        audit_db=audit,
    )
    assert validation["base_selected_ids"] == direct_ids
    assert validation["removed_candidate_ids"] == ["unselected-pass"]
    assert validation["effective_selected_ids"] == ["selected"]
    payload = json.loads(publication_audit.default_finalization_path(source).read_text())
    assert payload["source_padding_reconciliation_sha256"] is None
    assert payload["source_reconciled_day_review_sha256"] is None


def test_passing_audit_is_a_finalization_noop(tmp_path):
    source = _finalizable_source_run(tmp_path / "run" / "insights.db")
    audit = _complete_finalization_audit(
        source,
        source.parent / "publication-audit-v1" / "audit.db",
        selected_passes=True,
    )

    result = publication_audit.create_publication_finalization(
        source_run_db=source,
        audit_db=audit,
    )

    assert result == {
        "created": False,
        "reason_code": "publication_audit_passed",
        "path": str(publication_audit.default_finalization_path(source)),
        "effective_selected_ids": ["selected"],
    }
    assert not publication_audit.default_finalization_path(source).exists()


def test_editorial_finalization_strictly_removes_item_after_passing_audit(tmp_path):
    source = _finalizable_source_run(tmp_path / "run" / "insights.db")
    audit = _complete_finalization_audit(
        source,
        source.parent / "publication-audit-v1" / "audit.db",
        selected_passes=True,
    )
    review = {
        "schema_version": publication_audit.EDITORIAL_REVIEW_SCHEMA_VERSION,
        "review_id": "senior-product-review-2026-07-15",
        "reviewer": "product-owner",
        "removals": [
            {
                "candidate_id": "selected",
                "reason_code": "promotional_or_testimonial_evidence",
                "rationale": (
                    "The item relies on a partner testimonial and overstates it "
                    "as independent market validation."
                ),
            }
        ],
    }

    result = publication_audit.create_editorial_publication_finalization(
        source_run_db=source,
        audit_db=audit,
        editorial_review=review,
    )

    assert result["reason_code"] == "senior_editorial_disqualification"
    assert result["effective_selected_ids"] == []
    validation = publication_audit.validate_readonly_publication_finalization(
        source_run_db=source,
        audit_db=audit,
    )
    assert validation["audit"]["passed"] is True
    assert validation["base_selected_ids"] == ["selected"]
    assert validation["removed_candidate_ids"] == ["selected"]
    assert validation["effective_selected_ids"] == []
    assert validation["editorial_review"] == review
    projection = publication_audit.validated_publication_projection(
        source_run_db=source,
        audit_db=audit,
    )
    assert projection["mode"] == "editorial_disqualified_zero"
    assert projection["selected_count"] == 0


def test_editorial_finalization_fails_closed_on_substitution_or_tampering(tmp_path):
    source = _finalizable_source_run(tmp_path / "run" / "insights.db")
    audit = _complete_finalization_audit(
        source,
        source.parent / "publication-audit-v1" / "audit.db",
        selected_passes=True,
    )
    review = {
        "schema_version": publication_audit.EDITORIAL_REVIEW_SCHEMA_VERSION,
        "review_id": "senior-product-review-2026-07-15",
        "reviewer": "product-owner",
        "removals": [
            {
                "candidate_id": "not-selected",
                "reason_code": "insufficient_decision_value",
                "rationale": "This candidate does not materially sharpen a decision.",
            }
        ],
    }
    with pytest.raises(ValueError, match="only an active selected candidate"):
        publication_audit.create_editorial_publication_finalization(
            source_run_db=source,
            audit_db=audit,
            editorial_review=review,
        )

    review["removals"][0] = {
        "candidate_id": "selected",
        "reason_code": "insufficient_decision_value",
        "rationale": "This candidate does not materially sharpen a decision.",
    }
    publication_audit.create_editorial_publication_finalization(
        source_run_db=source,
        audit_db=audit,
        editorial_review=review,
    )
    path = publication_audit.default_finalization_path(source)
    payload = json.loads(path.read_text())
    payload["editorial_review"]["removals"][0]["rationale"] = "Changed later."
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="editorial_review_sha256"):
        publication_audit.validate_readonly_publication_finalization(
            source_run_db=source,
            audit_db=audit,
        )


def _audit_then_editorial_chain(tmp_path):
    source = _finalizable_source_run(
        tmp_path / "run" / "insights.db", active_count=2
    )
    audit = _complete_finalization_audit(
        source,
        source.parent / "publication-audit-v1" / "audit.db",
        failed_selected_ids={"unselected-pass"},
    )
    publication_audit.create_publication_finalization(
        source_run_db=source,
        audit_db=audit,
    )
    prerequisite = publication_audit.default_finalization_path(source)
    prerequisite_bytes = prerequisite.read_bytes()
    review = {
        "schema_version": publication_audit.EDITORIAL_REVIEW_SCHEMA_VERSION,
        "review_id": "senior-product-review-composed",
        "reviewer": "product-owner",
        "removals": [
            {
                "candidate_id": "selected",
                "reason_code": "insufficient_decision_value",
                "rationale": "The audit survivor does not sharpen a decision.",
            }
        ],
    }
    result = publication_audit.create_editorial_publication_finalization(
        source_run_db=source,
        audit_db=audit,
        editorial_review=review,
    )
    return source, audit, prerequisite, prerequisite_bytes, review, result


def test_composed_editorial_layer_preserves_audit_sidecar_and_history(tmp_path):
    source, audit, prerequisite, prerequisite_bytes, review, result = (
        _audit_then_editorial_chain(tmp_path)
    )

    terminal = publication_audit.default_editorial_finalization_path(source)
    assert result["path"] == str(terminal)
    assert result["prerequisite_finalization_path"] == str(prerequisite)
    assert result["prerequisite_finalization_sha256"] == publication_audit._sha256(
        prerequisite_bytes.decode()
    )
    assert prerequisite.read_bytes() == prerequisite_bytes
    assert terminal.is_file()

    validation = publication_audit.validate_readonly_publication_finalization(
        source_run_db=source,
        audit_db=audit,
    )
    assert validation["base_selected_ids"] == ["selected", "unselected-pass"]
    assert validation["post_audit_selected_ids"] == ["selected"]
    assert validation["removed_candidate_ids"] == ["selected"]
    assert validation["effective_selected_ids"] == []
    assert validation["history_selected_ids"] == ["selected"]
    assert validation["editorial_review"] == review
    assert validation["prerequisite_finalization"]["removed_candidate_ids"] == [
        "unselected-pass"
    ]

    projection = publication_audit.validated_publication_projection(
        source_run_db=source,
        audit_db=audit,
    )
    assert projection["mode"] == "audit_then_editorial_disqualified_zero"
    assert projection["base_selected_ids"] == ["selected", "unselected-pass"]
    assert projection["post_audit_selected_ids"] == ["selected"]
    assert projection["effective_selected_ids"] == []
    assert projection["history_selected_ids"] == ["selected"]


def test_composed_editorial_layer_rejects_audit_failed_candidate(tmp_path):
    source = _finalizable_source_run(
        tmp_path / "run" / "insights.db", active_count=2
    )
    audit = _complete_finalization_audit(
        source,
        source.parent / "publication-audit-v1" / "audit.db",
        failed_selected_ids={"unselected-pass"},
    )
    publication_audit.create_publication_finalization(
        source_run_db=source,
        audit_db=audit,
    )
    review = {
        "schema_version": publication_audit.EDITORIAL_REVIEW_SCHEMA_VERSION,
        "review_id": "invalid-audit-failed-removal",
        "reviewer": "product-owner",
        "removals": [
            {
                "candidate_id": "unselected-pass",
                "reason_code": "insufficient_decision_value",
                "rationale": "This item was already removed by the audit.",
            }
        ],
    }
    with pytest.raises(ValueError, match="active selected candidate"):
        publication_audit.create_editorial_publication_finalization(
            source_run_db=source,
            audit_db=audit,
            editorial_review=review,
        )


def test_composed_editorial_layer_fails_on_prerequisite_drift_or_removal(tmp_path):
    source, audit, prerequisite, prerequisite_bytes, _review, _result = (
        _audit_then_editorial_chain(tmp_path)
    )

    payload = json.loads(prerequisite.read_text())
    payload["effective_selected_ids"] = ["selected", "unselected-pass"]
    prerequisite.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="effective_selected_ids"):
        publication_audit.validated_publication_projection(
            source_run_db=source,
            audit_db=audit,
        )

    prerequisite.write_bytes(prerequisite_bytes)
    prerequisite.unlink()
    with pytest.raises(FileNotFoundError):
        publication_audit.validated_publication_projection(
            source_run_db=source,
            audit_db=audit,
        )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("effective_selected_ids", ["unselected-pass"]),
        ("post_audit_selected_ids", ["unselected-pass", "selected"]),
        ("history_selected_ids", ["unselected-pass"]),
    ],
)
def test_composed_editorial_layer_rejects_promotion_substitution_or_reordering(
    tmp_path, field, replacement
):
    source, audit, _prerequisite, _bytes, _review, _result = (
        _audit_then_editorial_chain(tmp_path)
    )
    terminal = publication_audit.default_editorial_finalization_path(source)
    payload = json.loads(terminal.read_text())
    payload[field] = replacement
    terminal.write_text(json.dumps(payload))

    with pytest.raises(ValueError, match=field):
        publication_audit.validated_publication_projection(
            source_run_db=source,
            audit_db=audit,
        )


def test_composed_editorial_layer_rejects_editorial_prerequisite(tmp_path):
    source = _finalizable_source_run(tmp_path / "run" / "insights.db")
    audit = _complete_finalization_audit(
        source,
        source.parent / "publication-audit-v1" / "audit.db",
        selected_passes=True,
    )
    review = {
        "schema_version": publication_audit.EDITORIAL_REVIEW_SCHEMA_VERSION,
        "review_id": "first-editorial-review",
        "reviewer": "product-owner",
        "removals": [
            {
                "candidate_id": "selected",
                "reason_code": "insufficient_decision_value",
                "rationale": "The item does not sharpen a decision.",
            }
        ],
    }
    publication_audit.create_editorial_publication_finalization(
        source_run_db=source,
        audit_db=audit,
        editorial_review=review,
    )
    with pytest.raises(ValueError, match="prerequisite must be an audit"):
        publication_audit.create_editorial_publication_finalization(
            source_run_db=source,
            audit_db=audit,
            editorial_review=review,
        )


def test_finalization_blocks_unresolved_false_negative_and_stale_source(tmp_path):
    source = _finalizable_source_run(tmp_path / "unresolved" / "insights.db")
    audit = _complete_finalization_audit(
        source,
        source.parent / "publication-audit-v1" / "audit.db",
        unresolved_false_negative=True,
    )
    with pytest.raises(ValueError, match="false negatives have not been adjudicated"):
        publication_audit.create_publication_finalization(
            source_run_db=source,
            audit_db=audit,
        )

    stale_source = _finalizable_source_run(tmp_path / "stale" / "insights.db")
    stale_audit = _complete_finalization_audit(
        stale_source,
        stale_source.parent / "publication-audit-v1" / "audit.db",
    )
    conn = audience_insight_runs.connect_run(stale_source)
    with conn:
        conn.execute(
            "UPDATE candidate_item SET claim = 'Changed after audit' "
            "WHERE candidate_id = 'selected'"
        )
    conn.close()
    with pytest.raises(ValueError, match="no longer matches source"):
        publication_audit.create_publication_finalization(
            source_run_db=stale_source,
            audit_db=stale_audit,
        )


def test_finalization_blocks_terminally_rejected_audit_item(tmp_path):
    source = _finalizable_source_run(tmp_path / "run" / "insights.db")
    audit = _complete_finalization_audit(
        source,
        source.parent / "publication-audit-v1" / "audit.db",
    )
    conn = publication_audit.connect(audit)
    rejected_id = conn.execute(
        "SELECT audit_item_id FROM audit_item "
        "WHERE sample_kind = 'review_reject' LIMIT 1"
    ).fetchone()[0]
    with conn:
        conn.execute(
            "UPDATE audit_item SET status = 'rejected' WHERE audit_item_id = ?",
            (rejected_id,),
        )
    conn.close()

    with pytest.raises(ValueError, match="publication audit is incomplete"):
        publication_audit.create_publication_finalization(
            source_run_db=source,
            audit_db=audit,
        )


def test_publication_validation_binds_exact_attempt_ledger(tmp_path):
    def complete_audit(label: str):
        source = _finalizable_source_run(tmp_path / label / "insights.db")
        audit = _complete_finalization_audit(
            source,
            source.parent / "publication-audit-v1" / "audit.db",
            selected_passes=True,
        )
        return source, audit

    missing_source, missing_audit = complete_audit("missing")
    conn = publication_audit.connect(missing_audit)
    item_id = conn.execute(
        "SELECT audit_item_id FROM audit_item ORDER BY audit_item_id LIMIT 1"
    ).fetchone()[0]
    with conn:
        conn.execute(
            "DELETE FROM audit_attempt WHERE audit_item_id = ?",
            (item_id,),
        )
    conn.close()
    with pytest.raises(ValueError, match="attempt count does not match"):
        publication_audit.validate_readonly_publication_audit(
            source_run_db=missing_source,
            audit_db=missing_audit,
            expected_selected_count=1,
        )

    surplus_source, surplus_audit = complete_audit("surplus")
    conn = publication_audit.connect(surplus_audit)
    row = conn.execute(
        "SELECT * FROM audit_attempt ORDER BY audit_item_id LIMIT 1"
    ).fetchone()
    duplicate = dict(row)
    duplicate["attempt_number"] = int(row["attempt_number"]) + 1
    columns = tuple(duplicate)
    with conn:
        conn.execute(
            f"INSERT INTO audit_attempt ({', '.join(columns)}) "
            f"VALUES ({', '.join('?' for _ in columns)})",
            tuple(duplicate[column] for column in columns),
        )
    conn.close()
    with pytest.raises(ValueError, match="attempt count does not match"):
        publication_audit.validate_readonly_publication_audit(
            source_run_db=surplus_source,
            audit_db=surplus_audit,
            expected_selected_count=1,
        )

    drift_source, drift_audit = complete_audit("drift")
    conn = publication_audit.connect(drift_audit)
    with conn:
        conn.execute(
            """UPDATE audit_item
               SET actionability = 'fail',
                   failure_codes_json = '["generic_investment_watchpoint"]',
                   rationale = 'Mutated after the recorded attempt.'
               WHERE sample_kind = 'selected'"""
        )
    conn.close()
    with pytest.raises(ValueError, match="judgments do not match"):
        publication_audit.validate_readonly_publication_audit(
            source_run_db=drift_source,
            audit_db=drift_audit,
            expected_selected_count=1,
        )


def test_finalization_validation_blocks_drift_and_substitution(tmp_path):
    source = _finalizable_source_run(tmp_path / "run" / "insights.db")
    audit = _complete_finalization_audit(
        source, source.parent / "publication-audit-v1" / "audit.db"
    )
    publication_audit.create_publication_finalization(
        source_run_db=source,
        audit_db=audit,
    )
    path = publication_audit.default_finalization_path(source)
    payload = json.loads(path.read_text())
    payload["effective_selected_ids"] = ["unselected-pass"]
    path.write_text(json.dumps(payload))

    with pytest.raises(ValueError, match="effective_selected_ids"):
        publication_audit.validate_readonly_publication_finalization(
            source_run_db=source,
            audit_db=audit,
        )
