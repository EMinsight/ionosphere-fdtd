import numpy as np

from ionosphere_fdtd.constants import EARTH_RADIUS_M
from verification.merged_latlon.model import apply_negative_laplacian, build_merged_grid, conservative_cfl_bound_s, harmonic_result


def test_merged_grid_closes_area_and_has_periodic_flux() -> None:
    grid = build_merged_grid(64)
    np.testing.assert_allclose(grid.area_m2.sum(), 4.0 * np.pi * EARTH_RADIUS_M**2, rtol=1e-14)
    np.testing.assert_allclose(apply_negative_laplacian(grid, np.ones(grid.cell_count)), 0.0)


def test_merged_operator_is_conservative_and_positive() -> None:
    grid = build_merged_grid(64)
    values = np.random.default_rng(20260814).standard_normal(grid.cell_count)
    applied = apply_negative_laplacian(grid, values)
    assert abs(np.sum(grid.area_m2 * applied)) < 1e-8
    assert np.sum(grid.area_m2 * values * applied) > 0.0
    assert conservative_cfl_bound_s(grid, 299_792_458.0) > 0.0


def test_sectoral_harmonic_converges_under_refinement() -> None:
    errors = [abs(harmonic_result(build_merged_grid(count), 8).relative_eigenvalue_error) for count in (64, 128, 256)]
    assert errors[2] < errors[1] < errors[0]
