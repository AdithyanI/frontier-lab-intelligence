import sqlite3

from fli.evidence.artifacts import store as artifacts


def _candidate(*, day: str, suffix: str) -> dict[str, object]:
    source_url = f"https://x.com/example/status/{suffix}"
    target_url = f"https://example.com/{suffix}"
    published_at = f"{day}T12:00:00+00:00"
    return {
        "event_day": day,
        "event_id": f"event-{suffix}",
        "source_rank": 1,
        "day_candidate_count": 1,
        "source_kind": "x_post",
        "source_provider": "twitterapi_io",
        "source_external_id": suffix,
        "source_snapshot_sha256": f"source-sha-{suffix}",
        "source_url": source_url,
        "disclosure_external_id": suffix,
        "disclosure_snapshot_sha256": f"source-sha-{suffix}",
        "disclosure_url": source_url,
        "disclosure_published_at": published_at,
        "source_published_at": published_at,
        "observed_url": target_url,
        "expanded_url": target_url,
        "candidate_source": "entity",
        "title_hint": "",
        "relation": "links_to",
        "forced_failure": None,
    }


def test_incremental_import_keeps_prior_day_catalog_rows(tmp_path, monkeypatch):
    artifact_db = tmp_path / "artifacts.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    feed_db.touch()
    events_db.touch()

    monkeypatch.setattr(
        artifacts,
        "_published_context",
        lambda events_path, feed_path, *, event_run_id=None: (
            {
                "run_id": event_run_id,
                "created_at": "2026-07-30T00:00:00+00:00",
            },
            {"run_id": f"feed-{event_run_id}"},
        ),
    )
    monkeypatch.setattr(
        artifacts,
        "_iter_feed_candidates",
        lambda **kwargs: (
            [
                _candidate(
                    day=("2026-07-29" if kwargs["event_run_id"] == "event-a" else "2026-07-30"),
                    suffix=("a" if kwargs["event_run_id"] == "event-a" else "b"),
                )
            ],
            {
                "feed_run_id": kwargs["feed_run_id"],
                "event_run_id": kwargs["event_run_id"],
                "selection_policy": artifacts.PRIMARY_AUTHOR_SELECTION_POLICY,
                "candidate_days": {},
            },
        ),
    )

    first = artifacts.import_feed_events(
        db_path=artifact_db,
        feed_db=feed_db,
        events_db=events_db,
        event_run_id="event-a",
        replace_catalog=False,
    )
    second = artifacts.import_feed_events(
        db_path=artifact_db,
        feed_db=feed_db,
        events_db=events_db,
        event_run_id="event-b",
        replace_catalog=False,
    )
    replay = artifacts.import_feed_events(
        db_path=artifact_db,
        feed_db=feed_db,
        events_db=events_db,
        event_run_id="event-a",
        replace_catalog=False,
    )

    conn = sqlite3.connect(artifact_db)
    assert conn.execute("SELECT COUNT(*) FROM artifact_import_run").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM artifact").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM artifact_observation").fetchone()[0] == 2
    conn.close()
    assert len(first["accepted_artifact_ids"]) == 1
    assert len(second["accepted_artifact_ids"]) == 1
    assert replay["reused"] is True
    assert replay["accepted_artifact_ids"] == first["accepted_artifact_ids"]

