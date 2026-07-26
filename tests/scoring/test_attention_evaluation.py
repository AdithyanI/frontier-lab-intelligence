import json
import sqlite3

from fli.scoring import evaluation


def _event(
    *,
    event_id: str,
    rank: int,
    votes: int,
    layer: int,
    relevant: bool | None = None,
) -> evaluation.ReplayedEvent:
    return evaluation.ReplayedEvent(
        day="2026-07-05",
        event_id=event_id,
        daily_rank=rank,
        trusted_votes=votes,
        decided_at_layer=layer,
        relevant=relevant,
        baseline_rank=rank if relevant is not None else None,
    )


def test_vote_buckets_preserve_counts_and_censored_hit_rates():
    rows = [
        _event(event_id="zero", rank=1, votes=0, layer=4, relevant=None),
        _event(event_id="one-kept", rank=2, votes=1, layer=3, relevant=True),
        _event(event_id="one-drop", rank=3, votes=1, layer=2, relevant=False),
        _event(event_id="two", rank=4, votes=2, layer=1, relevant=True),
        _event(event_id="four", rank=5, votes=4, layer=1, relevant=True),
        _event(event_id="five", rank=6, votes=5, layer=1, relevant=False),
    ]

    buckets = evaluation._vote_bucket_stats(rows)

    assert buckets["0"] == {
        "event_count": 1,
        "share": 0.166667,
        "labeled_count": 0,
        "relevant_count": 0,
        "hit_rate": None,
    }
    assert buckets["1"]["event_count"] == 2
    assert buckets["1"]["hit_rate"] == 0.5
    assert buckets["2"]["hit_rate"] == 1.0
    assert buckets["3-4"]["event_count"] == 1
    assert buckets["5+"]["hit_rate"] == 0.0


def test_layer_attribution_reports_every_layer_and_share():
    rows = [
        _event(event_id="a", rank=1, votes=3, layer=1),
        _event(event_id="b", rank=2, votes=2, layer=1),
        _event(event_id="c", rank=3, votes=2, layer=2),
        _event(event_id="d", rank=4, votes=1, layer=5),
    ]

    layers = evaluation._layer_attribution(rows)

    assert layers["1"] == {
        "name": "trusted_votes",
        "event_count": 2,
        "share": 0.5,
    }
    assert layers["2"]["event_count"] == 1
    assert layers["3"]["event_count"] == 0
    assert layers["4"]["event_count"] == 0
    assert layers["5"]["event_count"] == 1


def test_saved_days_join_historical_labels_to_current_event_projection(
    tmp_path, monkeypatch
):
    run_dir = tmp_path / "routing-run"
    run_dir.mkdir()
    db_path = run_dir / "routing.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
            CREATE TABLE run_meta (
                singleton INTEGER PRIMARY KEY,
                day TEXT NOT NULL,
                prompt_version TEXT NOT NULL,
                rank_version TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        CREATE TABLE routing_item (
            event_id TEXT PRIMARY KEY,
            feed_rank INTEGER NOT NULL,
            ai_engineering_relevant INTEGER NOT NULL,
            investment_relevant INTEGER NOT NULL,
            status TEXT NOT NULL
        );
            INSERT INTO run_meta VALUES (
                1, '2026-07-05', 'audience-routing-v9', 'daily-rank-v2',
                '2026-07-18T20:08:51+00:00'
            );
        INSERT INTO routing_item VALUES ('event-1', 7, 1, 0, 'complete');
        INSERT INTO routing_item VALUES ('missing-event', 8, 0, 0, 'complete');
        """
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(
        evaluation.event_store,
        "dates_payload",
        lambda: {
            "available": True,
            "dates": [{"day": "2026-07-05", "item_count": 2}],
        },
    )
    captured = {}

    def events_payload(**kwargs):
        captured.update(kwargs)
        return {
            "available": True,
            "items": [
                {
                    "event_id": "event-1",
                    "daily_rank": 1,
                    "rank_components": {
                        "version": "daily-rank-v2",
                        "trusted_votes": 3,
                        "decided_at_layer": 1,
                    },
                },
                {
                    "event_id": "event-2",
                    "daily_rank": 2,
                    "rank_components": {
                        "version": "daily-rank-v2",
                        "trusted_votes": 1,
                        "decided_at_layer": 2,
                    },
                },
            ],
        }

    monkeypatch.setattr(evaluation.event_store, "events_payload", events_payload)

    days = evaluation.load_saved_days(routing_root=tmp_path)
    replay = days["2026-07-05"]

    assert captured["day"] == "2026-07-05"
    assert "event_run_id" not in captured
    assert replay.routing_label_count == 2
    assert replay.unmatched_label_count == 1
    assert replay.events[0].event_id == "event-1"
    assert replay.events[0].relevant is True
    assert replay.events[0].baseline_rank == 7
    assert replay.events[1].relevant is None


def test_evaluation_payload_aggregates_days_and_top_100(monkeypatch, tmp_path):
    first = evaluation.ReplayedDay(
        day="2026-07-05",
        events=(
            _event(event_id="a", rank=1, votes=2, layer=1, relevant=True),
            _event(event_id="b", rank=2, votes=1, layer=2, relevant=False),
        ),
        routing_label_count=2,
        unmatched_label_count=0,
    )
    second_event = evaluation.ReplayedEvent(
        day="2026-07-06",
        event_id="c",
        daily_rank=1,
        trusted_votes=5,
        decided_at_layer=3,
        relevant=None,
        baseline_rank=None,
    )
    second = evaluation.ReplayedDay(
        day="2026-07-06",
        events=(second_event,),
        routing_label_count=0,
        unmatched_label_count=0,
    )
    monkeypatch.setattr(
        evaluation,
        "load_saved_days",
        lambda **_: {"2026-07-05": first, "2026-07-06": second},
    )

    payload = evaluation.evaluation_payload(routing_root=tmp_path)
    aggregate = payload["aggregate"]

    assert payload["rank_contract"]["version"] == "daily-rank-v2"
    assert payload["days"] == ["2026-07-05", "2026-07-06"]
    assert aggregate["day_count"] == 2
    assert aggregate["event_count"] == 3
    assert aggregate["top_100_event_count"] == 3
    assert aggregate["matched_label_count"] == 2
    assert aggregate["top_100_vote_buckets"]["1"]["event_count"] == 1
    assert aggregate["top_100_layer_attribution"]["3"]["event_count"] == 1


def test_cli_keeps_json_no_input_contract(monkeypatch, capsys):
    monkeypatch.setattr(
        evaluation,
        "evaluation_payload",
        lambda **_: {
            "rank_contract": {"version": "daily-rank-v2"},
            "aggregate": {},
        },
    )

    exit_code = evaluation.main(["evaluate", "--json", "--no-input"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["schema_version"] == "2.0"
    assert payload["command"] == "daily-rank.evaluate"
    assert payload["status"] == "ok"
    assert payload["data"]["rank_contract"]["version"] == "daily-rank-v2"
