import random

import pytest

from fli.scoring import attention


def _voter(entity_id: int, position: float) -> attention.Voter:
    return attention.Voter(
        entity_id=entity_id,
        position=position,
        entity_name=f"Entity {entity_id}",
    )


def _inputs(
    event_id: str,
    *,
    voter_positions: tuple[float, ...] = (),
    author_position: float = 0.0,
    public_interactions: int = 0,
) -> attention.RankInputs:
    return attention.RankInputs(
        voters=tuple(
            _voter(entity_id, position)
            for entity_id, position in enumerate(voter_positions, start=1)
        ),
        author_position=author_position,
        public_interactions=public_interactions,
        event_id=event_id,
    )


def test_dense_rank_positions_use_rank_levels_so_top_and_bottom_are_bounded():
    positions = attention.entity_positions(
        {
            10: {
                "network_rank": 1,
                "network_rank_total": 2_524,
                "network_rank_level_total": 663,
            },
            20: {
                "network_rank": 332,
                "network_rank_total": 2_524,
                "network_rank_level_total": 663,
            },
            30: {
                "network_rank": 663,
                "network_rank_total": 2_524,
                "network_rank_level_total": 663,
            },
        }
    )

    assert positions[10] == 1.0
    assert positions[20] == pytest.approx(0.5)
    assert positions[30] == 0.0


def test_lexicographic_layers_only_break_ties_in_order():
    rows = [
        (
            {"event_id": "three-low-voters"},
            _inputs("three-low-voters", voter_positions=(0.1, 0.1, 0.1)),
        ),
        (
            {"event_id": "two-top-voters"},
            _inputs("two-top-voters", voter_positions=(1.0, 1.0)),
        ),
        (
            {"event_id": "mean-wins"},
            _inputs(
                "mean-wins",
                voter_positions=(0.9,),
                author_position=0.1,
                public_interactions=1,
            ),
        ),
        (
            {"event_id": "author-wins"},
            _inputs(
                "author-wins",
                voter_positions=(0.5,),
                author_position=0.9,
                public_interactions=1,
            ),
        ),
        (
            {"event_id": "public-wins"},
            _inputs(
                "public-wins",
                voter_positions=(0.5,),
                author_position=0.5,
                public_interactions=100,
            ),
        ),
        (
            {"event_id": "event-a"},
            _inputs(
                "event-a",
                voter_positions=(0.5,),
                author_position=0.5,
                public_interactions=10,
            ),
        ),
        (
            {"event_id": "event-b"},
            _inputs(
                "event-b",
                voter_positions=(0.5,),
                author_position=0.5,
                public_interactions=10,
            ),
        ),
    ]

    ranked = attention.rank_events(rows)

    assert [row["event_id"] for row in ranked] == [
        "three-low-voters",
        "two-top-voters",
        "mean-wins",
        "author-wins",
        "public-wins",
        "event-a",
        "event-b",
    ]
    assert ranked[0]["rank_components"]["decided_at_layer"] == 1
    assert ranked[2]["rank_components"]["decided_at_layer"] == 2
    assert ranked[3]["rank_components"]["decided_at_layer"] == 3
    assert ranked[4]["rank_components"]["decided_at_layer"] == 4
    assert ranked[5]["rank_components"]["decided_at_layer"] == 5


def test_daily_rank_is_deterministic_and_has_no_scalar_score():
    rows = [
        (
            {"event_id": event_id, "title": event_id},
            _inputs(
                event_id,
                voter_positions=(0.75,),
                author_position=0.5,
                public_interactions=10,
            ),
        )
        for event_id in ("event-c", "event-a", "event-b")
    ]
    expected = ["event-a", "event-b", "event-c"]

    for seed in range(10):
        shuffled = list(rows)
        random.Random(seed).shuffle(shuffled)
        ranked = attention.rank_events(shuffled)

        assert [row["event_id"] for row in ranked] == expected
        assert [row["daily_rank"] for row in ranked] == [1, 2, 3]
        assert all(row["rank_components"]["version"] == "daily-rank-v2" for row in ranked)
        assert all("attention_score" not in row for row in ranked)
        assert all("score" not in row for row in ranked)
        assert all("score_components" not in row for row in ranked)
        assert all("score" not in row["rank_components"] for row in ranked)


def test_rank_inputs_reject_duplicate_voters_and_zero_voters_have_zero_mean():
    with pytest.raises(ValueError, match="deduplicated"):
        attention.RankInputs(
            voters=(_voter(1, 0.2), _voter(1, 0.8)),
            author_position=0.0,
            public_interactions=0,
            event_id="duplicate",
        )

    inputs = _inputs("zero-voters", author_position=1.0)

    assert inputs.trusted_votes == 0
    assert inputs.mean_voter_position == 0.0
