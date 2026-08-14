import numpy as np

from verification.analytic_solutions.operator_analysis import compare_te_operator_modes


def test_ritz_mode_comparison_is_finite() -> None:
    result = compare_te_operator_modes(1, 8, krylov_dimension=6)
    assert np.isfinite(result.analytic_relative_residual)
    assert np.isfinite(result.ritz_relative_residual)
    assert 0.0 <= result.analytic_ritz_overlap <= 1.0 + 1.0e-12
