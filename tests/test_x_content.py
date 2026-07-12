from datetime import timedelta

from fli import x_content


def test_client_reuses_raw_response_and_normalizes_posts(tmp_path):
    client = x_content.TwitterContentClient(
        api_key="test",
        db_path=tmp_path / "x-content.db",
        max_age=timedelta(hours=24),
    )
    calls = []

    def upstream(url):
        calls.append(url)
        return {
            "data": {
                "tweets": [
                    {
                        "id": "1",
                        "text": "hello",
                        "createdAt": "2026-07-12T10:00:00Z",
                        "likeCount": 5,
                    }
                ]
            }
        }

    client._fetch_upstream = upstream
    url = (
        "https://api.twitterapi.io/twitter/user/last_tweets"
        "?userName=test&includeReplies=false"
    )

    assert client._fetch_json(url) == client._fetch_json(url)
    assert calls == [url]
    assert client.stats() == {"cache_hits": 1, "provider_requests": 1}
    post = client.db.execute("SELECT * FROM x_post").fetchone()
    assert post["post_id"] == "1"
    assert post["author_handle"] == "test"
    assert post["like_count"] == 5
    assert client.db.execute("SELECT COUNT(*) FROM raw_response").fetchone()[0] == 1


def test_bundle_preserves_exact_ordered_model_evidence(tmp_path):
    client = x_content.TwitterContentClient(
        api_key="test", db_path=tmp_path / "x-content.db"
    )
    posts = (
        {
            "id": "2",
            "text": "second",
            "created_at": "2026-07-12T11:00:00Z",
            "post_type": "original",
        },
        {
            "id": "1",
            "text": "first",
            "created_at": "2026-07-12T10:00:00Z",
            "post_type": "quote",
        },
    )

    first = client.store_post_bundle(
        username="test", posts=posts, requested_limit=20
    )
    second = client.store_post_bundle(
        username="test", posts=posts, requested_limit=20
    )

    assert first == second
    assert client.db.execute("SELECT COUNT(*) FROM post_bundle").fetchone()[0] == 1
    rows = client.db.execute(
        "SELECT ordinal, post_id FROM post_bundle_item ORDER BY ordinal"
    ).fetchall()
    assert [(row["ordinal"], row["post_id"]) for row in rows] == [(1, "2"), (2, "1")]


def test_refresh_bypasses_raw_response_cache(tmp_path):
    db_path = tmp_path / "x-content.db"
    first = x_content.TwitterContentClient(api_key="test", db_path=db_path)
    first._fetch_upstream = lambda url: {"value": 1}
    url = "https://api.twitterapi.io/twitter/user/info?userName=test"
    assert first._fetch_json(url) == {"value": 1}
    first.close()

    refreshed = x_content.TwitterContentClient(
        api_key="test", db_path=db_path, refresh=True
    )
    refreshed._fetch_upstream = lambda url: {"value": 2}
    assert refreshed._fetch_json(url) == {"value": 2}
    assert refreshed.stats() == {"cache_hits": 0, "provider_requests": 1}
    assert refreshed.db.execute("SELECT COUNT(*) FROM raw_request").fetchone()[0] == 1
