import json
import shutil

from fastapi.testclient import TestClient
import pytest

from fli.evidence.artifacts import store as artifacts
from fli.web import artifact_library as artifact_store
from fli.web.app import app


client = TestClient(app)


def test_product_artifact_type_keeps_x_articles_distinct():
    assert artifact_store._artifact_type(
        "article", "http://x.com/i/article/2073093772817453056"
    ) == "x_article"
    assert artifact_store._artifact_type(
        "article", "https://example.com/research"
    ) == "web"


def test_google_docs_repair_has_a_reader_facing_fetch_method():
    assert artifact_store._fetch_method("google-docs-public-text-v1") == (
        "Google Docs export"
    )


def _artifact_fixture(path):
    conn = artifacts.connect(path)
    conn.executemany(
        """INSERT INTO artifact
           (artifact_id, canonical_url, canonicalization_contract, host,
            artifact_kind, title, first_seen_at, last_seen_at, created_at,
            updated_at)
           VALUES (?, ?, 'test-v1', ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                "older",
                "https://example.com/research",
                "example.com",
                "article",
                "A durable research result",
                "2026-07-10T09:00:00+00:00",
                "2026-07-12T10:01:00+00:00",
                "2026-07-10T09:00:00+00:00",
                "2026-07-12T10:01:00+00:00",
            ),
            (
                "newer",
                "https://github.com/example/project",
                "github.com",
                "repository",
                None,
                "2026-07-11T10:00:00+00:00",
                "2026-07-11T10:00:00+00:00",
                "2026-07-11T10:00:00+00:00",
                "2026-07-11T10:00:00+00:00",
            ),
        ],
    )
    conn.execute(
        """INSERT INTO artifact_import_run
           (import_run_id, schema_version, canonicalization_contract,
            source_feed_run_id, source_event_run_id, triage_runs_json,
            selection_policy, input_fingerprint, expected_candidate_count,
            accepted_count, excluded_count, failed_count, created_at,
            completed_at)
           VALUES ('import', ?, 'test-v1', 'feed-run', 'event-run', '[]',
                   'test', 'artifact-fixture', 2, 2, 0, 0,
                   '2026-07-11T10:00:00+00:00',
                   '2026-07-11T10:00:00+00:00')""",
        (artifacts.SCHEMA_VERSION,),
    )
    conn.execute(
        """INSERT INTO artifact_import_candidate
           (candidate_id, import_run_id, event_day, event_id, source_rank,
            day_candidate_count, source_kind, source_provider,
            source_external_id, source_snapshot_sha256, source_url,
            disclosure_external_id, disclosure_snapshot_sha256,
            disclosure_url, disclosure_published_at, observed_url,
            expanded_url, candidate_source, title_hint, relation, decision,
            reason_code, artifact_id, created_at)
           VALUES ('candidate-newer', 'import', '2026-07-11', 'event-newer',
                   2, 2, 'x_post', 'twitterapi_io', 'post-2', 'sha',
                   'https://x.com/example/status/2', 'post-2', 'sha',
                   'https://x.com/example/status/2',
                   '2026-07-11T10:00:00+00:00',
                   'https://github.com/example/project',
                   'https://github.com/example/project', 'post_url', NULL,
                   'links_to', 'accepted', 'external_http_url', 'newer',
                   '2026-07-11T10:00:00+00:00')"""
    )
    conn.execute(
        """INSERT INTO artifact_import_candidate
           (candidate_id, import_run_id, event_day, event_id, source_rank,
            day_candidate_count, source_kind, source_provider,
            source_external_id, source_snapshot_sha256, source_url,
            disclosure_external_id, disclosure_snapshot_sha256,
            disclosure_url, disclosure_published_at, observed_url,
            expanded_url, candidate_source, title_hint, relation, decision,
            reason_code, artifact_id, created_at)
           VALUES ('candidate-reshared', 'import', '2026-07-10', 'event-reshared',
                   3, 2, 'x_post', 'twitterapi_io', 'post-3', 'sha',
                   'https://x.com/example/status/3', 'post-3', 'sha',
                   'https://x.com/example/status/3',
                   '2026-07-11T11:00:00+00:00',
                   'https://example.com/research',
                   'https://example.com/research', 'post_url', NULL,
                   'links_to', 'accepted', 'external_http_url', 'older',
                   '2026-07-11T11:00:00+00:00')"""
    )
    conn.executemany(
        """INSERT INTO artifact_observation
           (observation_id, artifact_id, source_kind, source_provider,
            source_external_id, source_snapshot_sha256, source_url,
            observed_url, expanded_url, relation, source_published_at,
            first_event_day, best_source_rank, first_seen_at, last_seen_at)
           VALUES (?, ?, 'x_post', 'twitterapi_io', ?, 'sha', ?, ?, ?,
                   'links_to', ?, ?, ?, ?, ?)""",
        [
            (
                "observation-older",
                "older",
                "post-1",
                "https://x.com/example/status/1",
                "https://example.com/research",
                "https://example.com/research",
                "2026-07-10T09:00:00+00:00",
                "2026-07-10",
                4,
                "2026-07-10T09:00:00+00:00",
                "2026-07-10T09:00:00+00:00",
            ),
            (
                "observation-newer",
                "newer",
                "post-2",
                "https://x.com/example/status/2",
                "https://github.com/example/project",
                "https://github.com/example/project",
                "2026-07-11T10:00:00+00:00",
                "2026-07-11",
                2,
                "2026-07-11T10:00:00+00:00",
                "2026-07-11T10:00:00+00:00",
            ),
            (
                "observation-older-reshared",
                "older",
                "post-3",
                "https://x.com/example/status/3",
                "https://example.com/research",
                "https://example.com/research",
                "2026-07-11T11:00:00+00:00",
                "2026-07-11",
                3,
                "2026-07-11T11:00:00+00:00",
                "2026-07-11T11:00:00+00:00",
            ),
            (
                "observation-older-reshared-again",
                "older",
                "post-4",
                "https://x.com/example/status/4",
                "https://example.com/research",
                "https://example.com/research",
                "2026-07-11T11:30:00+00:00",
                "2026-07-11",
                5,
                "2026-07-11T11:30:00+00:00",
                "2026-07-11T11:30:00+00:00",
            ),
        ],
    )
    conn.execute(
        """INSERT INTO artifact_fetch_run
           (fetch_run_id, schema_version, fetch_policy, selection_policy,
            input_fingerprint, expected_count, success_count,
            failed_retryable_count, failed_terminal_count, started_at,
            completed_at, status)
           VALUES ('run', ?, 'bounded-public-v1', 'test', 'fingerprint',
                   1, 1, 0, 0, '2026-07-12T10:00:00+00:00',
                   '2026-07-12T10:01:00+00:00', 'complete')""",
        (artifacts.SCHEMA_VERSION,),
    )
    conn.execute(
        """INSERT INTO artifact_fetch
           (fetch_id, fetch_run_id, artifact_id, fetch_policy, requested_url,
            request_key, status, attempt_number, started_at, completed_at,
            final_url, http_status, extractor_contract, extractor_version,
            text_char_count, retryable)
           VALUES ('fetch', 'run', 'older', 'bounded-public-v1',
                   'https://example.com/research', 'request', 'success', 1,
                   '2026-07-12T10:00:00+00:00',
                   '2026-07-12T10:01:00+00:00',
                   'https://example.com/research', 200, 'readability-v1', '1',
                   4200, 0)"""
    )
    conn.commit()
    conn.close()


def test_artifacts_api_defaults_to_latest_source_day_with_provenance(
    tmp_path, monkeypatch
):
    db = tmp_path / "artifacts.db"
    _artifact_fixture(db)
    monkeypatch.setattr(artifact_store, "DEFAULT_ARTIFACT_DB", db)

    response = client.get("/api/artifacts?limit=20")
    assert response.status_code == 200
    payload = response.json()

    assert payload["available"] is True
    assert payload["catalog_total"] == 2
    assert payload["catalog_fetch_state_counts"] == {
        "catalogued": 1,
        "ready": 1,
        "retryable": 0,
        "unavailable": 0,
        "fetching": 0,
    }
    assert payload["date"] == "2026-07-11"
    assert payload["matching_total"] == 2
    assert [item["artifact_id"] for item in payload["items"]] == ["newer", "older"]
    assert payload["items"][0]["best_source_rank"] == 2
    assert payload["items"][0]["artifact_type"] == "repository"
    assert payload["items"][0]["source_published_at"] == (
        "2026-07-11T10:00:00+00:00"
    )
    assert payload["items"][0]["source_event_id"] == "event-newer"
    assert payload["items"][0]["fetch_state"] == "catalogued"
    assert payload["items"][1]["best_source_rank"] == 3
    assert payload["items"][1]["artifact_type"] == "web"
    assert payload["items"][1]["day_last_source_published_at"] == (
        "2026-07-11T11:30:00+00:00"
    )
    assert payload["items"][1]["day_observation_count"] == 2
    assert payload["items"][1]["source_provider"] == "twitterapi_io"
    assert payload["items"][1]["source_event_id"] == "event-reshared"
    assert payload["items"][1]["fetch_state"] == "ready"
    assert payload["items"][1]["fetch_method"] == "Direct fetch"
    assert payload["items"][1]["text_char_count"] == 4200


def test_artifact_text_api_returns_normalized_snapshot_without_exposing_path(
    tmp_path, monkeypatch
):
    db = tmp_path / "artifacts.db"
    _artifact_fixture(db)
    snapshot = tmp_path / "data" / "derived" / "artifacts" / "text" / "snapshot.txt"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text("# Extracted title\n\nExact normalized evidence.\n")
    conn = artifacts.connect(db)
    conn.execute(
        """UPDATE artifact_fetch
           SET text_snapshot_ref = ?, extractor_contract = 'jina-reader-markdown-v1',
               text_char_count = ?, text_truncated = 0
           WHERE fetch_id = 'fetch'""",
        (str(snapshot.relative_to(tmp_path)), len(snapshot.read_text())),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(artifact_store, "DEFAULT_ARTIFACT_DB", db)
    monkeypatch.setattr(artifact_store, "DEFAULT_REPO_ROOT", tmp_path)

    response = client.get("/api/artifacts/older/text")

    assert response.status_code == 200
    assert response.text == "# Extracted title\n\nExact normalized evidence.\n"
    assert response.headers["x-artifact-format"] == "markdown"
    assert response.headers["x-artifact-extractor"] == "jina-reader-markdown-v1"
    assert response.headers["cache-control"] == "private, max-age=0, must-revalidate"
    assert "snapshot.txt" not in response.text


def test_artifact_text_api_is_honest_when_snapshot_is_unavailable(
    tmp_path, monkeypatch
):
    db = tmp_path / "artifacts.db"
    _artifact_fixture(db)
    monkeypatch.setattr(artifact_store, "DEFAULT_ARTIFACT_DB", db)
    monkeypatch.setattr(artifact_store, "DEFAULT_REPO_ROOT", tmp_path)

    response = client.get("/api/artifacts/older/text")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No readable text snapshot exists for this artifact."
    )


def _relocated_artifact_fixture(tmp_path, monkeypatch):
    repo_root = tmp_path / "checkout"
    external = tmp_path / "production"
    external.mkdir()
    local_db = repo_root / "data" / "derived" / "artifacts" / "artifacts.db"
    _artifact_fixture(local_db)
    logical = "data/derived/artifacts/text/snapshot.txt"
    snapshot = repo_root / logical
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text("Preserved artifact evidence.\n")
    conn = artifacts.connect(local_db)
    conn.execute(
        "UPDATE artifact_fetch SET text_snapshot_ref = ? WHERE fetch_id = 'fetch'",
        (logical,),
    )
    conn.commit()
    conn.close()
    shutil.move(str(repo_root / "data" / "derived"), str(external / "derived"))
    (repo_root / "data" / "storage.local.json").write_text(
        json.dumps({"version": 1, "data_root": str(external)})
    )
    db = external / "derived" / "artifacts" / "artifacts.db"
    monkeypatch.delenv("FLI_STORAGE_CONFIG", raising=False)
    monkeypatch.setattr(artifact_store, "DEFAULT_ARTIFACT_DB", db)
    monkeypatch.setattr(artifact_store, "DEFAULT_REPO_ROOT", repo_root)
    return repo_root, external, db, logical


def test_artifact_text_survives_moving_storage_without_rewriting_database(
    tmp_path, monkeypatch
):
    repo_root, external, db, logical = _relocated_artifact_fixture(
        tmp_path, monkeypatch
    )
    before = db.read_bytes()

    response = client.get("/api/artifacts/older/text")

    assert response.status_code == 200
    assert response.text == "Preserved artifact evidence.\n"
    assert db.read_bytes() == before
    assert not (repo_root / "data" / "derived").exists()
    assert (external / "derived" / "artifacts" / "text" / "snapshot.txt").is_file()


@pytest.mark.parametrize("escape", ["traversal", "symlink", "absolute"])
def test_artifact_text_rejects_references_outside_configured_text_root(
    tmp_path, monkeypatch, escape
):
    repo_root, external, db, logical = _relocated_artifact_fixture(
        tmp_path, monkeypatch
    )
    # Another file in the configured data root is still outside the text boundary.
    outside = external / "derived" / "private.txt"
    outside.write_text("This must never be served.")
    if escape == "traversal":
        snapshot_ref = "data/derived/artifacts/text/../../private.txt"
    elif escape == "symlink":
        snapshot = external / "derived" / "artifacts" / "text" / "snapshot.txt"
        snapshot.unlink()
        snapshot.symlink_to(outside)
        snapshot_ref = logical
    else:
        snapshot_ref = str(outside)
    conn = artifacts.connect(db)
    conn.execute(
        "UPDATE artifact_fetch SET text_snapshot_ref = ? WHERE fetch_id = 'fetch'",
        (snapshot_ref,),
    )
    conn.commit()
    conn.close()

    response = client.get("/api/artifacts/older/text")

    assert response.status_code == 404
    assert response.json()["detail"] == "The artifact text snapshot is missing or invalid."
    assert "This must never be served." not in response.text


def test_artifact_dates_are_source_dates_with_distinct_counts(tmp_path, monkeypatch):
    db = tmp_path / "artifacts.db"
    _artifact_fixture(db)
    monkeypatch.setattr(artifact_store, "DEFAULT_ARTIFACT_DB", db)

    response = client.get("/api/artifacts/dates")
    assert response.status_code == 200
    assert response.json() == {
        "available": True,
        "latest_date": "2026-07-11",
        "date_from": "2026-07-10",
        "date_to": "2026-07-11",
        "dates": [
            {"day": "2026-07-10", "item_count": 1},
            {"day": "2026-07-11", "item_count": 2},
        ],
    }


def test_artifact_reads_do_not_mutate_the_catalog_file(tmp_path, monkeypatch):
    db = tmp_path / "artifacts.db"
    _artifact_fixture(db)
    monkeypatch.setattr(artifact_store, "DEFAULT_ARTIFACT_DB", db)
    wal = tmp_path / "artifacts.db-wal"
    before_version = (db.stat().st_mtime_ns, db.stat().st_size)

    assert client.get("/api/artifacts/dates").status_code == 200
    assert client.get("/api/artifacts?date=2026-07-11&limit=20").status_code == 200

    assert (db.stat().st_mtime_ns, db.stat().st_size) == before_version
    assert not wal.exists() or wal.stat().st_size == 0


def test_artifacts_api_filters_exact_source_day_and_search(tmp_path, monkeypatch):
    db = tmp_path / "artifacts.db"
    _artifact_fixture(db)
    monkeypatch.setattr(artifact_store, "DEFAULT_ARTIFACT_DB", db)

    older_day = client.get("/api/artifacts?date=2026-07-10")
    assert older_day.status_code == 200
    assert older_day.json()["matching_total"] == 1
    assert [item["artifact_id"] for item in older_day.json()["items"]] == [
        "older"
    ]

    searched = client.get("/api/artifacts?date=2026-07-11&q=github")
    assert searched.status_code == 200
    assert searched.json()["query"] == "github"
    assert searched.json()["matching_total"] == 1
    assert [item["artifact_id"] for item in searched.json()["items"]] == [
        "newer"
    ]

    earlier_observer = client.get(
        "/api/artifacts",
        params={"date": "2026-07-11", "q": "status/3"},
    )
    assert earlier_observer.status_code == 200
    assert earlier_observer.json()["matching_total"] == 1
    assert [item["artifact_id"] for item in earlier_observer.json()["items"]] == [
        "older"
    ]


def test_artifacts_api_is_honest_when_catalog_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        artifact_store, "DEFAULT_ARTIFACT_DB", tmp_path / "missing.db"
    )

    response = client.get("/api/artifacts")
    assert response.status_code == 200
    assert response.json()["available"] is False
