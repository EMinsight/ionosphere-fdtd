"""Local DEC-symbol diagnostics for horizontal numerical anisotropy."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from ionosphere_fdtd.constants import C_0, EARTH_RADIUS_M
from ionosphere_fdtd.mesh import GeodesicMesh, build_geodesic_mesh

FloatArray = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class DirectionalDispersion:
    """Per-vertex extrema of the local finite-volume wave symbol."""

    subdivision: int
    frequency_hz: float
    median_cells_per_wavelength: float
    headings_deg: FloatArray
    phase_velocity_ratio_min: FloatArray
    phase_velocity_ratio_max: FloatArray
    phase_velocity_ratio_mean: FloatArray
    group_velocity_ratio_mean: FloatArray
    pentagon_distance_rad: FloatArray
    vertices: FloatArray

    @property
    def phase_anisotropy(self) -> FloatArray:
        return (
            self.phase_velocity_ratio_max - self.phase_velocity_ratio_min
        ) / self.phase_velocity_ratio_mean

    @property
    def phase_absolute_error(self) -> FloatArray:
        return np.abs(self.phase_velocity_ratio_mean - 1.0)


@dataclass(frozen=True, slots=True)
class MaterialSupportConvergence:
    """Point-versus-area-support disagreement for a smooth material map."""

    subdivision: int
    characteristic_edge_angle: float
    radial_rms_difference: float
    tangential_rms_difference: float


def directional_dispersion(
    subdivision: int,
    *,
    frequency_hz: float = 20.0,
    radius_m: float = EARTH_RADIUS_M,
    headings: int = 12,
) -> DirectionalDispersion:
    """Evaluate local phase/group velocity over headings at every dual cell."""

    if frequency_hz <= 0.0 or radius_m <= 0.0 or headings < 3:
        raise ValueError("dispersion sampling requires positive wave controls")
    mesh = build_geodesic_mesh(subdivision)
    neighbors, weights, edge_angles = _vertex_stencils(mesh)
    center = mesh.vertices
    valid = neighbors >= 0
    neighbor_points = center[np.maximum(neighbors, 0)]
    cosine = np.sum(neighbor_points * center[:, None, :], axis=2)
    angle = np.arccos(np.clip(cosine, -1.0, 1.0))
    tangent = neighbor_points - cosine[:, :, None] * center[:, None, :]
    tangent_norm = np.linalg.norm(tangent, axis=2)
    tangent /= np.where(valid, tangent_norm, 1.0)[:, :, None]
    log_vectors = tangent * angle[:, :, None]
    mean_edge = np.sum(edge_angles, axis=1) / np.sum(valid, axis=1)
    wavenumber = np.full(
        mesh.n_vertices, 2.0 * np.pi * frequency_hz * radius_m / C_0
    )
    cells_per_wavelength = 2.0 * np.pi / (wavenumber * mean_edge)
    east, north = _tangent_bases(center)
    headings_deg = np.linspace(0.0, 360.0, headings, endpoint=False)
    phase = np.empty((headings, mesh.n_vertices), dtype=np.float64)
    group = np.empty_like(phase)
    for index, heading_deg in enumerate(headings_deg):
        heading = np.deg2rad(heading_deg)
        direction = np.cos(heading) * north + np.sin(heading) * east
        projected = np.sum(log_vectors * direction[:, None, :], axis=2)
        phase[index] = _phase_ratio(weights, projected, wavenumber)
        delta = 1.0e-3
        omega_plus = _angular_frequency(
            weights, projected, wavenumber * (1.0 + delta)
        )
        omega_minus = _angular_frequency(
            weights, projected, wavenumber * (1.0 - delta)
        )
        group[index] = (omega_plus - omega_minus) / (
            2.0 * delta * wavenumber
        )
    pentagons = center[mesh.vertex_degree == 5]
    pentagon_distance = np.min(
        np.arccos(np.clip(center @ pentagons.T, -1.0, 1.0)), axis=1
    )
    return DirectionalDispersion(
        subdivision=subdivision,
        frequency_hz=frequency_hz,
        median_cells_per_wavelength=float(np.median(cells_per_wavelength)),
        headings_deg=headings_deg,
        phase_velocity_ratio_min=np.min(phase, axis=0),
        phase_velocity_ratio_max=np.max(phase, axis=0),
        phase_velocity_ratio_mean=np.mean(phase, axis=0),
        group_velocity_ratio_mean=np.mean(group, axis=0),
        pentagon_distance_rad=pentagon_distance,
        vertices=center,
    )


def material_support_convergence(
    subdivision: int,
) -> MaterialSupportConvergence:
    """Measure point/area-support disagreement for a smooth conductivity map."""

    mesh = build_geodesic_mesh(subdivision)

    def field(directions: FloatArray) -> FloatArray:
        return 2.0 + directions[:, 0] + 0.5 * directions[:, 1] ** 2

    vertices = mesh.edges.ravel()
    edges = np.repeat(np.arange(mesh.n_edges, dtype=np.int64), 2)
    support, areas = mesh.dual_cell_wedge_quadrature(vertices, edges)
    radial_average = np.bincount(
        vertices,
        weights=areas * field(support),
        minlength=mesh.n_vertices,
    ) / mesh.dual_cell_solid_angles
    radial_point = field(mesh.vertices)
    radial_rms = _relative_rms(radial_point, radial_average)

    midpoint = mesh.edge_midpoints()
    endpoints = mesh.vertices[mesh.edges]
    left = mesh.face_centers[mesh.edge_left_faces]
    right = mesh.face_centers[mesh.edge_right_faces]
    support_points = (
        midpoint + endpoints[:, 0] + left,
        midpoint + left + endpoints[:, 1],
        midpoint + endpoints[:, 1] + right,
        midpoint + right + endpoints[:, 0],
    )
    areas = mesh.edge_diamond_quadrant_solid_angles()
    weights = areas / np.sum(areas, axis=1, keepdims=True)
    tangential_average = np.zeros(mesh.n_edges, dtype=np.float64)
    for quadrant, points in enumerate(support_points):
        points /= np.linalg.norm(points, axis=1, keepdims=True)
        tangential_average += weights[:, quadrant] * field(points)
    tangential_rms = _relative_rms(field(midpoint), tangential_average)
    return MaterialSupportConvergence(
        subdivision=subdivision,
        characteristic_edge_angle=float(np.mean(mesh.primal_edge_angles)),
        radial_rms_difference=radial_rms,
        tangential_rms_difference=tangential_rms,
    )


def _vertex_stencils(
    mesh: GeodesicMesh,
) -> tuple[NDArray[np.int64], FloatArray, FloatArray]:
    degree = int(np.max(mesh.vertex_degree))
    neighbors = np.full((mesh.n_vertices, degree), -1, dtype=np.int64)
    weights = np.zeros((mesh.n_vertices, degree), dtype=np.float64)
    edge_angles = np.zeros_like(weights)
    slots = np.zeros(mesh.n_vertices, dtype=np.int64)
    edge_weight = mesh.dual_edge_angles / mesh.primal_edge_angles
    for edge, (tail, head) in enumerate(mesh.edges):
        for vertex, neighbor in ((tail, head), (head, tail)):
            slot = slots[vertex]
            neighbors[vertex, slot] = neighbor
            weights[vertex, slot] = (
                edge_weight[edge] / mesh.dual_cell_solid_angles[vertex]
            )
            edge_angles[vertex, slot] = mesh.primal_edge_angles[edge]
            slots[vertex] += 1
    return neighbors, weights, edge_angles


def _tangent_bases(points: FloatArray) -> tuple[FloatArray, FloatArray]:
    reference = np.broadcast_to((0.0, 0.0, 1.0), points.shape).copy()
    polar = np.abs(points[:, 2]) > 0.9
    reference[polar] = (1.0, 0.0, 0.0)
    east = np.cross(reference, points)
    east /= np.linalg.norm(east, axis=1, keepdims=True)
    north = np.cross(points, east)
    return east, north


def _angular_frequency(
    weights: FloatArray, projected: FloatArray, wavenumber: FloatArray
) -> FloatArray:
    symbol = np.sum(
        weights * (1.0 - np.cos(wavenumber[:, None] * projected)), axis=1
    )
    return np.sqrt(np.maximum(symbol, 0.0))


def _phase_ratio(
    weights: FloatArray, projected: FloatArray, wavenumber: FloatArray
) -> FloatArray:
    return _angular_frequency(weights, projected, wavenumber) / wavenumber


def _relative_rms(reference: FloatArray, values: FloatArray) -> float:
    return float(
        np.sqrt(np.mean((values - reference) ** 2))
        / np.sqrt(np.mean(reference**2))
    )
