import pytest

from fli.routing import freshness


def _packet(*sources):
    return {"event_id": "event", "day": "2026-07-14", "sources": list(sources)}


def _x(source_id, relation="root"):
    return {
        "source_type": "x_post",
        "source_id": source_id,
        "url": f"https://x.com/a/status/{source_id}",
        "text": source_id,
        "author": "@a",
        "relation": relation,
    }


def test_seven_day_boundary_is_inclusive_and_future_sources_are_rejected():
    assert freshness.is_current(
        published_at="2026-07-07T23:59:00+00:00",
        evaluation_day="2026-07-14",
    )
    assert not freshness.is_current(
        published_at="2026-07-06T23:59:00+00:00",
        evaluation_day="2026-07-14",
    )
    assert not freshness.is_current(
        published_at="2026-07-15T00:00:00+00:00",
        evaluation_day="2026-07-14",
    )


def test_pruning_excludes_an_event_with_only_an_old_root():
    packet, summary = freshness.prune_packet_payload(
        _packet(_x("old")),
        evaluation_day="2026-07-14",
        published_at_by_source_id={"old": "2025-11-19T12:00:00+00:00"},
    )

    assert packet is None
    assert summary["excluded"] is True
    assert summary["stale_x_source_ids"] == ["old"]


def test_pruning_promotes_current_author_update_and_drops_unbound_artifact():
    packet, summary = freshness.prune_packet_payload(
        _packet(
            _x("old"),
            _x("current", "same_author_continuation"),
            {
                "source_type": "artifact",
                "source_id": "artifact",
                "url": "https://example.com/old",
                "text": "Old artifact",
                "relation": "self_published_artifact",
            },
        ),
        evaluation_day="2026-07-14",
        published_at_by_source_id={
            "old": "2025-07-15T12:00:00+00:00",
            "current": "2026-07-10T12:00:00+00:00",
        },
    )

    assert packet is not None
    assert [source["source_id"] for source in packet["sources"]] == ["current"]
    assert packet["sources"][0]["relation"] == "root"
    assert packet["sources"][0]["posted"] == "2026-07-10T12:00:00+00:00"
    assert summary["root_replaced"] is True


def test_pruning_requires_application_owned_dates():
    with pytest.raises(ValueError, match="no application-owned publication time"):
        freshness.prune_packet_payload(
            _packet(_x("missing")),
            evaluation_day="2026-07-14",
            published_at_by_source_id={},
        )
