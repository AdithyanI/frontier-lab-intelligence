import json

from fli import sources


class FakeClient:
    def __init__(self, pages):
        self.pages = pages

    def iter_member_pages(self, *, list_id):
        assert list_id == "1585430245762441216"
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
                    "followers": 10,
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
