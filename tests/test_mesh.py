import numpy as np
import pytest

from ionosphere_fdtd.mesh import build_geodesic_mesh


@pytest.mark.parametrize("level", range(4))
def test_icosphere_counts_and_dual_topology(level: int) -> None:
    mesh = build_geodesic_mesh(level)
    assert mesh.n_vertices == 10 * 4**level + 2
    assert mesh.n_edges == 30 * 4**level
    assert mesh.n_faces == 20 * 4**level
    assert np.count_nonzero(mesh.vertex_degree == 5) == 12
    if level > 0:
        assert np.count_nonzero(mesh.vertex_degree == 6) == mesh.n_vertices - 12
    assert np.isclose(mesh.face_solid_angles.sum(), 4 * np.pi)
    assert np.isclose(mesh.dual_cell_solid_angles.sum(), 4 * np.pi)


def test_boundary_of_boundary_is_zero() -> None:
    mesh = build_geodesic_mesh(2)
    vertex_values = np.arange(mesh.n_vertices, dtype=float)
    edge_gradient = mesh.edge_difference(vertex_values)
    assert np.allclose(mesh.face_circulation(edge_gradient), 0.0)


def test_dual_edge_circulations_cancel_globally() -> None:
    mesh = build_geodesic_mesh(1)
    edge_values = np.linspace(-1.0, 1.0, mesh.n_edges)
    assert np.isclose(mesh.dual_cell_circulation(edge_values).sum(), 0.0)


def test_polar_orientation_places_pentagons_at_geographic_poles() -> None:
    native = build_geodesic_mesh(2)
    polar = build_geodesic_mesh(2, orientation="polar")

    pentagons = polar.vertices[polar.vertex_degree == 5]
    assert np.max(pentagons[:, 2]) == pytest.approx(1.0)
    assert np.min(pentagons[:, 2]) == pytest.approx(-1.0)
    np.testing.assert_allclose(
        np.sort(native.primal_edge_angles), np.sort(polar.primal_edge_angles)
    )
    np.testing.assert_allclose(
        np.sort(native.dual_cell_solid_angles),
        np.sort(polar.dual_cell_solid_angles),
    )


def test_mesh_rejects_unknown_orientation() -> None:
    with pytest.raises(ValueError, match="orientation"):
        build_geodesic_mesh(0, orientation="sideways")
