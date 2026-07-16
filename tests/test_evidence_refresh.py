import json
import sqlite3
from pathlib import Path

import httpx

from fli import evidence_refresh


class _Client:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_refresh_evidence_runs_cached_pipeline_in_dependency_order(monkeypatch):
    calls: list[tuple[str, object]] = []
    client = _Client()

    monkeypatch.setattr(
        evidence_refresh.x_content,
        "create_client",
        lambda **kwargs: (calls.append(("client", kwargs)), client)[1],
    )
    monkeypatch.setattr(
        evidence_refresh.x_daily_collection,
        "execute_collection",
        lambda **kwargs: (
            calls.append(("collection", kwargs)),
            {"status": "complete", "failures": 0, "unfinished_accounts": 0},
        )[1],
    )
    monkeypatch.setattr(
        evidence_refresh.signal_feed,
        "materialize",
        lambda **kwargs: (calls.append(("feed", kwargs)), {"run_id": "feed-1"})[1],
    )
    monkeypatch.setattr(
        evidence_refresh.signal_events,
        "materialize",
        lambda **kwargs: (calls.append(("events", kwargs)), {"run_id": "event-1"})[1],
    )
    monkeypatch.setattr(
        evidence_refresh.signal_events,
        "publish",
        lambda **kwargs: (calls.append(("publish", kwargs)), {"run_id": "event-1"})[1],
    )
    monkeypatch.setattr(
        evidence_refresh.artifacts,
        "import_feed_envelopes",
        lambda **kwargs: (calls.append(("catalog", kwargs)), {"artifact_count": 3})[1],
    )
    monkeypatch.setattr(
        evidence_refresh.artifact_arxiv,
        "fetch_arxiv_metadata",
        lambda **kwargs: (calls.append(("arxiv", kwargs)), {"success": 1})[1],
    )
    monkeypatch.setattr(
        evidence_refresh.artifact_fetch,
        "fetch_cohort",
        lambda **kwargs: (calls.append(("content", kwargs)), {"success": 2})[1],
    )
    monkeypatch.setattr(
        evidence_refresh.artifact_x_articles,
        "fetch_x_articles",
        lambda **kwargs: (calls.append(("x_articles", kwargs)), {"success": 1})[1],
    )
    monkeypatch.setattr(
        evidence_refresh.artifact_fetch,
        "recover_with_jina_reader",
        lambda **kwargs: (calls.append(("fallback", kwargs)), {"success": 0})[1],
    )
    monkeypatch.setattr(
        evidence_refresh,
        "_optimize_stores",
        lambda stores: (calls.append(("optimize", stores)), {"status": "ok"})[1],
    )
    monkeypatch.setattr(
        evidence_refresh,
        "_warm_evidence_views",
        lambda **kwargs: (calls.append(("warm", kwargs)), {"status": "ready"})[1],
    )

    result = evidence_refresh.refresh_evidence(
        through="2026-07-13",
        days=9,
        workers=48,
        artifact_limit=60,
        x_article_limit=10,
        key_file=Path("key.txt"),
    )

    assert [name for name, _ in calls] == [
        "client",
        "collection",
        "feed",
        "events",
        "publish",
        "catalog",
        "content",
        "arxiv",
        "x_articles",
        "fallback",
        "optimize",
        "warm",
    ]
    assert calls[1][1]["start_day"].isoformat() == "2026-07-05"
    assert calls[1][1]["workers"] == 48
    assert calls[6][1]["limit"] == 60
    assert calls[8][1]["limit"] == 10
    assert result["range"] == {
        "start_day": "2026-07-05",
        "end_day": "2026-07-13",
    }
    assert client.closed is True


def test_refresh_evidence_can_rebuild_without_collection_or_content(monkeypatch):
    monkeypatch.setattr(
        evidence_refresh.signal_feed,
        "materialize",
        lambda **kwargs: {"run_id": "feed-1"},
    )
    monkeypatch.setattr(
        evidence_refresh.signal_events,
        "materialize",
        lambda **kwargs: {"run_id": "event-1"},
    )
    monkeypatch.setattr(
        evidence_refresh.signal_events,
        "publish",
        lambda **kwargs: {"run_id": "event-1"},
    )
    monkeypatch.setattr(
        evidence_refresh.artifacts,
        "import_feed_envelopes",
        lambda **kwargs: {"artifact_count": 3},
    )
    monkeypatch.setattr(
        evidence_refresh, "_optimize_stores", lambda stores: {"status": "ok"}
    )
    monkeypatch.setattr(
        evidence_refresh,
        "_warm_evidence_views",
        lambda **kwargs: {"status": "ready"},
    )

    result = evidence_refresh.refresh_evidence(
        through="2026-07-13",
        collect=False,
        artifact_limit=0,
        x_article_limit=0,
        reader_fallback=False,
    )

    assert result["collection"]["status"] == "skipped"
    assert result["content_fetch"] is None
    assert result["x_article_fetch"] is None
    assert result["reader_fallback"] is None


def test_refresh_evidence_proves_incremental_collection_covers_publication(
    monkeypatch, tmp_path
):
    calls: list[tuple[str, object]] = []
    client = _Client()
    manifest = tmp_path / "collection.db"
    conn = sqlite3.connect(manifest)
    conn.execute(
        """CREATE TABLE collection_run (
               run_id TEXT PRIMARY KEY,
               collection_contract TEXT NOT NULL,
               horizon_start_day TEXT NOT NULL,
               horizon_end_day TEXT NOT NULL,
               cohort_sha256 TEXT NOT NULL,
               status TEXT NOT NULL
           )"""
    )
    conn.executemany(
        "INSERT INTO collection_run VALUES (?, ?, ?, ?, ?, 'complete')",
        [
            ("old", "contract", "2026-07-05", "2026-07-13", "cohort"),
            ("new", "contract", "2026-07-13", "2026-07-15", "cohort"),
        ],
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(evidence_refresh.x_content, "create_client", lambda **_: client)
    monkeypatch.setattr(
        evidence_refresh.x_daily_collection,
        "execute_collection",
        lambda **kwargs: (
            calls.append(("collection", kwargs)),
            {
                "run_id": "new",
                "status": "complete",
                "contract": "contract",
                "cohort_sha256": "cohort",
                "failures": 0,
                "unfinished_accounts": 0,
            },
        )[1],
    )
    monkeypatch.setattr(
        evidence_refresh.signal_feed,
        "materialize",
        lambda **kwargs: (calls.append(("feed", kwargs)), {"run_id": "feed-1"})[1],
    )
    monkeypatch.setattr(
        evidence_refresh.signal_events, "materialize", lambda **_: {"run_id": "event-1"}
    )
    monkeypatch.setattr(
        evidence_refresh.signal_events, "publish", lambda **_: {"run_id": "event-1"}
    )
    monkeypatch.setattr(
        evidence_refresh.artifacts,
        "import_feed_envelopes",
        lambda **_: {"artifact_count": 0},
    )
    monkeypatch.setattr(evidence_refresh, "_optimize_stores", lambda _: {})

    result = evidence_refresh.refresh_evidence(
        through="2026-07-15",
        days=11,
        collection_days=3,
        collection_db=manifest,
        artifact_limit=0,
        x_article_limit=0,
        reader_fallback=False,
        view_warmup=False,
    )

    assert calls[0][1]["start_day"].isoformat() == "2026-07-13"
    assert calls[1][1]["days"] == 11
    assert result["collection_range"] == {
        "start_day": "2026-07-13",
        "end_day": "2026-07-15",
    }
    assert result["collection_coverage"]["run_ids"] == ["old", "new"]


def test_refresh_evidence_rejects_collection_window_larger_than_publication():
    try:
        evidence_refresh.refresh_evidence(
            through="2026-07-15", days=3, collection_days=4
        )
    except ValueError as exc:
        assert str(exc) == "collection_days must be between 1 and days"
    else:
        raise AssertionError("expected invalid collection_days to fail")


def test_cli_returns_stable_json_contract(monkeypatch, capsys):
    received = {}

    def fake_refresh(**kwargs):
        received.update(kwargs)
        return {
            "collection": {"run_id": "collection-1", "provider_requests": 3},
            "publication": {"event_run_id": "event-1"},
        }

    monkeypatch.setattr(evidence_refresh, "refresh_evidence", fake_refresh)

    code = evidence_refresh.main(
        [
            "--through",
            "2026-07-15",
            "--days",
            "11",
            "--collection-days",
            "3",
            "--progress",
            "off",
            "--no-input",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert captured.err == ""
    assert payload["schema_version"] == "1.0"
    assert payload["command"] == "evidence-refresh"
    assert payload["status"] == "ok"
    assert payload["error"] is None
    assert set(payload["meta"]) == {"request_id", "duration_ms", "timestamp_utc"}
    assert received["days"] == 11
    assert received["collection_days"] == 3


def test_cli_validation_error_is_structured(capsys):
    code = evidence_refresh.main(
        [
            "--through",
            "2026-07-15",
            "--days",
            "3",
            "--collection-days",
            "4",
            "--progress",
            "off",
            "--no-input",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["status"] == "error"
    assert payload["error"] == {
        "code": "E_VALIDATION",
        "message": "collection_days must be between 1 and days",
        "retryable": False,
        "hint": "Check the requested dates, windows, paths, and numeric limits.",
    }


def test_refresh_evidence_fetches_all_supported_content_by_default(monkeypatch):
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(
        evidence_refresh.signal_feed,
        "materialize",
        lambda **kwargs: {"run_id": "feed-1"},
    )
    monkeypatch.setattr(
        evidence_refresh.signal_events,
        "materialize",
        lambda **kwargs: {"run_id": "event-1"},
    )
    monkeypatch.setattr(
        evidence_refresh.signal_events,
        "publish",
        lambda **kwargs: {"run_id": "event-1"},
    )
    monkeypatch.setattr(
        evidence_refresh.artifacts,
        "import_feed_envelopes",
        lambda **kwargs: {"artifact_count": 3},
    )
    monkeypatch.setattr(
        evidence_refresh.artifact_fetch,
        "fetch_all_supported",
        lambda **kwargs: (calls.append(("content", kwargs)), {"success": 2})[1],
    )
    monkeypatch.setattr(
        evidence_refresh.artifact_arxiv,
        "fetch_arxiv_metadata",
        lambda **kwargs: (calls.append(("arxiv", kwargs)), {"success": 1})[1],
    )
    monkeypatch.setattr(
        evidence_refresh.artifact_x_articles,
        "fetch_x_articles",
        lambda **kwargs: (calls.append(("x_articles", kwargs)), {"success": 1})[1],
    )
    monkeypatch.setattr(
        evidence_refresh.artifact_fetch,
        "recover_with_jina_reader",
        lambda **kwargs: {"success": 0},
    )
    monkeypatch.setattr(
        evidence_refresh, "_optimize_stores", lambda stores: {"status": "ok"}
    )
    monkeypatch.setattr(
        evidence_refresh,
        "_warm_evidence_views",
        lambda **kwargs: {"status": "ready"},
    )

    evidence_refresh.refresh_evidence(
        through="2026-07-13",
        collect=False,
        workers=24,
    )

    assert calls == [
        ("content", {"db_path": evidence_refresh.artifacts.DEFAULT_DB, "workers": 24}),
        ("arxiv", {"db_path": evidence_refresh.artifacts.DEFAULT_DB}),
        (
            "x_articles",
            {
                "db_path": evidence_refresh.artifacts.DEFAULT_DB,
                "limit": None,
                "key_file": evidence_refresh.sources.DEFAULT_TWITTERAPI_IO_KEY_FILE,
            },
        ),
    ]


def test_optimize_stores_reports_materialized_indexes(tmp_path):
    db = tmp_path / "indexed.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        "CREATE TABLE item (id INTEGER PRIMARY KEY, value TEXT);"
        "CREATE INDEX idx_item_value ON item(value);"
    )
    conn.close()

    result = evidence_refresh._optimize_stores({"feed": db})

    assert result["feed"]["status"] == "optimized"
    assert result["feed"]["index_count"] == 1
    assert result["feed"]["wal_checkpoint"]["busy"] == 0


def test_warm_evidence_views_warms_current_days_and_artifacts():
    requested: list[tuple[str, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        day = request.url.params.get("date")
        requested.append((request.url.path, day))
        if request.url.path == "/api/events/dates":
            return httpx.Response(
                200,
                json={
                    "run_id": "event-1",
                    "date_from": "2026-07-05",
                    "date_to": "2026-07-06",
                    "dates": [
                        {"day": "2025-01-01", "item_count": 1},
                        {"day": "2026-07-05", "item_count": 10},
                        {"day": "2026-07-06", "item_count": 11},
                    ],
                },
            )
        return httpx.Response(200, json={"available": True})

    result = evidence_refresh._warm_evidence_views(
        transport=httpx.MockTransport(handler)
    )

    assert result["status"] == "ready"
    assert result["event_run_id"] == "event-1"
    assert result["days_warmed"] == 2
    assert requested == [
        ("/api/events/dates", None),
        ("/api/events", "2026-07-05"),
        ("/api/events", "2026-07-06"),
        ("/api/artifacts/dates", None),
    ]
