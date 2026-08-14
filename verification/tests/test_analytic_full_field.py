import numpy as np

from verification.analytic_solutions.full_field import observed_order


def test_observed_order_recovers_second_order_sequence() -> None:
    np.testing.assert_allclose(observed_order(np.asarray((0.16, 0.04, 0.01))), 2.0)
