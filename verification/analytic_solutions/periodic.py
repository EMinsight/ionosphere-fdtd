"""Periodic one-dimensional Yee benchmark for a homogeneous lossy medium."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from ionosphere_fdtd.constants import C_0, EPSILON_0, MU_0


@dataclass(frozen=True, slots=True)
class PeriodicModeMeasurement:
    cells: int
    time_step_s: float
    analytic_decay_per_s: float
    measured_decay_per_s: float
    relative_decay_error: float
    analytic_frequency_hz: float
    measured_frequency_hz: float
    relative_frequency_error: float


def measure_periodic_mode(
    cells: int,
    *,
    length_m: float = 10_000_000.0,
    mode_number: int = 4,
    conductivity_s_m: float = 1.0e-8,
    relative_permittivity: float = 2.0,
    courant_factor: float = 0.5,
    steps: int = 3_000,
) -> PeriodicModeMeasurement:
    """Measure one underdamped Fourier mode of the lossy periodic Yee scheme."""

    if cells < 8 or not 0 < mode_number < cells // 2:
        raise ValueError("periodic grid does not resolve the requested mode")
    epsilon = EPSILON_0 * relative_permittivity
    speed = C_0 / np.sqrt(relative_permittivity)
    dx = length_m / cells
    dt = courant_factor * dx / speed
    loss = conductivity_s_m * dt / (2.0 * epsilon)
    ca = (1.0 - loss) / (1.0 + loss)
    cb = dt / (epsilon * (1.0 + loss))
    x = np.arange(cells) * dx
    basis = np.cos(2.0 * np.pi * mode_number * x / length_m)
    electric = basis.copy()
    magnetic = np.zeros(cells)
    amplitude = np.empty(steps)
    for index in range(steps):
        amplitude[index] = 2.0 * np.dot(electric, basis) / cells
        magnetic -= dt / (MU_0 * dx) * (np.roll(electric, -1) - electric)
        electric = ca * electric - cb / dx * (magnetic - np.roll(magnetic, 1))
    design = np.column_stack((amplitude[1:-1], amplitude[:-2]))
    coefficient = np.linalg.lstsq(design, amplitude[2:], rcond=None)[0]
    roots = np.roots((1.0, -coefficient[0], -coefficient[1]))
    root = roots[int(np.argmax(roots.imag))]
    measured_decay = -np.log(abs(root)) / dt
    measured_frequency = np.angle(root) / (2.0 * np.pi * dt)
    analytic_decay = conductivity_s_m / (2.0 * epsilon)
    wavenumber = 2.0 * np.pi * mode_number / length_m
    angular_frequency = np.sqrt((speed * wavenumber) ** 2 - analytic_decay**2)
    analytic_frequency = angular_frequency / (2.0 * np.pi)
    return PeriodicModeMeasurement(
        cells, dt, analytic_decay, float(measured_decay),
        float(measured_decay / analytic_decay - 1.0),
        float(analytic_frequency), float(measured_frequency),
        float(measured_frequency / analytic_frequency - 1.0),
    )


def run_periodic_convergence() -> tuple[PeriodicModeMeasurement, ...]:
    return tuple(measure_periodic_mode(cells) for cells in (64, 128, 256, 512))
