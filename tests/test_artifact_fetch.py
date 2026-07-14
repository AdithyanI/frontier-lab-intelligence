import json
from pathlib import Path

import httpx

from fli import artifact_fetch, artifact_urls, artifacts


def _global_resolver(_host: str, _port: int):
    return ["93.184.216.34"]


def _seed_artifact(
    path: Path,
    *,
    url: str = "https://example.com/article",
    artifact_kind: str = "article",
) -> str:
    conn = artifacts.connect(path)
    artifact_id = artifact_urls.artifact_id(url)
    host = artifact_urls.canonicalize_url(url).split("/", 3)[2]
    now = "2026-07-14T00:00:00+00:00"
    with conn:
        conn.execute(
            """INSERT INTO artifact_import_run
               (import_run_id, schema_version, canonicalization_contract,
                source_feed_run_id, source_event_run_id, triage_runs_json,
                selection_policy, input_fingerprint, expected_candidate_count,
                accepted_count, excluded_count, failed_count, created_at,
                completed_at)
               VALUES ('import', ?, ?, 'feed', 'events', '[]', 'test',
                       'fingerprint', 1, 1, 0, 0, ?, ?)""",
            (artifacts.SCHEMA_VERSION, artifact_urls.CANONICALIZATION_CONTRACT, now, now),
        )
        conn.execute(
            """INSERT INTO artifact
               (artifact_id, canonical_url, canonicalization_contract, host,
                artifact_kind, first_seen_at, last_seen_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                artifact_id,
                url,
                artifact_urls.CANONICALIZATION_CONTRACT,
                host,
                artifact_kind,
                now,
                now,
                now,
                now,
            ),
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
               VALUES ('candidate', 'import', '2026-07-14', 'event', 1, 100,
                       'x_post', 'twitterapi_io', 'post', 'source-sha',
                       'https://x.com/a/status/post', 'post', 'source-sha',
                       'https://x.com/a/status/post', ?, 'https://t.co/a', ?,
                       'entity', NULL, 'links_to', 'accepted',
                       'external_http_url', ?, ?)""",
            (now, url, artifact_id, now),
        )
    conn.close()
    return artifact_id


def _native_terminal_failure(db: Path) -> None:
    def handler(request: httpx.Request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(403)

    result = artifact_fetch.fetch_cohort(
        db_path=db,
        limit=1,
        resolver=_global_resolver,
        transport=httpx.MockTransport(handler),
    )
    assert result["failed_terminal"] == 1


def test_safe_get_revalidates_redirect_target():
    def resolver(host: str, _port: int):
        return ["93.184.216.34"] if host == "example.com" else ["127.0.0.1"]

    def handler(request: httpx.Request):
        return httpx.Response(302, headers={"Location": "http://internal.test/secret"})

    client = httpx.Client(transport=httpx.MockTransport(handler), trust_env=False)
    try:
        try:
            artifact_fetch._safe_get(client, "https://example.com/start", resolver=resolver)
        except artifact_fetch.FetchFailure as exc:
            assert exc.code == "unsafe_address"
            assert exc.retryable is False
        else:
            raise AssertionError("unsafe redirect should fail")
    finally:
        client.close()


def test_extract_content_rejects_client_rendered_error_shell():
    body = b"""<html><head><title>Join us</title></head><body><main>
    <p>Oh dear. We were unable to load the form.</p>
    <p>Try checking your network connection or using a different browser.</p>
    </main></body></html>"""

    result = artifact_fetch.extract_content(
        body,
        content_type="text/html",
        charset="utf-8",
        final_url="https://example.com/form",
        artifact_kind="other",
    )

    assert result.success is False
    assert result.error_code == "extraction_client_rendered_shell"
    assert result.text is None


def test_fetch_cohort_snapshots_text_and_reuses_success(tmp_path, monkeypatch):
    db = tmp_path / "artifacts.db"
    artifact_id = _seed_artifact(db)
    monkeypatch.setattr(artifact_fetch, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(artifact_fetch, "TEXT_ROOT", tmp_path / "text")
    body = b"""<html><head><title>Useful launch</title></head><body><article>
    <h1>Useful launch</h1><p>This announcement contains a concrete, attributable
    technical release with enough substantive text for the deterministic artifact
    extractor to preserve and replay in later pipeline stages.</p></article></body></html>"""

    def handler(request: httpx.Request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, headers={"Content-Type": "text/html"}, content=body)

    transport = httpx.MockTransport(handler)
    first = artifact_fetch.fetch_cohort(
        db_path=db, limit=1, resolver=_global_resolver, transport=transport
    )
    second = artifact_fetch.fetch_cohort(
        db_path=db, limit=1, resolver=_global_resolver, transport=transport
    )

    assert first["success"] == 1
    assert second["reused"] is True
    conn = artifacts.connect(db)
    fetch = conn.execute("SELECT * FROM artifact_fetch").fetchone()
    assert fetch["artifact_id"] == artifact_id
    assert fetch["status"] == "success"
    assert fetch["extracted_title"] == "Useful launch"
    assert fetch["text_char_count"] > 100
    assert Path(fetch["raw_snapshot_ref"]).exists()
    assert Path(fetch["text_snapshot_ref"]).exists()
    conn.close()


def test_fetch_cohort_resumes_only_retryable_items(tmp_path, monkeypatch):
    db = tmp_path / "artifacts.db"
    artifact_id = _seed_artifact(db)
    monkeypatch.setattr(artifact_fetch, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(artifact_fetch, "TEXT_ROOT", tmp_path / "text")
    calls = {"artifact": 0}
    body = b"""<html><head><title>Recovered page</title></head><body><article>
    <h1>Recovered page</h1><p>The second bounded attempt recovered a concrete
    public artifact without re-running any already successful work in the
    frozen selection.</p></article></body></html>"""

    def handler(request: httpx.Request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls["artifact"] += 1
        if calls["artifact"] == 1:
            raise httpx.ConnectError("temporary route failure", request=request)
        return httpx.Response(200, headers={"Content-Type": "text/html"}, content=body)

    transport = httpx.MockTransport(handler)
    first = artifact_fetch.fetch_cohort(
        db_path=db, limit=1, resolver=_global_resolver, transport=transport
    )
    second = artifact_fetch.fetch_cohort(
        db_path=db, limit=1, resolver=_global_resolver, transport=transport
    )
    third = artifact_fetch.fetch_cohort(
        db_path=db, limit=1, resolver=_global_resolver, transport=transport
    )

    assert first["failed_retryable"] == 1
    assert first["reused"] is False
    assert second["success"] == 1
    assert second["reused"] is False
    assert third["reused"] is True
    assert calls["artifact"] == 2
    conn = artifacts.connect(db)
    attempts = conn.execute(
        """SELECT attempt_number, status FROM artifact_fetch
           WHERE artifact_id = ? ORDER BY attempt_number""",
        (artifact_id,),
    ).fetchall()
    assert [(row["attempt_number"], row["status"]) for row in attempts] == [
        (1, "failed_retryable"),
        (2, "success"),
    ]
    conn.close()


def test_fetch_cohort_does_not_retry_terminal_failure(tmp_path):
    db = tmp_path / "artifacts.db"
    artifact_id = _seed_artifact(db)
    calls = {"artifact": 0}

    def handler(request: httpx.Request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls["artifact"] += 1
        return httpx.Response(403)

    transport = httpx.MockTransport(handler)
    first = artifact_fetch.fetch_cohort(
        db_path=db, limit=1, resolver=_global_resolver, transport=transport
    )
    second = artifact_fetch.fetch_cohort(
        db_path=db, limit=1, resolver=_global_resolver, transport=transport
    )

    assert first["failed_terminal"] == 1
    assert first["reused"] is False
    assert second["reused"] is True
    assert calls["artifact"] == 1
    conn = artifacts.connect(db)
    attempts = conn.execute(
        "SELECT COUNT(*) FROM artifact_fetch WHERE artifact_id = ?",
        (artifact_id,),
    ).fetchone()[0]
    assert attempts == 1
    conn.close()


def test_jina_reader_recovers_eligible_native_failure_with_provenance(
    tmp_path, monkeypatch
):
    db = tmp_path / "artifacts.db"
    artifact_id = _seed_artifact(db)
    monkeypatch.setattr(artifact_fetch, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(artifact_fetch, "TEXT_ROOT", tmp_path / "text")
    _native_terminal_failure(db)
    seen: list[httpx.Request] = []

    def reader_handler(request: httpx.Request):
        seen.append(request)
        assert request.method == "POST"
        assert request.url == httpx.URL(artifact_fetch.JINA_READER_URL)
        assert request.headers["authorization"] == "Bearer test-reader-key"
        assert request.headers["accept"] == "application/json"
        assert json.loads(request.content) == {"url": "https://example.com/article"}
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            json={
                "code": 200,
                "status": 20000,
                "data": {
                    "title": "Recovered announcement",
                    "url": "https://example.com/article",
                    "content": (
                        "# Recovered announcement\n\nThis public announcement contains "
                        "enough concrete technical substance to support later "
                        "citation and extraction from the immutable Reader snapshot."
                    ),
                    "usage": {"tokens": 42},
                },
            },
        )

    first = artifact_fetch.recover_with_jina_reader(
        db_path=db,
        api_key="test-reader-key",
        transport=httpx.MockTransport(reader_handler),
    )
    second = artifact_fetch.recover_with_jina_reader(
        db_path=db,
        api_key="test-reader-key",
        transport=httpx.MockTransport(reader_handler),
    )

    assert first["success"] == 1
    assert first["authenticated"] is True
    assert second["expected_count"] == 0
    assert second["reused"] is True
    assert len(seen) == 1
    conn = artifacts.connect(db)
    fetch = conn.execute(
        """SELECT * FROM artifact_fetch
           WHERE artifact_id = ? AND fetch_policy = ?""",
        (artifact_id, artifact_fetch.JINA_READER_POLICY),
    ).fetchone()
    assert fetch["status"] == "success"
    assert fetch["extractor_contract"] == artifact_fetch.JINA_READER_EXTRACTOR
    assert fetch["extracted_title"] == "Recovered announcement"
    assert json.loads(fetch["response_headers_json"])["retrieval-provider"] == "jina_reader"
    assert json.loads(fetch["response_headers_json"])["reader-usage-tokens"] == "42"
    assert Path(fetch["raw_snapshot_ref"]).exists()
    assert Path(fetch["text_snapshot_ref"]).read_text().startswith(
        "# Recovered announcement"
    )
    conn.close()


def test_jina_reader_excludes_deferred_provider_adapters(tmp_path):
    db = tmp_path / "artifacts.db"
    _seed_artifact(
        db,
        url="https://www.linkedin.com/posts/example",
        artifact_kind="other",
    )
    _native_terminal_failure(db)
    calls = 0

    def reader_handler(_request: httpx.Request):
        nonlocal calls
        calls += 1
        raise AssertionError("deferred providers must not reach Jina Reader")

    result = artifact_fetch.recover_with_jina_reader(
        db_path=db,
        api_key="",
        transport=httpx.MockTransport(reader_handler),
    )

    assert result["expected_count"] == 0
    assert result["reused"] is True
    assert calls == 0


def test_jina_reader_rejects_thin_provider_output(tmp_path):
    db = tmp_path / "artifacts.db"
    _seed_artifact(db)
    _native_terminal_failure(db)

    def reader_handler(_request: httpx.Request):
        return httpx.Response(
            200,
            json={
                "code": 200,
                "status": 20000,
                "data": {
                    "title": "Blocked",
                    "url": "https://example.com/article",
                    "content": "Enable JavaScript.",
                },
            },
        )

    result = artifact_fetch.recover_with_jina_reader(
        db_path=db,
        api_key="",
        transport=httpx.MockTransport(reader_handler),
    )

    assert result["success"] == 0
    assert result["failed_terminal"] == 1
    conn = artifacts.connect(db)
    fetch = conn.execute(
        "SELECT * FROM artifact_fetch WHERE fetch_policy = ?",
        (artifact_fetch.JINA_READER_POLICY,),
    ).fetchone()
    assert fetch["error_code"] == "jina_thin_content"
    assert fetch["raw_snapshot_ref"] is None
    conn.close()


def test_jina_api_key_prefers_environment_then_repo_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("JINA_API_KEY='repo-key'\n", encoding="utf-8")
    monkeypatch.delenv("JINA_API_KEY", raising=False)
    assert artifact_fetch.jina_api_key(env_path=env_file) == "repo-key"
    monkeypatch.setenv("JINA_API_KEY", "environment-key")
    assert artifact_fetch.jina_api_key(env_path=env_file) == "environment-key"


def test_artifact_cli_has_stable_json_success_and_error_contract(tmp_path, capsys):
    db = tmp_path / "artifacts.db"

    assert artifacts.main(["summary", "--db", str(db), "--json", "--no-input"]) == 0
    success = json.loads(capsys.readouterr().out)
    assert success["schema_version"] == artifacts.RESULT_SCHEMA_VERSION
    assert success["command"] == "artifacts.summary"
    assert success["status"] == "ok"
    assert success["error"] is None
    assert set(success["meta"]) == {"request_id", "duration_ms", "timestamp_utc"}

    assert artifacts.main(["inspect", "--db", str(db), "--limit", "0"]) == 2
    failure = json.loads(capsys.readouterr().out)
    assert failure["command"] == "artifacts.inspect"
    assert failure["status"] == "error"
    assert failure["data"] is None
    assert failure["error"]["code"] == "E_VALIDATION"
    assert failure["error"]["retryable"] is False
    assert failure["error"]["hint"]


def test_summary_separates_fetch_attempts_from_artifact_outcomes(tmp_path):
    db = tmp_path / "artifacts.db"
    artifact_id = _seed_artifact(db)
    conn = artifacts.connect(db)
    now = "2026-07-14T00:00:00+00:00"
    with conn:
        conn.execute(
            """INSERT INTO artifact_fetch_run
               (fetch_run_id, schema_version, fetch_policy, selection_policy,
                input_fingerprint, expected_count, success_count,
                failed_retryable_count, failed_terminal_count, started_at,
                completed_at, status)
               VALUES ('fetch-run', ?, 'test', 'test-selection', 'fingerprint',
                       1, 1, 0, 0, ?, ?, 'complete')""",
            (artifacts.SCHEMA_VERSION, now, now),
        )
        conn.execute(
            """INSERT INTO artifact_fetch_run_item
               (fetch_run_id, artifact_id, selection_rank, stratum,
                selected_url, source_day, source_rank, normalized_rank,
                source_event_id)
               VALUES ('fetch-run', ?, 1, 'article',
                       'https://example.com/article', '2026-07-14', 1, 0.01,
                       'event')""",
            (artifact_id,),
        )
        for attempt_number, status in ((1, "failed_retryable"), (2, "success")):
            conn.execute(
                """INSERT INTO artifact_fetch
                   (fetch_id, fetch_run_id, artifact_id, attempt_number, status,
                    fetch_policy, request_key, requested_url, started_at,
                    completed_at, error_code, retryable)
                   VALUES (?, 'fetch-run', ?, ?, ?, 'test', ?,
                           'https://example.com/article', ?, ?, ?, ?)""",
                (
                    f"fetch-{attempt_number}",
                    artifact_id,
                    attempt_number,
                    status,
                    f"request-{attempt_number}",
                    now,
                    now,
                    "temporary" if status == "failed_retryable" else None,
                    1 if status == "failed_retryable" else 0,
                ),
            )

    result = artifacts.summary(conn)

    assert result["counts"]["fetch_attempts"] == 2
    assert result["fetch_attempt_statuses"] == {
        "failed_retryable": 1,
        "success": 1,
    }
    assert result["fetch_outcomes"] == {"success": 1}
    conn.close()
