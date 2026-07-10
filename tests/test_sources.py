import json
from io import BytesIO
from urllib import error

import pytest

from fli import sources


class FakeClient:
    def __init__(self, pages):
        self.pages = pages

    def iter_member_pages(self, *, list_id):
        assert list_id == "1585430245762441216"
        for page in self.pages:
            yield page


class FakeFollowingClient:
    def __init__(self, pages, profile=None):
        self.pages = pages
        self.profile = profile or {
            "userName": "trusted_seed",
            "id": "123456789",
            "name": "Trusted Seed",
            "description": "Researcher",
            "followers": 10_000,
        }

    def fetch_user(self, *, username):
        assert username == "trusted_seed"
        return self.profile

    def iter_following_pages(self, *, username, page_size):
        assert username == "trusted_seed"
        assert page_size == 200
        for page in self.pages:
            yield page


def test_import_x_list_dry_run_does_not_write(tmp_path):
    db = tmp_path / "test.db"
    fake = FakeClient(
        [
            [
                {
                    "userName": "OpenAI",
                    "id": "1",
                    "name": "OpenAI",
                    "description": "AI research lab",
                    "followers_count": 10,
                }
            ],
            [{"userName": "karpathy", "id": "2", "name": "Andrej Karpathy"}],
        ]
    )

    data = sources.run_import_x_list(
        db_path=str(db),
        list_id="1585430245762441216",
        source="ai_high_signal",
        key_file=tmp_path / "missing",
        dry_run=True,
        timeout_seconds=1,
        page_sleep_seconds=0,
        client=fake,
    )

    assert data["dry_run"] is True
    assert data["pages_fetched"] == 2
    assert data["unique_handles"] == 2
    assert data["would_create_accounts"] == 2

    conn = sources.channels.connect(db)
    assert conn.execute("SELECT COUNT(*) AS n FROM accounts").fetchone()["n"] == 0


def test_import_x_list_writes_accounts_facts_and_channels(tmp_path):
    db = tmp_path / "test.db"
    fake = FakeClient(
        [
            [
                {
                    "userName": "OpenAI",
                    "id": "1",
                    "name": "OpenAI",
                    "description": "AI research lab",
                    "followers": 10,
                }
            ]
        ]
    )

    data = sources.run_import_x_list(
        db_path=str(db),
        list_id="1585430245762441216",
        source="ai_high_signal",
        key_file=tmp_path / "missing",
        dry_run=False,
        timeout_seconds=1,
        page_sleep_seconds=0,
        client=fake,
    )

    assert data["created_accounts"] == 1
    assert data["source_facts_written"] == 1
    conn = sources.channels.connect(db)
    account = conn.execute("SELECT * FROM accounts WHERE handle = 'openai'").fetchone()
    assert account["display_name"] == "OpenAI"
    fact = conn.execute(
        """SELECT * FROM account_source_facts
           WHERE account_id = ? AND source = 'ai_high_signal'""",
        (account["id"],),
    ).fetchone()
    assert fact["fact"] == "list_member"
    assert fact["value"] == "1585430245762441216"
    channel = conn.execute("SELECT * FROM channels WHERE key = 'openai'").fetchone()
    assert channel["kind"] == "x"
    entity = conn.execute(
        """SELECT e.* FROM entities e
           JOIN entity_channels ec ON ec.entity_id = e.id
           WHERE ec.channel_id = ?""",
        (channel["id"],),
    ).fetchone()
    assert entity["kind"] == "unknown"


def test_sources_cli_missing_key_returns_json_error(tmp_path, capsys):
    code = sources.main(
        [
            "import-x-list",
            "--list-id",
            "1585430245762441216",
            "--source",
            "ai_high_signal",
            "--key-file",
            str(tmp_path / "missing"),
        ]
    )

    assert code == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "E_SECRET_MISSING"


def test_persist_x_profile_is_idempotent_and_materializes_entity(tmp_path):
    conn = sources.channels.connect(tmp_path / "test.db")
    profile = {
        "userName": "Example",
        "id": "42",
        "name": "Example Person",
        "description": "I build systems.",
        "followers": 2_500,
        "protected": False,
    }

    first = sources.persist_x_profile(
        conn,
        profile=profile,
        observed_at="2026-07-10T00:00:00+00:00",
    )
    second = sources.persist_x_profile(
        conn,
        profile=profile,
        observed_at="2026-07-10T00:00:00+00:00",
    )

    assert first["handle"] == "example"
    assert first["account_created"] is True
    assert first["entity_created"] is True
    assert second["account_created"] is False
    assert second["entity_created"] is False
    assert second["entity_id"] == first["entity_id"]
    assert conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 1
    assert conn.execute(
        """SELECT value FROM account_source_facts
           WHERE source = 'x_account_onboarding'
             AND fact = 'submitted_handle'"""
    ).fetchone()[0] == "example"
    observations = {
        row["metric"]: row["value"]
        for row in conn.execute(
            "SELECT metric, value FROM channel_observations"
        ).fetchall()
    }
    assert observations == {
        "bio": "I build systems.",
        "followers_count": "2500",
    }


def test_import_x_following_dry_run_does_not_write(tmp_path):
    db = tmp_path / "test.db"
    fake = FakeFollowingClient(
        [
            [
                {
                    "userName": "karpathy",
                    "id": "2",
                    "name": "Andrej Karpathy",
                    "description": "AI",
                    "followers": 100,
                }
            ],
            [{"userName": "OpenAI", "id": "1", "name": "OpenAI"}],
        ]
    )

    data = sources.run_import_x_following(
        db_path=str(db),
        username="@trusted_seed",
        source="trusted_seed_following",
        key_file=tmp_path / "missing",
        dry_run=True,
        timeout_seconds=1,
        page_sleep_seconds=0,
        client=fake,
    )

    assert data["dry_run"] is True
    assert data["pages_fetched"] == 2
    assert data["page_counts"] == [1, 1]
    assert data["unique_handles"] == 2
    assert data["would_create_accounts"] == 3
    assert data["would_write_edges"] == 2
    assert data["estimated_provider_credits"] == 120

    conn = sources.channels.connect(db)
    assert conn.execute("SELECT COUNT(*) AS n FROM accounts").fetchone()["n"] == 0


def test_import_x_following_writes_profiles_facts_edges_and_channels(tmp_path):
    db = tmp_path / "test.db"
    fake = FakeFollowingClient(
        [
            [
                {
                    "userName": "karpathy",
                    "id": "2",
                    "name": "Andrej Karpathy",
                    "description": "AI",
                    "followers": 100,
                },
                {
                    "userName": "OpenAI",
                    "id": "1",
                    "name": "OpenAI",
                    "description": "AI research lab",
                    "followers": 10,
                },
            ]
        ]
    )

    data = sources.run_import_x_following(
        db_path=str(db),
        username="trusted_seed",
        source="trusted_seed_following",
        key_file=tmp_path / "missing",
        dry_run=False,
        timeout_seconds=1,
        page_sleep_seconds=0,
        client=fake,
    )

    assert data["created_accounts"] == 3
    assert data["source_facts_written"] == 2
    assert data["edges_written"] == 2
    conn = sources.channels.connect(db)
    source_account = conn.execute(
        "SELECT * FROM accounts WHERE handle = 'trusted_seed'"
    ).fetchone()
    assert source_account["display_name"] == "Trusted Seed"
    assert source_account["x_id"] == "123456789"
    assert conn.execute(
        "SELECT followers_count FROM accounts WHERE handle = 'openai'"
    ).fetchone()["followers_count"] == 10
    edge = conn.execute(
        """SELECT source_account.handle AS source_handle,
                  target.handle AS target_handle,
                  edge.relationship
           FROM graph_edges edge
           JOIN accounts source_account ON source_account.id = edge.from_account_id
           JOIN accounts target ON target.id = edge.to_account_id
           WHERE edge.source = 'trusted_seed_following' AND target.handle = 'karpathy'"""
    ).fetchone()
    assert dict(edge) == {
        "source_handle": "trusted_seed",
        "target_handle": "karpathy",
        "relationship": "follows",
    }
    fact = conn.execute(
        """SELECT f.fact, f.value
           FROM account_source_facts f
           JOIN accounts a ON a.id = f.account_id
           WHERE a.handle = 'karpathy' AND f.source = 'trusted_seed_following'"""
    ).fetchone()
    assert dict(fact) == {"fact": "followed_by", "value": "trusted_seed"}
    assert conn.execute(
        "SELECT COUNT(*) AS n FROM channels WHERE kind = 'x'"
    ).fetchone()["n"] == 2
    assert conn.execute(
        "SELECT COUNT(*) AS n FROM entities WHERE kind = 'unknown'"
    ).fetchone()["n"] == 2
    assert conn.execute(
        "SELECT COUNT(*) AS n FROM channels WHERE key = 'trusted_seed'"
    ).fetchone()["n"] == 0


def test_import_x_following_replaces_stale_edges_but_keeps_accounts(tmp_path):
    db = tmp_path / "test.db"
    first = FakeFollowingClient(
        [[{"userName": "first", "id": "1"}, {"userName": "second", "id": "2"}]]
    )
    second = FakeFollowingClient(
        [[{"userName": "second", "id": "2"}, {"userName": "third", "id": "3"}]]
    )
    common = {
        "db_path": str(db),
        "username": "trusted_seed",
        "source": "trusted_seed_following",
        "key_file": tmp_path / "missing",
        "dry_run": False,
        "timeout_seconds": 1,
        "page_sleep_seconds": 0,
    }

    sources.run_import_x_following(**common, client=first)
    data = sources.run_import_x_following(**common, client=second)

    assert data["created_accounts"] == 1
    assert data["edges_removed"] == 1
    assert data["source_facts_removed"] == 1
    conn = sources.channels.connect(db)
    targets = conn.execute(
        """SELECT target.handle
           FROM graph_edges edge
           JOIN accounts target ON target.id = edge.to_account_id
           WHERE edge.source = 'trusted_seed_following'
           ORDER BY target.handle"""
    ).fetchall()
    assert [row["handle"] for row in targets] == ["second", "third"]
    assert conn.execute(
        "SELECT COUNT(*) AS n FROM accounts"
    ).fetchone()["n"] == 4


def test_sources_following_cli_missing_key_returns_json_error(tmp_path, capsys):
    code = sources.main(
        [
            "import-x-following",
            "--username",
            "trusted_seed",
            "--source",
            "trusted_seed_following",
            "--key-file",
            str(tmp_path / "missing"),
        ]
    )

    assert code == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "sources import-x-following"
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "E_SECRET_MISSING"


def test_twitter_api_io_client_retries_429_using_retry_after(monkeypatch):
    def fake_urlopen(_request, timeout):
        assert timeout == 1
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    class FakeResponse:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return self.body

    responses = iter(
        [
            error.HTTPError(
                "https://example.test",
                429,
                "rate limited",
                {"Retry-After": "0"},
                BytesIO(b"{}"),
            ),
            FakeResponse(b'{"status":"success","data":{"userName":"adi"}}'),
        ]
    )
    delays = []
    monkeypatch.setattr(sources.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(sources.time, "sleep", delays.append)

    client = sources.TwitterApiIoClient(api_key="secret", timeout=1)
    payload = client._fetch_json("https://example.test")

    assert payload["status"] == "success"
    assert delays == [0.0]


def test_recent_authored_posts_filter_retweets_replies_and_paginate(monkeypatch):
    client = sources.TwitterApiIoClient(api_key="secret", page_sleep_seconds=0)
    pages = iter(
        [
            {
                "data": {
                    "tweets": [
                        {
                            "id": "retweet",
                            "text": "RT @someone: borrowed words",
                            "retweeted_tweet": {"id": "source"},
                        },
                        {
                            "id": "original",
                            "text": "I built &amp; shipped this.",
                            "createdAt": "2026-07-10T00:00:00Z",
                        },
                    ],
                    "has_next_page": True,
                    "next_cursor": "next",
                }
            },
            {
                "tweets": [
                    {
                        "id": "reply",
                        "text": "A reply",
                        "isReply": True,
                    },
                    {
                        "id": "quote",
                        "text": "My own quote commentary",
                        "quoted_tweet": {"id": "quoted"},
                        "twitterUrl": "https://x.com/example/status/quote",
                    },
                ],
                "has_next_page": False,
            },
        ]
    )
    calls = []

    def fake_fetch_page(*, username, cursor=None):
        calls.append((username, cursor))
        return next(pages)

    monkeypatch.setattr(client, "fetch_recent_tweets_page", fake_fetch_page)
    monkeypatch.setattr(
        client,
        "fetch_user",
        lambda *, username: {"userName": username, "protected": False},
    )

    posts = client.fetch_recent_authored_posts(username="@Example", limit=2)

    assert calls == [("example", None), ("example", "next")]
    assert [post["id"] for post in posts] == ["original", "quote"]
    assert posts[0]["text"] == "I built & shipped this."
    assert posts[1]["post_type"] == "quote"


def test_recent_authored_posts_reject_protected_account(monkeypatch):
    client = sources.TwitterApiIoClient(api_key="secret", page_sleep_seconds=0)
    timeline_called = False

    monkeypatch.setattr(
        client,
        "fetch_user",
        lambda *, username: {"userName": username, "protected": True},
    )

    def fake_timeline(**_kwargs):
        nonlocal timeline_called
        timeline_called = True
        return {"tweets": []}

    monkeypatch.setattr(client, "fetch_recent_tweets_page", fake_timeline)

    with pytest.raises(sources.SourceCliError) as exc_info:
        client.fetch_recent_authored_posts(username="private_user")

    assert exc_info.value.code == "E_ACCOUNT_PROTECTED"
    assert timeline_called is False


def test_following_cli_defaults_to_no_page_sleep(monkeypatch, capsys):
    captured = {}

    def fake_run_import_x_following(**kwargs):
        captured.update(kwargs)
        return {"unique_handles": 0, "pages_fetched": 0, "dry_run": True}

    monkeypatch.setattr(
        sources,
        "run_import_x_following",
        fake_run_import_x_following,
    )
    code = sources.main(
        [
            "import-x-following",
            "--username",
            "trusted_seed",
            "--source",
            "trusted_seed_following",
            "--dry-run",
        ]
    )

    assert code == 0
    assert captured["page_sleep_seconds"] == 0.0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"
