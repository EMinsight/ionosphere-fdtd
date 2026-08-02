"""Command-line rendering for geodesic FDTD maps, sections, traces, and 3-D views."""

from __future__ import annotations

import argparse
from pathlib import Path

from .backends import BackendUnavailableError
from .solver import GeodesicFDTD, SimulationConfig
from .sources import (
    GWANGJU_LATITUDE_DEG,
    GWANGJU_LONGITUDE_DEG,
    GaussianCurrent,
)
from .visualization import (
    Receiver,
    animate_surface_field,
    plot_mesh_3d,
    plot_radial_section,
    plot_receiver_traces,
    plot_surface_field,
    record_receiver_traces,
    run_live_surface,
    sample_radial_section,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("numpy", "torch"), default="numpy")
    parser.add_argument(
        "--device",
        default="auto",
        help="compute device: auto, cpu, mps, cuda, cuda:N, or gpu",
    )
    parser.add_argument(
        "--dtype", choices=("auto", "float32", "float64"), default="auto"
    )
    parser.add_argument(
        "--torch-compile",
        action="store_true",
        help="compile the PyTorch field step for long-running simulations",
    )
    parser.add_argument(
        "--torch-threads",
        type=int,
        help="set PyTorch CPU intra-op threads (small grids often prefer 1)",
    )
    parser.add_argument("--subdivision", type=int, default=2, choices=range(0, 8))
    parser.add_argument("--radial-cells", type=int, default=24)
    parser.add_argument("--steps", type=int, default=100, help="warm-up steps")
    parser.add_argument("--source-current", type=float, default=1.0e6)
    parser.add_argument("--source-frequency", type=float, default=0.0)
    parser.add_argument(
        "--source-latitude", type=float, default=GWANGJU_LATITUDE_DEG
    )
    parser.add_argument(
        "--source-longitude", type=float, default=GWANGJU_LONGITUDE_DEG
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    surface = subparsers.add_parser("surface", help="render a projected field map")
    surface.add_argument("--component", choices=("er", "hr"), default="er")
    surface.add_argument("--altitude-km", type=float, default=0.0)
    surface.add_argument("--projection", default="mollweide")
    surface.add_argument("--scale", choices=("linear", "symlog"), default="linear")
    surface.add_argument("--color-limit", type=float)
    surface.add_argument("--coastlines", action="store_true")
    surface.add_argument("--output", type=Path, required=True)

    section = subparsers.add_parser("section", help="render a distance-height section")
    section.add_argument(
        "--start-latitude", type=float, default=GWANGJU_LATITUDE_DEG
    )
    section.add_argument(
        "--start-longitude", type=float, default=GWANGJU_LONGITUDE_DEG
    )
    section.add_argument(
        "--end-latitude", type=float, default=-GWANGJU_LATITUDE_DEG
    )
    section.add_argument(
        "--end-longitude", type=float, default=GWANGJU_LONGITUDE_DEG - 180.0
    )
    section.add_argument("--samples", type=int, default=241)
    section.add_argument("--scale", choices=("linear", "symlog"), default="linear")
    section.add_argument("--color-limit", type=float)
    section.add_argument("--output", type=Path, required=True)

    mesh = subparsers.add_parser("mesh", help="render a 3-D geodesic surface")
    mesh.add_argument("--component", choices=("topology", "er", "hr"), default="topology")
    mesh.add_argument("--altitude-km", type=float, default=0.0)
    mesh.add_argument("--color-limit", type=float)
    mesh.add_argument(
        "--earth-texture", action=argparse.BooleanOptionalAction, default=True
    )
    mesh.add_argument("--field-opacity", type=float, default=0.82)
    mesh.add_argument("--output", type=Path, required=True)

    animation = subparsers.add_parser("animate", help="write a GIF or MP4")
    animation.add_argument("--component", choices=("er", "hr"), default="er")
    animation.add_argument("--altitude-km", type=float, default=0.0)
    animation.add_argument("--frames", type=int, default=120)
    animation.add_argument("--steps-per-frame", type=int, default=10)
    animation.add_argument("--fps", type=int, default=24)
    animation.add_argument("--color-limit", type=float)
    animation.add_argument(
        "--earth-texture", action=argparse.BooleanOptionalAction, default=True
    )
    animation.add_argument("--field-opacity", type=float, default=0.82)
    animation.add_argument(
        "--show-edges", action=argparse.BooleanOptionalAction, default=True
    )
    animation.add_argument("--output", type=Path, required=True)

    live = subparsers.add_parser(
        "live", help="advance the solver in an interactive 3-D window"
    )
    live.add_argument("--component", choices=("er", "hr"), default="er")
    live.add_argument("--altitude-km", type=float, default=0.0)
    live.add_argument("--steps-per-frame", type=int, default=10)
    live.add_argument("--fps", type=int, default=20)
    live.add_argument(
        "--frames",
        type=int,
        default=0,
        help="stop calculation after this many frames; 0 runs until the window closes",
    )
    live.add_argument("--color-limit", type=float)
    live.add_argument(
        "--earth-texture", action=argparse.BooleanOptionalAction, default=True
    )
    live.add_argument("--field-opacity", type=float, default=0.82)
    live.add_argument(
        "--show-edges", action=argparse.BooleanOptionalAction, default=True
    )

    traces = subparsers.add_parser("traces", help="render receiver time series")
    traces.add_argument("--trace-steps", type=int, default=1000)
    traces.add_argument("--sample-every", type=int, default=10)
    traces.add_argument(
        "--receiver",
        nargs=3,
        action="append",
        metavar=("LAT", "LON", "ALT_KM"),
        type=float,
    )
    traces.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.steps < 0:
        raise SystemExit("--steps must be non-negative")
    if args.torch_threads is not None and args.torch_threads < 1:
        raise SystemExit("--torch-threads must be positive")
    try:
        simulation = GeodesicFDTD(
            config=SimulationConfig(
                subdivision=args.subdivision, radial_cells=args.radial_cells
            ),
            source=GaussianCurrent(
                latitude_deg=args.source_latitude,
                longitude_deg=args.source_longitude,
                peak_current_a=args.source_current,
                carrier_frequency_hz=args.source_frequency,
            ),
            backend=args.backend,
            device=args.device,
            dtype=args.dtype,
            compile_step=args.torch_compile,
            torch_threads=args.torch_threads,
        )
    except BackendUnavailableError as error:
        raise SystemExit(str(error)) from error
    thread_text = (
        f" threads={simulation.backend.threads}"
        if simulation.backend.threads is not None
        else ""
    )
    print(
        f"backend={simulation.backend.name} device={simulation.backend.device} "
        f"dtype={simulation.backend.dtype_name}{thread_text} "
        f"compiled={simulation.compiled}"
    )
    simulation.step(args.steps)
    output = getattr(args, "output", None)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)

    if args.command == "surface":
        figure, _, _ = plot_surface_field(
            simulation,
            args.component,
            altitude_m=1.0e3 * args.altitude_km,
            projection=args.projection,
            scale=args.scale,
            color_limit=args.color_limit,
            coastlines=args.coastlines,
        )
        figure.savefig(args.output, dpi=180)
        _close_figure(figure)
    elif args.command == "section":
        radial_section = sample_radial_section(
            simulation,
            args.start_latitude,
            args.start_longitude,
            args.end_latitude,
            args.end_longitude,
            samples=args.samples,
        )
        figure, _, _ = plot_radial_section(
            radial_section, scale=args.scale, color_limit=args.color_limit
        )
        figure.savefig(args.output, dpi=180)
        _close_figure(figure)
    elif args.command == "mesh":
        plot_mesh_3d(
            simulation,
            args.component,
            altitude_m=1.0e3 * args.altitude_km,
            color_limit=args.color_limit,
            earth_texture=args.earth_texture,
            field_opacity=args.field_opacity,
            screenshot=args.output,
        )
    elif args.command == "animate":
        animate_surface_field(
            simulation,
            args.output,
            component=args.component,
            altitude_m=1.0e3 * args.altitude_km,
            frames=args.frames,
            steps_per_frame=args.steps_per_frame,
            frames_per_second=args.fps,
            color_limit=args.color_limit,
            earth_texture=args.earth_texture,
            field_opacity=args.field_opacity,
            show_edges=args.show_edges,
        )
    elif args.command == "live":
        if args.frames < 0:
            raise SystemExit("--frames must be non-negative")
        completed_frames = run_live_surface(
            simulation,
            args.component,
            altitude_m=1.0e3 * args.altitude_km,
            steps_per_frame=args.steps_per_frame,
            frames_per_second=args.fps,
            max_frames=args.frames or None,
            color_limit=args.color_limit,
            show_edges=args.show_edges,
            earth_texture=args.earth_texture,
            field_opacity=args.field_opacity,
        )
        print(
            f"completed {completed_frames} live frames; "
            f"simulation step {simulation.steps}"
        )
    else:
        receiver_specs = args.receiver or [
            (35.6762, 139.6503, 0.0),
            (21.3069, -157.8583, 0.0),
        ]
        receivers = [
            Receiver(latitude, longitude, 1.0e3 * altitude)
            for latitude, longitude, altitude in receiver_specs
        ]
        receiver_traces = record_receiver_traces(
            simulation,
            receivers,
            args.trace_steps,
            sample_every=args.sample_every,
        )
        figure, _ = plot_receiver_traces(receiver_traces)
        figure.savefig(args.output, dpi=180)
        _close_figure(figure)
    if output is not None:
        print(output)
    return 0


def _close_figure(figure: object) -> None:
    import matplotlib.pyplot as plt

    plt.close(figure)
