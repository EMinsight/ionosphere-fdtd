from verification.analytic_solutions.periodic import measure_periodic_mode


def test_periodic_lossy_mode_converges() -> None:
    coarse = measure_periodic_mode(64, steps=500)
    fine = measure_periodic_mode(128, steps=500)
    assert abs(fine.relative_decay_error) < abs(coarse.relative_decay_error)
    assert abs(fine.relative_frequency_error) < abs(coarse.relative_frequency_error)
    assert fine.measured_decay_per_s > 0.0
    assert fine.measured_frequency_hz > 0.0
