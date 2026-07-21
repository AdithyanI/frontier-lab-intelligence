import sqlite3

from fli.scoring import evaluation


def test_kendall_tau_reports_identical_and_reversed_orders():
    baseline = ["a", "b", "c", "d"]

    assert evaluation._kendall_tau(baseline, baseline) == 1.0
    assert evaluation._kendall_tau(baseline, list(reversed(baseline))) == -1.0


def test_candidate_grid_is_explicit_and_unique():
    formulas = evaluation.candidate_grid()

    assert len(formulas) == 18
    assert len({formula.version for formula in formulas}) == 18
    assert {formula.amplifier_cap for formula in formulas} == {8, 16, 32}
    assert {formula.support_knee for formula in formulas} == {100, 150, 300}


def test_labeled_days_replay_the_event_run_bound_to_routing(
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
            source_event_run_id TEXT NOT NULL,
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
            1, '2026-07-05', 'audience-routing-v9',
            'event-run-bound-to-labels', '2026-07-18T20:08:51+00:00'
        );
        INSERT INTO routing_item VALUES ('event-1', 1, 1, 0, 'complete');
        """
    )
    conn.commit()
    conn.close()

    captured = {}

    def events_payload(**kwargs):
        captured.update(kwargs)
        return {
            "available": True,
            "items": [
                {
                    "event_id": "event-1",
                    "day_member_count": 2,
                    "daily_score_basis": {
                        "attention_score": 0.75,
                        "published_at": "2026-07-05T12:00:00+00:00",
                        "score_components": {
                            "registry_amplifiers": 3,
                        },
                    },
                }
            ],
        }

    monkeypatch.setattr(evaluation.event_store, "events_payload", events_payload)

    days = evaluation.load_labeled_days(routing_root=tmp_path)

    assert captured["event_run_id"] == "event-run-bound-to-labels"
    assert days["2026-07-05"][0].event_id == "event-1"
