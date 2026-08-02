"""Run the Simpson–Taflove 2004 Figure 7/8 validation experiment."""

from __future__ import annotations

import argparse
from datetime import datetime
import shlex
import subprocess
import time
from pathlib import Path

from .backends import BackendUnavailableError
from .simpson_taflove_2004 import (
    PAPER_MINIMUM_SIMULATION_STEPS,
    PAPER_TRACE_STEPS,
    compute_attenuation,
    create_validation_simulation,
    record_validation_traces,
    render_figure_7,
    render_figure_8,
    trace_metrics,
    validation_metrics,
)
from .simpson_taflove_2004_report import (
    ValidationRunSummary,
    write_validation_report,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/simpson-taflove-2004"),
    )
    parser.add_argument("--subdivision", type=int, choices=range(0, 8), default=7)
    parser.add_argument("--steps", type=int, default=PAPER_TRACE_STEPS)
    parser.add_argument(
        "--material", choices=("natural-earth", "uniform"), default="natural-earth"
    )
    parser.add_argument("--backend", choices=("numpy", "torch"), default="torch")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--dtype", choices=("auto", "float32", "float64"), default="float32")
    parser.add_argument(
        "--torch-compile", action=argparse.BooleanOptionalAction, default=True
    )
    parser.add_argument("--torch-threads", type=int)
    parser.add_argument("--synchronize-every", type=int, default=128)
    parser.add_argument(
        "--report",
        type=Path,
        help="Markdown report path (default: OUTPUT_DIR/verification-report.md)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.steps < PAPER_MINIMUM_SIMULATION_STEPS:
        raise SystemExit(
            "--steps must be at least "
            f"{PAPER_MINIMUM_SIMULATION_STEPS} for the paper DFT windows"
        )
    started = time.perf_counter()
    try:
        simulation = create_validation_simulation(
            subdivision=args.subdivision,
            material_model=args.material,
            backend=args.backend,
            device=args.device,
            dtype=args.dtype,
            compile_step=args.torch_compile,
            torch_threads=args.torch_threads,
        )
    except (BackendUnavailableError, ImportError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(
        f"grid={simulation.mesh.n_vertices:,}x{simulation.config.radial_cells} "
        f"backend={simulation.backend.name} device={simulation.backend.device} "
        f"dtype={simulation.backend.dtype_name} material={args.material} "
        f"dt={simulation.time_step_s:.3e}s",
        flush=True,
    )
    traces = record_validation_traces(
        simulation,
        steps=args.steps,
        synchronize_every=args.synchronize_every,
    )
    figure_7 = render_figure_7(
        traces,
        args.output_dir / "simpson-taflove-2004-fig-7.png",
    )
    curves = compute_attenuation(traces)
    figure_8 = render_figure_8(
        curves,
        args.output_dir / "simpson-taflove-2004-fig-8.png",
    )
    metrics = validation_metrics(curves)
    metrics.update(trace_metrics(traces))
    elapsed_s = time.perf_counter() - started
    report = write_validation_report(
        ValidationRunSummary(
            generated_at=datetime.now().astimezone(),
            command=_reproduction_command(args),
            git_revision=_git_revision(),
            subdivision=args.subdivision,
            surface_cells=simulation.mesh.n_vertices,
            radial_cells=simulation.config.radial_cells,
            time_step_s=simulation.time_step_s,
            steps=args.steps,
            material_model=args.material,
            backend=simulation.backend.name,
            device=simulation.backend.device,
            dtype=simulation.backend.dtype_name,
            compiled=simulation.compiled,
            elapsed_s=elapsed_s,
            metrics=metrics,
            figure_7=figure_7,
            figure_8=figure_8,
        ),
        args.report or args.output_dir / "verification-report.md",
    )
    print(f"figure 7: {figure_7}")
    print(f"figure 8: {figure_8}")
    print(f"report: {report}")
    for name, value in metrics.items():
        rendered = str(value) if isinstance(value, int) else f"{value:.3f}"
        print(f"{name}: {rendered}")
    print(f"elapsed: {elapsed_s:.1f}s")
    return 0


def _reproduction_command(args: argparse.Namespace) -> str:
    compile_flag = "--torch-compile" if args.torch_compile else "--no-torch-compile"
    quote = shlex.quote
    parts = [
        "uv run --extra pytorch --extra visualization ionosphere-verify-2004",
        f"--subdivision {args.subdivision}",
        f"--steps {args.steps}",
        f"--material {quote(args.material)}",
        f"--backend {quote(args.backend)}",
        f"--device {quote(args.device)}",
        f"--dtype {quote(args.dtype)}",
        compile_flag,
        f"--synchronize-every {args.synchronize_every}",
        f"--output-dir {quote(str(args.output_dir))}",
    ]
    if args.torch_threads is not None:
        parts.append(f"--torch-threads {args.torch_threads}")
    if args.report is not None:
        parts.append(f"--report {quote(str(args.report))}")
    separator = f" {chr(92)}\n  "
    return separator.join(parts)


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
