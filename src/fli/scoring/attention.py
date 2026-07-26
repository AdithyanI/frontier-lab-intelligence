"""Pure layered ranking for one canonical day of Events."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Sequence


DAILY_RANK_VERSION = "daily-rank-v2"
LAYER_NAMES = (
    "trusted_votes",
    "mean_voter_position",
    "author_position",
    "public_interactions",
    "event_id",
)


def network_position(*, network_rank: int, network_rank_total: int) -> float:
    """Convert a 1-based entity support rank to a 0–1 network position."""
    if network_rank < 1:
        raise ValueError("network_rank must be positive")
    if network_rank_total < network_rank:
        raise ValueError("network_rank_total must include network_rank")
    if network_rank_total == 1:
        return 1.0
    return 1 - (network_rank - 1) / (network_rank_total - 1)


@dataclass(frozen=True)
class Voter:
    entity_id: int
    position: float
    entity_name: str = ""
    entity_kind: str = ""
    handle: str = ""
    relation_type: str = ""
    source_url: str = ""

    def __post_init__(self) -> None:
        if self.entity_id < 1:
            raise ValueError("entity_id must be positive")
        if not math.isfinite(self.position) or not 0 <= self.position <= 1:
            raise ValueError("voter position must be between 0 and 1")

    def payload(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "entity_kind": self.entity_kind,
            "handle": self.handle,
            "relation_type": self.relation_type,
            "position": round(self.position, 6),
            "source_url": self.source_url,
        }


@dataclass(frozen=True)
class RankInputs:
    voters: tuple[Voter, ...]
    author_position: float
    public_interactions: int
    event_id: str

    def __post_init__(self) -> None:
        entity_ids = [voter.entity_id for voter in self.voters]
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError("voters must be deduplicated by entity_id")
        if not math.isfinite(self.author_position) or not 0 <= self.author_position <= 1:
            raise ValueError("author_position must be between 0 and 1")
        if self.public_interactions < 0:
            raise ValueError("public_interactions cannot be negative")
        if not self.event_id:
            raise ValueError("event_id is required")

    @property
    def trusted_votes(self) -> int:
        return len(self.voters)

    @property
    def mean_voter_position(self) -> float:
        if not self.voters:
            return 0.0
        return sum(voter.position for voter in self.voters) / len(self.voters)

    def substantive_key(self) -> tuple[int, float, float, int]:
        """Return the four descending ranking layers in their natural units."""
        return (
            self.trusted_votes,
            self.mean_voter_position,
            self.author_position,
            self.public_interactions,
        )

    def sort_key(self) -> tuple[int | float | str, ...]:
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
            "mean_voter_position": round(self.mean_voter_position, 6),
            "author_position": round(self.author_position, 6),
            "public_interactions": self.public_interactions,
            "decided_at_layer": decided_at_layer,
        }


def sort_key(inputs: RankInputs) -> tuple[int | float | str, ...]:
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
    """Project the canonical entity-union rank table to 0–1 positions."""
    items = ranks.items() if isinstance(ranks, dict) else ranks
    positions: dict[int, float] = {}
    for entity_id, row in items:
        positions[int(entity_id)] = network_position(
            network_rank=int(row["network_rank"]),
            network_rank_total=int(
                row.get("network_rank_level_total", row["network_rank_total"])
            ),
        )
    return positions
