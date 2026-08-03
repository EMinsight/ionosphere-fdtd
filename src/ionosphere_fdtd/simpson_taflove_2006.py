"""Reproduce Simpson, Heikes, and Taflove (2006), Figures 5--7."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .materials import ETOPO5Relief, SimpsonTaflove2004Material, SphericalAnomaly
from .simpson_taflove_2004 import (
    AttenuationCurves,
    ValidationTraces,
    compute_attenuation,
    natural_earth_land_classifier,
)
from .solver import GeodesicFDTD, SimulationConfig
from .sources import (
    TangentialGaussianCurrent,
    geographic_direction,
    geographic_face_index,
    geographic_tangent_basis,
)

FloatArray = NDArray[np.float64]

PAPER_SUBDIVISION = 7
PAPER_SURFACE_CELLS = 163_842
PAPER_NOMINAL_RADIAL_CELLS = 40
PAPER_RADIAL_SPACING_M = 5_000.0
PAPER_SUBGRID_SPACING_M = 1_250.0
PAPER_TRANSMITTER_LATITUDE_DEG = 46.5
PAPER_TRANSMITTER_LONGITUDE_DEG = -90.9
PAPER_TRANSMITTER_LINE_LENGTH_M = 22_500.0
PAPER_TRANSMITTER_CURRENT_A = 300.0
PAPER_CARRIER_FREQUENCY_HZ = 20.0
PAPER_ENVELOPE_FWHM_S = 42.5e-3
PAPER_ENVELOPE_ONE_OVER_E_HALF_WIDTH_S = PAPER_ENVELOPE_FWHM_S / (
    2.0 * np.sqrt(np.log(2.0))
)
PAPER_SOURCE_CENTER_S = 3.0 * PAPER_ENVELOPE_ONE_OVER_E_HALF_WIDTH_S
PAPER_OIL_LATITUDE_DEG = 69.0
PAPER_OIL_LONGITUDE_DEG = -156.0
PAPER_OIL_AREA_KM2 = 4_800.0
PAPER_OIL_RADIUS_M = 1_000.0 * np.sqrt(PAPER_OIL_AREA_KM2 / np.pi)
PAPER_OIL_THICKNESS_M = 1_250.0
PAPER_OIL_MEDIAN_DEPTH_M = 1_200.0
PAPER_OIL_CONDUCTIVITY_FACTOR = 0.1
PAPER_FIGURE_7_DURATION_S = 0.085


@dataclass(frozen=True, slots=True)
class RadarTraces:
    """Surface magnetic-field observations for one Figure 7 model."""

    time_s: FloatArray
    hr_a_m: FloatArray
    ht_east_a_m: FloatArray
    ht_north_a_m: FloatArray
    source_center_s: float
    case: str


@dataclass(frozen=True, slots=True)
class RadarPerturbation:
    """Pointwise normalized magnetic perturbations used in Figure 7."""

    time_s: FloatArray
    delta_ht_db: FloatArray
    delta_hr_db: FloatArray
    valid_ht: NDArray[np.bool_]
    valid_hr: NDArray[np.bool_]
    ht_projection_east_north: FloatArray


def radar_radial_altitudes_m() -> tuple[float, ...]:
    """Return the 5-km grid with 1.25-km lithosphere surface subgridding."""

    coarse = np.linspace(-100_000.0, 100_000.0, PAPER_NOMINAL_RADIAL_CELLS + 1)
    refined_lithosphere = np.arange(-5_000.0, 0.0, PAPER_SUBGRID_SPACING_M)
    return tuple(np.unique(np.concatenate((coarse, refined_lithosphere))))


def paper_anomalies(*, include_oil: bool) -> tuple[SphericalAnomaly, ...]:
    """Return the approximate Laurentian Shield and optional oil anomaly."""

    # The paper gives the Shield conductivity but no downloadable boundary.
    # A broad cap centered over Canada includes Clam Lake and most of Canada.
    shield = SphericalAnomaly(
        latitude_deg=58.0,
        longitude_deg=-95.0,
        radius_m=2_500_000.0,
        altitude_min_m=-20_000.0,
        altitude_max_m=-1.0,
        conductivity_factor=2.4e-4 / (1.0 / 500.0),
    )
    if not include_oil:
        return (shield,)
    half_thickness = 0.5 * PAPER_OIL_THICKNESS_M
    oil = SphericalAnomaly(
        latitude_deg=PAPER_OIL_LATITUDE_DEG,
        longitude_deg=PAPER_OIL_LONGITUDE_DEG,
        radius_m=PAPER_OIL_RADIUS_M,
        altitude_min_m=-(PAPER_OIL_MEDIAN_DEPTH_M + half_thickness),
        altitude_max_m=-(PAPER_OIL_MEDIAN_DEPTH_M - half_thickness),
        conductivity_factor=PAPER_OIL_CONDUCTIVITY_FACTOR,
    )
    return shield, oil


def create_radar_simulation(
    *,
    include_oil: bool,
    subdivision: int = PAPER_SUBDIVISION,
    material_model: str = "etopo5",
    etopo5_path: str | Path | None = None,
    backend: str = "torch",
    device: str = "auto",
    dtype: str = "float64",
    compile_step: bool = True,
    source_center_s: float = PAPER_SOURCE_CENTER_S,
) -> GeodesicFDTD:
    """Create one reference or oil-anomaly model for Figure 7."""

    anomalies = paper_anomalies(include_oil=include_oil)
    material_arguments: dict[str, Any] = {"anomalies": anomalies}
    if material_model == "etopo5":
        if etopo5_path is None:
            raise ValueError("etopo5_path is required for the ETOPO5 material")
        material_arguments["surface_elevation_sampler"] = ETOPO5Relief.from_file(
            etopo5_path
        )
    elif material_model == "natural-earth":
        material_arguments["land_classifier"] = natural_earth_land_classifier()
    else:
        raise ValueError("material_model must be 'etopo5' or 'natural-earth'")
    material = SimpsonTaflove2004Material(**material_arguments)
    source = TangentialGaussianCurrent(
        latitude_deg=PAPER_TRANSMITTER_LATITUDE_DEG,
        longitude_deg=PAPER_TRANSMITTER_LONGITUDE_DEG,
        altitude_m=0.0,
        peak_current_a=PAPER_TRANSMITTER_CURRENT_A,
        center_time_s=source_center_s,
        one_over_e_half_width_s=PAPER_ENVELOPE_ONE_OVER_E_HALF_WIDTH_S,
        carrier_frequency_hz=PAPER_CARRIER_FREQUENCY_HZ,
        azimuths_deg=(0.0, 90.0),
    )
    altitudes = radar_radial_altitudes_m()
    return GeodesicFDTD(
        config=SimulationConfig(
            subdivision=subdivision,
            radial_cells=len(altitudes) - 1,
            minimum_altitude_m=altitudes[0],
            maximum_altitude_m=altitudes[-1],
            courant_factor=0.4,
            radial_altitudes_m=altitudes,
        ),
        material=material,
        source=source,
        backend=backend,
        device=device,
        dtype=dtype,
        compile_step=compile_step,
    )


def _linear_radial_distribution(
    altitudes_m: FloatArray, altitude_m: float
) -> tuple[NDArray[np.int64], FloatArray]:
    upper = int(np.searchsorted(altitudes_m, altitude_m, side="left"))
    if upper < len(altitudes_m) and altitudes_m[upper] == altitude_m:
        return np.asarray((upper,), dtype=np.int64), np.asarray((1.0,))
    lower = upper - 1
    upper_weight = (altitude_m - altitudes_m[lower]) / (
        altitudes_m[upper] - altitudes_m[lower]
    )
    return (
        np.asarray((lower, upper), dtype=np.int64),
        np.asarray((1.0 - upper_weight, upper_weight)),
    )


def _surface_h_distributions(
    simulation: GeodesicFDTD,
) -> tuple[NDArray[np.int64], ...]:
    face = geographic_face_index(
        simulation, PAPER_OIL_LATITUDE_DEG, PAPER_OIL_LONGITUDE_DEG
    )
    hr_layers, hr_weights = _linear_radial_distribution(
        simulation.radial_midpoint_altitudes_m, 0.0
    )
    hr_faces = np.full((1, len(hr_layers)), face, dtype=np.int64)

    edges = simulation.mesh.face_edges[face]
    left = simulation.mesh.face_centers[simulation.mesh.edge_left_faces[edges]]
    right = simulation.mesh.face_centers[simulation.mesh.edge_right_faces[edges]]
    dual_directions = left - right
    radial = geographic_direction(PAPER_OIL_LATITUDE_DEG, PAPER_OIL_LONGITUDE_DEG)
    dual_directions -= (dual_directions @ radial)[:, None] * radial[None, :]
    dual_directions /= np.linalg.norm(dual_directions, axis=1, keepdims=True)
    east, north = geographic_tangent_basis(
        PAPER_OIL_LATITUDE_DEG, PAPER_OIL_LONGITUDE_DEG
    )
    samples = np.column_stack((dual_directions @ east, dual_directions @ north))
    reconstruction = samples @ np.linalg.inv(samples.T @ samples)
    ht_weights = np.stack((reconstruction[:, 0], reconstruction[:, 1]))
    surface_layer = int(np.argmin(np.abs(simulation.altitudes_m)))
    ht_edges = np.stack((edges, edges))
    ht_layers = np.full_like(ht_edges, surface_layer)
    return (
        hr_faces,
        hr_layers[None, :],
        hr_weights[None, :],
        ht_edges,
        ht_layers,
        ht_weights,
    )


def record_radar_traces(
    simulation: GeodesicFDTD,
    *,
    steps: int,
    case: str,
    synchronize_every: int = 128,
) -> RadarTraces:
    """Record interpolated surface ``Hr`` and east/north ``Htan`` traces."""

    if simulation.steps != 0:
        raise ValueError("radar recording requires a fresh simulation")
    distributions = _surface_h_distributions(simulation)
    hr, ht = simulation.record_h_observations(
        *distributions,
        steps,
        synchronize_every=synchronize_every,
    )
    time_s = np.arange(steps + 1, dtype=np.float64) * simulation.time_step_s
    source_center = (
        simulation.source.center_time_s
        if simulation.source is not None
        else PAPER_SOURCE_CENTER_S
    )
    assert source_center is not None
    return RadarTraces(
        time_s=time_s,
        hr_a_m=hr[:, 0].astype(np.float64, copy=False),
        ht_east_a_m=ht[:, 0].astype(np.float64, copy=False),
        ht_north_a_m=ht[:, 1].astype(np.float64, copy=False),
        source_center_s=source_center,
        case=case,
    )


def save_radar_traces(traces: RadarTraces, path: str | Path) -> Path:
    """Save a compact, self-describing radar trace archive."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        time_s=traces.time_s,
        hr_a_m=traces.hr_a_m,
        ht_east_a_m=traces.ht_east_a_m,
        ht_north_a_m=traces.ht_north_a_m,
        source_center_s=np.asarray(traces.source_center_s),
        case=np.asarray(traces.case),
    )
    return output


def load_radar_traces(path: str | Path) -> RadarTraces:
    """Load a radar trace archive written by :func:`save_radar_traces`."""

    with np.load(path) as values:
        return RadarTraces(
            time_s=values["time_s"].astype(np.float64),
            hr_a_m=values["hr_a_m"].astype(np.float64),
            ht_east_a_m=values["ht_east_a_m"].astype(np.float64),
            ht_north_a_m=values["ht_north_a_m"].astype(np.float64),
            source_center_s=float(values["source_center_s"]),
            case=str(values["case"]),
        )


def compute_radar_perturbation(
    reference: RadarTraces,
    anomaly: RadarTraces,
    *,
    relative_start_s: float = 0.0,
    relative_stop_s: float = PAPER_FIGURE_7_DURATION_S,
    denominator_floor_fraction: float = 1.0e-6,
) -> RadarPerturbation:
    """Compute the Figure 7 pointwise reference-normalized perturbations."""

    if reference.time_s.shape != anomaly.time_s.shape or not np.allclose(
        reference.time_s, anomaly.time_s, rtol=0.0, atol=1.0e-15
    ):
        raise ValueError("reference and anomaly traces must use the same time grid")
    relative_time = reference.time_s - reference.source_center_s
    selected = (relative_time >= relative_start_s) & (
        relative_time <= relative_stop_s
    )
    if not np.any(selected):
        raise ValueError("requested Figure 7 window is absent from the traces")

    reference_ht_vector = np.column_stack(
        (reference.ht_east_a_m[selected], reference.ht_north_a_m[selected])
    )
    _, _, principal_axes = np.linalg.svd(reference_ht_vector, full_matrices=False)
    projection = principal_axes[0]
    reference_ht = (
        projection[0] * reference.ht_east_a_m[selected]
        + projection[1] * reference.ht_north_a_m[selected]
    )
    anomaly_ht = (
        projection[0] * anomaly.ht_east_a_m[selected]
        + projection[1] * anomaly.ht_north_a_m[selected]
    )
    reference_hr = reference.hr_a_m[selected]
    anomaly_hr = anomaly.hr_a_m[selected]

    def relative_db(base: FloatArray, changed: FloatArray) -> tuple[FloatArray, NDArray[np.bool_]]:
        peak = float(np.max(np.abs(base)))
        if peak == 0.0:
            raise ValueError("reference magnetic field is identically zero")
        valid = np.abs(base) >= denominator_floor_fraction * peak
        ratio = np.full_like(base, np.nan)
        ratio[valid] = np.abs(changed[valid] - base[valid]) / np.abs(base[valid])
        ratio[valid] = np.maximum(ratio[valid], np.finfo(np.float64).tiny)
        return 20.0 * np.log10(ratio), valid

    delta_ht_db, valid_ht = relative_db(reference_ht, anomaly_ht)
    delta_hr_db, valid_hr = relative_db(reference_hr, anomaly_hr)
    return RadarPerturbation(
        time_s=relative_time[selected],
        delta_ht_db=delta_ht_db,
        delta_hr_db=delta_hr_db,
        valid_ht=valid_ht,
        valid_hr=valid_hr,
        ht_projection_east_north=projection,
    )


def radar_metrics(curves: RadarPerturbation) -> dict[str, float]:
    """Summarize Figure 7 away from reference zero-crossing singularities."""

    ht = curves.delta_ht_db[curves.valid_ht]
    hr = curves.delta_hr_db[curves.valid_hr]
    common = curves.valid_ht & curves.valid_hr
    return {
        "delta_ht_median_db": float(np.median(ht)),
        "delta_ht_fraction_below_minus_25_db": float(np.mean(ht < -25.0)),
        "delta_hr_median_db": float(np.median(hr)),
        "delta_hr_95th_percentile_db": float(np.percentile(hr, 95.0)),
        "delta_hr_maximum_db": float(np.max(hr)),
        "median_hr_over_ht_advantage_db": float(
            np.median(curves.delta_hr_db[common] - curves.delta_ht_db[common])
        ),
    }


def render_figure_5(traces: ValidationTraces, path: str | Path) -> Path:
    """Render the normalized geodesic-grid temporal response of Figure 5."""

    import matplotlib.pyplot as plt

    near = -0.5 * (traces.trace("A") + traces.trace("A′"))
    far = -0.5 * (traces.trace("B") + traces.trace("B′"))
    scale = float(max(np.max(np.abs(near)), np.max(np.abs(far))))
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(7.0, 4.5), constrained_layout=True)
    axis.plot(traces.time_s, near / scale, color="black", label="Points A and A′")
    axis.plot(
        traces.time_s,
        far / scale,
        color="0.35",
        linestyle=":",
        linewidth=2.0,
        label="Points B and B′",
    )
    axis.set(xlim=(0.0, 0.12), xlabel="Time (seconds)", ylabel="Normalized radial electric field")
    axis.legend(frameon=False)
    figure.savefig(output, dpi=180)
    plt.close(figure)
    return output


def render_figure_6(curves: AttenuationCurves, path: str | Path) -> Path:
    """Render the Figure 6 attenuation comparison."""

    import matplotlib.pyplot as plt

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    valid = curves.frequency_hz > 0.0
    figure, axis = plt.subplots(figsize=(7.0, 4.5), constrained_layout=True)
    axis.loglog(curves.frequency_hz[valid], curves.path_ab_db_per_mm[valid], color="black", label="East of source")
    axis.loglog(curves.frequency_hz[valid], curves.path_apbp_db_per_mm[valid], color="0.55", label="West of source")
    axis.loglog(curves.frequency_hz[valid], curves.benchmark_db_per_mm[valid], color="black", linestyle=":", label="Previous theoretical results")
    axis.set(xlim=(5.0, 2_000.0), ylim=(0.1, 30.0), xlabel="Frequency (Hz)", ylabel="Attenuation rate (dB/Mm)")
    axis.legend(frameon=False)
    figure.savefig(output, dpi=180)
    plt.close(figure)
    return output


def render_figure_7(curves: RadarPerturbation, path: str | Path) -> Path:
    """Render the normalized surface magnetic perturbations of Figure 7."""

    import matplotlib.pyplot as plt

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(7.0, 4.5), constrained_layout=True)
    axis.plot(curves.time_s, curves.delta_ht_db, color="black", linestyle="--", label="(a) ΔHtan")
    axis.plot(curves.time_s, curves.delta_hr_db, color="black", label="(b) ΔHr")
    axis.set(xlim=(0.0, PAPER_FIGURE_7_DURATION_S), ylim=(-100.0, 30.0), xlabel="Time (seconds)", ylabel="Surface magnetic field perturbation (dB)")
    axis.legend(frameon=False)
    figure.savefig(output, dpi=180)
    plt.close(figure)
    return output
