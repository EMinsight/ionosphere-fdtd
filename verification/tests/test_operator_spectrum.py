import numpy as np

from ionosphere_fdtd.mesh import build_geodesic_mesh
from verification.operator_spectrum.model import (
    analyze_operator_spectrum,
    frequency_to_degree,
)


def test_frequency_mapping_covers_elf_degree_range() -> None:
    degree=frequency_to_degree(np.asarray((50.0,500.0)))
    np.testing.assert_allclose(degree,(8.55784755,75.56590101),rtol=1e-8)


def test_operator_spectrum_tracks_requested_degrees() -> None:
    result=analyze_operator_spectrum(build_geodesic_mesh(2),np.asarray((1,2,3)))
    np.testing.assert_array_equal(result.degree,(1,2,3))
    np.testing.assert_array_equal(result.mode_count,(3,3,3))
    assert np.all(np.isfinite(result.eigenvalue_relative_error_mean))
    assert np.all(result.eigenfunction_residual_max>=0)
