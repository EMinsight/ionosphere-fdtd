"""Compare NumPy and PyTorch FDTD step throughput across available devices."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import platform
from pathlib import Path
import resource
from time import perf_counter

import numpy as np

from ionosphere_fdtd.backends import BackendUnavailableError
from ionosphere_fdtd.solver import GeodesicFDTD, SimulationConfig


@dataclass(frozen=True, slots=True)
class BackendResult:
    backend: str
    device: str
    dtype: str
    compiled: bool
    compile_chunk_size: int
    status: str
    initialization_seconds: float | None
    compile_seconds: float | None
    median_seconds: float | None
    steps_per_second: float | None
    field_memory_bytes: int | None
    persistent_memory_bytes: int | None
    peak_process_memory_bytes: int | None
    peak_device_memory_bytes: int | None
    reason: str | None = None


class VacuumMaterial:
    def sample(self, directions, altitudes_m, earth_radius_m):
        del earth_radius_m
        shape = (len(directions), len(altitudes_m))
        return np.zeros(shape), np.ones(shape)


def run_backend_matrix(
    *,
    subdivision: int = 2,
    radial_cells: int = 16,
    steps: int = 200,
    warmup_steps: int = 20,
    repeats: int = 3,
    dtype: str = "float32",
    torch_compile: bool = False,
    torch_compile_chunk_size: int = 8,
) -> dict[str, object]:
    if min(steps, repeats, torch_compile_chunk_size) < 1 or warmup_steps < 0:
        raise ValueError("steps/repeats must be positive and warmup nonnegative")
    configurations = (
        ("numpy", "cpu"),
        ("torch", "cpu"),
        ("torch", "cuda"),
        ("torch", "mps"),
    )
    results = [
        _measure(
            backend,
            device,
            subdivision=subdivision,
            radial_cells=radial_cells,
            steps=steps,
            warmup_steps=warmup_steps,
            repeats=repeats,
            dtype=dtype,
            compile_step=torch_compile and backend == "torch",
            compile_chunk_size=torch_compile_chunk_size,
        )
        for backend, device in configurations
    ]
    return {
        "system": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "torch": _torch_version(),
        },
        "configuration": {
            "subdivision": subdivision,
            "radial_cells": radial_cells,
            "steps": steps,
            "warmup_steps": warmup_steps,
            "repeats": repeats,
            "dtype": dtype,
            "torch_compile": torch_compile,
            "torch_compile_chunk_size": torch_compile_chunk_size,
        },
        "results": [asdict(result) for result in results],
    }


def _measure(
    backend,
    device,
    *,
    subdivision,
    radial_cells,
    steps,
    warmup_steps,
    repeats,
    dtype,
    compile_step,
    compile_chunk_size,
):
    _reset_device_peak_memory(device)
    initialized = perf_counter()
    try:
        simulation = GeodesicFDTD(
            SimulationConfig(
                subdivision=subdivision,
                radial_cells=radial_cells,
                minimum_altitude_m=0.0,
                maximum_altitude_m=100_000.0,
                courant_factor=0.35,
            ),
            material=VacuumMaterial(),
            backend=backend,
            device=device,
            dtype=dtype,
            compile_step=compile_step,
            compile_chunk_size=compile_chunk_size,
        )
        _initialize_fields(simulation)
        simulation.backend.synchronize()
    except (BackendUnavailableError, ImportError, RuntimeError) as error:
        return BackendResult(
            backend, device, dtype, compile_step, compile_chunk_size, "unavailable",
            None, None, None, None, None, None, _peak_process_memory_bytes(),
            _peak_device_memory_bytes(device), str(error),
        )
    initialization_seconds = perf_counter() - initialized
    compile_seconds = None
    if compile_step:
        compile_started = perf_counter()
        simulation.step(compile_chunk_size)
        simulation.backend.synchronize()
        compile_seconds = perf_counter() - compile_started
    if warmup_steps:
        simulation.step(warmup_steps)
        simulation.backend.synchronize()
    elapsed = []
    for _ in range(repeats):
        started = perf_counter()
        simulation.step(steps)
        simulation.backend.synchronize()
        elapsed.append(perf_counter() - started)
    median = float(np.median(elapsed))
    memory = sum(
        simulation.backend.nbytes(getattr(simulation, field))
        for field in ("er", "et", "hr", "ht")
    )
    return BackendResult(
        backend,
        simulation.backend.device,
        dtype,
        compile_step,
        compile_chunk_size,
        "ok",
        initialization_seconds,
        compile_seconds,
        median,
        steps / median,
        memory,
        simulation.persistent_backend_bytes,
        _peak_process_memory_bytes(),
        _peak_device_memory_bytes(simulation.backend.device),
    )


def _initialize_fields(simulation):
    generator = np.random.default_rng(20260814)
    for field in ("er", "et", "hr", "ht"):
        values = generator.standard_normal(getattr(simulation, field).shape) * 1.0e-6
        getattr(simulation, field)[:] = simulation.backend.asarray(values)


def _torch_version():
    try:
        import torch
    except ImportError:
        return None
    return torch.__version__


def _peak_process_memory_bytes() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if platform.system() == "Darwin" else peak * 1024)


def _reset_device_peak_memory(device: str) -> None:
    if not device.startswith("cuda"):
        return
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats(device)
    except (ImportError, RuntimeError, ValueError):
        pass


def _peak_device_memory_bytes(device: str) -> int | None:
    if not device.startswith("cuda"):
        return None
    try:
        import torch

        if torch.cuda.is_available():
            return int(torch.cuda.max_memory_allocated(device))
    except (ImportError, RuntimeError, ValueError):
        pass
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subdivision", type=int, default=2)
    parser.add_argument("--radial-cells", type=int, default=16)
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--warmup-steps", type=int, default=20)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--dtype", choices=("float32", "float64"), default="float32")
    parser.add_argument("--torch-compile", action="store_true")
    parser.add_argument("--torch-compile-chunk-size", type=int, default=8)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    payload = run_backend_matrix(
        subdivision=args.subdivision,
        radial_cells=args.radial_cells,
        steps=args.steps,
        warmup_steps=args.warmup_steps,
        repeats=args.repeats,
        dtype=args.dtype,
        torch_compile=args.torch_compile,
        torch_compile_chunk_size=args.torch_compile_chunk_size,
    )
    rendered = json.dumps(payload, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
