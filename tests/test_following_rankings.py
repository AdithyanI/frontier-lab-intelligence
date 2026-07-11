import csv
import json
import sqlite3

import pytest

from fli import channels, following_rankings, following_snapshots, registry


def _snapshot(path, *, status="complete"):
    conn = sqlite3.connect(path)
    conn.executescript(following_snapshots.SCHEMA)
    conn.execute(
        """INSERT INTO snapshot_run
           (snapshot_id, cohort_id, cohort_sha256, cohort_manifest_path,
            checkpoint_commit, checkpoint_db_sha256, provider, endpoint,
            schema_version, created_at, completed_at, status, source_count)
           VALUES ('fixture', 'fixture-cohort', 'cohort-sha', 'cohort.json',
                   'snapshot-commit', 'snapshot-registry-sha', 'fixture',
                   '/fixture', 'following-snapshot-v1', '2026-07-11T00:00:00Z',
                   '2026-07-11T01:00:00Z', ?, 4)""",
        (status,),
    )
    sources = [
        ("1", "alpha", "complete"),
        ("2", "beta", "complete"),
        ("3", "charlie", "complete"),
        ("4", "private", "protected"),
    ]
    for x_id, handle, source_status in sources:
        conn.execute(
            """INSERT INTO source_fetch
               (source_x_id, source_handle, next_cursor, fetched_count,
                raw_page_count, status, attempts, updated_at)
               VALUES (?, ?, '', 0, 0, ?, 1, '2026-07-11T01:00:00Z')""",
            (x_id, handle, source_status),
        )
    targets = [
        ("10", "x", "X", 100),
        ("11", "y", "Y", 200),
        ("12", "w", "W", 300),
        ("13", "z", "Z", 400),
    ]
    conn.executemany(
        """INSERT INTO account
           (x_id, handle, display_name, followers_count,
            first_observed_at, last_observed_at)
           VALUES (?, ?, ?, ?, '2026-07-11T00:00:00Z',
                   '2026-07-11T01:00:00Z')""",
        targets,
    )
    edges = [
        ("1", "10"),
        ("1", "11"),
        ("2", "10"),
        ("2", "13"),
        ("3", "10"),
        ("3", "11"),
        ("3", "12"),
        ("4", "13"),
    ]
    conn.executemany(
        """INSERT INTO edge
           (source_x_id, target_x_id, raw_page_id, observed_at)
           VALUES (?, ?, 1, '2026-07-11T01:00:00Z')""",
        edges,
    )
    conn.commit()
    conn.close()


def _registry_identity(conn, *, x_id, handle, name, rejected=False):
    account_id = conn.execute(
        """INSERT INTO accounts
           (platform, handle, display_name, x_id, first_seen_at, last_seen_at)
           VALUES ('x', ?, ?, ?, '2026-07-11', '2026-07-11')""",
        (handle, name, x_id),
    ).lastrowid
    entity_id = channels.upsert_entity(
        conn,
        kind="person",
        slug=f"x-{handle}",
        name=name,
        observed_at="2026-07-11T00:00:00Z",
    )
    channel_id = channels.upsert_channel(
        conn,
        kind="x",
        key=handle,
        label=name,
        observed_at="2026-07-11T00:00:00Z",
    )
    channels.link_entity_channel(
        conn,
        entity_id=entity_id,
        channel_id=channel_id,
        relationship="identity",
    )
    if rejected:
        conn.execute(
            """INSERT INTO entity_registry_rejections
               (entity_id, reason_code, reason, source, rejected_at)
               VALUES (?, 'fixture', 'Fixture rejection.', 'test',
                       '2026-07-11T00:00:00Z')""",
            (entity_id,),
        )
    return account_id, entity_id


def _registry(path):
    conn = channels.connect(path)
    registry.ensure_schema(conn)
    for x_id, handle in (("1", "alpha"), ("2", "beta"), ("3", "charlie")):
        _registry_identity(conn, x_id=x_id, handle=handle, name=handle.title())
    _registry_identity(
        conn, x_id="4", handle="private", name="Private", rejected=True
    )
    _registry_identity(conn, x_id="10", handle="x", name="Known X")
    _registry_identity(conn, x_id="11", handle="y", name="Rejected Y", rejected=True)
    conn.commit()
    conn.close()


def test_overlap_is_deterministic_mapped_and_resumable(tmp_path):
    snapshot_db = tmp_path / "snapshot.db"
    registry_db = tmp_path / "registry.db"
    analysis_db = tmp_path / "analysis.db"
    export_csv = tmp_path / "top.csv"
    export_unknown_csv = tmp_path / "unknown.csv"
    _snapshot(snapshot_db)
    _registry(registry_db)

    first = following_rankings.run_overlap(
        snapshot_db=snapshot_db,
        registry_db=registry_db,
        analysis_db=analysis_db,
        top_k=4,
        export_csv=export_csv,
        export_unknown_csv=export_unknown_csv,
    )
    second = following_rankings.run_overlap(
        snapshot_db=snapshot_db,
        registry_db=registry_db,
        analysis_db=analysis_db,
        top_k=4,
    )

    assert first["reused"] is False
    assert second["reused"] is True
    assert second["context_id"] == first["context_id"]
    assert second["run_id"] == first["run_id"]
    assert first["counts"] == {
        "complete_sources": 3,
        "eligible_edges": 7,
        "ranked_accounts": 4,
        "active": 1,
        "rejected": 1,
        "unknown": 2,
    }
    assert [
        (row["handle"], row["cohort_follow_count"], row["registry_state"])
        for row in first["top"]
    ] == [
        ("x", 3, "active"),
        ("y", 2, "rejected"),
        ("w", 1, "unknown"),
        ("z", 1, "unknown"),
    ]
    with sqlite3.connect(analysis_db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM analysis_context").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM ranking_run").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM ranking_result").fetchone()[0] == 4
    with export_csv.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["handle"] for row in rows] == ["x", "y", "w", "z"]
    assert [row["handle"] for row in first["top_active"]] == ["x"]
    assert [row["handle"] for row in first["top_unknown"]] == ["w", "z"]
    with export_unknown_csv.open(newline="") as stream:
        unknown_rows = list(csv.DictReader(stream))
    assert [row["handle"] for row in unknown_rows] == ["w", "z"]


def test_registry_authorizer_denies_legacy_graph_reads():
    assert (
        following_rankings._analysis_authorizer(
            sqlite3.SQLITE_READ, "graph_edges", None, "registry", None
        )
        == sqlite3.SQLITE_DENY
    )
    assert (
        following_rankings._analysis_authorizer(
            sqlite3.SQLITE_READ, "accounts", None, "registry", None
        )
        == sqlite3.SQLITE_OK
    )


def test_overlap_rejects_incomplete_snapshot_before_output(tmp_path):
    snapshot_db = tmp_path / "snapshot.db"
    registry_db = tmp_path / "registry.db"
    analysis_db = tmp_path / "analysis.db"
    _snapshot(snapshot_db, status="collecting")
    _registry(registry_db)

    with pytest.raises(
        following_rankings.RankingCliError, match="not complete"
    ) as exc:
        following_rankings.run_overlap(
            snapshot_db=snapshot_db,
            registry_db=registry_db,
            analysis_db=analysis_db,
        )

    assert exc.value.code == "E_SNAPSHOT_INCOMPLETE"
    assert not analysis_db.exists()


def test_overlap_fails_closed_on_registry_identity_conflict(tmp_path):
    snapshot_db = tmp_path / "snapshot.db"
    registry_db = tmp_path / "registry.db"
    _snapshot(snapshot_db)
    _registry(registry_db)
    with sqlite3.connect(registry_db) as conn:
        conn.execute(
            """INSERT INTO accounts
               (platform, handle, display_name, x_id, first_seen_at, last_seen_at)
               VALUES ('x', 'duplicate', 'Duplicate', '1',
                       '2026-07-11', '2026-07-11')"""
        )
        conn.commit()

    with pytest.raises(
        following_rankings.RankingCliError, match="multiple accounts"
    ) as exc:
        following_rankings.run_overlap(
            snapshot_db=snapshot_db,
            registry_db=registry_db,
            analysis_db=tmp_path / "analysis.db",
        )

    assert exc.value.code == "E_REGISTRY_IDENTITY_CONFLICT"


def test_overlap_cli_has_stable_json_success_and_error(tmp_path, capsys):
    snapshot_db = tmp_path / "snapshot.db"
    registry_db = tmp_path / "registry.db"
    _snapshot(snapshot_db)
    _registry(registry_db)

    assert following_rankings.main(
        [
            "overlap",
            "--snapshot-db",
            str(snapshot_db),
            "--registry-db",
            str(registry_db),
            "--analysis-db",
            str(tmp_path / "analysis.db"),
            "--top-k",
            "2",
            "--no-input",
        ]
    ) == 0
    success = json.loads(capsys.readouterr().out)
    assert success["schema_version"] == "1.0"
    assert success["command"] == "following-ranking overlap"
    assert success["status"] == "ok"
    assert success["error"] is None
    assert len(success["data"]["top"]) == 2

    assert following_rankings.main(
        ["overlap", "--snapshot-db", str(tmp_path / "missing.db")]
    ) == 3
    failure = json.loads(capsys.readouterr().out)
    assert failure["status"] == "error"
    assert failure["data"] is None
    assert failure["error"]["code"] == "E_NOT_FOUND"
    assert failure["error"]["retryable"] is False
