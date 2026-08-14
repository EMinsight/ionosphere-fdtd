"""Krylov comparison of analytic and discrete A4 electric eigenmodes."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from numpy.typing import NDArray

from ionosphere_fdtd.constants import C_0, EARTH_RADIUS_M
from ionosphere_fdtd.solver import GeodesicFDTD, SimulationConfig

from .cavity import (
    ElectricMode,
    VacuumMaterial,
    build_electric_mode,
    initialize_electric_standing_mode,
    measure_mode,
)


@dataclass(frozen=True, slots=True)
class OperatorComparison:
    subdivision: int
    radial_cells: int
    analytic_relative_residual: float
    ritz_relative_residual: float
    analytic_ritz_overlap: float
    analytic_frequency_hz: float
    ritz_frequency_hz: float
    ritz_projector_leakage_one_period: float


def compare_te_operator_modes(
    subdivision: int,
    radial_cells: int,
    *,
    krylov_dimension: int = 12,
) -> OperatorComparison:
    simulation = GeodesicFDTD(
        SimulationConfig(
            subdivision=subdivision,
            radial_cells=radial_cells,
            minimum_altitude_m=0.0,
            maximum_altitude_m=100_000.0,
            earth_radius_m=EARTH_RADIUS_M,
            courant_factor=0.4,
            geometry_mode="full-spherical",
        ),
        material=VacuumMaterial(),
        dtype="float64",
    )
    mode = build_electric_mode(simulation, 1, polarization="TE", radial_index=0)
    weight = np.concatenate((mode.er_weight.ravel(), mode.et_weight.ravel()))
    analytic = _pack(mode.er_v_m, mode.et_v_m)
    analytic /= _weighted_norm(analytic, weight)

    def operator(vector: NDArray[np.float64]) -> NDArray[np.float64]:
        er, et = _unpack(vector, mode)
        trial = replace(mode, er_v_m=er, et_v_m=et)
        initialize_electric_standing_mode(simulation, trial)
        simulation.step()
        advanced = _pack(
            simulation.to_numpy(simulation.er),
            simulation.to_numpy(simulation.et),
        )
        simulation.steps = 0
        simulation.time_s = 0.0
        return -(advanced - vector) / (C_0 * simulation.time_step_s) ** 2

    analytic_image = operator(analytic)
    analytic_value = _weighted_inner(analytic, analytic_image, weight)
    analytic_residual = _relative_residual(
        analytic_image, analytic, analytic_value, weight
    )
    basis = _krylov_basis(operator, analytic, weight, krylov_dimension)
    images = np.column_stack([operator(basis[:, index]) for index in range(basis.shape[1])])
    projected = basis.T @ (weight[:, None] * images)
    projected = 0.5 * (projected + projected.T)
    eigenvalues, eigenvectors = np.linalg.eigh(projected)
    selected = int(np.argmax(np.abs(eigenvectors[0])))
    ritz = basis @ eigenvectors[:, selected]
    ritz_image = operator(ritz)
    ritz_value = float(eigenvalues[selected])
    ritz_residual = _relative_residual(ritz_image, ritz, ritz_value, weight)
    overlap = abs(_weighted_inner(analytic, ritz, weight))
    ritz_er, ritz_et = _unpack(ritz, mode)
    ritz_mode = replace(mode, er_v_m=ritz_er, et_v_m=ritz_et)
    initialize_electric_standing_mode(simulation, ritz_mode)
    steps = int(np.ceil(1.0 / (float(C_0 * np.sqrt(max(ritz_value, 0.0)) / (2.0 * np.pi)) * simulation.time_step_s)))
    ritz_measurement = measure_mode(simulation, ritz_mode, steps)
    return OperatorComparison(
        subdivision=subdivision,
        radial_cells=radial_cells,
        analytic_relative_residual=analytic_residual,
        ritz_relative_residual=ritz_residual,
        analytic_ritz_overlap=overlap,
        analytic_frequency_hz=mode.wavenumber_rad_per_m * C_0 / (2.0 * np.pi),
        ritz_frequency_hz=float(
            C_0 * np.sqrt(max(ritz_value, 0.0)) / (2.0 * np.pi)
        ),
        ritz_projector_leakage_one_period=ritz_measurement.maximum_leakage,
    )


def run_te_operator_comparison() -> tuple[OperatorComparison, ...]:
    return tuple(
        compare_te_operator_modes(subdivision, radial_cells)
        for subdivision, radial_cells in ((1, 8), (2, 16), (3, 32), (4, 64))
    )


def _krylov_basis(operator, initial, weight, dimension):
    columns = [initial]
    for _ in range(1, dimension):
        candidate = operator(columns[-1])
        for _ in range(2):
            for column in columns:
                candidate -= _weighted_inner(column, candidate, weight) * column
        norm = _weighted_norm(candidate, weight)
        if norm < 1.0e-12 * _weighted_norm(operator(columns[-1]), weight):
            break
        columns.append(candidate / norm)
    return np.column_stack(columns)


def _pack(er, et):
    return np.concatenate((np.asarray(er).ravel(), np.asarray(et).ravel()))


def _unpack(vector, mode: ElectricMode):
    er_size = mode.er_v_m.size
    return vector[:er_size].reshape(mode.er_v_m.shape), vector[er_size:].reshape(mode.et_v_m.shape)


def _weighted_inner(left, right, weight):
    return float(np.dot(weight * left, right))


def _weighted_norm(vector, weight):
    return float(np.sqrt(max(_weighted_inner(vector, vector, weight), 0.0)))


def _relative_residual(image, vector, eigenvalue, weight):
    residual = image - eigenvalue * vector
    return _weighted_norm(residual, weight) / _weighted_norm(image, weight)
