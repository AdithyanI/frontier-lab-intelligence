from fli.scoring import development_attention as attention


def participant(
    entity_id: int,
    position: float,
    *roles: str,
) -> attention.Participant:
    return attention.Participant(
        entity_id=entity_id,
        position=position,
        roles=roles,
    )


def test_rank_counts_each_registry_entity_once_across_roles():
    inputs = attention.RankInputs(
        participants=(
            participant(1, 0.9, "source", "retweet"),
            participant(2, 0.5, "quote"),
        ),
        public_interactions=12,
        development_id="development-a",
    )

    assert inputs.trusted_attention == 2
    assert float(inputs.mean_participant_position) == 0.7
    assert inputs.payload()["participants"][0]["roles"] == ["source", "retweet"]


def test_rank_is_lexicographic_and_stable():
    ranked = attention.rank_developments(
        [
            (
                {"development_id": "public"},
                attention.RankInputs(
                    participants=(participant(1, 0.1, "source"),),
                    public_interactions=10_000,
                    development_id="public",
                ),
            ),
            (
                {"development_id": "trusted"},
                attention.RankInputs(
                    participants=(
                        participant(1, 0.1, "source"),
                        participant(2, 0.1, "retweet"),
                    ),
                    public_interactions=1,
                    development_id="trusted",
                ),
            ),
            (
                {"development_id": "mean"},
                attention.RankInputs(
                    participants=(participant(3, 0.9, "source"),),
                    public_interactions=0,
                    development_id="mean",
                ),
            ),
        ]
    )

    assert [item["development_id"] for item in ranked] == [
        "trusted",
        "mean",
        "public",
    ]
    assert ranked[0]["rank_components"]["decided_at_layer"] == 1
    assert ranked[1]["rank_components"]["decided_at_layer"] == 2

