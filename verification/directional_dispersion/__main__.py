"""Measure directional numerical dispersion on the geodesic validation grid."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import time
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

import numpy as np

from ionosphere_fdtd.backends import BackendUnavailableError
from ionosphere_fdtd.solver import GeodesicFDTD

from ..common.archive import save_npz_atomic
from ..mesh_optimization.mesquite import load_optimized_mesh
from ..simpson_taflove_2004.model import (
    PAPER_DFT_SIZE,
    PAPER_MINIMUM_SIMULATION_STEPS,
    PAPER_RADIAL_CELLS,
    PAPER_TIME_STEP_S,
    create_validation_simulation,
)
from .model import (
    compute_directional_phase_velocity,
    directional_dispersion_metrics,
    record_directional_traces,
    render_directional_dispersion,
    write_directional_dispersion_csv,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subdivision", type=int, choices=range(0, 10), default=7)
    parser.add_argument("--steps", type=int)
    parser.add_argument(
        "--radial-refinement",
        type=int,
        choices=range(1, 9),
        default=1,
        help="refine radial spacing and time step by the same integer factor",
    )
    parser.add_argument(
        "--time-refinement",
        type=int,
        choices=range(1, 9),
        help="override time/DFT refinement to separate temporal dispersion",
    )
    parser.add_argument("--azimuth-step-deg", type=int, default=30)
    parser.add_argument(
        "--mesh-coordinates",
        type=Path,
        help="validated NPZ coordinates produced by verification.mesh_optimization",
    )
    parser.add_argument("--backend", choices=("numpy", "torch"), default="torch")
    parser.add_argument("--device", default="auto")
    parser.add_argument(
        "--dtype", choices=("auto", "float32", "float64"), default="float64"
    )
    parser.add_argument(
        "--torch-compile", action=argparse.BooleanOptionalAction, default=True
    )
    parser.add_argument("--torch-threads", type=int)
    parser.add_argument("--synchronize-every", type=int, default=128)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/directional-dispersion"),
    )
    return parser


def _time_refinement(args: argparse.Namespace) -> int:
    """Return the explicit temporal refinement or its coupled radial default."""

    return args.time_refinement or args.radial_refinement


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    time_refinement = _time_refinement(args)
    minimum_steps = PAPER_MINIMUM_SIMULATION_STEPS * time_refinement
    if args.steps is None:
        args.steps = minimum_steps
    if args.steps < minimum_steps:
        raise SystemExit(
            f"--steps must be at least {minimum_steps} for radial refinement "
            f"{args.radial_refinement} and time refinement {time_refinement}"
        )
    if not 1 <= args.azimuth_step_deg <= 180 or 360 % args.azimuth_step_deg:
        raise SystemExit("--azimuth-step-deg must be a divisor of 360 in [1, 180]")
    azimuths = np.arange(0.0, 360.0, args.azimuth_step_deg)
    started = time.perf_counter()
    optimized_mesh = None
    mesh_metadata = None
    if args.mesh_coordinates is not None:
        try:
            optimized_mesh, mesh_metadata = load_optimized_mesh(
                args.mesh_coordinates,
                expected_subdivision=args.subdivision,
                expected_orientation="polar",
            )
        except (OSError, KeyError, ValueError) as error:
            raise SystemExit(str(error)) from error
    try:
        simulation = create_validation_simulation(
            subdivision=args.subdivision,
            radial_cells=PAPER_RADIAL_CELLS * args.radial_refinement,
            time_step_s=PAPER_TIME_STEP_S / time_refinement,
            material_model="uniform",
            backend=args.backend,
            device=args.device,
            dtype=args.dtype,
            compile_step=args.torch_compile,
            torch_threads=args.torch_threads,
            mesh=optimized_mesh,
        )
    except (BackendUnavailableError, ImportError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(
        f"grid={simulation.mesh.n_vertices:,}x{simulation.config.radial_cells} "
        f"azimuths={len(azimuths)} backend={simulation.backend.name} "
        f"device={simulation.backend.device} dtype={simulation.backend.dtype_name} "
        f"mesh_coordinates={args.mesh_coordinates or 'generated'} "
        f"dt={simulation.time_step_s:.3e}s",
        flush=True,
    )
    traces = record_directional_traces(
        simulation,
        azimuths_deg=azimuths,
        steps=args.steps,
        synchronize_every=args.synchronize_every,
    )
    curves = compute_directional_phase_velocity(
        traces,
        azimuths,
        time_step_s=simulation.time_step_s,
        n_fft=PAPER_DFT_SIZE * time_refinement,
    )
    metrics = directional_dispersion_metrics(curves)
    elapsed_s = time.perf_counter() - started

    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = save_npz_atomic(
        args.output_dir / "directional-traces.npz",
        time_steps=traces.time_steps,
        time_s=traces.time_s,
        er_v_m=traces.er_v_m,
        labels=np.asarray(traces.labels),
        azimuth_deg=azimuths,
    )
    csv_path = write_directional_dispersion_csv(
        curves, args.output_dir / "directional-phase-velocity.csv"
    )
    figure_path = render_directional_dispersion(
        curves, args.output_dir / "directional-phase-velocity.png"
    )
    report_path = _write_report(
        args,
        simulation,
        metrics,
        curves.dft_truncations,
        elapsed_s,
        trace_path,
        csv_path,
        figure_path,
        mesh_metadata,
    )
    print(f"traces: {trace_path}")
    print(f"csv: {csv_path}")
    print(f"figure: {figure_path}")
    print(f"report: {report_path}")
    for name, value in metrics.items():
        print(f"{name}: {value:.9g}")
    print(f"elapsed: {elapsed_s:.1f}s")
    return 0


def _write_report(
    args: argparse.Namespace,
    simulation: GeodesicFDTD,
    metrics: dict[str, float],
    truncations: Mapping[str, int],
    elapsed_s: float,
    trace_path: Path,
    csv_path: Path,
    figure_path: Path,
    mesh_metadata: Mapping[str, object] | None,
) -> Path:
    time_refinement = _time_refinement(args)
    output = args.output_dir / "verification-report.md"
    metric_rows = "\n".join(
        f"| `{name}` | {value:.9g} |" for name, value in metrics.items()
    )
    cutoff_values = tuple(int(value) for value in truncations.values())
    mesh_rows = "| mesh coordinates | generated recursive grid |"
    if mesh_metadata is not None:
        mesh_rows = (
            f"| mesh coordinates | `{args.mesh_coordinates}` |\n"
            "| mesh optimizer | `Sandia Mesquite` |\n"
            f"| mesh objective | `{mesh_metadata['optimizer_reported_objective']}` |\n"
            f"| mesh coordinate SHA-256 | `{mesh_metadata['vertices_sha256']}` |"
        )
    report = f"""# Geodesic grid directional-dispersion measurement

Generated: {datetime.now().astimezone().isoformat(timespec="seconds")}

## Reproduction command

```bash
{_reproduction_command(args)}
```

## Configuration

| Item | Value |
|---|---:|
| Git revision | `{_git_revision()}` |
| subdivision | {args.subdivision} |
| surface cells | {simulation.mesh.n_vertices:,} |
{mesh_rows}
| radial cells | {simulation.config.radial_cells} |
| radial spacing | {simulation.radial_steps_m[0] / 1_000.0:g} km |
| time step | {simulation.time_step_s:.9g} s |
| radial refinement | {args.radial_refinement} |
| time refinement | {time_refinement} |
| DFT size | {PAPER_DFT_SIZE * time_refinement:,} |
| material | `uniform` |
| backend | `{simulation.backend.name}` |
| device | `{simulation.backend.device}` |
| dtype | `{simulation.backend.dtype_name}` |
| compiled | `{simulation.compiled}` |
| azimuth spacing | {args.azimuth_step_deg}° |
| azimuth count | {360 // args.azimuth_step_deg} |
| receiver arcs | 45° / 90° |
| DFT cutoffs | {min(cutoff_values):,}–{max(cutoff_values):,} samples |
| elapsed | {elapsed_s:.1f} s |

## Metrics

| Metric | Value |
|---|---:|
{metric_rows}

![Directional phase velocity]({figure_path.name})

- [Per-frequency and per-azimuth values]({csv_path.name})
- [Receiver traces]({trace_path.name})

## Interpretation

The material and ionosphere are laterally uniform, so the continuum solution is
azimuth-independent. Deviation from the azimuth mean therefore measures grid
directionality. The difference between the azimuth mean and Bannister equation
(4) measures the combined frequency dispersion of the spatial discretization
and the finite radial material model. No latitude–longitude grid is introduced;
this experiment measures the existing geodesic dual grid unchanged.
"""
    output.write_text(report, encoding="utf-8")
    return output


def _reproduction_command(args: argparse.Namespace) -> str:
    flag = "--torch-compile" if args.torch_compile else "--no-torch-compile"
    parts = [
        "uv run --extra pytorch --extra visualization python -m "
        "verification.directional_dispersion",
        f"--subdivision {args.subdivision}",
        f"--steps {args.steps}",
        f"--radial-refinement {args.radial_refinement}",
        f"--azimuth-step-deg {args.azimuth_step_deg}",
        f"--backend {shlex.quote(args.backend)}",
        f"--device {shlex.quote(args.device)}",
        f"--dtype {shlex.quote(args.dtype)}",
        flag,
        f"--synchronize-every {args.synchronize_every}",
        f"--output-dir {shlex.quote(str(args.output_dir))}",
    ]
    if args.time_refinement is not None:
        parts.append(f"--time-refinement {args.time_refinement}")
    if args.mesh_coordinates is not None:
        parts.append(f"--mesh-coordinates {shlex.quote(str(args.mesh_coordinates))}")
    if args.torch_threads is not None:
        parts.append(f"--torch-threads {args.torch_threads}")
    return f" {chr(92)}\n  ".join(parts)


def _git_revision() -> str:
    try:
        revision = subprocess.run(
            ("git", "rev-parse", "--short", "HEAD"),
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ("git", "status", "--porcelain"),
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return f"{revision}-dirty" if dirty else revision


if __name__ == "__main__":
    raise SystemExit(main())
