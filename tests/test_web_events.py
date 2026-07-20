import copy
from datetime import date

from fastapi.testclient import TestClient

from fli.evidence import events as signal_events
from fli.evidence import feed as signal_feed
from fli.ingestion.x import content as x_content
from fli.registry import channels
from fli.routing import model as routing_model
from fli.routing import runs as routing_runs
from fli.routing import view as audience_routing_store
from fli.web import events as event_store, feed as feed_store
from fli.web.app import app
from tests.evidence.test_feed import _raw_fixture, _tweet
from tests.test_web_feed import _registry_fixture


client = TestClient(app)


def test_cutoff_component_identity_prefers_primary_thread_over_quoted_target():
    identity = event_store._component_identity(
        component_keys={
            ("twitterapi_io", "100"),
            ("twitterapi_io", "900"),
            ("twitterapi_io", "901"),
        },
        links=[
            {
                "provider": "twitterapi_io",
                "source_post_id": "901",
                "target_post_id": "900",
                "link_type": "primary_thread",
            },
            {
                "provider": "twitterapi_io",
                "source_post_id": "901",
                "target_post_id": "100",
                "link_type": "quote",
            },
        ],
    )

    assert identity == ("twitterapi_io", "post", "900")


def test_cutoff_component_identity_keeps_source_above_reaction_thread():
    identity = event_store._component_identity(
        component_keys={
            ("twitterapi_io", "100"),
            ("twitterapi_io", "900"),
            ("twitterapi_io", "901"),
        },
        links=[
            {
                "provider": "twitterapi_io",
                "source_post_id": "901",
                "target_post_id": "900",
                "link_type": "primary_thread",
            },
            {
                "provider": "twitterapi_io",
                "source_post_id": "900",
                "target_post_id": "100",
                "link_type": "quote",
            },
        ],
    )

    assert identity == ("twitterapi_io", "post", "100")


def _event_fixture(tmp_path, monkeypatch, *, include_singleton=False):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    registry = tmp_path / "registry.db"
    _raw_fixture(raw)
    if include_singleton:
        provider = x_content.TwitterContentClient(api_key="test", db_path=raw)
        with provider.db:
            provider._store_posts(
                url=(
                    "https://api.twitterapi.io/twitter/user/last_tweets"
                    "?userName=alice&includeReplies=false"
                ),
                payload={
                    "data": {
                        "tweets": [
                            _tweet(
                                "4",
                                "alice",
                                "2026-07-11T11:00:00Z",
                                "Independent observation",
                            )
                        ]
                    }
                },
                observed_at="2026-07-12T00:00:00+00:00",
            )
        provider.close()
    _registry_fixture(registry)
    signal_feed.materialize(
        source_db=raw, feed_db=feed_db, through=date(2026, 7, 11), days=1
    )
    event_run = signal_events.materialize(feed_db=feed_db, events_db=events_db)
    signal_events.publish(
        events_db=events_db, feed_db=feed_db, event_run_id=event_run["run_id"]
    )
    empty_rankings = tmp_path / "following"
    empty_rankings.mkdir()
    routing_root = tmp_path / "audience-routing"
    routing_root.mkdir()
    monkeypatch.setattr(feed_store, "DEFAULT_FEED_DB", feed_db)
    monkeypatch.setattr(feed_store, "DEFAULT_REGISTRY_DB", registry)
    monkeypatch.setattr(feed_store, "DEFAULT_DERIVED_ROOT", empty_rankings)
    monkeypatch.setattr(event_store, "DEFAULT_FEED_DB", feed_db)
    monkeypatch.setattr(event_store, "DEFAULT_EVENTS_DB", events_db)
    monkeypatch.setattr(event_store, "DEFAULT_EVENT_VIEW_CACHE_ROOT", None)
    monkeypatch.setattr(
        audience_routing_store, "DEFAULT_ROUTING_ROOT", routing_root
    )
    return {
        "registry": registry,
        "raw": raw,
        "feed_db": feed_db,
        "events_db": events_db,
    }


def _write_audience_routing_run(root, *, items):
    path = root / "audience-run-1" / "routing.db"
    conn = routing_runs.connect_run(path)
    now = "2026-07-13T10:05:00+00:00"
    conn.execute(
        """INSERT INTO run_meta
           (singleton, run_id, day, model, reasoning_effort, prompt_version,
            prompt_sha256, schema_version, source_event_run_id,
            source_feed_run_id, source_artifact_db, selection_kind,
            selection_limit,
            requested_event_id, cohort_sha256, expected_count,
            created_at, updated_at)
           VALUES (1, 'audience-run-1', '2026-07-11', 'gpt-5.4-mini',
                   'xhigh', ?, ?, ?, 'event-run-1',
                   'feed-run-1', 'artifacts.db', 'review_cohort', ?, NULL,
                   'cohort-hash', ?, ?, ?)""",
        (
            routing_model.PROMPT_VERSION,
            routing_model.prompt_sha256(),
            routing_model.SCHEMA_VERSION,
            len(items),
            len(items),
            now,
            now,
        ),
    )
    for rank, item in enumerate(items, start=1):
        conn.execute(
            """INSERT INTO routing_item
               (event_id, feed_rank, root_url, semantic_snapshot_sha256,
                packet_json, evidence_sha256, input_text, input_sha256,
                status, attempts,
                ai_engineering_relevant, ai_engineering_reason,
                investment_relevant, investment_reason,
                completed_at, updated_at)
               VALUES (?, ?, 'https://x.com/a/status/1', ?, '{}',
                       'evidence-hash', 'input', 'input-hash', 'complete', 1,
                       ?, ?, ?, ?, ?, ?)""",
            (
                item["event_id"],
                rank,
                item["semantic_snapshot_sha256"],
                int(rank == 1),
                "Concrete engineering relevance." if rank == 1 else "Not useful for engineering.",
                int(rank == 1),
                "Concrete investment relevance." if rank == 1 else "Not material for investment.",
                now,
                now,
            ),
        )
    conn.commit()
    conn.close()


def test_events_api_returns_root_once_with_exact_relationships(tmp_path, monkeypatch):
    _event_fixture(tmp_path, monkeypatch)

    dates = client.get("/api/events/dates").json()
    assert dates["available"] is True
    assert dates["dates"] == [{"day": "2026-07-11", "item_count": 2}]

    payload = client.get("/api/events?date=2026-07-11&limit=20").json()
    assert payload["available"] is True
    assert payload["run"]["clustering_contract"] == signal_events.CLUSTERING_CONTRACT
    assert payload["total"] == 2
    target_group = next(item for item in payload["items"] if item["root"]["post_id"] == "1")
    assert target_group["is_grouped"] is True
    assert target_group["member_count"] == 2
    assert target_group["link_count"] == 1
    assert target_group["anchor_types"] == ["same_target"]
    assert target_group["why_grouped"] == ["Exact same quoted or reposted post"]
    assert target_group["daily_score_basis"]["attention_score"] == (
        target_group["peak_attention_score"]
    )
    assert target_group["daily_score_basis"]["post_id"] == "1"
    assert target_group["daily_score_basis"]["score_components"] == (
        target_group["root"]["score_components"]
    )
    assert [item["post_id"] for item in target_group["evidence"]] == ["2"]
    assert target_group["evidence"][0]["relationship"] == "retweet"
    assert target_group["evidence"][0]["target_post_id"] == "1"
    assert target_group["relationship_counts"] == {
        "author_updates": 0,
        "replies": 0,
        "quotes": 0,
        "retweets": 1,
        "related": 0,
    }


def test_event_peak_score_does_not_overwrite_root_score_components(
    tmp_path, monkeypatch
):
    _event_fixture(tmp_path, monkeypatch)
    original_feed_payload = feed_store.feed_payload
    unmodified = original_feed_payload(
        day="2026-07-11",
        lane="all",
        sort="attention",
        query="",
        limit=20,
        offset=0,
    )
    root_candidate = next(
        item for item in unmodified["items"] if item["post_id"] == "1"
    )

    def feed_payload_with_scoring_reaction(**kwargs):
        payload = original_feed_payload(**kwargs)
        reaction = copy.deepcopy(root_candidate)
        reaction.update(
            {
                "post_id": "2",
                "published_at": "2026-07-11T09:00:00+00:00",
                "attention_score": root_candidate["attention_score"] + 20,
                "author": {
                    **reaction["author"],
                    "handle": "bob",
                    "name": "Bob",
                    "entity_id": 2,
                    "entity_name": "Bob",
                },
            }
        )
        payload["items"] = [*payload["items"], reaction]
        return payload

    monkeypatch.setattr(feed_store, "feed_payload", feed_payload_with_scoring_reaction)
    event_store._events_day_cached.cache_clear()
    payload = client.get("/api/events?date=2026-07-11&limit=20").json()
    grouped = next(item for item in payload["items"] if item["root"]["post_id"] == "1")

    assert grouped["daily_score_basis"]["post_id"] == "2"
    assert grouped["peak_attention_score"] > grouped["root"]["attention_score"]
    assert grouped["root"]["attention_score"] == root_candidate["attention_score"]
    assert grouped["root"]["score_components"] == root_candidate["score_components"]


def test_events_api_can_omit_heavy_evidence_from_list_rows(tmp_path, monkeypatch):
    _event_fixture(tmp_path, monkeypatch)

    payload = client.get(
        "/api/events?date=2026-07-11&limit=20&include_evidence=false"
    ).json()
    target_group = next(item for item in payload["items"] if item["root"]["post_id"] == "1")

    assert payload["include_evidence"] is False
    assert target_group["evidence"] == []
    assert target_group["amplifiers"] == []
    assert target_group["root"]["amplifiers"] == []
    assert target_group["relationship_counts"]["retweets"] == 1

    detail = client.get(
        "/api/events",
        params={
            "date": "2026-07-11",
            "event_id": target_group["event_id"],
            "include_evidence": "true",
            "limit": 1,
        },
    ).json()
    assert [item["post_id"] for item in detail["items"][0]["evidence"]] == ["2"]


def test_events_api_preserves_ungrouped_posts_as_singletons(tmp_path, monkeypatch):
    _event_fixture(tmp_path, monkeypatch, include_singleton=True)

    dates = client.get("/api/events/dates").json()
    assert dates["dates"] == [{"day": "2026-07-11", "item_count": 3}]
    payload = client.get("/api/events?date=2026-07-11&limit=20").json()
    singleton = next(item for item in payload["items"] if item["root"]["post_id"] == "4")
    assert singleton["is_grouped"] is False
    assert singleton["member_count"] == 1
    assert singleton["daily_score_basis"]["post_id"] == "4"
    assert singleton["daily_score_basis"]["attention_score"] == (
        singleton["peak_attention_score"]
    )
    assert singleton["evidence"] == []


def test_event_dates_cache_the_complete_summary(tmp_path, monkeypatch):
    _event_fixture(tmp_path, monkeypatch)
    original_dates_payload = feed_store.dates_payload
    calls = 0

    def counted_dates_payload(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original_dates_payload(*args, **kwargs)

    monkeypatch.setattr(feed_store, "dates_payload", counted_dates_payload)
    event_store._dates_payload_cached.cache_clear()

    cache_token = event_store._dates_cache_token()
    first = event_store._dates_payload_cached(cache_token)
    second = event_store._dates_payload_cached(cache_token)

    assert first == second
    assert calls == 1


def test_event_day_projection_reuses_persisted_exact_view(tmp_path, monkeypatch):
    _event_fixture(tmp_path, monkeypatch)
    cache_root = tmp_path / "web-event-cache"
    monkeypatch.setattr(event_store, "DEFAULT_EVENT_VIEW_CACHE_ROOT", cache_root)
    event_store._events_day_cached.cache_clear()
    cache_token = event_store._cache_token("2026-07-11")

    first = event_store._events_day_cached(
        day="2026-07-11",
        cache_token=cache_token,
    )
    assert (cache_root / "events-2026-07-11.json.gz").is_file()

    event_store._events_day_cached.cache_clear()

    def fail_source_projection(**_kwargs):
        raise AssertionError("persisted view should avoid rebuilding source projection")

    monkeypatch.setattr(event_store, "_all_feed_candidates", fail_source_projection)
    second = event_store._events_day_cached(
        day="2026-07-11",
        cache_token=cache_token,
    )

    assert second == first


def test_event_dates_reuse_persisted_exact_summary(tmp_path, monkeypatch):
    _event_fixture(tmp_path, monkeypatch)
    cache_root = tmp_path / "web-event-cache"
    monkeypatch.setattr(event_store, "DEFAULT_EVENT_VIEW_CACHE_ROOT", cache_root)
    event_store._events_day_cached.cache_clear()
    event_store._dates_payload_cached.cache_clear()

    first = event_store.dates_payload()
    assert (cache_root / "dates.json.gz").is_file()

    event_store._events_day_cached.cache_clear()
    event_store._dates_payload_cached.cache_clear()

    def fail_date_projection(*_args, **_kwargs):
        raise AssertionError("persisted summary should avoid rebuilding date counts")

    monkeypatch.setattr(feed_store, "dates_payload", fail_date_projection)
    second = event_store.dates_payload()

    assert second == first


def test_events_api_projects_completed_audience_routing_directly(
    tmp_path, monkeypatch
):
    _event_fixture(tmp_path, monkeypatch)
    baseline = client.get("/api/events?date=2026-07-11&limit=20").json()
    assert {item["routing_state"] for item in baseline["items"]} == {"unavailable"}
    _write_audience_routing_run(
        audience_routing_store.DEFAULT_ROUTING_ROOT,
        items=baseline["items"],
    )

    all_items = client.get("/api/events?date=2026-07-11&limit=20").json()
    assert all_items["audience_routing_run"]["run_id"] == "audience-run-1"
    assert all("triage" not in item for item in all_items["items"])
    routed = all_items["items"][0]
    assert {item["routing_state"] for item in all_items["items"]} == {"evaluated"}
    assert routed["audience_routing"]["ai_engineering"] == {
        "relevant": True,
        "reason": "Concrete engineering relevance.",
    }
    assert routed["audience_routing"]["investment"] == {
        "relevant": True,
        "reason": "Concrete investment relevance.",
    }
    second_route = all_items["items"][1]["audience_routing"]
    assert second_route["ai_engineering"]["relevant"] is False
    assert second_route["investment"]["relevant"] is False
    assert all_items["routing_counts"] == {
        "all": 2,
        "relevant": 1,
        "not_relevant": 1,
        "not_evaluated": 0,
    }
    assert all_items["daily_rank_total"] == 2
    daily_rank_by_event_id = {
        item["event_id"]: item["daily_rank"] for item in all_items["items"]
    }

    recent = client.get(
        "/api/events?date=2026-07-11&sort=recent&limit=20"
    ).json()
    assert {
        item["event_id"]: item["daily_rank"] for item in recent["items"]
    } == daily_rank_by_event_id

    search_target = all_items["items"][-1]
    searched = client.get(
        "/api/events",
        params={
            "date": "2026-07-11",
            "q": search_target["root"]["text"],
            "limit": 20,
        },
    ).json()
    searched_item = next(
        item
        for item in searched["items"]
        if item["event_id"] == search_target["event_id"]
    )
    assert searched_item["daily_rank"] == search_target["daily_rank"]
    assert searched["daily_rank_total"] == all_items["daily_rank_total"]

    focused = client.get(
        "/api/events",
        params={
            "date": "2026-07-11",
            "event_id": search_target["event_id"],
            "limit": 20,
        },
    ).json()
    assert focused["event_id"] == search_target["event_id"]
    assert focused["total"] == 1
    assert focused["items"][0]["event_id"] == search_target["event_id"]
    assert focused["items"][0]["daily_rank"] == search_target["daily_rank"]
    assert focused["daily_rank_total"] == all_items["daily_rank_total"]

    relevant = client.get(
        "/api/events?date=2026-07-11&routing=relevant&limit=20"
    ).json()
    assert relevant["total"] == 1
    assert relevant["items"][0]["event_id"] == routed["event_id"]
    neither = client.get(
        "/api/events?date=2026-07-11&routing=not_relevant&limit=20"
    ).json()
    assert neither["total"] == 1
    assert neither["items"][0]["event_id"] == all_items["items"][1]["event_id"]


def test_events_api_publishes_once_and_appends_later_activity(tmp_path, monkeypatch):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    registry = tmp_path / "registry.db"
    root = _tweet(
        "200", "alice", "2026-07-10T08:00:00Z", "A durable research result"
    )
    quote = _tweet(
        "201",
        "carol",
        "2026-07-11T09:00:00Z",
        "This result deserves another look",
        relation="quote",
        target=root,
    )
    provider = x_content.TwitterContentClient(api_key="test", db_path=raw)
    with provider.db:
        for handle, tweet in (("alice", root), ("carol", quote)):
            provider._store_posts(
                url=(
                    "https://api.twitterapi.io/twitter/user/last_tweets"
                    f"?userName={handle}&includeReplies=false"
                ),
                payload={"data": {"tweets": [tweet]}},
                observed_at="2026-07-12T00:00:00+00:00",
            )
    provider.close()
    _registry_fixture(registry)
    signal_feed.materialize(
        source_db=raw, feed_db=feed_db, through=date(2026, 7, 11), days=2
    )
    event_run = signal_events.materialize(feed_db=feed_db, events_db=events_db)
    signal_events.publish(
        events_db=events_db, feed_db=feed_db, event_run_id=event_run["run_id"]
    )
    rankings = tmp_path / "following"
    rankings.mkdir()
    monkeypatch.setattr(feed_store, "DEFAULT_FEED_DB", feed_db)
    monkeypatch.setattr(feed_store, "DEFAULT_REGISTRY_DB", registry)
    monkeypatch.setattr(feed_store, "DEFAULT_DERIVED_ROOT", rankings)
    monkeypatch.setattr(event_store, "DEFAULT_FEED_DB", feed_db)
    monkeypatch.setattr(event_store, "DEFAULT_EVENTS_DB", events_db)

    monday = client.get("/api/events?date=2026-07-10&limit=20").json()
    tuesday = client.get("/api/events?date=2026-07-11&limit=20").json()
    monday_event = next(item for item in monday["items"] if item["root"]["post_id"] == "200")
    assert not any(item["root"]["post_id"] == "200" for item in tuesday["items"])
    assert monday_event["canonical_root_post_id"] == "200"
    assert monday_event["member_count"] == 2
    assert monday_event["activity_days"] == ["2026-07-10", "2026-07-11"]
    assert [member["post_id"] for member in monday_event["evidence"]] == ["201"]

    weekly = client.get(
        "/api/events?date=2026-07-11&projection=week&limit=20"
    ).json()
    weekly_event = next(
        item for item in weekly["items"] if item["event_id"] == monday_event["event_id"]
    )
    assert weekly_event["projection"] == "week"
    assert weekly_event["window_from"] == "2026-07-05"
    assert weekly_event["window_to"] == "2026-07-11"
    assert weekly_event["active_days"] == ["2026-07-10", "2026-07-11"]
    assert weekly_event["member_count"] == 2
    assert weekly_event["audience_routing"] is None
    assert weekly_event["routing_state"] == "unavailable"
    assert weekly_event["semantic_snapshot_sha256"] not in {
        monday_event["semantic_snapshot_sha256"],
    }


def test_events_api_traverses_exact_parent_tree_before_later_branches(
    tmp_path, monkeypatch
):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    registry = tmp_path / "registry.db"
    root = _tweet("10", "alice", "2026-07-11T08:00:00Z", "Launch thread")
    root.update({"conversationId": "10", "isReply": False})
    continuation = _tweet(
        "13", "alice", "2026-07-11T08:15:00Z", "One more detail"
    )
    continuation.update(
        {
            "conversationId": "10",
            "inReplyToId": "10",
            "inReplyToUserId": "x-alice",
            "isReply": True,
        }
    )
    continuation_child = _tweet(
        "14", "alice", "2026-07-11T08:20:00Z", "Nested thread detail"
    )
    continuation_child.update(
        {
            "conversationId": "10",
            "inReplyToId": "13",
            "inReplyToUserId": "x-alice",
            "isReply": True,
        }
    )
    later_root_child = _tweet(
        "15", "alice", "2026-07-11T08:25:00Z", "Later root-level detail"
    )
    later_root_child.update(
        {
            "conversationId": "10",
            "inReplyToId": "10",
            "inReplyToUserId": "x-alice",
            "isReply": True,
        }
    )
    quote = _tweet(
        "12",
        "carol",
        "2026-07-11T09:00:00Z",
        "Separate quoted branch",
        relation="quote",
        target=root,
    )
    reply_to_quote = _tweet(
        "16", "outside", "2026-07-11T09:05:00Z", "Reply beneath the quote"
    )
    reply_to_quote.update(
        {
            "conversationId": "12",
            "inReplyToId": "12",
            "inReplyToUserId": "x-carol",
            "isReply": True,
        }
    )
    missing_parent = _tweet(
        "17", "outside", "2026-07-11T10:00:00Z", "Parent was not captured"
    )
    missing_parent.update(
        {
            "conversationId": "10",
            "inReplyToId": "999",
            "inReplyToUserId": "x-missing",
            "isReply": True,
        }
    )
    provider = x_content.TwitterContentClient(api_key="test", db_path=raw)
    with provider.db:
        for handle, tweets in (
            (
                "alice",
                [root, continuation, continuation_child, later_root_child],
            ),
            ("carol", [quote, reply_to_quote, missing_parent]),
        ):
            provider._store_posts(
                url=(
                    "https://api.twitterapi.io/twitter/user/last_tweets"
                    f"?userName={handle}&includeReplies=false"
                ),
                payload={"data": {"tweets": tweets}},
                observed_at="2026-07-12T00:00:00+00:00",
            )
    provider.close()
    _registry_fixture(registry)
    signal_feed.materialize(
        source_db=raw, feed_db=feed_db, through=date(2026, 7, 11), days=1
    )
    event_run = signal_events.materialize(feed_db=feed_db, events_db=events_db)
    signal_events.publish(
        events_db=events_db, feed_db=feed_db, event_run_id=event_run["run_id"]
    )
    empty_rankings = tmp_path / "following"
    empty_rankings.mkdir()
    monkeypatch.setattr(feed_store, "DEFAULT_FEED_DB", feed_db)
    monkeypatch.setattr(feed_store, "DEFAULT_REGISTRY_DB", registry)
    monkeypatch.setattr(feed_store, "DEFAULT_DERIVED_ROOT", empty_rankings)
    monkeypatch.setattr(event_store, "DEFAULT_FEED_DB", feed_db)
    monkeypatch.setattr(event_store, "DEFAULT_EVENTS_DB", events_db)

    payload = client.get("/api/events?date=2026-07-11&limit=20").json()
    assert payload["total"] == 1
    item = payload["items"][0]
    assert item["root"]["post_id"] == "10"
    assert [member["post_id"] for member in item["evidence"]] == [
        "13",
        "14",
        "15",
        "12",
    ]
    (
        continuation_result,
        continuation_child_result,
        later_root_child_result,
        quote_result,
    ) = item["evidence"]
    assert continuation_result["relationship"] == "reply"
    assert continuation_result["parent_post_id"] == "10"
    assert continuation_result["depth"] == 1
    assert continuation_result["same_author_as_root"] is True
    assert continuation_child_result["parent_post_id"] == "13"
    assert continuation_child_result["depth"] == 2
    assert continuation_child_result["same_author_as_root"] is True
    assert later_root_child_result["parent_post_id"] == "10"
    assert later_root_child_result["depth"] == 1
    assert quote_result["relationship"] == "quote"
    assert quote_result["parent_post_id"] == "10"
    assert quote_result["depth"] == 1


def test_events_follow_current_registry_rejections_without_rebuild(
    tmp_path, monkeypatch
):
    registry = _event_fixture(tmp_path, monkeypatch)["registry"]
    before = client.get("/api/events?date=2026-07-11&limit=20").json()
    assert before["total"] == 2

    conn = channels.connect(registry)
    conn.execute(
        """INSERT INTO entity_registry_rejections
           (entity_id, reason_code, reason, source, rejected_at)
           VALUES (2, 'test', 'Rejected structural member.', 'test',
                   '2026-07-12T01:00:00+00:00')"""
    )
    conn.commit()
    conn.close()

    after = client.get("/api/events?date=2026-07-11&limit=20").json()
    assert after["total"] == 2
    surviving = next(item for item in after["items"] if item["root"]["post_id"] == "1")
    assert surviving["is_grouped"] is False
    assert surviving["member_count"] == 1
    assert surviving["evidence"] == []


def test_events_read_only_the_atomically_published_feed_event_pair(
    tmp_path, monkeypatch
):
    fixture = _event_fixture(tmp_path, monkeypatch)
    before = client.get("/api/events?date=2026-07-11&limit=20").json()
    published_a = before["run"]

    provider = x_content.TwitterContentClient(api_key="test", db_path=fixture["raw"])
    with provider.db:
        provider._store_posts(
            url=(
                "https://api.twitterapi.io/twitter/user/last_tweets"
                "?userName=alice&includeReplies=false"
            ),
            payload={
                "data": {
                    "tweets": [
                        _tweet(
                            "publication-b",
                            "alice",
                            "2026-07-11T12:00:00Z",
                            "New evidence in an unpublished Feed run",
                        )
                    ]
                }
            },
            observed_at="2026-07-12T01:00:00+00:00",
        )
    provider.close()
    feed_b = signal_feed.materialize(
        source_db=fixture["raw"],
        feed_db=fixture["feed_db"],
        through=date(2026, 7, 11),
        days=1,
    )
    event_store._events_day_cached.cache_clear()
    after_feed_only = client.get("/api/events?date=2026-07-11&limit=20").json()
    assert after_feed_only["run"] == published_a
    assert after_feed_only["total"] == before["total"]

    events_b = signal_events.materialize(
        feed_db=fixture["feed_db"],
        events_db=fixture["events_db"],
        feed_run_id=feed_b["run_id"],
    )
    event_store._events_day_cached.cache_clear()
    after_unpublished_events = client.get(
        "/api/events?date=2026-07-11&limit=20"
    ).json()
    assert after_unpublished_events["run"] == published_a

    signal_events.publish(
        events_db=fixture["events_db"],
        feed_db=fixture["feed_db"],
        event_run_id=events_b["run_id"],
    )
    event_store._events_day_cached.cache_clear()
    after_publish = client.get("/api/events?date=2026-07-11&limit=20").json()
    assert after_publish["run"]["run_id"] == events_b["run_id"]
    assert after_publish["run"]["feed_run_id"] == feed_b["run_id"]
    assert after_publish["total"] == before["total"] + 1


def _configure_event_read_model(
    tmp_path, monkeypatch, *, feed_db, events_db, registry
):
    rankings = tmp_path / "following"
    rankings.mkdir(exist_ok=True)
    routing_root = tmp_path / "audience-routing"
    routing_root.mkdir(exist_ok=True)
    monkeypatch.setattr(feed_store, "DEFAULT_FEED_DB", feed_db)
    monkeypatch.setattr(feed_store, "DEFAULT_REGISTRY_DB", registry)
    monkeypatch.setattr(feed_store, "DEFAULT_DERIVED_ROOT", rankings)
    monkeypatch.setattr(event_store, "DEFAULT_FEED_DB", feed_db)
    monkeypatch.setattr(event_store, "DEFAULT_EVENTS_DB", events_db)
    monkeypatch.setattr(
        audience_routing_store, "DEFAULT_ROUTING_ROOT", routing_root
    )
    event_store._events_day_cached.cache_clear()


def _store_tweets(raw, *batches):
    provider = x_content.TwitterContentClient(api_key="test", db_path=raw)
    with provider.db:
        for handle, tweets in batches:
            provider._store_posts(
                url=(
                    "https://api.twitterapi.io/twitter/user/last_tweets"
                    f"?userName={handle}&includeReplies=false"
                ),
                payload={"data": {"tweets": list(tweets)}},
                observed_at="2026-07-16T00:00:00+00:00",
            )
    provider.close()


def _materialize_published_events(*, raw, feed_db, events_db, through, days):
    feed_run = signal_feed.materialize(
        source_db=raw, feed_db=feed_db, through=through, days=days
    )
    event_run = signal_events.materialize(
        feed_db=feed_db,
        events_db=events_db,
        feed_run_id=feed_run["run_id"],
    )
    signal_events.publish(
        events_db=events_db,
        feed_db=feed_db,
        event_run_id=event_run["run_id"],
    )
    event_store._events_day_cached.cache_clear()
    return event_run


def test_future_reaction_appends_without_republishing_or_rerouting(
    tmp_path, monkeypatch
):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    registry = tmp_path / "registry.db"
    monday_root = _tweet(
        "future-root",
        "alice",
        "2026-07-13T08:00:00Z",
        "A result available on Monday",
    )
    monday_quote = _tweet(
        "future-monday-quote",
        "carol",
        "2026-07-13T09:00:00Z",
        "Monday reaction",
        relation="quote",
        target=monday_root,
    )
    wednesday_quote = _tweet(
        "future-wednesday-quote",
        "bob",
        "2026-07-15T10:00:00Z",
        "Wednesday reaction",
        relation="quote",
        target=monday_root,
    )
    _store_tweets(
        raw,
        ("alice", [monday_root]),
        ("carol", [monday_quote]),
        ("bob", [wednesday_quote]),
    )
    _registry_fixture(registry)
    _configure_event_read_model(
        tmp_path,
        monkeypatch,
        feed_db=feed_db,
        events_db=events_db,
        registry=registry,
    )

    _materialize_published_events(
        raw=raw,
        feed_db=feed_db,
        events_db=events_db,
        through=date(2026, 7, 13),
        days=1,
    )
    before = client.get("/api/events?date=2026-07-13&limit=20").json()
    before_event = next(
        item for item in before["items"] if item["root"]["post_id"] == "future-root"
    )

    _materialize_published_events(
        raw=raw,
        feed_db=feed_db,
        events_db=events_db,
        through=date(2026, 7, 15),
        days=3,
    )
    after = client.get("/api/events?date=2026-07-13&limit=20").json()
    after_event = next(
        item for item in after["items"] if item["root"]["post_id"] == "future-root"
    )

    assert after_event["event_id"] == before_event["event_id"]
    assert after_event["semantic_snapshot_sha256"] == before_event["semantic_snapshot_sha256"]
    assert after_event["daily_rank"] == before_event["daily_rank"]
    assert [item["post_id"] for item in after_event["evidence"]] == [
        "future-monday-quote",
        "future-wednesday-quote",
    ]
    wednesday = client.get("/api/events?date=2026-07-15&limit=20").json()
    assert not any(
        item["event_id"] == after_event["event_id"] for item in wednesday["items"]
    )
    assert after_event["lifetime_member_count"] == 3


def test_future_reply_quote_does_not_merge_or_reidentify_source_components(
    tmp_path, monkeypatch
):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    registry = tmp_path / "registry.db"
    left_root = _tweet(
        "historical-left", "alice", "2026-07-13T08:00:00Z", "Left claim"
    )
    left_quote = _tweet(
        "historical-left-quote",
        "carol",
        "2026-07-13T08:30:00Z",
        "Left reaction",
        relation="quote",
        target=left_root,
    )
    right_root = _tweet(
        "historical-right", "bob", "2026-07-13T09:00:00Z", "Right claim"
    )
    right_quote = _tweet(
        "historical-right-quote",
        "alice",
        "2026-07-13T09:30:00Z",
        "Right reaction",
        relation="quote",
        target=right_root,
    )
    future_bridge = _tweet(
        "future-bridge",
        "carol",
        "2026-07-15T10:00:00Z",
        "Later bridge",
        relation="quote",
        target=left_root,
    )
    future_bridge.update(
        {
            "isReply": True,
            "conversationId": right_root["id"],
            "inReplyToId": right_root["id"],
            "inReplyToUserId": "x-bob",
        }
    )
    _store_tweets(
        raw,
        ("alice", [left_root, right_quote]),
        ("bob", [right_root]),
        ("carol", [left_quote, future_bridge]),
    )
    _registry_fixture(registry)
    _configure_event_read_model(
        tmp_path,
        monkeypatch,
        feed_db=feed_db,
        events_db=events_db,
        registry=registry,
    )

    _materialize_published_events(
        raw=raw,
        feed_db=feed_db,
        events_db=events_db,
        through=date(2026, 7, 13),
        days=1,
    )
    before = client.get("/api/events?date=2026-07-13&limit=20").json()
    before_items = {
        item["root"]["post_id"]: item
        for item in before["items"]
        if item["root"]["post_id"] in {"historical-left", "historical-right"}
    }
    assert set(before_items) == {"historical-left", "historical-right"}

    _materialize_published_events(
        raw=raw,
        feed_db=feed_db,
        events_db=events_db,
        through=date(2026, 7, 15),
        days=3,
    )
    after = client.get("/api/events?date=2026-07-13&limit=20").json()
    after_items = {
        item["root"]["post_id"]: item
        for item in after["items"]
        if item["root"]["post_id"] in {"historical-left", "historical-right"}
    }
    assert after_items == before_items

    wednesday = client.get("/api/events?date=2026-07-15&limit=20").json()
    for item in wednesday["items"]:
        member_ids = {
            item["root"]["post_id"],
            *[member["post_id"] for member in item["evidence"]],
        }
        assert "future-bridge" not in member_ids
        assert not {"historical-left", "historical-right"} <= member_ids

    weekly = client.get(
        "/api/events?date=2026-07-15&projection=week&limit=20"
    ).json()
    expected_components = {
        frozenset({"historical-left", "historical-left-quote"}),
        frozenset({"historical-right", "historical-right-quote"}),
    }
    weekly_components = {
        frozenset(
            {
                item["root"]["post_id"],
                *[member["post_id"] for member in item["evidence"]],
            }
        ): item
        for item in weekly["items"]
        if item["root"]["post_id"] in {"historical-left", "historical-right"}
    }
    assert set(weekly_components) == expected_components
    assert weekly_components[
        frozenset({"historical-left", "historical-left-quote"})
    ]["active_days"] == ["2026-07-13"]
    assert weekly_components[
        frozenset({"historical-right", "historical-right-quote"})
    ]["active_days"] == ["2026-07-13"]
    assert all(
        "future-bridge"
        not in {
            item["root"]["post_id"],
            *[member["post_id"] for member in item["evidence"]],
        }
        for item in weekly["items"]
    )

    projected_members = [
        (member.get("provider"), member["post_id"])
        for item in weekly["items"]
        for member in [item["root"], *item["evidence"]]
    ]
    assert len(projected_members) == len(set(projected_members))


def test_relationship_disclosed_by_future_wrapper_does_not_rewrite_monday(
    tmp_path, monkeypatch
):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    registry = tmp_path / "registry.db"
    monday_a = _tweet(
        "disclosed-a", "alice", "2026-07-13T08:00:00Z", "Sparse A"
    )
    monday_b = _tweet(
        "disclosed-b", "bob", "2026-07-13T09:00:00Z", "Independent B"
    )
    rich_a = _tweet(
        "disclosed-a",
        "alice",
        "2026-07-13T08:00:00Z",
        "Embedded A",
        relation="quote",
        target=monday_b,
    )
    wednesday_wrapper = _tweet(
        "disclosure-wrapper",
        "carol",
        "2026-07-15T10:00:00Z",
        "Later wrapper",
        relation="quote",
        target=rich_a,
    )
    _store_tweets(
        raw,
        ("alice", [monday_a]),
        ("bob", [monday_b]),
        ("carol", [wednesday_wrapper]),
    )
    _registry_fixture(registry)
    _configure_event_read_model(
        tmp_path,
        monkeypatch,
        feed_db=feed_db,
        events_db=events_db,
        registry=registry,
    )

    _materialize_published_events(
        raw=raw,
        feed_db=feed_db,
        events_db=events_db,
        through=date(2026, 7, 13),
        days=1,
    )
    before = client.get("/api/events?date=2026-07-13&limit=20").json()
    before_items = {
        item["root"]["post_id"]: item
        for item in before["items"]
        if item["root"]["post_id"] in {"disclosed-a", "disclosed-b"}
    }
    assert set(before_items) == {"disclosed-a", "disclosed-b"}

    _materialize_published_events(
        raw=raw,
        feed_db=feed_db,
        events_db=events_db,
        through=date(2026, 7, 15),
        days=3,
    )
    after = client.get("/api/events?date=2026-07-13&limit=20").json()
    after_items = {
        item["root"]["post_id"]: item
        for item in after["items"]
        if item["root"]["post_id"] in {"disclosed-a", "disclosed-b"}
    }
    assert set(after_items) == set(before_items)
    assert after_items["disclosed-b"] == before_items["disclosed-b"]
    for key in (
        "event_id",
        "canonical_root_post_id",
        "presentation_root_post_id",
        "daily_rank",
    ):
        assert after_items["disclosed-a"][key] == before_items["disclosed-a"][key]
    assert after_items["disclosed-a"]["semantic_snapshot_sha256"] != before_items[
        "disclosed-a"
    ]["semantic_snapshot_sha256"]
    assert [
        member["post_id"] for member in after_items["disclosed-a"]["evidence"]
    ] == ["disclosure-wrapper"]

    feed = signal_feed.connect(feed_db)
    disclosed = feed.execute(
        """SELECT source_post_id, target_post_id, discovered_day,
                  disclosure_post_id
           FROM feed_relation
           WHERE run_id = (
               SELECT run_id FROM feed_run
               WHERE date_to = '2026-07-15'
               ORDER BY created_at DESC, run_id DESC LIMIT 1
           )
           ORDER BY source_post_id, target_post_id"""
    ).fetchall()
    assert [tuple(row) for row in disclosed] == [
        ("disclosed-a", "disclosed-b", "2026-07-15", "disclosure-wrapper"),
        ("disclosure-wrapper", "disclosed-a", "2026-07-15", "disclosure-wrapper"),
    ]
    canonical_a = feed.execute(
        """SELECT text, first_discovered_day, disclosure_post_id
           FROM feed_post
           WHERE run_id = (
               SELECT run_id FROM feed_run
               WHERE date_to = '2026-07-15'
               ORDER BY created_at DESC, run_id DESC LIMIT 1
           )
             AND post_id = 'disclosed-a'"""
    ).fetchone()
    assert tuple(canonical_a) == ("Sparse A", "2026-07-13", "disclosed-a")
    feed.close()

    wednesday = client.get("/api/events?date=2026-07-15&limit=20").json()
    assert not any(
        {"disclosed-a", "disclosed-b", "disclosure-wrapper"}
        & {
            item["root"]["post_id"],
            *[member["post_id"] for member in item["evidence"]],
        }
        for item in wednesday["items"]
    )


def test_rejected_reply_quote_never_bridges_surviving_source_components(
    tmp_path, monkeypatch
):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    registry = tmp_path / "registry.db"
    left_root = _tweet(
        "bridge-left-root", "alice", "2026-07-11T08:00:00Z", "Left root"
    )
    left_quote = _tweet(
        "bridge-left-quote",
        "carol",
        "2026-07-11T08:05:00Z",
        "Left quote",
        relation="quote",
        target=left_root,
    )
    right_root = _tweet(
        "bridge-right-root", "alice", "2026-07-11T09:00:00Z", "Right root"
    )
    right_quote = _tweet(
        "bridge-right-quote",
        "carol",
        "2026-07-11T09:05:00Z",
        "Right quote",
        relation="quote",
        target=right_root,
    )
    bridge = _tweet(
        "bridge-rejected",
        "bob",
        "2026-07-11T10:00:00Z",
        "A structural bridge",
        relation="quote",
        target=left_root,
    )
    bridge.update(
        {
            "isReply": True,
            "conversationId": right_root["id"],
            "inReplyToId": right_root["id"],
            "inReplyToUserId": "x-alice",
        }
    )
    _store_tweets(
        raw,
        ("alice", [left_root, right_root]),
        ("carol", [left_quote, right_quote]),
        ("bob", [bridge]),
    )
    _registry_fixture(registry)
    _materialize_published_events(
        raw=raw,
        feed_db=feed_db,
        events_db=events_db,
        through=date(2026, 7, 11),
        days=1,
    )
    _configure_event_read_model(
        tmp_path,
        monkeypatch,
        feed_db=feed_db,
        events_db=events_db,
        registry=registry,
    )

    before = client.get("/api/events?date=2026-07-11&limit=20").json()
    before_components = [
        item
        for item in before["items"]
        if item["root"]["post_id"] in {"bridge-left-root", "bridge-right-root"}
    ]
    assert len(before_components) == 2
    assert {item["member_count"] for item in before_components} == {2}

    conn = channels.connect(registry)
    conn.execute(
        """INSERT INTO entity_registry_rejections
           (entity_id, reason_code, reason, source, rejected_at)
           VALUES (2, 'test_bridge', 'Reject the structural bridge.', 'test',
                   '2026-07-12T01:00:00+00:00')"""
    )
    conn.commit()
    conn.close()
    event_store._events_day_cached.cache_clear()

    after = client.get("/api/events?date=2026-07-11&limit=20").json()
    surviving_components = [
        item
        for item in after["items"]
        if item["root"]["post_id"] in {"bridge-left-root", "bridge-right-root"}
    ]
    assert len(surviving_components) == 2
    assert {item["member_count"] for item in surviving_components} == {2}
    assert {
        frozenset(
            [item["root"]["post_id"], *[row["post_id"] for row in item["evidence"]]]
        )
        for item in surviving_components
    } == {
        frozenset({"bridge-left-root", "bridge-left-quote"}),
        frozenset({"bridge-right-root", "bridge-right-quote"}),
    }
    assert all(
        "bridge-rejected"
        not in {
            item["root"]["post_id"],
            *[row["post_id"] for row in item["evidence"]],
        }
        for item in surviving_components
    )


def test_independent_reaction_topology_does_not_change_semantic_snapshot_hash(
    tmp_path, monkeypatch
):
    fixture = _event_fixture(tmp_path, monkeypatch)
    before = client.get("/api/events?date=2026-07-11&limit=20").json()
    before_event = next(item for item in before["items"] if item["root"]["post_id"] == "1")
    before_members = {
        before_event["root"]["post_id"],
        *[member["post_id"] for member in before_event["evidence"]],
    }

    conn = signal_events.connect(fixture["events_db"])
    published = signal_events.published_run(conn)
    conn.execute(
        """UPDATE event_link SET link_type = 'quote'
           WHERE run_id = ? AND event_id = ?
             AND source_post_id = '2' AND target_post_id = '1'""",
        (published["run_id"], before_event["event_id"]),
    )
    conn.commit()
    conn.close()
    event_store._events_day_cached.cache_clear()

    after = client.get("/api/events?date=2026-07-11&limit=20").json()
    after_event = next(item for item in after["items"] if item["root"]["post_id"] == "1")
    after_members = {
        after_event["root"]["post_id"],
        *[member["post_id"] for member in after_event["evidence"]],
    }
    assert after_members == before_members
    assert after_event["semantic_snapshot_sha256"] == before_event[
        "semantic_snapshot_sha256"
    ]


def test_events_api_groups_wrappers_that_share_an_opaque_provider_target(
    tmp_path, monkeypatch
):
    raw = tmp_path / "x-content.db"
    feed_db = tmp_path / "feed.db"
    events_db = tmp_path / "events.db"
    registry = tmp_path / "registry.db"
    opaque_target = {"id": "opaque-shared-target"}
    first = _tweet(
        "opaque-wrapper-a",
        "alice",
        "2026-07-11T08:00:00Z",
        "First wrapper",
        relation="quote",
        target=opaque_target,
    )
    second = _tweet(
        "opaque-wrapper-b",
        "carol",
        "2026-07-11T09:00:00Z",
        "Second wrapper",
        relation="quote",
        target=opaque_target,
    )
    _store_tweets(raw, ("alice", [first]), ("carol", [second]))
    _registry_fixture(registry)
    _materialize_published_events(
        raw=raw,
        feed_db=feed_db,
        events_db=events_db,
        through=date(2026, 7, 11),
        days=1,
    )
    _configure_event_read_model(
        tmp_path,
        monkeypatch,
        feed_db=feed_db,
        events_db=events_db,
        registry=registry,
    )

    payload = client.get("/api/events?date=2026-07-11&limit=20").json()
    assert payload["total"] == 1
    grouped = payload["items"][0]
    assert grouped["is_grouped"] is True
    assert grouped["member_count"] == 2
    assert grouped["link_count"] == 2
    assert grouped["anchor_types"] == ["same_target"]
    assert {
        grouped["root"]["post_id"],
        *[member["post_id"] for member in grouped["evidence"]],
    } == {"opaque-wrapper-a", "opaque-wrapper-b"}
    assert grouped["canonical_root_post_id"] == "opaque-shared-target"
    assert grouped["presentation_root_post_id"] in {
        "opaque-wrapper-a",
        "opaque-wrapper-b",
    }


def test_future_renderable_target_does_not_rewrite_prior_opaque_projection(
    tmp_path, monkeypatch
):
    raw = tmp_path / "x-content.db"
    short_feed = tmp_path / "short-feed.db"
    short_events = tmp_path / "short-events.db"
    long_feed = tmp_path / "long-feed.db"
    long_events = tmp_path / "long-events.db"
    registry = tmp_path / "registry.db"
    sparse_target = {"id": "later-root"}
    full_target = _tweet(
        "later-root",
        "alice",
        "2026-07-10T07:00:00Z",
        "The root was only rendered by a later wrapper",
    )
    early_wrapper = _tweet(
        "wrap-1",
        "alice",
        "2026-07-10T08:00:00Z",
        "Early wrapper with an opaque target",
        relation="quote",
        target=sparse_target,
    )
    late_wrapper = _tweet(
        "wrap-2",
        "carol",
        "2026-07-11T09:00:00Z",
        "Later wrapper with the full target payload",
        relation="quote",
        target=full_target,
    )
    _store_tweets(raw, ("alice", [early_wrapper]), ("carol", [late_wrapper]))
    _registry_fixture(registry)

    _materialize_published_events(
        raw=raw,
        feed_db=short_feed,
        events_db=short_events,
        through=date(2026, 7, 10),
        days=1,
    )
    _configure_event_read_model(
        tmp_path,
        monkeypatch,
        feed_db=short_feed,
        events_db=short_events,
        registry=registry,
    )
    short_payload = client.get("/api/events?date=2026-07-10&limit=20").json()
    short_item = next(
        item for item in short_payload["items"] if item["root"]["post_id"] == "wrap-1"
    )

    _materialize_published_events(
        raw=raw,
        feed_db=long_feed,
        events_db=long_events,
        through=date(2026, 7, 11),
        days=2,
    )
    _configure_event_read_model(
        tmp_path,
        monkeypatch,
        feed_db=long_feed,
        events_db=long_events,
        registry=registry,
    )
    long_payload = client.get("/api/events?date=2026-07-10&limit=20").json()
    long_item = next(
        item for item in long_payload["items"] if item["root"]["post_id"] == "wrap-1"
    )

    for key in (
        "event_id",
        "canonical_root_post_id",
        "presentation_root_post_id",
        "semantic_snapshot_sha256",
        "anchor_types",
        "why_grouped",
    ):
        assert long_item[key] == short_item[key]
    assert long_item["member_count"] > short_item["member_count"]
    assert long_item["link_count"] == 2
    assert long_item["event_id"] == event_store._canonical_event_id(
        "twitterapi_io", "later-root"
    )


def test_singleton_event_ids_are_qualified_by_provider():
    item = {
        "post_id": "shared-provider-id",
        "published_at": "2026-07-11T08:00:00+00:00",
        "raw_sha256": "raw-hash",
        "author": {"entity_id": 1},
        "observed_directly": True,
        "amplifiers": [],
        "attention_score": 50.0,
        "score_components": {"public_interactions": 10},
    }
    twitter = event_store._singleton({**item, "provider": "twitterapi.io"})
    github = event_store._singleton({**item, "provider": "github"})

    assert twitter["event_id"] != github["event_id"]
    assert twitter["event_id"] == event_store._singleton(
        {**item, "provider": "twitterapi.io"}
    )["event_id"]
    assert twitter["event_id"] == event_store._canonical_event_id(
        "twitterapi.io", "shared-provider-id"
    )
    assert github["event_id"] == event_store._canonical_event_id(
        "github", "shared-provider-id"
    )


def test_event_reader_requests_complete_feed_candidates_once(monkeypatch):
    calls = []

    def fake_feed_payload(*, limit, offset, **kwargs):
        calls.append((limit, offset, kwargs["run_id"]))
        total = 5_001
        end = min(offset + limit, total)
        return {
            "available": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "score_formula": {},
            "items": [
                {
                    "provider": "twitterapi_io",
                    "post_id": str(index),
                }
                for index in range(offset, end)
            ],
        }

    monkeypatch.setattr(feed_store, "feed_payload", fake_feed_payload)

    result = event_store._all_feed_candidates(day="2026-07-11", run_id="feed-run")

    assert len(result["items"]) == 5_001
    assert result["items"][-1]["post_id"] == "5000"
    assert calls == [(2**31 - 1, 0, "feed-run")]


def test_feed_candidate_identity_is_provider_qualified():
    twitter = {"provider": "twitterapi_io", "post_id": "same-id"}
    github = {"provider": "github", "post_id": "same-id"}

    candidates = {
        event_store._feed_key(item): item for item in (twitter, github)
    }
    consumed = {event_store._feed_key(twitter)}

    assert len(candidates) == 2
    assert event_store._feed_key(twitter) in consumed
    assert event_store._feed_key(github) not in consumed
