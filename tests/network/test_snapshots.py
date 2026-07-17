import json
import pytest

from fli.ingestion import sources
from fli.network import snapshots as following_snapshots
from fli.registry import channels
from fli.registry import store as registry


class FakeCollectorClient:
    def __init__(self, *, profiles, pages):
        self.profiles = profiles
        self.pages = pages
        self.profile_calls = []
        self.page_calls = []

    def fetch_user(self, *, username):
        self.profile_calls.append(username)
        value = self.profiles[username]
        if isinstance(value, Exception):
            raise value
        return value

    def fetch_following_page(self, *, username, cursor, page_size):
        self.page_calls.append((username, cursor, page_size))
        value = self.pages[(username, cursor)]
        if isinstance(value, Exception):
            raise value
        return value


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


def test_child_snapshot_reuses_complete_parent_and_leaves_new_source_pending(
    tmp_path,
):
    parent_db, _ = _snapshot(tmp_path)
    parent = following_snapshots.connect_snapshot(parent_db)
    following_snapshots.record_profile(
        parent,
        source_x_id="1",
        profile={"id": "1", "userName": "alpha", "following": 1},
    )
    following_snapshots.record_page(
        parent,
        source_x_id="1",
        request_cursor=None,
        payload={
            "followings": [{"id": "10", "userName": "target"}],
            "has_next_page": False,
        },
    )
    following_snapshots.mark_source(
        parent,
        source_x_id="2",
        status="protected",
        error_code="E_ACCOUNT_PROTECTED",
        error_message="Protected.",
    )
    following_snapshots.finalize_snapshot(parent)
    parent.close()

    child_cohort_root = tmp_path / "child-cohort"
    child_cohort_root.mkdir()
    cohort_path, _ = _cohort(child_cohort_root)
    cohort = json.loads(cohort_path.read_text())
    cohort["sources"].append(
        {
            "x_id": "4",
            "handle": "gamma",
            "display_name": "Gamma",
            "followers_count": 500,
        }
    )
    cohort["source_count"] = len(cohort["sources"])
    cohort["cohort_sha256"] = following_snapshots._cohort_hash(cohort["sources"])
    child_cohort = tmp_path / "child.json"
    child_cohort.write_text(json.dumps(cohort))
    child_db = tmp_path / "child.db"
    following_snapshots.initialize_snapshot(
        snapshot_id="child-snapshot",
        cohort_path=child_cohort,
        snapshot_db=child_db,
    )
    child = following_snapshots.connect_snapshot(child_db)

    first = following_snapshots.reuse_parent_snapshot(
        child,
        parent_snapshot_db=parent_db,
        copied_at="2026-07-14T00:00:00+00:00",
    )
    second = following_snapshots.reuse_parent_snapshot(
        child,
        parent_snapshot_db=parent_db,
    )

    assert first["created"] is True
    assert second["created"] is False
    assert first["lineage"]["copied_sources"] == 2
    assert first["lineage"]["copied_edges"] == 1
    assert first["snapshot"]["source_statuses"]["complete"] == 1
    assert first["snapshot"]["source_statuses"]["protected"] == 1
    assert first["snapshot"]["source_statuses"]["pending"] == 1
    assert child.execute("SELECT COUNT(*) FROM edge").fetchone()[0] == 1
    assert following_snapshots.validate_snapshot(child)["valid"] is True
    child.close()


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
    conn.execute("UPDATE snapshot_run SET estimated_cost_usd = 0.0009")
    conn.commit()
    with pytest.raises(following_snapshots.SnapshotCliError) as exc:
        following_snapshots.mark_source(conn, source_x_id="2", status="missing")
    assert exc.value.code == "E_SOURCE_TERMINAL"
    summary = following_snapshots.finalize_snapshot(
        conn,
        reported_cost_usd=0.001,
        completed_at="2026-07-11T02:00:00+00:00",
    )
    assert summary["status"] == "complete"
    assert summary["estimated_cost_usd"] == 0.0009
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


def test_collector_pauses_and_resumes_without_refetching_profile_or_page(tmp_path):
    snapshot_db, _ = _snapshot(tmp_path)
    conn = following_snapshots.connect_snapshot(snapshot_db)
    client = FakeCollectorClient(
        profiles={"alpha": {"id": "1", "userName": "alpha", "following": 2}},
        pages={
            ("alpha", None): {
                "followings": [{"id": "10", "userName": "first"}],
                "has_next_page": True,
                "next_cursor": "cursor-2",
            },
            ("alpha", "cursor-2"): {
                "followings": [{"id": "11", "userName": "second"}],
                "has_next_page": False,
            },
        },
    )

    first = following_snapshots.collect_snapshot(
        conn,
        client=client,
        handles=["@alpha"],
        max_pages_per_source=1,
    )
    second = following_snapshots.collect_snapshot(
        conn,
        client=client,
        handles=["alpha"],
    )

    assert first["outcomes"]["paused"] == 1
    assert first["profiles_fetched"] == 1
    assert first["pages_fetched"] == 1
    assert second["outcomes"]["complete"] == 1
    assert second["profiles_fetched"] == 0
    assert second["profiles_reused"] == 1
    assert second["pages_fetched"] == 1
    assert client.profile_calls == ["alpha"]
    assert client.page_calls == [
        ("alpha", None, 200),
        ("alpha", "cursor-2", 200),
    ]
    assert second["cumulative_cost"] == {
        "profile_requests": 1,
        "unpersisted_error_requests": 0,
        "following_page_requests": 2,
        "estimated_provider_credits": 138,
        "estimated_provider_cost_usd": 0.00138,
    }
    assert second["snapshot"]["counts"]["raw_profiles"] == 1
    assert second["snapshot"]["counts"]["edges"] == 2
    conn.close()


def test_collector_marks_protected_without_fetching_following_page(tmp_path):
    snapshot_db, _ = _snapshot(tmp_path)
    conn = following_snapshots.connect_snapshot(snapshot_db)
    client = FakeCollectorClient(
        profiles={
            "beta": {
                "id": "2",
                "userName": "beta",
                "protected": True,
                "following": 20,
            }
        },
        pages={},
    )

    result = following_snapshots.collect_snapshot(
        conn,
        client=client,
        handles=["beta"],
    )

    assert result["outcomes"]["protected"] == 1
    assert result["pages_fetched"] == 0
    assert client.page_calls == []
    assert conn.execute(
        "SELECT status FROM source_fetch WHERE source_x_id = '2'"
    ).fetchone()[0] == "protected"
    conn.close()


def test_collector_preserves_retryable_error_and_resume_cursor(tmp_path):
    snapshot_db, _ = _snapshot(tmp_path)
    conn = following_snapshots.connect_snapshot(snapshot_db)
    network_error = sources.SourceCliError(
        code="E_NETWORK",
        message="Could not reach TwitterAPI.io.",
        hint="Retry later.",
        exit_code=4,
        retryable=True,
    )
    client = FakeCollectorClient(
        profiles={"alpha": network_error},
        pages={},
    )

    with pytest.raises(following_snapshots.SnapshotCliError) as exc:
        following_snapshots.collect_snapshot(
            conn,
            client=client,
            handles=["alpha"],
        )

    assert exc.value.code == "E_NETWORK"
    source = conn.execute(
        "SELECT * FROM source_fetch WHERE source_x_id = '1'"
    ).fetchone()
    assert source["status"] == "pending"
    assert source["next_cursor"] == ""
    assert source["attempts"] == 1
    assert source["last_error_code"] == "E_NETWORK"
    conn.close()


def test_collector_dry_run_needs_no_client_or_secret(tmp_path):
    snapshot_db, _ = _snapshot(tmp_path)
    conn = following_snapshots.connect_snapshot(snapshot_db)

    result = following_snapshots.collect_snapshot(
        conn,
        handles=["alpha"],
        dry_run=True,
        key_file=tmp_path / "missing",
    )

    assert result["dry_run"] is True
    assert result["selected_sources"] == 1
    assert result["selected_handle_preview"] == ["alpha"]
    assert result["snapshot"]["counts"]["raw_pages"] == 0
    conn.close()


def test_profiles_only_caches_counts_without_following_pages(tmp_path):
    snapshot_db, _ = _snapshot(tmp_path)
    conn = following_snapshots.connect_snapshot(snapshot_db)
    client = FakeCollectorClient(
        profiles={
            "alpha": {
                "id": "1",
                "userName": "alpha",
                "followers": 12_345,
                "following": 2,
            }
        },
        pages={},
    )

    result = following_snapshots.collect_snapshot(
        conn,
        client=client,
        handles=["alpha"],
        profiles_only=True,
    )

    assert result["outcomes"]["profiled"] == 1
    assert result["pages_fetched"] == 0
    assert client.page_calls == []
    assert result["profile_cost_projection"] == {
        "sources_with_following_count": 1,
        "advertised_following_total": 2,
        "average_advertised_following_count": 2.0,
        "projected_provider_credits_for_profiled_sources": 78,
        "projected_cost_usd_for_profiled_sources": 0.00078,
    }
    source = conn.execute(
        "SELECT * FROM source_fetch WHERE source_x_id = '1'"
    ).fetchone()
    assert source["status"] == "pending"
    assert source["advertised_following_count"] == 2
    assert following_snapshots.validate_snapshot(conn)["valid"] is True
    conn.close()


def test_parallel_profile_scan_respects_profile_only_boundary(tmp_path):
    snapshot_db, _ = _snapshot(tmp_path)
    conn = following_snapshots.connect_snapshot(snapshot_db)
    client = FakeCollectorClient(
        profiles={
            "alpha": {"id": "1", "userName": "alpha", "following": 2},
            "beta": {"id": "2", "userName": "beta", "following": 3},
        },
        pages={},
    )

    result = following_snapshots.collect_snapshot(
        conn,
        client=client,
        collect_all=True,
        profiles_only=True,
        workers=2,
        requests_per_second=10_000,
    )

    assert result["workers"] == 2
    assert result["outcomes"]["profiled"] == 2
    assert result["profiles_fetched"] == 2
    assert result["pages_fetched"] == 0
    assert sorted(client.profile_calls) == ["alpha", "beta"]
    assert client.page_calls == []
    assert following_snapshots.validate_snapshot(conn)["valid"] is True
    conn.close()


def test_parallel_following_crawl_keeps_each_source_cursor_chain_ordered(tmp_path):
    snapshot_db, _ = _snapshot(tmp_path)
    conn = following_snapshots.connect_snapshot(snapshot_db)
    client = FakeCollectorClient(
        profiles={
            "alpha": {"id": "1", "userName": "alpha", "following": 2},
            "beta": {"id": "2", "userName": "beta", "following": 1},
        },
        pages={
            ("alpha", None): {
                "followings": [{"id": "10", "userName": "first"}],
                "has_next_page": True,
                "next_cursor": "alpha-2",
            },
            ("alpha", "alpha-2"): {
                "followings": [{"id": "11", "userName": "second"}],
                "has_next_page": False,
            },
            ("beta", None): {
                "followings": [{"id": "12", "userName": "third"}],
                "has_next_page": False,
            },
        },
    )

    result = following_snapshots.collect_snapshot_parallel(
        conn,
        snapshot_db=snapshot_db,
        client=client,
        collect_all=True,
        workers=2,
        requests_per_second=10_000,
    )

    assert result["workers"] == 2
    assert result["outcomes"]["complete"] == 2
    assert result["pages_fetched"] == 3
    assert [call[1] for call in client.page_calls if call[0] == "alpha"] == [
        None,
        "alpha-2",
    ]
    assert result["snapshot"]["counts"]["edges"] == 3
    assert following_snapshots.validate_snapshot(conn)["valid"] is True
    conn.close()


def test_zero_following_profile_completes_without_page_request(tmp_path):
    snapshot_db, _ = _snapshot(tmp_path)
    conn = following_snapshots.connect_snapshot(snapshot_db)
    client = FakeCollectorClient(
        profiles={"alpha": {"id": "1", "userName": "alpha", "following": 0}},
        pages={},
    )

    result = following_snapshots.collect_snapshot(
        conn,
        client=client,
        handles=["alpha"],
    )

    assert result["outcomes"]["complete"] == 1
    assert result["pages_fetched"] == 0
    assert client.page_calls == []
    source = conn.execute(
        "SELECT * FROM source_fetch WHERE source_x_id = '1'"
    ).fetchone()
    assert source["status"] == "complete"
    assert source["fetched_count"] == 0
    assert source["raw_page_count"] == 0
    assert following_snapshots.validate_snapshot(conn)["valid"] is True
    conn.close()


def test_collect_cli_requires_explicit_scope(tmp_path, capsys):
    snapshot_db, _ = _snapshot(tmp_path)

    code = following_snapshots.main(
        ["collect", "--snapshot-db", str(snapshot_db), "--no-input"]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "E_USAGE"


def test_collection_lock_rejects_concurrent_local_collector(tmp_path):
    snapshot_db, _ = _snapshot(tmp_path)

    with following_snapshots.collection_lock(snapshot_db):
        with pytest.raises(following_snapshots.SnapshotCliError) as exc:
            with following_snapshots.collection_lock(snapshot_db):
                pass

    assert exc.value.code == "E_COLLECTION_LOCKED"
