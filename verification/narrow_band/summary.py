"""Aggregate completed narrow-band runs and compare the level-9 extrapolation."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import numpy as np

from verification.simpson_taflove_2004.model import bannister_figure_8_guide, bannister_phase_velocity_fraction_c


def summarize(root: str | Path) -> dict[str, object]:
    root = Path(root)
    runs = []
    for level in (7, 8, 9):
        directory = root / f"level-{level}-400hz"
        data = np.load(directory / "narrow-band.npz")
        metadata = json.loads((directory / "metadata.json").read_text())
        runs.append({
            "subdivision": level,
            "attenuation_db_per_mm": float(np.mean(data["attenuation_db_per_mm"])),
            "phase_velocity_fraction_c": float(np.mean(data["phase_velocity_fraction_c"])),
            "complex_residual_rms": float(np.mean(data["complex_residual_rms"])),
            "runtime_s": metadata["elapsed_s"],
            "peak_device_memory_bytes": metadata["peak_device_memory_bytes"],
            "time_step_s": metadata["time_step_s"],
        })
    attenuation = np.asarray([run["attenuation_db_per_mm"] for run in runs])
    velocity = np.asarray([run["phase_velocity_fraction_c"] for run in runs])
    attenuation_prediction = attenuation[1] + (attenuation[1] - attenuation[0]) / 4.0
    velocity_prediction = velocity[1] + (velocity[1] - velocity[0]) / 4.0
    frequency = np.asarray((400.0,))
    result = {
        "frequency_hz": 400.0,
        "runs": runs,
        "second_order_level_9_prediction": {
            "attenuation_db_per_mm": float(attenuation_prediction),
            "phase_velocity_fraction_c": float(velocity_prediction),
        },
        "direct_minus_prediction": {
            "attenuation_db_per_mm": float(attenuation[2] - attenuation_prediction),
            "phase_velocity_fraction_c": float(velocity[2] - velocity_prediction),
        },
        "observed_order_7_to_9": {
            "attenuation": float(np.log((attenuation[0]-attenuation[1])/(attenuation[1]-attenuation[2]))/np.log(2.0)),
            "phase_velocity": float(np.log((velocity[1]-velocity[0])/(velocity[2]-velocity[1]))/np.log(2.0)),
        },
        "bannister": {
            "attenuation_db_per_mm": float(bannister_figure_8_guide(frequency)[0]),
            "phase_velocity_fraction_c": float(bannister_phase_velocity_fraction_c(frequency)[0]),
            "direct_level_9_velocity_residual_fraction_c": float(velocity[2]-bannister_phase_velocity_fraction_c(frequency)[0]),
        },
    }
    (root / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    with (root / "summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=runs[0].keys(), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(runs)
    render(result, root / "narrow-band-convergence.png")
    return result


def render(summary: dict[str, object], output: str | Path) -> Path:
    import matplotlib.pyplot as plt
    runs = summary["runs"]
    levels = np.asarray([run["subdivision"] for run in runs])
    attenuation = np.asarray([run["attenuation_db_per_mm"] for run in runs])
    velocity = np.asarray([run["phase_velocity_fraction_c"] for run in runs])
    figure, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    axes[0].plot(levels, attenuation, "o-", label="narrow-band")
    axes[0].axhline(summary["bannister"]["attenuation_db_per_mm"], color="k", ls="--", label="Bannister")
    axes[1].plot(levels, velocity, "o-", label="narrow-band")
    axes[1].axhline(summary["bannister"]["phase_velocity_fraction_c"], color="k", ls="--", label="Bannister")
    axes[0].set_ylabel("Attenuation (dB/Mm)"); axes[1].set_ylabel("Phase velocity (c)")
    for axis in axes:
        axis.set_xlabel("Subdivision"); axis.set_xticks(levels); axis.grid(True, color=".9"); axis.legend()
    output = Path(output); figure.savefig(output, dpi=180, facecolor="white"); plt.close(figure); return output


if __name__ == "__main__":
    print(json.dumps(summarize(Path("artifacts/narrow-band")), indent=2))
