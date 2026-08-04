import numpy as np
import pytest

from ionosphere_fdtd.mesh import build_geodesic_mesh
from ionosphere_fdtd.mesh_quality import (
    laplace_eigenmode_errors,
    mesh_quality_metrics,
    scalar_laplacian,
)


def test_scalar_laplacian_annihilates_constant_field() -> None:
    mesh = build_geodesic_mesh(2)
    result = scalar_laplacian(mesh, np.ones(mesh.n_vertices))
    np.testing.assert_allclose(result, 0.0, rtol=0.0, atol=1.0e-14)


def test_scalar_laplacian_rejects_wrong_shape() -> None:
    mesh = build_geodesic_mesh(1)
    with pytest.raises(ValueError, match="values"):
        scalar_laplacian(mesh, np.ones(mesh.n_vertices + 1))


def test_laplace_eigenmode_error_converges_with_refinement() -> None:
    coarse = laplace_eigenmode_errors(build_geodesic_mesh(2))
    fine = laplace_eigenmode_errors(build_geodesic_mesh(3))

    assert max(fine[label] for label in fine if label.startswith("l1_")) < max(
        coarse[label] for label in coarse if label.startswith("l1_")
    )
    assert max(fine[label] for label in fine if label.startswith("l2_")) < max(
        coarse[label] for label in coarse if label.startswith("l2_")
    )


def test_projected_optimizer_improves_laplace_consistency() -> None:
    base = mesh_quality_metrics(build_geodesic_mesh(3))
    optimized = mesh_quality_metrics(
        build_geodesic_mesh(3, optimization_steps=1)
    )

    assert optimized.laplace_l1_max_relative_l2 < base.laplace_l1_max_relative_l2
    assert optimized.laplace_l2_max_relative_l2 < base.laplace_l2_max_relative_l2
    assert optimized.adjacent_dual_area_rms_relative < (
        base.adjacent_dual_area_rms_relative
    )
