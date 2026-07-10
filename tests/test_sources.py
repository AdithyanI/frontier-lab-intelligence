import json
from io import BytesIO
from urllib import error

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
            "userName": "adithyan_ai",
            "id": "1296368039768842240",
            "name": "Adithyan",
            "description": "Founder",
            "followers": 752,
        }

    def fetch_user(self, *, username):
        assert username == "adithyan_ai"
        return self.profile

    def iter_following_pages(self, *, username, page_size):
        assert username == "adithyan_ai"
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
        username="@adithyan_ai",
        source="adi_following",
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
        username="adithyan_ai",
        source="adi_following",
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
        "SELECT * FROM accounts WHERE handle = 'adithyan_ai'"
    ).fetchone()
    assert source_account["display_name"] == "Adithyan"
    assert source_account["x_id"] == "1296368039768842240"
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
           WHERE edge.source = 'adi_following' AND target.handle = 'karpathy'"""
    ).fetchone()
    assert dict(edge) == {
        "source_handle": "adithyan_ai",
        "target_handle": "karpathy",
        "relationship": "follows",
    }
    fact = conn.execute(
        """SELECT f.fact, f.value
           FROM account_source_facts f
           JOIN accounts a ON a.id = f.account_id
           WHERE a.handle = 'karpathy' AND f.source = 'adi_following'"""
    ).fetchone()
    assert dict(fact) == {"fact": "followed_by", "value": "adithyan_ai"}
    assert conn.execute(
        "SELECT COUNT(*) AS n FROM channels WHERE kind = 'x'"
    ).fetchone()["n"] == 3
    assert conn.execute(
        "SELECT COUNT(*) AS n FROM entities WHERE kind = 'unknown'"
    ).fetchone()["n"] == 3


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
        "username": "adithyan_ai",
        "source": "adi_following",
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
           WHERE edge.source = 'adi_following'
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
            "adithyan_ai",
            "--source",
            "adi_following",
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
            "adithyan_ai",
            "--source",
            "adi_following",
            "--dry-run",
        ]
    )

    assert code == 0
    assert captured["page_sleep_seconds"] == 0.0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"
