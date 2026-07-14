from fastapi.testclient import TestClient

from fli import artifacts
from fli.web import artifact_library as artifact_store
from fli.web.app import app


client = TestClient(app)


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
    conn.executemany(
        """INSERT INTO artifact_observation
           (observation_id, artifact_id, source_kind, source_provider,
            source_external_id, source_snapshot_sha256, source_url,
            observed_url, expanded_url, relation, source_published_at,
            first_envelope_day, best_source_rank, first_seen_at, last_seen_at)
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


def test_artifacts_api_returns_newest_first_with_provenance(tmp_path, monkeypatch):
    db = tmp_path / "artifacts.db"
    _artifact_fixture(db)
    monkeypatch.setattr(artifact_store, "DEFAULT_ARTIFACT_DB", db)

    response = client.get("/api/artifacts?limit=20")
    assert response.status_code == 200
    payload = response.json()

    assert payload["available"] is True
    assert payload["total"] == 2
    assert payload["counts"] == {
        "catalogued": 1,
        "ready": 1,
        "retryable": 0,
        "unavailable": 0,
        "fetching": 0,
    }
    assert [item["artifact_id"] for item in payload["items"]] == ["newer", "older"]
    assert payload["items"][0]["last_source_published_at"] == (
        "2026-07-11T10:00:00+00:00"
    )
    assert payload["items"][0]["source_provider"] == "twitterapi_io"
    assert payload["items"][0]["fetch_state"] == "catalogued"
    assert payload["items"][1]["fetch_state"] == "ready"
    assert payload["items"][1]["fetch_method"] == "Direct fetch"
    assert payload["items"][1]["text_char_count"] == 4200


def test_artifacts_api_is_honest_when_catalog_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        artifact_store, "DEFAULT_ARTIFACT_DB", tmp_path / "missing.db"
    )

    response = client.get("/api/artifacts")
    assert response.status_code == 200
    assert response.json()["available"] is False
