import numpy as np

from ionosphere_fdtd.constants import C_0, EARTH_RADIUS_M, EPSILON_0
from verification.analytic_solutions.model import conductive_relaxation, homogeneous_medium_propagation_constant, leapfrog_frequency_hz, pec_spherical_shell_frequencies_hz, spherical_surface_frequency_hz


def test_vacuum_plane_wave_reduces_to_c() -> None:
    result = homogeneous_medium_propagation_constant(400.0)
    assert result.attenuation_np_per_m == 0.0
    np.testing.assert_allclose(result.phase_velocity_m_per_s, C_0, rtol=1e-15)


def test_conductive_relaxation_has_exact_time_constant() -> None:
    sigma = 1.0e-3
    tau = EPSILON_0 / sigma
    np.testing.assert_allclose(conductive_relaxation(tau, initial_e_v_m=2.0, conductivity_s_m=sigma), 2.0 / np.e)


def test_surface_frequency_and_leapfrog_limit() -> None:
    frequency = spherical_surface_frequency_hz(8, EARTH_RADIUS_M)
    numerical = leapfrog_frequency_hz(2.0 * np.pi * frequency, 1.0e-8)
    np.testing.assert_allclose(numerical, frequency, rtol=1e-10)


def test_pec_shell_roots_are_ordered_for_both_polarizations() -> None:
    for polarization in ("TE", "TM"):
        roots = pec_spherical_shell_frequencies_hz(1, EARTH_RADIUS_M, EARTH_RADIUS_M + 100_000.0, polarization=polarization, count=2)
        assert np.all(np.diff(roots) > 0.0)
        assert np.all(roots > 0.0)
