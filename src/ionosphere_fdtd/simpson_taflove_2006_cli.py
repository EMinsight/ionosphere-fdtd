"""Run the Simpson--Taflove 2006 Figure 5--7 verification experiments."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

from .simpson_taflove_2004 import ValidationTraces, compute_attenuation
from .simpson_taflove_2006 import (
    PAPER_FIGURE_7_DURATION_S,
    PAPER_SOURCE_CENTER_S,
    compute_radar_perturbation,
    create_radar_simulation,
    load_radar_traces,
    radar_field_metrics,
    radar_metrics,
    record_radar_traces,
    render_figure_5,
    render_figure_6,
    render_figure_7,
    save_radar_traces,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    fig56 = commands.add_parser("figures-5-6")
    fig56.add_argument("--traces", type=Path, required=True)
    fig56.add_argument("--output-dir", type=Path, required=True)

    radar = commands.add_parser("radar-run")
    radar.add_argument("--case", choices=("reference", "anomaly"), required=True)
    radar.add_argument("--output", type=Path, required=True)
    radar.add_argument("--subdivision", type=int, choices=range(0, 8), default=7)
    radar.add_argument(
        "--material", choices=("etopo5", "natural-earth"), default="etopo5"
    )
    radar.add_argument("--etopo5-path", type=Path)
    radar.add_argument(
        "--tangential-interface",
        choices=("point", "fractional"),
        default="point",
    )
    radar.add_argument(
        "--tangential-support",
        choices=("point", "edge-diamond"),
        default="point",
    )
    radar.add_argument("--backend", choices=("numpy", "torch"), default="torch")
    radar.add_argument("--device", default="auto")
    radar.add_argument("--dtype", choices=("float32", "float64"), default="float64")
    radar.add_argument(
        "--torch-compile", action=argparse.BooleanOptionalAction, default=True
    )
    radar.add_argument("--source-center", type=float, default=PAPER_SOURCE_CENTER_S)
    radar.add_argument("--source-altitude-m", type=float, default=0.0)
    radar.add_argument(
        "--source-basis",
        choices=("both", "north", "east", "difference"),
        default="both",
    )
    radar.add_argument("--courant", type=float, default=0.4)
    radar.add_argument(
        "--source-edge-assignment",
        choices=("projected", "nearest"),
        default="projected",
    )
    radar.add_argument(
        "--stop-after-center", type=float, default=PAPER_FIGURE_7_DURATION_S
    )
    radar.add_argument("--synchronize-every", type=int, default=256)
    radar.add_argument(
        "--receiver-support",
        choices=("face", "local-linear"),
        default="local-linear",
    )

    analyze = commands.add_parser("analyze-radar")
    analyze.add_argument("--reference", type=Path, required=True)
    analyze.add_argument("--anomaly", type=Path, required=True)
    analyze.add_argument("--figure", type=Path, required=True)
    return parser


def _load_validation_traces(path: Path) -> ValidationTraces:
    with np.load(path) as values:
        return ValidationTraces(
            time_steps=values["time_steps"].astype(np.int64),
            time_s=values["time_s"].astype(np.float64),
            er_v_m=values["er_v_m"].astype(np.float64),
            labels=tuple(str(value) for value in values["labels"]),
        )


def _run_figures_5_6(args: argparse.Namespace) -> int:
    traces = _load_validation_traces(args.traces)
    curves = compute_attenuation(traces)
    figure_5 = render_figure_5(traces, args.output_dir / "figure-5.png")
    figure_6 = render_figure_6(curves, args.output_dir / "figure-6.png")
    print(f"figure_5={figure_5}")
    print(f"figure_6={figure_6}")
    return 0


def _run_radar(args: argparse.Namespace) -> int:
    if args.stop_after_center <= 0.0:
        raise SystemExit("--stop-after-center must be positive")
    if args.material == "etopo5" and args.etopo5_path is None:
        raise SystemExit("--etopo5-path is required with --material etopo5")
    source_azimuths = {
        "both": (0.0, 90.0),
        "north": (0.0,),
        "east": (90.0,),
        "difference": (0.0, 270.0),
    }[args.source_basis]
    simulation = create_radar_simulation(
        include_oil=args.case == "anomaly",
        subdivision=args.subdivision,
        material_model=args.material,
        etopo5_path=args.etopo5_path,
        backend=args.backend,
        device=args.device,
        dtype=args.dtype,
        compile_step=args.torch_compile,
        source_center_s=args.source_center,
        courant_factor=args.courant,
        source_edge_assignment=args.source_edge_assignment,
        tangential_interface_mode=args.tangential_interface,
        tangential_material_support=args.tangential_support,
        source_altitude_m=args.source_altitude_m,
        source_azimuths_deg=source_azimuths,
    )
    steps = int(
        np.ceil((args.source_center + args.stop_after_center) / simulation.time_step_s)
    )
    print(
        f"case={args.case} grid={simulation.mesh.n_vertices:,}x"
        f"{len(simulation.radial_steps_m)} backend={simulation.backend.name} "
        f"device={simulation.backend.device} dtype={simulation.backend.dtype_name} "
        f"interface={args.tangential_interface} "
        f"support={args.tangential_support} "
        f"source={args.source_basis}@{args.source_altitude_m:g}m "
        f"receiver={args.receiver_support} "
        f"dt={simulation.time_step_s:.9e}s steps={steps:,}",
        flush=True,
    )
    started = time.perf_counter()
    traces = record_radar_traces(
        simulation,
        steps=steps,
        case=args.case,
        synchronize_every=args.synchronize_every,
        receiver_support=args.receiver_support,
    )
    output = save_radar_traces(traces, args.output)
    print(f"elapsed_s={time.perf_counter() - started:.3f} output={output}", flush=True)
    return 0


def _analyze_radar(args: argparse.Namespace) -> int:
    reference = load_radar_traces(args.reference)
    anomaly = load_radar_traces(args.anomaly)
    curves = compute_radar_perturbation(reference, anomaly)
    figure = render_figure_7(curves, args.figure)
    print(f"figure={figure}")
    metrics = radar_metrics(curves)
    metrics.update(radar_field_metrics(reference, anomaly, curves))
    for name, value in metrics.items():
        print(f"{name}={value:.9g}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "figures-5-6":
        return _run_figures_5_6(args)
    if args.command == "radar-run":
        return _run_radar(args)
    return _analyze_radar(args)


if __name__ == "__main__":
    raise SystemExit(main())
