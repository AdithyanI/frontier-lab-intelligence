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
