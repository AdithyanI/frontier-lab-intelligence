import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from fli import (
    artifact_x_articles,
    artifacts,
    audience_insight_evaluations,
    audience_insight_production_reconciliation as reconciliation,
    audience_insight_publication_audit as publication_audit,
    audience_insight_recall,
    audience_insight_runs,
    audience_insights,
    cli,
)
from fli.web import insights as insight_store


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
    run_id = f"production-{audience}-{day}-r1"
    event_id = f"event-{audience}-{day}"
    candidate_id = audience_insight_runs._candidate_id(day, audience, event_id)
    quote = f"Researcher reported a bounded result for {audience} on {day}."
    packet_payload = {
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
    packet = json.dumps(packet_payload, sort_keys=True, separators=(",", ":"))
    packet_object = audience_insight_runs._packet_from_payload(packet_payload)
    extraction_input = audience_insights.render_model_input(
        packet_object,
        version=audience_insights.INPUT_RENDER_PROVIDER_SAFE_V2,
    )
    extraction_input_sha = hashlib.sha256(extraction_input.encode()).hexdigest()
    extraction_cache_key = audience_insights.prompt_cache_key(audience, event_id)
    event_ids_json = json.dumps([event_id], separators=(",", ":"))
    cohort_sha256 = hashlib.sha256(
        json.dumps([packet_payload], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    conn = audience_insight_runs.connect_run(source)
    contracts = reconciliation.current_expected_contracts()[audience]
    extraction_tags = json.dumps(
        list(
            audience_insights.request_tags(
                audience=audience,
                job="insight-extraction",
                run=run_id,
                day=day,
                version=contracts["extraction"]["prompt_version"],
            )
        )
    )
    editor_tags = json.dumps(
        list(
            audience_insights.request_tags(
                audience=audience,
                job="daily-editor",
                run=run_id,
                day=day,
                version=contracts["editor"]["prompt_version"],
            )
        )
    )
    review_tags = json.dumps(
        list(
            audience_insight_evaluations.request_tags(
                audience=audience,
                run=run_id,
                day=day,
                prompt_version=contracts["item_review"]["prompt_version"],
            )
        )
    )
    day_tags = json.dumps(
        list(
            audience_insight_evaluations.request_tags(
                audience=audience,
                run=run_id,
                day=day,
                prompt_version=contracts["day_review"]["prompt_version"],
            )
        )
    )
    with conn:
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
               VALUES (1, ?, ?, ?, 'gpt-5.6-luna', 'medium', ?, 'extract-sha',
                       'provider-safe-v2',
                       'extract-schema', 'gpt-5.6-luna', 'high', ?, 'editor-sha',
                       'editor-schema', 'gpt-5.6-luna', 'high', 'review-v2',
                       'review-sha', 'review-schema', 'day-v2', 'day-sha',
                       'day-schema', 'triage.db', 'artifacts.db', 50, ?,
                       ?, 1, ?, ?)""",
            (
                run_id,
                audience,
                day,
                f"{audience}-insight-v2",
                f"{audience}-daily-editor-v2",
                event_ids_json,
                cohort_sha256,
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
               VALUES (?, ?, ?, 4, ?, ?, ?,
                       ?, 'complete', 1, 'insight', ?,
                       'third_party_observation', 'The result supports a bounded action.',
                       ?, ?, 1, 'x_post', ?, ?, '@researcher', 'source-sha', 0,
                       ?, 'resp-extract', 'gpt-5.6-luna', 1500, 1000, 0, 90,
                       0.01, '[]', '{}', ?, ?)""",
            (
                candidate_id,
                event_id,
                day,
                packet,
                extraction_input,
                extraction_input_sha,
                extraction_cache_key,
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
            "UPDATE candidate_item SET request_tags_json = ?",
            (extraction_tags,),
        )
        conn.execute(
            "UPDATE candidate_attempt SET request_tags_json = ?",
            (extraction_tags,),
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
                review_tags,
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
                editor_tags,
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
                day_tags,
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


def _write_canonical_web_pair(
    root: Path, source_manifest: Path
) -> tuple[Path, dict]:
    publication_dir = root / insight_store.PRODUCTION_RECONCILIATION_DIR
    publication_dir.mkdir(parents=True, exist_ok=True)
    manifest = publication_dir / insight_store.PRODUCTION_RECONCILIATION_MANIFEST
    manifest.write_text(source_manifest.read_text())
    report = reconciliation.evaluate_manifest(manifest)
    reconciliation.write_report(
        report,
        publication_dir / insight_store.PRODUCTION_RECONCILIATION_REPORT,
    )
    return manifest, report


def _refreeze_passing_audit(source: Path, audit_db: Path) -> None:
    audit = publication_audit.connect(audit_db)
    source_conn = sqlite3.connect(source)
    audience, day = source_conn.execute(
        "SELECT audience, day FROM run_meta WHERE singleton = 1"
    ).fetchone()
    source_conn.close()
    publication_audit.freeze_audit(
        audit,
        audit_id=f"publication-audit-{audience}-{day}",
        source_run_db=source,
        reject_sample_limit=0,
    )
    meta = audit.execute("SELECT * FROM audit_run WHERE singleton = 1").fetchone()
    for row in audit.execute(
        "SELECT * FROM audit_item ORDER BY audit_item_id"
    ).fetchall():
        publication_audit._store_success(
            audit,
            row,
            meta,
            _passing_audit_result(str(row["audit_item_id"]), meta),
        )
    audit.close()


def _make_two_item_audit_then_editorial_run(
    source: Path,
    audit_db: Path,
) -> tuple[str, str]:
    """Expand one fixture run, then freeze one audit fail and one survivor."""
    conn = audience_insight_runs.connect_run(source)
    first = conn.execute(
        "SELECT * FROM candidate_item ORDER BY feed_rank, event_id LIMIT 1"
    ).fetchone()
    assert first is not None
    first_id = str(first["candidate_id"])
    packet_payload = json.loads(str(first["packet_json"]))
    second_event = f"{first['event_id']}-second"
    packet_payload["event_id"] = second_event
    packet_payload["feed_rank"] = int(first["feed_rank"]) + 1
    packet_payload["sources"][0]["source_id"] += "-second"
    packet_payload["sources"][0]["url"] += "-second"
    packet = audience_insight_runs._packet_from_payload(packet_payload)
    canonical_packet = audience_insight_runs._packet_payload(packet)
    packet_text = reconciliation._canonical_json(canonical_packet)
    render_version = audience_insight_runs.declared_input_render_version(conn)
    model_input = audience_insights.render_model_input(
        packet,
        version=render_version,
    )
    audience = str(
        conn.execute(
            "SELECT audience FROM run_meta WHERE singleton = 1"
        ).fetchone()[0]
    )
    second_id = audience_insight_runs._candidate_id(
        str(first["day"]), audience, second_event
    )
    candidate = dict(first)
    candidate.update(
        {
            "candidate_id": second_id,
            "event_id": second_event,
            "feed_rank": int(first["feed_rank"]) + 1,
            "packet_json": packet_text,
            "input_text": model_input,
            "input_sha256": reconciliation._sha256(model_input),
            "prompt_cache_key": audience_insights.prompt_cache_key(
                audience, second_event
            ),
            "claim": "A second bounded result cleared extraction.",
            "supporting_quote": canonical_packet["sources"][0]["text"],
            "citation_source_id": canonical_packet["sources"][0]["source_id"],
            "citation_source_url": canonical_packet["sources"][0]["url"],
            "response_id": "resp-extract-second",
        }
    )
    candidate_columns = list(candidate)
    with conn:
        conn.execute(
            f"INSERT INTO candidate_item ({','.join(candidate_columns)}) "
            f"VALUES ({','.join('?' for _ in candidate_columns)})",
            tuple(candidate[column] for column in candidate_columns),
        )
        attempt = dict(
            conn.execute(
                "SELECT * FROM candidate_attempt WHERE candidate_id = ?",
                (first_id,),
            ).fetchone()
        )
        attempt.update(
            {"candidate_id": second_id, "response_id": "resp-extract-second"}
        )
        attempt_columns = list(attempt)
        conn.execute(
            f"INSERT INTO candidate_attempt ({','.join(attempt_columns)}) "
            f"VALUES ({','.join('?' for _ in attempt_columns)})",
            tuple(attempt[column] for column in attempt_columns),
        )
        review = dict(
            conn.execute(
                "SELECT * FROM item_review WHERE candidate_id = ?",
                (first_id,),
            ).fetchone()
        )
        review.update(
            {
                "candidate_id": second_id,
                "prompt_cache_key": "review-cache-second",
                "response_id": "resp-review-second",
            }
        )
        review_columns = list(review)
        conn.execute(
            f"INSERT INTO item_review ({','.join(review_columns)}) "
            f"VALUES ({','.join('?' for _ in review_columns)})",
            tuple(review[column] for column in review_columns),
        )
        conn.execute(
            "INSERT INTO daily_selection "
            "(editorial_rank, candidate_id, decision_value, audit_reason) "
            "VALUES (2, ?, 'experiment_or_benchmark', 'Second exact survivor.')",
            (second_id,),
        )
        conn.execute(
            "INSERT INTO publication_selection "
            "(publication_rank, original_editorial_rank, candidate_id, activated_at) "
            "VALUES (2, 2, ?, ?)",
            (second_id, NOW),
        )
        review_input = json.dumps(
            {
                "selected": [
                    {"candidate_id": first_id},
                    {"candidate_id": second_id},
                ]
            },
            sort_keys=True,
        )
        conn.execute(
            "UPDATE day_set_review SET input_text = ?, input_sha256 = ? "
            "WHERE singleton = 1",
            (review_input, reconciliation._sha256(review_input)),
        )
        conn.execute(
            "UPDATE editor_run SET selected_count = 2 WHERE singleton = 1"
        )
        gate = json.loads(
            str(
                conn.execute(
                    "SELECT result_json FROM quality_gate WHERE singleton = 1"
                ).fetchone()[0]
            )
        )
        gate["selected_count"] = 2
        conn.execute(
            "UPDATE quality_gate SET result_json = ? WHERE singleton = 1",
            (reconciliation._canonical_json(gate),),
        )
        packets = [
            json.loads(str(row[0]))
            for row in conn.execute(
                "SELECT packet_json FROM candidate_item ORDER BY feed_rank, event_id"
            ).fetchall()
        ]
        event_ids = [packet["event_id"] for packet in packets]
        conn.execute(
            "UPDATE run_meta SET expected_count = 2, event_ids_json = ?, "
            "cohort_sha256 = ? WHERE singleton = 1",
            (
                reconciliation._canonical_json(event_ids),
                reconciliation._sha256(reconciliation._canonical_json(packets)),
            ),
        )
    conn.close()

    shutil.rmtree(audit_db.parent)
    audit = publication_audit.connect(audit_db)
    publication_audit.freeze_audit(
        audit,
        audit_id="publication-audit-composed-finalization",
        source_run_db=source,
        reject_sample_limit=0,
    )
    meta = audit.execute("SELECT * FROM audit_run WHERE singleton = 1").fetchone()
    rows = audit.execute("SELECT * FROM audit_item ORDER BY audit_item_id").fetchall()
    for row in rows:
        result = _passing_audit_result(str(row["audit_item_id"]), meta)
        if str(row["source_candidate_id"]) == first_id:
            result.update(
                {
                    "actionability": "fail",
                    "specificity": "fail",
                    "failure_codes": ["generic_engineering_action"],
                    "rationale": "The first item fails the external publication audit.",
                }
            )
            result["raw_output_text"] = json.dumps(
                {
                    field: result[field]
                    for field in publication_audit.OUTPUT_FIELDS
                },
                sort_keys=True,
            )
        publication_audit._store_success(audit, row, meta, result)
    audit.close()
    return first_id, second_id


def _seed_terminal_x_article(
    path: Path,
    *,
    event_id: str | None = None,
    article_number: str = "123",
    request_post_id: str = "456",
) -> str:
    event_id = event_id or f"event-investment-{DAY}"
    url = f"https://x.com/i/article/{article_number}"
    artifact_id = hashlib.sha256(url.encode()).hexdigest()
    raw_snapshot = path.parent / f"article-{article_number}-raw.json"
    text_snapshot = path.parent / f"article-{article_number}-text.txt"
    contents = [{"type": "unstyled", "text": "Bounded X Article body."}]
    raw_payload = {
        "article": {"title": "Bounded article", "contents": contents},
        "status": "success",
        "message": "ok",
    }
    raw_snapshot.write_text(
        json.dumps(raw_payload, sort_keys=True, separators=(",", ":"))
    )
    text_snapshot.write_text("Bounded X Article body.\n")
    raw_sha256 = hashlib.sha256(raw_snapshot.read_bytes()).hexdigest()
    text_sha256 = hashlib.sha256(text_snapshot.read_bytes()).hexdigest()
    contents_json = json.dumps(contents, sort_keys=True, separators=(",", ":"))
    contents_sha256 = hashlib.sha256(contents_json.encode()).hexdigest()
    conn = artifacts.connect(path)
    with conn:
        conn.execute(
            """INSERT OR IGNORE INTO artifact_import_run
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
               VALUES (?, 'import', ?, ?, 4, 1, 'x_post',
                       'twitterapi_io', ?, 'source-sha',
                       'https://x.com/researcher/status/investment',
                       ?, 'source-sha',
                       'https://x.com/researcher/status/investment', ?, ?, ?,
                       'x_article', 'Article', 'self_publishes', 'accepted',
                       'x_longform_article', ?, ?)""",
            (
                f"import-candidate-{article_number}",
                DAY,
                event_id,
                request_post_id,
                request_post_id,
                NOW,
                url,
                url,
                artifact_id,
                NOW,
            ),
        )
        conn.execute(
            """INSERT OR IGNORE INTO artifact_fetch_run
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
                completed_at, final_url, http_status, content_type,
                content_length, raw_sha256, raw_snapshot_ref,
                extractor_contract, extractor_version, extracted_title,
                text_sha256, text_snapshot_ref, text_char_count,
                text_truncated, declared_canonical_url, retryable)
               VALUES (?, 'x-run', ?, ?, ?, ?, 'success', 1,
                       ?, ?, ?, 200, 'application/json', ?, ?, ?, ?, ?, ?, ?, ?,
                       24, 0, ?, 0)""",
            (
                f"x-fetch-{article_number}",
                artifact_id,
                artifact_x_articles.FETCH_POLICY,
                url,
                f"request-key-{article_number}",
                NOW,
                NOW,
                url,
                len(raw_snapshot.read_bytes()),
                raw_sha256,
                str(raw_snapshot),
                artifact_x_articles.EXTRACTOR_CONTRACT,
                artifact_x_articles.EXTRACTOR_VERSION,
                "Bounded article",
                text_sha256,
                str(text_snapshot),
                url,
            ),
        )
        conn.execute(
            """INSERT INTO artifact_x_article_fetch
                (fetch_id, artifact_id, provider, endpoint, request_post_id,
                canonical_article_id, canonical_article_url, request_made,
                estimated_provider_credits, provider_status, provider_message,
                response_fetched_at, content_block_count, content_blocks_json,
                content_blocks_sha256, created_at)
               VALUES (?, ?, 'twitterapi_io', ?, ?,
                       ?, ?, 1, 100, 'success', 'ok', ?, 1, ?, ?, ?)""",
            (
                f"x-fetch-{article_number}",
                artifact_id,
                artifact_x_articles.ENDPOINT,
                request_post_id,
                article_number,
                url,
                NOW,
                contents_json,
                contents_sha256,
                NOW,
            ),
        )
    conn.close()
    return artifact_id


def _seed_frozen_recall_origin(
    path: Path,
    *,
    artifact_db: Path,
    event_id: str,
    artifact_id: str,
    day: str = DAY,
    feed_rank: int = 83,
) -> tuple[str, str]:
    sample_id = audience_insight_recall._sample_id(day, event_id)
    band = audience_insight_recall.X_ARTICLE_51_100
    packet = {
        "event_id": event_id,
        "day": day,
        "feed_rank": feed_rank,
        "sources": [],
    }
    conn = audience_insight_recall.connect(path)
    with conn:
        conn.execute(
            """INSERT INTO recall_run
               (singleton, run_id, protocol_version, days_json,
                source_triage_dbs_json, source_artifact_db, extraction_model,
                extraction_reasoning_effort, review_model,
                review_reasoning_effort, contract_sha256, sample_set_sha256,
                expected_sample_count, expected_evaluation_count,
                created_at, updated_at)
               VALUES (1, 'frozen-recall-proof', ?, ?, '{}', ?,
                       'gpt-5.6-luna', 'medium', 'gpt-5.6-luna', 'high',
                       ?, ?, 1, 2, ?, ?)""",
            (
                audience_insight_recall.PROTOCOL_VERSION,
                json.dumps([day], separators=(",", ":")),
                str(artifact_db.resolve()),
                "a" * 64,
                "b" * 64,
                NOW,
                NOW,
            ),
        )
        conn.execute(
            """INSERT INTO recall_sample
               (sample_id, selection_order, day, event_id, band, sample_kind,
                triage_decision, feed_rank, selection_sha256,
                article_artifact_ids_json, packet_json, evidence_sha256,
                extraction_input_text, extraction_input_sha256, created_at)
               VALUES (?, 1, ?, ?, ?, 'x_article_census', 'keep', ?, ?, ?, ?,
                       ?, 'rank-blind input', ?, ?)""",
            (
                sample_id,
                day,
                event_id,
                band,
                feed_rank,
                audience_insight_recall.selection_sha256(
                    day=day, band=band, event_id=event_id
                ),
                json.dumps([artifact_id], separators=(",", ":")),
                json.dumps(packet, sort_keys=True, separators=(",", ":")),
                "c" * 64,
                "d" * 64,
                NOW,
            ),
        )
    conn.close()
    return sample_id, reconciliation.frozen_recall_origin_binding_sha256(path)


def test_report_is_deterministic_and_counts_every_stage(tmp_path):
    manifest, _payload = _manifest(tmp_path)

    first = reconciliation.evaluate_manifest(manifest)
    second = reconciliation.evaluate_manifest(manifest)

    assert first == second
    assert first["passed"] is True
    assert first["mode"] == "partial"
    assert first["expected_contracts"] == reconciliation.current_expected_contracts()
    assert first["expected_contracts"]["investment"]["extraction"][
        "reasoning_effort"
    ] == "high"
    assert first["expected_contracts"]["ai_engineering"]["extraction"][
        "reasoning_effort"
    ] == "medium"
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


def test_reconciliation_accepts_exact_editorial_disqualification(tmp_path):
    manifest, payload = _manifest(tmp_path, days=(DAY, "2026-07-12"))
    for audience in ("investment", "ai_engineering"):
        first_entry = next(
            row
            for row in payload["runs"]
            if row["audience"] == audience and row["day"] == DAY
        )
        next_entry = next(
            row
            for row in payload["runs"]
            if row["audience"] == audience and row["day"] == "2026-07-12"
        )
        first_source = Path(first_entry["source_run_db"])
        first_conn = reconciliation._open_readonly(first_source)
        first_ids = [
            str(row[0])
            for row in first_conn.execute(
                "SELECT candidate_id FROM publication_selection "
                "ORDER BY publication_rank"
            ).fetchall()
        ]
        history = audience_insight_runs.selected_history_row(
            first_conn, candidate_ids=first_ids
        )
        first_conn.close()
        history_json = reconciliation._canonical_json(history)
        next_conn = sqlite3.connect(next_entry["source_run_db"])
        next_conn.execute(
            "UPDATE editor_run SET prior_selected_json = ?, history_sha256 = ? "
            "WHERE singleton = 1",
            (history_json, reconciliation._sha256(history_json)),
        )
        next_conn.commit()
        next_conn.close()
    entry = payload["runs"][0]
    source = Path(entry["source_run_db"])
    audit = Path(entry["audit_db"])
    conn = sqlite3.connect(source)
    candidate_id = str(
        conn.execute(
            "SELECT candidate_id FROM publication_selection "
            "ORDER BY publication_rank LIMIT 1"
        ).fetchone()[0]
    )
    conn.close()
    publication_audit.create_editorial_publication_finalization(
        source_run_db=source,
        audit_db=audit,
        editorial_review={
            "schema_version": publication_audit.EDITORIAL_REVIEW_SCHEMA_VERSION,
            "review_id": "senior-product-review-2026-07-15",
            "reviewer": "product-owner",
            "removals": [
                {
                    "candidate_id": candidate_id,
                    "reason_code": "insufficient_decision_value",
                    "rationale": (
                        "The exact item passes factual audit but does not materially "
                        "sharpen an audience decision."
                    ),
                }
            ],
        },
    )
    entry["finalization_path"] = str(
        publication_audit.default_finalization_path(source)
    )
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    report = reconciliation.evaluate_manifest(manifest)

    assert report["passed"] is True
    assert report["totals"]["all"]["counts"]["base_publication"] == 4
    assert report["totals"]["all"]["counts"]["effective_publication"] == 3
    finalized = next(
        row for row in report["runs"] if row["source_run_db"] == str(source)
    )
    assert finalized["audit"]["passed"] is True
    assert finalized["audit"]["status"] == "passed_selected_editorial_finalized"
    assert finalized["finalization"]["reason_code"] == (
        publication_audit.EDITORIAL_FINALIZATION_REASON_CODE
    )
    assert finalized["finalization"]["removed_candidate_ids"] == [candidate_id]
    next_investment = next(
        row
        for row in report["runs"]
        if row["audience"] == "investment" and row["day"] == "2026-07-12"
    )
    assert next_investment["history"]["prior_item_count"] == 1


def test_reconciliation_binds_composed_audit_and_editorial_finalizations(tmp_path):
    manifest, payload = _manifest(tmp_path)
    entry = payload["runs"][0]
    source = Path(entry["source_run_db"])
    audit = Path(entry["audit_db"])
    audit_failed_id, editorial_id = _make_two_item_audit_then_editorial_run(
        source, audit
    )
    entry["expected_selected_count"] = 2

    publication_audit.create_publication_finalization(
        source_run_db=source,
        audit_db=audit,
    )
    prerequisite = publication_audit.default_finalization_path(source)
    prerequisite_sha = reconciliation._file_sha256(prerequisite)
    publication_audit.create_editorial_publication_finalization(
        source_run_db=source,
        audit_db=audit,
        editorial_review={
            "schema_version": publication_audit.EDITORIAL_REVIEW_SCHEMA_VERSION,
            "review_id": "senior-product-review-composed",
            "reviewer": "product-owner",
            "removals": [
                {
                    "candidate_id": editorial_id,
                    "reason_code": "insufficient_decision_value",
                    "rationale": "The audit survivor does not sharpen a decision.",
                }
            ],
        },
    )
    terminal = publication_audit.default_editorial_finalization_path(source)
    entry["finalization_path"] = str(terminal)
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    report = reconciliation.evaluate_manifest(manifest)

    assert report["passed"] is True
    finalized = next(
        row for row in report["runs"] if row["source_run_db"] == str(source)
    )
    assert finalized["audit"]["passed"] is False
    assert finalized["audit"]["status"] == (
        "failed_selected_audit_and_editorial_finalized"
    )
    assert finalized["selection"]["base_ids"] == [audit_failed_id, editorial_id]
    assert finalized["selection"]["post_audit_ids"] == [editorial_id]
    assert finalized["selection"]["effective_ids"] == []
    assert finalized["selection"]["history_ids"] == [editorial_id]
    assert finalized["finalization"]["path"] == str(terminal)
    assert finalized["finalization"]["sha256"] == reconciliation._file_sha256(
        terminal
    )
    assert finalized["finalization"]["prerequisite"] == {
        "path": str(prerequisite),
        "reason_code": publication_audit.FINALIZATION_REASON_CODE,
        "sha256": prerequisite_sha,
        "effective_selected_ids": [editorial_id],
    }

    prerequisite.write_text(prerequisite.read_text() + " ")
    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match="finalization validation failed",
    ):
        reconciliation.evaluate_manifest(manifest)


def test_write_report_atomically_replaces_existing_bytes(tmp_path, monkeypatch):
    output = tmp_path / "report.json"
    output.write_text("stale report\n")
    report = {"passed": True, "runs": []}
    replacements = []
    real_replace = reconciliation.os.replace

    def observed_replace(source, destination):
        source_path = Path(source)
        destination_path = Path(destination)
        assert source_path.parent == output.parent
        assert source_path.read_text() == reconciliation.canonical_report_text(report)
        assert destination_path.read_text() == "stale report\n"
        replacements.append((source_path, destination_path))
        real_replace(source, destination)

    monkeypatch.setattr(reconciliation.os, "replace", observed_replace)
    reconciliation.write_report(report, output)

    assert output.read_text() == reconciliation.canonical_report_text(report)
    assert len(replacements) == 1
    assert list(tmp_path.glob(".report.json.*.tmp")) == []


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


@pytest.mark.parametrize(
    ("sql", "message"),
    (
        (
            "UPDATE candidate_item SET input_text = input_text || ' drift'",
            "frozen model input drift",
        ),
        (
            "UPDATE candidate_item SET input_sha256 = 'wrong'",
            "frozen model input drift",
        ),
        (
            "UPDATE candidate_item SET prompt_cache_key = 'wrong'",
            "extraction cache key drift",
        ),
        (
            "UPDATE run_meta SET cohort_sha256 = 'wrong'",
            "frozen cohort binding drift",
        ),
    ),
)
def test_frozen_cohort_reconstruction_fails_closed(tmp_path, sql, message):
    manifest, payload = _manifest(tmp_path)
    source = Path(payload["runs"][0]["source_run_db"])
    conn = sqlite3.connect(source)
    conn.execute(sql)
    conn.commit()
    conn.close()

    with pytest.raises(reconciliation.ProductionReconciliationError, match=message):
        reconciliation.evaluate_manifest(manifest)


def test_request_tags_must_match_the_exact_stage_contract(tmp_path):
    manifest, payload = _manifest(tmp_path)
    source = Path(payload["runs"][0]["source_run_db"])
    conn = sqlite3.connect(source)
    conn.execute(
        "UPDATE candidate_attempt SET request_tags_json = ?",
        (json.dumps(["app:frontier-lab-intelligence", "job:wrong"]),),
    )
    conn.commit()
    conn.close()

    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match="extraction request tags do not match the frozen contract",
    ):
        reconciliation.evaluate_manifest(manifest)


def _seed_reconciled_day_telemetry(
    source: Path, *, run_suffix: str = ":padding-tail-trim"
) -> None:
    conn = sqlite3.connect(source)
    conn.row_factory = sqlite3.Row
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    tags = json.dumps(
        list(
            audience_insight_evaluations.request_tags(
                audience=str(meta["audience"]),
                run=f"{meta['run_id']}{run_suffix}",
                day=str(meta["day"]),
                prompt_version=str(meta["day_review_prompt_version"]),
            )
        )
    )
    with conn:
        conn.execute(
            """INSERT INTO reconciled_day_set_review
               (singleton, status, attempts, reconciliation_reason,
                source_review_input_sha256, input_text, input_sha256,
                prompt_cache_key, duplicate_pairs_json, padding_detected,
                thin_day_honest, set_rationale, response_id, response_model,
                input_tokens, cached_tokens, cache_write_tokens, output_tokens,
                reported_cost_usd, request_tags_json, raw_output_text,
                completed_at, updated_at)
               VALUES (1, 'complete', 1, 'padding_tail_trim', 'source-sha',
                       'reconciled input', 'reconciled-input-sha',
                       'padding-tail-trim-cache', '[]', 0, 1,
                       'The trimmed set is coherent.', 'resp-reconciled-day',
                       'gpt-5.6-luna', 1200, 700, 0, 70, 0.004, ?, '{}', ?, ?)""",
            (tags, NOW, NOW),
        )
    conn.close()


def test_reconciled_day_accepts_only_runner_owned_padding_tail_tags(tmp_path):
    source, _audit = _complete_run(
        tmp_path / "valid", audience="investment"
    )
    _seed_reconciled_day_telemetry(source)
    conn = reconciliation._open_readonly(source)
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()

    telemetry = reconciliation._source_telemetry(
        conn, meta, source_path=source
    )

    assert telemetry["day"]["attempts"] == 2
    assert telemetry["day"]["recorded_attempts"] == 2
    conn.close()

    for name, suffix in (
        ("base-run", ""),
        ("arbitrary-suffix", ":padding-tail-trim-extra"),
    ):
        invalid_source, _audit = _complete_run(
            tmp_path / name, audience="investment"
        )
        _seed_reconciled_day_telemetry(invalid_source, run_suffix=suffix)
        invalid = reconciliation._open_readonly(invalid_source)
        invalid_meta = invalid.execute(
            "SELECT * FROM run_meta WHERE singleton = 1"
        ).fetchone()
        with pytest.raises(
            reconciliation.ProductionReconciliationError,
            match="reconciled day request tags do not match the frozen contract",
        ):
            reconciliation._source_telemetry(
                invalid, invalid_meta, source_path=invalid_source
            )
        invalid.close()


def test_initial_day_rejects_padding_tail_run_tags(tmp_path):
    source, _audit = _complete_run(tmp_path, audience="investment")
    conn = sqlite3.connect(source)
    conn.row_factory = sqlite3.Row
    meta = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    tags = audience_insight_evaluations.request_tags(
        audience=str(meta["audience"]),
        run=f"{meta['run_id']}:padding-tail-trim",
        day=str(meta["day"]),
        prompt_version=str(meta["day_review_prompt_version"]),
    )
    conn.execute(
        "UPDATE day_set_review SET request_tags_json = ?",
        (json.dumps(list(tags)),),
    )
    conn.commit()
    conn.close()
    readonly = reconciliation._open_readonly(source)
    readonly_meta = readonly.execute(
        "SELECT * FROM run_meta WHERE singleton = 1"
    ).fetchone()
    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match="day request tags do not match the frozen contract",
    ):
        reconciliation._source_telemetry(
            readonly, readonly_meta, source_path=source
        )
    readonly.close()


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


def test_proxy_reported_zero_cost_is_valid_but_unknown_cost_requires_supersession(
    tmp_path,
):
    zero_manifest, zero_payload = _manifest(tmp_path / "reported-zero")
    zero_source = Path(zero_payload["runs"][0]["source_run_db"])
    conn = sqlite3.connect(zero_source)
    conn.execute("UPDATE candidate_attempt SET reported_cost_usd = 0.0")
    conn.commit()
    conn.close()

    report = reconciliation.evaluate_manifest(zero_manifest)

    zero_run = next(
        row for row in report["runs"] if row["source_run_db"] == str(zero_source)
    )
    assert zero_run["telemetry"]["extraction"]["proxy_reported_cost_usd"] == 0.0
    assert zero_run["telemetry"]["extraction"]["proxy_cost_records"] == 1

    unknown_manifest, unknown_payload = _manifest(tmp_path / "unknown")
    unknown_source = Path(unknown_payload["runs"][0]["source_run_db"])
    conn = sqlite3.connect(unknown_source)
    conn.execute("UPDATE candidate_attempt SET reported_cost_usd = NULL")
    conn.commit()
    conn.close()
    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match=(
            "missing proxy-reported cost.*unknown cost cannot be coerced to zero.*"
            "must be superseded"
        ),
    ):
        reconciliation.evaluate_manifest(unknown_manifest)


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
        match="missing proxy-reported cost",
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
            "frozen_recall_origin": None,
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


def test_x_article_cohort_binds_exact_run_and_frozen_recall_origin_union(tmp_path):
    artifact_db = tmp_path / "artifacts.db"
    run_artifact_id = _seed_terminal_x_article(artifact_db)
    recall_event_id = "recall-extra-event"
    recall_artifact_id = _seed_terminal_x_article(
        artifact_db,
        event_id=recall_event_id,
        article_number="789",
        request_post_id="987",
    )
    recall_db = tmp_path / "recall.db"
    sample_id, binding_sha256 = _seed_frozen_recall_origin(
        recall_db,
        artifact_db=artifact_db,
        event_id=recall_event_id,
        artifact_id=recall_artifact_id,
    )
    manifest, _payload = _manifest(
        tmp_path,
        x_article_cohort={
            "artifact_db": str(artifact_db),
            "artifact_ids": [run_artifact_id, recall_artifact_id],
            "frozen_recall_origin": {
                "recall_db": str(recall_db),
                "binding_sha256": binding_sha256,
                "sample_ids": [sample_id],
            },
        },
    )

    report = reconciliation.evaluate_manifest(manifest)

    binding = report["x_article_cohort"]["binding"]
    assert binding["derived_artifact_count"] == 1
    assert binding["frozen_recall_artifact_count"] == 1
    assert binding["frozen_recall_origin"]["sample_count"] == 1
    assert binding["frozen_recall_origin"]["items"][0]["sample_id"] == sample_id
    assert {
        item["artifact_id"]: item["origin"]
        for item in report["x_article_cohort"]["items"]
    } == {
        run_artifact_id: "production_run_event",
        recall_artifact_id: "frozen_recall_x_article_census",
    }


def test_frozen_recall_x_article_origin_rejects_drift_and_broad_supersets(tmp_path):
    artifact_db = tmp_path / "artifacts.db"
    run_artifact_id = _seed_terminal_x_article(artifact_db)
    recall_event_id = "recall-extra-event"
    recall_artifact_id = _seed_terminal_x_article(
        artifact_db,
        event_id=recall_event_id,
        article_number="789",
        request_post_id="987",
    )
    recall_db = tmp_path / "recall.db"
    sample_id, binding_sha256 = _seed_frozen_recall_origin(
        recall_db,
        artifact_db=artifact_db,
        event_id=recall_event_id,
        artifact_id=recall_artifact_id,
    )
    manifest, payload = _manifest(
        tmp_path,
        x_article_cohort={
            "artifact_db": str(artifact_db),
            "artifact_ids": [run_artifact_id, recall_artifact_id],
            "frozen_recall_origin": {
                "recall_db": str(recall_db),
                "binding_sha256": binding_sha256,
                "sample_ids": [sample_id],
            },
        },
    )

    payload["x_article_cohort"]["artifact_ids"].append("0" * 64)
    manifest.write_text(json.dumps(payload))
    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match="does not match the exact origin union.*extra=",
    ):
        reconciliation.evaluate_manifest(manifest)

    payload["x_article_cohort"]["artifact_ids"].pop()
    conn = sqlite3.connect(recall_db)
    conn.execute(
        "UPDATE recall_sample SET feed_rank = feed_rank + 1 WHERE sample_id = ?",
        (sample_id,),
    )
    conn.commit()
    conn.close()
    manifest.write_text(json.dumps(payload))
    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match="frozen recall origin binding does not match the manifest",
    ):
        reconciliation.evaluate_manifest(manifest)


def test_frozen_recall_origin_cannot_relabel_an_arbitrary_sample(tmp_path):
    artifact_db = tmp_path / "artifacts.db"
    run_artifact_id = _seed_terminal_x_article(artifact_db)
    recall_event_id = "recall-extra-event"
    recall_artifact_id = _seed_terminal_x_article(
        artifact_db,
        event_id=recall_event_id,
        article_number="789",
        request_post_id="987",
    )
    recall_db = tmp_path / "recall.db"
    sample_id, _binding_sha256 = _seed_frozen_recall_origin(
        recall_db,
        artifact_db=artifact_db,
        event_id=recall_event_id,
        artifact_id=recall_artifact_id,
    )
    conn = sqlite3.connect(recall_db)
    conn.execute(
        "UPDATE recall_sample SET sample_kind = 'lower_kept' WHERE sample_id = ?",
        (sample_id,),
    )
    conn.commit()
    conn.close()
    manifest, _payload = _manifest(
        tmp_path,
        x_article_cohort={
            "artifact_db": str(artifact_db),
            "artifact_ids": [run_artifact_id, recall_artifact_id],
            "frozen_recall_origin": {
                "recall_db": str(recall_db),
                "binding_sha256": (
                    reconciliation.frozen_recall_origin_binding_sha256(recall_db)
                ),
                "sample_ids": [sample_id],
            },
        },
    )

    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match="is not an accepted X Article census sample",
    ):
        reconciliation.evaluate_manifest(manifest)


def test_x_article_provider_mapping_drift_fails_closed(tmp_path):
    artifact_db = tmp_path / "artifacts.db"
    artifact_id = _seed_terminal_x_article(artifact_db)
    manifest, _payload = _manifest(
        tmp_path,
        x_article_cohort={
            "artifact_db": str(artifact_db),
            "artifact_ids": [artifact_id],
            "frozen_recall_origin": None,
        },
    )
    conn = sqlite3.connect(artifact_db)
    conn.execute(
        "UPDATE artifact_x_article_fetch SET request_post_id = '999'"
    )
    conn.commit()
    conn.close()

    with pytest.raises(
        reconciliation.ProductionReconciliationError,
        match="X Article provider provenance is invalid.*request_post_id",
    ):
        reconciliation.evaluate_manifest(manifest)


def test_default_web_rejects_same_identity_source_and_audit_replacement(
    tmp_path, monkeypatch
):
    source_manifest, payload = _manifest(tmp_path)
    canonical_manifest, stored_report = _write_canonical_web_pair(
        tmp_path, source_manifest
    )
    monkeypatch.setattr(insight_store, "DEFAULT_INSIGHTS_ROOT", tmp_path)
    assert insight_store.insight_dates_payload(audience="investment")[
        "available"
    ]

    entry = next(
        row for row in payload["runs"] if row["audience"] == "investment"
    )
    source = Path(entry["source_run_db"])
    audit_db = Path(entry["audit_db"])
    shutil.rmtree(source.parent)
    replacement_source, replacement_audit = _complete_run(
        tmp_path / "runs", audience="investment", day=DAY
    )
    assert replacement_source == source
    assert replacement_audit == audit_db

    shutil.rmtree(replacement_audit.parent)
    conn = sqlite3.connect(replacement_source)
    conn.execute(
        "UPDATE candidate_item SET claim = ?",
        ("A different same-identity experimental claim.",),
    )
    conn.commit()
    conn.close()
    _refreeze_passing_audit(replacement_source, replacement_audit)

    replacement_report = reconciliation.evaluate_manifest(canonical_manifest)
    assert replacement_report["passed"] is True
    assert replacement_report != stored_report
    assert insight_store.insight_dates_payload(audience="investment") == {
        "available": False,
        "reason": "No completed investment insight days exist yet.",
        "audience": "investment",
        "latest_date": None,
        "dates": [],
    }


def test_default_web_rejects_bound_x_article_snapshot_drift(
    tmp_path, monkeypatch
):
    artifact_db = tmp_path / "artifacts.db"
    artifact_id = _seed_terminal_x_article(artifact_db)
    source_manifest, _payload = _manifest(
        tmp_path,
        x_article_cohort={
            "artifact_db": str(artifact_db),
            "artifact_ids": [artifact_id],
            "frozen_recall_origin": None,
        },
    )
    _write_canonical_web_pair(tmp_path, source_manifest)
    monkeypatch.setattr(insight_store, "DEFAULT_INSIGHTS_ROOT", tmp_path)
    assert insight_store.insight_dates_payload(audience="investment")[
        "available"
    ]

    conn = sqlite3.connect(artifact_db)
    text_snapshot = Path(
        conn.execute(
            "SELECT text_snapshot_ref FROM artifact_fetch WHERE artifact_id = ?",
            (artifact_id,),
        ).fetchone()[0]
    )
    conn.close()
    text_snapshot.write_text("Tampered X Article body.\n")

    assert insight_store.insight_dates_payload(audience="investment") == {
        "available": False,
        "reason": "No completed investment insight days exist yet.",
        "audience": "investment",
        "latest_date": None,
        "dates": [],
    }
