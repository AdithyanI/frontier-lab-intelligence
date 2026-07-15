import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from fli import (
    audience_insight_evaluations,
    audience_insight_runs,
    audience_insights,
)


class FakeClient:
    pass


def _source_databases(tmp_path):
    triage_db = tmp_path / "triage.db"
    triage = sqlite3.connect(triage_db)
    triage.execute(
        """CREATE TABLE triage_item (
               event_id TEXT PRIMARY KEY,
               current_rank INTEGER,
               envelope_json TEXT,
               status TEXT,
               decision TEXT
           )"""
    )
    envelope = {
        "day": "2026-07-11",
        "event_id": "event-1",
        "root": {
            "post_id": "post-1",
            "author": "@author",
            "text": "We measured a 35% reduction in serving latency.",
        },
        "related_posts": [],
    }
    triage.execute(
        "INSERT INTO triage_item VALUES ('event-1', 4, ?, 'complete', 'keep')",
        (json.dumps(envelope),),
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
               text_snapshot_ref TEXT, text_sha256 TEXT,
               completed_at TEXT
           );"""
    )
    artifact.commit()
    artifact.close()
    return triage_db, artifact_db


def _extraction_result(packet):
    quote = "We measured a 35% reduction in serving latency."
    return {
        "outcome": "insight",
        "no_insight_reason": None,
        "claim": "The author reported a 35% serving-latency reduction.",
        "claim_posture": "first_party_report",
        "why_it_matters": "If reproduced, the result could reduce adoption friction.",
        "investment_implication": "If validated, lower latency could improve product usability.",
        "what_to_watch": "Reproduction on representative production workloads.",
        "supporting_quote": quote,
        "citation_block_index": 1,
        "audience_fields": {
            "investment_implication": "If validated, lower latency could improve product usability.",
            "what_to_watch": "Reproduction on representative production workloads.",
        },
        "citation": audience_insights.bind_citation(packet, 1, quote),
        "response_id": "resp-extract",
        "response_model": "gpt-test",
        "input_tokens": 1800,
        "cached_tokens": 1024,
        "cache_write_tokens": 0,
        "output_tokens": 180,
        "reported_cost_usd": 0.01,
        "request_tags": ["pipeline:audience-insights"],
        "raw_output_text": "{}",
    }


def _add_source_event(triage_db: Path, *, event_id: str, rank: int) -> None:
    conn = sqlite3.connect(triage_db)
    envelope = json.loads(
        conn.execute(
            "SELECT envelope_json FROM triage_item WHERE event_id = 'event-1'"
        ).fetchone()[0]
    )
    envelope["event_id"] = event_id
    envelope["root"]["post_id"] = f"post-{event_id}"
    conn.execute(
        "INSERT INTO triage_item VALUES (?, ?, ?, 'complete', 'keep')",
        (event_id, rank, json.dumps(envelope)),
    )
    conn.commit()
    conn.close()


@pytest.mark.parametrize(
    ("audience", "expected_effort"),
    [
        (audience_insights.INVESTMENT, "high"),
        (audience_insights.AI_ENGINEERING, "medium"),
    ],
)
def test_dry_run_uses_audience_specific_extraction_effort_by_default(
    tmp_path, capsys, audience, expected_effort
):
    triage_db, artifact_db = _source_databases(tmp_path)
    run_db = tmp_path / audience / "insights.db"

    assert audience_insight_runs.main(
        [
            "run",
            "--run-id",
            f"dry-run-{audience}",
            "--run-db",
            str(run_db),
            "--audience",
            audience,
            "--day",
            "2026-07-11",
            "--triage-db",
            str(triage_db),
            "--artifact-db",
            str(artifact_db),
            "--history-mode",
            "none",
            "--dry-run",
        ]
    ) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["will_call_model"] is False
    assert payload["data"]["run"]["reasoning_effort"] == expected_effort
    assert payload["data"]["history_input"] == {
        "mode": "none",
        "sources": [],
        "prior_item_count": 0,
        "history_sha256": audience_insight_runs._sha256("[]"),
    }


def test_new_run_persists_provider_safe_input_render_version(tmp_path):
    triage_db, artifact_db = _source_databases(tmp_path)
    conn = audience_insight_runs.connect_run(tmp_path / "versioned" / "insights.db")

    audience_insight_runs.freeze_run(
        conn,
        run_id="versioned",
        audience="investment",
        day="2026-07-11",
        triage_db=triage_db,
        artifact_db=artifact_db,
    )

    assert audience_insight_runs.declared_input_render_version(conn) == (
        audience_insights.INPUT_RENDER_PROVIDER_SAFE_V2
    )
    assert audience_insight_runs.summary(conn)["run"]["input_render_version"] == (
        audience_insights.INPUT_RENDER_PROVIDER_SAFE_V2
    )


def test_pre_column_run_is_explicitly_classified_as_verbatim_v1():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE run_meta (
               singleton INTEGER PRIMARY KEY,
               run_id TEXT NOT NULL
           )"""
    )
    conn.execute("INSERT INTO run_meta VALUES (1, 'legacy')")

    assert audience_insight_runs.declared_input_render_version(conn) == (
        audience_insights.INPUT_RENDER_VERBATIM_V1
    )


def test_resume_sends_exact_frozen_input_bytes_and_rejects_hash_drift(
    tmp_path, monkeypatch
):
    triage_db, artifact_db = _source_databases(tmp_path)
    conn = audience_insight_runs.connect_run(tmp_path / "resume" / "insights.db")
    audience_insight_runs.freeze_run(
        conn,
        run_id="resume-exact-input",
        audience="investment",
        day="2026-07-11",
        triage_db=triage_db,
        artifact_db=artifact_db,
    )
    exact_input = "exact frozen bytes\nincluding [EXPLETIVE] and whitespace  "
    exact_sha256 = hashlib.sha256(exact_input.encode()).hexdigest()
    conn.execute(
        "UPDATE candidate_item SET input_text = ?, input_sha256 = ?",
        (exact_input, exact_sha256),
    )
    conn.commit()
    observed_inputs = []

    def fake_extract(_client, packet, **kwargs):
        observed_inputs.append(kwargs["frozen_input_text"])
        return _extraction_result(packet)

    monkeypatch.setattr(audience_insights, "evaluate_one", fake_extract)
    audience_insight_runs.run_pending(conn, client=FakeClient(), workers=1)
    assert observed_inputs == [exact_input]

    drift_conn = audience_insight_runs.connect_run(
        tmp_path / "resume-drift" / "insights.db"
    )
    audience_insight_runs.freeze_run(
        drift_conn,
        run_id="resume-hash-drift",
        audience="investment",
        day="2026-07-11",
        triage_db=triage_db,
        artifact_db=artifact_db,
    )
    drift_conn.execute("UPDATE candidate_item SET input_text = input_text || ' drift'")
    drift_conn.commit()

    with pytest.raises(ValueError, match="frozen candidate input hash drift"):
        audience_insight_runs.run_pending(
            drift_conn,
            client=FakeClient(),
            workers=1,
        )
    assert observed_inputs == [exact_input]


def test_full_run_is_resumable_editor_owned_and_quality_gated(tmp_path, monkeypatch):
    triage_db, artifact_db = _source_databases(tmp_path)
    conn = audience_insight_runs.connect_run(tmp_path / "run" / "insights.db")
    assert audience_insight_runs.freeze_run(
        conn,
        run_id="gate-investment",
        audience="investment",
        day="2026-07-11",
        triage_db=triage_db,
        artifact_db=artifact_db,
    ) == 1
    assert audience_insight_runs.freeze_run(
        conn,
        run_id="gate-investment",
        audience="investment",
        day="2026-07-11",
        triage_db=triage_db,
        artifact_db=artifact_db,
    ) == 1
    row = conn.execute("SELECT * FROM candidate_item").fetchone()
    assert "post-1" not in row["input_text"]
    assert "https://x.com" not in row["input_text"]
    assert "feed_rank" not in row["input_text"]

    extraction_calls = []

    def fake_extract(_client, packet, **_kwargs):
        extraction_calls.append(packet.event_id)
        return _extraction_result(packet)

    monkeypatch.setattr(audience_insights, "evaluate_one", fake_extract)
    first = audience_insight_runs.run_pending(conn, client=FakeClient(), workers=2)
    second = audience_insight_runs.run_pending(conn, client=FakeClient(), workers=2)
    assert extraction_calls == ["event-1"]
    assert first["counts"]["complete"] == 1
    assert second["counts"]["complete"] == 1

    candidate_id = str(row["candidate_id"])

    def fake_editor(_client, _editor_input, **_kwargs):
        return {
            "selected": [
                {
                    "candidate_id": candidate_id,
                    "decision_value": "thesis_or_model",
                    "audit_reason": "The only candidate changes a concrete diligence question.",
                    "updates_prior_id": None,
                }
            ],
            "suppressed_duplicates": [],
            "thin_day_reason": "Only one verified candidate cleared the audience bar.",
            "response_id": "resp-editor",
            "response_model": "gpt-test",
            "input_tokens": 1000,
            "cached_tokens": 0,
            "cache_write_tokens": 0,
            "output_tokens": 100,
            "reported_cost_usd": 0.005,
            "request_tags": ["job:daily-editor"],
            "raw_output_text": "{}",
        }

    monkeypatch.setattr(audience_insights, "evaluate_editor", fake_editor)
    with pytest.raises(ValueError, match="item quality review"):
        audience_insight_runs.prepare_editor(conn)

    def fake_item_review(_client, review, **_kwargs):
        return {
            "candidate_id": review.candidate_id,
            "claim_fidelity": "pass",
            "epistemic_discipline": "pass",
            "audience_usefulness": "pass",
            "actionability": "pass",
            "specificity": "pass",
            "failure_codes": [],
            "rationale": "The claim and audience decision fields are specific and bounded.",
            "response_id": "resp-review-item",
            "response_model": "gpt-test",
            "input_tokens": 1000,
            "cached_tokens": 0,
            "cache_write_tokens": 0,
            "output_tokens": 100,
            "reported_cost_usd": 0.005,
            "request_tags": ["job:quality-evaluation"],
            "raw_output_text": "{}",
        }

    def fake_day_review(_client, _review, **_kwargs):
        return {
            "duplicate_pairs": [],
            "padding_detected": False,
            "thin_day_honest": True,
            "set_rationale": "The one-item thin day is honest and non-duplicative.",
            "response_id": "resp-review-day",
            "response_model": "gpt-test",
            "input_tokens": 1000,
            "cached_tokens": 0,
            "cache_write_tokens": 0,
            "output_tokens": 100,
            "reported_cost_usd": 0.005,
            "request_tags": ["job:quality-evaluation"],
            "raw_output_text": "{}",
        }

    monkeypatch.setattr(
        audience_insight_evaluations, "review_item", fake_item_review
    )
    monkeypatch.setattr(
        audience_insight_evaluations, "review_day_set", fake_day_review
    )
    audience_insight_runs.run_item_reviews(conn, client=FakeClient())
    audience_insight_runs.prepare_editor(conn)
    audience_insight_runs.run_editor(conn, client=FakeClient())
    result = audience_insight_runs.run_quality_reviews(conn, client=FakeClient())
    assert result["quality_gate"]["passed"] is True
    assert result["counts"]["selected"] == 1
    assert conn.execute("SELECT passed FROM quality_gate").fetchone()[0] == 1
    assert audience_insight_runs.selected_history_row(conn)[0]["claim"].startswith(
        "The author reported"
    )


def test_item_review_filters_editor_and_day_set_without_leaking_judgments(
    tmp_path, monkeypatch
):
    triage_db, artifact_db = _source_databases(tmp_path)
    _add_source_event(triage_db, event_id="event-2", rank=5)
    conn = audience_insight_runs.connect_run(tmp_path / "filter" / "insights.db")
    audience_insight_runs.freeze_run(
        conn,
        run_id="quality-filter",
        audience="investment",
        day="2026-07-11",
        triage_db=triage_db,
        artifact_db=artifact_db,
    )
    monkeypatch.setattr(
        audience_insights,
        "evaluate_one",
        lambda _client, packet, **_kwargs: _extraction_result(packet),
    )
    audience_insight_runs.run_pending(conn, client=FakeClient(), workers=2)
    ids = {
        str(row["event_id"]): str(row["candidate_id"])
        for row in conn.execute("SELECT event_id, candidate_id FROM candidate_item")
    }

    review_calls = []

    def fake_review(_client, review, **_kwargs):
        review_calls.append(review.candidate_id)
        passing = review.candidate_id == ids["event-1"]
        rating = "pass" if passing else "fail"
        return {
            "candidate_id": review.candidate_id,
            "claim_fidelity": rating,
            "epistemic_discipline": rating,
            "audience_usefulness": rating,
            "actionability": rating,
            "specificity": rating,
            "failure_codes": [] if passing else ["not_decision_relevant"],
            "rationale": "PRIVATE REVIEW RATIONALE",
            "response_id": f"review-{review.candidate_id}",
            "response_model": "gpt-test",
            "input_tokens": 1000,
            "cached_tokens": 0,
            "cache_write_tokens": 0,
            "output_tokens": 100,
            "reported_cost_usd": 0.005,
            "request_tags": ["job:quality-evaluation"],
            "raw_output_text": "{}",
        }

    monkeypatch.setattr(audience_insight_evaluations, "review_item", fake_review)
    audience_insight_runs.run_item_reviews(
        conn, client=FakeClient(), workers=2
    )
    audience_insight_runs.run_item_reviews(
        conn, client=FakeClient(), workers=2
    )
    assert set(review_calls) == set(ids.values())
    assert len(review_calls) == 2

    assert audience_insight_runs.prepare_editor(conn) == 1
    editor = conn.execute("SELECT input_text FROM editor_run").fetchone()
    assert ids["event-1"] in editor["input_text"]
    assert ids["event-2"] not in editor["input_text"]
    assert "PRIVATE REVIEW RATIONALE" not in editor["input_text"]
    assert "claim_fidelity" not in editor["input_text"]

    def fake_editor(_client, editor_input, **_kwargs):
        assert [item["candidate_id"] for item in editor_input.candidates] == [
            ids["event-1"]
        ]
        return {
            "selected": [{
                "candidate_id": ids["event-1"],
                "decision_value": "thesis_or_model",
                "audit_reason": "The eligible item changes a decision.",
                "updates_prior_id": None,
            }],
            "suppressed_duplicates": [],
            "thin_day_reason": "Only one candidate passed independent review.",
            "response_id": "editor-filter",
            "response_model": "gpt-test",
            "input_tokens": 1000,
            "cached_tokens": 0,
            "cache_write_tokens": 0,
            "output_tokens": 100,
            "reported_cost_usd": 0.005,
            "request_tags": ["job:daily-editor"],
            "raw_output_text": "{}",
        }

    monkeypatch.setattr(audience_insights, "evaluate_editor", fake_editor)
    audience_insight_runs.run_editor(conn, client=FakeClient())
    assert audience_insight_runs.prepare_day_set_review(conn) == 1
    day_input = audience_insight_runs._quality_day_input(conn)
    assert [item["candidate_id"] for item in day_input.selected] == [ids["event-1"]]
    assert day_input.unselected == ()


def _prepared_selection_run(
    tmp_path, monkeypatch, *, name, selected_count=4
):
    triage_db, artifact_db = _source_databases(tmp_path)
    for offset in range(2, selected_count + 1):
        _add_source_event(
            triage_db,
            event_id=f"event-{offset}",
            rank=offset + 3,
        )
    conn = audience_insight_runs.connect_run(
        tmp_path / name / "insights.db"
    )
    audience_insight_runs.freeze_run(
        conn,
        run_id=name,
        audience="investment",
        day="2026-07-11",
        triage_db=triage_db,
        artifact_db=artifact_db,
    )
    monkeypatch.setattr(
        audience_insights,
        "evaluate_one",
        lambda _client, packet, **_kwargs: _extraction_result(packet),
    )
    audience_insight_runs.run_pending(conn, client=FakeClient(), workers=4)

    def pass_item(_client, review, **_kwargs):
        return {
            "candidate_id": review.candidate_id,
            "claim_fidelity": "pass",
            "epistemic_discipline": "pass",
            "audience_usefulness": "pass",
            "actionability": "pass",
            "specificity": "pass",
            "failure_codes": [],
            "rationale": "The candidate is safe, useful, and specific.",
            "response_id": f"review-{review.candidate_id}",
            "response_model": "gpt-test",
            "input_tokens": 1000,
            "cached_tokens": 0,
            "cache_write_tokens": 0,
            "output_tokens": 100,
            "reported_cost_usd": 0.005,
            "request_tags": ["job:quality-evaluation"],
            "raw_output_text": "{}",
        }

    monkeypatch.setattr(audience_insight_evaluations, "review_item", pass_item)
    audience_insight_runs.run_item_reviews(
        conn, client=FakeClient(), workers=4
    )
    candidate_ids = [
        str(row["candidate_id"])
        for row in conn.execute(
            "SELECT candidate_id FROM candidate_item ORDER BY feed_rank"
        )
    ]

    def select_items(_client, _editor_input, **_kwargs):
        return {
            "selected": [
                {
                    "candidate_id": candidate_id,
                    "decision_value": "thesis_or_model",
                    "audit_reason": f"Decision-relevant item {rank}.",
                    "updates_prior_id": None,
                }
                for rank, candidate_id in enumerate(candidate_ids, start=1)
            ],
            "suppressed_duplicates": [],
            "thin_day_reason": None,
            "response_id": f"editor-{selected_count}",
            "response_model": "gpt-test",
            "input_tokens": 1000,
            "cached_tokens": 0,
            "cache_write_tokens": 0,
            "output_tokens": 100,
            "reported_cost_usd": 0.005,
            "request_tags": ["job:daily-editor"],
            "raw_output_text": "{}",
        }

    monkeypatch.setattr(audience_insights, "evaluate_editor", select_items)
    audience_insight_runs.prepare_editor(conn)
    audience_insight_runs.run_editor(conn, client=FakeClient())
    return conn, candidate_ids


def _prepared_four_selection_run(tmp_path, monkeypatch, *, name):
    return _prepared_selection_run(
        tmp_path, monkeypatch, name=name, selected_count=4
    )


def _day_result(
    review,
    *,
    padding,
    duplicates=(),
    response_id,
    cache_scope="initial",
):
    return {
        "duplicate_pairs": list(duplicates),
        "padding_detected": padding,
        "thin_day_honest": False,
        "set_rationale": "The structured daily-set judgment is complete.",
        "response_id": response_id,
        "response_model": "gpt-test",
        "input_tokens": 1000,
        "cached_tokens": 0,
        "cache_write_tokens": 0,
        "output_tokens": 100,
        "reported_cost_usd": 0.005,
        "request_tags": ["job:quality-evaluation"],
        "raw_output_text": f'{{"response":"{response_id}"}}',
        "input_sha256": review.input_sha256,
        "prompt_cache_key": audience_insight_evaluations.day_set_prompt_cache_key(
            review.audience,
            review.input_sha256,
            cache_scope=cache_scope,
        ),
    }


def test_padding_veto_trims_one_tail_and_preserves_both_reviews(
    tmp_path, monkeypatch
):
    conn, candidate_ids = _prepared_four_selection_run(
        tmp_path, monkeypatch, name="padding-reconciled"
    )
    # Force both inputs onto the same numeric shard.  The explicit
    # reconciliation namespace must still make the routing keys distinct.
    monkeypatch.setattr(
        audience_insight_evaluations.llm_responses,
        "sharded_prompt_cache_key",
        lambda *, namespace, prompt_version, scope_key, shards: (
            f"fli:{namespace}:{prompt_version}:shard-00"
        ),
    )
    calls = []

    def review_day(_client, review, **kwargs):
        selected = tuple(item["candidate_id"] for item in review.selected)
        calls.append((selected, kwargs["run"]))
        return _day_result(
            review,
            padding=len(selected) == 4,
            response_id=f"day-{len(selected)}",
            cache_scope=(
                "initial" if len(selected) == 4 else "padding_tail_trim"
            ),
        )

    monkeypatch.setattr(
        audience_insight_evaluations, "review_day_set", review_day
    )
    result = audience_insight_runs.run_quality_reviews(
        conn, client=FakeClient()
    )

    assert result["quality_gate"]["passed"] is True
    assert result["counts"]["editor_selected"] == 4
    assert result["counts"]["selected"] == 3
    assert calls == [
        (tuple(candidate_ids), "padding-reconciled"),
        (tuple(candidate_ids[:3]), "padding-reconciled:padding-tail-trim"),
    ]
    assert [
        str(row[0])
        for row in conn.execute(
            "SELECT candidate_id FROM daily_selection ORDER BY editorial_rank"
        )
    ] == candidate_ids
    assert [
        str(row[0])
        for row in conn.execute(
            "SELECT candidate_id FROM publication_selection ORDER BY publication_rank"
        )
    ] == candidate_ids[:3]
    reconciliation = conn.execute(
        "SELECT * FROM selection_reconciliation"
    ).fetchone()
    assert reconciliation["status"] == "complete"
    assert reconciliation["reason_code"] == "padding_tail_trim"
    assert reconciliation["removed_candidate_id"] == candidate_ids[3]
    assert reconciliation["removed_editorial_rank"] == 4
    first = conn.execute("SELECT * FROM day_set_review").fetchone()
    second = conn.execute("SELECT * FROM reconciled_day_set_review").fetchone()
    assert first["padding_detected"] == 1
    assert first["response_id"] == "day-4"
    assert second["padding_detected"] == 0
    assert second["response_id"] == "day-3"
    assert first["input_sha256"] != second["input_sha256"]
    assert first["prompt_cache_key"] != second["prompt_cache_key"]
    assert "padding-tail-trim" not in first["prompt_cache_key"]
    assert "padding-tail-trim" in second["prompt_cache_key"]
    assert result["day_reviews"]["attempts"] == 2
    assert result["day_reviews"]["prompt_cache_keys"] == 2
    assert result["day_reviews"]["reported_cost_usd"] == pytest.approx(0.01)
    assert audience_insight_runs.selected_history_row(conn)[-1][
        "selected_item_id"
    ] == candidate_ids[2]

    original_first = dict(first)
    resumed = audience_insight_runs.run_quality_reviews(conn, client=FakeClient())
    assert len(calls) == 2
    assert resumed["quality_gate"]["passed"] is True
    assert dict(conn.execute("SELECT * FROM day_set_review").fetchone()) == original_first


def test_padding_veto_preserves_one_strong_item_from_a_thin_two_item_set(
    tmp_path, monkeypatch
):
    conn, candidate_ids = _prepared_selection_run(
        tmp_path, monkeypatch, name="thin-padding-reconciled", selected_count=2
    )
    calls = []

    def review_day(_client, review, **kwargs):
        selected = tuple(item["candidate_id"] for item in review.selected)
        calls.append((selected, kwargs["run"]))
        return _day_result(
            review,
            padding=len(selected) == 2,
            response_id=f"thin-day-{len(selected)}",
            cache_scope=(
                "initial" if len(selected) == 2 else "padding_tail_trim"
            ),
        ) | {"thin_day_honest": True}

    monkeypatch.setattr(
        audience_insight_evaluations, "review_day_set", review_day
    )
    result = audience_insight_runs.run_quality_reviews(
        conn, client=FakeClient()
    )

    assert result["quality_gate"]["passed"] is True
    assert result["counts"]["editor_selected"] == 2
    assert result["counts"]["selected"] == 1
    assert calls == [
        (tuple(candidate_ids), "thin-padding-reconciled"),
        (
            tuple(candidate_ids[:1]),
            "thin-padding-reconciled:padding-tail-trim",
        ),
    ]
    assert [
        str(row[0])
        for row in conn.execute(
            "SELECT candidate_id FROM publication_selection "
            "ORDER BY publication_rank"
        )
    ] == candidate_ids[:1]
    reconciliation = conn.execute(
        "SELECT * FROM selection_reconciliation"
    ).fetchone()
    assert reconciliation["removed_candidate_id"] == candidate_ids[1]
    assert reconciliation["removed_editorial_rank"] == 2


def test_reconciled_review_veto_fails_closed_without_a_second_trim(
    tmp_path, monkeypatch
):
    conn, candidate_ids = _prepared_four_selection_run(
        tmp_path, monkeypatch, name="padding-vetoed"
    )
    calls = 0

    def review_day(_client, review, **_kwargs):
        nonlocal calls
        calls += 1
        selected = tuple(item["candidate_id"] for item in review.selected)
        duplicates = (
            {
                "left_id": selected[0],
                "right_id": selected[1],
                "scope": "same_day",
                "rationale": "The final set still contains a duplicate.",
            },
        ) if len(selected) == 3 else ()
        return _day_result(
            review,
            padding=True,
            duplicates=duplicates,
            response_id=f"veto-{len(selected)}",
            cache_scope=(
                "initial" if len(selected) == 4 else "padding_tail_trim"
            ),
        )

    monkeypatch.setattr(
        audience_insight_evaluations, "review_day_set", review_day
    )
    result = audience_insight_runs.run_quality_reviews(
        conn, client=FakeClient()
    )
    assert result["quality_gate"]["passed"] is False
    assert {"no_padding", "no_duplicate_stories"} <= set(
        result["quality_gate"]["failure_reasons"]
    )
    assert result["counts"]["selected"] == 3
    assert calls == 2

    resumed = audience_insight_runs.run_quality_reviews(conn, client=FakeClient())
    assert resumed["quality_gate"]["passed"] is False
    assert resumed["counts"]["selected"] == 3
    assert calls == 2
    assert conn.execute("SELECT COUNT(*) FROM daily_selection").fetchone()[0] == 4
    assert conn.execute("SELECT COUNT(*) FROM publication_selection").fetchone()[0] == 3
    assert conn.execute(
        "SELECT removed_candidate_id FROM selection_reconciliation"
    ).fetchone()[0] == candidate_ids[3]


def test_reconciled_review_error_is_fail_closed_and_resumable(
    tmp_path, monkeypatch
):
    conn, _ = _prepared_four_selection_run(
        tmp_path, monkeypatch, name="padding-error"
    )

    def fail_second(_client, review, **_kwargs):
        if len(review.selected) == 4:
            return _day_result(
                review, padding=True, response_id="first-padding"
            )
        raise RuntimeError("temporary reviewer failure")

    monkeypatch.setattr(
        audience_insight_evaluations, "review_day_set", fail_second
    )
    with pytest.raises(RuntimeError, match="temporary reviewer failure"):
        audience_insight_runs.run_quality_reviews(conn, client=FakeClient())
    assert conn.execute("SELECT COUNT(*) FROM quality_gate").fetchone()[0] == 0
    assert conn.execute(
        "SELECT status FROM selection_reconciliation"
    ).fetchone()[0] == "failed"
    assert conn.execute(
        "SELECT status, attempts FROM reconciled_day_set_review"
    ).fetchone()[:] == ("failed", 1)
    assert conn.execute("SELECT COUNT(*) FROM daily_selection").fetchone()[0] == 4
    assert conn.execute("SELECT COUNT(*) FROM publication_selection").fetchone()[0] == 3

    def pass_resume(_client, review, **_kwargs):
        assert len(review.selected) == 3
        return _day_result(
            review,
            padding=False,
            response_id="resumed-pass",
            cache_scope="padding_tail_trim",
        )

    monkeypatch.setattr(
        audience_insight_evaluations, "review_day_set", pass_resume
    )
    resumed = audience_insight_runs.run_quality_reviews(conn, client=FakeClient())
    assert resumed["quality_gate"]["passed"] is True
    assert conn.execute(
        "SELECT status, attempts FROM reconciled_day_set_review"
    ).fetchone()[:] == ("complete", 2)
    assert conn.execute(
        "SELECT status FROM selection_reconciliation"
    ).fetchone()[0] == "complete"


def test_freeze_refuses_changed_audience_or_source_cohort(tmp_path):
    triage_db, artifact_db = _source_databases(tmp_path)
    conn = audience_insight_runs.connect_run(tmp_path / "run" / "insights.db")
    audience_insight_runs.freeze_run(
        conn,
        run_id="frozen",
        audience="investment",
        day="2026-07-11",
        triage_db=triage_db,
        artifact_db=artifact_db,
    )
    with pytest.raises(ValueError, match="frozen request"):
        audience_insight_runs.freeze_run(
            conn,
            run_id="frozen",
            audience="ai_engineering",
            day="2026-07-11",
            triage_db=triage_db,
            artifact_db=artifact_db,
        )

    triage = sqlite3.connect(triage_db)
    payload = json.loads(
        triage.execute(
            "SELECT envelope_json FROM triage_item WHERE event_id = 'event-1'"
        ).fetchone()[0]
    )
    payload["root"]["text"] = "Changed frozen text."
    triage.execute(
        "UPDATE triage_item SET envelope_json = ? WHERE event_id = 'event-1'",
        (json.dumps(payload),),
    )
    triage.commit()
    triage.close()
    with pytest.raises(ValueError, match="cohort_sha256"):
        audience_insight_runs.freeze_run(
            conn,
            run_id="frozen",
            audience="investment",
            day="2026-07-11",
            triage_db=triage_db,
            artifact_db=artifact_db,
        )


def test_repeated_citation_failure_becomes_audited_terminal_rejection(
    tmp_path, monkeypatch
):
    triage_db, artifact_db = _source_databases(tmp_path)
    conn = audience_insight_runs.connect_run(tmp_path / "rejection" / "insights.db")
    audience_insight_runs.freeze_run(
        conn,
        run_id="citation-rejection",
        audience="investment",
        day="2026-07-11",
        triage_db=triage_db,
        artifact_db=artifact_db,
    )

    def reject_quote(_client, packet, **_kwargs):
        result = _extraction_result(packet)
        result["supporting_quote"] = "A paraphrase that is not in evidence."
        raise audience_insights.CitationVerificationError(
            "supporting quote is not exact", result=result
        )

    monkeypatch.setattr(audience_insights, "evaluate_one", reject_quote)
    first = audience_insight_runs.run_pending(conn, client=FakeClient())
    second = audience_insight_runs.run_pending(
        conn, client=FakeClient(), retry_failed=True
    )

    assert first["counts"]["failed"] == 1
    assert second["counts"]["failed"] == 0
    assert second["counts"]["rejected"] == 1
    row = conn.execute("SELECT * FROM candidate_item").fetchone()
    assert row["status"] == "rejected"
    assert row["terminal_reason"] == "citation_verification_failed"
    assert row["attempts"] == 2
    assert row["completed_at"] is not None
    attempts = conn.execute(
        "SELECT attempt_number, status FROM candidate_attempt ORDER BY attempt_number"
    ).fetchall()
    assert [tuple(attempt) for attempt in attempts] == [
        (1, "failed"),
        (2, "rejected"),
    ]
    assert second["counts"]["insights"] == 0
    assert second["counts"]["expected_attempts"] == 2
    assert second["counts"]["recorded_attempts"] == 2
    assert second["counts"]["telemetry_missing_attempts"] == 0
    assert second["counts"]["input_tokens"] == 3600
    assert second["counts"]["reported_cost_usd"] == pytest.approx(0.02)
    assert audience_insight_runs.prepare_editor(conn) == 0


def test_terminal_rejection_requires_two_citation_failures(tmp_path, monkeypatch):
    triage_db, artifact_db = _source_databases(tmp_path)
    conn = audience_insight_runs.connect_run(tmp_path / "mixed" / "insights.db")
    audience_insight_runs.freeze_run(
        conn,
        run_id="mixed-failures",
        audience="investment",
        day="2026-07-11",
        triage_db=triage_db,
        artifact_db=artifact_db,
    )
    calls = 0

    def mixed_failures(_client, packet, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary provider failure")
        result = _extraction_result(packet)
        result["supporting_quote"] = "A paraphrase that is not in evidence."
        raise audience_insights.CitationVerificationError(
            "supporting quote is not exact", result=result
        )

    monkeypatch.setattr(audience_insights, "evaluate_one", mixed_failures)
    audience_insight_runs.run_pending(conn, client=FakeClient())
    after_one_citation_failure = audience_insight_runs.run_pending(
        conn, client=FakeClient(), retry_failed=True
    )
    assert after_one_citation_failure["counts"]["failed"] == 1
    assert after_one_citation_failure["counts"]["rejected"] == 0

    terminal = audience_insight_runs.run_pending(
        conn, client=FakeClient(), retry_failed=True
    )
    assert terminal["counts"]["failed"] == 0
    assert terminal["counts"]["rejected"] == 1
    assert terminal["counts"]["expected_attempts"] == 3
    assert terminal["counts"]["recorded_attempts"] == 3
    attempts = conn.execute(
        "SELECT status, error_type FROM candidate_attempt ORDER BY attempt_number"
    ).fetchall()
    assert [tuple(attempt) for attempt in attempts] == [
        ("failed", "RuntimeError"),
        ("failed", "CitationVerificationError"),
        ("rejected", "CitationVerificationError"),
    ]


def test_repeated_schema_failure_is_audited_and_terminal_but_provider_is_not(
    tmp_path, monkeypatch
):
    triage_db, artifact_db = _source_databases(tmp_path)
    conn = audience_insight_runs.connect_run(tmp_path / "schema" / "insights.db")
    audience_insight_runs.freeze_run(
        conn,
        run_id="schema-failures",
        audience="investment",
        day="2026-07-11",
        triage_db=triage_db,
        artifact_db=artifact_db,
    )
    calls = 0

    def schema_then_provider(_client, packet, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("temporary provider failure")
        result = _extraction_result(packet)
        result["raw_output_text"] = '{"outcome":"insight"}'
        raise audience_insights.ExtractionValidationError(
            "response does not match the exact audience insight schema",
            result=result,
        )

    monkeypatch.setattr(audience_insights, "evaluate_one", schema_then_provider)
    first = audience_insight_runs.run_pending(conn, client=FakeClient())
    transient = audience_insight_runs.run_pending(
        conn, client=FakeClient(), retry_failed=True
    )
    terminal = audience_insight_runs.run_pending(
        conn, client=FakeClient(), retry_failed=True
    )

    assert first["counts"]["failed"] == 1
    assert transient["counts"]["failed"] == 1
    assert transient["counts"]["rejected"] == 0
    assert terminal["counts"]["failed"] == 0
    assert terminal["counts"]["rejected"] == 1
    row = conn.execute("SELECT * FROM candidate_item").fetchone()
    assert row["terminal_reason"] == "schema_validation_failed"
    assert row["raw_output_text"] == '{"outcome":"insight"}'
    attempts = conn.execute(
        """SELECT status, error_type, raw_output_text, response_id,
                  input_tokens, reported_cost_usd
           FROM candidate_attempt ORDER BY attempt_number"""
    ).fetchall()
    assert [tuple(attempt[:2]) for attempt in attempts] == [
        ("failed", "ExtractionValidationError"),
        ("failed", "RuntimeError"),
        ("rejected", "ExtractionValidationError"),
    ]
    assert attempts[0]["raw_output_text"] == '{"outcome":"insight"}'
    assert attempts[0]["response_id"] == "resp-extract"
    assert attempts[0]["input_tokens"] == 1800
    assert attempts[0]["reported_cost_usd"] == pytest.approx(0.01)
    assert attempts[1]["raw_output_text"] is None
    assert terminal["counts"]["expected_attempts"] == 3
    assert terminal["counts"]["recorded_attempts"] == 3
    assert terminal["counts"]["telemetry_missing_attempts"] == 0
    assert terminal["counts"]["reported_cost_usd"] == pytest.approx(0.02)


def _history_run(
    root: Path,
    *,
    day: str,
    run_id: str,
    computed_at: str,
    passed: bool,
    claim: str,
    audience: str = "investment",
) -> Path:
    path = root / day / audience / run_id / "insights.db"
    path.parent.mkdir(parents=True)
    conn = sqlite3.connect(path)
    conn.executescript(
        """CREATE TABLE run_meta (
               singleton INTEGER PRIMARY KEY,
               audience TEXT,
               day TEXT,
               run_id TEXT,
               created_at TEXT
           );
           CREATE TABLE editor_run (
               singleton INTEGER PRIMARY KEY,
               status TEXT
           );
           CREATE TABLE quality_gate (
               singleton INTEGER PRIMARY KEY,
               passed INTEGER,
               computed_at TEXT
           );
           CREATE TABLE candidate_item (
               candidate_id TEXT PRIMARY KEY,
               claim TEXT,
               audience_fields_json TEXT,
               citation_source_author TEXT,
               citation_source_title TEXT
           );
           CREATE TABLE daily_selection (
               editorial_rank INTEGER,
               candidate_id TEXT
           );
           CREATE TABLE publication_selection (
               publication_rank INTEGER,
               candidate_id TEXT
           );"""
    )
    candidate_id = f"candidate-{run_id}"
    conn.execute(
        "INSERT INTO run_meta VALUES (1, ?, ?, ?, ?)",
        (audience, day, run_id, computed_at),
    )
    conn.execute("INSERT INTO editor_run VALUES (1, 'complete')")
    conn.execute(
        "INSERT INTO quality_gate VALUES (1, ?, ?)",
        (int(passed), computed_at),
    )
    conn.execute(
        "INSERT INTO candidate_item VALUES (?, ?, '{}', '@author', 'Source')",
        (candidate_id, claim),
    )
    conn.execute("INSERT INTO daily_selection VALUES (1, ?)", (candidate_id,))
    conn.execute("INSERT INTO publication_selection VALUES (1, ?)", (candidate_id,))
    conn.commit()
    conn.close()
    return path


def test_prior_history_uses_latest_audited_passed_run_once_per_day(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        audience_insight_runs.audience_insight_publication_audit,
        "validate_readonly_publication_audit",
        lambda **_kwargs: {"passed": True},
    )
    root = tmp_path / "runs"
    _history_run(
        root,
        day="2026-07-08",
        run_id="passed-old",
        computed_at="2026-07-08T10:00:00+00:00",
        passed=True,
        claim="Older passed claim.",
    )
    _history_run(
        root,
        day="2026-07-08",
        run_id="failed-newer",
        computed_at="2026-07-08T12:00:00+00:00",
        passed=False,
        claim="Failed claim that must be ignored.",
    )
    _history_run(
        root,
        day="2026-07-08",
        run_id="passed-new",
        computed_at="2026-07-08T11:00:00+00:00",
        passed=True,
        claim="Latest passed claim.",
    )
    _history_run(
        root,
        day="2026-07-09",
        run_id="passed-next-day",
        computed_at="2026-07-09T09:00:00+00:00",
        passed=True,
        claim="Next day passed claim.",
    )
    _history_run(
        root,
        day="2026-07-10",
        run_id="future-run",
        computed_at="2026-07-10T09:00:00+00:00",
        passed=True,
        claim="Current-day claim that must be ignored.",
    )

    history = audience_insight_runs._prior_history(
        root=root,
        audience="investment",
        day="2026-07-10",
    )

    assert [item["claim"] for item in history] == [
        "Latest passed claim.",
        "Next day passed claim.",
    ]


def test_prior_history_falls_back_when_newer_internal_pass_lacks_audit(
    tmp_path, monkeypatch
):
    root = tmp_path / "runs"
    _history_run(
        root,
        day="2026-07-08",
        run_id="audited-old",
        computed_at="2026-07-08T10:00:00+00:00",
        passed=True,
        claim="Audited history.",
    )
    _history_run(
        root,
        day="2026-07-08",
        run_id="unaudited-new",
        computed_at="2026-07-08T11:00:00+00:00",
        passed=True,
        claim="Internal-only history.",
    )

    def validate(*, source_run_db, **_kwargs):
        if source_run_db.parent.name == "unaudited-new":
            raise ValueError("missing exact publication audit")
        return {"passed": True}

    monkeypatch.setattr(
        audience_insight_runs.audience_insight_publication_audit,
        "validate_readonly_publication_audit",
        validate,
    )

    history = audience_insight_runs._prior_history(
        root=root,
        audience="investment",
        day="2026-07-09",
    )

    assert [item["claim"] for item in history] == ["Audited history."]


def test_prior_history_consumes_effective_finalized_zero_projection(
    tmp_path, monkeypatch
):
    root = tmp_path / "runs"
    _history_run(
        root,
        day="2026-07-08",
        run_id="finalized-zero",
        computed_at="2026-07-08T10:00:00+00:00",
        passed=True,
        claim="Failed publication item that must not enter history.",
    )
    calls = []

    def projection(**kwargs):
        calls.append(kwargs["source_run_db"])
        return {
            "mode": "audit_disqualified_zero",
            "effective_selected_ids": [],
        }

    monkeypatch.setattr(
        audience_insight_runs.audience_insight_publication_audit,
        "validated_publication_projection",
        projection,
    )

    history = audience_insight_runs._prior_history(
        root=root,
        audience="investment",
        day="2026-07-09",
    )

    assert len(calls) == 1
    assert history == []


def test_prior_history_retains_senior_editorial_veto_for_duplicate_suppression(
    tmp_path, monkeypatch
):
    root = tmp_path / "runs"
    _history_run(
        root,
        day="2026-07-08",
        run_id="editorial-veto",
        computed_at="2026-07-08T10:00:00+00:00",
        passed=True,
        claim="Mechanically valid framing vetoed from release.",
    )
    candidate_id = "candidate-editorial-veto"
    audit_module = audience_insight_runs.audience_insight_publication_audit
    finalization_reason = audit_module.EDITORIAL_FINALIZATION_REASON_CODE

    monkeypatch.setattr(
        audience_insight_runs.audience_insight_publication_audit,
        "validated_publication_projection",
        lambda **_kwargs: {
            "mode": "editorial_disqualified_zero",
            "base_selected_ids": [candidate_id],
            "effective_selected_ids": [],
            "finalization": {"reason_code": finalization_reason},
        },
    )

    history = audience_insight_runs._prior_history(
        root=root,
        audience="investment",
        day="2026-07-09",
    )

    assert [item["claim"] for item in history] == [
        "Mechanically valid framing vetoed from release."
    ]


def test_explicit_history_preserves_exact_order_and_projection_semantics(
    tmp_path, monkeypatch
):
    root = tmp_path / "runs"
    audit_veto = _history_run(
        root,
        day="2026-07-06",
        run_id="audit-veto",
        computed_at="2026-07-06T10:00:00+00:00",
        passed=True,
        claim="Audit-vetoed framing.",
    )
    editorial_veto = _history_run(
        root,
        day="2026-07-07",
        run_id="editorial-veto-explicit",
        computed_at="2026-07-07T10:00:00+00:00",
        passed=True,
        claim="Editorially vetoed framing retained for suppression.",
    )
    calls = []

    def projection(*, source_run_db, audit_db):
        calls.append((source_run_db, audit_db))
        candidate_id = f"candidate-{source_run_db.parent.name}"
        if source_run_db == audit_veto.resolve():
            return {
                "mode": "audit_disqualified_zero",
                "base_selected_ids": [candidate_id],
                "effective_selected_ids": [],
                "finalization": {"reason_code": "audit_disqualification"},
            }
        return {
            "mode": "editorial_disqualified_zero",
            "base_selected_ids": [candidate_id],
            "effective_selected_ids": [],
            "finalization": {
                "reason_code": audience_insight_runs.audience_insight_publication_audit.EDITORIAL_FINALIZATION_REASON_CODE
            },
        }

    monkeypatch.setattr(
        audience_insight_runs.audience_insight_publication_audit,
        "validated_publication_projection",
        projection,
    )

    history, resolved = audience_insight_runs._explicit_prior_history(
        prior_run_dbs=[audit_veto, editorial_veto],
        audience="investment",
        day="2026-07-08",
    )

    assert [item["claim"] for item in history] == [
        "Editorially vetoed framing retained for suppression."
    ]
    assert [source["day"] for source in resolved["sources"]] == [
        "2026-07-06",
        "2026-07-07",
    ]
    assert [source["projection_mode"] for source in resolved["sources"]] == [
        "audit_disqualified_zero",
        "editorial_disqualified_zero",
    ]
    assert calls == [
        (
            audit_veto.resolve(),
            audit_veto.parent / "publication-audit-v1" / "audit.db",
        ),
        (
            editorial_veto.resolve(),
            editorial_veto.parent / "publication-audit-v1" / "audit.db",
        ),
    ]


def test_explicit_history_rejects_wrong_audience(tmp_path):
    run_db = _history_run(
        tmp_path / "runs",
        day="2026-07-06",
        run_id="engineering-run",
        computed_at="2026-07-06T10:00:00+00:00",
        passed=True,
        claim="Engineering claim.",
        audience="ai_engineering",
    )

    with pytest.raises(ValueError, match="audience does not match"):
        audience_insight_runs._explicit_prior_history(
            prior_run_dbs=[run_db],
            audience="investment",
            day="2026-07-07",
        )


def test_explicit_history_rejects_current_or_future_day(tmp_path):
    run_db = _history_run(
        tmp_path / "runs",
        day="2026-07-08",
        run_id="not-prior",
        computed_at="2026-07-08T10:00:00+00:00",
        passed=True,
        claim="Not prior.",
    )

    with pytest.raises(ValueError, match="must be earlier"):
        audience_insight_runs._explicit_prior_history(
            prior_run_dbs=[run_db],
            audience="investment",
            day="2026-07-08",
        )


def test_explicit_history_rejects_duplicate_day(tmp_path):
    root = tmp_path / "runs"
    first = _history_run(
        root,
        day="2026-07-06",
        run_id="first",
        computed_at="2026-07-06T10:00:00+00:00",
        passed=True,
        claim="First.",
    )
    second = _history_run(
        root,
        day="2026-07-06",
        run_id="second",
        computed_at="2026-07-06T11:00:00+00:00",
        passed=True,
        claim="Second.",
    )
    with pytest.raises(ValueError, match="duplicate day"):
        audience_insight_runs._explicit_prior_history(
            prior_run_dbs=[first, second],
            audience="investment",
            day="2026-07-08",
        )


def test_explicit_history_rejects_out_of_order_days(tmp_path, monkeypatch):
    root = tmp_path / "runs"
    earlier = _history_run(
        root,
        day="2026-07-06",
        run_id="earlier",
        computed_at="2026-07-06T10:00:00+00:00",
        passed=True,
        claim="Earlier.",
    )
    later = _history_run(
        root,
        day="2026-07-07",
        run_id="later",
        computed_at="2026-07-07T10:00:00+00:00",
        passed=True,
        claim="Later.",
    )
    monkeypatch.setattr(
        audience_insight_runs.audience_insight_publication_audit,
        "validated_publication_projection",
        lambda **_kwargs: pytest.fail(
            "malformed chain must fail before publication sidecar validation"
        ),
    )

    with pytest.raises(ValueError, match="strictly increasing"):
        audience_insight_runs._explicit_prior_history(
            prior_run_dbs=[later, earlier],
            audience="investment",
            day="2026-07-08",
        )


@pytest.mark.parametrize("failure", ["stale audit", "stale finalization"])
def test_explicit_history_fails_closed_on_stale_publication_sidecar(
    tmp_path, monkeypatch, failure
):
    run_db = _history_run(
        tmp_path / "runs",
        day="2026-07-06",
        run_id="stale-sidecar",
        computed_at="2026-07-06T10:00:00+00:00",
        passed=True,
        claim="Stale sidecar claim.",
    )
    monkeypatch.setattr(
        audience_insight_runs.audience_insight_publication_audit,
        "validated_publication_projection",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError(failure)),
    )

    with pytest.raises(ValueError, match="missing or stale"):
        audience_insight_runs._explicit_prior_history(
            prior_run_dbs=[run_db],
            audience="investment",
            day="2026-07-07",
        )


def test_run_rejects_implicit_history_before_creating_model_client(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(
        audience_insight_runs.entity_kinds,
        "create_litellm_client",
        lambda: pytest.fail("model client must not be created"),
    )

    assert audience_insight_runs.main(
        [
            "run",
            "--run-id",
            "implicit-history",
            "--run-db",
            str(tmp_path / "run" / "insights.db"),
            "--audience",
            "investment",
            "--day",
            "2026-07-08",
        ]
    ) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "E_INVALID_INPUT"
    assert "must not use implicit directory recency" in payload["error"]["message"]


def test_long_text_sectioning_is_verbatim_and_lossless():
    text = ("a" * 40_000) + "\n\n" + ("b" * 40_000) + "\n\n" + ("c" * 40_000)
    sections = audience_insight_runs._section_text(text)

    assert len(sections) == 3
    reconstructed = "".join(section for _, _, section in sections)
    # The sectioner drops only boundary newlines, never source prose.
    assert reconstructed == text.replace("\n\n", "")
    assert all(section for _, _, section in sections)
    assert all(end > start for start, end, _ in sections)
