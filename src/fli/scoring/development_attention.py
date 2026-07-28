"""Pure layered ranking for one canonical day of Developments."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Sequence


DAILY_RANK_VERSION = "daily-development-rank-v1"
POSITION_QUANTUM = Decimal("0.000001")
POSITION_ZERO = Decimal("0.000000")
POSITION_ONE = Decimal("1.000000")
LAYER_NAMES = (
    "trusted_attention",
    "mean_participant_position",
    "public_interactions",
    "development_id",
)


def _position(value: Decimal | float | int | str) -> Decimal:
    position = value if isinstance(value, Decimal) else Decimal(str(value))
    if not position.is_finite() or not POSITION_ZERO <= position <= POSITION_ONE:
        raise ValueError("network position must be between 0 and 1")
    return position.quantize(POSITION_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Participant:
    """One Registry entity contributing attention to a Development."""

    entity_id: int
    position: Decimal
    entity_name: str = ""
    entity_kind: str = ""
    handle: str = ""
    roles: tuple[str, ...] = ()
    source_urls: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.entity_id < 1:
            raise ValueError("entity_id must be positive")
        object.__setattr__(self, "position", _position(self.position))
        normalized_roles = tuple(
            sorted(
                set(self.roles),
                key=lambda role: (
                    {"source": 0, "quote": 1, "retweet": 2}.get(role, 9),
                    role,
                ),
            )
        )
        if any(role not in {"source", "quote", "retweet"} for role in normalized_roles):
            raise ValueError("participant roles must be source, quote, or retweet")
        object.__setattr__(self, "roles", normalized_roles)
        object.__setattr__(self, "source_urls", tuple(sorted(set(self.source_urls))))

    def payload(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "entity_kind": self.entity_kind,
            "handle": self.handle,
            "roles": list(self.roles),
            "position": float(self.position),
            "source_urls": list(self.source_urls),
        }


@dataclass(frozen=True)
class RankInputs:
    participants: tuple[Participant, ...]
    public_interactions: int
    development_id: str

    def __post_init__(self) -> None:
        entity_ids = [participant.entity_id for participant in self.participants]
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError("participants must be deduplicated by entity_id")
        if self.public_interactions < 0:
            raise ValueError("public_interactions cannot be negative")
        if not self.development_id:
            raise ValueError("development_id is required")

    @property
    def trusted_attention(self) -> int:
        return len(self.participants)

    @property
    def mean_participant_position(self) -> Decimal:
        if not self.participants:
            return POSITION_ZERO
        return _position(
            sum(
                (participant.position for participant in self.participants),
                start=POSITION_ZERO,
            )
            / len(self.participants)
        )

    def substantive_key(self) -> tuple[int, Decimal, int]:
        return (
            self.trusted_attention,
            self.mean_participant_position,
            self.public_interactions,
        )

    def sort_key(self) -> tuple[int | Decimal | str, ...]:
        return (
            -self.trusted_attention,
            -self.mean_participant_position,
            -self.public_interactions,
            self.development_id,
        )

    def payload(self, *, decided_at_layer: int | None = None) -> dict[str, Any]:
        return {
            "version": DAILY_RANK_VERSION,
            "trusted_attention": self.trusted_attention,
            "participants": [
                participant.payload()
                for participant in sorted(
                    self.participants,
                    key=lambda participant: (
                        -participant.position,
                        participant.entity_id,
                    ),
                )
            ],
            "mean_participant_position": float(self.mean_participant_position),
            "public_interactions": self.public_interactions,
            "decided_at_layer": decided_at_layer,
        }


def deciding_layer(left: RankInputs, right: RankInputs) -> int:
    for index, (left_value, right_value) in enumerate(
        zip(left.substantive_key(), right.substantive_key(), strict=True),
        start=1,
    ):
        if left_value != right_value:
            return index
    return 4


def rank_developments(
    rows: Sequence[tuple[dict[str, Any], RankInputs]],
) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: row[1].sort_key())
    ranked: list[dict[str, Any]] = []
    for index, (item, inputs) in enumerate(ordered):
        if len(ordered) == 1:
            layer = 4
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
