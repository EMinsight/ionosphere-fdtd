"""Optimize a geodesic grid with Sandia Mesquite on the unit sphere."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from ionosphere_fdtd.mesh import build_geodesic_mesh
from ionosphere_fdtd.mesh_quality import mesh_quality_metrics

from .mesquite import optimize_with_mesquite, save_optimized_mesh


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subdivision", type=int, choices=range(0, 9), default=5)
    parser.add_argument(
        "--orientation", choices=("native", "polar"), default="polar"
    )
    parser.add_argument(
        "--fixed-vertices",
        choices=("none", "poles", "pentagons"),
        default="poles",
    )
    parser.add_argument(
        "--executable",
        type=Path,
        default=Path("build/mesquite/bin/ionosphere-mesquite-optimize"),
    )
    parser.add_argument("--movement-tolerance", type=float, default=1.0e-10)
    parser.add_argument("--max-iterations", type=int, default=200)
    parser.add_argument("--timeout", type=float, default=1_800.0)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    base = build_geodesic_mesh(
        subdivision=args.subdivision,
        orientation=args.orientation,
    )
    before = asdict(mesh_quality_metrics(base))
    result = optimize_with_mesquite(
        base,
        args.executable,
        orientation=args.orientation,
        fixed_vertices=args.fixed_vertices,
        movement_tolerance=args.movement_tolerance,
        max_iterations=args.max_iterations,
        timeout_s=args.timeout,
    )
    after = asdict(mesh_quality_metrics(result.mesh))
    destination = save_optimized_mesh(
        args.output,
        result,
        orientation=args.orientation,
        fixed_vertices=args.fixed_vertices,
        movement_tolerance=args.movement_tolerance,
        max_iterations=args.max_iterations,
        quality_before=before,
        quality_after=after,
    )
    print(
        json.dumps(
            {
                "output": str(destination),
                "elapsed_s": result.elapsed_s,
                "maximum_displacement_rad": result.maximum_displacement_rad,
                "fixed_vertex_count": result.fixed_vertex_count,
                "quality_before": before,
                "quality_after": after,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
