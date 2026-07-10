"""Tests for the hand-curated lab registry."""

from fli import graph, labs


def test_seed_links_org_accounts_and_is_idempotent(tmp_path):
    graph.connect(tmp_path / "test.db").close()  # create accounts schema
    conn = labs.connect(tmp_path / "test.db")
    # one org account already observed in the graph, one not
    conn.execute(
        """INSERT INTO accounts (platform, handle, display_name, first_seen_at, last_seen_at)
           VALUES ('x', 'openai', 'OpenAI', '2026-07-08', '2026-07-08')"""
    )

    counts = labs.seed(conn)
    assert counts["labs"] == len(labs.SEED_LABS)
    assert counts["x_linked"] == 1  # only openai exists in accounts

    row = conn.execute("SELECT * FROM labs WHERE slug = 'openai'").fetchone()
    assert row["status"] == "frontier"
    assert row["x_account_id"] is not None
    entity = conn.execute("SELECT * FROM entities WHERE slug = 'openai'").fetchone()
    assert entity["kind"] == "organization"
    x_channel = conn.execute(
        """SELECT c.* FROM channels c
           JOIN entity_channels ec ON ec.channel_id = c.id
           WHERE ec.entity_id = ? AND c.kind = 'x'""",
        (entity["id"],),
    ).fetchone()
    assert x_channel["key"] == "openai"
    linked_channels = conn.execute(
        "SELECT COUNT(*) AS n FROM entity_channels WHERE entity_id = ?",
        (entity["id"],),
    ).fetchone()["n"]
    assert linked_channels >= 4
    ssi = conn.execute("SELECT * FROM labs WHERE slug = 'ssi'").fetchone()
    assert ssi["status"] == "emerging"
    assert ssi["x_account_id"] is None  # not observed in this test graph

    # reseed must not duplicate
    counts2 = labs.seed(conn)
    assert counts2["labs"] == counts["labs"]


def test_seed_can_claim_multiple_x_accounts_for_one_organization(tmp_path):
    db = tmp_path / "test.db"
    conn = labs.connect(db)
    conn.executemany(
        """INSERT INTO accounts
           (platform, handle, display_name, first_seen_at, last_seen_at)
           VALUES ('x', ?, ?, '2026-07-10', '2026-07-10')""",
        [("spacex", "SpaceX"), ("spacexai", "SpaceXAI")],
    )
    lab = {
        "slug": "spacex",
        "name": "SpaceX",
        "status": "frontier",
        "x_handle": "spacexai",
        "x_handles": ["spacex", "spacexai"],
        "website": "https://x.ai",
        "blog_feed": None,
        "github_org": "xai-org",
        "arxiv_query": 'all:"xAI"',
        "notes": "Tracks the AI unit inside SpaceX.",
    }

    counts = labs.seed(conn, labs=[lab])

    assert counts["configured_x_channels"] == 2
    entity = conn.execute(
        "SELECT * FROM entities WHERE slug = 'spacex'"
    ).fetchone()
    handles = conn.execute(
        """SELECT c.key
           FROM channels c
           JOIN entity_channels ec ON ec.channel_id = c.id
           WHERE ec.entity_id = ? AND c.kind = 'x'
           ORDER BY c.key""",
        (entity["id"],),
    ).fetchall()
    assert [row["key"] for row in handles] == ["spacex", "spacexai"]
    assert conn.execute(
        "SELECT COUNT(*) FROM entities WHERE kind = 'organization'"
    ).fetchone()[0] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM channels WHERE kind = 'arxiv'"
    ).fetchone()[0] == 0
