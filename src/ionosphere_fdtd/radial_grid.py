"""Deterministic 2:1-balanced static radial h-refinement."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class RadialRefinementRegion:
    """Altitude interval with a requested maximum radial cell size."""

    minimum_altitude_m: float
    maximum_altitude_m: float
    maximum_step_m: float

    def __post_init__(self) -> None:
        values = (
            self.minimum_altitude_m,
            self.maximum_altitude_m,
            self.maximum_step_m,
        )
        if not all(np.isfinite(value) for value in values):
            raise ValueError("radial refinement values must be finite")
        if self.minimum_altitude_m >= self.maximum_altitude_m:
            raise ValueError("radial refinement bounds are reversed")
        if self.maximum_step_m <= 0.0:
            raise ValueError("radial refinement step must be positive")


@dataclass(frozen=True, slots=True)
class RadialGridValidation:
    """Cell-count and 2:1-balance diagnostics for a radial grid."""

    cells: int
    minimum_step_m: float
    maximum_step_m: float
    maximum_adjacent_step_ratio: float


def build_refined_radial_grid(
    minimum_altitude_m: float,
    maximum_altitude_m: float,
    background_step_m: float,
    regions: tuple[RadialRefinementRegion, ...],
) -> tuple[float, ...]:
    """Build a closed, dyadic grid refined and balanced around fixed regions.

    Base cells are split in half until every cell intersecting a requested
    interval meets its maximum size. Coarser neighbors are then split until
    adjacent refinement levels differ by at most one.
    """

    values = (minimum_altitude_m, maximum_altitude_m, background_step_m)
    if not all(np.isfinite(value) for value in values):
        raise ValueError("radial grid bounds and spacing must be finite")
    if minimum_altitude_m >= maximum_altitude_m:
        raise ValueError("radial grid bounds are reversed")
    if background_step_m <= 0.0:
        raise ValueError("background radial step must be positive")
    selected_regions = tuple(regions)
    if not all(
        isinstance(value, RadialRefinementRegion)
        for value in selected_regions
    ):
        raise TypeError("regions must contain RadialRefinementRegion values")
    for region in selected_regions:
        if (
            region.minimum_altitude_m < minimum_altitude_m
            or region.maximum_altitude_m > maximum_altitude_m
        ):
            raise ValueError("radial refinement region lies outside the grid")

    base_cells = int(
        math.ceil(
            (maximum_altitude_m - minimum_altitude_m) / background_step_m
        )
    )
    base_nodes = np.linspace(
        minimum_altitude_m, maximum_altitude_m, base_cells + 1
    )
    cells = [
        (float(base_nodes[index]), float(base_nodes[index + 1]), 0)
        for index in range(base_cells)
    ]

    while True:
        refined = []
        changed = False
        for lower, upper, level in cells:
            target = min(
                (
                    region.maximum_step_m
                    for region in selected_regions
                    if upper > region.minimum_altitude_m
                    and lower < region.maximum_altitude_m
                ),
                default=math.inf,
            )
            if upper - lower > target * (1.0 + 1.0e-12):
                midpoint = 0.5 * (lower + upper)
                refined.extend(
                    ((lower, midpoint, level + 1), (midpoint, upper, level + 1))
                )
                changed = True
            else:
                refined.append((lower, upper, level))
        cells = refined
        if not changed:
            break

    while True:
        split_index = None
        for index, (left, right) in enumerate(zip(cells[:-1], cells[1:])):
            if abs(left[2] - right[2]) > 1:
                split_index = index if left[2] < right[2] else index + 1
                break
        if split_index is None:
            break
        lower, upper, level = cells[split_index]
        midpoint = 0.5 * (lower + upper)
        cells[split_index : split_index + 1] = [
            (lower, midpoint, level + 1),
            (midpoint, upper, level + 1),
        ]

    nodes = (cells[0][0], *(cell[1] for cell in cells))
    validate_radial_grid(nodes, maximum_adjacent_step_ratio=2.0)
    return tuple(float(value) for value in nodes)


def validate_radial_grid(
    altitudes_m: tuple[float, ...] | NDArray[np.float64],
    *,
    maximum_adjacent_step_ratio: float = 2.0,
) -> RadialGridValidation:
    """Validate finite increasing nodes and a declared adjacent-step ratio."""

    altitudes = np.asarray(altitudes_m, dtype=np.float64)
    if (
        altitudes.ndim != 1
        or len(altitudes) < 3
        or not np.all(np.isfinite(altitudes))
        or not np.all(np.diff(altitudes) > 0.0)
    ):
        raise ValueError("radial grid must contain finite increasing nodes")
    if (
        not np.isfinite(maximum_adjacent_step_ratio)
        or maximum_adjacent_step_ratio < 1.0
    ):
        raise ValueError("maximum adjacent step ratio must be at least one")
    steps = np.diff(altitudes)
    ratios = np.maximum(steps[:-1] / steps[1:], steps[1:] / steps[:-1])
    maximum_ratio = float(np.max(ratios))
    if maximum_ratio > maximum_adjacent_step_ratio * (1.0 + 1.0e-12):
        raise ValueError("radial grid violates the adjacent-step ratio")
    return RadialGridValidation(
        cells=len(steps),
        minimum_step_m=float(np.min(steps)),
        maximum_step_m=float(np.max(steps)),
        maximum_adjacent_step_ratio=maximum_ratio,
    )
