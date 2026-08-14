"""Time representative A0--A4 workloads without applying correctness gates."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from time import perf_counter
from typing import Callable

import numpy as np

from ionosphere_fdtd.constants import EARTH_RADIUS_M
from ionosphere_fdtd.solver import GeodesicFDTD, SimulationConfig
from verification.analytic_solutions.cavity import (
    VacuumMaterial,
    build_electric_mode,
    initialize_electric_standing_mode,
    project_electric_mode,
)
from verification.analytic_solutions.periodic import measure_periodic_mode


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    case: str
    workload: str
    repeats: int
    operations_per_repeat: int
    median_seconds: float
    minimum_seconds: float


class ConductiveMaterial:
    def sample(self, directions, altitudes_m, earth_radius_m):
        del earth_radius_m
        shape = (len(directions), len(altitudes_m))
        return np.full(shape, 1.0e-3), np.ones(shape)


def benchmark_cases() -> dict[str, tuple[str, int, Callable[[], object]]]:
    """Return isolated workloads; timings never determine scientific verdicts."""

    return {
        "A0": (
            "zero-field production workflow (setup + steps)",
            200,
            lambda: _solver_steps(None, 200),
        ),
        "A1": (
            "conductive curl-free production workflow (setup + steps)",
            200,
            lambda: _solver_steps(ConductiveMaterial(), 200, initialize=True),
        ),
        "A2": (
            "low-TM full-field workflow (setup + steps)",
            200,
            lambda: _mode_steps("TM", 0, 8, 200),
        ),
        "A3": (
            "periodic lossy auxiliary-reference workflow",
            1_000,
            lambda: measure_periodic_mode(128, steps=1_000),
        ),
        "A4": (
            "radial-TE full-field workflow (setup + steps + projection)",
            200,
            lambda: _mode_steps("TE", 0, 16, 200, project=True),
        ),
    }


def run_benchmarks(repeats: int = 3) -> tuple[BenchmarkResult, ...]:
    if repeats < 1:
        raise ValueError("repeats must be positive")
    results = []
    for case, (workload, operations, function) in benchmark_cases().items():
        elapsed = []
        for _ in range(repeats):
            started = perf_counter()
            function()
            elapsed.append(perf_counter() - started)
        results.append(
            BenchmarkResult(
                case,
                workload,
                repeats,
                operations,
                float(np.median(elapsed)),
                float(np.min(elapsed)),
            )
        )
    return tuple(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    payload = [asdict(result) for result in run_benchmarks(args.repeats)]
    rendered = json.dumps(payload, indent=2) + "\n"
    if args.output is not None:
        args.output.write_text(rendered)
    print(rendered, end="")
    return 0


def _simulation(material=None, *, radial_cells=8):
    return GeodesicFDTD(
        SimulationConfig(
            subdivision=2,
            radial_cells=radial_cells,
            minimum_altitude_m=0.0,
            maximum_altitude_m=100_000.0,
            earth_radius_m=EARTH_RADIUS_M,
            courant_factor=0.4,
            geometry_mode="full-spherical",
        ),
        material=material or VacuumMaterial(),
        dtype="float64",
    )


def _solver_steps(material, steps, *, initialize=False):
    simulation = _simulation(material)
    if initialize:
        simulation.er[:] = 1.0
    simulation.step(steps)


def _mode_steps(polarization, radial_index, radial_cells, steps, *, project=False):
    simulation = _simulation(radial_cells=radial_cells)
    mode = build_electric_mode(
        simulation, 1, polarization=polarization, radial_index=radial_index
    )
    initialize_electric_standing_mode(simulation, mode)
    simulation.step(steps)
    if project:
        project_electric_mode(simulation, mode)


if __name__ == "__main__":
    raise SystemExit(main())
