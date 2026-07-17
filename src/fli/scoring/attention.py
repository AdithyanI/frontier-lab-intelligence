"""Versioned attention-score formulas shared by the Feed and offline replay."""

from __future__ import annotations

import bisect
from dataclasses import asdict, dataclass
import math
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class AttentionFormula:
    """One explicit attention-score contract.

    Fixed ``amplifier_cap`` and ``support_knee`` values select saturating-log
    transforms. ``None`` preserves the v1.1 day-relative percentile transform.
    Public engagement remains a day-relative percentile in both contracts.
    """

    version: str
    network_attention_weight: float
    originator_support_weight: float
    public_engagement_weight: float
    amplifier_cap: int | None = None
    support_knee: int | None = None

    def __post_init__(self) -> None:
        weights = (
            self.network_attention_weight,
            self.originator_support_weight,
            self.public_engagement_weight,
        )
        if any(not math.isfinite(weight) or weight < 0 for weight in weights):
            raise ValueError("attention weights must be finite and non-negative")
        total = (
            self.network_attention_weight
            + self.originator_support_weight
            + self.public_engagement_weight
        )
        if not math.isclose(total, 1.0):
            raise ValueError("attention weights must sum to 1")
        if (self.amplifier_cap is None) != (self.support_knee is None):
            raise ValueError("fixed attention transforms require both anchors")
        if self.amplifier_cap is not None and self.amplifier_cap < 1:
            raise ValueError("amplifier_cap must be positive")
        if self.support_knee is not None and self.support_knee < 1:
            raise ValueError("support_knee must be positive")

    @property
    def uses_fixed_curves(self) -> bool:
        return self.amplifier_cap is not None

    def payload(self) -> dict[str, Any]:
        return {
            key: value for key, value in asdict(self).items() if value is not None
        }


ATTENTION_V1_1 = AttentionFormula(
    version="attention-v1.1",
    network_attention_weight=0.55,
    originator_support_weight=0.25,
    public_engagement_weight=0.20,
)

ATTENTION_V2_CANDIDATE = AttentionFormula(
    version="attention-v2-candidate",
    network_attention_weight=0.55,
    originator_support_weight=0.20,
    public_engagement_weight=0.25,
    amplifier_cap=16,
    support_knee=150,
)


def percentiles(values: Iterable[float]) -> dict[float, float]:
    """Map each value to the share of observations strictly below it."""
    sequence = list(values)
    ordered = sorted(sequence)
    if not ordered or ordered[-1] <= 0:
        return {value: 0.0 for value in sequence}
    denominator = max(len(ordered) - 1, 1)
    return {
        value: bisect.bisect_left(ordered, value) / denominator
        for value in set(sequence)
    }


def saturating_log(value: int | float, anchor: int) -> float:
    if value <= 0:
        return 0.0
    return min(1.0, math.log1p(value) / math.log1p(anchor))


def score_components(
    components: Mapping[str, Any], formula: AttentionFormula
) -> tuple[float, dict[str, float]]:
    """Score stored raw components under one formula.

    The stored public-engagement percentile is valid for both versions because
    v2 deliberately leaves that day-relative transform unchanged.
    """
    engagement = float(
        components.get(
            "public_engagement_factor",
            components["public_engagement_percentile"],
        )
    )
    if not math.isfinite(engagement) or not 0 <= engagement <= 1:
        raise ValueError("public engagement factor must be between 0 and 1")
    if formula.uses_fixed_curves:
        assert formula.amplifier_cap is not None
        assert formula.support_knee is not None
        network = saturating_log(
            int(components["registry_amplifiers"]), formula.amplifier_cap
        )
        support = saturating_log(
            int(components["originator_network_support"]), formula.support_knee
        )
    else:
        network = float(
            components.get(
                "network_attention_factor",
                components["network_attention_percentile"],
            )
        )
        support = float(
            components.get(
                "originator_support_factor",
                components["originator_support_percentile"],
            )
        )
        if any(
            not math.isfinite(value) or not 0 <= value <= 1
            for value in (network, support)
        ):
            raise ValueError("attention factors must be between 0 and 1")
    score = 100 * (
        formula.network_attention_weight * network
        + formula.originator_support_weight * support
        + formula.public_engagement_weight * engagement
    )
    return round(score, 1), {
        "network_attention_factor": round(network, 6),
        "originator_support_factor": round(support, 6),
        "public_engagement_factor": round(engagement, 6),
    }


def apply_attention_scores(
    items: list[dict[str, Any]], formula: AttentionFormula = ATTENTION_V1_1
) -> None:
    """Apply a formula to one complete visible Feed day in place."""
    network_percentiles = percentiles(
        float(item["_network_raw"]) for item in items
    )
    support_percentiles = percentiles(
        float(item["_originator_support"]) for item in items
    )
    engagement_percentiles = percentiles(
        math.log1p(item["_engagement"]) for item in items
    )
    for item in items:
        raw_components = {
            "registry_amplifiers": item["_amplifier_count"],
            "originator_network_support": item["_originator_support"],
            "network_attention_percentile": network_percentiles[
                float(item["_network_raw"])
            ],
            "originator_support_percentile": support_percentiles[
                float(item["_originator_support"])
            ],
            "public_engagement_percentile": engagement_percentiles[
                math.log1p(item["_engagement"])
            ],
        }
        score, factors = score_components(raw_components, formula)
        item["attention_score"] = score
        item["score_components"] = {
            "registry_amplifiers": item.pop("_amplifier_count"),
            "originator_network_support": item.pop("_originator_support"),
            "originator_network_rank": item.pop("_originator_rank"),
            "public_interactions": item.pop("_engagement"),
            "network_attention_percentile": round(
                raw_components["network_attention_percentile"], 3
            ),
            "originator_support_percentile": round(
                raw_components["originator_support_percentile"], 3
            ),
            "public_engagement_percentile": round(
                raw_components["public_engagement_percentile"], 3
            ),
            **factors,
        }
        item.pop("_network_raw")
