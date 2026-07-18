import json
import sqlite3

from fli.evidence.artifacts import cli as artifact_cli
from fli.evidence.artifacts import store as artifacts
from fli.evidence.artifacts import urls as artifact_urls


def _fixture(tmp_path):
    def write_triage(path, root_id):
        triage = sqlite3.connect(path)
        triage.execute(
            """CREATE TABLE triage_item (
                   event_id TEXT PRIMARY KEY,
                   event_json TEXT NOT NULL,
                   status TEXT NOT NULL,
                   decision TEXT NOT NULL
               )"""
        )
        triage.execute(
            "INSERT INTO triage_item VALUES (?, ?, 'complete', 'keep')",
            ("event", json.dumps({"root": {"post_id": root_id}})),
        )
        triage.commit()
        triage.close()

    older_triage_db = tmp_path / "older-triage.db"
    triage_db = tmp_path / "triage.db"
    write_triage(older_triage_db, "older-root")
    write_triage(triage_db, "root")

    feed_db = tmp_path / "feed.db"
    feed = sqlite3.connect(feed_db)
    feed.execute(
        """CREATE TABLE feed_post (
               run_id TEXT NOT NULL,
               provider TEXT NOT NULL,
               post_id TEXT NOT NULL,
               author_x_id TEXT,
               conversation_id TEXT,
               post_type TEXT,
               raw_sha256 TEXT NOT NULL,
               raw_json TEXT NOT NULL
           )"""
    )
    source_url = "https://example.com/primary-source"
    feed.executemany(
        "INSERT INTO feed_post VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                "feed-run",
                "twitterapi_io",
                "older-root",
                "author-1",
                "older-root",
                "original",
                "older-root-sha",
                json.dumps({"id": "older-root", "entities": {"urls": []}}),
            ),
            (
                "feed-run",
                "twitterapi_io",
                "root",
                "author-1",
                "root",
                "original",
                "root-sha",
                json.dumps({"id": "root", "entities": {"urls": []}}),
            ),
            (
                "feed-run",
                "twitterapi_io",
                "reply",
                "author-1",
                "root",
                "reply",
                "reply-sha",
                json.dumps(
                    {
                        "id": "reply",
                        "entities": {
                            "urls": [
                                {
                                    "url": "https://t.co/source",
                                    "expanded_url": source_url,
                                }
                            ]
                        },
                    }
                ),
            ),
        ],
    )
    feed.commit()
    feed.close()

    artifact_db = tmp_path / "artifacts.db"
    catalog = artifacts.connect(artifact_db)
    artifact_id = artifact_urls.artifact_id(source_url)
    now = "2026-07-15T00:00:00+00:00"
    with catalog:
        catalog.execute(
            """INSERT INTO artifact_import_run
               (import_run_id, schema_version, canonicalization_contract,
                source_feed_run_id, source_event_run_id, triage_runs_json,
                selection_policy, input_fingerprint, expected_candidate_count,
                accepted_count, excluded_count, failed_count, created_at,
                completed_at)
               VALUES ('import', ?, ?, 'feed-run', 'event-run', ?, ?,
                       'fingerprint', 1, 1, 0, 0, ?, ?)""",
            (
                artifacts.SCHEMA_VERSION,
                artifact_urls.CANONICALIZATION_CONTRACT,
                json.dumps(
                    [
                        {
                            "day": "2026-07-14",
                            "path": str(older_triage_db),
                        },
                        {"day": "2026-07-15", "path": str(triage_db)},
                    ]
                ),
                artifacts.PRIMARY_AUTHOR_SELECTION_POLICY,
                now,
                now,
            ),
        )
        catalog.execute(
            """INSERT INTO artifact
               (artifact_id, canonical_url, canonicalization_contract, host,
                artifact_kind, first_seen_at, last_seen_at, created_at, updated_at)
               VALUES (?, ?, ?, 'example.com', 'article', ?, ?, ?, ?)""",
            (
                artifact_id,
                source_url,
                artifact_urls.CANONICALIZATION_CONTRACT,
                now,
                now,
                now,
                now,
            ),
        )
        catalog.execute(
            """INSERT INTO artifact_import_candidate
               (candidate_id, import_run_id, event_day, event_id, source_rank,
                day_candidate_count, source_kind, source_provider,
                source_external_id, source_snapshot_sha256, source_url,
                disclosure_external_id, disclosure_snapshot_sha256,
                disclosure_url, disclosure_published_at, observed_url,
                expanded_url, candidate_source, title_hint, relation, decision,
                reason_code, artifact_id, created_at)
               VALUES ('candidate', 'import', '2026-07-15', 'event', 1, 10,
                       'x_post', 'twitterapi_io', 'reply', 'reply-sha',
                       'https://x.com/a/status/reply', 'reply', 'reply-sha',
                       'https://x.com/a/status/reply', ?, 'https://t.co/source', ?,
                       'entity', NULL, 'links_to', 'accepted',
                       'external_http_url', ?, ?)""",
            (now, source_url, artifact_id, now),
        )
        catalog.execute(
            """INSERT INTO artifact_observation
               (observation_id, artifact_id, source_kind, source_provider,
                source_external_id, source_snapshot_sha256, source_url,
                observed_url, expanded_url, relation, source_published_at,
                first_event_day, best_source_rank, first_seen_at, last_seen_at)
               VALUES ('observation', ?, 'x_post', 'twitterapi_io', 'reply',
                       'reply-sha', 'https://x.com/a/status/reply',
                       'https://t.co/source', ?, 'links_to', ?, '2026-07-15',
                       1, ?, ?)""",
            (artifact_id, source_url, now, now, now),
        )
        catalog.execute(
            """INSERT INTO artifact_disclosure
               (disclosure_id, observation_id, source_provider,
                disclosure_external_id, disclosure_snapshot_sha256,
                disclosure_url, disclosure_published_at, first_event_day,
                last_event_day)
               VALUES ('disclosure', 'observation', 'twitterapi_io', 'reply',
                       'reply-sha', 'https://x.com/a/status/reply', ?,
                       '2026-07-15', '2026-07-15')""",
            (now,),
        )
    catalog.close()
    return artifact_db, feed_db


def test_primary_author_lineage_audit_passes_same_author_reply(tmp_path):
    artifact_db, feed_db = _fixture(tmp_path)

    # The import manifest preserves triage provenance, but the lineage proof is
    # intentionally self-contained once the candidate and raw Feed post have
    # been frozen. Historical triage databases may be cleaned up later.
    (tmp_path / "older-triage.db").unlink()
    (tmp_path / "triage.db").unlink()

    report = artifacts.audit_primary_author_lineage(
        db_path=artifact_db,
        feed_db=feed_db,
    )

    assert report["passed"] is True
    assert report["counts"] == {
        "accepted_candidates": 1,
        "artifacts": 1,
        "observations": 1,
        "reviewed_supplements": 0,
        "violations": 0,
    }
    assert report["violation_reasons"] == {}


def test_primary_author_lineage_cli_fails_with_structured_foreign_author_report(
    tmp_path, capsys
):
    artifact_db, feed_db = _fixture(tmp_path)
    feed = sqlite3.connect(feed_db)
    feed.execute(
        "UPDATE feed_post SET author_x_id = 'foreign-author' WHERE post_id = 'reply'"
    )
    feed.commit()
    feed.close()

    exit_code = artifact_cli.main(
        [
            "audit-lineage",
            "--db",
            str(artifact_db),
            "--feed-db",
            str(feed_db),
            "--json",
            "--no-input",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["command"] == "artifacts.audit-lineage"
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "E_INTEGRITY"
    assert payload["data"]["passed"] is False
    assert payload["data"]["violation_reasons"] == {"foreign_author": 1}


def test_primary_author_lineage_reports_missing_frozen_root_as_coverage(tmp_path):
    artifact_db, feed_db = _fixture(tmp_path)
    feed = sqlite3.connect(feed_db)
    feed.execute("DELETE FROM feed_post WHERE post_id = 'root'")
    feed.commit()
    feed.close()

    report = artifacts.audit_primary_author_lineage(
        db_path=artifact_db,
        feed_db=feed_db,
    )

    assert report["passed"] is True
    assert report["coverage"] == {
        "conversation_roots_verified": 0,
        "conversation_roots_frozen_import_only": 1,
    }
    assert report["violation_reasons"] == {}
