"""Command-line smoke runner; visualization and persistence are intentionally absent."""

from __future__ import annotations

import argparse

import numpy as np

from .materials import EarthIonosphereMaterial, SphericalAnomaly
from .solver import GeodesicFDTD, SimulationConfig
from .sources import GaussianCurrent


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--subdivision", type=int, default=2, choices=range(0, 8))
    parser.add_argument("--radial-cells", type=int, default=24)
    parser.add_argument(
        "--surface-step",
        type=float,
        help="refine radial nodes within +/-5 km of sea level to this spacing (m)",
    )
    parser.add_argument("--courant", type=float, default=0.35)
    parser.add_argument("--report-every", type=int, default=20)
    parser.add_argument("--source-current", type=float, default=1.0e6)
    parser.add_argument("--source-frequency", type=float, default=0.0)
    parser.add_argument("--source-center", type=float)
    parser.add_argument(
        "--source-width",
        type=float,
        help="Gaussian 1/e half-width in seconds",
    )
    parser.add_argument("--source-latitude", type=float, default=0.0)
    parser.add_argument("--source-longitude", type=float, default=-47.0)
    parser.add_argument(
        "--oil-anomaly",
        action="store_true",
        help="enable a small Alaska-like low-conductivity lithosphere anomaly",
    )
    parser.add_argument("--anomaly-radius-km", type=float, default=40.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.steps < 0:
        raise SystemExit("--steps must be non-negative")
    if args.report_every <= 0:
        raise SystemExit("--report-every must be positive")
    if args.surface_step is not None and args.surface_step <= 0.0:
        raise SystemExit("--surface-step must be positive")
    if args.anomaly_radius_km <= 0.0:
        raise SystemExit("--anomaly-radius-km must be positive")

    radial_altitudes: tuple[float, ...] | None = None
    if args.surface_step is not None:
        coarse = np.linspace(-100_000.0, 100_000.0, args.radial_cells + 1)
        refined = np.arange(-5_000.0, 5_000.0, args.surface_step)
        refined = np.append(refined, 5_000.0)
        radial_altitudes = tuple(np.unique(np.concatenate((coarse, refined))))

    anomalies: tuple[SphericalAnomaly, ...] = ()
    if args.oil_anomaly:
        anomalies = (
            SphericalAnomaly(
                latitude_deg=69.0,
                longitude_deg=-156.0,
                radius_m=1_000.0 * args.anomaly_radius_km,
                altitude_min_m=-2_000.0,
                altitude_max_m=-500.0,
                conductivity_factor=0.1,
            ),
        )
    simulation = GeodesicFDTD(
        config=SimulationConfig(
            subdivision=args.subdivision,
            radial_cells=args.radial_cells,
            courant_factor=args.courant,
            radial_altitudes_m=radial_altitudes,
        ),
        material=EarthIonosphereMaterial(anomalies=anomalies),
        source=GaussianCurrent(
            latitude_deg=args.source_latitude,
            longitude_deg=args.source_longitude,
            peak_current_a=args.source_current,
            carrier_frequency_hz=args.source_frequency,
            center_time_s=args.source_center,
            one_over_e_half_width_s=args.source_width,
        ),
    )
    if args.oil_anomaly:
        anomaly = anomalies[0]
        points = np.concatenate(
            (simulation.mesh.vertices, simulation.mesh.edge_midpoints()), axis=0
        )
        nearest_distance = simulation.config.earth_radius_m * float(
            np.arccos(np.clip(points @ anomaly.center, -1.0, 1.0)).min()
        )
        electric_altitudes = np.concatenate(
            (simulation.altitudes_m, simulation.radial_midpoint_altitudes_m)
        )
        resolves_depth = bool(
            np.any(
                (electric_altitudes >= anomaly.altitude_min_m)
                & (electric_altitudes <= anomaly.altitude_max_m)
            )
        )
        if nearest_distance > anomaly.radius_m or not resolves_depth:
            print(
                "warning: the requested oil anomaly is not resolved by this horizontal "
                "and/or radial grid and affects no electric-field sample; use a finer "
                "grid or a larger anomaly"
            )
    print(
        f"mesh: {simulation.mesh.n_vertices} dual cells, "
        f"{simulation.mesh.n_edges} edges, {simulation.mesh.n_faces} triangles, "
        f"{len(simulation.radial_steps_m)} radial cells"
    )
    print(
        f"dt={simulation.time_step_s:.6e} s "
        f"(conservative limit), field memory={simulation.memory_bytes / 2**20:.2f} MiB"
    )
    for start in range(0, args.steps, args.report_every):
        simulation.step(min(args.report_every, args.steps - start))
        values = simulation.diagnostics()
        print(
            f"step={values['step']:6d} t={values['time_s']:.6e} s "
            f"|Er|max={values['max_abs_er_v_m']:.6e} V/m "
            f"|H|max={max(values['max_abs_hr_a_m'], values['max_abs_ht_a_m']):.6e} A/m"
        )
    return 0
