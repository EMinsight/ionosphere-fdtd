"""Extract propagation constants with multi-receiver spatial regression."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import time
from pathlib import Path

import numpy as np

from ..common.archive import save_npz_atomic
from ..simpson_taflove_2004.model import (
    PAPER_DFT_SIZE,
    PAPER_MINIMUM_SIMULATION_STEPS,
    PAPER_RADIAL_CELLS,
    PAPER_TIME_STEP_S,
    create_validation_simulation,
)
from .model import (
    DEFAULT_RECEIVER_ARCS_DEG,
    fit_propagation_constants,
    record_multi_receiver_traces,
    render_fit,
    write_fit_csv,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subdivision", type=int, choices=range(0, 10), default=6)
    parser.add_argument("--steps", type=int, default=PAPER_MINIMUM_SIMULATION_STEPS)
    parser.add_argument("--azimuth-step-deg", type=int, default=30)
    parser.add_argument("--receiver-arcs-deg", type=float, nargs="+", default=DEFAULT_RECEIVER_ARCS_DEG)
    parser.add_argument("--backend", choices=("numpy", "torch"), default="torch")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--dtype", choices=("auto", "float32", "float64"), default="float64")
    parser.add_argument("--torch-compile", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--synchronize-every", type=int, default=1024)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/propagation-constant"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.steps < PAPER_MINIMUM_SIMULATION_STEPS:
        raise SystemExit(f"--steps must be at least {PAPER_MINIMUM_SIMULATION_STEPS}")
    if not 1 <= args.azimuth_step_deg <= 180 or 360 % args.azimuth_step_deg:
        raise SystemExit("--azimuth-step-deg must divide 360")
    azimuths = np.arange(0.0, 360.0, args.azimuth_step_deg)
    started = time.perf_counter()
    simulation = create_validation_simulation(
        subdivision=args.subdivision,
        radial_cells=PAPER_RADIAL_CELLS,
        time_step_s=PAPER_TIME_STEP_S,
        material_model="uniform",
        backend=args.backend,
        device=args.device,
        dtype=args.dtype,
        compile_step=args.torch_compile,
    )
    print(f"grid={simulation.mesh.n_vertices:,}x{simulation.config.radial_cells} receivers={len(azimuths) * len(args.receiver_arcs_deg)} device={simulation.backend.device}", flush=True)
    traces = record_multi_receiver_traces(
        simulation, azimuths_deg=azimuths, receiver_arcs_deg=args.receiver_arcs_deg,
        steps=args.steps, synchronize_every=args.synchronize_every,
    )
    fit = fit_propagation_constants(traces, azimuths, args.receiver_arcs_deg)
    elapsed = time.perf_counter() - started
    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = save_npz_atomic(args.output_dir / "receiver-traces.npz", time_steps=traces.time_steps, time_s=traces.time_s, er_v_m=traces.er_v_m, labels=np.asarray(traces.labels), azimuth_deg=azimuths, receiver_arc_deg=np.asarray(args.receiver_arcs_deg))
    fit_path = save_npz_atomic(
        args.output_dir / "propagation-constant-fit.npz",
        azimuth_deg=fit.azimuth_deg, receiver_arc_deg=fit.receiver_arc_deg,
        receiver_distance_m=fit.receiver_distance_m, frequency_hz=fit.frequency_hz,
        spectra=fit.spectra, attenuation_db_per_mm=fit.attenuation_db_per_mm,
        beta_rad_per_m=fit.beta_rad_per_m, phase_velocity_fraction_c=fit.phase_velocity_fraction_c,
        amplitude_residual_rms=fit.amplitude_residual_rms,
        phase_residual_rms_rad=fit.phase_residual_rms_rad,
        complex_residual_rms=fit.complex_residual_rms,
        residual_by_receiver=fit.residual_by_receiver,
        bannister_attenuation_db_per_mm=fit.bannister_attenuation_db_per_mm,
        bannister_phase_velocity_fraction_c=fit.bannister_phase_velocity_fraction_c,
    )
    csv_path = write_fit_csv(fit, args.output_dir / "propagation-constant-fit.csv")
    figure_path = render_fit(fit, args.output_dir / "propagation-constant-fit.png")
    metrics = {
        "attenuation_mae_db_per_mm": float(np.mean(np.abs(np.mean(fit.attenuation_db_per_mm, axis=0) - fit.bannister_attenuation_db_per_mm))),
        "phase_velocity_mae_fraction_c": float(np.mean(np.abs(np.mean(fit.phase_velocity_fraction_c, axis=0) - fit.bannister_phase_velocity_fraction_c))),
        "mean_complex_regression_rms": float(np.mean(fit.complex_residual_rms)),
        "high_band_complex_regression_rms": float(np.mean(fit.complex_residual_rms[:, fit.frequency_hz >= 375.0])),
    }
    metadata = {"git_revision": _git_revision(), "subdivision": args.subdivision, "surface_cells": simulation.mesh.n_vertices, "radial_cells": simulation.config.radial_cells, "radial_spacing_km": float(simulation.radial_steps_m[0] / 1000), "time_step_s": simulation.time_step_s, "steps": args.steps, "dft_size": PAPER_DFT_SIZE, "material": "uniform", "backend": simulation.backend.name, "device": simulation.backend.device, "dtype": simulation.backend.dtype_name, "compiled": simulation.compiled, "azimuth_deg": azimuths.tolist(), "receiver_arc_deg": list(args.receiver_arcs_deg), "dft_truncations": dict(fit.dft_truncations), "elapsed_s": elapsed, "metrics": metrics, "command": _command(args)}
    (args.output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"traces: {trace_path}\nfit: {fit_path}\ncsv: {csv_path}\nfigure: {figure_path}")
    print(json.dumps(metrics, indent=2)); print(f"elapsed: {elapsed:.1f}s")
    return 0


def _git_revision() -> str:
    revision = subprocess.run(("git", "rev-parse", "--short", "HEAD"), check=True, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(("git", "status", "--porcelain"), check=True, capture_output=True, text=True).stdout.strip()
    return revision + ("-dirty" if dirty else "")


def _command(args: argparse.Namespace) -> str:
    arcs = " ".join(f"{value:g}" for value in args.receiver_arcs_deg)
    return " ".join(("python -m verification.propagation_constant", f"--subdivision {args.subdivision}", f"--steps {args.steps}", f"--azimuth-step-deg {args.azimuth_step_deg}", f"--receiver-arcs-deg {arcs}", f"--backend {shlex.quote(args.backend)}", f"--device {shlex.quote(args.device)}", f"--dtype {args.dtype}", "--torch-compile" if args.torch_compile else "--no-torch-compile", f"--synchronize-every {args.synchronize_every}", f"--output-dir {shlex.quote(str(args.output_dir))}"))


if __name__ == "__main__":
    raise SystemExit(main())
