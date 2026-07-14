import sqlite3

from fli import insight_triage_runs
from fli.web import triage


def _insert_meta(conn, *, run_id="run-1"):
    now = "2026-07-13T10:00:00+00:00"
    conn.execute(
        """INSERT INTO run_meta
           (singleton, run_id, day, model, reasoning_effort, prompt_version,
            prompt_sha256, schema_version, candidate_limit, cohort_sha256,
            expected_count, created_at, updated_at)
           VALUES (1, ?, '2026-07-11', 'gpt-5.4-mini', 'medium',
                   'prompt-v1', 'prompt-hash', 'schema-v1', 1, 'cohort-hash',
                   1, ?, ?)""",
        (run_id, now, now),
    )


def test_triage_payload_exposes_snapshot_and_reuse_provenance(
    tmp_path, monkeypatch
):
    root = tmp_path / "triage"
    conn = insight_triage_runs.connect_run(root / "run-1" / "triage.db")
    _insert_meta(conn)
    conn.execute(
        """INSERT INTO triage_item
           (event_id, current_rank, root_post_id, root_url, envelope_json,
            input_text, input_sha256, snapshot_content_sha256,
            prompt_cache_key, status, decision, reason,
            reused_from_run_id, reused_from_event_id, updated_at)
           VALUES ('event-1', 1, 'post-1', 'https://x.com/a/status/1', '{}',
                   'input', 'input-hash', 'snapshot-hash', 'cache-key',
                   'complete', 'keep', 'Concrete evidence.',
                   'prior-run', 'prior-event', '2026-07-13T10:00:00+00:00')"""
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(triage, "DEFAULT_TRIAGE_ROOT", root)
    triage._triage_payload_cached.cache_clear()

    payload = triage.triage_payload("2026-07-11")

    assert payload["items"]["event-1"] == {
        "decision": "keep",
        "reason": "Concrete evidence.",
        "input_sha256": "input-hash",
        "snapshot_content_sha256": "snapshot-hash",
        "reused_from_run_id": "prior-run",
        "reused_from_event_id": "prior-event",
    }


def test_triage_payload_treats_legacy_snapshot_hash_as_null(
    tmp_path, monkeypatch
):
    root = tmp_path / "triage"
    path = root / "legacy" / "triage.db"
    path.parent.mkdir(parents=True)
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE run_meta (
            singleton INTEGER PRIMARY KEY,
            run_id TEXT NOT NULL,
            day TEXT NOT NULL,
            model TEXT NOT NULL,
            reasoning_effort TEXT NOT NULL,
            prompt_version TEXT NOT NULL,
            prompt_sha256 TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            candidate_limit INTEGER NOT NULL,
            cohort_sha256 TEXT NOT NULL,
            expected_count INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        INSERT INTO run_meta VALUES (
            1, 'legacy', '2026-07-11', 'gpt-5.4-mini', 'medium',
            'prompt-v1', 'prompt-hash', 'schema-v1', 1, 'cohort-hash', 1,
            '2026-07-12T10:00:00+00:00', '2026-07-12T10:00:00+00:00'
        );
        CREATE TABLE triage_item (
            event_id TEXT PRIMARY KEY,
            input_sha256 TEXT NOT NULL,
            status TEXT NOT NULL,
            decision TEXT,
            reason TEXT
        );
        INSERT INTO triage_item VALUES (
            'legacy-event', 'legacy-input', 'complete', 'drop', 'Old decision.'
        );
        """
    )
    conn.close()
    monkeypatch.setattr(triage, "DEFAULT_TRIAGE_ROOT", root)
    triage._triage_payload_cached.cache_clear()

    payload = triage.triage_payload("2026-07-11")

    assert payload["available"] is True
    assert payload["items"]["legacy-event"]["snapshot_content_sha256"] is None
    assert payload["items"]["legacy-event"]["reused_from_run_id"] is None

