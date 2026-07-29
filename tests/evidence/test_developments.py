from fli.evidence import developments


def exact_event(
    event_id: str,
    *,
    rank: int,
    post_id: str,
    entity_id: int,
    entity_name: str,
    entity_kind: str = "person",
    voters: list[dict] | None = None,
) -> dict:
    voters = voters or []
    author = {
        "x_id": post_id,
        "handle": entity_name.lower(),
        "name": entity_name,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "entity_kind": entity_kind,
    }
    root = {
        "post_id": post_id,
        "author": author,
        "published_at": "2026-07-21T12:00:00+00:00",
        "text": f"{entity_name} source",
        "url": f"https://x.com/{author['handle']}/status/{post_id}",
        "post_type": "original",
        "observed_directly": True,
        "context": None,
        "amplifiers": voters,
        "metrics": {
            "likes": rank,
            "replies": 0,
            "reposts": 0,
            "quotes": 0,
            "views": None,
            "bookmarks": None,
        },
    }
    return {
        "event_id": event_id,
        "daily_rank": rank,
        "semantic_snapshot_sha256": f"snapshot-{event_id}",
        "root": root,
        "why_grouped": [],
        "evidence": [],
        "amplifiers": voters,
        "rank_components": {
            "voters": voters,
            "public_interactions": rank,
        },
        "is_grouped": False,
        "member_count": 1,
        "lifetime_member_count": 1,
        "day_member_count": 1,
        "activity_days": ["2026-07-21"],
        "first_activity_day": "2026-07-21",
        "link_count": 0,
        "first_hand_count": 1,
        "latest_evidence_at": "2026-07-21T12:00:00+00:00",
    }


def artifact(
    artifact_id: str,
    url: str,
    *,
    first_event_day: str = "2026-07-21",
) -> dict:
    return {
        "artifact_id": artifact_id,
        "canonical_url": url,
        "artifact_kind": "article",
        "title": "Release",
        "source_rank": 1,
        "merge_anchor": developments.artifact_is_merge_anchor(url),
        "first_event_day": first_event_day,
    }


def test_shared_release_artifact_forms_one_development_and_unions_participants():
    first = exact_event(
        "event-a",
        rank=2,
        post_id="post-a",
        entity_id=1,
        entity_name="Lab",
        entity_kind="organization",
        voters=[
            {
                "entity_id": 3,
                "position": 0.8,
                "entity_name": "Watcher",
                "entity_kind": "person",
                "handle": "watcher",
                "relation_type": "retweet",
                "network_support": 10,
                "network_position": 0.8,
                "source_url": "https://x.com/watcher/status/3",
            }
        ],
    )
    second = exact_event(
        "event-b",
        rank=4,
        post_id="post-b",
        entity_id=2,
        entity_name="Researcher",
        voters=[
            {
                "entity_id": 3,
                "position": 0.8,
                "entity_name": "Watcher",
                "entity_kind": "person",
                "handle": "watcher",
                "relation_type": "quote",
                "network_support": 10,
                "network_position": 0.8,
                "source_url": "https://x.com/watcher/status/4",
            }
        ],
    )
    shared = artifact("artifact-release", "https://example.com/releases/model-1")

    bundled = developments.bundle_events(
        items=[first, second],
        event_artifacts={"event-a": [shared], "event-b": [shared]},
        entity_positions={1: 0.6, 2: 0.7, 3: 0.8},
        day="2026-07-21",
    )

    assert len(bundled) == 1
    item = bundled[0]
    assert item["primary_event_id"] == "event-a"
    assert item["source_event_ids"] == ["event-a", "event-b"]
    assert item["original_poster_count"] == 2
    assert item["amplifier_count"] == 1
    assert item["_rank_inputs"].trusted_attention == 3
    assert item["development_artifacts"][0]["is_merge_basis"] is True


def test_generic_host_root_does_not_merge_events():
    events = [
        exact_event(
            "event-a",
            rank=1,
            post_id="post-a",
            entity_id=1,
            entity_name="One",
        ),
        exact_event(
            "event-b",
            rank=2,
            post_id="post-b",
            entity_id=2,
            entity_name="Two",
        ),
    ]
    root = artifact("artifact-root", "https://example.com/")

    bundled = developments.bundle_events(
        items=events,
        event_artifacts={"event-a": [root], "event-b": [root]},
        entity_positions={1: 0.5, 2: 0.5},
        day="2026-07-21",
    )

    assert len(bundled) == 2


def test_release_artifact_publishes_one_development_on_its_first_day():
    events = [
        exact_event(
            "event-a",
            rank=1,
            post_id="post-a",
            entity_id=1,
            entity_name="One",
        ),
        exact_event(
            "event-b",
            rank=2,
            post_id="post-b",
            entity_id=2,
            entity_name="Two",
        ),
    ]
    old_release = artifact(
        "artifact-release",
        "https://example.com/releases/model-1",
        first_event_day="2026-07-20",
    )

    bundled = developments.bundle_events(
        items=events,
        event_artifacts={
            "event-a": [old_release],
            "event-b": [old_release],
        },
        entity_positions={1: 0.5, 2: 0.5},
        day="2026-07-21",
    )

    assert bundled == []
