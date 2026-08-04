"""Mesh-quality and Laplace-consistency diagnostics on the unit sphere."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .mesh import FloatArray, GeodesicMesh


@dataclass(frozen=True, slots=True)
class MeshQualityMetrics:
    """Dimensionless geometry and discrete-Laplace quality measures."""

    primal_edge_cv: float
    primal_face_area_cv: float
    dual_cell_area_cv: float
    adjacent_dual_area_rms_relative: float
    adjacent_dual_area_max_relative: float
    laplace_l1_max_relative_l2: float
    laplace_l2_max_relative_l2: float


def scalar_laplacian(mesh: GeodesicMesh, values: FloatArray) -> FloatArray:
    r"""Apply the circumcentric finite-volume Laplacian on the unit sphere.

    For each primal edge, the scalar difference is weighted by the ratio of
    dual-edge to primal-edge length. The resulting outward flux is divided by
    the corresponding dual-cell solid angle. This is the scalar spatial
    operator induced by the same primal/dual metric terms used by the FDTD
    curls.
    """

    field = np.asarray(values, dtype=np.float64)
    if field.shape != (mesh.n_vertices,):
        raise ValueError(f"values must have shape ({mesh.n_vertices},)")
    differences = field[mesh.edges[:, 1]] - field[mesh.edges[:, 0]]
    edge_flux = (
        mesh.dual_edge_angles / mesh.primal_edge_angles * differences
    )
    return mesh.dual_cell_circulation(edge_flux) / mesh.dual_cell_solid_angles


def laplace_eigenmode_errors(mesh: GeodesicMesh) -> dict[str, float]:
    """Return area-weighted relative errors for real l=1 and l=2 modes."""

    x, y, z = mesh.vertices.T
    modes = {
        "l1_x": (x, 2.0),
        "l1_y": (y, 2.0),
        "l1_z": (z, 2.0),
        "l2_xy": (x * y, 6.0),
        "l2_xz": (x * z, 6.0),
        "l2_yz": (y * z, 6.0),
        "l2_x2_minus_y2": (x * x - y * y, 6.0),
        "l2_3z2_minus_1": (3.0 * z * z - 1.0, 6.0),
    }
    areas = mesh.dual_cell_solid_angles
    errors: dict[str, float] = {}
    for label, (field, eigenvalue) in modes.items():
        exact = -eigenvalue * field
        residual = scalar_laplacian(mesh, field) - exact
        numerator = np.sum(areas * residual * residual)
        denominator = np.sum(areas * exact * exact)
        errors[label] = float(np.sqrt(numerator / denominator))
    return errors


def mesh_quality_metrics(mesh: GeodesicMesh) -> MeshQualityMetrics:
    """Summarize grid smoothness and low-order Laplace consistency."""

    dual_areas = mesh.dual_cell_solid_angles
    mean_dual_area = float(np.mean(dual_areas))
    adjacent_jump = np.abs(
        dual_areas[mesh.edges[:, 0]] - dual_areas[mesh.edges[:, 1]]
    )
    laplace_errors = laplace_eigenmode_errors(mesh)
    return MeshQualityMetrics(
        primal_edge_cv=float(
            np.std(mesh.primal_edge_angles) / np.mean(mesh.primal_edge_angles)
        ),
        primal_face_area_cv=float(
            np.std(mesh.face_solid_angles) / np.mean(mesh.face_solid_angles)
        ),
        dual_cell_area_cv=float(np.std(dual_areas) / mean_dual_area),
        adjacent_dual_area_rms_relative=float(
            np.sqrt(np.mean(adjacent_jump * adjacent_jump)) / mean_dual_area
        ),
        adjacent_dual_area_max_relative=float(
            np.max(adjacent_jump) / mean_dual_area
        ),
        laplace_l1_max_relative_l2=max(
            value for label, value in laplace_errors.items() if label.startswith("l1_")
        ),
        laplace_l2_max_relative_l2=max(
            value for label, value in laplace_errors.items() if label.startswith("l2_")
        ),
    )
