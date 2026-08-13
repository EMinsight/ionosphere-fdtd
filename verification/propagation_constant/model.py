"""Fit complex propagation constants from receivers on great-circle paths."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from ionosphere_fdtd.constants import C_0, EARTH_RADIUS_M
from ionosphere_fdtd.solver import GeodesicFDTD
from ionosphere_fdtd.sources import geographic_distribution

from ..directional_dispersion.model import (
    DEFAULT_AZIMUTHS_DEG,
    _latitude_longitude,
    destination_direction,
)
from ..simpson_taflove_2004.model import (
    PAPER_DFT_SIZE,
    PAPER_TIME_STEP_S,
    ValidationTraces,
    _receiver_spectra,
    bannister_figure_8_guide,
    bannister_phase_velocity_fraction_c,
    find_dft_truncations,
    paper_evaluation_frequencies,
)

FloatArray = NDArray[np.float64]
ComplexArray = NDArray[np.complex128]
DEFAULT_RECEIVER_ARCS_DEG = (30.0, 45.0, 60.0, 75.0, 90.0)


@dataclass(frozen=True, slots=True)
class PropagationConstantFit:
    azimuth_deg: FloatArray
    receiver_arc_deg: FloatArray
    receiver_distance_m: FloatArray
    frequency_hz: FloatArray
    spectra: ComplexArray
    attenuation_db_per_mm: FloatArray
    beta_rad_per_m: FloatArray
    phase_velocity_fraction_c: FloatArray
    amplitude_residual_rms: FloatArray
    phase_residual_rms_rad: FloatArray
    complex_residual_rms: FloatArray
    residual_by_receiver: ComplexArray
    bannister_attenuation_db_per_mm: FloatArray
    bannister_phase_velocity_fraction_c: FloatArray
    dft_truncations: Mapping[str, int]


def _label(azimuth_index: int, receiver_index: int) -> str:
    return f"az-{azimuth_index:02d}-r-{receiver_index:02d}"


def record_multi_receiver_traces(
    simulation: GeodesicFDTD,
    *,
    azimuths_deg: Sequence[float] = DEFAULT_AZIMUTHS_DEG,
    receiver_arcs_deg: Sequence[float] = DEFAULT_RECEIVER_ARCS_DEG,
    steps: int,
    synchronize_every: int = 128,
) -> ValidationTraces:
    """Record surface ``Er`` at several distances along each great circle."""

    if simulation.source is None or simulation.steps != 0:
        raise ValueError("recording requires a fresh simulation with a source")
    if steps < 1:
        raise ValueError("steps must be positive")
    azimuths = np.asarray(azimuths_deg, dtype=np.float64)
    arcs = np.asarray(receiver_arcs_deg, dtype=np.float64)
    if azimuths.ndim != 1 or len(azimuths) < 1 or not np.all(np.isfinite(azimuths)):
        raise ValueError("azimuths must be a nonempty finite sequence")
    if arcs.ndim != 1 or len(arcs) < 3 or not np.all(np.diff(arcs) > 0.0):
        raise ValueError("at least three strictly increasing receiver arcs are required")
    if arcs[0] <= 0.0 or arcs[-1] >= 180.0:
        raise ValueError("receiver arcs must lie between 0 and 180 degrees")

    source = simulation.source.direction()
    distributions = []
    labels = []
    for azimuth_index, azimuth in enumerate(azimuths):
        for receiver_index, arc in enumerate(arcs):
            latitude, longitude = _latitude_longitude(
                destination_direction(source, float(azimuth), float(arc))
            )
            distributions.append(
                geographic_distribution(simulation, latitude, longitude, 0.0)
            )
            labels.append(_label(azimuth_index, receiver_index))
    vertices = np.stack([item[0] for item in distributions])
    layers = np.asarray([item[1] for item in distributions], dtype=np.int64)
    weights = np.stack([item[2] for item in distributions])
    values = simulation.record_er_observations(
        vertices, layers, weights, steps, synchronize_every=synchronize_every
    ).astype(np.float64, copy=False)
    time_steps = np.arange(steps + 1, dtype=np.int64)
    return ValidationTraces(
        time_steps=time_steps,
        time_s=time_steps.astype(np.float64) * simulation.time_step_s,
        er_v_m=values,
        labels=tuple(labels),
    )


def fit_propagation_constants(
    traces: ValidationTraces,
    azimuths_deg: Sequence[float],
    receiver_arcs_deg: Sequence[float] = DEFAULT_RECEIVER_ARCS_DEG,
    *,
    time_step_s: float = PAPER_TIME_STEP_S,
    n_fft: int = PAPER_DFT_SIZE,
    truncations: Mapping[str, int] | None = None,
) -> PropagationConstantFit:
    """Regress amplitude and spatial phase after spherical spreading removal."""

    azimuths = np.asarray(azimuths_deg, dtype=np.float64)
    arcs = np.asarray(receiver_arcs_deg, dtype=np.float64)
    expected = tuple(
        _label(a, r) for a in range(len(azimuths)) for r in range(len(arcs))
    )
    if traces.labels != expected:
        raise ValueError("trace labels do not match receiver geometry")
    selected = find_dft_truncations(traces) if truncations is None else truncations
    selected_truncations, raw_spectra = _receiver_spectra(
        traces, n_fft=n_fft, truncations=selected
    )
    dft_frequency = np.fft.rfftfreq(n_fft, d=time_step_s)
    frequency = paper_evaluation_frequencies()
    spectra = np.empty((len(azimuths), len(arcs), len(frequency)), np.complex128)
    for a in range(len(azimuths)):
        for r in range(len(arcs)):
            value = raw_spectra[_label(a, r)]
            spectra[a, r] = np.interp(frequency, dft_frequency, value.real) + 1j * np.interp(
                frequency, dft_frequency, value.imag
            )

    distance = np.deg2rad(arcs) * EARTH_RADIUS_M
    spreading = 1.0 / np.sqrt(np.sin(np.deg2rad(arcs)))
    corrected = spectra / spreading[None, :, None]
    design = np.column_stack((np.ones(len(distance)), distance))
    attenuation = np.empty((len(azimuths), len(frequency)))
    beta = np.empty_like(attenuation)
    amp_rms = np.empty_like(attenuation)
    phase_rms = np.empty_like(attenuation)
    complex_rms = np.empty_like(attenuation)
    residual = np.empty_like(corrected)
    reference_beta = (
        2.0 * np.pi * frequency
        / (bannister_phase_velocity_fraction_c(frequency) * C_0)
    )
    for a in range(len(azimuths)):
        log_amplitude = np.log(np.maximum(np.abs(corrected[a]), np.finfo(float).tiny))
        # Adjacent receivers can differ by more than pi at the upper bins. Remove
        # the published reference slope before unwrapping, then restore it. This
        # chooses the physically relevant spatial branch without fitting to it.
        phase = np.unwrap(
            np.angle(corrected[a] * np.exp(1j * distance[:, None] * reference_beta)),
            axis=0,
        ) - distance[:, None] * reference_beta
        for f in range(len(frequency)):
            amp_coef = np.linalg.lstsq(design, log_amplitude[:, f], rcond=None)[0]
            phase_coef = np.linalg.lstsq(design, phase[:, f], rcond=None)[0]
            amp_error = log_amplitude[:, f] - design @ amp_coef
            phase_error = phase[:, f] - design @ phase_coef
            attenuation[a, f] = -amp_coef[1] * (20.0 / np.log(10.0)) * 1.0e6
            beta[a, f] = -phase_coef[1]
            amp_rms[a, f] = np.sqrt(np.mean(amp_error**2))
            phase_rms[a, f] = np.sqrt(np.mean(phase_error**2))
            predicted = np.exp(design @ amp_coef + 1j * (design @ phase_coef))
            residual[a, :, f] = corrected[a, :, f] / predicted - 1.0
            complex_rms[a, f] = np.sqrt(np.mean(np.abs(residual[a, :, f]) ** 2))
    if np.any(beta <= 0.0):
        raise ValueError("fitted phase constants must be positive")
    velocity = 2.0 * np.pi * frequency[None, :] / beta / C_0
    return PropagationConstantFit(
        azimuth_deg=azimuths,
        receiver_arc_deg=arcs,
        receiver_distance_m=distance,
        frequency_hz=frequency,
        spectra=spectra,
        attenuation_db_per_mm=attenuation,
        beta_rad_per_m=beta,
        phase_velocity_fraction_c=velocity,
        amplitude_residual_rms=amp_rms,
        phase_residual_rms_rad=phase_rms,
        complex_residual_rms=complex_rms,
        residual_by_receiver=residual,
        bannister_attenuation_db_per_mm=bannister_figure_8_guide(frequency),
        bannister_phase_velocity_fraction_c=bannister_phase_velocity_fraction_c(frequency),
        dft_truncations=selected_truncations,
    )


def write_fit_csv(fit: PropagationConstantFit, output: str | Path) -> Path:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = ["frequency_hz,azimuth_deg,attenuation_db_per_mm,beta_rad_per_m,phase_velocity_fraction_c,amplitude_residual_rms,phase_residual_rms_rad,complex_residual_rms,bannister_attenuation_db_per_mm,bannister_phase_velocity_fraction_c"]
    for a, azimuth in enumerate(fit.azimuth_deg):
        for f, frequency in enumerate(fit.frequency_hz):
            rows.append(",".join(f"{value:.12g}" for value in (
                frequency, azimuth, fit.attenuation_db_per_mm[a, f], fit.beta_rad_per_m[a, f],
                fit.phase_velocity_fraction_c[a, f], fit.amplitude_residual_rms[a, f],
                fit.phase_residual_rms_rad[a, f], fit.complex_residual_rms[a, f],
                fit.bannister_attenuation_db_per_mm[f], fit.bannister_phase_velocity_fraction_c[f],
            )))
    output.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return output


def render_fit(fit: PropagationConstantFit, output: str | Path) -> Path:
    import matplotlib.pyplot as plt
    output = Path(output)
    mean_alpha = np.mean(fit.attenuation_db_per_mm, axis=0)
    mean_velocity = np.mean(fit.phase_velocity_fraction_c, axis=0)
    mean_residual = np.mean(fit.complex_residual_rms, axis=0)
    receiver_residual = np.sqrt(np.mean(np.abs(fit.residual_by_receiver) ** 2, axis=(0, 2)))
    figure, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    axes[0, 0].plot(fit.frequency_hz, mean_alpha, label="multi-receiver fit")
    axes[0, 0].plot(fit.frequency_hz, fit.bannister_attenuation_db_per_mm, "k--", label="Bannister")
    axes[0, 1].plot(fit.frequency_hz, mean_velocity, label="multi-receiver fit")
    axes[0, 1].plot(fit.frequency_hz, fit.bannister_phase_velocity_fraction_c, "k--", label="Bannister")
    axes[1, 0].plot(fit.frequency_hz, mean_residual)
    axes[1, 1].plot(fit.receiver_arc_deg, receiver_residual, marker="o")
    axes[0, 0].set_ylabel("Attenuation (dB/Mm)"); axes[0, 1].set_ylabel("Phase velocity (c)")
    axes[1, 0].set_ylabel("Complex regression RMS"); axes[1, 1].set_ylabel("Complex residual RMS")
    axes[1, 0].set_xlabel("Frequency (Hz)"); axes[1, 1].set_xlabel("Receiver arc (deg)")
    for axis in axes.flat: axis.grid(True, color="0.9");
    axes[0, 0].legend(); axes[0, 1].legend()
    figure.savefig(output, dpi=180, facecolor="white"); plt.close(figure)
    return output
