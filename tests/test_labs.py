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
    assert entity["kind"] == "lab"
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
