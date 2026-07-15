import json
from datetime import datetime, timezone
from urllib import parse

from fli import channels, registry, sources, x_content, x_daily_collection
from fli.cli import main as root_main


def _registry(path, *accounts):
    conn = channels.connect(path)
    try:
        for account in accounts:
            entity_id = channels.upsert_entity(
                conn,
                kind=account.get("kind", "person"),
                slug=f"person-{account['handle']}",
                name=account.get("name", account["handle"].title()),
            )
            channel_id = channels.upsert_channel(
                conn,
                kind="x",
                key=account["handle"],
            )
            channels.link_entity_channel(
                conn,
                entity_id=entity_id,
                channel_id=channel_id,
                relationship="identity",
            )
            if account.get("zero_following"):
                channels.observe_channel(
                    conn,
                    channel_id=channel_id,
                    source="test_profile",
                    metric="following_count",
                    value=0,
                    observed_at="2026-07-12T00:00:00+00:00",
                )
            if account.get("rejected"):
                registry.reject_entity(
                    conn,
                    entity_id=entity_id,
                    reason_code=account["rejected"],
                    reason="Not an active public source.",
                    source="test",
                )
        conn.commit()
    finally:
        conn.close()


def _timeline_payload(*, tweets, has_next=False, next_cursor=None):
    return {
        "data": {
            "tweets": tweets,
            "has_next_page": has_next,
            "next_cursor": next_cursor,
        }
    }


def _cache(client, handle, payload, cursor=None):
    client._store_raw(
        url=x_daily_collection._timeline_url(handle, cursor),
        payload=payload,
    )


def test_daily_timeline_contract_includes_authored_replies():
    url = x_daily_collection._timeline_url("Example_User", "next page")
    query = parse.parse_qs(parse.urlparse(url).query)

    assert query == {
        "userName": ["Example_User"],
        "includeReplies": ["true"],
        "cursor": ["next page"],
    }


def test_freeze_is_stable_and_excludes_rejected_but_not_zero_following(tmp_path):
    registry_path = tmp_path / "registry.db"
    manifest_path = tmp_path / "manifest.db"
    _registry(
        registry_path,
        {"handle": "active", "zero_following": True},
        {"handle": "private", "rejected": "protected_x_account"},
        {"handle": "irrelevant", "rejected": "manual_scope_rejection"},
    )

    first = x_daily_collection.freeze_run(
        registry_path=registry_path,
        manifest_path=manifest_path,
        start_day="2026-07-11",
        end_day="2026-07-12",
    )
    second = x_daily_collection.freeze_run(
        registry_path=registry_path,
        manifest_path=manifest_path,
        start_day="2026-07-11",
        end_day="2026-07-12",
    )

    assert first["run_id"] == second["run_id"]
    assert first["cohort_sha256"] == second["cohort_sha256"]
    assert first["cohort_count"] == 1
    assert first["excluded_rejected_count"] == 2
    assert first["excluded_protected_count"] == 1
    conn = x_daily_collection.connect_manifest(manifest_path)
    assert conn.execute(
        "SELECT handle FROM collection_account"
    ).fetchone()[0] == "active"


def test_plan_proves_cached_date_coverage_without_provider_call(tmp_path):
    registry_path = tmp_path / "registry.db"
    raw_path = tmp_path / "raw.db"
    manifest_path = tmp_path / "manifest.db"
    _registry(registry_path, {"handle": "alpha"})
    client = x_content.TwitterContentClient(api_key="test", db_path=raw_path)
    _cache(
        client,
        "alpha",
        _timeline_payload(
            tweets=[
                {
                    "id": "old",
                    "createdAt": "Fri Jul 10 23:00:00 +0000 2026",
                    "text": "old boundary",
                }
            ]
        ),
    )

    result = x_daily_collection.plan_collection(
        registry_path=registry_path,
        raw_path=raw_path,
        manifest_path=manifest_path,
        start_day="2026-07-11",
        end_day="2026-07-12",
    )

    assert result["status"] == "complete"
    assert result["statuses"] == {"cached": 1}
    assert result["provider_requests"] == 0
    conn = x_daily_collection.connect_manifest(manifest_path)
    account = conn.execute("SELECT * FROM collection_account").fetchone()
    assert account["reached_start_boundary"] == 1
    assert account["page_count"] == 1


def test_execute_fetches_only_missing_account_and_resumes_without_refetch(tmp_path):
    registry_path = tmp_path / "registry.db"
    raw_path = tmp_path / "raw.db"
    manifest_path = tmp_path / "manifest.db"
    _registry(registry_path, {"handle": "alpha"}, {"handle": "beta"})
    client = x_content.TwitterContentClient(
        api_key="test", db_path=raw_path, refresh=True
    )
    payload = _timeline_payload(
        tweets=[
            {
                "id": "old",
                "createdAt": "Fri Jul 10 23:00:00 +0000 2026",
                "text": "old boundary",
            }
        ]
    )
    _cache(client, "alpha", payload)
    calls = []

    def upstream(url):
        calls.append(parse.parse_qs(parse.urlparse(url).query)["userName"][0])
        return payload

    client._fetch_upstream = upstream
    first = x_daily_collection.execute_collection(
        client=client,
        registry_path=registry_path,
        raw_path=raw_path,
        manifest_path=manifest_path,
        start_day="2026-07-11",
        end_day="2026-07-12",
    )
    second = x_daily_collection.execute_collection(
        client=client,
        registry_path=registry_path,
        raw_path=raw_path,
        manifest_path=manifest_path,
        start_day="2026-07-11",
        end_day="2026-07-12",
    )

    assert calls == ["beta"]
    assert first["status"] == second["status"] == "complete"
    assert first["provider_requests"] == second["provider_requests"] == 1
    assert second["statuses"] == {"cached": 1, "fetched": 1}


def test_execute_follows_cursor_chain_until_start_boundary(tmp_path):
    registry_path = tmp_path / "registry.db"
    raw_path = tmp_path / "raw.db"
    manifest_path = tmp_path / "manifest.db"
    _registry(registry_path, {"handle": "alpha"})
    client = x_content.TwitterContentClient(
        api_key="test", db_path=raw_path, refresh=True
    )
    calls = []

    def upstream(url):
        query = parse.parse_qs(parse.urlparse(url).query)
        cursor = query.get("cursor", [None])[0]
        calls.append(cursor)
        if cursor is None:
            return _timeline_payload(
                tweets=[
                    {
                        "id": "new",
                        "createdAt": "Sun Jul 12 12:00:00 +0000 2026",
                        "text": "new",
                    }
                ],
                has_next=True,
                next_cursor="page-2",
            )
        return _timeline_payload(
            tweets=[
                {
                    "id": "old",
                    "createdAt": "Fri Jul 10 23:00:00 +0000 2026",
                    "text": "old",
                }
            ]
        )

    client._fetch_upstream = upstream
    result = x_daily_collection.execute_collection(
        client=client,
        registry_path=registry_path,
        raw_path=raw_path,
        manifest_path=manifest_path,
        start_day="2026-07-11",
        end_day="2026-07-12",
    )

    assert result["status"] == "complete"
    assert result["provider_requests"] == 2
    assert calls == [None, "page-2"]
    conn = x_daily_collection.connect_manifest(manifest_path)
    assert conn.execute(
        "SELECT page_count FROM collection_account"
    ).fetchone()[0] == 2


def test_execute_stops_when_terminal_page_leaves_an_inert_cursor(tmp_path):
    registry_path = tmp_path / "registry.db"
    raw_path = tmp_path / "raw.db"
    manifest_path = tmp_path / "manifest.db"
    _registry(registry_path, {"handle": "alpha"})
    client = x_content.TwitterContentClient(
        api_key="test", db_path=raw_path, refresh=True
    )
    calls = []

    def upstream(url):
        calls.append(url)
        return _timeline_payload(
            tweets=[], has_next=False, next_cursor="stale-terminal-cursor"
        )

    client._fetch_upstream = upstream
    result = x_daily_collection.execute_collection(
        client=client,
        registry_path=registry_path,
        raw_path=raw_path,
        manifest_path=manifest_path,
        start_day="2026-07-11",
        end_day="2026-07-12",
    )

    assert result["status"] == "complete"
    assert result["provider_requests"] == 1
    assert len(calls) == 1
    conn = x_daily_collection.connect_manifest(manifest_path)
    account = conn.execute("SELECT * FROM collection_account").fetchone()
    assert account["reached_terminal_page"] == 1
    assert account["page_count"] == 1


def test_cached_terminal_page_ignores_an_inert_cursor(tmp_path):
    registry_path = tmp_path / "registry.db"
    raw_path = tmp_path / "raw.db"
    manifest_path = tmp_path / "manifest.db"
    _registry(registry_path, {"handle": "alpha"})
    client = x_content.TwitterContentClient(api_key="test", db_path=raw_path)
    _cache(
        client,
        "alpha",
        _timeline_payload(
            tweets=[], has_next=False, next_cursor="stale-terminal-cursor"
        ),
    )

    result = x_daily_collection.plan_collection(
        registry_path=registry_path,
        raw_path=raw_path,
        manifest_path=manifest_path,
        start_day="2026-07-11",
        end_day="2026-07-12",
    )

    assert result["status"] == "complete"
    assert result["statuses"] == {"cached": 1}
    assert result["provider_requests"] == 0
    conn = x_daily_collection.connect_manifest(manifest_path)
    account = conn.execute("SELECT * FROM collection_account").fetchone()
    assert account["reached_terminal_page"] == 1
    assert account["page_count"] == 1


def test_cached_malformed_success_payload_fails_closed(tmp_path):
    registry_path = tmp_path / "registry.db"
    raw_path = tmp_path / "raw.db"
    manifest_path = tmp_path / "manifest.db"
    _registry(registry_path, {"handle": "alpha"})
    client = x_content.TwitterContentClient(api_key="test", db_path=raw_path)
    _cache(client, "alpha", {"data": {}, "status": "success"})

    result = x_daily_collection.plan_collection(
        registry_path=registry_path,
        raw_path=raw_path,
        manifest_path=manifest_path,
        start_day="2026-07-11",
        end_day="2026-07-12",
    )

    assert result["status"] == "planned"
    assert result["statuses"] == {"pending": 1}
    conn = x_daily_collection.connect_manifest(manifest_path)
    account = conn.execute("SELECT * FROM collection_account").fetchone()
    assert account["coverage_reason"] == (
        "cached provider response is missing the tweets array"
    )


def test_cached_tweets_array_with_non_object_item_fails_closed(tmp_path):
    registry_path = tmp_path / "registry.db"
    raw_path = tmp_path / "raw.db"
    manifest_path = tmp_path / "manifest.db"
    _registry(registry_path, {"handle": "alpha"})
    client = x_content.TwitterContentClient(api_key="test", db_path=raw_path)
    _cache(client, "alpha", {"data": {"tweets": [None]}})

    result = x_daily_collection.plan_collection(
        registry_path=registry_path,
        raw_path=raw_path,
        manifest_path=manifest_path,
        start_day="2026-07-11",
        end_day="2026-07-12",
    )

    assert result["status"] == "planned"
    assert result["statuses"] == {"pending": 1}


def test_cached_unparseable_tweet_timestamp_fails_closed(tmp_path):
    registry_path = tmp_path / "registry.db"
    raw_path = tmp_path / "raw.db"
    manifest_path = tmp_path / "manifest.db"
    _registry(registry_path, {"handle": "alpha"})
    client = x_content.TwitterContentClient(api_key="test", db_path=raw_path)
    _cache(
        client,
        "alpha",
        _timeline_payload(tweets=[{"id": "missing-created-at", "text": "bad"}]),
    )

    result = x_daily_collection.plan_collection(
        registry_path=registry_path,
        raw_path=raw_path,
        manifest_path=manifest_path,
        start_day="2026-07-11",
        end_day="2026-07-12",
    )

    assert result["status"] == "planned"
    assert result["statuses"] == {"pending": 1}
    conn = x_daily_collection.connect_manifest(manifest_path)
    account = conn.execute("SELECT * FROM collection_account").fetchone()
    assert account["coverage_reason"] == (
        "cached provider response contains an unparseable tweet timestamp"
    )


def test_live_malformed_success_payload_fails_closed(tmp_path):
    registry_path = tmp_path / "registry.db"
    raw_path = tmp_path / "raw.db"
    manifest_path = tmp_path / "manifest.db"
    _registry(registry_path, {"handle": "alpha"})
    client = x_content.TwitterContentClient(
        api_key="test", db_path=raw_path, refresh=True
    )
    client._fetch_upstream = lambda _url: {"data": {}, "status": "success"}

    result = x_daily_collection.execute_collection(
        client=client,
        registry_path=registry_path,
        raw_path=raw_path,
        manifest_path=manifest_path,
        start_day="2026-07-11",
        end_day="2026-07-12",
    )

    assert result["status"] == "partial"
    assert result["statuses"] == {"failed": 1}
    assert result["failures"] == 1
    conn = x_daily_collection.connect_manifest(manifest_path)
    account = conn.execute("SELECT * FROM collection_account").fetchone()
    assert account["error_code"] == "E_PROVIDER_SCHEMA"


def test_live_unparseable_tweet_timestamp_fails_closed(tmp_path):
    registry_path = tmp_path / "registry.db"
    raw_path = tmp_path / "raw.db"
    manifest_path = tmp_path / "manifest.db"
    _registry(registry_path, {"handle": "alpha"})
    client = x_content.TwitterContentClient(
        api_key="test", db_path=raw_path, refresh=True
    )
    client._fetch_upstream = lambda _url: _timeline_payload(
        tweets=[{"id": "missing-created-at", "text": "bad"}]
    )

    result = x_daily_collection.execute_collection(
        client=client,
        registry_path=registry_path,
        raw_path=raw_path,
        manifest_path=manifest_path,
        start_day="2026-07-11",
        end_day="2026-07-12",
    )

    assert result["status"] == "partial"
    assert result["statuses"] == {"failed": 1}
    conn = x_daily_collection.connect_manifest(manifest_path)
    account = conn.execute("SELECT * FROM collection_account").fetchone()
    assert account["error_code"] == "E_PROVIDER_SCHEMA"


def test_start_midnight_does_not_prove_complete_start_day(tmp_path):
    registry_path = tmp_path / "registry.db"
    raw_path = tmp_path / "raw.db"
    manifest_path = tmp_path / "manifest.db"
    _registry(registry_path, {"handle": "alpha"})
    client = x_content.TwitterContentClient(
        api_key="test", db_path=raw_path, refresh=True
    )
    calls = []

    def upstream(url):
        cursor = parse.parse_qs(parse.urlparse(url).query).get("cursor", [None])[0]
        calls.append(cursor)
        if cursor is None:
            return _timeline_payload(
                tweets=[
                    {
                        "id": "at-boundary",
                        "createdAt": "Sat Jul 11 00:00:00 +0000 2026",
                    }
                ],
                has_next=True,
                next_cursor="older",
            )
        return _timeline_payload(
            tweets=[
                {
                    "id": "before-boundary",
                    "createdAt": "Fri Jul 10 23:59:59 +0000 2026",
                }
            ]
        )

    client._fetch_upstream = upstream
    result = x_daily_collection.execute_collection(
        client=client,
        registry_path=registry_path,
        raw_path=raw_path,
        manifest_path=manifest_path,
        start_day="2026-07-11",
        end_day="2026-07-12",
    )

    assert result["status"] == "complete"
    assert result["provider_requests"] == 2
    assert calls == [None, "older"]


def test_freeze_rejects_an_incomplete_utc_day(tmp_path):
    registry_path = tmp_path / "registry.db"
    manifest_path = tmp_path / "manifest.db"
    _registry(registry_path, {"handle": "alpha"})
    today = datetime.now(timezone.utc).date().isoformat()

    try:
        x_daily_collection.freeze_run(
            registry_path=registry_path,
            manifest_path=manifest_path,
            start_day=today,
            end_day=today,
        )
    except ValueError as exc:
        assert str(exc) == "end_day must be a complete UTC day before today"
    else:
        raise AssertionError("an incomplete UTC day must fail before collection")


def test_execute_refreshes_a_stale_base_response(tmp_path):
    registry_path = tmp_path / "registry.db"
    raw_path = tmp_path / "raw.db"
    manifest_path = tmp_path / "manifest.db"
    _registry(registry_path, {"handle": "alpha"})
    client = x_content.TwitterContentClient(api_key="test", db_path=raw_path)
    stale = _timeline_payload(tweets=[])
    fresh = _timeline_payload(
        tweets=[
            {
                "id": "old",
                "createdAt": "Fri Jul 10 23:00:00 +0000 2026",
                "text": "old boundary",
            }
        ]
    )
    _cache(client, "alpha", stale)
    with client.db:
        client.db.execute(
            "UPDATE raw_response SET fetched_at = '2026-07-12T12:00:00+00:00'"
        )
    calls = []
    client._fetch_upstream = lambda url: calls.append(url) or fresh

    result = x_daily_collection.execute_collection(
        client=client,
        registry_path=registry_path,
        raw_path=raw_path,
        manifest_path=manifest_path,
        start_day="2026-07-11",
        end_day="2026-07-12",
    )

    assert result["status"] == "complete"
    assert result["provider_requests"] == 1
    assert len(calls) == 1
    assert client.refresh is False


class _ProtectedClient:
    def __init__(self):
        self.calls = 0

    def stats(self):
        return {"provider_requests": self.calls, "cache_hits": 0}

    def fetch_recent_tweets_page(self, **_kwargs):
        self.calls += 1
        raise sources.SourceCliError(
            code="E_ACCOUNT_PROTECTED",
            message="This account has protected posts.",
            hint="Reject it.",
        )


def test_execute_records_unexpected_active_protected_account_once(tmp_path):
    registry_path = tmp_path / "registry.db"
    raw_path = tmp_path / "missing-raw.db"
    manifest_path = tmp_path / "manifest.db"
    _registry(registry_path, {"handle": "private"})
    client = _ProtectedClient()

    first = x_daily_collection.execute_collection(
        client=client,
        registry_path=registry_path,
        raw_path=raw_path,
        manifest_path=manifest_path,
        start_day="2026-07-11",
        end_day="2026-07-12",
    )
    second = x_daily_collection.execute_collection(
        client=client,
        registry_path=registry_path,
        raw_path=raw_path,
        manifest_path=manifest_path,
        start_day="2026-07-11",
        end_day="2026-07-12",
    )

    assert client.calls == 1
    assert first["statuses"] == second["statuses"] == {"protected": 1}
    assert first["status"] == second["status"] == "complete"
    conn = x_daily_collection.connect_manifest(manifest_path)
    account = conn.execute("SELECT * FROM collection_account").fetchone()
    assert account["page_count"] == 0
    assert account["observed_after_horizon"] == 0
    assert account["reached_start_boundary"] == 0
    assert account["reached_terminal_page"] == 0


def test_cli_plan_defaults_to_stable_json_contract(tmp_path, capsys):
    registry_path = tmp_path / "registry.db"
    raw_path = tmp_path / "raw.db"
    manifest_path = tmp_path / "manifest.db"
    _registry(registry_path, {"handle": "alpha"})
    client = x_content.TwitterContentClient(api_key="test", db_path=raw_path)
    _cache(
        client,
        "alpha",
        _timeline_payload(
            tweets=[
                {
                    "id": "old",
                    "createdAt": "Fri Jul 10 23:00:00 +0000 2026",
                    "text": "old boundary",
                }
            ]
        ),
    )
    client.close()

    code = root_main(
        [
            "x-daily-collection",
            "plan",
            "--registry-db",
            str(registry_path),
            "--raw-db",
            str(raw_path),
            "--manifest-db",
            str(manifest_path),
            "--start-day",
            "2026-07-11",
            "--end-day",
            "2026-07-12",
            "--no-input",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["schema_version"] == "1.0"
    assert payload["command"] == "x-daily-collection plan"
    assert payload["status"] == "ok"
    assert payload["error"] is None
    assert payload["data"]["start_day"] == "2026-07-11"
    assert payload["data"]["end_day"] == "2026-07-12"
    assert payload["data"]["cached_accounts"] == 1
    assert set(payload["meta"]) == {
        "request_id",
        "duration_ms",
        "timestamp_utc",
    }


def test_cli_execute_uses_cached_plan_without_provider_call(
    tmp_path, capsys, monkeypatch
):
    registry_path = tmp_path / "registry.db"
    raw_path = tmp_path / "raw.db"
    manifest_path = tmp_path / "manifest.db"
    _registry(registry_path, {"handle": "alpha"})
    client = x_content.TwitterContentClient(api_key="test", db_path=raw_path)
    _cache(
        client,
        "alpha",
        _timeline_payload(
            tweets=[
                {
                    "id": "old",
                    "createdAt": "Fri Jul 10 23:00:00 +0000 2026",
                    "text": "old boundary",
                }
            ]
        ),
    )
    client._fetch_upstream = lambda _url: (_ for _ in ()).throw(
        AssertionError("provider must not be called")
    )
    monkeypatch.setattr(x_content, "create_client", lambda **_kwargs: client)

    code = x_daily_collection.main(
        [
            "execute",
            "--registry-db",
            str(registry_path),
            "--raw-db",
            str(raw_path),
            "--manifest-db",
            str(manifest_path),
            "--start-day",
            "2026-07-11",
            "--end-day",
            "2026-07-12",
            "--no-input",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["command"] == "x-daily-collection execute"
    assert payload["data"]["provider_requests"] == 0
    assert payload["data"]["status"] == "complete"


def test_cli_status_and_validation_error_are_structured(tmp_path, capsys):
    registry_path = tmp_path / "registry.db"
    raw_path = tmp_path / "raw.db"
    manifest_path = tmp_path / "manifest.db"
    _registry(registry_path, {"handle": "alpha"})

    invalid_code = x_daily_collection.main(
        [
            "plan",
            "--registry-db",
            str(registry_path),
            "--raw-db",
            str(raw_path),
            "--manifest-db",
            str(manifest_path),
            "--start-day",
            "2026-07-13",
            "--end-day",
            "2026-07-12",
            "--no-input",
        ]
    )
    invalid = json.loads(capsys.readouterr().out)
    assert invalid_code == 2
    assert invalid["status"] == "error"
    assert invalid["error"]["code"] == "E_VALIDATION"
    assert invalid["error"]["retryable"] is False

    frozen = x_daily_collection.freeze_run(
        registry_path=registry_path,
        manifest_path=manifest_path,
        start_day="2026-07-11",
        end_day="2026-07-12",
    )
    status_code = x_daily_collection.main(
        [
            "status",
            "--manifest-db",
            str(manifest_path),
            "--run-id",
            frozen["run_id"],
            "--plain",
            "--no-input",
        ]
    )
    output = capsys.readouterr().out
    assert status_code == 0
    assert output.startswith("status=ok ")
    assert f"run_id={frozen['run_id']}" in output
