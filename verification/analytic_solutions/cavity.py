"""Vector-spherical-harmonic initialization and projection for a PEC shell."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from numpy.polynomial.legendre import Legendre
from numpy.typing import NDArray
from scipy.special import spherical_jn, spherical_yn

from ionosphere_fdtd.constants import C_0, EPSILON_0
from ionosphere_fdtd.solver import GeodesicFDTD

from .model import pec_spherical_shell_wavenumbers


@dataclass(frozen=True, slots=True)
class ElectricMode:
    degree: int
    polarization: str
    wavenumber_rad_per_m: float
    er_v_m: NDArray[np.float64]
    et_v_m: NDArray[np.float64]
    er_weight: NDArray[np.float64]
    et_weight: NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class Projection:
    amplitude: float
    relative_leakage: float


@dataclass(frozen=True, slots=True)
class ModeMeasurement:
    frequency_hz: float
    relative_frequency_error: float
    maximum_leakage: float
    amplitude: NDArray[np.float64]


class VacuumMaterial:
    def sample(self, directions, altitudes_m, earth_radius_m):
        del earth_radius_m
        shape = (len(directions), len(altitudes_m))
        return np.zeros(shape), np.ones(shape)


def build_electric_mode(
    simulation: GeodesicFDTD,
    degree: int,
    *,
    polarization: str,
    radial_index: int = 0,
) -> ElectricMode:
    """Sample a real, axisymmetric PEC-cavity standing mode on E DOFs."""

    if simulation.config.geometry_mode != "full-spherical":
        raise ValueError("PEC cavity modes require full-spherical geometry")
    roots = pec_spherical_shell_wavenumbers(
        degree,
        float(simulation.radii_m[0]),
        float(simulation.radii_m[-1]),
        polarization=polarization,
        count=radial_index + 1,
    )
    k = float(roots[radial_index])
    vertex_y, _ = _zonal_harmonic(simulation.mesh.vertices, degree)
    _, edge_gradient = _zonal_harmonic(simulation.mesh.edge_midpoints(), degree)
    edge_tangent = _edge_tangents(simulation)
    if polarization == "TE":
        angular_et = np.einsum(
            "ij,ij->i",
            np.cross(simulation.mesh.edge_midpoints(), edge_gradient),
            edge_tangent,
        )
        er = np.zeros((simulation.mesh.n_vertices, len(simulation.radii_m)))
        radial_et = _radial_combination(
            degree,
            k,
            simulation.radial_midpoints_m,
            float(simulation.radii_m[0]),
            polarization,
        )[0]
        et = angular_et[:, None] * radial_et[None, :]
    elif polarization == "TM":
        angular_et = np.einsum("ij,ij->i", edge_gradient, edge_tangent)
        radial_er, _ = _radial_combination(
            degree, k, simulation.radii_m, float(simulation.radii_m[0]), polarization
        )
        _, radial_et = _radial_combination(
            degree,
            k,
            simulation.radial_midpoints_m,
            float(simulation.radii_m[0]),
            polarization,
        )
        er = vertex_y[:, None] * radial_er[None, :]
        et = angular_et[:, None] * radial_et[None, :]
    else:
        raise ValueError("polarization must be TE or TM")
    scale = max(float(np.max(np.abs(er))), float(np.max(np.abs(et))))
    if not np.isfinite(scale) or scale == 0.0:
        raise RuntimeError("sampled cavity mode is degenerate")
    er = er / scale
    et = et / scale
    er_weight = (
        EPSILON_0
        * simulation.mesh.dual_cell_solid_angles[:, None]
        * simulation.radii_m[None, :] ** 2
        * simulation.radial_node_control_lengths_m[None, :]
    )
    et_weight = (
        EPSILON_0
        * simulation.mesh.edge_diamond_solid_angles()[:, None]
        * simulation.radial_midpoints_m[None, :] ** 2
        * simulation.radial_steps_m[None, :]
    )
    return ElectricMode(
        degree, polarization, k, er, et, er_weight, et_weight
    )


def initialize_electric_standing_mode(
    simulation: GeodesicFDTD, mode: ElectricMode
) -> None:
    if simulation.er.shape != mode.er_v_m.shape or simulation.et.shape != mode.et_v_m.shape:
        raise ValueError("mode and simulation shapes do not match")
    simulation.er[:] = mode.er_v_m
    simulation.et[:] = mode.et_v_m
    simulation.hr[:] = 0.0
    simulation.ht[:] = 0.0


def project_electric_mode(
    simulation: GeodesicFDTD, mode: ElectricMode
) -> Projection:
    numerator = np.sum(mode.er_weight * simulation.er * mode.er_v_m)
    numerator += np.sum(mode.et_weight * simulation.et * mode.et_v_m)
    denominator = np.sum(mode.er_weight * mode.er_v_m**2)
    denominator += np.sum(mode.et_weight * mode.et_v_m**2)
    amplitude = float(numerator / denominator)
    residual = np.sum(mode.er_weight * (simulation.er - amplitude * mode.er_v_m) ** 2)
    residual += np.sum(mode.et_weight * (simulation.et - amplitude * mode.et_v_m) ** 2)
    field_norm = np.sum(mode.er_weight * simulation.er**2)
    field_norm += np.sum(mode.et_weight * simulation.et**2)
    leakage = float(np.sqrt(residual / field_norm)) if field_norm > 0.0 else 0.0
    return Projection(amplitude, leakage)


def measure_mode(
    simulation: GeodesicFDTD, mode: ElectricMode, steps: int
) -> ModeMeasurement:
    """Advance a standing mode and fit its exact second-order recurrence."""

    if steps < 3:
        raise ValueError("at least three steps are required")
    amplitude = np.empty(steps + 1)
    maximum_leakage = 0.0
    for index in range(steps + 1):
        projection = project_electric_mode(simulation, mode)
        amplitude[index] = projection.amplitude
        if abs(projection.amplitude) >= 0.25:
            maximum_leakage = max(maximum_leakage, projection.relative_leakage)
        if index < steps:
            simulation.step()
    center = amplitude[1:-1]
    cosine = float(np.dot(center, amplitude[2:] + amplitude[:-2]) / (2.0 * np.dot(center, center)))
    cosine = float(np.clip(cosine, -1.0, 1.0))
    frequency = np.arccos(cosine) / (2.0 * np.pi * simulation.time_step_s)
    analytic = mode.wavenumber_rad_per_m * C_0 / (2.0 * np.pi)
    return ModeMeasurement(
        float(frequency), float(frequency / analytic - 1.0),
        maximum_leakage, amplitude,
    )


def _zonal_harmonic(
    directions: NDArray[np.float64], degree: int
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    points = np.asarray(directions)
    z = np.clip(points[:, 2], -1.0, 1.0)
    polynomial = Legendre.basis(degree)
    values = polynomial(z)
    derivative_theta = -np.sqrt(np.maximum(0.0, 1.0 - z**2)) * polynomial.deriv()(z)
    longitude = np.arctan2(points[:, 1], points[:, 0])
    cos_theta = z
    sin_theta = np.sqrt(np.maximum(0.0, 1.0 - z**2))
    e_theta = np.column_stack(
        (cos_theta * np.cos(longitude), cos_theta * np.sin(longitude), -sin_theta)
    )
    return values, derivative_theta[:, None] * e_theta


def _edge_tangents(simulation: GeodesicFDTD) -> NDArray[np.float64]:
    endpoints = simulation.mesh.vertices[simulation.mesh.edges]
    tangent = endpoints[:, 1] - endpoints[:, 0]
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    return tangent


def _radial_combination(degree, k, radii, inner_radius, polarization):
    x = k * np.asarray(radii)
    xa = k * inner_radius

    def value(kind, argument):
        function = spherical_jn if kind == "j" else spherical_yn
        return function(degree, argument)

    def derivative_combo(kind, argument):
        function = spherical_jn if kind == "j" else spherical_yn
        return function(degree, argument) + argument * function(
            degree, argument, derivative=True
        )

    if polarization == "TE":
        radial = value("j", x) * value("y", xa) - value("y", x) * value("j", xa)
        return radial, radial
    coefficient_j = derivative_combo("y", xa)
    coefficient_y = derivative_combo("j", xa)
    radial = value("j", x) * coefficient_j - value("y", x) * coefficient_y
    derivative = derivative_combo("j", x) * coefficient_j - derivative_combo("y", x) * coefficient_y
    return degree * (degree + 1.0) * radial / x, derivative / x
