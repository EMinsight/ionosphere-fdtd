"""Generate independent horizontal-dispersion and material convergence evidence."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

import numpy as np

from .model import directional_dispersion, material_support_convergence


def _summary(result):
    near = result.pentagon_distance_rad <= np.percentile(
        result.pentagon_distance_rad, 10.0
    )
    far = result.pentagon_distance_rad >= np.percentile(
        result.pentagon_distance_rad, 90.0
    )
    return {
        "subdivision": result.subdivision,
        "frequency_hz": result.frequency_hz,
        "median_cells_per_wavelength": result.median_cells_per_wavelength,
        "phase_error_median": float(np.median(result.phase_absolute_error)),
        "phase_error_p95": float(np.percentile(result.phase_absolute_error, 95.0)),
        "phase_anisotropy_median": float(np.median(result.phase_anisotropy)),
        "phase_anisotropy_p95": float(np.percentile(result.phase_anisotropy, 95.0)),
        "group_error_median": float(
            np.median(np.abs(result.group_velocity_ratio_mean - 1.0))
        ),
        "pentagon_near_phase_error_mean": float(
            np.mean(result.phase_absolute_error[near])
        ),
        "pentagon_far_phase_error_mean": float(
            np.mean(result.phase_absolute_error[far])
        ),
    }


def _plot(results, path: Path) -> None:
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(
        2, 3, figsize=(15, 8), subplot_kw={"projection": "mollweide"}
    )
    for axis, result in zip(axes.flat, results, strict=False):
        longitude = np.arctan2(result.vertices[:, 1], result.vertices[:, 0])
        latitude = np.arcsin(np.clip(result.vertices[:, 2], -1.0, 1.0))
        image = axis.scatter(
            longitude,
            latitude,
            c=100.0 * result.phase_anisotropy,
            s=max(1.0, 24.0 / 2 ** (result.subdivision - 2)),
            cmap="viridis",
            rasterized=True,
        )
        axis.set_title(f"subdivision {result.subdivision}")
        axis.grid(True, alpha=0.25)
        axis.set_xticklabels([])
        axis.set_yticklabels([])
    for axis in axes.flat[len(results):]:
        axis.set_visible(False)
    figure.colorbar(image, ax=axes, label="Phase anisotropy (%)", shrink=0.75)
    figure.suptitle(
        f"Directional dispersion anisotropy at {results[0].frequency_hz:g} Hz"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180, facecolor="white", bbox_inches="tight")
    plt.close(figure)


def _plot_errors(results, path: Path) -> None:
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(
        len(results),
        2,
        figsize=(12, 2.6 * len(results)),
        subplot_kw={"projection": "mollweide"},
    )
    for row, result in enumerate(results):
        longitude = np.arctan2(result.vertices[:, 1], result.vertices[:, 0])
        latitude = np.arcsin(np.clip(result.vertices[:, 2], -1.0, 1.0))
        values = (
            100.0 * result.phase_absolute_error,
            100.0 * np.abs(result.group_velocity_ratio_mean - 1.0),
        )
        labels = ("Mean phase-speed error (%)", "Mean group-speed error (%)")
        for column, (metric, label) in enumerate(zip(values, labels, strict=True)):
            axis = axes[row, column]
            image = axis.scatter(
                longitude,
                latitude,
                c=metric,
                s=max(1.0, 18.0 / 2 ** (result.subdivision - 2)),
                cmap="magma",
                rasterized=True,
            )
            axis.grid(True, alpha=0.2)
            axis.set_xticklabels([])
            axis.set_yticklabels([])
            axis.set_title(f"subdivision {result.subdivision}: {label}")
            figure.colorbar(image, ax=axis, shrink=0.65)
    figure.suptitle(f"Local dispersion error at {results[0].frequency_hz:g} Hz")
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180, facecolor="white", bbox_inches="tight")
    plt.close(figure)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subdivisions", default="2,3,4,5,6")
    parser.add_argument("--frequency-hz", type=float, default=20.0)
    parser.add_argument("--headings", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plot", type=Path)
    parser.add_argument("--error-plot", type=Path)
    args = parser.parse_args(argv)
    subdivisions = tuple(int(value) for value in args.subdivisions.split(","))
    dispersion = [
        directional_dispersion(
            subdivision,
            frequency_hz=args.frequency_hz,
            headings=args.headings,
        )
        for subdivision in subdivisions
    ]
    material = [
        material_support_convergence(subdivision)
        for subdivision in subdivisions
    ]
    payload = {
        "method": {
            "dispersion": "local circumcentric DEC Laplacian symbol",
            "material": "smooth-map point versus finite-volume support average",
            "headings": args.headings,
        },
        "directional_dispersion": [_summary(result) for result in dispersion],
        "material_support_convergence": [asdict(result) for result in material],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    if args.plot is not None:
        _plot(dispersion, args.plot)
    if args.error_plot is not None:
        _plot_errors(dispersion, args.error_plot)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
