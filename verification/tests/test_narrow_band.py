import numpy as np

from verification.narrow_band.model import fit_amplitudes


def test_narrow_band_fit_recovers_known_propagation_constant() -> None:
    frequency = 400.0
    arcs = np.asarray((30.0, 45.0, 60.0, 75.0, 90.0))
    distance = np.deg2rad(arcs) * 6_371_000.0
    alpha = 8.0 / 1.0e6 * np.log(10.0) / 20.0
    beta = 2.0 * np.pi * frequency / (0.87 * 299_792_458.0)
    spreading = 1.0 / np.sqrt(np.sin(np.deg2rad(arcs)))
    amplitudes = spreading * np.exp((-alpha - 1j * beta) * distance)
    fit = fit_amplitudes(frequency, (0.0,), arcs, amplitudes)
    np.testing.assert_allclose(fit.attenuation_db_per_mm[0], 8.0, rtol=1e-10)
    np.testing.assert_allclose(fit.phase_velocity_fraction_c[0], 0.87, rtol=1e-10)
