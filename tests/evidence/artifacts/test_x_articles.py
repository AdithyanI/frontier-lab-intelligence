import hashlib
import json
from pathlib import Path

import httpx
import pytest

from fli.evidence.artifacts import fetch as artifact_fetch
from fli.evidence.artifacts import store as artifacts
from fli.evidence.artifacts import urls as artifact_urls
from fli.evidence.artifacts import x_articles as artifact_x_articles


def _seed_x_article(
    path: Path,
    *,
    article_id: str = "111",
    post_ids: tuple[str, ...] = ("222",),
) -> str:
    url = f"http://x.com/i/article/{article_id}"
    artifact_id = artifact_urls.artifact_id(url)
    now = "2026-07-14T00:00:00+00:00"
    conn = artifacts.connect(path)
    with conn:
        import_exists = conn.execute(
            "SELECT 1 FROM artifact_import_run WHERE import_run_id = 'import'"
        ).fetchone()
        if import_exists is None:
            conn.execute(
                """INSERT INTO artifact_import_run
                   (import_run_id, schema_version, canonicalization_contract,
                    source_feed_run_id, source_event_run_id, triage_runs_json,
                    selection_policy, input_fingerprint, expected_candidate_count,
                    accepted_count, excluded_count, failed_count, created_at,
                    completed_at)
                   VALUES ('import', ?, ?, 'feed', 'events', '[]', 'test',
                           'fingerprint', ?, ?, 0, 0, ?, ?)""",
                (
                    artifacts.SCHEMA_VERSION,
                    artifact_urls.CANONICALIZATION_CONTRACT,
                    len(post_ids),
                    len(post_ids),
                    now,
                    now,
                ),
            )
        conn.execute(
            """INSERT INTO artifact
               (artifact_id, canonical_url, canonicalization_contract, host,
                artifact_kind, first_seen_at, last_seen_at, created_at, updated_at)
               VALUES (?, ?, ?, 'x.com', 'article', ?, ?, ?, ?)""",
            (
                artifact_id,
                url,
                artifact_urls.CANONICALIZATION_CONTRACT,
                now,
                now,
                now,
                now,
            ),
        )
        for ordinal, post_id in enumerate(post_ids, 1):
            conn.execute(
                """INSERT INTO artifact_import_candidate
                   (candidate_id, import_run_id, envelope_day, event_id,
                    source_rank, day_candidate_count, source_kind,
                    source_provider, source_external_id,
                    source_snapshot_sha256, source_url,
                    disclosure_external_id, disclosure_snapshot_sha256,
                    disclosure_url, disclosure_published_at, observed_url,
                    expanded_url, candidate_source, title_hint, relation,
                    decision, reason_code, artifact_id, created_at)
                   VALUES (?, 'import', '2026-07-14', ?, ?, 100, 'x_post',
                           'twitterapi_io', ?, 'source-sha', ?, ?, 'source-sha',
                           ?, ?, ?, ?, 'x_article', 'Preview title',
                           'self_publishes', 'accepted', 'x_longform_article',
                           ?, ?)""",
                (
                    f"candidate-{article_id}-{ordinal}",
                    f"event-{article_id}-{ordinal}",
                    ordinal,
                    post_id,
                    f"https://x.com/author/status/{post_id}",
                    post_id,
                    f"https://x.com/author/status/{post_id}",
                    now,
                    url,
                    url,
                    artifact_id,
                    now,
                ),
            )
    conn.close()
    return artifact_id


def test_x_article_fetch_preserves_raw_blocks_and_body_only(
    tmp_path, monkeypatch
):
    db = tmp_path / "artifacts.db"
    artifact_id = _seed_x_article(db)
    monkeypatch.setattr(artifact_fetch, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(artifact_fetch, "TEXT_ROOT", tmp_path / "text")
    raw = (
        b'{"article":{"title":"Actual title","preview_text":"Do not cite preview",'
        b'"contents":[{"type":"unstyled","text":"First paragraph."},'
        b'{"type":"image","url":"https://example.com/image.png"},'
        b'{"type":"unstyled","text":"Second paragraph."}]},'
        b'"status":"success","message":"ok"}'
    )
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request):
        requests.append(request)
        assert request.method == "GET"
        assert request.url.path == "/twitter/article"
        assert request.url.params["tweet_id"] == "222"
        assert request.headers["x-api-key"] == "test-key"
        return httpx.Response(
            200, headers={"Content-Type": "application/json"}, content=raw
        )

    first = artifact_x_articles.fetch_x_articles(
        db_path=db,
        limit=1,
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    second = artifact_x_articles.fetch_x_articles(
        db_path=db,
        limit=1,
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    assert first == {
        "fetch_run_id": first["fetch_run_id"],
        "expected_count": 1,
        "success": 1,
        "failed_retryable": 0,
        "failed_terminal": 0,
        "provider_request_attempts": 1,
        "estimated_provider_credits": 100,
        "provider_request_attempts_this_call": 1,
        "estimated_provider_credits_this_call": 100,
        "reused": False,
    }
    assert second["reused"] is True
    assert second["provider_request_attempts_this_call"] == 0
    assert second["estimated_provider_credits_this_call"] == 0
    assert len(requests) == 1

    conn = artifacts.connect(db)
    fetch = conn.execute(
        "SELECT * FROM artifact_fetch WHERE fetch_policy = ?",
        (artifact_x_articles.FETCH_POLICY,),
    ).fetchone()
    provider = conn.execute("SELECT * FROM artifact_x_article_fetch").fetchone()
    assert fetch["artifact_id"] == artifact_id
    assert fetch["status"] == "success"
    assert fetch["extracted_title"] == "Actual title"
    assert fetch["declared_canonical_url"] == "https://x.com/i/article/111"
    assert Path(fetch["raw_snapshot_ref"]).read_bytes() == raw
    assert Path(fetch["text_snapshot_ref"]).read_text() == (
        "First paragraph.\n\nSecond paragraph.\n"
    )
    assert "Do not cite preview" not in Path(fetch["text_snapshot_ref"]).read_text()
    assert provider["request_post_id"] == "222"
    assert provider["canonical_article_id"] == "111"
    assert provider["canonical_article_url"] == "https://x.com/i/article/111"
    assert provider["content_block_count"] == 3
    blocks = json.loads(provider["content_blocks_json"])
    assert [block["type"] for block in blocks] == ["unstyled", "image", "unstyled"]
    assert provider["content_blocks_sha256"] == hashlib.sha256(
        provider["content_blocks_json"].encode()
    ).hexdigest()
    conn.close()


def test_x_article_preview_only_is_terminal_and_never_body_evidence(
    tmp_path, monkeypatch
):
    db = tmp_path / "artifacts.db"
    _seed_x_article(db)
    monkeypatch.setattr(artifact_fetch, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(artifact_fetch, "TEXT_ROOT", tmp_path / "text")

    def handler(_request: httpx.Request):
        return httpx.Response(
            200,
            json={
                "article": {
                    "title": "Title is metadata",
                    "preview_text": "Preview must not become evidence",
                    "contents": [{"type": "image", "url": "https://example.com/a"}],
                },
                "status": "success",
                "message": "ok",
            },
        )

    result = artifact_x_articles.fetch_x_articles(
        db_path=db,
        limit=1,
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    assert result["failed_terminal"] == 1
    conn = artifacts.connect(db)
    fetch = conn.execute(
        "SELECT * FROM artifact_fetch WHERE fetch_policy = ?",
        (artifact_x_articles.FETCH_POLICY,),
    ).fetchone()
    assert fetch["error_code"] == "x_article_body_missing"
    assert fetch["text_snapshot_ref"] is None
    assert fetch["raw_snapshot_ref"] is not None
    assert fetch["extracted_title"] == "Title is metadata"
    conn.close()


def test_x_article_placeholder_body_is_terminal_and_never_text_evidence(
    tmp_path, monkeypatch
):
    db = tmp_path / "artifacts.db"
    _seed_x_article(db)
    monkeypatch.setattr(artifact_fetch, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(artifact_fetch, "TEXT_ROOT", tmp_path / "text")

    def handler(_request: httpx.Request):
        return httpx.Response(
            200,
            json={
                "article": {
                    "title": "Broken extraction",
                    "contents": [
                        {
                            "type": "unstyled",
                            "text": (("\u2588" * 12 + " ") * 50)
                            + "BY PUBLISHER",
                        }
                    ],
                },
                "status": "success",
                "message": "ok",
            },
        )

    result = artifact_x_articles.fetch_x_articles(
        db_path=db,
        limit=1,
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    assert result["failed_terminal"] == 1
    conn = artifacts.connect(db)
    fetch = conn.execute(
        "SELECT * FROM artifact_fetch WHERE fetch_policy = ?",
        (artifact_x_articles.FETCH_POLICY,),
    ).fetchone()
    conn.close()
    assert fetch["error_code"] == artifact_fetch.PLACEHOLDER_ERROR_CODE
    assert fetch["raw_snapshot_ref"] is not None
    assert fetch["text_snapshot_ref"] is None


def test_x_article_fetch_retries_http_failure_and_preserves_both_attempts(
    tmp_path, monkeypatch
):
    db = tmp_path / "artifacts.db"
    _seed_x_article(db)
    monkeypatch.setattr(artifact_fetch, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(artifact_fetch, "TEXT_ROOT", tmp_path / "text")
    calls = 0

    def handler(_request: httpx.Request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, json={"status": "failed", "message": "busy"})
        return httpx.Response(
            200,
            json={
                "article": {
                    "title": "Recovered",
                    "preview_text": "preview",
                    "contents": [{"type": "unstyled", "text": "Recovered body."}],
                },
                "status": "success",
                "message": "ok",
            },
        )

    transport = httpx.MockTransport(handler)
    first = artifact_x_articles.fetch_x_articles(
        db_path=db, limit=1, api_key="test-key", transport=transport
    )
    second = artifact_x_articles.fetch_x_articles(
        db_path=db, limit=1, api_key="test-key", transport=transport
    )

    assert first["failed_retryable"] == 1
    assert first["estimated_provider_credits"] == 100
    assert second["success"] == 1
    assert second["estimated_provider_credits"] == 200
    assert calls == 2
    conn = artifacts.connect(db)
    attempts = conn.execute(
        """SELECT status, error_code, raw_snapshot_ref
           FROM artifact_fetch WHERE fetch_policy = ? ORDER BY attempt_number""",
        (artifact_x_articles.FETCH_POLICY,),
    ).fetchall()
    assert [(row["status"], row["error_code"]) for row in attempts] == [
        ("failed_retryable", "x_article_http_503"),
        ("success", None),
    ]
    assert all(row["raw_snapshot_ref"] for row in attempts)
    conn.close()


def test_x_article_ambiguous_post_mapping_is_terminal_without_provider_call(
    tmp_path,
):
    db = tmp_path / "artifacts.db"
    _seed_x_article(db, post_ids=("222", "333"))
    calls = 0

    def handler(_request: httpx.Request):
        nonlocal calls
        calls += 1
        raise AssertionError("ambiguous mappings must fail before provider retrieval")

    result = artifact_x_articles.fetch_x_articles(
        db_path=db,
        limit=1,
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    assert result["failed_terminal"] == 1
    assert result["provider_request_attempts"] == 0
    assert result["estimated_provider_credits"] == 0
    assert calls == 0
    conn = artifacts.connect(db)
    fetch = conn.execute(
        "SELECT * FROM artifact_fetch WHERE fetch_policy = ?",
        (artifact_x_articles.FETCH_POLICY,),
    ).fetchone()
    provider = conn.execute("SELECT * FROM artifact_x_article_fetch").fetchone()
    assert fetch["error_code"] == "x_article_post_id_ambiguous"
    assert provider["request_made"] == 0
    assert provider["request_post_id"] is None
    conn.close()


def test_x_article_artifact_id_filter_is_exact_and_order_independent(
    tmp_path, monkeypatch
):
    db = tmp_path / "artifacts.db"
    first_id = _seed_x_article(db, article_id="111", post_ids=("222",))
    second_id = _seed_x_article(db, article_id="333", post_ids=("444",))
    excluded_id = _seed_x_article(db, article_id="555", post_ids=("666",))
    monkeypatch.setattr(artifact_fetch, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(artifact_fetch, "TEXT_ROOT", tmp_path / "text")
    requested_posts: list[str] = []

    def handler(request: httpx.Request):
        post_id = request.url.params["tweet_id"]
        requested_posts.append(post_id)
        return httpx.Response(
            200,
            json={
                "article": {
                    "title": f"Article {post_id}",
                    "contents": [
                        {"type": "unstyled", "text": f"Body for post {post_id}."}
                    ],
                },
                "status": "success",
                "message": "ok",
            },
        )

    transport = httpx.MockTransport(handler)
    first = artifact_x_articles.fetch_x_articles(
        db_path=db,
        artifact_ids=[second_id.upper(), first_id],
        api_key="test-key",
        transport=transport,
    )
    second = artifact_x_articles.fetch_x_articles(
        db_path=db,
        artifact_ids=[first_id, second_id],
        api_key="test-key",
        transport=transport,
    )

    assert first["expected_count"] == 2
    assert first["success"] == 2
    assert second["fetch_run_id"] == first["fetch_run_id"]
    assert second["reused"] is True
    assert sorted(requested_posts) == ["222", "444"]
    conn = artifacts.connect(db)
    fetched = {
        str(row["artifact_id"])
        for row in conn.execute(
            "SELECT artifact_id FROM artifact_fetch WHERE fetch_policy = ?",
            (artifact_x_articles.FETCH_POLICY,),
        ).fetchall()
    }
    assert fetched == {first_id, second_id}
    assert excluded_id not in fetched
    conn.close()


@pytest.mark.parametrize(
    "artifact_ids, message",
    [
        (["not-a-digest"], "64-character hexadecimal digest"),
        (["a" * 64, "A" * 64], "provided more than once"),
    ],
)
def test_x_article_artifact_id_filter_validates_ids(
    tmp_path, artifact_ids, message
):
    with pytest.raises(ValueError, match=message):
        artifact_x_articles.fetch_x_articles(
            db_path=tmp_path / "artifacts.db", artifact_ids=artifact_ids
        )


def test_x_article_artifact_id_filter_rejects_non_article_catalog_id(tmp_path):
    db = tmp_path / "artifacts.db"
    _seed_x_article(db)
    unknown_id = "f" * 64

    with pytest.raises(ValueError, match="not a catalogued X Article"):
        artifact_x_articles.fetch_x_articles(
            db_path=db, artifact_ids=[unknown_id], api_key="test-key"
        )


def _fetch_provenance_fixture(db: Path, tmp_path: Path, monkeypatch) -> str:
    artifact_id = _seed_x_article(db)
    monkeypatch.setattr(artifact_fetch, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(artifact_fetch, "TEXT_ROOT", tmp_path / "text")

    def handler(_request: httpx.Request):
        return httpx.Response(
            200,
            json={
                "article": {
                    "title": "Bound title",
                    "preview_text": "metadata only",
                    "contents": [
                        {"type": "unstyled", "text": "Exact body."},
                        {"type": "image", "url": "https://example.com/a.png"},
                    ],
                },
                "status": "success",
                "message": "ok",
            },
        )

    result = artifact_x_articles.fetch_x_articles(
        db_path=db,
        artifact_ids=[artifact_id],
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    assert result["success"] == 1
    return artifact_id


def test_x_article_provenance_is_exact_read_only_and_deterministic(
    tmp_path, monkeypatch
):
    db = tmp_path / "artifacts.db"
    artifact_id = _fetch_provenance_fixture(db, tmp_path, monkeypatch)

    first = artifact_x_articles.validate_x_article_provenance(
        db_path=db, artifact_ids=[artifact_id]
    )
    second = artifact_x_articles.validate_x_article_provenance(
        db_path=db, artifact_ids=(artifact_id.upper(),)
    )

    assert first == second
    assert first["schema_version"] == (
        artifact_x_articles.PROVENANCE_SCHEMA_VERSION
    )
    assert first["artifact_db"] == str(db.resolve())
    assert first["artifact_count"] == 1
    assert len(first["binding_sha256"]) == 64
    item = first["items"][0]
    assert item["artifact_id"] == artifact_id
    assert item["canonical_article_id"] == "111"
    assert item["canonical_article_url"] == "https://x.com/i/article/111"
    assert item["request_post_id"] == "222"
    assert item["mapping_error"] is None
    assert len(item["attempts"]) == 1
    attempt = item["attempts"][0]
    assert attempt["status"] == "success"
    assert attempt["provider"] == "twitterapi_io"
    assert attempt["endpoint"] == artifact_x_articles.ENDPOINT
    assert attempt["request_post_id"] == "222"
    assert attempt["canonical_article_id"] == "111"
    assert attempt["canonical_article_url"] == "https://x.com/i/article/111"
    assert attempt["request_made"] == 1
    assert attempt["estimated_provider_credits"] == 100
    assert attempt["provider_status"] == "success"
    assert attempt["provider_message"] == "ok"
    assert attempt["content_block_count"] == 2
    assert len(attempt["content_blocks_sha256"]) == 64
    assert Path(attempt["raw_snapshot_ref"]).is_file()
    assert Path(attempt["text_snapshot_ref"]).is_file()


@pytest.mark.parametrize(
    "field, value",
    [
        ("provider", "unbound-provider"),
        ("endpoint", "https://example.com/not-the-endpoint"),
        ("request_post_id", "999"),
        ("canonical_article_id", "999"),
        ("canonical_article_url", "https://x.com/i/article/999"),
        ("request_made", 0),
        ("estimated_provider_credits", 999),
    ],
)
def test_x_article_provenance_rejects_provider_mapping_drift(
    tmp_path, monkeypatch, field, value
):
    db = tmp_path / "artifacts.db"
    artifact_id = _fetch_provenance_fixture(db, tmp_path, monkeypatch)
    conn = artifacts.connect(db)
    conn.execute("PRAGMA ignore_check_constraints = ON")
    with conn:
        conn.execute(
            f"UPDATE artifact_x_article_fetch SET {field} = ?",  # noqa: S608
            (value,),
        )
    conn.close()

    with pytest.raises(ValueError, match=f"binding drift: {field}"):
        artifact_x_articles.validate_x_article_provenance(
            db_path=db, artifact_ids=[artifact_id]
        )


@pytest.mark.parametrize(
    "field, value",
    [
        ("provider_status", "failed"),
        ("provider_message", "not the stored response"),
        ("content_block_count", 99),
        ("content_blocks_sha256", "0" * 64),
    ],
)
def test_x_article_provenance_rejects_response_projection_drift(
    tmp_path, monkeypatch, field, value
):
    db = tmp_path / "artifacts.db"
    artifact_id = _fetch_provenance_fixture(db, tmp_path, monkeypatch)
    conn = artifacts.connect(db)
    with conn:
        conn.execute(
            f"UPDATE artifact_x_article_fetch SET {field} = ?",  # noqa: S608
            (value,),
        )
    conn.close()

    with pytest.raises(ValueError, match=f"binding drift: {field}"):
        artifact_x_articles.validate_x_article_provenance(
            db_path=db, artifact_ids=[artifact_id]
        )


def test_x_article_provenance_rejects_snapshot_drift(tmp_path, monkeypatch):
    db = tmp_path / "artifacts.db"
    artifact_id = _fetch_provenance_fixture(db, tmp_path, monkeypatch)
    conn = artifacts.connect(db)
    snapshot = Path(
        conn.execute(
            "SELECT text_snapshot_ref FROM artifact_fetch"
        ).fetchone()["text_snapshot_ref"]
    )
    conn.close()
    snapshot.write_text("tampered body\n")

    with pytest.raises(ValueError, match="text snapshot hash drift"):
        artifact_x_articles.validate_x_article_provenance(
            db_path=db, artifact_ids=[artifact_id]
        )


def test_x_article_provenance_binds_terminal_mapping_error(tmp_path):
    db = tmp_path / "artifacts.db"
    artifact_id = _seed_x_article(db, post_ids=("222", "333"))
    result = artifact_x_articles.fetch_x_articles(
        db_path=db,
        artifact_ids=[artifact_id],
        api_key="unused",
        transport=httpx.MockTransport(
            lambda _request: pytest.fail("mapping failure must not call provider")
        ),
    )
    assert result["failed_terminal"] == 1

    provenance = artifact_x_articles.validate_x_article_provenance(
        db_path=db, artifact_ids=[artifact_id]
    )
    item = provenance["items"][0]
    assert item["mapping_error"] == "x_article_post_id_ambiguous"
    assert item["request_post_id"] is None
    assert item["attempts"][0]["status"] == "failed_terminal"
    assert item["attempts"][0]["error_code"] == (
        "x_article_post_id_ambiguous"
    )
    assert item["attempts"][0]["request_made"] == 0
    assert item["attempts"][0]["estimated_provider_credits"] == 0

    conn = artifacts.connect(db)
    with conn:
        conn.execute(
            "UPDATE artifact_fetch SET error_code = 'x_article_post_id_missing'"
        )
    conn.close()
    with pytest.raises(ValueError, match="binding drift: error_code"):
        artifact_x_articles.validate_x_article_provenance(
            db_path=db, artifact_ids=[artifact_id]
        )


def test_x_article_cli_passes_repeatable_exact_filter_and_keeps_default_limit(
    tmp_path, monkeypatch, capsys
):
    calls: list[dict] = []

    def fake_fetch_x_articles(**kwargs):
        calls.append(kwargs)
        return {"fetch_run_id": "fixture", "expected_count": 0}

    monkeypatch.setattr(
        artifact_x_articles, "fetch_x_articles", fake_fetch_x_articles
    )
    first_id = "a" * 64
    second_id = "b" * 64
    assert artifacts.main(
        [
            "fetch-x-articles",
            "--db",
            str(tmp_path / "artifacts.db"),
            "--artifact-id",
            first_id,
            "--artifact-id",
            second_id,
            "--json",
        ]
    ) == 0
    capsys.readouterr()
    assert artifacts.main(
        [
            "fetch-x-articles",
            "--db",
            str(tmp_path / "artifacts.db"),
            "--json",
        ]
    ) == 0
    capsys.readouterr()

    assert calls[0]["artifact_ids"] == [first_id, second_id]
    assert calls[0]["limit"] is None
    assert calls[1]["artifact_ids"] is None
    assert calls[1]["limit"] == 20
