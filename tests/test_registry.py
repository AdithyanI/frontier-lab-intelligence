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


def test_registry_read_model_excludes_attention_and_source_fields(tmp_path):
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
        "bio",
        "channels",
    }
    assert row["kind_reason"] is None
    assert row["registry_state"] == "active"
    assert row["rejection_reason"] is None
    assert row["bio"] == "I like to train neural nets."
    assert "rank" not in row


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
