import json
from pathlib import Path
import sqlite3

import httpx
import pytest

from fli.evidence.artifacts import fetch as artifact_fetch
from fli.evidence.artifacts import cli as artifact_cli
from fli.evidence.artifacts import store as artifacts
from fli.evidence.artifacts import urls as artifact_urls


def test_connect_migrates_v1_store_to_event_native_v2(tmp_path):
    db = tmp_path / "artifacts-v1.db"
    legacy_schema = (
        artifacts.SCHEMA.replace(artifacts.SCHEMA_VERSION, "artifact-store-v1")
        .replace("first_event_day", "first_envelope_day")
        .replace("last_event_day", "last_envelope_day")
        .replace("event_day", "envelope_day")
        .replace(
            "source_semantic_snapshot_sha256",
            "source_snapshot_content_sha256",
        )
    )
    conn = sqlite3.connect(db)
    conn.executescript(legacy_schema)
    conn.execute(
        """INSERT INTO artifact_import_run (
               import_run_id, schema_version, canonicalization_contract,
               source_feed_run_id, source_event_run_id, triage_runs_json,
               selection_policy, input_fingerprint, expected_candidate_count,
               accepted_count, excluded_count, failed_count, created_at,
               completed_at)
           VALUES ('legacy-import', 'artifact-store-v1', 'canonical-v1',
                   'feed', 'events', '{}',
                   'feed-envelope-primary-author-thread-artifacts-v1',
                   'fingerprint', 1, 1, 0, 0, 'created', 'completed')"""
    )
    conn.execute(
        """INSERT INTO artifact_import_candidate (
               candidate_id, import_run_id, envelope_day, event_id,
               source_rank, day_candidate_count, source_kind, source_provider,
               source_external_id, source_snapshot_sha256, source_url,
               disclosure_external_id, disclosure_snapshot_sha256,
               disclosure_url, disclosure_published_at, observed_url,
               expanded_url, candidate_source, title_hint, relation, decision,
               reason_code, artifact_id, created_at)
           VALUES ('legacy-candidate', 'legacy-import', '2026-07-15', 'event-1',
                   1, 100, 'x_post', 'provider', 'post-1', 'source-sha',
                   'https://x.com/a/status/1', 'post-1', 'disclosure-sha',
                   'https://x.com/a/status/1', 'published', 'https://t.co/a',
                   'https://example.com/a', 'entity', NULL, 'links_to',
                   'accepted', 'external_http_url', NULL, 'created')"""
    )
    conn.execute(
        """INSERT INTO artifact_fetch_run (
               fetch_run_id, schema_version, fetch_policy, selection_policy,
               input_fingerprint, expected_count, success_count,
               failed_retryable_count, failed_terminal_count, started_at,
               completed_at, status)
           VALUES ('legacy-fetch', 'artifact-store-v1', 'fetch-v1', 'explicit',
                   'fetch-fingerprint', 0, 0, 0, 0, 'started', 'completed',
                   'complete')"""
    )
    conn.commit()
    conn.close()

    assert artifacts.migrate_store(db) is True
    migrated = artifacts.connect(db)
    candidate = migrated.execute(
        "SELECT event_day, event_id FROM artifact_import_candidate"
    ).fetchone()
    versions = {
        str(row[0])
        for row in migrated.execute(
            "SELECT schema_version FROM artifact_import_run "
            "UNION SELECT schema_version FROM artifact_fetch_run"
        ).fetchall()
    }
    supplement_columns = {
        str(row["name"])
        for row in migrated.execute(
            "PRAGMA table_info(artifact_event_supplement)"
        ).fetchall()
    }
    migrated.close()

    assert dict(candidate) == {"event_day": "2026-07-15", "event_id": "event-1"}
    assert versions == {artifacts.SCHEMA_VERSION}
    assert "source_semantic_snapshot_sha256" in supplement_columns
    assert "source_snapshot_content_sha256" not in supplement_columns
    assert artifacts.migrate_store(db) is False


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
               (candidate_id, import_run_id, event_day, event_id,
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


def test_safe_get_rejects_navigation_redirect_target():
    def handler(request: httpx.Request):
        if request.url.path == "/author/researcher":
            return httpx.Response(301, headers={"Location": "/search"})
        return httpx.Response(
            200,
            headers={"Content-Type": "text/html"},
            content=b"<html><body>Changing search results</body></html>",
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler), trust_env=False
    )
    try:
        with pytest.raises(artifact_fetch.FetchFailure) as failure:
            artifact_fetch._safe_get(
                client,
                "https://example.com/author/researcher",
                resolver=_global_resolver,
            )
        assert failure.value.code == "final_url_search_navigation"
        assert failure.value.retryable is False
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


def test_fetch_rejects_placeholder_dominated_text_before_snapshot(
    tmp_path, monkeypatch
):
    db = tmp_path / "artifacts.db"
    _seed_artifact(db)
    monkeypatch.setattr(artifact_fetch, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(artifact_fetch, "TEXT_ROOT", tmp_path / "text")

    def handler(request: httpx.Request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(
            200,
            headers={"Content-Type": "text/plain; charset=utf-8"},
            content=(("\u2588" * 12 + " ") * 50 + "BY PUBLISHER").encode(),
        )

    result = artifact_fetch.fetch_cohort(
        db_path=db,
        limit=1,
        resolver=_global_resolver,
        transport=httpx.MockTransport(handler),
    )

    assert result["failed_terminal"] == 1
    conn = artifacts.connect(db)
    fetch = conn.execute("SELECT * FROM artifact_fetch").fetchone()
    conn.close()
    assert fetch["error_code"] == artifact_fetch.PLACEHOLDER_ERROR_CODE
    assert fetch["raw_snapshot_ref"] is not None
    assert fetch["text_snapshot_ref"] is None
    assert fetch["text_sha256"] is None


@pytest.mark.parametrize(
    "text",
    [
        "\u2588" * 99,
        ("\u2588" * 90) + ("valid prose " * 12),
        "\ufffd" * 99,
        "print('valid code')\n" + ("# \u2588 rendered progress bar\n" * 20),
    ],
)
def test_placeholder_validation_keeps_short_or_mixed_text(text):
    assert artifact_fetch.extracted_text_issue(text) is None


@pytest.mark.parametrize(
    ("title", "url", "text"),
    [
        (
            "Just a moment...",
            "https://example.com/paper",
            "Performing security verification. This website uses a security "
            "service to protect against malicious bots. Please wait.",
        ),
        (
            "Google Forms: Sign-in",
            "https://docs.google.com/forms/d/e/example/viewform",
            "Sign in to continue with Google Forms. Use your email or phone to "
            "continue with this protected form.",
        ),
        (
            "Vercel Security Checkpoint",
            "https://example.vercel.app/report",
            "Vercel Security Checkpoint. Complete the check below to continue "
            "to the requested deployment.",
        ),
        (
            "Repository",
            "https://github.com/example/repository",
            "There was an error while loading. Please reload this page. " * 3,
        ),
        (
            "Video",
            "https://www.youtube.com/watch?v=example",
            "About Press Copyright Contact us Creators Advertise Developers " * 3,
        ),
        (
            "Not available in your region",
            "https://example.com/announcement",
            "This page isn't yet available in your region. Please check back "
            "later for availability.",
        ),
        (
            "Bloomberg - Are you a robot?",
            "https://www.bloomberg.com/news/articles/example",
            "We've detected unusual activity from your computer network. "
            "Click the box below to let us know you're not a robot.",
        ),
        (
            "Blocked",
            "https://www.reddit.com/r/MachineLearning/comments/example",
            "You've been blocked by network security. If you think you've "
            "been blocked by mistake, file a ticket below.",
        ),
        (
            "Research notes",
            "https://example.notion.site/research",
            "JavaScript must be enabled in order to use Notion. Please enable "
            "JavaScript to continue.",
        ),
        (
            "Maps",
            "https://consent.google.com/m?continue=https://maps.google.com",
            "Bevor Sie zu Google Maps weitergehen. Wir verwenden Cookies und "
            "Daten, um Google-Dienste bereitzustellen.",
        ),
        (
            "Welcome back - OpenAI",
            "https://chatgpt.com/yubikey",
            "Welcome back. Email address. Continue. Or continue with Google, "
            "Microsoft Account, Apple, or phone.",
        ),
        (
            "Sign in required",
            "https://example.chatgpt.site/",
            "You're almost in. This site uses ChatGPT to securely sign you in. "
            "Continue with ChatGPT.",
        ),
        (
            "ChatGPT",
            "https://chatgpt.com/",
            "Get responses tailored to you. Log in to get answers based on "
            "saved chats and preferences.",
        ),
    ],
)
def test_content_validation_rejects_non_content_shells(title, url, text):
    issue = artifact_fetch.extracted_text_issue(
        text,
        title=title,
        final_url=url,
    )

    assert issue is not None
    assert issue[0] == artifact_fetch.NON_CONTENT_ERROR_CODE


def test_content_validation_rejects_control_heavy_garbled_text():
    text = ("\x00\x01\x02\x03\x04\x05" + "\u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a") * 100

    issue = artifact_fetch.extracted_text_issue(text)

    assert issue is not None
    assert issue[0] == artifact_fetch.GARBLED_TEXT_ERROR_CODE


def test_content_validation_keeps_legitimate_short_mixed_content():
    text = (
        "We released EdgeBench today. It evaluates inference latency across "
        "three accelerators, includes the benchmark code, and reports the exact "
        "measurement protocol."
    )

    assert artifact_fetch.extracted_text_issue(
        text,
        title="EdgeBench: reproducible inference measurements",
        final_url="https://example.com/edgebench",
    ) is None


def test_content_validation_keeps_substantive_javascript_discussion():
    text = (
        "JavaScript must be enabled for the interactive demo, but the paper "
        "reports a 17% latency reduction across six evaluated models. " * 12
    )

    assert artifact_fetch.extracted_text_issue(
        text,
        title="Measured serving latency results",
        final_url="https://example.com/research/serving-latency",
    ) is None


def test_extract_content_rejects_empty_html_without_raising():
    result = artifact_fetch.extract_content(
        b"",
        content_type="text/html",
        charset="utf-8",
        final_url="https://example.com/empty",
        artifact_kind="other",
    )

    assert result.success is False
    assert result.error_code == "extraction_empty_or_client_rendered"


def test_extract_content_uses_scoped_sec_archives_fallback():
    body = b"""<DOCUMENT><TYPE>EX-99.1<SEQUENCE>2<FILENAME>filing.htm
    <DESCRIPTION>EXHIBIT 99.1<TEXT><HTML><HEAD><TITLE></TITLE></HEAD><BODY>
    <P STYLE="font: 10pt Times New Roman">TeraWulf entered into a 20-year lease
    with Anthropic.</P><P STYLE="font: 10pt Times New Roman">The campus will
    accommodate approximately 401 MW and the lease is expected to generate
    approximately $19 billion over the initial term.</P></BODY></HTML></TEXT>
    </DOCUMENT>"""

    result = artifact_fetch.extract_content(
        body,
        content_type="text/html",
        charset="utf-8",
        final_url=(
            "https://www.sec.gov/Archives/edgar/data/1083301/"
            "000110465926080583/tm2619468d1_ex99-1.htm"
        ),
        artifact_kind="other",
    )

    assert result.success is True
    assert result.extractor_contract == "html-sec-archives-lxml-v1"
    assert "20-year lease" in result.text
    assert "with Anthropic" in result.text
    assert "approximately $19 billion" in result.text


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://docs.google.com/document/d/document_123/edit?usp=sharing",
            "https://docs.google.com/document/d/document_123/export?format=txt",
        ),
        (
            "https://docs.google.com/document/u/1/d/document-456/view#heading=h.1",
            "https://docs.google.com/document/d/document-456/export?format=txt",
        ),
        ("https://docs.google.com/document/d/e/published-id/pub", None),
        ("https://docs.google.com/forms/d/e/form-id/viewform", None),
        ("https://example.com/document/d/document-id/edit", None),
    ],
)
def test_google_doc_text_export_url_is_narrow(url, expected):
    assert artifact_fetch._google_doc_text_export_url(url) == expected


def test_google_doc_editor_shell_is_rejected_by_content_validation():
    text = """Die Datei kann in Ihrem Browser nicht geöffnet werden, weil
    JavaScript nicht aktiviert ist. Aktivieren Sie JavaScript und laden Sie die
    Seite noch einmal. Research notes. Tab. Freigeben. Datei. Bearbeiten.
    Ansicht. Tools. Hilfe. Bedienungshilfen. Fehlerbehebung."""

    issue = artifact_fetch.extracted_text_issue(
        text,
        title="Research notes - Google Docs",
        final_url="https://docs.google.com/document/d/document-id/edit",
    )

    assert issue is not None
    assert issue[0] == artifact_fetch.NON_CONTENT_ERROR_CODE


def test_fetch_cohort_uses_public_google_doc_text_export_without_identity_churn(
    tmp_path, monkeypatch
):
    db = tmp_path / "artifacts.db"
    source_url = (
        "https://docs.google.com/document/d/document_123/edit?usp=sharing"
    )
    artifact_id = _seed_artifact(db, url=source_url, artifact_kind="other")
    monkeypatch.setattr(artifact_fetch, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(artifact_fetch, "TEXT_ROOT", tmp_path / "text")
    requested_urls: list[str] = []
    body = (
        "\ufeffPublic research notes\n\nThis is the actual Google document body, "
        "not the JavaScript editor shell.\n"
    ).encode("utf-8")

    def handler(request: httpx.Request):
        requested_urls.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.host == "docs.google.com":
            assert request.url.path == "/document/d/document_123/export"
            assert request.url.params["format"] == "txt"
            return httpx.Response(
                307,
                headers={
                    "Location": (
                        "https://doc-01-docstext.googleusercontent.com/"
                        "exported/document_123.txt"
                    )
                },
            )
        return httpx.Response(
            200,
            headers={
                "Content-Type": "text/plain; charset=utf-8",
                "Content-Disposition": (
                    "attachment; filename=\"ResearchNotes.txt\"; "
                    "filename*=UTF-8''Research%20Notes.txt"
                ),
            },
            content=body,
        )

    result = artifact_fetch.fetch_cohort(
        db_path=db,
        limit=1,
        resolver=_global_resolver,
        transport=httpx.MockTransport(handler),
    )

    assert result["success"] == 1
    assert requested_urls[1].endswith(
        "/document/d/document_123/export?format=txt"
    )
    conn = artifacts.connect(db)
    fetch = conn.execute("SELECT * FROM artifact_fetch").fetchone()
    stored_artifacts = conn.execute(
        "SELECT artifact_id, canonical_url FROM artifact"
    ).fetchall()
    conn.close()
    assert fetch["artifact_id"] == artifact_id
    assert fetch["final_url"] == source_url
    assert fetch["extractor_contract"] == (
        artifact_fetch.GOOGLE_DOCS_TEXT_EXPORT_EXTRACTOR
    )
    assert fetch["extracted_title"] == "Research Notes"
    assert len(stored_artifacts) == 1
    assert dict(stored_artifacts[0]) == {
        "artifact_id": artifact_id,
        "canonical_url": source_url,
    }
    text = Path(fetch["text_snapshot_ref"]).read_text(encoding="utf-8")
    assert text.startswith("Public research notes")
    assert "JavaScript editor shell" in text
    assert not text.startswith("\ufeff")


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


def test_claim_repairs_resurrected_redirect_source(tmp_path, monkeypatch):
    db = tmp_path / "artifacts.db"
    short_url = "https://go.example/launch"
    final_url = "https://example.com/launch"
    source_id = _seed_artifact(db, url=short_url)
    target_id = artifact_urls.artifact_id(final_url)
    monkeypatch.setattr(artifact_fetch, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(artifact_fetch, "TEXT_ROOT", tmp_path / "text")
    body = b"""<html><head><title>Launch</title></head><body><article>
    <h1>Launch</h1><p>This redirect target contains enough concrete public text
    for the bounded extractor to preserve as reusable evidence.</p></article></body></html>"""

    def handler(request: httpx.Request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.host == "go.example":
            return httpx.Response(302, headers={"Location": final_url})
        return httpx.Response(
            200, headers={"Content-Type": "text/html"}, content=body
        )

    first = artifact_fetch.fetch_cohort(
        db_path=db,
        limit=1,
        resolver=_global_resolver,
        transport=httpx.MockTransport(handler),
    )
    assert first["success"] == 1

    conn = artifacts.connect(db)
    fetch_run_id = str(
        conn.execute("SELECT fetch_run_id FROM artifact_fetch_run").fetchone()[0]
    )
    now = "2026-07-15T08:00:00+00:00"
    with conn:
        conn.execute(
            """INSERT INTO artifact
               (artifact_id, canonical_url, canonicalization_contract, host,
                artifact_kind, first_seen_at, last_seen_at, created_at, updated_at)
               VALUES (?, ?, ?, 'go.example', 'article', ?, ?, ?, ?)""",
            (
                source_id,
                short_url,
                artifact_urls.CANONICALIZATION_CONTRACT,
                now,
                now,
                now,
                now,
            ),
        )

    claimed = artifact_fetch._claim(
        conn,
        fetch_run_id=fetch_run_id,
        artifact_id=source_id,
        requested_url=short_url,
    )

    assert claimed is None
    assert conn.execute(
        "SELECT 1 FROM artifact WHERE artifact_id = ?", (source_id,)
    ).fetchone() is None
    assert conn.execute(
        "SELECT 1 FROM artifact WHERE artifact_id = ?", (target_id,)
    ).fetchone() is not None
    fetches = conn.execute(
        "SELECT artifact_id, status FROM artifact_fetch"
    ).fetchall()
    assert [(row["artifact_id"], row["status"]) for row in fetches] == [
        (target_id, "success")
    ]
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


def test_fetch_cohort_exact_artifact_id_does_not_widen_scope(tmp_path, monkeypatch):
    db = tmp_path / "artifacts.db"
    _seed_artifact(db)
    exact_url = "https://example.com/exact"
    exact_id = artifact_urls.artifact_id(exact_url)
    now = "2026-07-15T08:00:00+00:00"
    conn = artifacts.connect(db)
    with conn:
        conn.execute(
            """INSERT INTO artifact
               (artifact_id, canonical_url, canonicalization_contract, host,
                artifact_kind, first_seen_at, last_seen_at, created_at, updated_at)
               VALUES (?, ?, ?, 'example.com', 'other', ?, ?, ?, ?)""",
            (
                exact_id,
                exact_url,
                artifact_urls.CANONICALIZATION_CONTRACT,
                now,
                now,
                now,
                now,
            ),
        )
        conn.execute(
            """INSERT INTO artifact_event_supplement
               (supplement_id, contract, manifest_sha256, artifact_id,
                event_id, event_day, source_rank, day_candidate_count,
                source_triage_run_id, source_input_sha256,
                source_semantic_snapshot_sha256, evidence_role,
                source_published_at, rationale, reviewed_by, reviewed_at,
                created_at)
               VALUES ('supplement', ?, 'manifest-sha', ?, 'event-exact',
                       '2026-07-06', 50, 863, 'triage-run', 'input-sha',
                       'snapshot-sha', 'official_primary_source', '2026-07-06',
                       'Official source.', 'human-review', ?, ?)""",
            (artifacts.REVIEWED_SUPPLEMENT_CONTRACT, exact_id, now, now),
        )
    conn.close()
    monkeypatch.setattr(artifact_fetch, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(artifact_fetch, "TEXT_ROOT", tmp_path / "text")
    fetched_paths: list[str] = []
    body = b"""<html><body><article><h1>Exact source</h1><p>This exact artifact
    contains enough substantive public evidence for deterministic extraction
    without fetching any unrelated catalog row.</p></article></body></html>"""

    def handler(request: httpx.Request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        fetched_paths.append(request.url.path)
        return httpx.Response(200, headers={"Content-Type": "text/html"}, content=body)

    result = artifact_fetch.fetch_cohort(
        db_path=db,
        artifact_ids=[exact_id],
        resolver=_global_resolver,
        transport=httpx.MockTransport(handler),
    )

    assert result["success"] == 1
    assert fetched_paths == ["/exact"]
    conn = artifacts.connect(db)
    run = conn.execute(
        "SELECT selection_policy, expected_count FROM artifact_fetch_run"
    ).fetchone()
    assert run["selection_policy"] == artifact_fetch.EXPLICIT_SELECTION_POLICY
    assert run["expected_count"] == 1
    assert conn.execute(
        "SELECT artifact_id FROM artifact_fetch_run_item"
    ).fetchone()[0] == exact_id
    conn.close()


def test_explicit_fetch_rebuilds_items_pruned_with_reimported_artifact(
    tmp_path, monkeypatch
):
    db = tmp_path / "artifacts.db"
    artifact_url = "https://example.com/article"
    artifact_id = _seed_artifact(db, url=artifact_url)
    monkeypatch.setattr(artifact_fetch, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(artifact_fetch, "TEXT_ROOT", tmp_path / "text")
    body = b"""<html><head><title>Restored source</title></head><body><article>
    <h1>Restored source</h1><p>This public artifact contains enough concrete
    evidence to prove that a reimported catalog row is fetched again after its
    prior run membership and fetch outcome were removed by cascading deletes.
    </p></article></body></html>"""
    calls = {"artifact": 0}

    def handler(request: httpx.Request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls["artifact"] += 1
        return httpx.Response(
            200, headers={"Content-Type": "text/html"}, content=body
        )

    transport = httpx.MockTransport(handler)
    first = artifact_fetch.fetch_cohort(
        db_path=db,
        artifact_ids=[artifact_id],
        resolver=_global_resolver,
        transport=transport,
    )
    assert first["success"] == 1

    conn = artifacts.connect(db)
    now = "2026-07-15T08:00:00+00:00"
    with conn:
        conn.execute("DELETE FROM artifact WHERE artifact_id = ?", (artifact_id,))
        assert conn.execute(
            "SELECT COUNT(*) FROM artifact_fetch_run_item"
        ).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM artifact_fetch").fetchone()[0] == 0
        conn.execute(
            """INSERT INTO artifact
               (artifact_id, canonical_url, canonicalization_contract, host,
                artifact_kind, first_seen_at, last_seen_at, created_at, updated_at)
               VALUES (?, ?, ?, 'example.com', 'article', ?, ?, ?, ?)""",
            (
                artifact_id,
                artifact_url,
                artifact_urls.CANONICALIZATION_CONTRACT,
                now,
                now,
                now,
                now,
            ),
        )
        conn.execute(
            "UPDATE artifact_import_candidate SET artifact_id = ?",
            (artifact_id,),
        )
    conn.close()

    second = artifact_fetch.fetch_cohort(
        db_path=db,
        artifact_ids=[artifact_id],
        resolver=_global_resolver,
        transport=transport,
    )

    assert second["reused"] is False
    assert second["success"] == 1
    assert calls["artifact"] == 2
    conn = artifacts.connect(db)
    assert conn.execute(
        "SELECT COUNT(*) FROM artifact_fetch_run_item"
    ).fetchone()[0] == 1
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


def test_jina_reader_rejects_provider_shell_after_retrieval(tmp_path, monkeypatch):
    db = tmp_path / "artifacts.db"
    _seed_artifact(db)
    monkeypatch.setattr(artifact_fetch, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(artifact_fetch, "TEXT_ROOT", tmp_path / "text")
    _native_terminal_failure(db)

    def reader_handler(_request: httpx.Request):
        return httpx.Response(
            200,
            json={
                "code": 200,
                "status": 20000,
                "data": {
                    "title": "Just a moment...",
                    "url": "https://example.com/article",
                    "content": (
                        "# Just a moment...\n\nPerforming security verification. "
                        "This website uses a security service to protect against "
                        "malicious bots. Please wait while the check completes."
                    ),
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
    assert fetch["error_code"] == artifact_fetch.NON_CONTENT_ERROR_CODE
    assert fetch["raw_snapshot_ref"] is not None
    assert fetch["text_snapshot_ref"] is None
    conn.close()


def test_jina_reader_resumes_retryable_provider_failure(tmp_path, monkeypatch):
    db = tmp_path / "artifacts.db"
    _seed_artifact(db)
    monkeypatch.setattr(artifact_fetch, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(artifact_fetch, "TEXT_ROOT", tmp_path / "text")
    _native_terminal_failure(db)
    calls = 0

    def reader_handler(_request: httpx.Request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503)
        return httpx.Response(
            200,
            json={
                "code": 200,
                "status": 20000,
                "data": {
                    "title": "Recovered on retry",
                    "url": "https://example.com/article",
                    "content": (
                        "# Recovered on retry\n\nThe second Reader attempt returned "
                        "a substantive public artifact while preserving the "
                        "first retryable attempt for operational audit."
                    ),
                },
            },
        )

    transport = httpx.MockTransport(reader_handler)
    first = artifact_fetch.recover_with_jina_reader(
        db_path=db, api_key="", transport=transport
    )
    second = artifact_fetch.recover_with_jina_reader(
        db_path=db, api_key="", transport=transport
    )

    assert first["failed_retryable"] == 1
    assert second["success"] == 1
    assert calls == 2
    conn = artifacts.connect(db)
    attempts = conn.execute(
        """SELECT attempt_number, status FROM artifact_fetch
           WHERE fetch_policy = ? ORDER BY attempt_number""",
        (artifact_fetch.JINA_READER_POLICY,),
    ).fetchall()
    assert [(row["attempt_number"], row["status"]) for row in attempts] == [
        (1, "failed_retryable"),
        (2, "success"),
    ]
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

    assert artifact_cli.main(
        ["summary", "--db", str(db), "--json", "--no-input"]
    ) == 0
    success = json.loads(capsys.readouterr().out)
    assert success["schema_version"] == artifact_cli.RESULT_SCHEMA_VERSION
    assert success["command"] == "artifacts.summary"
    assert success["status"] == "ok"
    assert success["error"] is None
    assert set(success["meta"]) == {"request_id", "duration_ms", "timestamp_utc"}

    assert artifact_cli.main(["inspect", "--db", str(db), "--limit", "0"]) == 2
    failure = json.loads(capsys.readouterr().out)
    assert failure["command"] == "artifacts.inspect"
    assert failure["status"] == "error"
    assert failure["data"] is None
    assert failure["error"]["code"] == "E_VALIDATION"
    assert failure["error"]["retryable"] is False
    assert failure["error"]["hint"]


def test_revalidate_content_quarantines_stored_shell_idempotently(
    tmp_path, monkeypatch, capsys
):
    db = tmp_path / "artifacts.db"
    artifact_id = _seed_artifact(db)
    snapshot = tmp_path / "text" / "shell.txt"
    snapshot.parent.mkdir()
    snapshot.write_text(
        "Performing security verification. This website uses a security service "
        "to protect against malicious bots. Please wait while the check completes.",
        encoding="utf-8",
    )
    now = "2026-07-14T00:00:00+00:00"
    conn = artifacts.connect(db)
    with conn:
        conn.execute(
            """INSERT INTO artifact_fetch_run
               (fetch_run_id, schema_version, fetch_policy, selection_policy,
                input_fingerprint, expected_count, success_count,
                failed_retryable_count, failed_terminal_count, started_at,
                completed_at, status)
               VALUES ('fetch-run', ?, ?, 'test-selection', 'fingerprint',
                       1, 1, 0, 0, ?, ?, 'complete')""",
            (artifacts.SCHEMA_VERSION, artifact_fetch.FETCH_POLICY, now, now),
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
        conn.execute(
            """INSERT INTO artifact_fetch
               (fetch_id, fetch_run_id, artifact_id, fetch_policy,
                requested_url, request_key, status, attempt_number, started_at,
                completed_at, final_url, extractor_contract, extractor_version,
                extracted_title, text_sha256, text_snapshot_ref,
                text_char_count, text_truncated, retryable)
               VALUES ('fetch', 'fetch-run', ?, ?, 'https://example.com/article',
                       'request', 'success', 1, ?, ?,
                       'https://example.com/article', 'test', '1',
                       'Just a moment...', 'sha', ?, 145, 0, 0)""",
            (artifact_id, artifact_fetch.FETCH_POLICY, now, now, str(snapshot)),
        )
        conn.execute(
            """UPDATE artifact SET title = 'Just a moment...',
                                      title_fetch_id = 'fetch'
               WHERE artifact_id = ?""",
            (artifact_id,),
        )
    conn.close()

    assert artifact_cli.main(
        ["revalidate-content", "--db", str(db), "--json", "--no-input"]
    ) == 0
    first = json.loads(capsys.readouterr().out)["data"]
    assert first["quarantined_count"] == 1
    assert first["by_error_code"] == {
        artifact_fetch.NON_CONTENT_ERROR_CODE: 1
    }
    assert artifact_cli.main(
        ["revalidate-content", "--db", str(db), "--json", "--no-input"]
    ) == 0
    second = json.loads(capsys.readouterr().out)["data"]
    assert second["quarantined_count"] == 0

    conn = artifacts.connect(db)
    fetch = conn.execute("SELECT * FROM artifact_fetch WHERE fetch_id = 'fetch'").fetchone()
    run = conn.execute(
        "SELECT * FROM artifact_fetch_run WHERE fetch_run_id = 'fetch-run'"
    ).fetchone()
    artifact = conn.execute(
        "SELECT title, title_fetch_id FROM artifact WHERE artifact_id = ?",
        (artifact_id,),
    ).fetchone()
    conn.close()
    assert fetch["status"] == "failed_terminal"
    assert fetch["text_snapshot_ref"] is None
    assert fetch["text_sha256"] is None
    assert fetch["error_code"] == artifact_fetch.NON_CONTENT_ERROR_CODE
    assert run["success_count"] == 0
    assert run["failed_terminal_count"] == 1
    assert artifact["title"] is None
    assert artifact["title_fetch_id"] is None


def test_artifact_cli_passes_repeatable_exact_native_fetch_filter(
    tmp_path, monkeypatch, capsys
):
    calls: list[dict] = []

    def fake_fetch_cohort(**kwargs):
        calls.append(kwargs)
        return {"fetch_run_id": "exact", "expected_count": 2}

    monkeypatch.setattr(artifact_fetch, "fetch_cohort", fake_fetch_cohort)
    first_id = "a" * 64
    second_id = "b" * 64
    assert artifact_cli.main(
        [
            "fetch",
            "--db",
            str(tmp_path / "artifacts.db"),
            "--artifact-id",
            second_id,
            "--artifact-id",
            first_id,
            "--json",
            "--no-input",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "ok"
    assert calls == [
        {
            "db_path": tmp_path / "artifacts.db",
            "limit": 30,
            "artifact_ids": [second_id, first_id],
        }
    ]

    assert artifact_cli.main(
        [
            "fetch",
            "--limit",
            "1",
            "--artifact-id",
            first_id,
            "--json",
        ]
    ) == 2
    failure = json.loads(capsys.readouterr().out)
    assert failure["error"]["code"] == "E_VALIDATION"
    assert "cannot be combined" in failure["error"]["message"]


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
