"""Pure candidate formulas for trusted-network Event attention replay.

These candidates are offline experiments. Production remains on
``attention-v1.1`` until a later product decision explicitly selects and
versions a replacement.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence


TRUST_UPLIFT = 0.5
FLAT_CONVERGENCE = "trusted-flat-v0"
WEIGHTED_CONVERGENCE = "trusted-weighted-v0"
DAILY_BUDGET = "trusted-budget-v0"
CANDIDATE_VERSIONS = (
    FLAT_CONVERGENCE,
    WEIGHTED_CONVERGENCE,
    DAILY_BUDGET,
)


@dataclass(frozen=True)
class TrustedParticipant:
    entity_id: int
    trust_percentile: float

    def __post_init__(self) -> None:
        if self.entity_id < 1:
            raise ValueError("entity_id must be positive")
        if (
            not math.isfinite(self.trust_percentile)
            or not 0 <= self.trust_percentile <= 1
        ):
            raise ValueError("trust_percentile must be between 0 and 1")

    @property
    def bounded_weight(self) -> float:
        return 1 + TRUST_UPLIFT * self.trust_percentile


@dataclass(frozen=True)
class TrustedAttentionEvent:
    day: str
    event_id: str
    baseline_rank: int
    relevant: bool | None
    participants: tuple[TrustedParticipant, ...]
    independent_amplifier_count: int
    first_party_source: bool
    organization_authored: bool
    public_interactions: int
    day_member_count: int
    published_at: str
    author_name: str
    author_handle: str
    text: str
    url: str

    def __post_init__(self) -> None:
        ids = [participant.entity_id for participant in self.participants]
        if len(ids) != len(set(ids)):
            raise ValueError("participants must be deduplicated by entity_id")
        if self.baseline_rank < 1:
            raise ValueError("baseline_rank must be positive")
        if self.independent_amplifier_count < 0:
            raise ValueError("independent_amplifier_count cannot be negative")
        if self.public_interactions < 0:
            raise ValueError("public_interactions cannot be negative")

    @property
    def participant_count(self) -> int:
        return len(self.participants)

    @property
    def participant_trust_sum(self) -> float:
        return sum(
            participant.trust_percentile for participant in self.participants
        )


def trust_percentile(*, network_rank: int, network_rank_total: int) -> float:
    """Convert a 1-based Registry rank into 0–1 trust position.

    The highest-ranked entity receives 1 and the lowest-ranked entity receives
    0. A one-entity network receives 1.
    """
    if network_rank < 1:
        raise ValueError("network_rank must be positive")
    if network_rank_total < network_rank:
        raise ValueError("network_rank_total must include network_rank")
    if network_rank_total == 1:
        return 1.0
    return 1 - (network_rank - 1) / (network_rank_total - 1)


def participant_touch_counts(
    events: Sequence[TrustedAttentionEvent],
) -> dict[int, int]:
    """Count the distinct candidate Events each entity touched in one day."""
    touches: dict[int, int] = {}
    for event in events:
        for participant in event.participants:
            touches[participant.entity_id] = (
                touches.get(participant.entity_id, 0) + 1
            )
    return touches


def score_event(
    event: TrustedAttentionEvent,
    *,
    version: str,
    touch_counts: Mapping[int, int],
) -> float:
    """Return one candidate score in trusted-participant vote units."""
    if version == FLAT_CONVERGENCE:
        score = float(event.participant_count)
    elif version == WEIGHTED_CONVERGENCE:
        score = sum(
            participant.bounded_weight for participant in event.participants
        )
    elif version == DAILY_BUDGET:
        score = sum(
            participant.bounded_weight
            / max(1, int(touch_counts.get(participant.entity_id, 1)))
            for participant in event.participants
        )
    else:
        raise ValueError(f"Unknown trusted-attention candidate: {version}")
    return round(score, 6)


def rank_events(
    events: Sequence[TrustedAttentionEvent],
    *,
    version: str,
) -> list[tuple[TrustedAttentionEvent, float]]:
    """Rank one day with explicit deterministic secondary keys."""
    touches = participant_touch_counts(events)
    scored = [
        (
            event,
            score_event(event, version=version, touch_counts=touches),
        )
        for event in events
    ]
    return sorted(
        scored,
        key=lambda row: (
            -row[1],
            -row[0].independent_amplifier_count,
            -row[0].participant_trust_sum,
            -int(row[0].first_party_source),
            -row[0].public_interactions,
            row[0].event_id,
        ),
    )


def candidate_contract(version: str) -> dict[str, object]:
    if version == FLAT_CONVERGENCE:
        return {
            "version": version,
            "formula": "distinct trusted participants",
            "trust_uplift": 0.0,
            "daily_budget": False,
        }
    if version == WEIGHTED_CONVERGENCE:
        return {
            "version": version,
            "formula": "sum(1 + 0.5 × trust percentile)",
            "trust_uplift": TRUST_UPLIFT,
            "daily_budget": False,
        }
    if version == DAILY_BUDGET:
        return {
            "version": version,
            "formula": (
                "sum((1 + 0.5 × trust percentile) "
                "÷ candidate Events touched that day)"
            ),
            "trust_uplift": TRUST_UPLIFT,
            "daily_budget": True,
        }
    raise ValueError(f"Unknown trusted-attention candidate: {version}")
