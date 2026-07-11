import json

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
