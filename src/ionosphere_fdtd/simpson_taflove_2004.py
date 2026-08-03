"""Reproduce the validation study in Simpson and Taflove (2004), Figs. 7–8."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from numpy.typing import NDArray

from .constants import EARTH_RADIUS_M
from .materials import EarthIonosphereMaterial, SimpsonTaflove2004Material
from .solver import GeodesicFDTD, SimulationConfig
from .sources import GaussianCurrent, geographic_distribution

PAPER_TIME_STEP_S = 3.0e-6
PAPER_RADIAL_CELLS = 40
PAPER_SOURCE_LATITUDE_DEG = 0.0
PAPER_SOURCE_LONGITUDE_DEG = -47.0
PAPER_SOURCE_ALTITUDE_M = 2_500.0
PAPER_SOURCE_PEAK_CURRENT_A = 1.0
PAPER_SOURCE_FULL_WIDTH_STEPS = 480
PAPER_SOURCE_CENTER_STEPS = 960
PAPER_TRACE_STEPS = 35_000
PAPER_DFT_TRUNCATIONS = {"A": 22_849, "B": 24_165, "A′": 22_737, "B′": 25_023}
PAPER_DFT_SIZE = 32_768
REPRESENTATIVE_IONOSPHERE_REFERENCE_HEIGHT_M = 70_000.0
REPRESENTATIVE_IONOSPHERE_SCALE_HEIGHT_M = 3_330.0
PAPER_VALID_FREQUENCY_HZ = (50.0, 500.0)
PAPER_PATH_AB_TOLERANCE_DB_PER_MM = 0.5
PAPER_PATH_APBP_TOLERANCE_DB_PER_MM = 1.0
PAPER_MINIMUM_SIMULATION_STEPS = max(PAPER_DFT_TRUNCATIONS.values()) - 1
BANNISTER_REFERENCE_HEIGHT_KM = 70.0
BANNISTER_SCALE_HEIGHT_KM = 1.0 / 0.3

_paper_frequency_resolution_hz = 1.0 / (PAPER_DFT_SIZE * PAPER_TIME_STEP_S)
PAPER_EVALUATION_FREQUENCIES_HZ = tuple(
    np.arange(
        np.ceil(PAPER_VALID_FREQUENCY_HZ[0] / _paper_frequency_resolution_hz),
        np.floor(PAPER_VALID_FREQUENCY_HZ[1] / _paper_frequency_resolution_hz) + 1,
    )
    * _paper_frequency_resolution_hz
)

FloatArray = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class PaperReceiver:
    """One equatorial observation point from Figure 7."""

    label: str
    longitude_deg: float
    fraction_to_antipode: float
    direction: str
    altitude_m: float = 0.0


PAPER_RECEIVERS = (
    PaperReceiver("A", -2.0, 0.25, "east"),
    PaperReceiver("A′", -92.0, 0.25, "west"),
    PaperReceiver("B", 43.0, 0.50, "east"),
    PaperReceiver("B′", -137.0, 0.50, "west"),
)


@dataclass(frozen=True, slots=True)
class ValidationTraces:
    """Radial electric fields at the four Figure 7 receivers."""

    time_steps: NDArray[np.int64]
    time_s: FloatArray
    er_v_m: FloatArray
    labels: tuple[str, ...]

    def trace(self, label: str) -> FloatArray:
        return self.er_v_m[:, self.labels.index(label)]


@dataclass(frozen=True, slots=True)
class AttenuationCurves:
    """Frequency-domain attenuation for the east and west 45° paths."""

    frequency_hz: FloatArray
    path_ab_db_per_mm: FloatArray
    path_apbp_db_per_mm: FloatArray
    benchmark_db_per_mm: FloatArray
    dft_truncations: Mapping[str, int]
    valid_frequency_hz: tuple[float, float] = PAPER_VALID_FREQUENCY_HZ


def natural_earth_land_classifier() -> Callable[[FloatArray], NDArray[np.bool_]]:
    """Build a vectorized land classifier from Natural Earth's 110-m polygons."""

    geometry, contains_xy = _natural_earth_geometry()

    def classify(directions: FloatArray) -> NDArray[np.bool_]:
        longitude = np.rad2deg(np.arctan2(directions[:, 1], directions[:, 0]))
        latitude = np.rad2deg(
            np.arctan2(
                directions[:, 2],
                np.hypot(directions[:, 0], directions[:, 1]),
            )
        )
        return np.asarray(contains_xy(geometry, longitude, latitude), dtype=np.bool_)

    return classify


@lru_cache(maxsize=1)
def _natural_earth_geometry() -> tuple[Any, Any]:
    try:
        from cartopy.io import shapereader
        from shapely import contains_xy
        from shapely.ops import unary_union
    except ImportError as error:
        raise ImportError(
            "Natural Earth materials require: uv sync --extra visualization"
        ) from error
    path = shapereader.natural_earth(
        resolution="110m", category="physical", name="land"
    )
    geometry = unary_union(tuple(shapereader.Reader(path).geometries()))
    return geometry, contains_xy


def create_validation_simulation(
    *,
    subdivision: int = 7,
    material_model: str = "natural-earth",
    backend: str = "torch",
    device: str = "auto",
    dtype: str = "float32",
    compile_step: bool = True,
    torch_threads: int | None = None,
    ionosphere_reference_height_m: float = (
        REPRESENTATIVE_IONOSPHERE_REFERENCE_HEIGHT_M
    ),
    ionosphere_scale_height_m: float = REPRESENTATIVE_IONOSPHERE_SCALE_HEIGHT_M,
) -> GeodesicFDTD:
    """Create the paper's 200-km radial domain, pulse, and 3-µs time step."""

    if material_model == "natural-earth":
        material: Any = SimpsonTaflove2004Material(
            land_classifier=natural_earth_land_classifier(),
            ionosphere_reference_height_m=ionosphere_reference_height_m,
            ionosphere_scale_height_m=ionosphere_scale_height_m,
        )
    elif material_model == "uniform":
        material = EarthIonosphereMaterial(
            ionosphere_reference_height_m=ionosphere_reference_height_m,
            ionosphere_scale_height_m=ionosphere_scale_height_m,
        )
    else:
        raise ValueError("material_model must be 'natural-earth' or 'uniform'")
    source = GaussianCurrent(
        latitude_deg=PAPER_SOURCE_LATITUDE_DEG,
        longitude_deg=PAPER_SOURCE_LONGITUDE_DEG,
        altitude_m=PAPER_SOURCE_ALTITUDE_M,
        peak_current_a=PAPER_SOURCE_PEAK_CURRENT_A,
        center_time_s=PAPER_SOURCE_CENTER_STEPS * PAPER_TIME_STEP_S,
        one_over_e_half_width_s=(
            0.5 * PAPER_SOURCE_FULL_WIDTH_STEPS * PAPER_TIME_STEP_S
        ),
    )
    return GeodesicFDTD(
        config=SimulationConfig(
            subdivision=subdivision,
            radial_cells=PAPER_RADIAL_CELLS,
            minimum_altitude_m=-100_000.0,
            maximum_altitude_m=100_000.0,
            courant_factor=0.4,
            time_step_s=PAPER_TIME_STEP_S,
        ),
        material=material,
        source=source,
        backend=backend,
        device=device,
        dtype=dtype,
        compile_step=compile_step,
        torch_threads=torch_threads,
    )


def record_validation_traces(
    simulation: GeodesicFDTD,
    *,
    steps: int = PAPER_TRACE_STEPS,
    synchronize_every: int = 128,
) -> ValidationTraces:
    """Record barycentrically interpolated ``Er`` at A, A′, B, and B′."""

    if simulation.steps != 0:
        raise ValueError("validation recording requires a fresh simulation")
    if steps < 1:
        raise ValueError("steps must be positive")
    distributions = [
        geographic_distribution(
            simulation, 0.0, receiver.longitude_deg, receiver.altitude_m
        )
        for receiver in PAPER_RECEIVERS
    ]
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
        labels=tuple(receiver.label for receiver in PAPER_RECEIVERS),
    )


def compute_attenuation(
    traces: ValidationTraces,
    *,
    time_step_s: float = PAPER_TIME_STEP_S,
    n_fft: int = PAPER_DFT_SIZE,
    truncations: Mapping[str, int] | None = None,
) -> AttenuationCurves:
    """Compute attenuation using receiver-specific rectangular DFT windows.

    By default, each record is truncated at its own positive-to-negative zero
    crossing following the primary pulse and overshoot.  This implements the
    physical windowing criterion described by Simpson and Taflove instead of
    assuming that their reported sample numbers apply to a different waveform.
    """

    selected_truncations = dict(
        find_dft_truncations(traces) if truncations is None else truncations
    )
    missing = set(traces.labels) - set(selected_truncations)
    if missing:
        raise ValueError(f"missing DFT truncations for: {', '.join(sorted(missing))}")
    required = max(selected_truncations.values())
    if n_fft < required:
        raise ValueError(f"n_fft must be at least {required}")
    spectra: dict[str, FloatArray] = {}
    for label in traces.labels:
        cutoff = selected_truncations[label]
        if not 2 <= cutoff <= len(traces.time_steps):
            raise ValueError(
                f"DFT truncation for {label} must be between 2 and "
                f"{len(traces.time_steps)}"
            )
        signal = traces.trace(label)[:cutoff]
        spectra[label] = np.abs(np.fft.rfft(signal, n=n_fft))
    tiny = np.finfo(np.float64).tiny
    path_distance_mm = (0.25 * np.pi * EARTH_RADIUS_M) / 1.0e6
    path_ab = 20.0 * np.log10(
        np.maximum(spectra["A"], tiny) / np.maximum(spectra["B"], tiny)
    ) / path_distance_mm
    path_apbp = 20.0 * np.log10(
        np.maximum(spectra["A′"], tiny) / np.maximum(spectra["B′"], tiny)
    ) / path_distance_mm
    frequency = np.fft.rfftfreq(n_fft, d=time_step_s)
    benchmark = bannister_figure_8_guide(frequency)
    return AttenuationCurves(
        frequency,
        path_ab,
        path_apbp,
        benchmark,
        selected_truncations,
    )


def find_dft_truncations(traces: ValidationTraces) -> dict[str, int]:
    """Locate the post-overshoot zero crossing that precedes each slow tail."""

    truncations: dict[str, int] = {}
    for label in traces.labels:
        signal = traces.trace(label)
        negative_peak = int(np.argmin(signal))
        negative_amplitude = abs(float(signal[negative_peak]))
        if negative_amplitude == 0.0:
            raise ValueError(f"{label} trace has no negative primary pulse")
        positive_threshold = max(
            1.0e-6 * negative_amplitude,
            np.finfo(np.float64).eps * negative_amplitude,
        )
        overshoot_candidates = np.flatnonzero(
            signal[negative_peak + 1 :] > positive_threshold
        )
        if not len(overshoot_candidates):
            raise ValueError(
                f"{label} trace has no positive overshoot after its primary pulse; "
                "the paper's DFT window is undefined"
            )
        overshoot = negative_peak + 1 + int(overshoot_candidates[0])
        crossings = np.flatnonzero(
            (signal[overshoot:-1] >= 0.0) & (signal[overshoot + 1 :] < 0.0)
        )
        if not len(crossings):
            raise ValueError(
                f"{label} trace has no post-overshoot zero crossing before the "
                "slow tail"
            )
        crossing = overshoot + int(crossings[0])
        truncations[label] = crossing + 1
    return truncations


def bannister_figure_8_guide(frequency_hz: FloatArray) -> FloatArray:
    """Evaluate the daytime attenuation model used for Figure 8.

    This implements Bannister (1984), equations (5), (7), and (8), with
    ``H = 70 km`` and ``xi_0 = xi_1 = 1 / 0.3 km`` as specified below those
    equations. Simpson and Taflove cite that curve as the previous results in
    their Figure 8.
    """

    frequency = np.asarray(frequency_hz, dtype=np.float64)
    safe_frequency = np.where(frequency > 0.0, frequency, 1.0)
    h0_km = BANNISTER_REFERENCE_HEIGHT_KM - BANNISTER_SCALE_HEIGHT_KM * np.log(
        2.5e5 / (2.0 * np.pi * safe_frequency)
    )
    h1_km = h0_km + 2.0 * BANNISTER_SCALE_HEIGHT_KM * np.log(
        2.39e4 / (safe_frequency * BANNISTER_SCALE_HEIGHT_KM)
    )
    attenuation = (
        0.143
        * safe_frequency
        * np.sqrt(h1_km / h0_km)
        * BANNISTER_SCALE_HEIGHT_KM
        * (1.0 / h0_km + 1.0 / h1_km)
    )
    return np.where(frequency > 0.0, attenuation, 0.0)


def paper_evaluation_frequencies() -> FloatArray:
    """Return the 45 DFT frequencies implied by the Figure 8 markers."""

    return np.asarray(PAPER_EVALUATION_FREQUENCIES_HZ, dtype=np.float64)


def sample_paper_comparison(
    curves: AttenuationCurves,
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    """Sample attenuation curves at the fixed Figure 8 comparison bins."""

    frequency = paper_evaluation_frequencies()
    if (
        frequency[0] < curves.frequency_hz[0]
        or frequency[-1] > curves.frequency_hz[-1]
    ):
        raise ValueError("attenuation curves do not cover the paper frequencies")
    return (
        frequency,
        np.interp(frequency, curves.frequency_hz, curves.path_ab_db_per_mm),
        np.interp(frequency, curves.frequency_hz, curves.path_apbp_db_per_mm),
        bannister_figure_8_guide(frequency),
    )


def render_figure_7(
    traces: ValidationTraces, output: str | Path
) -> Path:
    """Render the two temporal-response panels of Figure 7."""

    import matplotlib.pyplot as plt

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(
        2,
        1,
        figsize=(10.0, 7.4),
        sharex=True,
        constrained_layout=True,
    )
    for ax, near, far, fraction in (
        (axes[0], "A", "A′", "1/4 distance to antipode"),
        (axes[1], "B", "B′", "1/2 distance to antipode"),
    ):
        ax.plot(
            traces.time_steps,
            1.0e6 * traces.trace(near),
            label=f"{near} (east)",
        )
        ax.plot(
            traces.time_steps,
            1.0e6 * traces.trace(far),
            label=f"{far} (west)",
        )
        ax.axhline(0.0, color="0.35", linewidth=0.7)
        ax.set_ylabel(r"$E_r$ ($\mu$V/m)")
        ax.set_title(f"Equator, {fraction}")
        ax.grid(True, color="0.9", linewidth=0.7)
        ax.legend()
    axes[-1].set_xlabel("Time steps (Δt = 3 μs)")
    figure.suptitle("Simpson & Taflove (2004), Fig. 7 verification run")
    figure.savefig(output_path, dpi=180, facecolor="white")
    plt.close(figure)
    return output_path


def render_figure_8(
    curves: AttenuationCurves, output: str | Path
) -> Path:
    """Render attenuation curves and the Bannister daytime model."""

    import matplotlib.pyplot as plt

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frequency = curves.frequency_hz
    display = (frequency >= 5.0) & (frequency <= 2_000.0)
    comparison_frequency, path_ab, path_apbp, _ = sample_paper_comparison(curves)
    figure, ax = plt.subplots(figsize=(9.0, 6.2), constrained_layout=True)
    ax.axvspan(
        *curves.valid_frequency_hz,
        color="#e8f2ff",
        label="paper-valid DFT window",
    )
    ax.plot(
        frequency[display],
        curves.benchmark_db_per_mm[display],
        color="black",
        label="Bannister daytime model",
    )
    ax.plot(
        comparison_frequency,
        path_ab,
        "*",
        markersize=6,
        label="Path A–B",
    )
    ax.plot(
        comparison_frequency,
        path_apbp,
        ".",
        markersize=5,
        label="Path A′–B′",
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(5.0, 2_000.0)
    ax.set_ylim(0.1, 30.0)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Attenuation rate (dB/Mm)")
    ax.set_title("Simpson & Taflove (2004), Fig. 8 verification run")
    ax.grid(True, which="both", color="0.9", linewidth=0.6)
    ax.legend()
    figure.savefig(output_path, dpi=180, facecolor="white")
    plt.close(figure)
    return output_path


def validation_metrics(curves: AttenuationCurves) -> dict[str, float]:
    """Return errors from the Bannister model at the paper's DFT bins."""

    frequency, path_ab, path_apbp, benchmark = sample_paper_comparison(curves)
    ab_residual = path_ab - benchmark
    apbp_residual = path_apbp - benchmark
    ab_maximum_index = int(np.argmax(np.abs(ab_residual)))
    apbp_maximum_index = int(np.argmax(np.abs(apbp_residual)))
    return {
        "path_ab_mean_absolute_error_db_per_mm": float(
            np.mean(np.abs(ab_residual))
        ),
        "path_apbp_mean_absolute_error_db_per_mm": float(
            np.mean(np.abs(apbp_residual))
        ),
        "path_ab_maximum_absolute_error_db_per_mm": float(
            np.max(np.abs(ab_residual))
        ),
        "path_apbp_maximum_absolute_error_db_per_mm": float(
            np.max(np.abs(apbp_residual))
        ),
        "path_ab_maximum_error_frequency_hz": float(
            frequency[ab_maximum_index]
        ),
        "path_apbp_maximum_error_frequency_hz": float(
            frequency[apbp_maximum_index]
        ),
        "path_ab_maximum_residual_db_per_mm": float(
            ab_residual[ab_maximum_index]
        ),
        "path_apbp_maximum_residual_db_per_mm": float(
            apbp_residual[apbp_maximum_index]
        ),
    }


def trace_metrics(traces: ValidationTraces) -> dict[str, float | int]:
    """Summarize pulse arrival and east/west asymmetry in Figure 7 traces."""

    result: dict[str, float | int] = {}
    for label in traces.labels:
        values = traces.trace(label)
        peak_index = int(np.argmin(values))
        result[f"{label}_negative_peak_step"] = int(traces.time_steps[peak_index])
        result[f"{label}_negative_peak_uv_m"] = float(1.0e6 * values[peak_index])
    for east, west, name in (("A", "A′", "quarter"), ("B", "B′", "half")):
        east_values = traces.trace(east)
        west_values = traces.trace(west)
        scale = max(float(np.sqrt(np.mean(east_values**2))), np.finfo(float).tiny)
        result[f"{name}_east_west_relative_rms"] = float(
            np.sqrt(np.mean((east_values - west_values) ** 2)) / scale
        )
    return result
