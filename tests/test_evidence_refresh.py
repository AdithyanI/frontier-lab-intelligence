from pathlib import Path

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
        "x_articles",
        "fallback",
    ]
    assert calls[1][1]["start_day"].isoformat() == "2026-07-05"
    assert calls[1][1]["workers"] == 48
    assert calls[6][1]["limit"] == 60
    assert calls[7][1]["limit"] == 10
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
