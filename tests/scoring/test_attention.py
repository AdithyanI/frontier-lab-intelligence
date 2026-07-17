import math

import pytest

from fli.scoring import attention


def _components(*, amplifiers: int, support: int, engagement: float = 0.5):
    return {
        "registry_amplifiers": amplifiers,
        "originator_network_support": support,
        "network_attention_percentile": 0.75,
        "originator_support_percentile": 0.6,
        "public_engagement_percentile": engagement,
    }


def test_v1_1_reproduces_stored_percentile_formula():
    score, factors = attention.score_components(
        _components(amplifiers=1, support=50), attention.ATTENTION_V1_1
    )

    # Python's round uses ties-to-even; production v1.1 does the same.
    assert score == 66.2
    assert factors == {
        "network_attention_factor": 0.75,
        "originator_support_factor": 0.6,
        "public_engagement_factor": 0.5,
    }


def test_v2_uses_fixed_saturating_curves():
    score, factors = attention.score_components(
        _components(amplifiers=16, support=150),
        attention.ATTENTION_V2_CANDIDATE,
    )

    assert score == 87.5
    assert factors["network_attention_factor"] == 1.0
    assert factors["originator_support_factor"] == 1.0


def test_v2_preserves_resolution_across_multiple_amplifiers():
    values = [
        attention.score_components(
            _components(amplifiers=count, support=50),
            attention.ATTENTION_V2_CANDIDATE,
        )[1]["network_attention_factor"]
        for count in (0, 1, 2, 4, 8, 16, 40)
    ]

    assert values == sorted(values)
    assert len(set(values[:6])) == 6
    assert values[-1] == values[-2] == 1.0


def test_attention_formula_rejects_invalid_contracts():
    with pytest.raises(ValueError, match="sum to 1"):
        attention.AttentionFormula(
            version="bad",
            network_attention_weight=0.5,
            originator_support_weight=0.5,
            public_engagement_weight=0.5,
        )
    with pytest.raises(ValueError, match="both anchors"):
        attention.AttentionFormula(
            version="bad",
            network_attention_weight=0.5,
            originator_support_weight=0.25,
            public_engagement_weight=0.25,
            amplifier_cap=8,
        )


def test_percentiles_keep_tied_values_at_bottom_of_tie_range():
    values = attention.percentiles([0.0, 1.0, 1.0, 2.0])

    assert values[0.0] == 0.0
    assert values[1.0] == pytest.approx(1 / 3)
    assert values[2.0] == 1.0
    assert math.isclose(attention.percentiles([0.0, 0.0])[0.0], 0.0)
