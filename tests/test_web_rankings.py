import sqlite3

from fastapi.testclient import TestClient

from fli import following_rankings
from fli.web import rankings as rankings_store
from fli.web.app import app


client = TestClient(app)


def _ranking_fixture(tmp_path, monkeypatch):
    derived_root = tmp_path / "derived"
    analysis_dir = derived_root / "fixture"
    analysis_dir.mkdir(parents=True)
    analysis_db = analysis_dir / "analysis.db"
    conn = sqlite3.connect(analysis_db)
    conn.executescript(following_rankings.SCHEMA)
    conn.execute(
        """INSERT INTO analysis_context
           (context_id, schema_version, snapshot_id, cohort_sha256,
            snapshot_db_sha256, snapshot_checkpoint_commit,
            snapshot_checkpoint_db_sha256, registry_checkpoint_commit,
            registry_db_sha256, created_at)
           VALUES ('context', ?, 'fixture', 'cohort', 'snapshot', 'snapshot-git',
                   'snapshot-registry', 'registry-git', 'registry',
                   '2026-07-12T08:00:00+00:00')""",
        [following_rankings.ANALYSIS_SCHEMA_VERSION],
    )
    conn.executemany(
        """INSERT INTO graph_node
           (context_id, x_id, handle, display_name, followers_count,
            registry_state, entity_id, entity_kind, entity_name)
           VALUES ('context', ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            ("source", "source", "Source", 100, "active", 1, "person", "Source"),
            ("target", "target", "Target", 200, "unknown", None, None, None),
        ],
    )
    conn.executemany(
        """INSERT INTO ranking_run
           (run_id, context_id, algorithm, parameters_json,
            eligible_source_account_count, eligible_source_entity_count,
            eligible_edge_count, eligible_vote_count, ranked_node_count,
            completed_at)
           VALUES (?, 'context', ?, ?, 2, 1, 3, 2, 2, ?)""",
        [
            (
                "overlap",
                following_rankings.OVERLAP_ALGORITHM,
                '{"algorithm":"overlap"}',
                "2026-07-12T08:01:00+00:00",
            ),
            (
                "pagerank",
                following_rankings.PAGERANK_ALGORITHM,
                '{"algorithm":"pagerank"}',
                "2026-07-12T08:02:00+00:00",
            ),
        ],
    )
    conn.executemany(
        """INSERT INTO ranking_result
           (run_id, x_id, position, score_rank, score,
            cohort_follow_count, cohort_follow_share)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            ("overlap", "target", 1, 1, 2.0, 2, 1.0),
            ("overlap", "source", 2, 2, 1.0, 1, 0.5),
            ("pagerank", "source", 1, 1, 0.9, 1, 0.5),
            ("pagerank", "target", 2, 2, 0.1, 2, 1.0),
        ],
    )
    conn.commit()
    conn.close()

    raw_root = tmp_path / "raw"
    snapshot_dir = raw_root / "fixture"
    snapshot_dir.mkdir(parents=True)
    snapshot = sqlite3.connect(snapshot_dir / "snapshot.db")
    snapshot.execute(
        "CREATE TABLE edge (source_x_id TEXT NOT NULL, target_x_id TEXT NOT NULL)"
    )
    snapshot.execute("INSERT INTO edge VALUES ('source', 'target')")
    snapshot.commit()
    snapshot.close()

    monkeypatch.setattr(rankings_store, "DEFAULT_DERIVED_ROOT", derived_root)
    monkeypatch.setattr(rankings_store, "RAW_FOLLOWING_ROOT", raw_root)


def test_rankings_api_reads_current_schema_and_prefers_overlap(tmp_path, monkeypatch):
    _ranking_fixture(tmp_path, monkeypatch)

    response = client.get("/api/rankings?limit=10")

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["run"] == {
        "algorithm": following_rankings.OVERLAP_ALGORITHM,
        "snapshot_id": "fixture",
        "completed_at": "2026-07-12T08:01:00+00:00",
        "sources": 2,
        "edges": 3,
        "ranked_accounts": 2,
        "active_accounts": 1,
        "unknown_accounts": 1,
    }
    assert [node["rank"] for node in payload["nodes"]] == [1, 2]
    assert payload["nodes"][0]["x_id"] == "target"


def test_ranking_followers_api_uses_current_position_column(tmp_path, monkeypatch):
    _ranking_fixture(tmp_path, monkeypatch)

    response = client.get("/api/rankings/followers/target")

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["total"] == 1
    assert payload["followers"] == [
        {
            "x_id": "source",
            "handle": "source",
            "display_name": "Source",
            "entity_name": "Source",
            "rank": 2,
            "cohort_follow_count": 1,
        }
    ]
