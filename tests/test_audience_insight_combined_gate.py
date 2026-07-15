import json
from pathlib import Path

from fli import (
    audience_insight_combined_gate as combined_gate,
    audience_insight_publication_audit as publication_audit,
    audience_insight_runs,
)


def _packet(*, event_id: str, day: str, rank: int) -> str:
    text = f"Researcher reported a bounded result for {event_id}."
    return json.dumps(
        {
            "event_id": event_id,
            "day": day,
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
                    "source_sha256": f"sha-{event_id}",
                    "section_ordinal": None,
                    "source_char_start": None,
                    "source_char_end": None,
                }
            ],
        }
    )


def _store_passing_audit_results(audit) -> None:
    meta = audit.execute("SELECT * FROM audit_run WHERE singleton = 1").fetchone()
    rows = audit.execute("SELECT * FROM audit_item ORDER BY audit_item_id").fetchall()
    tags = list(
        publication_audit.request_tags(
            audience=str(meta["audience"]),
            audit_id=str(meta["audit_id"]),
            day=str(meta["day"]),
        )
    )
    for row in rows:
        output = {
            "audit_item_id": str(row["audit_item_id"]),
            "citation_fidelity": "pass",
            "attribution_fidelity": "pass",
            "epistemic_discipline": "pass",
            "audience_usefulness": "pass",
            "actionability": "pass",
            "specificity": "pass",
            "failure_codes": [],
            "rationale": "All dimensions pass.",
        }
        result = {
            **output,
            "raw_output_text": json.dumps(output, sort_keys=True),
            "response_id": "resp-audit",
            "response_model": "gpt-5.6-luna",
            "input_tokens": 1_200,
            "cached_tokens": 800,
            "cache_write_tokens": 0,
            "output_tokens": 100,
            "reported_cost_usd": 0.01,
            "request_tags": tags,
        }
        publication_audit._store_success(audit, row, meta, result)


def _make_pair(
    root: Path,
    *,
    audience: str,
    day: str,
    selected_count: int,
    passing_reject_count: int = 0,
) -> Path:
    run_id = f"run-{audience}-{day}"
    source_path = root / day / audience / run_id / "insights.db"
    conn = audience_insight_runs.connect_run(source_path)
    now = "2026-07-15T00:00:00+00:00"
    prompt_version = (
        "investment-insight-v2.2"
        if audience == "investment"
        else "ai-engineering-insight-v2.3"
    )
    editor_version = (
        "investment-daily-editor-v2.1"
        if audience == "investment"
        else "ai-engineering-daily-editor-v2.3"
    )
    conn.execute(
        """INSERT INTO run_meta
           (singleton, run_id, audience, day, model, reasoning_effort,
            prompt_version, prompt_sha256, schema_version, editor_model,
            editor_reasoning_effort, editor_prompt_version,
            editor_prompt_sha256, editor_schema_version, review_model,
            review_reasoning_effort, item_review_prompt_version,
            item_review_prompt_sha256, item_review_schema_version,
            day_review_prompt_version, day_review_prompt_sha256,
            day_review_schema_version, source_triage_db, source_artifact_db,
            rank_limit, event_ids_json, cohort_sha256, expected_count,
            created_at, updated_at)
           VALUES (1, ?, ?, ?, 'luna', 'high', ?, 'extract-sha',
                   'extract-schema', 'luna', 'high', ?, 'editor-sha',
                   'editor-schema', 'luna', 'high', 'filter-v2', 'filter-sha',
                   'filter-schema', 'day-v2', 'day-sha', 'day-schema',
                   'triage.db', 'artifact.db', 50, '[]', 'cohort', ?, ?, ?)""",
        (
            run_id,
            audience,
            day,
            prompt_version,
            editor_version,
            selected_count + passing_reject_count,
            now,
            now,
        ),
    )
    candidate_ids: list[str] = []
    for index in range(selected_count + passing_reject_count):
        candidate_id = f"candidate-{audience}-{day}-{index + 1}"
        event_id = f"event-{audience}-{day}-{index + 1}"
        quote = f"Researcher reported a bounded result for {event_id}."
        audience_fields = (
            {
                "investment_implication": "If validated, compare the product's execution risk.",
                "what_to_watch": "Check whether an independent evaluation reproduces the result.",
            }
            if audience == "investment"
            else {
                "action_type": "evaluate",
                "engineering_action": "Reproduce the result on a representative workload.",
                "validation_boundary": "Do not adopt it unless the bounded result reproduces.",
            }
        )
        conn.execute(
            """INSERT INTO candidate_item
               (candidate_id, event_id, day, feed_rank, packet_json, input_text,
                input_sha256, prompt_cache_key, status, outcome, claim,
                claim_posture, why_it_matters, audience_fields_json,
                supporting_quote, citation_block_index, citation_source_type,
                citation_source_id, citation_source_url, citation_source_author,
                citation_source_sha256, citation_char_start, citation_char_end,
                updated_at)
               VALUES (?, ?, ?, ?, ?, 'source input', ?, ?, 'complete',
                       'insight', ?, 'third_party_observation', ?, ?, ?, 1,
                       'x_post', ?, ?, '@researcher', ?, 0, ?, ?)""",
            (
                candidate_id,
                event_id,
                day,
                index + 1,
                _packet(event_id=event_id, day=day, rank=index + 1),
                f"input-sha-{candidate_id}",
                f"cache-{candidate_id}",
                f"The researcher reported a bounded result for {event_id}.",
                "If reproduced, the result could change a concrete decision.",
                json.dumps(audience_fields),
                quote,
                f"post-{event_id}",
                f"https://x.com/researcher/status/{event_id}",
                f"sha-{event_id}",
                len(quote),
                now,
            ),
        )
        candidate_ids.append(candidate_id)
        if index < selected_count:
            conn.execute(
                """INSERT INTO publication_selection
                   (publication_rank, original_editorial_rank,
                    candidate_id, activated_at)
                   VALUES (?, ?, ?, ?)""",
                (index + 1, index + 1, candidate_id, now),
            )
        else:
            conn.execute(
                """INSERT INTO item_review
                   (candidate_id, status, attempts, input_text, input_sha256,
                    prompt_cache_key, claim_fidelity, epistemic_discipline,
                    audience_usefulness, actionability, specificity,
                    failure_codes_json, rationale, updated_at)
                   VALUES (?, 'complete', 1, 'review input', ?, ?, 'fail', 'pass',
                           'fail', 'fail', 'fail', '["not_decision_relevant"]',
                           'The source filter rejected this item.', ?)""",
                (
                    candidate_id,
                    f"review-sha-{candidate_id}",
                    f"review-cache-{candidate_id}",
                    now,
                ),
            )
    gate_result = {
        "audience": audience,
        "day": day,
        "selected_count": selected_count,
        "thin_day": selected_count < 3,
        "checks": {
            "fixture_complete": True,
            "thin_day_honest_and_all_quality": True,
        },
        "passed": True,
    }
    conn.execute(
        "INSERT INTO quality_gate VALUES (1, 1, ?, ?)",
        (json.dumps(gate_result), now),
    )
    conn.commit()
    conn.close()

    audit_path = source_path.parent / combined_gate.ADJACENT_AUDIT_PATH
    audit = publication_audit.connect(audit_path)
    publication_audit.freeze_audit(
        audit,
        audit_id=f"audit-{audience}-{day}",
        source_run_db=source_path,
    )
    _store_passing_audit_results(audit)
    audit.close()
    return source_path


def _manifest(
    path: Path,
    sources: list[Path],
    *,
    holdout_day: str | dict[str, str],
    policies: dict[str, str] | None = None,
    evaluation_days: dict[str, list[str]] | None = None,
) -> Path:
    days_by_audience = {
        audience: sorted(
            source.parents[2].name
            for source in sources
            if source.parents[1].name == audience
        )
        for audience in ("investment", "ai_engineering")
    }
    holdout_days = (
        holdout_day
        if isinstance(holdout_day, dict)
        else {audience: holdout_day for audience in days_by_audience}
    )
    payload = {
        "schema_version": combined_gate.MANIFEST_SCHEMA_VERSION,
        "evaluation_id": "quality-calibration-v1",
        "audiences": {
            audience: {
                "policy": (policies or {}).get(
                    audience, combined_gate.STANDARD_POLICY
                ),
                "holdout_day": holdout_days[audience],
                "evaluation_days": (evaluation_days or {}).get(
                    audience, days_by_audience[audience]
                ),
            }
            for audience in days_by_audience
        },
        "runs": [{"source_run_db": str(source)} for source in sources],
    }
    path.write_text(json.dumps(payload))
    return path


def _passing_window(tmp_path: Path, *, passing_reject: bool = False) -> list[Path]:
    sources = []
    for audience in ("investment", "ai_engineering"):
        sources.append(
            _make_pair(
                tmp_path / "runs",
                audience=audience,
                day="2026-07-11",
                selected_count=1,
            )
        )
        sources.append(
            _make_pair(
                tmp_path / "runs",
                audience=audience,
                day="2026-07-13",
                selected_count=2,
                passing_reject_count=int(
                    passing_reject and audience == "investment"
                ),
            )
        )
    return sources


def test_combined_gate_passes_and_writes_byte_deterministic_report(tmp_path):
    sources = _passing_window(tmp_path)
    manifest = _manifest(tmp_path / "manifest.json", sources, holdout_day="2026-07-13")

    first = combined_gate.evaluate_manifest(manifest)
    second = combined_gate.evaluate_manifest(manifest)

    assert first == second
    assert first["passed"] is True
    assert first["blocking_reasons"] == []
    assert first["checks"][
        "exact_evaluation_day_set_present_for_each_audience"
    ] is True
    assert first["checks"]["uniform_source_contract_per_audience"] is True
    for audience in ("investment", "ai_engineering"):
        report = first["audiences"][audience]
        assert report["selected_count"] == 3
        assert report["selected_days"] == ["2026-07-11", "2026-07-13"]
        assert report["holdout_selected_count"] == 2
        assert report["joint_quality_ratio"] == 1.0
        assert report["checks"]["exact_manifest_day_set_present"] is True
        assert report["checks"]["uniform_source_contract"] is True
        assert len(report["source_contract_sha256s"]) == 1

    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    combined_gate.write_report(first, first_path)
    combined_gate.write_report(second, second_path)
    assert first_path.read_bytes() == second_path.read_bytes()


def test_combined_gate_rejects_a_missing_declared_audience_day(tmp_path):
    sources = _passing_window(tmp_path)
    sources = [
        source
        for source in sources
        if not ("/ai_engineering/" in str(source) and "2026-07-11" in str(source))
    ]
    manifest = _manifest(
        tmp_path / "manifest.json",
        sources,
        holdout_day="2026-07-13",
        evaluation_days={
            "investment": ["2026-07-11", "2026-07-13"],
            "ai_engineering": ["2026-07-11", "2026-07-13"],
        },
    )

    report = combined_gate.evaluate_manifest(manifest)

    assert report["passed"] is False
    assert report["checks"][
        "exact_evaluation_day_set_present_for_each_audience"
    ] is False
    assert report["audiences"]["investment"]["checks"][
        "exact_manifest_day_set_present"
    ] is True
    assert report["audiences"]["ai_engineering"]["checks"][
        "exact_manifest_day_set_present"
    ] is False


def test_combined_gate_rejects_contract_drift_with_valid_adjacent_audit(tmp_path):
    sources = _passing_window(tmp_path)
    drifted = next(
        source
        for source in sources
        if "/investment/" in str(source) and "2026-07-13" in str(source)
    )
    source = audience_insight_runs.connect_run(drifted)
    source.execute(
        "UPDATE run_meta SET item_review_prompt_version = 'filter-v3' "
        "WHERE singleton = 1"
    )
    source.commit()
    source.close()

    audit_path = drifted.parent / combined_gate.ADJACENT_AUDIT_PATH
    audit_path.unlink()
    audit = publication_audit.connect(audit_path)
    publication_audit.freeze_audit(
        audit,
        audit_id="audit-investment-2026-07-13-drifted",
        source_run_db=drifted,
    )
    _store_passing_audit_results(audit)
    audit.close()

    manifest = _manifest(tmp_path / "manifest.json", sources, holdout_day="2026-07-13")
    report = combined_gate.evaluate_manifest(manifest)

    assert report["passed"] is False
    assert report["checks"]["uniform_source_contract_per_audience"] is False
    assert report["audiences"]["investment"]["checks"][
        "uniform_source_contract"
    ] is False
    assert report["audiences"]["ai_engineering"]["checks"][
        "uniform_source_contract"
    ] is True


def test_zero_item_days_never_make_window_pass_vacuously(tmp_path):
    sources = [
        _make_pair(
            tmp_path / "runs",
            audience=audience,
            day=day,
            selected_count=0,
        )
        for audience in ("investment", "ai_engineering")
        for day in ("2026-07-11", "2026-07-13")
    ]
    manifest = _manifest(tmp_path / "manifest.json", sources, holdout_day="2026-07-13")

    report = combined_gate.evaluate_manifest(manifest)

    assert report["passed"] is False
    for audience in ("investment", "ai_engineering"):
        audience_report = report["audiences"][audience]
        assert audience_report["thin_zero_item_days"] == [
            "2026-07-11",
            "2026-07-13",
        ]
        assert audience_report["joint_quality_ratio"] == 0.0
        assert audience_report["checks"]["selected_count_at_least_three"] is False
        assert audience_report["checks"]["holdout_has_selection"] is False
        assert audience_report["checks"]["joint_quality_at_least_80_percent"] is False

    output = tmp_path / "failing-report.json"
    assert combined_gate.main(
        ["--manifest", str(manifest), "--output", str(output)]
    ) == 4
    assert json.loads(output.read_text())["passed"] is False


def _write_would_not_enter_adjudications(
    source: Path,
    run_report: dict,
) -> None:
    pairs = list(
        zip(
            run_report["false_negative_review_rejects"]["audit_item_ids"],
            run_report["false_negative_review_rejects"]["source_candidate_ids"],
            strict=True,
        )
    )
    payload = {
        "schema_version": combined_gate.ADJUDICATION_SCHEMA_VERSION,
        "source_run_id": run_report["source_run_id"],
        "source_contract_sha256": run_report["source_contract_sha256"],
        "audit_id": run_report["audit_id"],
        "audit_cohort_sha256": run_report["audit_cohort_sha256"],
        "audit_result_sha256": run_report["audit_result_sha256"],
        "adjudications": [
            {
                "audit_item_id": audit_item_id,
                "source_candidate_id": candidate_id,
                "verdict": "would_not_enter",
                "rationale": "The exact frozen reject remains below the daily bar.",
            }
            for audit_item_id, candidate_id in pairs
        ],
    }
    path = source.parent / combined_gate.ADJACENT_ADJUDICATION_PATH
    path.write_text(json.dumps(payload))


def _sparse_policy_window(tmp_path: Path, *, investment_selected: int) -> list[Path]:
    sources = []
    for day in ("2026-07-05", "2026-07-06", "2026-07-09", "2026-07-11", "2026-07-13"):
        sources.append(
            _make_pair(
                tmp_path / "runs",
                audience="investment",
                day=day,
                selected_count=investment_selected if day == "2026-07-09" else 0,
                passing_reject_count=5 if day == "2026-07-06" else 0,
            )
        )
    for day, selected_count in (("2026-07-11", 1), ("2026-07-13", 2)):
        sources.append(
            _make_pair(
                tmp_path / "runs",
                audience="ai_engineering",
                day=day,
                selected_count=selected_count,
            )
        )
    return sources


def test_audited_sparse_policy_passes_without_weakening_standard_gate(tmp_path):
    sources = _sparse_policy_window(tmp_path, investment_selected=1)
    manifest = _manifest(
        tmp_path / "manifest.json",
        sources,
        holdout_day={
            "investment": "2026-07-06",
            "ai_engineering": "2026-07-13",
        },
        policies={"investment": combined_gate.AUDITED_SPARSE_POLICY},
    )

    blocked = combined_gate.evaluate_manifest(manifest)
    holdout_run = next(
        row
        for row in blocked["runs"]
        if row["audience"] == "investment" and row["day"] == "2026-07-06"
    )
    holdout_source = next(
        source
        for source in sources
        if "/investment/" in str(source) and "2026-07-06" in str(source)
    )
    _write_would_not_enter_adjudications(holdout_source, holdout_run)

    report = combined_gate.evaluate_manifest(manifest)

    assert report["passed"] is True
    investment = report["audiences"]["investment"]
    assert investment["policy"] == combined_gate.AUDITED_SPARSE_POLICY
    assert investment["outcome"] == "audited_sparse"
    assert investment["selected_count"] == 1
    assert investment["holdout_selected_count"] == 0
    assert investment["holdout_reject_audit_total"] == 5
    assert investment["standard_yield_checks"][
        "selected_count_at_least_three"
    ] is False
    assert report["audiences"]["ai_engineering"]["outcome"] == "standard_pass"


def test_audited_sparse_policy_still_rejects_an_all_zero_window(tmp_path):
    sources = _sparse_policy_window(tmp_path, investment_selected=0)
    manifest = _manifest(
        tmp_path / "manifest.json",
        sources,
        holdout_day={
            "investment": "2026-07-06",
            "ai_engineering": "2026-07-13",
        },
        policies={"investment": combined_gate.AUDITED_SPARSE_POLICY},
    )
    blocked = combined_gate.evaluate_manifest(manifest)
    holdout_run = next(
        row
        for row in blocked["runs"]
        if row["audience"] == "investment" and row["day"] == "2026-07-06"
    )
    holdout_source = next(
        source
        for source in sources
        if "/investment/" in str(source) and "2026-07-06" in str(source)
    )
    _write_would_not_enter_adjudications(holdout_source, holdout_run)

    report = combined_gate.evaluate_manifest(manifest)

    assert report["passed"] is False
    investment = report["audiences"]["investment"]
    assert investment["outcome"] == "failed"
    assert investment["checks"]["selected_count_at_least_one"] is False
    assert investment["checks"]["joint_quality_at_least_80_percent"] is False


def test_audited_sparse_policy_rejects_a_non_honest_zero_day(tmp_path):
    sources = _sparse_policy_window(tmp_path, investment_selected=1)
    manifest = _manifest(
        tmp_path / "manifest.json",
        sources,
        holdout_day={
            "investment": "2026-07-06",
            "ai_engineering": "2026-07-13",
        },
        policies={"investment": combined_gate.AUDITED_SPARSE_POLICY},
    )
    blocked = combined_gate.evaluate_manifest(manifest)
    holdout_run = next(
        row
        for row in blocked["runs"]
        if row["audience"] == "investment" and row["day"] == "2026-07-06"
    )
    holdout_source = next(
        source
        for source in sources
        if "/investment/" in str(source) and "2026-07-06" in str(source)
    )
    _write_would_not_enter_adjudications(holdout_source, holdout_run)

    zero_day = next(
        source
        for source in sources
        if "/investment/" in str(source) and "2026-07-05" in str(source)
    )
    conn = audience_insight_runs.connect_run(zero_day)
    gate = conn.execute(
        "SELECT result_json FROM quality_gate WHERE singleton = 1"
    ).fetchone()
    result = json.loads(gate["result_json"])
    result["thin_day"] = False
    result["checks"]["thin_day_honest_and_all_quality"] = False
    conn.execute(
        "UPDATE quality_gate SET result_json = ? WHERE singleton = 1",
        (json.dumps(result),),
    )
    conn.commit()
    conn.close()

    report = combined_gate.evaluate_manifest(manifest)

    assert report["passed"] is False
    investment = report["audiences"]["investment"]
    assert investment["checks"]["zero_item_days_are_explicitly_honest"] is False


def test_bound_would_not_enter_adjudication_clears_false_negative(tmp_path):
    sources = _passing_window(tmp_path, passing_reject=True)
    investment_holdout = next(
        path
        for path in sources
        if "/investment/" in str(path) and "2026-07-13" in str(path)
    )
    manifest = _manifest(tmp_path / "manifest.json", sources, holdout_day="2026-07-13")

    blocked = combined_gate.evaluate_manifest(manifest)
    blocked_run = next(
        row
        for row in blocked["runs"]
        if row["audience"] == "investment" and row["day"] == "2026-07-13"
    )
    assert blocked["passed"] is False
    assert blocked_run["false_negative_adjudication"]["status"] == "required_missing"
    finding = {
        "audit_item_id": blocked_run["false_negative_review_rejects"][
            "audit_item_ids"
        ][0],
        "source_candidate_id": blocked_run["false_negative_review_rejects"][
            "source_candidate_ids"
        ][0],
        "verdict": "would_not_enter",
        "rationale": "It repeats the selected story and would replace it, not add coverage.",
    }
    adjudication = {
        "schema_version": combined_gate.ADJUDICATION_SCHEMA_VERSION,
        "source_run_id": blocked_run["source_run_id"],
        "source_contract_sha256": blocked_run["source_contract_sha256"],
        "audit_id": blocked_run["audit_id"],
        "audit_cohort_sha256": blocked_run["audit_cohort_sha256"],
        "audit_result_sha256": blocked_run["audit_result_sha256"],
        "adjudications": [finding],
    }
    adjudication_path = (
        investment_holdout.parent / combined_gate.ADJACENT_ADJUDICATION_PATH
    )
    adjudication_path.write_text(json.dumps(adjudication))

    cleared = combined_gate.evaluate_manifest(manifest)
    cleared_run = next(
        row
        for row in cleared["runs"]
        if row["audience"] == "investment" and row["day"] == "2026-07-13"
    )
    assert cleared["passed"] is True
    assert cleared_run["false_negative_adjudication"]["status"] == "cleared"
    assert cleared_run["checks"]["false_negative_review_rejects_adjudicated"] is True

    adjudication["adjudications"][0]["verdict"] = "would_enter"
    adjudication_path.write_text(json.dumps(adjudication))
    would_enter = combined_gate.evaluate_manifest(manifest)
    assert would_enter["passed"] is False
    assert any("false_negative" in reason for reason in would_enter["blocking_reasons"])


def test_source_contract_mutation_blocks_gate(tmp_path):
    sources = _passing_window(tmp_path)
    manifest = _manifest(tmp_path / "manifest.json", sources, holdout_day="2026-07-13")
    source = sources[0]
    conn = audience_insight_runs.connect_run(source)
    conn.execute(
        "UPDATE candidate_item SET claim = 'The frozen claim was mutated.' WHERE candidate_id = (SELECT candidate_id FROM publication_selection LIMIT 1)"
    )
    conn.commit()
    conn.close()

    report = combined_gate.evaluate_manifest(manifest)
    run = next(row for row in report["runs"] if row["source_run_db"] == str(source))

    assert report["passed"] is False
    assert run["checks"]["audit_source_binding_valid"] is False
    assert run["source_binding_checks"]["source_contract_sha256_matches"] is False
    assert run["source_binding_mismatches"]
