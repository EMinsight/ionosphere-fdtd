"""Measure azimuth-dependent phase dispersion on the geodesic dual grid."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from ionosphere_fdtd.constants import C_0, EARTH_RADIUS_M
from ionosphere_fdtd.solver import GeodesicFDTD
from ionosphere_fdtd.sources import geographic_distribution

from ..simpson_taflove_2004.model import (
    PAPER_DFT_SIZE,
    PAPER_TIME_STEP_S,
    ValidationTraces,
    _receiver_spectra,
    bannister_phase_velocity_fraction_c,
    find_dft_truncations,
    paper_evaluation_frequencies,
)

FloatArray = NDArray[np.float64]
DEFAULT_AZIMUTHS_DEG = tuple(float(value) for value in range(0, 360, 30))
NEAR_ARC_DEG = 45.0
FAR_ARC_DEG = 90.0


@dataclass(frozen=True, slots=True)
class DirectionalPhaseVelocity:
    """Phase velocities for equal-length paths at several source azimuths."""

    azimuth_deg: FloatArray
    frequency_hz: FloatArray
    velocity_fraction_c: FloatArray
    benchmark_fraction_c: FloatArray
    dft_truncations: Mapping[str, int]


def destination_direction(
    source_direction: FloatArray,
    azimuth_deg: float,
    arc_deg: float,
) -> FloatArray:
    """Return a spherical destination at an azimuth and central-angle distance."""

    source = np.asarray(source_direction, dtype=np.float64)
    if source.shape != (3,) or not np.all(np.isfinite(source)):
        raise ValueError("source_direction must be one finite 3-vector")
    norm = float(np.linalg.norm(source))
    if norm == 0.0:
        raise ValueError("source_direction must be nonzero")
    if not 0.0 < arc_deg < 180.0:
        raise ValueError("arc_deg must be between 0 and 180")
    source = source / norm

    pole = np.asarray((0.0, 0.0, 1.0))
    east = np.cross(pole, source)
    if np.linalg.norm(east) < 1.0e-12:
        east = np.cross(np.asarray((1.0, 0.0, 0.0)), source)
    east /= np.linalg.norm(east)
    north = np.cross(source, east)
    azimuth = np.deg2rad(azimuth_deg)
    arc = np.deg2rad(arc_deg)
    tangent = np.cos(azimuth) * north + np.sin(azimuth) * east
    destination = np.cos(arc) * source + np.sin(arc) * tangent
    return destination / np.linalg.norm(destination)


def _latitude_longitude(direction: FloatArray) -> tuple[float, float]:
    latitude = np.rad2deg(
        np.arctan2(direction[2], np.hypot(direction[0], direction[1]))
    )
    longitude = np.rad2deg(np.arctan2(direction[1], direction[0]))
    return float(latitude), float(longitude)


def _labels(index: int) -> tuple[str, str]:
    return f"near-{index:02d}", f"far-{index:02d}"


def record_directional_traces(
    simulation: GeodesicFDTD,
    *,
    azimuths_deg: Sequence[float] = DEFAULT_AZIMUTHS_DEG,
    steps: int,
    synchronize_every: int = 128,
) -> ValidationTraces:
    """Record 45° and 90° receivers along every requested source azimuth."""

    if simulation.source is None:
        raise ValueError("directional dispersion measurement requires a source")
    if simulation.steps != 0:
        raise ValueError("directional recording requires a fresh simulation")
    if steps < 1:
        raise ValueError("steps must be positive")
    azimuths = np.asarray(azimuths_deg, dtype=np.float64)
    if azimuths.ndim != 1 or len(azimuths) < 2:
        raise ValueError("at least two azimuths are required")
    if not np.all(np.isfinite(azimuths)):
        raise ValueError("azimuths must be finite")

    source = simulation.source.direction()
    distributions: list[tuple[NDArray[np.int64], int, FloatArray]] = []
    labels: list[str] = []
    for index, azimuth in enumerate(azimuths):
        near_label, far_label = _labels(index)
        for label, arc_deg in (
            (near_label, NEAR_ARC_DEG),
            (far_label, FAR_ARC_DEG),
        ):
            latitude, longitude = _latitude_longitude(
                destination_direction(source, float(azimuth), arc_deg)
            )
            distributions.append(
                geographic_distribution(
                    simulation,
                    latitude,
                    longitude,
                    0.0,
                )
            )
            labels.append(label)

    vertices = np.stack([item[0] for item in distributions])
    layers = np.asarray([item[1] for item in distributions], dtype=np.int64)
    weights = np.stack([item[2] for item in distributions])
    values = simulation.record_er_observations(
        vertices,
        layers,
        weights,
        steps,
        synchronize_every=synchronize_every,
    ).astype(np.float64, copy=False)
    time_steps = np.arange(steps + 1, dtype=np.int64)
    return ValidationTraces(
        time_steps=time_steps,
        time_s=time_steps.astype(np.float64) * simulation.time_step_s,
        er_v_m=values,
        labels=tuple(labels),
    )


def compute_directional_phase_velocity(
    traces: ValidationTraces,
    azimuths_deg: Sequence[float],
    *,
    time_step_s: float = PAPER_TIME_STEP_S,
    n_fft: int = PAPER_DFT_SIZE,
    truncations: Mapping[str, int] | None = None,
) -> DirectionalPhaseVelocity:
    """Compute 45° path phase velocity for every measured azimuth."""

    azimuths = np.asarray(azimuths_deg, dtype=np.float64)
    expected_labels = tuple(
        label for index in range(len(azimuths)) for label in _labels(index)
    )
    if traces.labels != expected_labels:
        raise ValueError("trace labels do not match the directional receiver order")
    selected = find_dft_truncations(traces) if truncations is None else truncations
    selected_truncations, spectra = _receiver_spectra(
        traces,
        n_fft=n_fft,
        truncations=selected,
    )
    dft_frequency = np.fft.rfftfreq(n_fft, d=time_step_s)
    frequency = paper_evaluation_frequencies()
    stop = int(np.searchsorted(dft_frequency, frequency[-1], side="right")) + 1
    path_distance_m = np.deg2rad(FAR_ARC_DEG - NEAR_ARC_DEG) * EARTH_RADIUS_M
    velocities = np.empty((len(azimuths), len(frequency)), dtype=np.float64)

    for index in range(len(azimuths)):
        near_label, far_label = _labels(index)
        phase = np.unwrap(
            np.angle(
                spectra[near_label][:stop] * np.conj(spectra[far_label][:stop])
            )
        )
        sampled_phase = np.interp(frequency, dft_frequency[:stop], phase)
        if np.any(sampled_phase <= 0.0):
            raise ValueError(
                f"receiver phase delay must be positive at azimuth {azimuths[index]:g}°"
            )
        velocities[index] = (
            2.0 * np.pi * frequency * path_distance_m / sampled_phase / C_0
        )

    return DirectionalPhaseVelocity(
        azimuth_deg=azimuths,
        frequency_hz=frequency,
        velocity_fraction_c=velocities,
        benchmark_fraction_c=bannister_phase_velocity_fraction_c(frequency),
        dft_truncations=selected_truncations,
    )


def directional_dispersion_metrics(
    curves: DirectionalPhaseVelocity,
) -> dict[str, float]:
    """Summarize azimuthal anisotropy and benchmark phase-velocity error."""

    mean_velocity = np.mean(curves.velocity_fraction_c, axis=0)
    relative_deviation = (
        curves.velocity_fraction_c - mean_velocity[None, :]
    ) / mean_velocity[None, :]
    relative_spread = np.ptp(curves.velocity_fraction_c, axis=0) / mean_velocity
    benchmark_residual = mean_velocity - curves.benchmark_fraction_c
    maximum_spread_index = int(np.argmax(relative_spread))
    maximum_benchmark_index = int(np.argmax(np.abs(benchmark_residual)))
    return {
        "mean_azimuthal_relative_spread": float(np.mean(relative_spread)),
        "maximum_azimuthal_relative_spread": float(np.max(relative_spread)),
        "maximum_azimuthal_spread_frequency_hz": float(
            curves.frequency_hz[maximum_spread_index]
        ),
        "azimuthal_relative_rms": float(
            np.sqrt(np.mean(relative_deviation**2))
        ),
        "mean_phase_velocity_mae_fraction_c": float(
            np.mean(np.abs(benchmark_residual))
        ),
        "mean_phase_velocity_max_error_fraction_c": float(
            np.max(np.abs(benchmark_residual))
        ),
        "mean_phase_velocity_max_error_frequency_hz": float(
            curves.frequency_hz[maximum_benchmark_index]
        ),
    }


def write_directional_dispersion_csv(
    curves: DirectionalPhaseVelocity,
    output: str | Path,
) -> Path:
    """Write one row per frequency and azimuth for reproducible reanalysis."""

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mean_velocity = np.mean(curves.velocity_fraction_c, axis=0)
    rows = [
        "frequency_hz,azimuth_deg,phase_velocity_fraction_c,"
        "azimuth_mean_fraction_c,relative_deviation_from_azimuth_mean,"
        "bannister_fraction_c"
    ]
    for frequency_index, frequency in enumerate(curves.frequency_hz):
        mean = mean_velocity[frequency_index]
        for azimuth_index, azimuth in enumerate(curves.azimuth_deg):
            velocity = curves.velocity_fraction_c[azimuth_index, frequency_index]
            rows.append(
                f"{frequency:.12f},{azimuth:.6f},{velocity:.12f},{mean:.12f},"
                f"{(velocity - mean) / mean:.12e},"
                f"{curves.benchmark_fraction_c[frequency_index]:.12f}"
            )
    output_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return output_path


def render_directional_dispersion(
    curves: DirectionalPhaseVelocity,
    output: str | Path,
) -> Path:
    """Plot absolute phase velocity and its residual directional anisotropy."""

    import matplotlib.pyplot as plt

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mean_velocity = np.mean(curves.velocity_fraction_c, axis=0)
    colors = plt.cm.hsv(np.linspace(0.0, 1.0, len(curves.azimuth_deg), endpoint=False))
    figure, axes = plt.subplots(
        2,
        1,
        figsize=(10.0, 8.0),
        sharex=True,
        constrained_layout=True,
    )
    for index, (azimuth, color) in enumerate(zip(curves.azimuth_deg, colors)):
        axes[0].plot(
            curves.frequency_hz,
            curves.velocity_fraction_c[index],
            color=color,
            linewidth=1.0,
            label=f"{azimuth:g}°",
        )
        axes[1].plot(
            curves.frequency_hz,
            100.0
            * (curves.velocity_fraction_c[index] - mean_velocity)
            / mean_velocity,
            color=color,
            linewidth=1.0,
        )
    axes[0].plot(
        curves.frequency_hz,
        curves.benchmark_fraction_c,
        color="black",
        linewidth=2.0,
        linestyle="--",
        label="Bannister eq. (4)",
    )
    axes[0].plot(
        curves.frequency_hz,
        mean_velocity,
        color="black",
        linewidth=2.0,
        label="azimuth mean",
    )
    axes[0].set_ylabel("Phase velocity (fraction of c)")
    axes[0].set_title("Uniform-model directional phase velocity")
    axes[0].legend(ncol=4, fontsize=8)
    axes[1].axhline(0.0, color="black", linewidth=0.8)
    axes[1].set_xlabel("Frequency (Hz)")
    axes[1].set_ylabel("Deviation from azimuth mean (%)")
    axes[1].set_title("Geodesic-grid directional anisotropy")
    for axis in axes:
        axis.grid(True, color="0.9", linewidth=0.7)
    figure.savefig(output_path, dpi=180, facecolor="white")
    plt.close(figure)
    return output_path
