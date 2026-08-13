import numpy as np

from ionosphere_fdtd.mesh import build_geodesic_mesh
from verification.maxwell_spectrum.model import analyze_maxwell_spectrum,apply_one_form_hodge_laplacian


def test_one_form_operator_is_positive() -> None:
    mesh=build_geodesic_mesh(1);values=np.random.default_rng(4).standard_normal(mesh.n_edges);weight=mesh.dual_edge_angles/mesh.primal_edge_angles
    assert np.sum(weight*values*apply_one_form_hodge_laplacian(mesh,values))>0


def test_maxwell_spectrum_contains_both_polarizations() -> None:
    result=analyze_maxwell_spectrum(build_geodesic_mesh(2),np.asarray((1,2,3)))
    np.testing.assert_array_equal(result.degree,(1,2,3));assert np.all(np.isfinite(result.tm_wavenumber_error));assert np.all(np.isfinite(result.te_wavenumber_error))
