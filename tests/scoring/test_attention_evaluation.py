from fli.scoring import evaluation


def test_kendall_tau_reports_identical_and_reversed_orders():
    baseline = ["a", "b", "c", "d"]

    assert evaluation._kendall_tau(baseline, baseline) == 1.0
    assert evaluation._kendall_tau(baseline, list(reversed(baseline))) == -1.0


def test_candidate_grid_is_explicit_and_unique():
    formulas = evaluation.candidate_grid()

    assert len(formulas) == 18
    assert len({formula.version for formula in formulas}) == 18
    assert {formula.amplifier_cap for formula in formulas} == {8, 16, 32}
    assert {formula.support_knee for formula in formulas} == {100, 150, 300}
