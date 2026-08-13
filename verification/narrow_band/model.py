"""Online lock-in sampling and spatial propagation-constant fitting."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
import numpy as np
from numpy.typing import NDArray

from ionosphere_fdtd.constants import C_0, EARTH_RADIUS_M
from ionosphere_fdtd.solver import GeodesicFDTD
from ionosphere_fdtd.sources import geographic_distribution
from verification.directional_dispersion.model import _latitude_longitude, destination_direction
from verification.simpson_taflove_2004.model import bannister_phase_velocity_fraction_c


@dataclass(frozen=True, slots=True)
class NarrowBandFit:
    frequency_hz: float
    azimuth_deg: NDArray[np.float64]
    receiver_arc_deg: NDArray[np.float64]
    amplitudes: NDArray[np.complex128]
    attenuation_db_per_mm: NDArray[np.float64]
    beta_rad_per_m: NDArray[np.float64]
    phase_velocity_fraction_c: NDArray[np.float64]
    complex_residual_rms: NDArray[np.float64]


def receiver_distributions(
    simulation: GeodesicFDTD,
    azimuths_deg: Sequence[float],
    receiver_arcs_deg: Sequence[float],
) -> tuple[NDArray[np.int64], NDArray[np.int64], NDArray[np.float64]]:
    source = simulation.source
    if source is None:
        raise ValueError("simulation requires a source")
    distributions = []
    for azimuth in azimuths_deg:
        for arc in receiver_arcs_deg:
            latitude, longitude = _latitude_longitude(
                destination_direction(source.direction(), float(azimuth), float(arc))
            )
            distributions.append(geographic_distribution(simulation, latitude, longitude, 0.0))
    return (
        np.stack([value[0] for value in distributions]),
        np.asarray([value[1] for value in distributions], dtype=np.int64),
        np.stack([value[2] for value in distributions]),
    )


def record_lockin_amplitudes(
    simulation: GeodesicFDTD,
    frequency_hz: float,
    vertices: NDArray[np.int64],
    layers: NDArray[np.int64],
    weights: NDArray[np.float64],
    steps: int,
    *,
    accumulation_start_step: int = 0,
    synchronize_every: int = 1024,
) -> NDArray[np.complex128]:
    """Accumulate selected receiver DFT values without storing time histories."""

    if simulation.steps != 0 or simulation.source is None:
        raise ValueError("lock-in recording requires a fresh simulation with a source")
    if frequency_hz <= 0.0 or steps < 1 or not 0 <= accumulation_start_step < steps:
        raise ValueError("frequency and steps must be positive")
    backend_vertices = simulation.backend.index_array(vertices)
    backend_layers = simulation.backend.index_array(layers)
    backend_weights = simulation.backend.asarray(weights)
    real = simulation.backend.zeros((len(layers),))
    imaginary = simulation.backend.zeros((len(layers),))
    currents = simulation._source_currents(steps)
    omega_dt = 2.0 * np.pi * frequency_hz * simulation.time_step_s
    for offset in range(steps):
        simulation._field_step(currents[offset])
        simulation.steps += 1
        simulation.time_s = simulation.steps * simulation.time_step_s
        if simulation.steps > accumulation_start_step:
            selected = simulation.er[backend_vertices, backend_layers[:, None]]
            sample = (selected * backend_weights).sum(axis=1)
            phase = omega_dt * simulation.steps
            real += sample * np.cos(phase)
            imaginary -= sample * np.sin(phase)
        if (offset + 1) % synchronize_every == 0:
            simulation.backend.synchronize()
    simulation.backend.synchronize()
    return simulation.to_numpy(real).astype(np.float64) + 1j * simulation.to_numpy(imaginary).astype(np.float64)


def fit_amplitudes(
    frequency_hz: float,
    azimuths_deg: Sequence[float],
    receiver_arcs_deg: Sequence[float],
    amplitudes: NDArray[np.complex128],
) -> NarrowBandFit:
    azimuths = np.asarray(azimuths_deg, dtype=np.float64)
    arcs = np.asarray(receiver_arcs_deg, dtype=np.float64)
    values = np.asarray(amplitudes, dtype=np.complex128).reshape(len(azimuths), len(arcs))
    distance = np.deg2rad(arcs) * EARTH_RADIUS_M
    corrected = values * np.sqrt(np.sin(np.deg2rad(arcs)))[None, :]
    design = np.column_stack((np.ones(len(arcs)), distance))
    reference_beta = 2.0 * np.pi * frequency_hz / (
        bannister_phase_velocity_fraction_c(np.asarray((frequency_hz,)))[0] * C_0
    )
    attenuation = np.empty(len(azimuths)); beta = np.empty(len(azimuths)); residual = np.empty(len(azimuths))
    for index, row in enumerate(corrected):
        log_amplitude = np.log(np.maximum(np.abs(row), np.finfo(float).tiny))
        phase = np.unwrap(np.angle(row * np.exp(1j * distance * reference_beta))) - distance * reference_beta
        amp_coef = np.linalg.lstsq(design, log_amplitude, rcond=None)[0]
        phase_coef = np.linalg.lstsq(design, phase, rcond=None)[0]
        attenuation[index] = -amp_coef[1] * 20.0 / np.log(10.0) * 1.0e6
        beta[index] = -phase_coef[1]
        prediction = np.exp(design @ amp_coef + 1j * (design @ phase_coef))
        residual[index] = np.sqrt(np.mean(np.abs(row / prediction - 1.0) ** 2))
    if np.any(beta <= 0.0):
        raise ValueError("fitted phase constants must be positive")
    velocity = 2.0 * np.pi * frequency_hz / beta / C_0
    return NarrowBandFit(frequency_hz, azimuths, arcs, values, attenuation, beta, velocity, residual)
