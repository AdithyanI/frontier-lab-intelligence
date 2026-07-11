import json
import pytest

from fli import channels, following_snapshots, registry


def _product_db(path):
    conn = channels.connect(path)
    registry.ensure_schema(conn)
    observed_at = "2026-07-11T00:00:00+00:00"
    for x_id, handle in (("1", "alpha"), ("2", "beta"), ("3", "rejected")):
        conn.execute(
            """INSERT INTO accounts
               (platform, handle, display_name, x_id, followers_count,
                first_seen_at, last_seen_at)
               VALUES ('x', ?, ?, ?, 1000, ?, ?)""",
            (handle, handle.title(), x_id, observed_at, observed_at),
        )
        channel_id = channels.upsert_channel(
            conn,
            kind="x",
            key=handle,
            label=handle.title(),
            observed_at=observed_at,
        )
        entity_id = channels.upsert_entity(
            conn,
            kind="person",
            slug=f"person-{handle}",
            name=handle.title(),
            observed_at=observed_at,
        )
        channels.link_entity_channel(
            conn,
            entity_id=entity_id,
            channel_id=channel_id,
            relationship="identity",
            confidence=1.0,
            evidence_url=f"https://x.com/{handle}",
            notes=None,
            observed_at=observed_at,
        )
        if handle == "rejected":
            registry.reject_entity(
                conn,
                entity_id=entity_id,
                reason_code="test_rejection",
                reason="Excluded from active collection.",
                source="test",
                evidence_url=f"https://x.com/{handle}",
                rejected_at=observed_at,
            )
    conn.commit()
    conn.close()


def _cohort(tmp_path):
    product_db = tmp_path / "product.db"
    cohort_path = tmp_path / "cohort.json"
    _product_db(product_db)
    result = following_snapshots.freeze_cohort(
        product_db=product_db,
        output_path=cohort_path,
        cohort_id="test-cohort",
        created_at="2026-07-11T00:00:00+00:00",
        checkpoint_commit="test-commit",
    )
    return cohort_path, result


def _snapshot(tmp_path):
    cohort_path, _ = _cohort(tmp_path)
    snapshot_db = tmp_path / "snapshot.db"
    result = following_snapshots.initialize_snapshot(
        snapshot_id="test-snapshot",
        cohort_path=cohort_path,
        snapshot_db=snapshot_db,
        created_at="2026-07-11T00:00:00+00:00",
    )
    return snapshot_db, result


def test_freeze_cohort_excludes_rejections_and_is_idempotent(tmp_path):
    cohort_path, first = _cohort(tmp_path)
    second = following_snapshots.freeze_cohort(
        product_db=tmp_path / "product.db",
        output_path=cohort_path,
        cohort_id="test-cohort",
        created_at="later-is-ignored",
        checkpoint_commit="test-commit",
    )

    assert first["created"] is True
    assert first["source_count"] == 2
    assert [source["handle"] for source in first["sources"]] == ["alpha", "beta"]
    assert second["created"] is False
    assert second["cohort_sha256"] == first["cohort_sha256"]


def test_initialize_snapshot_is_idempotent_and_frozen(tmp_path):
    cohort_path, cohort = _cohort(tmp_path)
    snapshot_db = tmp_path / "snapshot.db"
    first = following_snapshots.initialize_snapshot(
        snapshot_id="test-snapshot",
        cohort_path=cohort_path,
        snapshot_db=snapshot_db,
        created_at="2026-07-11T00:00:00+00:00",
    )
    second = following_snapshots.initialize_snapshot(
        snapshot_id="test-snapshot",
        cohort_path=cohort_path,
        snapshot_db=snapshot_db,
    )

    assert first["created"] is True
    assert second["created"] is False
    assert first["counts"]["sources"] == 2
    assert first["cohort_sha256"] == cohort["cohort_sha256"]
    assert first["source_statuses"]["pending"] == 2


def test_record_page_persists_raw_first_and_resumes_by_cursor(tmp_path):
    snapshot_db, _ = _snapshot(tmp_path)
    conn = following_snapshots.connect_snapshot(snapshot_db)
    page_one = {
        "followings": [
            {
                "id": "10",
                "userName": "TargetOne",
                "name": "Target One",
                "followers": 20,
            },
            {"id": "11", "userName": "TargetTwo"},
        ],
        "has_next_page": True,
        "next_cursor": "cursor-2",
    }
    first = following_snapshots.record_page(
        conn,
        source_x_id="1",
        request_cursor=None,
        payload=page_one,
        retrieved_at="2026-07-11T01:00:00+00:00",
        advertised_following_count=2,
    )
    duplicate = following_snapshots.record_page(
        conn,
        source_x_id="1",
        request_cursor=None,
        payload=page_one,
        retrieved_at="later-does-not-rewrite-evidence",
    )
    second = following_snapshots.record_page(
        conn,
        source_x_id="1",
        request_cursor="cursor-2",
        payload={
            "followings": [{"id": "11", "userName": "TargetTwo"}],
            "has_next_page": False,
        },
        retrieved_at="2026-07-11T01:01:00+00:00",
    )

    assert first["created"] is True
    assert duplicate["created"] is False
    assert second["source_status"] == "complete"
    assert second["duplicates"] == 1
    assert conn.execute("SELECT COUNT(*) FROM raw_page").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM edge").fetchone()[0] == 2
    source = conn.execute(
        "SELECT * FROM source_fetch WHERE source_x_id = '1'"
    ).fetchone()
    assert source["advertised_following_count"] == 2
    assert source["fetched_count"] == 2
    assert source["raw_page_count"] == 2
    assert source["next_cursor"] == ""
    assert source["status"] == "complete"
    edge = conn.execute(
        """SELECT sf.source_handle, a.handle
           FROM edge e
           JOIN source_fetch sf ON sf.source_x_id = e.source_x_id
           JOIN account a ON a.x_id = e.target_x_id
           WHERE a.x_id = '10'"""
    ).fetchone()
    assert tuple(edge) == ("alpha", "targetone")
    conn.close()


def test_record_page_rejects_conflicting_cache_value(tmp_path):
    snapshot_db, _ = _snapshot(tmp_path)
    conn = following_snapshots.connect_snapshot(snapshot_db)
    following_snapshots.record_page(
        conn,
        source_x_id="1",
        request_cursor=None,
        payload={"followings": [], "has_next_page": False},
    )

    with pytest.raises(following_snapshots.SnapshotCliError) as exc:
        following_snapshots.record_page(
            conn,
            source_x_id="1",
            request_cursor=None,
            payload={
                "followings": [{"id": "10", "userName": "new"}],
                "has_next_page": False,
            },
        )

    assert exc.value.code == "E_PAGE_CONFLICT"
    assert conn.execute("SELECT COUNT(*) FROM raw_page").fetchone()[0] == 1
    conn.close()


def test_finalize_requires_terminal_sources_and_makes_snapshot_immutable(tmp_path):
    snapshot_db, _ = _snapshot(tmp_path)
    conn = following_snapshots.connect_snapshot(snapshot_db)
    following_snapshots.record_page(
        conn,
        source_x_id="1",
        request_cursor=None,
        payload={"followings": [], "has_next_page": False},
    )
    with pytest.raises(following_snapshots.SnapshotCliError) as exc:
        following_snapshots.finalize_snapshot(conn)
    assert exc.value.code == "E_SNAPSHOT_INCOMPLETE"

    following_snapshots.mark_source(
        conn,
        source_x_id="2",
        status="protected",
        error_code="E_ACCOUNT_PROTECTED",
        error_message="Posts and following evidence are unavailable.",
    )
    with pytest.raises(following_snapshots.SnapshotCliError) as exc:
        following_snapshots.mark_source(conn, source_x_id="2", status="missing")
    assert exc.value.code == "E_SOURCE_TERMINAL"
    summary = following_snapshots.finalize_snapshot(
        conn,
        reported_cost_usd=0.001,
        completed_at="2026-07-11T02:00:00+00:00",
    )
    assert summary["status"] == "complete"
    assert summary["source_statuses"]["complete"] == 1
    assert summary["source_statuses"]["protected"] == 1

    with pytest.raises(following_snapshots.SnapshotCliError) as exc:
        following_snapshots.mark_source(conn, source_x_id="2", status="missing")
    assert exc.value.code == "E_SNAPSHOT_COMPLETE"
    assert following_snapshots.validate_snapshot(conn)["valid"] is True
    conn.close()


def test_validate_detects_reconciliation_error(tmp_path):
    snapshot_db, _ = _snapshot(tmp_path)
    conn = following_snapshots.connect_snapshot(snapshot_db)
    conn.execute("UPDATE source_fetch SET raw_page_count = 1 WHERE source_x_id = '1'")
    conn.commit()

    result = following_snapshots.validate_snapshot(conn)

    assert result["valid"] is False
    assert result["validation_failures"] == ["source_page_count_mismatch:1"]
    conn.close()


def test_cli_status_is_json_and_missing_snapshot_is_structured(tmp_path, capsys):
    snapshot_db, _ = _snapshot(tmp_path)
    code = following_snapshots.main(
        ["status", "--snapshot-db", str(snapshot_db), "--no-input"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["schema_version"] == "1.0"
    assert payload["status"] == "ok"
    assert payload["data"]["counts"]["sources"] == 2

    code = following_snapshots.main(
        ["status", "--snapshot-db", str(tmp_path / "missing.db"), "--no-input"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 3
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "E_NOT_FOUND"


def test_invalid_cohort_checksum_is_rejected(tmp_path):
    cohort_path, _ = _cohort(tmp_path)
    cohort = json.loads(cohort_path.read_text())
    cohort["sources"][0]["handle"] = "tampered"
    cohort_path.write_text(json.dumps(cohort))

    with pytest.raises(following_snapshots.SnapshotCliError) as exc:
        following_snapshots.initialize_snapshot(
            snapshot_id="test",
            cohort_path=cohort_path,
            snapshot_db=tmp_path / "snapshot.db",
        )

    assert exc.value.code == "E_INVALID_COHORT"
