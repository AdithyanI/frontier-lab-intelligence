import csv
import hashlib
import json
import sqlite3

import pytest

from fli.network import rankings as following_rankings
from fli.network import snapshots as following_snapshots
from fli.registry import channels
from fli.registry import store as registry


def _snapshot(path, *, status="complete"):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(following_snapshots.SCHEMA)
    conn.execute(
        """INSERT INTO snapshot_run
           (snapshot_id, cohort_id, cohort_sha256, cohort_manifest_path,
            checkpoint_commit, checkpoint_db_sha256, provider, endpoint,
            schema_version, created_at, completed_at, status, source_count)
           VALUES ('fixture', 'fixture-cohort', 'cohort-sha', 'cohort.json',
                   'snapshot-commit', 'snapshot-registry-sha', 'fixture',
                   '/fixture', 'following-snapshot-v1', '2026-07-11T00:00:00Z',
                   '2026-07-11T01:00:00Z', ?, 5)""",
        (status,),
    )
    sources = [
        ("1", "alpha", "complete"),
        ("2", "beta", "complete"),
        ("3", "charlie", "complete"),
        ("4", "private", "complete"),
        ("5", "alpha_alt", "complete"),
    ]
    edges = [
        ("1", "10"),
        ("1", "11"),
        ("2", "10"),
        ("2", "13"),
        ("3", "10"),
        ("3", "11"),
        ("3", "12"),
        ("4", "13"),
        ("4", "14"),
        ("5", "10"),
        ("5", "13"),
        ("1", "2"),
        ("2", "1"),
        ("3", "5"),
        ("5", "3"),
        ("4", "1"),
        ("1", "5"),
    ]
    edge_counts = {
        x_id: sum(1 for source_x_id, _ in edges if source_x_id == x_id)
        for x_id, _, _ in sources
    }
    for x_id, handle, source_status in sources:
        conn.execute(
            """INSERT INTO source_fetch
               (source_x_id, source_handle, next_cursor, fetched_count,
                raw_page_count, status, attempts, updated_at)
               VALUES (?, ?, '', ?, 1, ?, 1, '2026-07-11T01:00:00Z')""",
            (x_id, handle, edge_counts[x_id], source_status),
        )
    targets = [
        ("1", "alpha", "Alpha", 1000),
        ("2", "beta", "Beta", 1000),
        ("3", "charlie", "Charlie", 1000),
        ("4", "private", "Private", 1000),
        ("5", "alpha_alt", "Alpha Alt", 1000),
        ("10", "x", "X", 100),
        ("11", "y", "Y", 200),
        ("12", "w", "W", 300),
        ("13", "z", "Z", 400),
        ("14", "v", "V", 500),
    ]
    conn.executemany(
        """INSERT INTO account
           (x_id, handle, display_name, followers_count,
            first_observed_at, last_observed_at)
           VALUES (?, ?, ?, ?, '2026-07-11T00:00:00Z',
                   '2026-07-11T01:00:00Z')""",
        targets,
    )
    page_ids = {}
    response_json = "{}"
    response_sha256 = hashlib.sha256(response_json.encode()).hexdigest()
    for x_id, _, _ in sources:
        page_ids[x_id] = conn.execute(
            """INSERT INTO raw_page
               (source_x_id, request_cursor, next_cursor, item_count,
                retrieved_at, response_json, response_sha256)
               VALUES (?, '', NULL, ?, '2026-07-11T01:00:00Z', ?, ?)""",
            (x_id, edge_counts[x_id], response_json, response_sha256),
        ).lastrowid
    conn.executemany(
        """INSERT INTO edge
           (source_x_id, target_x_id, raw_page_id, observed_at)
           VALUES (?, ?, ?, '2026-07-11T01:00:00Z')""",
        [(source, target, page_ids[source]) for source, target in edges],
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
    _, alpha_entity_id = _registry_identity(
        conn, x_id="1", handle="alpha", name="Alpha"
    )
    conn.execute(
        """INSERT INTO accounts
           (platform, handle, display_name, x_id, first_seen_at, last_seen_at)
           VALUES ('x', 'alpha_alt', 'Alpha Alt', '5',
                   '2026-07-11', '2026-07-11')"""
    )
    alpha_alt_channel = channels.upsert_channel(
        conn,
        kind="x",
        key="alpha_alt",
        label="Alpha Alt",
        observed_at="2026-07-11T00:00:00Z",
    )
    channels.link_entity_channel(
        conn,
        entity_id=alpha_entity_id,
        channel_id=alpha_alt_channel,
        relationship="official",
    )
    for x_id, handle in (("2", "beta"), ("3", "charlie")):
        _registry_identity(conn, x_id=x_id, handle=handle, name=handle.title())
    _registry_identity(
        conn, x_id="4", handle="private", name="Private", rejected=True
    )
    _registry_identity(conn, x_id="10", handle="x", name="Known X")
    _registry_identity(conn, x_id="11", handle="y", name="Rejected Y", rejected=True)
    _registry_identity(
        conn, x_id="99", handle="zero_support", name="Zero Support"
    )
    conn.commit()
    conn.close()


def _personalization(path, sources=None):
    sources = sources or [
        {
            "x_id": "1",
            "handle": "alpha",
            "category": "fixture",
            "weight": 1.0,
            "reason": "Fixture trusted source.",
        }
    ]
    path.write_text(
        json.dumps(
            {
                "schema_version": "following-personalization-v1",
                "personalization_id": "fixture-personalization",
                "snapshot_id": "fixture",
                "status": "experimental",
                "weighting": "uniform",
                "selection_rule": "Fixture selection rule.",
                "sources": sources,
            }
        )
    )


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
        top_k=10,
        export_csv=export_csv,
        export_unknown_csv=export_unknown_csv,
    )
    second = following_rankings.run_overlap(
        snapshot_db=snapshot_db,
        registry_db=registry_db,
        analysis_db=analysis_db,
        top_k=10,
    )

    assert first["reused"] is False
    assert second["reused"] is True
    assert second["context_id"] == first["context_id"]
    assert second["run_id"] == first["run_id"]
    assert first["counts"] == {
        "eligible_source_accounts": 4,
        "eligible_source_entities": 3,
        "eligible_edges": 14,
        "eligible_entity_votes": 13,
        "ranked_accounts": 10,
        "ranked_registry_entities": 5,
        "registry_entity_support_votes": 7,
        "active": 5,
        "rejected": 2,
        "unknown": 3,
    }
    assert [
        (row["handle"], row["cohort_follow_count"], row["registry_state"])
        for row in first["top"]
    ] == [
        ("x", 3, "active"),
        ("alpha_alt", 2, "active"),
        ("y", 2, "rejected"),
        ("z", 2, "unknown"),
        ("alpha", 1, "active"),
        ("beta", 1, "active"),
        ("charlie", 1, "active"),
        ("w", 1, "unknown"),
        ("private", 0, "rejected"),
        ("v", 0, "unknown"),
    ]
    assert [row["score_rank"] for row in first["top"]] == [
        1, 2, 2, 2, 3, 3, 3, 3, 4, 4
    ]
    with sqlite3.connect(analysis_db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM analysis_context").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM ranking_run").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM ranking_result").fetchone()[0] == 10
        entity_support = conn.execute(
            """SELECT entity_id, support_rank, support_count, channel_count
               FROM entity_support_result
               ORDER BY support_rank, entity_id"""
        ).fetchall()
        assert entity_support == [
            (5, 1, 3, 1),
            (1, 2, 2, 2),
            (2, 3, 1, 1),
            (3, 3, 1, 1),
            (7, 4, 0, 1),
        ]
    with export_csv.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["handle"] for row in rows] == [
        "x", "alpha_alt", "y", "z", "alpha", "beta", "charlie", "w",
        "private", "v"
    ]
    assert [row["handle"] for row in first["top_active"]] == [
        "x", "alpha_alt", "alpha", "beta", "charlie"
    ]
    assert [row["handle"] for row in first["top_unknown"]] == ["z", "w", "v"]
    with export_unknown_csv.open(newline="") as stream:
        unknown_rows = list(csv.DictReader(stream))
    assert [row["handle"] for row in unknown_rows] == ["z", "w", "v"]


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


def test_registry_authorizer_blocks_an_attached_legacy_graph(tmp_path):
    registry_db = tmp_path / "registry.db"
    _registry(registry_db)
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "ATTACH DATABASE ? AS registry",
        (following_rankings._readonly_uri(registry_db),),
    )
    conn.set_authorizer(following_rankings._analysis_authorizer)
    try:
        assert conn.execute("SELECT COUNT(*) FROM registry.accounts").fetchone()[0]
        with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
            conn.execute("SELECT COUNT(*) FROM registry.graph_edges").fetchone()
    finally:
        conn.set_authorizer(None)
        conn.close()


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


@pytest.mark.parametrize("collision", ["snapshot", "registry", "export"])
def test_overlap_rejects_output_path_collisions_before_writing(
    tmp_path, collision
):
    snapshot_db = tmp_path / "snapshot.db"
    registry_db = tmp_path / "registry.db"
    analysis_db = tmp_path / "analysis.db"
    _snapshot(snapshot_db)
    _registry(registry_db)
    snapshot_before = hashlib.sha256(snapshot_db.read_bytes()).hexdigest()
    registry_before = hashlib.sha256(registry_db.read_bytes()).hexdigest()
    kwargs = {
        "snapshot_db": snapshot_db,
        "registry_db": registry_db,
        "analysis_db": analysis_db,
    }
    if collision == "snapshot":
        kwargs["analysis_db"] = snapshot_db
    elif collision == "registry":
        kwargs["analysis_db"] = registry_db
    else:
        kwargs["export_csv"] = analysis_db

    with pytest.raises(following_rankings.RankingCliError) as exc:
        following_rankings.run_overlap(**kwargs)

    assert exc.value.code == "E_PATH_CONFLICT"
    assert hashlib.sha256(snapshot_db.read_bytes()).hexdigest() == snapshot_before
    assert hashlib.sha256(registry_db.read_bytes()).hexdigest() == registry_before


def test_overlap_rejects_symlink_alias_to_protected_database(tmp_path):
    snapshot_db = tmp_path / "snapshot.db"
    registry_db = tmp_path / "registry.db"
    snapshot_alias = tmp_path / "analysis.db"
    _snapshot(snapshot_db)
    _registry(registry_db)
    snapshot_alias.symlink_to(snapshot_db)
    snapshot_before = hashlib.sha256(snapshot_db.read_bytes()).hexdigest()

    with pytest.raises(following_rankings.RankingCliError) as exc:
        following_rankings.run_overlap(
            snapshot_db=snapshot_db,
            registry_db=registry_db,
            analysis_db=snapshot_alias,
        )

    assert exc.value.code == "E_PATH_CONFLICT"
    assert hashlib.sha256(snapshot_db.read_bytes()).hexdigest() == snapshot_before


def test_registry_backup_includes_committed_wal_rows(tmp_path):
    snapshot_db = tmp_path / "snapshot.db"
    registry_db = tmp_path / "registry.db"
    _snapshot(snapshot_db)
    _registry(registry_db)
    conn = sqlite3.connect(registry_db)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA wal_autocheckpoint = 0")
    conn.execute(
        """INSERT INTO accounts
           (platform, handle, display_name, x_id, first_seen_at, last_seen_at)
           VALUES ('x', 'wal_orphan', 'WAL Orphan', '998',
                   '2026-07-11', '2026-07-11')"""
    )
    conn.commit()
    try:
        with pytest.raises(
            following_rankings.RankingCliError, match="no single entity owner"
        ) as exc:
            following_rankings.run_overlap(
                snapshot_db=snapshot_db,
                registry_db=registry_db,
                analysis_db=tmp_path / "analysis.db",
            )
    finally:
        conn.close()
    assert exc.value.code == "E_REGISTRY_IDENTITY_CONFLICT"


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


def test_overlap_fails_closed_on_orphan_registry_account(tmp_path):
    snapshot_db = tmp_path / "snapshot.db"
    registry_db = tmp_path / "registry.db"
    _snapshot(snapshot_db)
    _registry(registry_db)
    with sqlite3.connect(registry_db) as conn:
        conn.execute(
            """INSERT INTO accounts
               (platform, handle, display_name, x_id, first_seen_at, last_seen_at)
               VALUES ('x', 'orphan', 'Orphan', '999',
                       '2026-07-11', '2026-07-11')"""
        )
        conn.commit()

    with pytest.raises(
        following_rankings.RankingCliError, match="no single entity owner"
    ) as exc:
        following_rankings.run_overlap(
            snapshot_db=snapshot_db,
            registry_db=registry_db,
            analysis_db=tmp_path / "analysis.db",
        )

    assert exc.value.code == "E_REGISTRY_IDENTITY_CONFLICT"


def test_overlap_reuse_detects_corrupt_result_rows(tmp_path):
    snapshot_db = tmp_path / "snapshot.db"
    registry_db = tmp_path / "registry.db"
    analysis_db = tmp_path / "analysis.db"
    _snapshot(snapshot_db)
    _registry(registry_db)
    first = following_rankings.run_overlap(
        snapshot_db=snapshot_db,
        registry_db=registry_db,
        analysis_db=analysis_db,
    )
    with sqlite3.connect(analysis_db) as conn:
        conn.execute(
            "DELETE FROM ranking_result WHERE run_id = ? AND position = 4",
            (first["run_id"],),
        )
        conn.commit()

    with pytest.raises(
        following_rankings.RankingCliError, match="do not match"
    ) as exc:
        following_rankings.run_overlap(
            snapshot_db=snapshot_db,
            registry_db=registry_db,
            analysis_db=analysis_db,
        )

    assert exc.value.code == "E_ANALYSIS_RECONCILIATION"


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


def test_personalization_hash_is_order_independent_and_rejects_duplicates(tmp_path):
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    sources = [
        {
            "x_id": "1",
            "handle": "alpha",
            "category": "fixture",
            "weight": 1.0,
            "reason": "Alpha reason.",
        },
        {
            "x_id": "2",
            "handle": "beta",
            "category": "fixture",
            "weight": 1.0,
            "reason": "Beta reason.",
        },
    ]
    _personalization(first_path, sources)
    _personalization(second_path, list(reversed(sources)))
    _, first_hash = following_rankings.load_personalization(first_path)
    _, second_hash = following_rankings.load_personalization(second_path)
    assert first_hash == second_hash

    duplicate_path = tmp_path / "duplicate.json"
    _personalization(duplicate_path, [sources[0], sources[0]])
    with pytest.raises(
        following_rankings.RankingCliError, match="duplicated"
    ) as exc:
        following_rankings.load_personalization(duplicate_path)
    assert exc.value.code == "E_PERSONALIZATION_INVALID"


def test_personalized_pagerank_converges_compares_and_reuses(tmp_path):
    snapshot_db = tmp_path / "snapshot.db"
    registry_db = tmp_path / "registry.db"
    analysis_db = tmp_path / "analysis.db"
    personalization = tmp_path / "personalization.json"
    comparison_csv = tmp_path / "comparison.csv"
    unknown_csv = tmp_path / "unknown.csv"
    _snapshot(snapshot_db)
    _registry(registry_db)
    _personalization(personalization)

    first = following_rankings.run_pagerank(
        snapshot_db=snapshot_db,
        registry_db=registry_db,
        analysis_db=analysis_db,
        personalization_path=personalization,
        top_k=10,
        export_comparison_csv=comparison_csv,
        export_unknown_csv=unknown_csv,
    )
    second = following_rankings.run_pagerank(
        snapshot_db=snapshot_db,
        registry_db=registry_db,
        analysis_db=analysis_db,
        personalization_path=personalization,
        top_k=10,
    )

    assert first["reused"] is False
    assert second["reused"] is True
    assert first["run_id"] == second["run_id"]
    assert first["diagnostics"]["converged"] == 1
    assert first["diagnostics"]["seed_count"] == 1
    assert first["diagnostics"]["iterations"] <= 100
    assert first["diagnostics"]["score_sum"] == pytest.approx(1.0, abs=1e-12)
    assert {row["handle"] for row in first["top_unknown"]} == {"v", "w", "z"}
    with sqlite3.connect(analysis_db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM ranking_run").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM ranking_result").fetchone()[0] == 20
        assert conn.execute("SELECT COUNT(*) FROM ranking_comparison").fetchone()[0] == 10
    with unknown_csv.open(newline="") as stream:
        assert {row["registry_state"] for row in csv.DictReader(stream)} == {
            "unknown"
        }


def test_personalized_pagerank_nonconvergence_stores_no_partial_run(tmp_path):
    snapshot_db = tmp_path / "snapshot.db"
    registry_db = tmp_path / "registry.db"
    analysis_db = tmp_path / "analysis.db"
    personalization = tmp_path / "personalization.json"
    _snapshot(snapshot_db)
    _registry(registry_db)
    _personalization(personalization)

    with pytest.raises(
        following_rankings.RankingCliError, match="did not converge"
    ) as exc:
        following_rankings.run_pagerank(
            snapshot_db=snapshot_db,
            registry_db=registry_db,
            analysis_db=analysis_db,
            personalization_path=personalization,
            tolerance=1e-30,
            max_iterations=1,
        )

    assert exc.value.code == "E_PAGERANK_DID_NOT_CONVERGE"
    with sqlite3.connect(analysis_db) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM ranking_run WHERE algorithm = ?",
            (following_rankings.PAGERANK_ALGORITHM,),
        ).fetchone()[0] == 0
