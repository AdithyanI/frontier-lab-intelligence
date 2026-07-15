import hashlib
import json
import sqlite3

import pytest

from fli import artifact_urls, artifacts, audience_insight_runs


EVENT_ID = "event-reviewed"
ARTIFACT_URL = "https://www.sec.gov/Archives/edgar/data/1/filing.htm"


def _triage_db(path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """CREATE TABLE run_meta (
               singleton INTEGER PRIMARY KEY,
               run_id TEXT NOT NULL,
               day TEXT NOT NULL,
               expected_count INTEGER NOT NULL
           );
           CREATE TABLE triage_item (
               event_id TEXT PRIMARY KEY,
               current_rank INTEGER NOT NULL,
               input_sha256 TEXT NOT NULL,
               snapshot_content_sha256 TEXT,
               status TEXT NOT NULL,
               decision TEXT NOT NULL
           );"""
    )
    conn.execute(
        "INSERT INTO run_meta VALUES (1, 'triage-reviewed', '2026-07-06', 863)"
    )
    conn.execute(
        """INSERT INTO triage_item VALUES
           (?, 50, 'input-sha', 'snapshot-sha', 'complete', 'keep')""",
        (EVENT_ID,),
    )
    conn.commit()
    conn.close()


def _manifest(path, *, rationale="Official filing directly confirms the event."):
    payload = {
        "schema_version": artifacts.REVIEWED_SUPPLEMENT_CONTRACT,
        "reviewed_by": "human-review",
        "reviewed_at": "2026-07-15T08:00:00+00:00",
        "items": [
            {
                "event_id": EVENT_ID,
                "artifact_url": ARTIFACT_URL,
                "evidence_role": "official_primary_source",
                "source_published_at": "2026-07-06",
                "rationale": rationale,
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def test_reviewed_supplement_import_is_frozen_and_replayable(tmp_path):
    triage_db = tmp_path / "triage.db"
    artifact_db = tmp_path / "artifacts.db"
    manifest = tmp_path / "supplements.json"
    _triage_db(triage_db)
    payload = _manifest(manifest)

    first = artifacts.import_reviewed_supplements(
        manifest_path=manifest, triage_db=triage_db, db_path=artifact_db
    )
    second = artifacts.import_reviewed_supplements(
        manifest_path=manifest, triage_db=triage_db, db_path=artifact_db
    )

    artifact_id = artifact_urls.artifact_id(ARTIFACT_URL)
    assert first["artifact_ids"] == [artifact_id]
    assert first["imported_count"] == 1
    assert first["reused_count"] == 0
    assert second["imported_count"] == 0
    assert second["reused_count"] == 1
    assert first["manifest_sha256"] == hashlib.sha256(
        artifacts._canonical_json(payload).encode()
    ).hexdigest()

    conn = artifacts.connect(artifact_db)
    row = conn.execute("SELECT * FROM artifact_event_supplement").fetchone()
    assert row["event_id"] == EVENT_ID
    assert row["source_rank"] == 50
    assert row["day_candidate_count"] == 863
    assert row["source_triage_run_id"] == "triage-reviewed"
    assert row["source_input_sha256"] == "input-sha"
    assert row["source_snapshot_content_sha256"] == "snapshot-sha"
    assert row["evidence_role"] == "official_primary_source"
    assert row["reviewed_by"] == "human-review"
    assert conn.execute("SELECT COUNT(*) FROM artifact_import_candidate").fetchone()[0] == 0
    conn.close()


def test_reviewed_supplement_rejects_changed_assertion_for_same_frozen_event(
    tmp_path,
):
    triage_db = tmp_path / "triage.db"
    artifact_db = tmp_path / "artifacts.db"
    manifest = tmp_path / "supplements.json"
    _triage_db(triage_db)
    _manifest(manifest)
    artifacts.import_reviewed_supplements(
        manifest_path=manifest, triage_db=triage_db, db_path=artifact_db
    )
    _manifest(manifest, rationale="A materially changed rationale.")

    with pytest.raises(ValueError, match="conflicts with an existing frozen association"):
        artifacts.import_reviewed_supplements(
            manifest_path=manifest, triage_db=triage_db, db_path=artifact_db
        )


def test_reviewed_supplement_cli_returns_machine_contract(tmp_path, capsys):
    triage_db = tmp_path / "triage.db"
    artifact_db = tmp_path / "artifacts.db"
    manifest = tmp_path / "supplements.json"
    _triage_db(triage_db)
    _manifest(manifest)

    exit_code = artifacts.main(
        [
            "import-reviewed-supplements",
            "--db",
            str(artifact_db),
            "--triage-db",
            str(triage_db),
            "--manifest",
            str(manifest),
            "--json",
            "--no-input",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["command"] == "artifacts.import-reviewed-supplements"
    assert payload["status"] == "ok"
    assert payload["error"] is None
    assert payload["data"]["imported_count"] == 1


def test_reviewed_supplement_text_strengthens_only_its_exact_event(tmp_path):
    triage_db = tmp_path / "triage.db"
    artifact_db = tmp_path / "artifacts.db"
    manifest = tmp_path / "supplements.json"
    snapshot = tmp_path / "official.txt"
    snapshot.write_text(
        "TeraWulf entered a 20-year Anthropic lease for approximately 401 MW.\n",
        encoding="utf-8",
    )
    _triage_db(triage_db)
    _manifest(manifest)
    result = artifacts.import_reviewed_supplements(
        manifest_path=manifest, triage_db=triage_db, db_path=artifact_db
    )
    artifact_id = result["artifact_ids"][0]
    now = "2026-07-15T08:01:00+00:00"
    conn = artifacts.connect(artifact_db)
    with conn:
        conn.execute(
            """INSERT INTO artifact_fetch_run
               (fetch_run_id, schema_version, fetch_policy, selection_policy,
                input_fingerprint, expected_count, success_count,
                failed_retryable_count, failed_terminal_count, started_at,
                completed_at, status)
               VALUES ('fetch', ?, 'test', 'exact', 'fingerprint', 1, 1, 0, 0,
                       ?, ?, 'complete')""",
            (artifacts.SCHEMA_VERSION, now, now),
        )
        conn.execute(
            """INSERT INTO artifact_fetch
               (fetch_id, fetch_run_id, artifact_id, fetch_policy,
                requested_url, request_key, status, attempt_number, started_at,
                completed_at, text_sha256, text_snapshot_ref, text_char_count,
                text_truncated, retryable)
               VALUES ('fetch-item', 'fetch', ?, 'test', ?, 'request', 'success',
                       1, ?, ?, 'text-sha', ?, 72, 0, 0)""",
            (artifact_id, ARTIFACT_URL, now, now, str(snapshot)),
        )

    sources = audience_insight_runs._artifact_sources(
        conn,
        event_id=EVENT_ID,
        primary_post_ids={"root-post"},
        include_reviewed_supplements=True,
    )
    unrelated = audience_insight_runs._artifact_sources(
        conn,
        event_id="other-event",
        primary_post_ids={"root-post"},
        include_reviewed_supplements=True,
    )
    conn.close()

    assert len(sources) == 1
    assert sources[0].source_type == "artifact"
    assert sources[0].source_id == artifact_id
    assert sources[0].url == ARTIFACT_URL
    assert "20-year Anthropic lease" in sources[0].text
    assert unrelated == []
