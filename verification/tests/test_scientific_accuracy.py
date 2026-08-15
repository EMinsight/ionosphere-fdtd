import numpy as np

from verification.scientific_accuracy import (
    directional_dispersion,
    material_support_convergence,
)


def test_directional_dispersion_converges_at_fixed_physical_frequency() -> None:
    results = [directional_dispersion(level) for level in (2, 3, 4)]
    errors = np.asarray(
        [np.mean(result.phase_absolute_error) for result in results]
    )

    assert np.all(np.diff(errors) < 0.0)
    np.testing.assert_allclose(errors[:-1] / errors[1:], 4.0, rtol=0.08)
    assert np.all(
        np.diff([result.median_cells_per_wavelength for result in results]) > 0.0
    )


def test_directional_dispersion_resolves_pentagon_distance_and_heading() -> None:
    result = directional_dispersion(3, headings=18)

    assert np.count_nonzero(result.pentagon_distance_rad == 0.0) == 12
    assert np.all(result.phase_velocity_ratio_max >= result.phase_velocity_ratio_min)
    assert np.percentile(result.phase_anisotropy, 95.0) > 0.0
    assert np.isfinite(result.group_velocity_ratio_mean).all()


def test_material_support_disagreement_converges_under_refinement() -> None:
    results = [material_support_convergence(level) for level in (2, 3, 4)]

    assert np.all(
        np.diff([result.radial_rms_difference for result in results]) < 0.0
    )
    assert np.all(
        np.diff([result.tangential_rms_difference for result in results]) < 0.0
    )
