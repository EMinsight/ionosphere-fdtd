"""Run full-field A2 and A4 analytic cavity convergence measurements."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from ionosphere_fdtd.constants import C_0, EARTH_RADIUS_M
from ionosphere_fdtd.solver import GeodesicFDTD, SimulationConfig

from .cavity import VacuumMaterial, build_electric_mode, initialize_electric_standing_mode, measure_mode


@dataclass(frozen=True, slots=True)
class ConvergenceRow:
    case: str
    polarization: str
    subdivision: int
    radial_cells: int
    analytic_frequency_hz: float
    measured_frequency_hz: float
    relative_frequency_error: float
    maximum_leakage: float
    time_step_s: float


def run_full_field_suite() -> tuple[ConvergenceRow, ...]:
    rows = []
    for subdivision in (1, 2, 3, 4):
        rows.append(_run("A2", "TM", subdivision, 8, 0, 2_000))
    for polarization, radial_index in (("TE", 0), ("TM", 1)):
        for radial_cells in (8, 16, 32):
            rows.append(_run("A4", polarization, 2, radial_cells, radial_index, 400))
    return tuple(rows)


def _run(case, polarization, subdivision, radial_cells, radial_index, steps):
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
    mode = build_electric_mode(
        simulation, 1, polarization=polarization, radial_index=radial_index
    )
    initialize_electric_standing_mode(simulation, mode)
    result = measure_mode(simulation, mode, steps)
    analytic = mode.wavenumber_rad_per_m * C_0 / (2.0 * np.pi)
    return ConvergenceRow(
        case, polarization, subdivision, radial_cells, analytic,
        result.frequency_hz, result.relative_frequency_error,
        result.maximum_leakage, simulation.time_step_s,
    )


def observed_order(errors: np.ndarray) -> float:
    values = np.abs(np.asarray(errors, dtype=np.float64))
    return float(np.mean(np.log2(values[:-1] / values[1:])))
