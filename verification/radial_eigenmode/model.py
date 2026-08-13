"""Independent conservative TM eigenproblem for a stratified ionosphere."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from scipy.sparse import diags
from scipy.sparse.linalg import eigs

from ionosphere_fdtd.constants import C_0, EPSILON_0

FloatArray = NDArray[np.float64]
ComplexArray = NDArray[np.complex128]
REFERENCE_HEIGHT_M = 70_000.0
SCALE_HEIGHT_M = 1_000.0 / 0.3
IONOSPHERE_PREFACTOR_HZ = 2.5e5
TOP_ALTITUDE_M = 100_000.0
REFERENCE_ANALYSIS_SPACING_M = 100.0


@dataclass(frozen=True, slots=True)
class EigenmodeCurve:
    frequency_hz: FloatArray
    beta_rad_per_m: ComplexArray
    attenuation_db_per_mm: FloatArray
    phase_velocity_fraction_c: FloatArray
    eigen_residual: FloatArray
    analysis_spacing_m: float


@dataclass(frozen=True, slots=True)
class RadialBenchmark:
    continuous: EigenmodeCurve
    spacing_m: FloatArray
    discretized_beta_rad_per_m: ComplexArray
    discretized_attenuation_db_per_mm: FloatArray
    discretized_phase_velocity_fraction_c: FloatArray
    attenuation_error_db_per_mm: FloatArray
    phase_velocity_error_fraction_c: FloatArray
    eigen_residual: FloatArray


def conductivity_s_m(altitude_m: FloatArray) -> FloatArray:
    altitude = np.asarray(altitude_m, dtype=np.float64)
    return IONOSPHERE_PREFACTOR_HZ * EPSILON_0 * np.exp(
        (altitude - REFERENCE_HEIGHT_M) / SCALE_HEIGHT_M
    )


def discretized_conductivity_s_m(
    altitude_m: FloatArray, radial_spacing_m: float
) -> FloatArray:
    """Return cell-center samples held constant over each radial cell."""
    if not np.isfinite(radial_spacing_m) or radial_spacing_m <= 0.0:
        raise ValueError("radial spacing must be finite and positive")
    altitude = np.asarray(altitude_m, dtype=np.float64)
    cell = np.floor(np.clip(altitude, 0.0, TOP_ALTITUDE_M - 1e-9) / radial_spacing_m)
    return conductivity_s_m((cell + 0.5) * radial_spacing_m)


def solve_tm_mode(
    frequency_hz: float,
    *,
    radial_spacing_m: float | None = None,
    analysis_spacing_m: float = REFERENCE_ANALYSIS_SPACING_M,
) -> tuple[complex, float]:
    """Solve the fundamental TM mode as a complex generalized eigenproblem.

    The equation is

    ``d/dz[(1/epsilon_c) dH/dz] + k0^2 H = beta^2 H/epsilon_c``.

    Zero normal flux is imposed at sea level and 100 km, matching the closed
    radial extent of the 3-D control while avoiding any 3-D solver result.
    """
    if frequency_hz <= 0.0 or not np.isfinite(frequency_hz):
        raise ValueError("frequency must be finite and positive")
    if analysis_spacing_m <= 0.0 or TOP_ALTITUDE_M % analysis_spacing_m:
        raise ValueError("analysis spacing must be a positive divisor of 100 km")
    altitude = np.arange(0.0, TOP_ALTITUDE_M + analysis_spacing_m, analysis_spacing_m)
    omega = 2.0 * np.pi * frequency_hz
    k0 = omega / C_0
    sigma = (
        conductivity_s_m(altitude)
        if radial_spacing_m is None
        else discretized_conductivity_s_m(altitude, radial_spacing_m)
    )
    epsilon = 1.0 - 1j * sigma / (omega * EPSILON_0)
    inverse_epsilon = 1.0 / epsilon
    interface = (
        2.0 * inverse_epsilon[:-1] * inverse_epsilon[1:]
        / (inverse_epsilon[:-1] + inverse_epsilon[1:])
    )
    off_diagonal = interface / analysis_spacing_m**2
    diagonal = np.empty(len(altitude), dtype=np.complex128)
    diagonal[0] = -off_diagonal[0]
    diagonal[-1] = -off_diagonal[-1]
    diagonal[1:-1] = -(off_diagonal[:-1] + off_diagonal[1:])
    operator = diags(
        (off_diagonal, diagonal + k0**2, off_diagonal), (-1, 0, 1), format="csc"
    )
    weight = diags(inverse_epsilon, format="csc")
    # ``scipy.sparse.linalg.eigs(..., M=...)`` requires a Hermitian positive
    # definite mass matrix. The conductive complex weight is neither, so form
    # the exactly equivalent standard non-Hermitian operator B^-1 A.
    standard_operator = diags(epsilon, format="csc") @ operator
    eigenvalues, eigenvectors = eigs(
        standard_operator, k=3, sigma=(k0 / 0.85) ** 2, which="LM"
    )
    candidates = []
    for index, eigenvalue in enumerate(eigenvalues):
        beta = np.sqrt(eigenvalue)
        if beta.real < 0.0:
            beta = -beta
        velocity = omega / beta.real / C_0
        attenuation = -20.0 / np.log(10.0) * beta.imag * 1.0e6
        if 0.65 < velocity < 1.05 and 0.0 < attenuation < 100.0:
            candidates.append((abs(velocity - 0.85), index, beta))
    if not candidates:
        raise RuntimeError(f"no physical fundamental mode found at {frequency_hz:g} Hz")
    _, index, beta = min(candidates)
    vector = eigenvectors[:, index]
    residual = np.linalg.norm(operator @ vector - beta**2 * (weight @ vector)) / (
        np.linalg.norm(operator @ vector) + np.linalg.norm(beta**2 * (weight @ vector))
    )
    return complex(beta), float(residual)


def solve_curve(
    frequency_hz: FloatArray,
    *,
    radial_spacing_m: float | None = None,
    analysis_spacing_m: float = REFERENCE_ANALYSIS_SPACING_M,
) -> EigenmodeCurve:
    frequency = np.asarray(frequency_hz, dtype=np.float64)
    beta = np.empty(len(frequency), dtype=np.complex128)
    residual = np.empty(len(frequency))
    for index, value in enumerate(frequency):
        beta[index], residual[index] = solve_tm_mode(
            float(value), radial_spacing_m=radial_spacing_m,
            analysis_spacing_m=analysis_spacing_m,
        )
    attenuation = -20.0 / np.log(10.0) * beta.imag * 1.0e6
    velocity = 2.0 * np.pi * frequency / beta.real / C_0
    return EigenmodeCurve(
        frequency, beta, attenuation, velocity, residual, analysis_spacing_m
    )


def run_benchmark(
    frequency_hz: FloatArray,
    spacings_m: FloatArray = np.asarray((5_000.0, 2_500.0, 1_250.0, 625.0)),
) -> RadialBenchmark:
    continuous = solve_curve(frequency_hz)
    spacings = np.asarray(spacings_m, dtype=np.float64)
    curves = [solve_curve(frequency_hz, radial_spacing_m=float(value)) for value in spacings]
    beta = np.stack([curve.beta_rad_per_m for curve in curves])
    attenuation = np.stack([curve.attenuation_db_per_mm for curve in curves])
    velocity = np.stack([curve.phase_velocity_fraction_c for curve in curves])
    return RadialBenchmark(
        continuous, spacings, beta, attenuation, velocity,
        attenuation - continuous.attenuation_db_per_mm,
        velocity - continuous.phase_velocity_fraction_c,
        np.stack([curve.eigen_residual for curve in curves]),
    )


def write_csv(result: RadialBenchmark, output: str | Path) -> Path:
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    rows=["frequency_hz,radial_spacing_km,attenuation_db_per_mm,phase_velocity_fraction_c,attenuation_error_db_per_mm,phase_velocity_error_fraction_c,beta_real_rad_per_m,beta_imag_rad_per_m,eigen_residual"]
    for s,spacing in enumerate(result.spacing_m):
        for f,frequency in enumerate(result.continuous.frequency_hz):
            values=(frequency,spacing/1000,result.discretized_attenuation_db_per_mm[s,f],result.discretized_phase_velocity_fraction_c[s,f],result.attenuation_error_db_per_mm[s,f],result.phase_velocity_error_fraction_c[s,f],result.discretized_beta_rad_per_m[s,f].real,result.discretized_beta_rad_per_m[s,f].imag,result.eigen_residual[s,f])
            rows.append(",".join(f"{value:.12g}" for value in values))
    output.write_text("\n".join(rows)+"\n",encoding="utf-8");return output


def render(result: RadialBenchmark, output: str | Path) -> Path:
    import matplotlib.pyplot as plt
    output=Path(output);figure,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True);f=result.continuous.frequency_hz
    axes[0,0].plot(f,result.continuous.attenuation_db_per_mm,"k",label="continuous");axes[0,1].plot(f,result.continuous.phase_velocity_fraction_c,"k",label="continuous")
    for i,spacing in enumerate(result.spacing_m):
        label=f"{spacing/1000:g} km";axes[0,0].plot(f,result.discretized_attenuation_db_per_mm[i],label=label);axes[0,1].plot(f,result.discretized_phase_velocity_fraction_c[i],label=label);axes[1,0].plot(f,result.attenuation_error_db_per_mm[i],label=label);axes[1,1].plot(f,result.phase_velocity_error_fraction_c[i],label=label)
    axes[0,0].set_ylabel("Attenuation (dB/Mm)");axes[0,1].set_ylabel("Phase velocity (c)");axes[1,0].set_ylabel("Attenuation error (dB/Mm)");axes[1,1].set_ylabel("Phase-velocity error (c)")
    for ax in axes[1]:ax.set_xlabel("Frequency (Hz)")
    for ax in axes.flat:ax.grid(True,color="0.9");ax.legend(fontsize=8)
    figure.savefig(output,dpi=180,facecolor="white");plt.close(figure);return output
