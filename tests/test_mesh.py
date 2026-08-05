import numpy as np
import pytest

from ionosphere_fdtd.mesh import (
    build_geodesic_mesh,
    build_geodesic_mesh_from_vertices,
)


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


def test_edge_diamonds_partition_the_sphere() -> None:
    mesh = build_geodesic_mesh(3)
    areas = mesh.edge_diamond_solid_angles()

    assert np.all(areas > 0.0)
    assert np.sum(areas) == pytest.approx(4.0 * np.pi, rel=1.0e-12)


def test_default_orientation_places_pentagons_at_geographic_poles() -> None:
    native = build_geodesic_mesh(2, orientation="native")
    polar = build_geodesic_mesh(2)

    pentagons = polar.vertices[polar.vertex_degree == 5]
    assert np.max(pentagons[:, 2]) == pytest.approx(1.0)
    assert np.min(pentagons[:, 2]) == pytest.approx(-1.0)
    native_north = int(np.argmax(native.vertices[:, 2]))
    native_south = int(np.argmin(native.vertices[:, 2]))
    assert native.vertex_degree[native_north] == 6
    assert native.vertex_degree[native_south] == 6
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


def test_edge_optimizer_improves_mesh_quality_and_fixes_pentagons() -> None:
    base = build_geodesic_mesh(3)
    optimized = build_geodesic_mesh(3, optimization_steps=1)

    np.testing.assert_allclose(
        optimized.vertices[base.vertex_degree == 5],
        base.vertices[base.vertex_degree == 5],
        rtol=0.0,
        atol=0.0,
    )
    assert np.std(optimized.primal_edge_angles) < np.std(base.primal_edge_angles)
    assert np.std(optimized.face_solid_angles) < np.std(base.face_solid_angles)
    assert np.std(optimized.dual_cell_solid_angles) < np.std(
        base.dual_cell_solid_angles
    )

    base_area_jump = np.abs(
        base.dual_cell_solid_angles[base.edges[:, 0]]
        - base.dual_cell_solid_angles[base.edges[:, 1]]
    )
    optimized_area_jump = np.abs(
        optimized.dual_cell_solid_angles[optimized.edges[:, 0]]
        - optimized.dual_cell_solid_angles[optimized.edges[:, 1]]
    )
    assert np.sqrt(np.mean(optimized_area_jump**2)) < np.sqrt(
        np.mean(base_area_jump**2)
    )
    assert np.max(optimized_area_jump) < np.max(base_area_jump)


def test_mesh_rejects_negative_optimization_steps() -> None:
    with pytest.raises(ValueError, match="optimization_steps"):
        build_geodesic_mesh(0, optimization_steps=-1)


def test_mesh_accepts_external_unit_sphere_vertices() -> None:
    base = build_geodesic_mesh(2)
    serialized = np.round(base.vertices, decimals=10)
    rebuilt = build_geodesic_mesh_from_vertices(2, serialized)

    np.testing.assert_array_equal(rebuilt.faces, base.faces)
    np.testing.assert_array_equal(rebuilt.edges, base.edges)
    np.testing.assert_allclose(np.linalg.norm(rebuilt.vertices, axis=1), 1.0)
    assert np.isclose(rebuilt.face_solid_angles.sum(), 4.0 * np.pi)
    assert np.isclose(rebuilt.dual_cell_solid_angles.sum(), 4.0 * np.pi)


def test_mesh_rejects_invalid_external_vertices() -> None:
    with pytest.raises(ValueError, match="shape"):
        build_geodesic_mesh_from_vertices(1, np.ones((4, 3)))
    with pytest.raises(ValueError, match="unit sphere"):
        build_geodesic_mesh_from_vertices(0, np.ones((12, 3)))


def test_mesh_rejects_external_vertices_with_invalid_circumcentric_dual() -> None:
    base = build_geodesic_mesh(1)
    distorted = base.vertices.copy()
    distorted[12] = distorted[12] + 0.6 * (distorted[0] - distorted[12])
    distorted[12] /= np.linalg.norm(distorted[12])

    with pytest.raises(ValueError, match="well-centered"):
        build_geodesic_mesh_from_vertices(1, distorted)
