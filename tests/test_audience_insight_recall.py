import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from fli import (
    audience_insight_evaluations,
    audience_insight_recall,
    audience_insights,
)


class FakeClient:
    pass


def _event(day: str, event_id: str, rank: int, decision: str) -> tuple:
    envelope = {
        "day": day,
        "event_id": event_id,
        "root": {
            "post_id": f"post-{day}-{rank}-{event_id}",
            "author": "@researcher",
            "text": f"Evidence text published on {day} for an audited source.",
        },
        "related_posts": [],
    }
    return event_id, rank, json.dumps(envelope), "complete", decision


def _triage_db(path: Path, day: str, rows: list[tuple]) -> Path:
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE triage_item (
               event_id TEXT PRIMARY KEY,
               current_rank INTEGER NOT NULL,
               envelope_json TEXT NOT NULL,
               status TEXT NOT NULL,
               decision TEXT NOT NULL
           )"""
    )
    conn.executemany("INSERT INTO triage_item VALUES (?, ?, ?, ?, ?)", rows)
    conn.commit()
    conn.close()
    return path


def _artifact_db(
    path: Path, article_edges: list[tuple[str, str, str, str]]
) -> Path:
    conn = sqlite3.connect(path)
    conn.executescript(
        """CREATE TABLE artifact_import_run (
               import_run_id TEXT PRIMARY KEY,
               selection_policy TEXT
           );
           CREATE TABLE artifact_import_candidate (
               import_run_id TEXT,
               envelope_day TEXT,
               event_id TEXT,
               decision TEXT,
               artifact_id TEXT,
               source_external_id TEXT
           );
           CREATE TABLE artifact (
               artifact_id TEXT PRIMARY KEY,
               canonical_url TEXT,
               host TEXT,
               title TEXT
           );
           CREATE TABLE artifact_fetch (
               fetch_id TEXT,
               artifact_id TEXT,
               status TEXT,
               text_snapshot_ref TEXT,
               text_sha256 TEXT,
               completed_at TEXT
           );"""
    )
    conn.execute(
        "INSERT INTO artifact_import_run VALUES (?, ?)",
        ("strict-run", "kept-envelope-primary-author-thread-artifacts-v1"),
    )
    for day, event_id, artifact_id, source_external_id in article_edges:
        conn.execute(
            "INSERT INTO artifact VALUES (?, ?, 'x.com', ?)",
            (artifact_id, f"http://x.com/i/article/{artifact_id}", artifact_id),
        )
        conn.execute(
            "INSERT INTO artifact_import_candidate VALUES ('strict-run', ?, ?, 'accepted', ?, ?)",
            (day, event_id, artifact_id, source_external_id),
        )
    conn.commit()
    conn.close()
    return path


def _day_rows(day: str, *, prefix: str) -> list[tuple]:
    return [
        _event(day, f"{prefix}-keep-51", 51, "keep"),
        _event(day, f"{prefix}-keep-52", 52, "keep"),
        _event(day, f"{prefix}-keep-53", 53, "keep"),
        _event(day, f"{prefix}-keep-76", 76, "keep"),
        _event(day, f"{prefix}-keep-77", 77, "keep"),
        _event(day, f"{prefix}-keep-78", 78, "keep"),
        _event(day, f"{prefix}-drop-1", 1, "drop"),
        _event(day, f"{prefix}-drop-2", 2, "drop"),
        _event(day, f"{prefix}-drop-26", 26, "drop"),
        _event(day, f"{prefix}-drop-27", 27, "drop"),
        _event(day, f"{prefix}-drop-90", 90, "drop"),
        _event(day, f"{prefix}-drop-91", 91, "drop"),
    ]


def _source_fixture(tmp_path: Path, days=("2026-07-05",)):
    triage_dbs = {}
    for day in days:
        triage_dbs[day] = _triage_db(
            tmp_path / f"triage-{day}.db", day, _day_rows(day, prefix=day)
        )
    artifact_db = _artifact_db(tmp_path / "artifacts.db", [])
    return triage_dbs, artifact_db


def _complete_review(
    conn: sqlite3.Connection,
    *,
    sample_id: str,
    audience: str,
    failed_dimension: str | None = None,
) -> sqlite3.Row:
    fields = {
        "claim_fidelity": 1,
        "epistemic_discipline": 1,
        "audience_useful": 1,
        "actionable": 1,
        "specific": 1,
    }
    if failed_dimension is not None:
        fields[failed_dimension] = 0
    result = {
        "claim": "The source reported a bounded result.",
        "claim_posture": "first_party_report",
        "why_it_matters": "It changes a specific decision if reproduced.",
        "supporting_quote": "Evidence text",
        "citation_block_index": 1,
        "audience_fields": {},
    }
    conn.execute(
        """UPDATE recall_audience_evaluation
           SET extraction_status = 'complete', outcome = 'insight',
               no_insight = 0, citation_valid = 1,
               extraction_result_json = ?, review_status = 'complete',
               review_input_text = 'frozen-review-input',
               review_input_sha256 = ?, review_prompt_cache_key = ?,
               claim_fidelity = ?, epistemic_discipline = ?,
               audience_useful = ?, actionable = ?, specific = ?,
               review_failure_codes_json = '[]',
               review_rationale = 'Deterministic fixture review.',
               review_completed_at = '2026-07-15T00:00:00+00:00'
           WHERE sample_id = ? AND audience = ?""",
        (
            json.dumps(result),
            f"review-{sample_id}-{audience}",
            f"cache-{sample_id}-{audience}",
            fields["claim_fidelity"],
            fields["epistemic_discipline"],
            fields["audience_useful"],
            fields["actionable"],
            fields["specific"],
            sample_id,
            audience,
        ),
    )
    conn.commit()
    return conn.execute(
        """SELECT * FROM recall_audience_evaluation
           WHERE sample_id = ? AND audience = ?""",
        (sample_id, audience),
    ).fetchone()


def _complete_remaining_as_no_insight(
    conn: sqlite3.Connection, *, audience: str
) -> None:
    conn.execute(
        """UPDATE recall_audience_evaluation
           SET extraction_status = 'complete',
               outcome = 'no_extractable_insight', no_insight = 1,
               no_insight_reason = 'Deterministic fixture no-insight.',
               review_status = 'not_applicable'
           WHERE audience = ? AND extraction_status != 'complete'""",
        (audience,),
    )
    conn.commit()


def _comparison(day: str, *, outcome: str) -> dict:
    return {
        "reference_set_id": f"published-{day}",
        "reference_candidate_ids": [f"published-{day}-1"],
        "outcome": outcome,
        "note": "Compared directly with the frozen higher-ranked daily set.",
    }


def _insight_result(packet, audience):
    quote = packet.sources[0].text
    common = {
        "outcome": "insight",
        "no_insight_reason": None,
        "claim": "The researcher reported a concrete result.",
        "claim_posture": "first_party_report",
        "why_it_matters": "If validated, it could change a bounded decision.",
        "supporting_quote": quote,
        "citation_block_index": 1,
        "citation": audience_insights.bind_citation(packet, 1, quote),
        "response_id": "resp-extract",
        "response_model": "test-model",
        "input_tokens": 100,
        "cached_tokens": 0,
        "cache_write_tokens": 0,
        "output_tokens": 20,
        "reported_cost_usd": 0.001,
        "request_tags": ["job:insight-extraction"],
        "raw_output_text": "{}",
    }
    if audience == "investment":
        fields = {
            "investment_implication": "If validated, revisit the thesis.",
            "what_to_watch": "Watch for an independent reproduction.",
        }
    else:
        fields = {
            "action_type": "benchmark",
            "engineering_action": "Benchmark the same workload.",
            "validation_boundary": "Use the disclosed workload only.",
        }
    return {**common, **fields, "audience_fields": fields}


def test_selection_digest_uses_the_exact_predeclared_rule():
    day = "2026-07-05"
    band = audience_insight_recall.KEPT_51_75
    event_id = "event-123"
    expected = hashlib.sha256(
        f"audience-insights-v2-recall-v1|{day}|{band}|{event_id}".encode()
    ).hexdigest()

    assert (
        audience_insight_recall.selection_sha256(
            day=day, band=band, event_id=event_id
        )
        == expected
    )


def test_freeze_is_deterministic_rank_blind_and_adds_article_census(tmp_path):
    day = "2026-07-05"
    rows = _day_rows(day, prefix="day5")
    # Rank 54 is outside the two-item quota if its hash loses, but the Article
    # census must include it regardless.  Add enough candidates to make it legal.
    article_event = "day5-article-only"
    rows.append(_event(day, article_event, 54, "keep"))
    triage_db = _triage_db(tmp_path / "triage.db", day, rows)
    artifact_db = _artifact_db(
        tmp_path / "artifacts.db",
        [(day, article_event, "article-1", f"post-{day}-54-{article_event}")],
    )
    conn = audience_insight_recall.connect(tmp_path / "recall.db")

    count = audience_insight_recall.freeze_audit(
        conn,
        run_id="recall-fixture",
        days=(day,),
        triage_dbs={day: triage_db},
        artifact_db=artifact_db,
    )
    assert count == 8  # four lower kept + Article census + three drops
    assert audience_insight_recall.freeze_audit(
        conn,
        run_id="recall-fixture",
        days=(day,),
        triage_dbs={day: triage_db},
        artifact_db=artifact_db,
    ) == count

    article = conn.execute(
        "SELECT * FROM recall_sample WHERE event_id = ?", (article_event,)
    ).fetchone()
    assert article["sample_kind"] == "x_article_census"
    assert json.loads(article["article_artifact_ids_json"]) == ["article-1"]
    assert article["triage_decision"] == "keep"
    assert article["feed_rank"] == 54
    assert article["selection_sha256"] == audience_insight_recall.selection_sha256(
        day=day,
        band=audience_insight_recall.X_ARTICLE_51_100,
        event_id=article_event,
    )

    evaluations = conn.execute(
        """SELECT audience, candidate_id, extraction_input_text,
                  extraction_input_sha256
           FROM recall_audience_evaluation
           WHERE sample_id = ? ORDER BY audience""",
        (article["sample_id"],),
    ).fetchall()
    assert [row["audience"] for row in evaluations] == [
        "ai_engineering",
        "investment",
    ]
    assert evaluations[0]["candidate_id"] != evaluations[1]["candidate_id"]
    assert evaluations[0]["extraction_input_sha256"] == evaluations[1][
        "extraction_input_sha256"
    ]
    for evaluation in evaluations:
        model_input = evaluation["extraction_input_text"]
        assert article_event not in model_input
        assert "feed_rank" not in model_input
        assert "triage_decision" not in model_input
        assert "http://x.com" not in model_input
    conn.close()


def test_repeated_events_are_replaced_by_the_next_hash_ordered_event(tmp_path):
    first_day = "2026-07-05"
    second_day = "2026-07-06"
    # Find a shared ID that sorts ahead of both second-day unique options so it
    # is truly a selected duplicate, not an irrelevant tail candidate.
    unique_ids = ["second-unique-a", "second-unique-b"]
    shared = next(
        f"shared-{index}"
        for index in range(100_000)
        if audience_insight_recall.selection_sha256(
            day=second_day,
            band=audience_insight_recall.KEPT_51_75,
            event_id=f"shared-{index}",
        )
        < min(
            audience_insight_recall.selection_sha256(
                day=second_day,
                band=audience_insight_recall.KEPT_51_75,
                event_id=event_id,
            )
            for event_id in unique_ids
        )
    )
    first_rows = _day_rows(first_day, prefix="first")
    # Make the first-day band contain exactly the shared row and one other row.
    first_rows = [
        row
        for row in first_rows
        if not (row[4] == "keep" and 51 <= row[1] <= 75)
    ]
    first_rows.extend(
        [
            _event(first_day, shared, 51, "keep"),
            _event(first_day, "first-only", 52, "keep"),
        ]
    )
    second_rows = _day_rows(second_day, prefix="second")
    second_rows = [
        row
        for row in second_rows
        if not (row[4] == "keep" and 51 <= row[1] <= 75)
    ]
    second_rows.extend(
        [
            _event(second_day, shared, 51, "keep"),
            _event(second_day, unique_ids[0], 52, "keep"),
            _event(second_day, unique_ids[1], 53, "keep"),
        ]
    )
    triage_dbs = {
        first_day: _triage_db(tmp_path / "first.db", first_day, first_rows),
        second_day: _triage_db(tmp_path / "second.db", second_day, second_rows),
    }
    artifact_db = _artifact_db(tmp_path / "artifacts.db", [])
    conn = audience_insight_recall.connect(tmp_path / "recall.db")

    audience_insight_recall.freeze_audit(
        conn,
        run_id="duplicates",
        days=(first_day, second_day),
        triage_dbs=triage_dbs,
        artifact_db=artifact_db,
    )

    event_ids = [row[0] for row in conn.execute("SELECT event_id FROM recall_sample")]
    assert len(event_ids) == len(set(event_ids))
    replacement = conn.execute(
        """SELECT * FROM recall_replacement
           WHERE skipped_event_id = ? AND reason = 'repeated_event'""",
        (shared,),
    ).fetchone()
    assert replacement is not None
    assert replacement["replacement_event_id"] in unique_ids
    assert replacement["skipped_selection_sha256"] == (
        audience_insight_recall.selection_sha256(
            day=second_day,
            band=audience_insight_recall.KEPT_51_75,
            event_id=shared,
        )
    )
    conn.close()


def test_extraction_and_review_resume_with_separate_recall_judgments(
    tmp_path, monkeypatch
):
    day = "2026-07-05"
    triage_dbs, artifact_db = _source_fixture(tmp_path, days=(day,))
    conn = audience_insight_recall.connect(tmp_path / "recall.db")
    audience_insight_recall.freeze_audit(
        conn,
        run_id="execution",
        days=(day,),
        triage_dbs=triage_dbs,
        artifact_db=artifact_db,
    )
    sample_ids = [
        row[0]
        for row in conn.execute(
            "SELECT sample_id FROM recall_sample ORDER BY selection_order"
        )
    ]
    no_insight_sample = sample_ids[0]
    citation_failure_sample = sample_ids[1]
    sample_by_event = {
        row["event_id"]: row["sample_id"]
        for row in conn.execute("SELECT event_id, sample_id FROM recall_sample")
    }
    calls = []

    def fake_extract(_client, packet, *, audience, **_kwargs):
        sample_id = sample_by_event[packet.event_id]
        calls.append((sample_id, audience))
        if audience == "investment" and sample_id == no_insight_sample:
            return {
                "outcome": "no_extractable_insight",
                "no_insight_reason": "no_audience_decision_value",
                "citation": None,
                "response_id": "no-insight",
                "response_model": "test",
                "input_tokens": 10,
                "cached_tokens": 0,
                "cache_write_tokens": 0,
                "output_tokens": 5,
                "reported_cost_usd": 0.001,
                "request_tags": [],
                "raw_output_text": "{}",
            }
        if audience == "investment" and sample_id == citation_failure_sample:
            result = _insight_result(packet, audience)
            raise audience_insights.CitationVerificationError(
                "quote did not bind", result=result
            )
        return _insight_result(packet, audience)

    monkeypatch.setattr(audience_insights, "evaluate_one", fake_extract)
    first = audience_insight_recall.run_extractions(
        conn, client=FakeClient(), audiences=("investment",), workers=3
    )
    second = audience_insight_recall.run_extractions(
        conn, client=FakeClient(), audiences=("investment",), workers=3
    )
    assert first["evaluations"][1]["extraction_failed"] == 1
    assert second["evaluations"][1]["extraction_failed"] == 1
    call_count_after_resume = len(calls)

    audience_insight_recall.run_extractions(
        conn,
        client=FakeClient(),
        audiences=("investment",),
        workers=3,
        retry_failed=True,
    )
    failed_row = conn.execute(
        """SELECT * FROM recall_audience_evaluation
           WHERE sample_id = ? AND audience = 'investment'""",
        (citation_failure_sample,),
    ).fetchone()
    assert failed_row["extraction_status"] == "rejected"
    assert failed_row["citation_failure_attempts"] == 2
    assert failed_row["citation_terminal_failure"] == 1
    assert failed_row["schema_terminal_failure"] == 0
    assert len(calls) == call_count_after_resume + 1

    no_insight = conn.execute(
        """SELECT * FROM recall_audience_evaluation
           WHERE sample_id = ? AND audience = 'investment'""",
        (no_insight_sample,),
    ).fetchone()
    assert no_insight["no_insight"] == 1
    assert no_insight["review_status"] == "not_applicable"
    assert no_insight["audience_useful"] is None

    review_calls = []

    def fake_review(_client, review, **_kwargs):
        review_calls.append(review.candidate_id)
        rendered = audience_insight_evaluations.render_item_input(review)
        assert "feed_rank" not in rendered
        assert "triage_decision" not in rendered
        return {
            "candidate_id": review.candidate_id,
            "claim_fidelity": "pass",
            "epistemic_discipline": "pass",
            "audience_usefulness": "pass",
            "actionability": "pass",
            "specificity": "pass",
            "failure_codes": [],
            "rationale": "The item is concrete and decision-relevant.",
            "response_id": "review",
            "response_model": "test",
            "input_tokens": 10,
            "cached_tokens": 0,
            "cache_write_tokens": 0,
            "output_tokens": 5,
            "reported_cost_usd": 0.001,
            "request_tags": [],
            "raw_output_text": "{}",
        }

    monkeypatch.setattr(audience_insight_evaluations, "review_item", fake_review)
    audience_insight_recall.run_reviews(
        conn, client=FakeClient(), audiences=("investment",), workers=3
    )
    completed_review_calls = len(review_calls)
    audience_insight_recall.run_reviews(
        conn, client=FakeClient(), audiences=("investment",), workers=3
    )
    assert len(review_calls) == completed_review_calls

    reviewable = conn.execute(
        """SELECT * FROM recall_audience_evaluation
           WHERE audience = 'investment' AND review_status = 'complete'
           ORDER BY candidate_id LIMIT 1"""
    ).fetchone()
    assert reviewable["audience_useful"] == 1
    assert reviewable["actionable"] == 1
    assert reviewable["specific"] == 1
    assert reviewable["final_set_worthy"] is None
    audience_insight_recall.record_adjudication(
        conn,
        sample_id=reviewable["sample_id"],
        audience="investment",
        redundant=False,
        final_set_worthy=True,
        note="This would materially diversify the higher-ranked daily set.",
        comparison={
            "reference_set_id": "investment-2026-07-05-passed-set",
            "reference_candidate_ids": ["published-1", "published-2"],
            "outcome": "materially_diversifies",
            "note": "Adds a decision axis absent from both published items.",
        },
    )
    adjudicated = conn.execute(
        """SELECT redundant, final_set_worthy, high_consequence,
                  adjudication_comparison_json
           FROM recall_audience_evaluation
           WHERE sample_id = ? AND audience = 'investment'""",
        (reviewable["sample_id"],),
    ).fetchone()
    assert tuple(adjudicated)[:3] == (0, 1, 0)
    assert json.loads(adjudicated["adjudication_comparison_json"])["outcome"] == (
        "materially_diversifies"
    )
    conn.close()


def test_schema_failures_are_tracked_separately_from_citation_failures(
    tmp_path, monkeypatch
):
    day = "2026-07-05"
    triage_dbs, artifact_db = _source_fixture(tmp_path, days=(day,))
    conn = audience_insight_recall.connect(tmp_path / "recall.db")
    audience_insight_recall.freeze_audit(
        conn,
        run_id="schema-failure",
        days=(day,),
        triage_dbs=triage_dbs,
        artifact_db=artifact_db,
    )

    def bad_schema(_client, _packet, **_kwargs):
        raise audience_insights.ExtractionValidationError(
            "invalid schema",
            result={
                "raw_output_text": "not-json",
                "response_id": "bad-schema",
                "request_tags": [],
            },
        )

    monkeypatch.setattr(audience_insights, "evaluate_one", bad_schema)
    audience_insight_recall.run_extractions(
        conn, client=FakeClient(), audiences=("ai_engineering",), workers=2
    )
    audience_insight_recall.run_extractions(
        conn,
        client=FakeClient(),
        audiences=("ai_engineering",),
        workers=2,
        retry_failed=True,
    )
    rows = conn.execute(
        """SELECT schema_terminal_failure, citation_terminal_failure,
                  schema_failure_attempts, extraction_status, review_status
           FROM recall_audience_evaluation
           WHERE audience = 'ai_engineering'"""
    ).fetchall()
    assert rows
    assert all(
        tuple(row) == (1, 0, 2, "rejected", "not_applicable") for row in rows
    )
    conn.close()


def test_summary_treats_legacy_terminal_rejection_as_unknown_not_review_pending(
    tmp_path,
):
    day = "2026-07-05"
    triage_dbs, artifact_db = _source_fixture(tmp_path, days=(day,))
    conn = audience_insight_recall.connect(tmp_path / "recall.db")
    audience_insight_recall.freeze_audit(
        conn,
        run_id="legacy-terminal-summary",
        days=(day,),
        triage_dbs=triage_dbs,
        artifact_db=artifact_db,
    )
    _complete_remaining_as_no_insight(conn, audience="investment")
    sample_id = conn.execute(
        """SELECT sample_id FROM recall_sample
           WHERE band = ? ORDER BY selection_order LIMIT 1""",
        (audience_insight_recall.KEPT_51_75,),
    ).fetchone()[0]
    conn.execute(
        """UPDATE recall_audience_evaluation
           SET extraction_status = 'rejected', outcome = NULL, no_insight = 0,
               schema_terminal_failure = 1, review_status = 'pending'
           WHERE sample_id = ? AND audience = 'investment'""",
        (sample_id,),
    )
    conn.commit()

    result = audience_insight_recall.summary(conn)
    investment = next(
        row for row in result["evaluations"] if row["audience"] == "investment"
    )
    assert investment["extraction_rejected"] == 1
    assert investment["schema_terminal"] == 1
    assert investment["review_pending"] == 0
    assert investment["useful_misses"] is None
    widening = next(
        row
        for row in result["widening"]["by_day_audience"]
        if row["day"] == day and row["audience"] == "investment"
    )
    assert widening["diagnosis_status"] == "unknown_incomplete_evaluation"
    assert widening["incomplete_evaluations"] == 1
    assert widening["recommended_rank_limit"] is None
    assert widening["kept_51_75_misses"] is None
    conn.close()


def test_summary_only_awaits_all_five_pass_adjudications(tmp_path):
    day = "2026-07-05"
    triage_dbs, artifact_db = _source_fixture(tmp_path, days=(day,))
    conn = audience_insight_recall.connect(tmp_path / "recall.db")
    audience_insight_recall.freeze_audit(
        conn,
        run_id="eligible-adjudication-summary",
        days=(day,),
        triage_dbs=triage_dbs,
        artifact_db=artifact_db,
    )
    sample_ids = [
        row[0]
        for row in conn.execute(
            """SELECT sample_id FROM recall_sample
               WHERE band = ? ORDER BY selection_order LIMIT 2""",
            (audience_insight_recall.KEPT_51_75,),
        )
    ]
    passing = _complete_review(
        conn, sample_id=sample_ids[0], audience="investment"
    )
    _complete_review(
        conn,
        sample_id=sample_ids[1],
        audience="investment",
        failed_dimension="specific",
    )
    _complete_remaining_as_no_insight(conn, audience="investment")

    result = audience_insight_recall.summary(conn)
    investment = next(
        row for row in result["evaluations"] if row["audience"] == "investment"
    )
    assert investment["review_complete"] == 2
    assert investment["awaiting_adjudication"] == 1
    assert investment["final_set_worthy"] is None
    widening = next(
        row
        for row in result["widening"]["by_day_audience"]
        if row["day"] == day and row["audience"] == "investment"
    )
    assert widening["diagnosis_status"] == "pending_adjudication"
    assert widening["awaiting_adjudication"] == 1
    assert widening["recommended_rank_limit"] is None

    audience_insight_recall.record_adjudication(
        conn,
        sample_id=passing["sample_id"],
        audience="investment",
        redundant=False,
        final_set_worthy=False,
        high_consequence=False,
        note="The candidate does not enter the higher-ranked set.",
        comparison=_comparison(day, outcome="would_not_enter"),
    )
    completed = audience_insight_recall.summary(conn)
    investment = next(
        row for row in completed["evaluations"] if row["audience"] == "investment"
    )
    assert investment["awaiting_adjudication"] == 0
    assert investment["final_set_worthy"] == 0
    widening = next(
        row
        for row in completed["widening"]["by_day_audience"]
        if row["day"] == day and row["audience"] == "investment"
    )
    assert widening["diagnosis_status"] == "complete"
    assert widening["recommended_rank_limit"] == 50
    conn.close()


def test_triage_diagnosis_is_pending_until_dropped_candidate_adjudication(tmp_path):
    day = "2026-07-05"
    triage_dbs, artifact_db = _source_fixture(tmp_path, days=(day,))
    conn = audience_insight_recall.connect(tmp_path / "recall.db")
    audience_insight_recall.freeze_audit(
        conn,
        run_id="triage-pending-summary",
        days=(day,),
        triage_dbs=triage_dbs,
        artifact_db=artifact_db,
    )
    sample_id = conn.execute(
        """SELECT sample_id FROM recall_sample
           WHERE sample_kind = 'dropped' ORDER BY selection_order LIMIT 1"""
    ).fetchone()[0]
    _complete_review(conn, sample_id=sample_id, audience="investment")
    _complete_remaining_as_no_insight(conn, audience="investment")

    result = audience_insight_recall.summary(conn)
    triage = next(
        row
        for row in result["triage_diagnosis"]
        if row["audience"] == "investment"
    )
    assert triage["diagnosis_status"] == "pending_adjudication"
    assert triage["awaiting_adjudication"] == 1
    assert triage["false_negatives"] is None
    assert triage["second_frozen_sample_required"] is None
    investment = next(
        row for row in result["evaluations"] if row["audience"] == "investment"
    )
    assert investment["triage_false_negatives"] is None

    audience_insight_recall.record_adjudication(
        conn,
        sample_id=sample_id,
        audience="investment",
        redundant=False,
        final_set_worthy=False,
        high_consequence=False,
        note="The candidate does not enter the higher-ranked set.",
        comparison=_comparison(day, outcome="would_not_enter"),
    )
    completed = audience_insight_recall.summary(conn)
    triage = next(
        row
        for row in completed["triage_diagnosis"]
        if row["audience"] == "investment"
    )
    assert triage["diagnosis_status"] == "complete"
    assert triage["false_negatives"] == 0
    assert triage["second_frozen_sample_required"] is False
    conn.close()


def test_runtime_contract_drift_blocks_extract_and_review_before_model_calls(
    tmp_path, monkeypatch
):
    day = "2026-07-05"
    triage_dbs, artifact_db = _source_fixture(tmp_path, days=(day,))
    conn = audience_insight_recall.connect(tmp_path / "recall.db")
    audience_insight_recall.freeze_audit(
        conn,
        run_id="contract-drift",
        days=(day,),
        triage_dbs=triage_dbs,
        artifact_db=artifact_db,
    )
    extraction_calls = []
    review_calls = []
    monkeypatch.setattr(
        audience_insights,
        "evaluate_one",
        lambda *_args, **_kwargs: extraction_calls.append(True),
    )
    original_prompt_sha256 = audience_insights.prompt_sha256
    monkeypatch.setattr(
        audience_insights,
        "prompt_sha256",
        lambda audience: (
            "runtime-drift"
            if audience == "investment"
            else original_prompt_sha256(audience)
        ),
    )
    with pytest.raises(ValueError, match="contract drift"):
        audience_insight_recall.run_extractions(conn, client=FakeClient())
    assert extraction_calls == []

    monkeypatch.setattr(audience_insights, "prompt_sha256", original_prompt_sha256)
    conn.execute(
        """UPDATE recall_audience_evaluation
           SET extraction_prompt_version = 'tampered-version'
           WHERE audience = 'investment'"""
    )
    conn.commit()
    with pytest.raises(ValueError, match="extraction contract drift"):
        audience_insight_recall.run_extractions(conn, client=FakeClient())
    conn.execute(
        """UPDATE recall_audience_evaluation
           SET extraction_prompt_version = ? WHERE audience = 'investment'""",
        (audience_insights.prompt_version("investment"),),
    )
    conn.commit()
    original_item_sha256 = audience_insight_evaluations.item_prompt_sha256
    monkeypatch.setattr(
        audience_insight_evaluations,
        "item_prompt_sha256",
        lambda _audience: "runtime-review-drift",
    )
    monkeypatch.setattr(
        audience_insight_evaluations,
        "review_item",
        lambda *_args, **_kwargs: review_calls.append(True),
    )
    with pytest.raises(ValueError, match="contract drift"):
        audience_insight_recall.run_reviews(conn, client=FakeClient())
    assert review_calls == []
    monkeypatch.setattr(
        audience_insight_evaluations,
        "item_prompt_sha256",
        original_item_sha256,
    )
    conn.close()


def test_final_set_worthy_requires_all_five_dimensions_and_comparison(tmp_path):
    day = "2026-07-05"
    triage_dbs, artifact_db = _source_fixture(tmp_path, days=(day,))
    conn = audience_insight_recall.connect(tmp_path / "recall.db")
    audience_insight_recall.freeze_audit(
        conn,
        run_id="five-dimensions",
        days=(day,),
        triage_dbs=triage_dbs,
        artifact_db=artifact_db,
    )
    sample_id = conn.execute(
        "SELECT sample_id FROM recall_sample ORDER BY selection_order LIMIT 1"
    ).fetchone()[0]
    _complete_review(
        conn,
        sample_id=sample_id,
        audience="investment",
        failed_dimension="claim_fidelity",
    )
    with pytest.raises(ValueError, match="all five review dimensions"):
        audience_insight_recall.record_adjudication(
            conn,
            sample_id=sample_id,
            audience="investment",
            redundant=False,
            final_set_worthy=True,
            high_consequence=False,
            note="Would otherwise enter the set.",
            comparison=_comparison(day, outcome="would_enter"),
        )
    with pytest.raises(ValueError, match="reference_set_id"):
        audience_insight_recall.record_adjudication(
            conn,
            sample_id=sample_id,
            audience="investment",
            redundant=False,
            final_set_worthy=False,
            high_consequence=False,
            note="Does not meet the reviewer bar.",
            comparison={
                "reference_set_id": "",
                "reference_candidate_ids": [],
                "outcome": "would_not_enter",
                "note": "Compared with the higher-ranked set.",
            },
        )
    audience_insight_recall.record_adjudication(
        conn,
        sample_id=sample_id,
        audience="investment",
        redundant=False,
        final_set_worthy=False,
        high_consequence=False,
        note="Does not meet the reviewer bar.",
        comparison=_comparison(day, outcome="would_not_enter"),
    )
    conn.close()


def test_adjudication_batch_export_is_deterministic_and_import_is_atomic(tmp_path):
    day = "2026-07-05"
    triage_dbs, artifact_db = _source_fixture(tmp_path, days=(day,))
    conn = audience_insight_recall.connect(tmp_path / "recall.db")
    audience_insight_recall.freeze_audit(
        conn,
        run_id="batch-adjudication",
        days=(day,),
        triage_dbs=triage_dbs,
        artifact_db=artifact_db,
    )
    sample_ids = [
        row[0]
        for row in conn.execute(
            "SELECT sample_id FROM recall_sample ORDER BY selection_order LIMIT 2"
        )
    ]
    for sample_id in sample_ids:
        _complete_review(conn, sample_id=sample_id, audience="investment")

    first = audience_insight_recall.export_adjudication_batch(conn)
    second = audience_insight_recall.export_adjudication_batch(conn)
    assert first == second
    assert first["expected_row_count"] == 2
    export_path = tmp_path / "adjudications.json"
    assert audience_insight_recall.main(
        [
            "adjudication-export",
            "--run-db",
            str(tmp_path / "recall.db"),
            "--output",
            str(export_path),
        ]
    ) == 0
    assert json.loads(export_path.read_text()) == first
    for item in first["rows"]:
        item["comparison"] = _comparison(day, outcome="would_enter")
        item["adjudication"] = {
            "redundant": False,
            "final_set_worthy": True,
            "high_consequence": False,
            "note": "This would enter the higher-ranked final set.",
        }
    assert audience_insight_recall.import_adjudication_batch(conn, first) == 2
    import_path = tmp_path / "completed-adjudications.json"
    import_path.write_text(json.dumps(first))
    assert audience_insight_recall.main(
        [
            "adjudication-import",
            "--run-db",
            str(tmp_path / "recall.db"),
            "--input",
            str(import_path),
        ]
    ) == 0
    stored = conn.execute(
        """SELECT COUNT(*) FROM recall_audience_evaluation
           WHERE final_set_worthy = 1"""
    ).fetchone()[0]
    assert stored == 2

    broken = json.loads(json.dumps(first))
    broken["rows"][0]["candidate_id"] = "changed-after-export"
    before = conn.execute(
        "SELECT MAX(updated_at) FROM recall_audience_evaluation"
    ).fetchone()[0]
    with pytest.raises(ValueError, match="identity changed"):
        audience_insight_recall.import_adjudication_batch(conn, broken)
    after = conn.execute(
        "SELECT MAX(updated_at) FROM recall_audience_evaluation"
    ).fetchone()[0]
    assert after == before
    conn.close()


def test_adjudication_batch_survives_live_prompt_drift(tmp_path, monkeypatch):
    day = "2026-07-05"
    triage_dbs, artifact_db = _source_fixture(tmp_path, days=(day,))
    conn = audience_insight_recall.connect(tmp_path / "recall.db")
    audience_insight_recall.freeze_audit(
        conn,
        run_id="preserved-adjudication",
        days=(day,),
        triage_dbs=triage_dbs,
        artifact_db=artifact_db,
    )
    sample_id = conn.execute(
        "SELECT sample_id FROM recall_sample ORDER BY selection_order LIMIT 1"
    ).fetchone()[0]
    _complete_review(conn, sample_id=sample_id, audience="investment")

    original_prompt_sha256 = audience_insights.prompt_sha256
    monkeypatch.setattr(
        audience_insights,
        "prompt_sha256",
        lambda audience: (
            "new-live-prompt"
            if audience == "investment"
            else original_prompt_sha256(audience)
        ),
    )
    with pytest.raises(ValueError, match="contract drift"):
        audience_insight_recall.run_extractions(conn, client=FakeClient())

    payload = audience_insight_recall.export_adjudication_batch(conn)
    assert payload["run_id"] == "preserved-adjudication"
    assert payload["expected_row_count"] == 1
    payload["rows"][0]["comparison"] = _comparison(
        day, outcome="would_not_enter"
    )
    payload["rows"][0]["adjudication"] = {
        "redundant": False,
        "final_set_worthy": False,
        "high_consequence": False,
        "note": "The frozen item would not enter the final set.",
    }
    assert audience_insight_recall.import_adjudication_batch(conn, payload) == 1
    conn.close()


def test_summary_reports_strata_widening_and_triage_thresholds(tmp_path):
    days = ("2026-07-05", "2026-07-06", "2026-07-07")
    triage_dbs, artifact_db = _source_fixture(tmp_path, days=days)
    conn = audience_insight_recall.connect(tmp_path / "recall.db")
    audience_insight_recall.freeze_audit(
        conn,
        run_id="recall-thresholds",
        days=days,
        triage_dbs=triage_dbs,
        artifact_db=artifact_db,
    )

    def adjudicate_band(
        day: str, band: str, *, high_consequence: bool = False
    ) -> None:
        sample_id = conn.execute(
            """SELECT sample_id FROM recall_sample
               WHERE day = ? AND band = ? ORDER BY selection_order LIMIT 1""",
            (day, band),
        ).fetchone()[0]
        _complete_review(conn, sample_id=sample_id, audience="investment")
        audience_insight_recall.record_adjudication(
            conn,
            sample_id=sample_id,
            audience="investment",
            redundant=False,
            final_set_worthy=True,
            high_consequence=high_consequence,
            note="This is a final-set-worthy miss after direct comparison.",
            comparison=_comparison(day, outcome="would_enter"),
        )

    for day in days:
        adjudicate_band(day, audience_insight_recall.KEPT_51_75)
    adjudicate_band(days[0], audience_insight_recall.KEPT_76_100)
    adjudicate_band(days[0], audience_insight_recall.DROPPED_1_25)
    adjudicate_band(
        days[1], audience_insight_recall.DROPPED_26_50, high_consequence=True
    )
    _complete_remaining_as_no_insight(conn, audience="investment")

    result = audience_insight_recall.summary(conn)
    day_rows = {
        (row["day"], row["audience"]): row
        for row in result["widening"]["by_day_audience"]
    }
    assert day_rows[(days[0], "investment")]["recommended_rank_limit"] == 100
    assert day_rows[(days[1], "investment")]["recommended_rank_limit"] == 75
    assert day_rows[(days[2], "investment")]["recommended_rank_limit"] == 75
    systemic = result["widening"]["systemic"]
    assert systemic == [
        {
            "audience": "investment",
            "pattern": "kept_51_75",
            "failure_days": list(days),
            "failure_day_count": 3,
            "recommended_rank_limit_all_days": 75,
        }
    ]
    investment_triage = next(
        row
        for row in result["triage_diagnosis"]
        if row["audience"] == "investment"
    )
    assert investment_triage["false_negatives"] == 2
    assert investment_triage["high_consequence_false_negatives"] == 1
    assert investment_triage["second_frozen_sample_required"] is True
    assert investment_triage["trigger"] == "high_consequence_false_negative"
    assert any(
        row["final_set_worthy_misses"] == 1
        and row["high_consequence_misses"] == 1
        for row in result["strata"]
    )
    conn.close()
