"""Prospectively declared asymptotic TE acceptance sequence for A4."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import numpy as np

from .full_field import ConvergenceRow, _run, observed_order


def run_a4_te_asymptotic() -> tuple[ConvergenceRow, ...]:
    return tuple(
        _run(
            "A4",
            "asymptotic",
            "TE",
            subdivision,
            radial_cells,
            0,
            periods=5.0,
        )
        for subdivision, radial_cells in ((2, 16), (3, 32), (4, 64))
    )


def write_a4_te_asymptotic(output: Path) -> dict[str, object]:
    rows = run_a4_te_asymptotic()
    frequency = np.asarray([row.relative_frequency_error for row in rows])
    energy = np.asarray([row.relative_energy_variation for row in rows])
    leakage = np.asarray([row.maximum_leakage for row in rows])
    orders = {
        "frequency_order": observed_order(frequency),
        "energy_variation_order": observed_order(energy),
        "leakage_order": observed_order(leakage),
    }
    failures = []
    if orders["frequency_order"] < 1.8:
        failures.append("frequency order below 1.8")
    if orders["energy_variation_order"] < 1.5:
        failures.append("energy-variation order below 1.5")
    if orders["leakage_order"] <= 0.0:
        failures.append("leakage order is not positive")
    if max(row.maximum_pec_residual for row in rows) != 0.0:
        failures.append("PEC residual is nonzero")
    summary: dict[str, object] = {
        "protocol": "TE subdivisions/radial-cells 2/16, 3/32, 4/64; five periods",
        **orders,
        "A4_acceptance_verdict": "PASS" if not failures else "FAIL",
        "A4_acceptance_failures": failures,
    }
    names = tuple(asdict(rows[0]))
    csv_rows = [",".join(names)] + [
        ",".join(str(getattr(row, name)) for name in names) for row in rows
    ]
    (output / "a4-te-asymptotic.csv").write_text("\n".join(csv_rows) + "\n")
    (output / "a4-te-asymptotic-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    return summary
