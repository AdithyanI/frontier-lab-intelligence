import json

from fli import artifacts, audience_routing_runs
from fli.web import events as event_store


def test_freeze_run_reads_ranked_evidence_without_triage(tmp_path, monkeypatch):
    artifact_db = tmp_path / "artifacts.db"
    artifacts.connect(artifact_db).close()
    item = {
        "event_id": "event-1",
        "daily_rank": 3,
        "snapshot_content_sha256": "snapshot-1",
        "root": {
            "post_id": "post-1",
            "author": {"handle": "alice"},
            "text": "A concrete primary-source result.",
            "url": "https://x.com/alice/status/post-1",
        },
        "evidence": [
            {
                "post_id": "post-2",
                "author": {"handle": "bob"},
                "text": "An independently authored reaction.",
                "relationship": "quote",
                "same_author_as_root": False,
            }
        ],
    }
    monkeypatch.setattr(
        event_store,
        "events_payload",
        lambda **_: {
            "available": True,
            "run": {"run_id": "event-run-1", "feed_run_id": "feed-run-1"},
            "items": [item],
        },
    )

    conn = audience_routing_runs.connect_run(tmp_path / "routing.db")
    count = audience_routing_runs.freeze_run(
        conn,
        run_id="direct-run-1",
        day="2026-07-12",
        top_ranked=1,
        event_id=None,
        artifact_db=artifact_db,
        model="gpt-5.6-luna",
        effort="medium",
    )

    meta = conn.execute("SELECT * FROM run_meta").fetchone()
    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(run_meta)").fetchall()
    }
    frozen = conn.execute("SELECT * FROM routing_item").fetchone()
    conn.close()

    assert count == 1
    assert meta["source_event_run_id"] == "event-run-1"
    assert meta["source_feed_run_id"] == "feed-run-1"
    assert meta["selection_kind"] == "top_ranked"
    assert meta["selection_limit"] == 1
    assert "source_triage_db" not in columns
    assert "source_triage_run_id" not in columns
    assert frozen["event_id"] == "event-1"
    assert frozen["feed_rank"] == 3
    packet = json.loads(frozen["packet_json"])
    assert [source["relation"] for source in packet["sources"]] == ["root", "quote"]

