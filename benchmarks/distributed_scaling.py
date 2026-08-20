"""Measure two-GPU sharded FDTD throughput under ``torchrun``."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any

import numpy as np

from ionosphere_fdtd.distributed import (
    DistributedGeodesicFDTD,
    initialize_torchrun_process_group,
)
from ionosphere_fdtd.mesh import build_geodesic_mesh
from ionosphere_fdtd.partition import (
    partition_surface_mesh,
    validate_surface_partition,
)
from ionosphere_fdtd.solver import SimulationConfig


def summarize_distributed_timings(
    elapsed_seconds: list[float], steps: int
) -> dict[str, float]:
    """Return the steady-state result using the slow-rank durations."""

    if steps < 1 or not elapsed_seconds or any(value <= 0 for value in elapsed_seconds):
        raise ValueError("steps and elapsed durations must be positive")
    median_seconds = float(median(elapsed_seconds))
    return {
        "median_seconds": median_seconds,
        "steps_per_second": steps / median_seconds,
    }


def _write_payload(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n")
    temporary.replace(path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--subdivision", type=int, default=4)
    parser.add_argument("--radial-cells", type=int, default=40)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--warmup-steps", type=int, default=20)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--dtype", choices=("float32", "float64"), default="float32")
    parser.add_argument("--cuda-graph-chunk-size", type=int, default=0)
    parser.add_argument("--capacities", type=float, nargs=2, default=(1.0, 1.0))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if min(args.steps, args.repeats) < 1 or args.warmup_steps < 0:
        raise SystemExit("steps/repeats must be positive and warmup nonnegative")
    if args.cuda_graph_chunk_size < 0:
        raise SystemExit("--cuda-graph-chunk-size must be nonnegative")

    device = initialize_torchrun_process_group("nccl")
    import torch
    import torch.distributed as distributed

    rank = distributed.get_rank()
    measurement_group = distributed.new_group(ranks=(0, 1), backend="gloo")
    simulation = None
    try:
        mesh = build_geodesic_mesh(args.subdivision)
        partition = partition_surface_mesh(
            mesh, part_capacities=np.asarray(args.capacities, dtype=np.float64)
        )
        validation = validate_surface_partition(mesh, partition)
        simulation = DistributedGeodesicFDTD(
            partition,
            config=SimulationConfig(
                subdivision=args.subdivision,
                radial_cells=args.radial_cells,
                minimum_altitude_m=0.0,
                maximum_altitude_m=100_000.0,
                courant_factor=0.35,
            ),
            mesh=mesh,
            device=str(device),
            dtype=args.dtype,
        )
        if args.cuda_graph_chunk_size:
            simulation.enable_cuda_graph(args.cuda_graph_chunk_size)
        simulation.step(args.warmup_steps)
        torch.cuda.synchronize(device)

        elapsed_seconds = []
        for _ in range(args.repeats):
            distributed.barrier(group=measurement_group)
            started = perf_counter()
            simulation.step(args.steps)
            torch.cuda.synchronize(device)
            elapsed = torch.tensor(perf_counter() - started, dtype=torch.float64)
            distributed.all_reduce(
                elapsed, op=distributed.ReduceOp.MAX, group=measurement_group
            )
            elapsed_seconds.append(float(elapsed.item()))

        device_names: list[str | None] = [None, None]
        distributed.all_gather_object(
            device_names, torch.cuda.get_device_name(device), group=measurement_group
        )
        local_memory = torch.tensor(simulation.field_memory_bytes, dtype=torch.int64)
        total_memory = local_memory.clone()
        maximum_memory = local_memory.clone()
        distributed.all_reduce(
            total_memory, op=distributed.ReduceOp.SUM, group=measurement_group
        )
        distributed.all_reduce(
            maximum_memory, op=distributed.ReduceOp.MAX, group=measurement_group
        )
        if rank == 0:
            result = summarize_distributed_timings(elapsed_seconds, args.steps)
            _write_payload(
                args.output,
                {
                    "system": {
                        "platform": platform.platform(),
                        "python": platform.python_version(),
                        "torch": torch.__version__,
                        "cuda": torch.version.cuda,
                        "cuda_devices": device_names,
                    },
                    "configuration": {
                        "subdivision": args.subdivision,
                        "radial_cells": args.radial_cells,
                        "steps": args.steps,
                        "warmup_steps": args.warmup_steps,
                        "repeats": args.repeats,
                        "dtype": args.dtype,
                        "cuda_graph_chunk_size": args.cuda_graph_chunk_size,
                        "capacities": list(args.capacities),
                    },
                    "mesh": {
                        "vertices": mesh.n_vertices,
                        "edges": mesh.n_edges,
                        "faces": mesh.n_faces,
                        "cut_edges": validation.cut_edges,
                        "halo_values_per_radial_column": (
                            validation.halo_values_per_radial_column
                        ),
                        "relative_face_load_imbalance": (
                            validation.relative_face_load_imbalance
                        ),
                    },
                    "result": {
                        **result,
                        "slow_rank_seconds": elapsed_seconds,
                        "total_field_memory_bytes": int(total_memory.item()),
                        "maximum_rank_field_memory_bytes": int(maximum_memory.item()),
                    },
                },
            )
    finally:
        if simulation is not None:
            simulation.close()
        distributed.destroy_process_group(measurement_group)
        distributed.destroy_process_group()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
