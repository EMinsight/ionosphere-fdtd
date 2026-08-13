"""Run memory-minimal narrow-band geodesic propagation measurements."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ionosphere_fdtd.sources import GaussianCurrent
from verification.common.archive import save_npz_atomic
from verification.propagation_constant.model import DEFAULT_RECEIVER_ARCS_DEG
from verification.simpson_taflove_2004.model import (
    PAPER_RADIAL_CELLS,
    PAPER_SOURCE_CENTER_STEPS,
    PAPER_SOURCE_FULL_WIDTH_STEPS,
    PAPER_TIME_STEP_S,
    create_validation_simulation,
)

from .model import fit_amplitudes, receiver_distributions, record_lockin_amplitudes


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subdivision", type=int, choices=range(0, 10), required=True)
    parser.add_argument("--frequency-hz", type=float, required=True)
    parser.add_argument("--steps", type=int)
    parser.add_argument("--time-step-s", type=float, default=PAPER_TIME_STEP_S)
    parser.add_argument("--azimuth-step-deg", type=int, default=90)
    parser.add_argument("--receiver-arcs-deg", type=float, nargs="+", default=DEFAULT_RECEIVER_ARCS_DEG)
    parser.add_argument("--backend", choices=("numpy", "torch"), default="torch")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--dtype", choices=("float32", "float64"), default="float32")
    parser.add_argument("--torch-compile", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--synchronize-every", type=int, default=1024)
    parser.add_argument("--broadband-fit", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/narrow-band"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if 360 % args.azimuth_step_deg:
        raise SystemExit("--azimuth-step-deg must divide 360")
    frequency = args.frequency_hz
    ramp_cycles = 4.0
    accumulation_cycles = 10.0
    accumulation_start_s = max(0.060, 8.0 / frequency)
    accumulation_start_step = int(np.ceil(accumulation_start_s / args.time_step_s))
    if args.steps is None:
        args.steps = accumulation_start_step + int(np.rint(accumulation_cycles / frequency / args.time_step_s))
    azimuths = np.arange(0.0, 360.0, args.azimuth_step_deg)
    started = time.perf_counter()
    simulation = create_validation_simulation(
        subdivision=args.subdivision,
        radial_cells=PAPER_RADIAL_CELLS,
        time_step_s=args.time_step_s,
        material_model="uniform",
        backend=args.backend,
        device=args.device,
        dtype=args.dtype,
        compile_step=args.torch_compile,
        compress_uniform_material_coefficients=True,
    )
    simulation.source = RampedHarmonicCurrent(
        latitude_deg=simulation.source.latitude_deg,
        longitude_deg=simulation.source.longitude_deg,
        altitude_m=simulation.source.altitude_m,
        peak_current_a=simulation.source.peak_current_a,
        vertical_element_length_m=simulation.source.vertical_element_length_m,
        carrier_frequency_hz=frequency,
        ramp_time_s=ramp_cycles / frequency,
    )
    vertices, layers, weights = receiver_distributions(simulation, azimuths, args.receiver_arcs_deg)
    _reset_peak_memory(simulation)
    amplitudes = record_lockin_amplitudes(
        simulation, frequency, vertices, layers, weights, args.steps,
        accumulation_start_step=accumulation_start_step,
        synchronize_every=args.synchronize_every,
    )
    fit = fit_amplitudes(frequency, azimuths, args.receiver_arcs_deg, amplitudes)
    elapsed = time.perf_counter() - started
    broadband = _broadband_reference(args.broadband_fit, frequency, azimuths, args.receiver_arcs_deg)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_npz_atomic(
        args.output_dir / "narrow-band.npz",
        frequency_hz=np.asarray((frequency,)), azimuth_deg=fit.azimuth_deg,
        receiver_arc_deg=fit.receiver_arc_deg, amplitudes=fit.amplitudes,
        attenuation_db_per_mm=fit.attenuation_db_per_mm,
        beta_rad_per_m=fit.beta_rad_per_m,
        phase_velocity_fraction_c=fit.phase_velocity_fraction_c,
        complex_residual_rms=fit.complex_residual_rms,
    )
    rows = ["frequency_hz,subdivision,azimuth_deg,attenuation_db_per_mm,beta_rad_per_m,phase_velocity_fraction_c,complex_residual_rms"]
    for index, azimuth in enumerate(azimuths):
        rows.append(",".join(f"{value:.12g}" for value in (frequency,args.subdivision,azimuth,fit.attenuation_db_per_mm[index],fit.beta_rad_per_m[index],fit.phase_velocity_fraction_c[index],fit.complex_residual_rms[index])))
    (args.output_dir / "narrow-band.csv").write_text("\n".join(rows) + "\n")
    metrics = {
        "mean_attenuation_db_per_mm": float(np.mean(fit.attenuation_db_per_mm)),
        "mean_phase_velocity_fraction_c": float(np.mean(fit.phase_velocity_fraction_c)),
        "mean_complex_residual_rms": float(np.mean(fit.complex_residual_rms)),
    }
    if broadband is not None:
        metrics.update({
            "broadband_attenuation_db_per_mm": float(np.mean(broadband.attenuation_db_per_mm)),
            "broadband_phase_velocity_fraction_c": float(np.mean(broadband.phase_velocity_fraction_c)),
            "attenuation_difference_from_broadband_db_per_mm": float(np.mean(fit.attenuation_db_per_mm)-np.mean(broadband.attenuation_db_per_mm)),
            "phase_velocity_difference_from_broadband_fraction_c": float(np.mean(fit.phase_velocity_fraction_c)-np.mean(broadband.phase_velocity_fraction_c)),
        })
    metadata = {
        "git_revision": _revision(), "subdivision": args.subdivision,
        "frequency_hz": frequency, "steps": args.steps, "time_step_s": args.time_step_s,
        "source": {"waveform":"sinusoid with raised-cosine ramp", "ramp_cycles":ramp_cycles},
        "accumulation_start_step": accumulation_start_step,
        "accumulation_cycles": accumulation_cycles,
        "online_lockin": "sum Er(t) exp(-j 2 pi f t); no receiver histories stored",
        "azimuth_deg": azimuths.tolist(), "receiver_arc_deg": list(args.receiver_arcs_deg),
        "backend": simulation.backend.name, "device": simulation.backend.device,
        "dtype": simulation.backend.dtype_name, "compiled": simulation.compiled,
        "field_memory_bytes": simulation.memory_bytes,
        "persistent_backend_bytes": simulation.persistent_backend_bytes,
        "peak_device_memory_bytes": _peak_memory(simulation),
        "elapsed_s": elapsed, "broadband_fit": str(args.broadband_fit) if args.broadband_fit else None,
        "metrics": metrics,
    }
    (args.output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2)); return 0


@dataclass(frozen=True, slots=True)
class RampedHarmonicCurrent(GaussianCurrent):
    ramp_time_s: float = 0.01

    def current_a(self, time_s: float, dt_s: float) -> float:
        ramp = 1.0 if time_s >= self.ramp_time_s else 0.5 * (1.0 - np.cos(np.pi * time_s / self.ramp_time_s))
        return float(self.peak_current_a * ramp * np.cos(2.0 * np.pi * self.carrier_frequency_hz * time_s))


def _broadband_reference(path: Path | None, frequency: float, azimuths: np.ndarray, arcs: list[float]):
    if path is None:
        return None
    data = np.load(path)
    source_azimuths = data["azimuth_deg"]
    source_arcs = data["receiver_arc_deg"]
    if not np.array_equal(source_arcs, np.asarray(arcs)):
        raise ValueError("broadband receiver arcs do not match")
    indices = [int(np.flatnonzero(source_azimuths == value)[0]) for value in azimuths]
    source_frequency = data["frequency_hz"]
    attenuation = np.asarray([np.interp(frequency, source_frequency, data["attenuation_db_per_mm"][index]) for index in indices])
    beta = np.asarray([np.interp(frequency, source_frequency, data["beta_rad_per_m"][index]) for index in indices])
    velocity = 2.0 * np.pi * frequency / beta / 299_792_458.0
    residual = np.asarray([np.interp(frequency, source_frequency, data["complex_residual_rms"][index]) for index in indices])
    return type("BroadbandReference", (), {"attenuation_db_per_mm": attenuation, "phase_velocity_fraction_c": velocity, "complex_residual_rms": residual})()


def _reset_peak_memory(simulation) -> None:
    if simulation.backend.name == "torch" and simulation.backend.torch_device.type == "cuda":
        simulation.backend.torch.cuda.reset_peak_memory_stats(simulation.backend.torch_device)


def _peak_memory(simulation) -> int | None:
    if simulation.backend.name == "torch" and simulation.backend.torch_device.type == "cuda":
        return int(simulation.backend.torch.cuda.max_memory_allocated(simulation.backend.torch_device))
    return None


def _revision() -> str:
    value = subprocess.run(("git","rev-parse","--short","HEAD"),check=True,capture_output=True,text=True).stdout.strip()
    dirty = subprocess.run(("git","status","--porcelain"),check=True,capture_output=True,text=True).stdout.strip()
    return value + ("-dirty" if dirty else "")


if __name__ == "__main__":
    raise SystemExit(main())
