from fli.evidence import events as signal_events
from fli.evidence import feed as signal_feed


def _insert_feed_run(conn, *, run_id: str, date_from: str, date_to: str) -> None:
    conn.execute(
        """INSERT INTO feed_run
           (run_id, schema_version, selection_contract, date_from, date_to,
            source_db, source_fingerprint, source_post_count,
            normalized_post_count, relation_count, opaque_target_count,
            shared_opaque_target_count, created_at)
           VALUES (?, ?, ?, ?, ?, 'raw.db', ?, 0, 0, 0, 0, 0, ?)""",
        (
            run_id,
            signal_feed.SCHEMA_VERSION,
            signal_feed.SELECTION_CONTRACT,
            date_from,
            date_to,
            f"fingerprint-{run_id}",
            f"{date_to}T23:59:59+00:00",
        ),
    )


def _insert_event_run(conn, *, run_id: str, feed_run_id: str) -> None:
    conn.execute(
        """INSERT INTO event_run
           (run_id, schema_version, clustering_contract, feed_run_id,
            feed_schema_version, input_fingerprint, cluster_count,
            member_count, link_count, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, ?)""",
        (
            run_id,
            signal_events.SCHEMA_VERSION,
            signal_events.CLUSTERING_CONTRACT,
            feed_run_id,
            signal_feed.SCHEMA_VERSION,
            f"fingerprint-{run_id}",
            "2026-07-30T00:00:00+00:00",
        ),
    )


def test_one_day_publication_does_not_move_older_days(tmp_path):
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"

    feed = signal_feed.connect(feed_db)
    _insert_feed_run(
        feed,
        run_id="historical-feed",
        date_from="2026-07-28",
        date_to="2026-07-29",
    )
    _insert_feed_run(
        feed,
        run_id="daily-feed",
        date_from="2026-07-30",
        date_to="2026-07-30",
    )
    feed.commit()
    feed.close()

    events = signal_events.connect(events_db)
    _insert_event_run(
        events,
        run_id="historical-events",
        feed_run_id="historical-feed",
    )
    _insert_event_run(events, run_id="daily-events", feed_run_id="daily-feed")
    events.commit()
    events.close()

    signal_events.publish(
        events_db=events_db,
        feed_db=feed_db,
        event_run_id="historical-events",
    )
    signal_events.publish(
        events_db=events_db,
        feed_db=feed_db,
        event_run_id="daily-events",
        days=["2026-07-30"],
    )

    events = signal_events.connect(events_db)
    assert signal_events.published_run(events, day="2026-07-28")["run_id"] == (
        "historical-events"
    )
    assert signal_events.published_run(events, day="2026-07-29")["run_id"] == (
        "historical-events"
    )
    assert signal_events.published_run(events, day="2026-07-30")["run_id"] == (
        "daily-events"
    )
    assert [
        (row["day"], row["run_id"]) for row in signal_events.published_days(events)
    ] == [
        ("2026-07-28", "historical-events"),
        ("2026-07-29", "historical-events"),
        ("2026-07-30", "daily-events"),
    ]
    events.close()

