import hashlib
import json
import sqlite3

import pytest

from fli import channels, graph, labs, registry


def test_materializes_one_unknown_entity_per_unlinked_channel(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    channel_id = channels.upsert_channel(
        conn,
        kind="x",
        key="karpathy",
        label="Andrej Karpathy",
        observed_at="2026-07-09T00:00:00+00:00",
    )

    first = registry.materialize_unlinked_channels(
        conn, observed_at="2026-07-09T00:00:00+00:00"
    )
    second = registry.materialize_unlinked_channels(
        conn, observed_at="2026-07-09T00:00:00+00:00"
    )

    assert first["created_entities"] == 1
    assert second["created_entities"] == 0
    entity = conn.execute(
        """SELECT e.* FROM entities e
           JOIN entity_channels ec ON ec.entity_id = e.id
           WHERE ec.channel_id = ?""",
        (channel_id,),
    ).fetchone()
    assert entity["kind"] == "unknown"
    assert entity["name"] == "Andrej Karpathy"
    assert second["unlinked_channels"] == 0


def test_known_lab_replaces_its_provisional_unknown(tmp_path):
    db = tmp_path / "test.db"
    conn = graph.connect(db)
    conn.execute(
        """INSERT INTO accounts
           (platform, handle, display_name, first_seen_at, last_seen_at)
           VALUES ('x', 'openai', 'OpenAI', '2026-07-09', '2026-07-09')"""
    )
    conn.execute(
        """INSERT INTO account_source_facts
           (account_id, source, fact, value, observed_at)
           VALUES (1, 'test', 'list_member', 'seed', '2026-07-09')"""
    )
    conn.commit()
    channels.sync_all(conn)
    assert conn.execute(
        "SELECT COUNT(*) FROM entities WHERE kind = 'unknown'"
    ).fetchone()[0] == 1

    conn = labs.connect(db)
    labs.seed(
        conn,
        labs=[
            {
                "slug": "openai",
                "name": "OpenAI",
                "status": "frontier",
                "x_handle": "openai",
                "website": "https://openai.com",
                "blog_feed": None,
                "github_org": None,
                "arxiv_query": None,
                "notes": None,
            }
        ],
    )

    owner = conn.execute(
        """SELECT e.* FROM entities e
           JOIN entity_channels ec ON ec.entity_id = e.id
           JOIN channels c ON c.id = ec.channel_id
           WHERE c.kind = 'x' AND c.key = 'openai'"""
    ).fetchone()
    assert owner["kind"] == "organization"
    assert owner["slug"] == "openai"
    assert conn.execute(
        "SELECT COUNT(*) FROM entities WHERE kind = 'unknown'"
    ).fetchone()[0] == 0


def test_registry_read_model_excludes_rank_and_source_fields(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    channel_id = channels.upsert_channel(
        conn,
        kind="x",
        key="karpathy",
        label="Andrej Karpathy",
        observed_at="2026-07-09T00:00:00+00:00",
    )
    channels.observe_channel(
        conn,
        channel_id=channel_id,
        source="x_profile",
        metric="bio",
        value="I like to train neural nets.",
        observed_at="2026-07-09T00:00:00+00:00",
    )
    channels.observe_channel(
        conn,
        channel_id=channel_id,
        source="attention_source",
        metric="role",
        value="researcher",
        observed_at="2026-07-09T00:00:00+00:00",
    )
    registry.materialize_unlinked_channels(conn)

    row = registry.read_entities(conn)[0]
    assert set(row) == {
        "id",
        "slug",
        "kind",
        "kind_reason",
        "registry_state",
        "rejection_reason_code",
        "rejection_reason",
        "rejection_source",
        "rejection_evidence_url",
        "name",
        "followers_count",
        "bio",
        "channels",
    }
    assert row["kind_reason"] is None
    assert row["registry_state"] == "active"
    assert row["rejection_reason"] is None
    assert row["bio"] == "I like to train neural nets."
    assert row["followers_count"] is None
    assert "rank" not in row


def test_registry_sums_followers_across_an_organizations_x_channels(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    entity_id = channels.upsert_entity(
        conn,
        kind="organization",
        slug="example-org",
        name="Example Org",
        observed_at="2026-07-10T00:00:00+00:00",
    )
    for handle, followers in [("example", 100), ("exampledevs", 75)]:
        channel_id = channels.upsert_channel(
            conn,
            kind="x",
            key=handle,
            observed_at="2026-07-10T00:00:00+00:00",
        )
        channels.link_entity_channel(
            conn,
            entity_id=entity_id,
            channel_id=channel_id,
            relationship="official",
        )
        conn.execute(
            """INSERT INTO accounts
               (platform, handle, followers_count, first_seen_at, last_seen_at)
               VALUES ('x', ?, ?, '2026-07-10', '2026-07-10')""",
            (handle, followers),
        )
    conn.commit()

    entity = registry.read_entities(conn)[0]

    assert entity["followers_count"] == 175


def test_registry_rejection_is_reasoned_and_separate_from_kind(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    channels.upsert_channel(
        conn,
        kind="x",
        key="private_person",
        label="Private Person",
        observed_at="2026-07-10T00:00:00+00:00",
    )
    registry.materialize_unlinked_channels(conn)
    entity = conn.execute("SELECT * FROM entities").fetchone()
    conn.execute(
        "UPDATE entities SET kind = 'unsure' WHERE id = ?",
        (entity["id"],),
    )
    registry.reject_entity(
        conn,
        entity_id=entity["id"],
        reason_code="protected_x_account",
        reason="The X account has protected posts.",
        source="twitterapi_io",
        evidence_url="https://x.com/private_person",
        rejected_at="2026-07-10T00:00:00+00:00",
    )
    conn.commit()

    row = registry.read_entities(conn)[0]
    assert row["kind"] == "unsure"
    assert row["registry_state"] == "rejected"
    assert row["rejection_reason_code"] == "protected_x_account"
    assert row["rejection_reason"] == "The X account has protected posts."
    assert row["rejection_source"] == "twitterapi_io"
    assert registry.kind_counts(conn) == {
        "person": 0,
        "organization": 0,
        "unsure": 0,
        "unknown": 0,
        "rejected": 1,
    }


def test_merge_entity_moves_channels_without_losing_observations(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    registry.ensure_schema(conn)
    canonical_id = channels.upsert_entity(
        conn,
        kind="organization",
        slug="spacex",
        name="SpaceX",
        observed_at="2026-07-10T00:00:00+00:00",
    )
    duplicate_id = channels.upsert_entity(
        conn,
        kind="organization",
        slug="x-spacexai",
        name="SpaceXAI",
        observed_at="2026-07-10T00:00:00+00:00",
    )
    corporate_channel = channels.upsert_channel(
        conn,
        kind="x",
        key="spacex",
        observed_at="2026-07-10T00:00:00+00:00",
    )
    ai_channel = channels.upsert_channel(
        conn,
        kind="x",
        key="spacexai",
        observed_at="2026-07-10T00:00:00+00:00",
    )
    channels.link_entity_channel(
        conn,
        entity_id=canonical_id,
        channel_id=corporate_channel,
        relationship="official",
    )
    channels.link_entity_channel(
        conn,
        entity_id=duplicate_id,
        channel_id=ai_channel,
        relationship="identity",
    )
    channels.observe_channel(
        conn,
        channel_id=ai_channel,
        source="x_profile",
        metric="followers_count",
        value=2_000_000,
        observed_at="2026-07-10T00:00:00+00:00",
    )
    conn.commit()

    result = registry.merge_entity_into(
        conn,
        canonical_entity_id=canonical_id,
        duplicate_entity_id=duplicate_id,
        observed_at="2026-07-10T01:00:00+00:00",
    )

    assert result["moved_channels"] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM entities WHERE id = ?", (duplicate_id,)
    ).fetchone()[0] == 0
    handles = conn.execute(
        """SELECT c.key
           FROM channels c
           JOIN entity_channels ec ON ec.channel_id = c.id
           WHERE ec.entity_id = ? AND c.kind = 'x'
           ORDER BY c.key""",
        (canonical_id,),
    ).fetchall()
    assert [row["key"] for row in handles] == ["spacex", "spacexai"]
    assert conn.execute(
        "SELECT value FROM channel_observations WHERE channel_id = ?",
        (ai_channel,),
    ).fetchone()["value"] == "2000000"


def test_organization_groups_are_explicit_and_idempotent(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    registry.ensure_schema(conn)
    entities = {}
    for handle, name in [
        ("anthropicai", "Anthropic"),
        ("claudeai", "Claude"),
        ("claudedevs", "Claude Developers"),
    ]:
        entity_id = channels.upsert_entity(
            conn,
            kind="organization",
            slug=f"x-{handle}",
            name=name,
            observed_at="2026-07-10T00:00:00+00:00",
        )
        channel_id = channels.upsert_channel(
            conn,
            kind="x",
            key=handle,
            label=name,
            observed_at="2026-07-10T00:00:00+00:00",
        )
        channels.link_entity_channel(
            conn,
            entity_id=entity_id,
            channel_id=channel_id,
            relationship="identity",
        )
        channels.observe_channel(
            conn,
            channel_id=channel_id,
            source="x_profile",
            metric="bio",
            value=f"Bio for {handle}",
            observed_at="2026-07-10T00:00:00+00:00",
        )
        entities[handle] = entity_id
    conn.commit()
    groups = [
        {
            "canonical_handle": "anthropicai",
            "member_handles": ["claudeai", "claudedevs"],
            "reason": "Official Anthropic product accounts.",
            "evidence_url": "https://www.anthropic.com/claude",
        }
    ]

    first = registry.apply_organization_groups(conn, groups)
    conn.commit()
    second = registry.apply_organization_groups(conn, groups)
    conn.commit()

    assert first["merged_entities"] == 2
    assert first["moved_channels"] == 2
    assert second["merged_entities"] == 0
    assert second["already_grouped"] == 2
    assert conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 1
    handles = conn.execute(
        """SELECT c.key
           FROM channels c
           JOIN entity_channels ec ON ec.channel_id = c.id
           WHERE ec.entity_id = ? AND c.kind = 'x'
           ORDER BY c.key""",
        (entities["anthropicai"],),
    ).fetchall()
    assert [row["key"] for row in handles] == [
        "anthropicai",
        "claudeai",
        "claudedevs",
    ]
    assert conn.execute("SELECT COUNT(*) FROM entity_merge_audit").fetchone()[0] == 2
    assert registry.read_entities(conn)[0]["bio"] == "Bio for anthropicai"


def test_organization_group_dry_run_preserves_logical_snapshot(tmp_path):
    db = tmp_path / "test.db"
    conn = channels.connect(db)
    registry.ensure_schema(conn)
    for handle in ["openai", "openaidevs"]:
        entity_id = channels.upsert_entity(
            conn,
            kind="organization",
            slug=f"x-{handle}",
            name=handle,
            observed_at="2026-07-10T00:00:00+00:00",
        )
        channel_id = channels.upsert_channel(
            conn,
            kind="x",
            key=handle,
            observed_at="2026-07-10T00:00:00+00:00",
        )
        channels.link_entity_channel(
            conn,
            entity_id=entity_id,
            channel_id=channel_id,
            relationship="identity",
        )
    conn.commit()
    manifest = tmp_path / "groups.json"
    manifest.write_text(
        json.dumps(
            [
                {
                    "canonical_handle": "openai",
                    "member_handles": ["openaidevs"],
                    "reason": "Official OpenAI developer account.",
                    "evidence_url": "https://platform.openai.com/docs",
                }
            ]
        )
    )
    before = {
        "entities": conn.execute("SELECT * FROM entities ORDER BY id").fetchall(),
        "links": conn.execute(
            "SELECT * FROM entity_channels ORDER BY entity_id, channel_id"
        ).fetchall(),
        "audit": conn.execute("SELECT * FROM entity_merge_audit").fetchall(),
    }

    registry.main(
        [
            "apply-organization-groups",
            "--db",
            str(db),
            "--manifest",
            str(manifest),
            "--dry-run",
        ]
    )

    after = {
        "entities": conn.execute("SELECT * FROM entities ORDER BY id").fetchall(),
        "links": conn.execute(
            "SELECT * FROM entity_channels ORDER BY entity_id, channel_id"
        ).fetchall(),
        "audit": conn.execute("SELECT * FROM entity_merge_audit").fetchall(),
    }
    assert after == before


def test_organization_group_preflight_fails_before_mutation(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    registry.ensure_schema(conn)
    for handle in ["openai", "openaidevs"]:
        entity_id = channels.upsert_entity(
            conn,
            kind="organization",
            slug=f"x-{handle}",
            name=handle,
            observed_at="2026-07-10T00:00:00+00:00",
        )
        channel_id = channels.upsert_channel(
            conn,
            kind="x",
            key=handle,
            observed_at="2026-07-10T00:00:00+00:00",
        )
        channels.link_entity_channel(
            conn,
            entity_id=entity_id,
            channel_id=channel_id,
            relationship="identity",
        )
    conn.commit()
    groups = [
        {
            "canonical_handle": "openai",
            "member_handles": ["openaidevs", "missing_handle"],
            "reason": "Official OpenAI developer accounts.",
            "evidence_url": "https://platform.openai.com/docs",
        }
    ]

    with pytest.raises(ValueError, match="missing_handle"):
        registry.apply_organization_groups(conn, groups)

    assert conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM entity_merge_audit").fetchone()[0] == 0


def _write_coverage_snapshot(path, accounts):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE snapshot_run (
            snapshot_id TEXT PRIMARY KEY,
            cohort_sha256 TEXT NOT NULL,
            status TEXT NOT NULL
        );
        CREATE TABLE account (
            x_id TEXT PRIMARY KEY,
            handle TEXT NOT NULL,
            display_name TEXT,
            bio TEXT,
            followers_count INTEGER,
            first_observed_at TEXT NOT NULL,
            last_observed_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        "INSERT INTO snapshot_run VALUES ('snapshot-test', 'cohort-test', 'complete')"
    )
    for account in accounts:
        conn.execute(
            """INSERT INTO account
               (x_id, handle, display_name, bio, followers_count,
                first_observed_at, last_observed_at)
               VALUES (?, ?, ?, ?, ?, '2026-07-11T00:00:00+00:00',
                       '2026-07-11T01:00:00+00:00')""",
            account,
        )
    conn.commit()
    conn.close()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _coverage_manifest(snapshot_sha256, *, microsoft_x_id="1"):
    return {
        "schema_version": "organization-coverage-v1",
        "snapshot": {
            "snapshot_id": "snapshot-test",
            "cohort_sha256": "cohort-test",
            "database_sha256": snapshot_sha256,
        },
        "organizations": [
            {
                "slug": "microsoft",
                "name": "Microsoft",
                "reason": "Microsoft owns Visual Studio Code.",
                "evidence_url": "https://github.com/microsoft/vscode",
                "channels": [
                    {
                        "kind": "x",
                        "key": "microsoft",
                        "expected_x_id": microsoft_x_id,
                        "relationship": "identity",
                        "evidence_url": "https://x.com/microsoft",
                    },
                    {
                        "kind": "x",
                        "key": "code",
                        "expected_x_id": "2",
                        "relationship": "official",
                        "evidence_url": "https://github.com/microsoft/vscode",
                    },
                    {
                        "kind": "website",
                        "key": "https://www.microsoft.com/ai/",
                        "label": "Microsoft AI",
                        "relationship": "official",
                        "evidence_url": "https://www.microsoft.com/ai/",
                    },
                ],
                "merge_handles": [
                    {
                        "handle": "code",
                        "expected_entity_name": "Visual Studio Code",
                    }
                ],
            }
        ],
    }


def _make_coverage_duplicate(conn):
    entity_id = channels.upsert_entity(
        conn,
        kind="organization",
        slug="x-code",
        name="Visual Studio Code",
        observed_at="2026-07-11T00:00:00+00:00",
    )
    channel_id = channels.upsert_channel(
        conn,
        kind="x",
        key="code",
        label="Visual Studio Code",
        observed_at="2026-07-11T00:00:00+00:00",
    )
    channels.link_entity_channel(
        conn,
        entity_id=entity_id,
        channel_id=channel_id,
        relationship="identity",
    )
    conn.commit()


def test_organization_coverage_imports_merges_and_replays(tmp_path):
    snapshot_path = tmp_path / "snapshot.db"
    snapshot_sha256 = _write_coverage_snapshot(
        snapshot_path,
        [
            ("1", "microsoft", "Microsoft", "Parent bio", 1000),
            ("2", "code", "Visual Studio Code", "Product bio", 2000),
        ],
    )
    manifest = _coverage_manifest(snapshot_sha256)
    conn = channels.connect(tmp_path / "registry.db")
    registry.ensure_schema(conn)
    _make_coverage_duplicate(conn)

    first = registry.apply_organization_coverage(
        conn,
        manifest,
        snapshot_path=snapshot_path,
        observed_at="2026-07-11T02:00:00+00:00",
    )
    conn.commit()
    second = registry.apply_organization_coverage(
        conn,
        manifest,
        snapshot_path=snapshot_path,
        observed_at="2026-07-11T03:00:00+00:00",
    )
    conn.commit()

    assert first["created_entities"] == 1
    assert first["merged_entities"] == 1
    assert first["imported_accounts"] == 2
    assert second["created_entities"] == 0
    assert second["merged_entities"] == 0
    assert second["imported_accounts"] == 0
    assert second["already_grouped"] == 1
    microsoft = conn.execute(
        "SELECT * FROM entities WHERE slug = 'microsoft'"
    ).fetchone()
    assert microsoft["name"] == "Microsoft"
    assert conn.execute(
        "SELECT COUNT(*) FROM entities WHERE name = 'Visual Studio Code'"
    ).fetchone()[0] == 0
    rows = conn.execute(
        """SELECT c.kind, c.key, ec.relationship
           FROM channels c JOIN entity_channels ec ON ec.channel_id = c.id
           WHERE ec.entity_id = ? ORDER BY c.kind, c.key""",
        (microsoft["id"],),
    ).fetchall()
    assert [(row["kind"], row["key"], row["relationship"]) for row in rows] == [
        ("website", "https://www.microsoft.com/ai/", "official"),
        ("x", "code", "official"),
        ("x", "microsoft", "identity"),
    ]
    assert conn.execute(
        """SELECT COUNT(*) FROM account_source_facts
           WHERE source = 'following-snapshot:snapshot-test'
             AND fact = 'organization_coverage'"""
    ).fetchone()[0] == 2
    assert conn.execute(
        "SELECT COUNT(*) FROM entity_merge_audit"
    ).fetchone()[0] == 1


def test_organization_coverage_dry_run_and_conflict_are_non_mutating(
    tmp_path, capsys
):
    snapshot_path = tmp_path / "snapshot.db"
    snapshot_sha256 = _write_coverage_snapshot(
        snapshot_path,
        [
            ("1", "microsoft", "Microsoft", "Parent bio", 1000),
            ("2", "code", "Visual Studio Code", "Product bio", 2000),
        ],
    )
    registry_path = tmp_path / "registry.db"
    conn = channels.connect(registry_path)
    registry.ensure_schema(conn)
    _make_coverage_duplicate(conn)
    manifest_path = tmp_path / "coverage.json"
    manifest_path.write_text(json.dumps(_coverage_manifest(snapshot_sha256)))

    registry.main(
        [
            "apply-organization-coverage",
            "--db",
            str(registry_path),
            "--manifest",
            str(manifest_path),
            "--snapshot",
            str(snapshot_path),
            "--dry-run",
        ]
    )
    assert json.loads(capsys.readouterr().out)["dry_run"] is True
    assert conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0

    conflict = _coverage_manifest(snapshot_sha256, microsoft_x_id="wrong")
    with pytest.raises(ValueError, match="snapshot X ID mismatch"):
        registry.apply_organization_coverage(
            conn, conflict, snapshot_path=snapshot_path
        )
    assert conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0


def _make_relevance_candidate(conn, *, handle="irrelevant", name="Irrelevant"):
    account_id = conn.execute(
        """INSERT INTO accounts
           (platform, handle, display_name, followers_count,
            first_seen_at, last_seen_at)
           VALUES ('x', ?, ?, 5000, '2026-07-11', '2026-07-11')""",
        (handle, name),
    ).lastrowid
    conn.execute(
        """INSERT INTO account_source_facts
           (account_id, source, fact, value, observed_at)
           VALUES (?, 'test', 'list_member', 'test', '2026-07-11')""",
        (account_id,),
    )
    channel_id = channels.upsert_channel(
        conn,
        kind="x",
        key=handle,
        label=name,
        observed_at="2026-07-11T00:00:00+00:00",
    )
    entity_id = channels.upsert_entity(
        conn,
        kind="person",
        slug=f"x-{handle}",
        name=name,
        observed_at="2026-07-11T00:00:00+00:00",
    )
    channels.link_entity_channel(
        conn,
        entity_id=entity_id,
        channel_id=channel_id,
        relationship="identity",
    )
    channels.observe_channel(
        conn,
        channel_id=channel_id,
        source="x_profile",
        metric="bio",
        value="Clearly unrelated.",
        observed_at="2026-07-11T00:00:00+00:00",
    )
    conn.commit()
    return entity_id, channel_id, account_id


def _relevance_removal(entity_id, *, name="Irrelevant"):
    return {
        "entity_id": entity_id,
        "name": name,
        "kind": "person",
        "model_decision": "remove",
        "review_basis": "model_remove",
        "reason": "Clearly irrelevant to frontier AI.",
    }


def test_relevance_removal_deletes_exact_identity_evidence_and_replays(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    registry.ensure_schema(conn)
    entity_id, channel_id, account_id = _make_relevance_candidate(conn)

    first = registry.apply_relevance_removals(
        conn, [_relevance_removal(entity_id)]
    )
    conn.commit()
    second = registry.apply_relevance_removals(
        conn, [_relevance_removal(entity_id)]
    )
    conn.commit()

    assert first == {
        "requested": 1,
        "removed_entities": 1,
        "removed_channels": 1,
        "removed_accounts": 1,
        "already_removed": 0,
    }
    assert second["already_removed"] == 1
    assert second["removed_entities"] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM entities WHERE id = ?", (entity_id,)
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM channels WHERE id = ?", (channel_id,)
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM channel_observations WHERE channel_id = ?",
        (channel_id,),
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM accounts WHERE id = ?", (account_id,)
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM account_source_facts WHERE account_id = ?",
        (account_id,),
    ).fetchone()[0] == 0


def test_relevance_removal_preflight_prevents_partial_mutation(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    registry.ensure_schema(conn)
    first_id, _, _ = _make_relevance_candidate(
        conn, handle="first", name="First"
    )
    second_id, _, _ = _make_relevance_candidate(
        conn, handle="second", name="Second"
    )

    with pytest.raises(ValueError, match="does not match manifest identity"):
        registry.apply_relevance_removals(
            conn,
            [
                _relevance_removal(first_id, name="First"),
                _relevance_removal(second_id, name="Wrong"),
            ],
        )

    assert conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 2


def test_load_relevance_removal_accepts_explicit_keep_override(tmp_path):
    manifest = tmp_path / "removals.csv"
    manifest.write_text(
        "entity_id,name,kind,model_decision,review_basis,reason\n"
        "42,Retired Source,organization,keep,manual_override_from_keep,"
        "Source is now dormant.\n"
    )

    rows = registry.load_relevance_removals(manifest)

    assert rows == [
        {
            "entity_id": 42,
            "name": "Retired Source",
            "kind": "organization",
            "model_decision": "keep",
            "review_basis": "manual_override_from_keep",
            "reason": "Source is now dormant.",
        }
    ]


def _make_override_entity(conn, *, name="ikka", kind="organization"):
    entity_id = channels.upsert_entity(
        conn,
        kind=kind,
        slug="x-shahules786",
        name=name,
        observed_at="2026-07-11T00:00:00+00:00",
    )
    channel_id = channels.upsert_channel(
        conn,
        kind="x",
        key="shahules786",
        observed_at="2026-07-11T00:00:00+00:00",
    )
    channels.link_entity_channel(
        conn,
        entity_id=entity_id,
        channel_id=channel_id,
        relationship="identity",
    )
    conn.commit()
    return entity_id


def _entity_override(entity_id):
    return {
        "entity_id": entity_id,
        "expected_name": "ikka",
        "expected_kind": "organization",
        "target_name": "Shahul ES",
        "target_kind": "person",
        "reason": "The X account represents one individual.",
        "source": "test-review",
        "evidence_url": "https://example.com/team",
    }


def test_entity_override_updates_identity_records_reason_and_replays(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    registry.ensure_schema(conn)
    entity_id = _make_override_entity(conn)

    first = registry.apply_entity_overrides(conn, [_entity_override(entity_id)])
    conn.commit()
    second = registry.apply_entity_overrides(conn, [_entity_override(entity_id)])
    conn.commit()

    assert first == {"requested": 1, "overridden": 1, "already_overridden": 0}
    assert second == {"requested": 1, "overridden": 0, "already_overridden": 1}
    entity = conn.execute(
        "SELECT name, kind FROM entities WHERE id = ?", (entity_id,)
    ).fetchone()
    assert dict(entity) == {"name": "Shahul ES", "kind": "person"}
    assert conn.execute(
        "SELECT COUNT(*) FROM entity_override_audit WHERE entity_id = ?",
        (entity_id,),
    ).fetchone()[0] == 1
    read = next(item for item in registry.read_entities(conn) if item["id"] == entity_id)
    assert read["kind_reason"] == "The X account represents one individual."


def test_entity_override_dry_run_preserves_entity_and_audit(tmp_path):
    db = tmp_path / "test.db"
    conn = channels.connect(db)
    registry.ensure_schema(conn)
    entity_id = _make_override_entity(conn)
    manifest = tmp_path / "overrides.json"
    manifest.write_text(json.dumps([_entity_override(entity_id)]))

    registry.main(
        [
            "apply-entity-overrides",
            "--db",
            str(db),
            "--manifest",
            str(manifest),
            "--dry-run",
        ]
    )

    entity = conn.execute(
        "SELECT name, kind FROM entities WHERE id = ?", (entity_id,)
    ).fetchone()
    assert dict(entity) == {"name": "ikka", "kind": "organization"}
    assert conn.execute("SELECT COUNT(*) FROM entity_override_audit").fetchone()[0] == 0
