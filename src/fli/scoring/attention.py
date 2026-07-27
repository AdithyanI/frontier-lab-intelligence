"""Pure layered ranking for one canonical day of Events."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable, Sequence


DAILY_RANK_VERSION = "daily-rank-v2"
POSITION_QUANTUM = Decimal("0.000001")
POSITION_ZERO = Decimal("0.000000")
POSITION_ONE = Decimal("1.000000")
LAYER_NAMES = (
    "trusted_votes",
    "mean_voter_position",
    "author_position",
    "public_interactions",
    "event_id",
)


def _position(value: Decimal | float | int | str) -> Decimal:
    """Return the one canonical six-decimal representation of a position."""
    position = value if isinstance(value, Decimal) else Decimal(str(value))
    if not position.is_finite() or not POSITION_ZERO <= position <= POSITION_ONE:
        raise ValueError("network position must be between 0 and 1")
    return position.quantize(POSITION_QUANTUM, rounding=ROUND_HALF_UP)


def network_position(
    *, network_entities_below: int, network_rank_total: int
) -> Decimal:
    """Return an entity's tie-aware support percentile on the 0–1 scale."""
    if network_rank_total < 1:
        raise ValueError("network_rank_total must be positive")
    if not 0 <= network_entities_below < network_rank_total:
        raise ValueError(
            "network_entities_below must identify fewer entities than "
            "network_rank_total"
        )
    if network_rank_total == 1:
        return POSITION_ONE
    return _position(
        Decimal(network_entities_below) / Decimal(network_rank_total - 1)
    )


@dataclass(frozen=True)
class Voter:
    entity_id: int
    position: Decimal
    entity_name: str = ""
    entity_kind: str = ""
    handle: str = ""
    relation_type: str = ""
    source_url: str = ""

    def __post_init__(self) -> None:
        if self.entity_id < 1:
            raise ValueError("entity_id must be positive")
        object.__setattr__(self, "position", _position(self.position))

    def payload(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "entity_kind": self.entity_kind,
            "handle": self.handle,
            "relation_type": self.relation_type,
            "position": float(self.position),
            "source_url": self.source_url,
        }


@dataclass(frozen=True)
class RankInputs:
    voters: tuple[Voter, ...]
    author_position: Decimal
    public_interactions: int
    event_id: str

    def __post_init__(self) -> None:
        entity_ids = [voter.entity_id for voter in self.voters]
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError("voters must be deduplicated by entity_id")
        object.__setattr__(self, "author_position", _position(self.author_position))
        if self.public_interactions < 0:
            raise ValueError("public_interactions cannot be negative")
        if not self.event_id:
            raise ValueError("event_id is required")

    @property
    def trusted_votes(self) -> int:
        return len(self.voters)

    @property
    def mean_voter_position(self) -> Decimal:
        if not self.voters:
            return POSITION_ZERO
        return _position(
            sum(
                (voter.position for voter in self.voters),
                start=POSITION_ZERO,
            )
            / len(self.voters)
        )

    def substantive_key(self) -> tuple[int, Decimal, Decimal, int]:
        """Return the four descending ranking layers in their natural units."""
        return (
            self.trusted_votes,
            self.mean_voter_position,
            self.author_position,
            self.public_interactions,
        )

    def sort_key(self) -> tuple[int | Decimal | str, ...]:
        """Return an ascending Python sort key for the descending layers."""
        return (
            -self.trusted_votes,
            -self.mean_voter_position,
            -self.author_position,
            -self.public_interactions,
            self.event_id,
        )

    def payload(self, *, decided_at_layer: int | None = None) -> dict[str, Any]:
        return {
            "version": DAILY_RANK_VERSION,
            "trusted_votes": self.trusted_votes,
            "voters": [
                voter.payload()
                for voter in sorted(
                    self.voters,
                    key=lambda voter: (-voter.position, voter.entity_id),
                )
            ],
            "mean_voter_position": float(self.mean_voter_position),
            "author_position": float(self.author_position),
            "public_interactions": self.public_interactions,
            "decided_at_layer": decided_at_layer,
        }


def sort_key(inputs: RankInputs) -> tuple[int | Decimal | str, ...]:
    return inputs.sort_key()


def deciding_layer(left: RankInputs, right: RankInputs) -> int:
    """Return the first layer that separates two already ordered Events."""
    for index, (left_value, right_value) in enumerate(
        zip(left.substantive_key(), right.substantive_key(), strict=True),
        start=1,
    ):
        if left_value != right_value:
            return index
    return 5


def rank_events(
    rows: Sequence[tuple[dict[str, Any], RankInputs]],
) -> list[dict[str, Any]]:
    """Order a complete day and attach rank plus adjacent-layer attribution."""
    ordered = sorted(rows, key=lambda row: row[1].sort_key())
    ranked: list[dict[str, Any]] = []
    for index, (item, inputs) in enumerate(ordered):
        if len(ordered) == 1:
            layer = 5
        elif index < len(ordered) - 1:
            layer = deciding_layer(inputs, ordered[index + 1][1])
        else:
            layer = deciding_layer(ordered[index - 1][1], inputs)
        ranked.append(
            {
                **item,
                "daily_rank": index + 1,
                "rank_components": inputs.payload(decided_at_layer=layer),
            }
        )
    return ranked


def entity_positions(
    ranks: dict[int, dict[str, Any]] | Iterable[tuple[int, dict[str, Any]]],
) -> dict[int, float]:
    """Project entity-union support counts to tie-aware 0–1 percentiles."""
    items = ranks.items() if isinstance(ranks, dict) else ranks
    positions: dict[int, float] = {}
    for entity_id, row in items:
        positions[int(entity_id)] = float(
            network_position(
                network_entities_below=int(row["network_entities_below"]),
                network_rank_total=int(row["network_rank_total"]),
            )
        )
    return positions
