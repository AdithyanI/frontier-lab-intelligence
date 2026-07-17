import hashlib
import json
import sqlite3

import pytest

from fli.evidence.artifacts import store as artifacts
from fli.evidence.artifacts import urls as artifact_urls


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
