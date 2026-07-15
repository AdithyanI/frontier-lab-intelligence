import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from fli import (
    artifact_x_articles,
    artifacts,
    audience_insight_production_reconciliation as reconciliation,
    audience_insight_publication_audit as publication_audit,
    audience_insight_runs,
    cli,
)


DAY = "2026-07-11"
NOW = "2026-07-15T00:00:00+00:00"


def _audience_fields(audience: str) -> dict[str, str]:
    if audience == "investment":
        return {
            "investment_implication": "Test whether the bounded result changes the thesis.",
            "what_to_watch": "Watch for an independent replication.",
        }
    return {
        "action_type": "benchmark",
        "engineering_action": "Benchmark the bounded method on the production workload.",
        "validation_boundary": "The supplied evidence covers one bounded workload.",
    }


def _passing_audit_result(audit_item_id: str, meta) -> dict:
    output = {
        "audit_item_id": audit_item_id,
        "citation_fidelity": "pass",
        "attribution_fidelity": "pass",
        "epistemic_discipline": "pass",
        "audience_usefulness": "pass",
        "actionability": "pass",
        "specificity": "pass",
        "failure_codes": [],
        "rationale": "The bounded claim and action follow from the supplied evidence.",
    }
    return {
        **output,
        "raw_output_text": json.dumps(output, sort_keys=True),
        "response_id": "resp-audit",
        "response_model": "gpt-5.6-luna",
        "input_tokens": 1_300,
        "cached_tokens": 900,
        "cache_write_tokens": 0,
        "output_tokens": 80,
        "reported_cost_usd": 0.004,
        "request_tags": list(
            publication_audit.request_tags(
                audience=str(meta["audience"]),
                audit_id=str(meta["audit_id"]),
                day=str(meta["day"]),
            )
        ),
    }


def _complete_run(root: Path, *, audience: str, day: str = DAY) -> tuple[Path, Path]:
    source = root / day / audience / "production-r1" / "insights.db"
    candidate_id = f"candidate-{audience}-{day}"
    event_id = f"event-{audience}-{day}"
    quote = f"Researcher reported a bounded result for {audience} on {day}."
    packet = json.dumps(
        {
            "event_id": event_id,
            "day": day,
            "feed_rank": 4,
            "sources": [
                {
                    "source_type": "x_post",
                    "source_id": f"post-{audience}",
                    "url": f"https://x.com/researcher/status/{audience}",
                    "text": quote,
                    "author": "@researcher",
                    "title": None,
                    "relation": "root",
                    "source_sha256": "source-sha",
                    "section_ordinal": None,
                    "source_char_start": None,
                    "source_char_end": None,
                }
            ],
        }
    )
    conn = audience_insight_runs.connect_run(source)
    contracts = reconciliation.current_expected_contracts()[audience]
    with conn:
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
               VALUES (1, ?, ?, ?, 'gpt-5.6-luna', 'medium', ?, 'extract-sha',
                       'extract-schema', 'gpt-5.6-luna', 'high', ?, 'editor-sha',
                       'editor-schema', 'gpt-5.6-luna', 'high', 'review-v2',
                       'review-sha', 'review-schema', 'day-v2', 'day-sha',
                       'day-schema', 'triage.db', 'artifacts.db', 50, ?,
                       'cohort-sha', 1, ?, ?)""",
            (
                f"production-{audience}-{day}-r1",
                audience,
                day,
                f"{audience}-insight-v2",
                f"{audience}-daily-editor-v2",
                json.dumps([event_id]),
                NOW,
                NOW,
            ),
        )
        conn.execute(
            """UPDATE run_meta
               SET model = ?, reasoning_effort = ?, prompt_version = ?,
                   prompt_sha256 = ?, schema_version = ?, editor_model = ?,
                   editor_reasoning_effort = ?, editor_prompt_version = ?,
                   editor_prompt_sha256 = ?, editor_schema_version = ?,
                   review_model = ?, review_reasoning_effort = ?,
                   item_review_prompt_version = ?, item_review_prompt_sha256 = ?,
                   item_review_schema_version = ?, day_review_prompt_version = ?,
                   day_review_prompt_sha256 = ?, day_review_schema_version = ?
               WHERE singleton = 1""",
            (
                contracts["extraction"]["model"],
                contracts["extraction"]["reasoning_effort"],
                contracts["extraction"]["prompt_version"],
                contracts["extraction"]["prompt_sha256"],
                contracts["extraction"]["schema_version"],
                contracts["editor"]["model"],
                contracts["editor"]["reasoning_effort"],
                contracts["editor"]["prompt_version"],
                contracts["editor"]["prompt_sha256"],
                contracts["editor"]["schema_version"],
                contracts["item_review"]["model"],
                contracts["item_review"]["reasoning_effort"],
                contracts["item_review"]["prompt_version"],
                contracts["item_review"]["prompt_sha256"],
                contracts["item_review"]["schema_version"],
                contracts["day_review"]["prompt_version"],
                contracts["day_review"]["prompt_sha256"],
                contracts["day_review"]["schema_version"],
            ),
        )
        conn.execute(
            """INSERT INTO candidate_item
               (candidate_id, event_id, day, feed_rank, packet_json, input_text,
                input_sha256, prompt_cache_key, status, attempts, outcome,
                claim, claim_posture, why_it_matters, audience_fields_json,
                supporting_quote, citation_block_index, citation_source_type,
                citation_source_id, citation_source_url, citation_source_author,
                citation_source_sha256, citation_char_start, citation_char_end,
                response_id, response_model, input_tokens, cached_tokens,
                cache_write_tokens, output_tokens, reported_cost_usd,
                request_tags_json, raw_output_text, completed_at, updated_at)
               VALUES (?, ?, ?, 4, ?, 'extract input', 'extract-input-sha',
                       'extract-cache', 'complete', 1, 'insight', ?,
                       'third_party_observation', 'The result supports a bounded action.',
                       ?, ?, 1, 'x_post', ?, ?, '@researcher', 'source-sha', 0,
                       ?, 'resp-extract', 'gpt-5.6-luna', 1500, 1000, 0, 90,
                       0.01, '[]', '{}', ?, ?)""",
            (
                candidate_id,
                event_id,
                day,
                packet,
                quote,
                json.dumps(_audience_fields(audience)),
                quote,
                f"post-{audience}",
                f"https://x.com/researcher/status/{audience}",
                len(quote),
                NOW,
                NOW,
            ),
        )
        conn.execute(
            """INSERT INTO candidate_attempt
               (candidate_id, attempt_number, status, result_json,
                raw_output_text, response_id, response_model, input_tokens,
                cached_tokens, cache_write_tokens, output_tokens,
                       reported_cost_usd, request_tags_json, created_at)
               VALUES (?, 1, 'complete', '{}', '{}', 'resp-extract',
                       'gpt-5.6-luna', 1500, 1000, 0, 90, 0.01, '[]', ?)""",
            (candidate_id, NOW),
        )
        conn.execute(
            "UPDATE candidate_attempt SET request_tags_json = ?",
            (json.dumps(["app:frontier-lab-intelligence", "job:extraction"]),),
        )
        conn.execute(
            """INSERT INTO item_review
               (candidate_id, status, attempts, input_text, input_sha256,
                prompt_cache_key, claim_fidelity, epistemic_discipline,
                audience_usefulness, actionability, specificity,
                failure_codes_json, rationale, response_id, response_model,
                input_tokens, cached_tokens, cache_write_tokens, output_tokens,
                reported_cost_usd, request_tags_json, raw_output_text,
                completed_at, updated_at)
               VALUES (?, 'complete', 1, 'review input', 'review-input-sha',
                       'review-cache', 'pass', 'pass', 'pass', 'pass', 'pass',
                       '[]', 'The item clears the audience bar.', 'resp-review',
                       'gpt-5.6-luna', 1200, 800, 0, 70, 0.003, ?, '{}', ?, ?)""",
            (
                candidate_id,
                json.dumps(["app:frontier-lab-intelligence", "job:item-review"]),
                NOW,
                NOW,
            ),
        )
        conn.execute(
            """INSERT INTO editor_run
               (singleton, status, attempts, candidate_set_sha256,
                history_sha256, prior_selected_json, input_text,
                prompt_cache_key, selected_count, thin_day_reason,
                response_id, response_model, input_tokens, cached_tokens,
                cache_write_tokens, output_tokens, reported_cost_usd,
                request_tags_json, raw_output_text, completed_at, updated_at)
               VALUES (1, 'complete', 1, 'candidate-set',
                       '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945',
                       '[]',
                       'editor input', 'editor-cache', 1, NULL, 'resp-editor',
                       'gpt-5.6-luna', 1400, 900, 0, 80, 0.005, ?, '{}', ?, ?)""",
            (
                json.dumps(["app:frontier-lab-intelligence", "job:editor"]),
                NOW,
                NOW,
            ),
        )
        conn.execute(
            """INSERT INTO daily_selection
               (editorial_rank, candidate_id, decision_value, audit_reason)
               VALUES (1, ?, ?, 'The item is decision-relevant.')""",
            (
                candidate_id,
                "thesis_or_model"
                if audience == "investment"
                else "experiment_or_benchmark",
            ),
        )
        conn.execute(
            """INSERT INTO publication_selection
               (publication_rank, original_editorial_rank, candidate_id,
                activated_at) VALUES (1, 1, ?, ?)""",
            (candidate_id, NOW),
        )
        review_input = json.dumps(
            {"selected": [{"candidate_id": candidate_id}]}, sort_keys=True
        )
        conn.execute(
            """INSERT INTO day_set_review
               (singleton, status, attempts, input_text, input_sha256,
                prompt_cache_key, duplicate_pairs_json, padding_detected,
                thin_day_honest, set_rationale, response_id, response_model,
                input_tokens, cached_tokens, cache_write_tokens, output_tokens,
                reported_cost_usd, request_tags_json, raw_output_text,
                completed_at, updated_at)
               VALUES (1, 'complete', 1, ?, 'day-input-sha', 'day-cache', '[]',
                       0, 1, 'The single selected item is not padding.',
                       'resp-day', 'gpt-5.6-luna', 1300, 850, 0, 75, 0.004,
                       ?, '{}', ?, ?)""",
            (
                review_input,
                json.dumps(["app:frontier-lab-intelligence", "job:day-review"]),
                NOW,
                NOW,
            ),
        )
        conn.execute(
            """INSERT INTO quality_gate
               (singleton, passed, result_json, computed_at)
               VALUES (1, 1, ?, ?)""",
            (
                json.dumps(
                    {
                        "audience": audience,
                        "day": day,
                        "checks": {"all_quality_checks": True},
                        "failure_reasons": [],
                        "passed": True,
                        "reconciliation": None,
                        "selected_count": 1,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                NOW,
            ),
        )
    conn.close()

    audit_db = source.parent / reconciliation.ADJACENT_AUDIT
    audit = publication_audit.connect(audit_db)
    publication_audit.freeze_audit(
        audit,
        audit_id=f"publication-audit-{audience}-{day}",
        source_run_db=source,
        reject_sample_limit=0,
    )
    meta = audit.execute("SELECT * FROM audit_run WHERE singleton = 1").fetchone()
    rows = audit.execute("SELECT * FROM audit_item ORDER BY audit_item_id").fetchall()
    for row in rows:
        publication_audit._store_success(
            audit,
            row,
            meta,
            _passing_audit_result(str(row["audit_item_id"]), meta),
        )
    audit.close()
    return source, audit_db


def _manifest(
    tmp_path: Path,
    *,
    x_article_cohort=None,
    mode: str = "partial",
    days: tuple[str, ...] = (DAY,),
) -> tuple[Path, dict]:
    runs = []
    for day in days:
        for audience in ("investment", "ai_engineering"):
            source, audit = _complete_run(
                tmp_path / "runs", audience=audience, day=day
            )
            runs.append(
                {
                    "audience": audience,
                    "day": day,
                    "source_run_db": str(source),
                    "audit_db": str(audit),
                    "expected_selected_count": 1,
                    "finalization_path": None,
                }
            )
    payload = {
        "schema_version": reconciliation.MANIFEST_SCHEMA_VERSION,
        "reconciliation_id": "production-partial-proof",
        "mode": mode,
        "expected_contracts": reconciliation.current_expected_contracts(),
        "expected_audience_days": {
            "investment": list(days),
            "ai_engineering": list(days),
        },
        "runs": runs,
        "x_article_cohort": x_article_cohort,
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path, payload


def _seed_terminal_x_article(path: Path) -> str:
    url = "https://x.com/i/article/123"
    artifact_id = hashlib.sha256(url.encode()).hexdigest()
    raw_snapshot = path.parent / "article-raw.json"
    text_snapshot = path.parent / "article-text.txt"
    raw_snapshot.write_bytes(b'{"article":{"contents":[]}}')
    text_snapshot.write_text("Bounded X Article body.\n")
    raw_sha256 = hashlib.sha256(raw_snapshot.read_bytes()).hexdigest()
    text_sha256 = hashlib.sha256(text_snapshot.read_bytes()).hexdigest()
    conn = artifacts.connect(path)
    with conn:
        conn.execute(
            """INSERT INTO artifact_import_run
               (import_run_id, schema_version, canonicalization_contract,
                source_feed_run_id, source_event_run_id, triage_runs_json,
                selection_policy, input_fingerprint, expected_candidate_count,
                accepted_count, excluded_count, failed_count, created_at,
                completed_at)
               VALUES ('import', ?, 'test-contract', 'feed', 'events', '[]',
                       'test', 'import-fingerprint', 1, 1, 0, 0, ?, ?)""",
            (artifacts.SCHEMA_VERSION, NOW, NOW),
        )
        conn.execute(
            """INSERT INTO artifact
               (artifact_id, canonical_url, canonicalization_contract, host,
                artifact_kind, first_seen_at, last_seen_at, created_at, updated_at)
               VALUES (?, ?, 'test-contract', 'x.com', 'article', ?, ?, ?, ?)""",
            (artifact_id, url, NOW, NOW, NOW, NOW),
        )
        conn.execute(
            """INSERT INTO artifact_import_candidate
               (candidate_id, import_run_id, envelope_day, event_id,
                source_rank, day_candidate_count, source_kind, source_provider,
                source_external_id, source_snapshot_sha256, source_url,
                disclosure_external_id, disclosure_snapshot_sha256,
                disclosure_url, disclosure_published_at, observed_url,
                expanded_url, candidate_source, title_hint, relation, decision,
                reason_code, artifact_id, created_at)
               VALUES ('import-candidate', 'import', ?, ?, 4, 1, 'x_post',
                       'twitterapi_io', 'post-investment', 'source-sha',
                       'https://x.com/researcher/status/investment',
                       'post-investment', 'source-sha',
                       'https://x.com/researcher/status/investment', ?, ?, ?,
                       'x_article', 'Article', 'self_publishes', 'accepted',
                       'x_longform_article', ?, ?)""",
            (
                DAY,
                f"event-investment-{DAY}",
                NOW,
                url,
                url,
                artifact_id,
                NOW,
            ),
        )
        conn.execute(
            """INSERT INTO artifact_fetch_run
               (fetch_run_id, schema_version, fetch_policy, selection_policy,
                input_fingerprint, expected_count, success_count,
                failed_retryable_count, failed_terminal_count, started_at,
                completed_at, status)
               VALUES ('x-run', ?, ?, 'test-selection', 'fingerprint', 1, 1,
                       0, 0, ?, ?, 'complete')""",
            (artifacts.SCHEMA_VERSION, artifact_x_articles.FETCH_POLICY, NOW, NOW),
        )
        conn.execute(
            """INSERT INTO artifact_fetch
               (fetch_id, fetch_run_id, artifact_id, fetch_policy,
                requested_url, request_key, status, attempt_number, started_at,
                completed_at, final_url, content_type, raw_sha256,
                raw_snapshot_ref, text_sha256, text_snapshot_ref,
                text_char_count, text_truncated, declared_canonical_url)
               VALUES ('x-fetch', 'x-run', ?, ?, ?, 'request-key', 'success', 1,
                       ?, ?, ?, 'text/plain', ?, ?, ?, ?, 24, 0, ?)""",
            (
                artifact_id,
                artifact_x_articles.FETCH_POLICY,
                url,
                NOW,
                NOW,
                url,
                raw_sha256,
                str(raw_snapshot),
                text_sha256,
                str(text_snapshot),
                url,
            ),
        )
        conn.execute(
            """INSERT INTO artifact_x_article_fetch
               (fetch_id, artifact_id, provider, endpoint, request_post_id,
                canonical_article_id, canonical_article_url, request_made,
                estimated_provider_credits, provider_status, created_at)
               VALUES ('x-fetch', ?, 'twitterapi_io', '/twitter/article', '456',
                       '123', ?, 1, 100, 'success', ?)""",
            (artifact_id, url, NOW),
        )
    conn.close()
    return artifact_id


def test_report_is_deterministic_and_counts_every_stage(tmp_path):
    manifest, _payload = _manifest(tmp_path)

    first = reconciliation.evaluate_manifest(manifest)
    second = reconciliation.evaluate_manifest(manifest)

    assert first == second
    assert first["passed"] is True
    assert first["mode"] == "partial"
    assert first["expected_contracts"] == reconciliation.current_expected_contracts()
    assert first["totals"]["all"]["run_count"] == 2
    assert first["totals"]["all"]["counts"] == {
        "expected_candidates": 2,
        "candidates": 2,
        "pending": 0,
        "complete": 2,
        "rejected": 0,
        "failed": 0,
        "insights": 2,
        "editor_selected": 2,
        "base_publication": 2,
        "effective_publication": 2,
    }
    assert first["totals"]["all"]["telemetry_all_stages"]["attempts"] == 10
    assert first["totals"]["all"]["telemetry_all_stages"][
        "telemetry_missing_attempts"
    ] == 0
    assert first["totals"]["all"]["telemetry_all_stages"][
        "telemetry_surplus_attempts"
    ] == 0
    assert {row["audit"]["status"] for row in first["runs"]} == {"passed"}
    assert first["x_article_cohort"]["status"] == "not_bound"
    assert first["checks"]["x_article_cohort_requirement_satisfied"]


def test_cli_writes_report_and_exact_manifest_rejects_missing_or_duplicate_runs(
    tmp_path, capsys
):
    manifest, payload = _manifest(tmp_path)
    output = tmp_path / "report.json"

    assert cli.main(
        [
            "audience-insight-production-reconciliation",
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ]
    ) == 0
    assert json.loads(output.read_text())["passed"] is True
    assert json.loads(capsys.readouterr().out)["status"] == "ok"

    payload["runs"].pop()
    manifest.write_text(json.dumps(payload))
    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match="runs do not match expected_audience_days exactly",
    ):
        reconciliation.load_manifest(manifest)

    payload["runs"].append(dict(payload["runs"][0]))
    manifest.write_text(json.dumps(payload))
    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match="duplicate audience/day run",
    ):
        reconciliation.load_manifest(manifest)


def test_final_mode_requires_exact_days_and_bound_x_article_cohort(tmp_path):
    one_day_manifest, _payload = _manifest(tmp_path / "one-day", mode="final")
    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match="final mode requires exactly 2026-07-05 through 2026-07-13",
    ):
        reconciliation.load_manifest(one_day_manifest)

    final_manifest, _payload = _manifest(
        tmp_path / "final",
        mode="final",
        days=reconciliation.FINAL_DAYS,
    )
    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match="final mode requires a non-null exact X Article cohort",
    ):
        reconciliation.load_manifest(final_manifest)


def test_manifest_and_run_contracts_are_bound_to_current_code(tmp_path):
    manifest, payload = _manifest(tmp_path / "manifest-contract")
    payload["expected_contracts"]["investment"]["extraction"][
        "prompt_sha256"
    ] = "0" * 64
    manifest.write_text(json.dumps(payload))
    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match="does not match the current production contract",
    ):
        reconciliation.load_manifest(manifest)

    manifest, payload = _manifest(tmp_path / "run-contract")
    source = Path(payload["runs"][0]["source_run_db"])
    conn = sqlite3.connect(source)
    conn.execute("UPDATE run_meta SET prompt_version = 'stale-extraction'")
    conn.commit()
    conn.close()
    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match="extraction contract does not match manifest",
    ):
        reconciliation.evaluate_manifest(manifest)


def _duplicate_extraction_attempt(
    source: Path, *, attempt_number: int, expected_attempts: int
) -> None:
    conn = sqlite3.connect(source)
    candidate_id = str(
        conn.execute("SELECT candidate_id FROM candidate_item LIMIT 1").fetchone()[0]
    )
    conn.execute(
        "UPDATE candidate_item SET attempts = ? WHERE candidate_id = ?",
        (expected_attempts, candidate_id),
    )
    conn.execute(
        """INSERT INTO candidate_attempt
           (candidate_id, attempt_number, status, result_json, raw_output_text,
            error_type, error_message, response_id, response_model, input_tokens,
            cached_tokens, cache_write_tokens, output_tokens, reported_cost_usd,
            request_tags_json, created_at)
           SELECT candidate_id, ?, status, result_json, raw_output_text,
                  error_type, error_message, response_id, response_model,
                  input_tokens, cached_tokens, cache_write_tokens, output_tokens,
                  reported_cost_usd, request_tags_json, created_at
           FROM candidate_attempt
           WHERE candidate_id = ? AND attempt_number = 1""",
        (attempt_number, candidate_id),
    )
    conn.commit()
    conn.close()


def test_telemetry_rejects_missing_surplus_and_noncontiguous_attempts(tmp_path):
    missing_manifest, missing_payload = _manifest(tmp_path / "missing")
    missing_source = Path(missing_payload["runs"][0]["source_run_db"])
    conn = sqlite3.connect(missing_source)
    conn.execute("UPDATE candidate_item SET attempts = 2")
    conn.commit()
    conn.close()
    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match=r"expected=\[1, 2\], actual=\[1\]",
    ):
        reconciliation.evaluate_manifest(missing_manifest)

    surplus_manifest, surplus_payload = _manifest(tmp_path / "surplus")
    surplus_source = Path(surplus_payload["runs"][0]["source_run_db"])
    _duplicate_extraction_attempt(
        surplus_source, attempt_number=2, expected_attempts=1
    )
    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match=r"expected=\[1\], actual=\[1, 2\]",
    ):
        reconciliation.evaluate_manifest(surplus_manifest)

    gap_manifest, gap_payload = _manifest(tmp_path / "gap")
    gap_source = Path(gap_payload["runs"][0]["source_run_db"])
    _duplicate_extraction_attempt(gap_source, attempt_number=3, expected_attempts=2)
    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match=r"expected=\[1, 2\], actual=\[1, 3\]",
    ):
        reconciliation.evaluate_manifest(gap_manifest)


@pytest.mark.parametrize(
    "field",
    (
        "response_id",
        "response_model",
        "input_tokens",
        "cached_tokens",
        "output_tokens",
        "request_tags_json",
        "reported_cost_usd",
    ),
)
def test_telemetry_rejects_null_required_fields(tmp_path, field):
    manifest, payload = _manifest(tmp_path / field)
    source = Path(payload["runs"][0]["source_run_db"])
    conn = sqlite3.connect(source)
    conn.execute(f"UPDATE candidate_attempt SET {field} = NULL")
    conn.commit()
    conn.close()

    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match=rf"telemetry has null required fields.*{field}",
    ):
        reconciliation.evaluate_manifest(manifest)


def test_optional_cache_write_tokens_are_counted_without_coercion(tmp_path):
    manifest, payload = _manifest(tmp_path)
    source = Path(payload["runs"][0]["source_run_db"])
    conn = sqlite3.connect(source)
    conn.execute("UPDATE candidate_attempt SET cache_write_tokens = NULL")
    conn.commit()
    conn.close()

    report = reconciliation.evaluate_manifest(manifest)

    source_run = next(
        row for row in report["runs"] if row["source_run_db"] == str(source)
    )
    extraction = source_run["telemetry"]["extraction"]
    assert extraction["cache_write_tokens"] == 0
    assert extraction["cache_write_tokens_reported_records"] == 0
    assert extraction["cache_write_tokens_unreported_records"] == 1
    all_stages = report["totals"]["all"]["telemetry_all_stages"]
    assert all_stages["cache_write_tokens_reported_records"] == 9
    assert all_stages["cache_write_tokens_unreported_records"] == 1

def test_reconciliation_fails_closed_on_source_drift_or_omitted_finalization(
    tmp_path,
):
    manifest, payload = _manifest(tmp_path)
    source = Path(payload["runs"][0]["source_run_db"])
    conn = sqlite3.connect(source)
    conn.execute("UPDATE candidate_item SET claim = 'drifted claim'")
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="no longer matches source"):
        reconciliation.evaluate_manifest(manifest)

    manifest, payload = _manifest(tmp_path / "omitted")
    source = Path(payload["runs"][0]["source_run_db"])
    finalization = publication_audit.default_finalization_path(source)
    finalization.parent.mkdir(parents=True, exist_ok=True)
    finalization.write_text("{}\n")
    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match="manifest omitted existing finalization",
    ):
        reconciliation.evaluate_manifest(manifest)


def test_history_gate_and_telemetry_integrity_are_fail_closed(tmp_path):
    history_manifest, history_payload = _manifest(tmp_path / "history")
    history_source = Path(history_payload["runs"][0]["source_run_db"])
    conn = sqlite3.connect(history_source)
    conn.execute("UPDATE editor_run SET history_sha256 = 'wrong-history'")
    conn.commit()
    conn.close()
    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match="editor history does not match",
    ):
        reconciliation.evaluate_manifest(history_manifest)

    telemetry_manifest, telemetry_payload = _manifest(tmp_path / "telemetry")
    telemetry_source = Path(telemetry_payload["runs"][0]["source_run_db"])
    conn = sqlite3.connect(telemetry_source)
    conn.execute("UPDATE candidate_attempt SET reported_cost_usd = NULL")
    conn.commit()
    conn.close()
    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match="telemetry has null required fields.*reported_cost_usd",
    ):
        reconciliation.evaluate_manifest(telemetry_manifest)

    gate_manifest, gate_payload = _manifest(tmp_path / "gate")
    gate_source = Path(gate_payload["runs"][0]["source_run_db"])
    conn = sqlite3.connect(gate_source)
    result = json.loads(
        conn.execute(
            "SELECT result_json FROM quality_gate WHERE singleton = 1"
        ).fetchone()[0]
    )
    result["checks"]["all_quality_checks"] = False
    conn.execute(
        "UPDATE quality_gate SET result_json = ? WHERE singleton = 1",
        (json.dumps(result),),
    )
    conn.commit()
    conn.close()
    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match="internal quality gate result is incomplete or inconsistent",
    ):
        reconciliation.evaluate_manifest(gate_manifest)


def test_explicit_x_article_cohort_reports_terminal_state(tmp_path):
    artifact_db = tmp_path / "artifacts.db"
    artifact_id = _seed_terminal_x_article(artifact_db)
    manifest, _payload = _manifest(
        tmp_path,
        x_article_cohort={
            "artifact_db": str(artifact_db),
            "artifact_ids": [artifact_id],
        },
    )

    report = reconciliation.evaluate_manifest(manifest)

    assert report["passed"] is True
    cohort = report["x_article_cohort"]
    assert cohort["status"] == "validated"
    assert cohort["artifact_db"] == str(artifact_db.resolve())
    assert cohort["binding"]["source_event_count"] == 2
    assert cohort["binding"]["derived_artifact_count"] == 1
    assert cohort["artifact_count"] == cohort["terminal_count"] == 1
    assert cohort["terminal_complete"] is True
    assert cohort["status_counts"] == {"success": 1}
    assert cohort["provider_request_count"] == 1
    assert cohort["estimated_provider_credits"] == 100
    assert cohort["items"][0]["artifact_id"] == artifact_id
    assert cohort["items"][0]["status"] == "success"
    assert cohort["items"][0]["raw_sha256"]
    assert cohort["items"][0]["text_sha256"]
