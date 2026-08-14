from pathlib import Path

from verification.analytic_solutions.a4_asymptotic import write_a4_te_asymptotic
from verification.analytic_solutions.full_field import ConvergenceRow


def test_asymptotic_writer_applies_declared_gates(tmp_path: Path, monkeypatch) -> None:
    rows = tuple(
        ConvergenceRow(
            "A4", "asymptotic", "TE", subdivision, radial_cells,
            1.0, 1.0 + error, error, leakage, energy, 0.0, 1.0,
        )
        for subdivision, radial_cells, error, leakage, energy in (
            (2, 16, 0.16, 0.04, 0.16),
            (3, 32, 0.04, 0.02, 0.04),
            (4, 64, 0.01, 0.01, 0.01),
        )
    )
    monkeypatch.setattr(
        "verification.analytic_solutions.a4_asymptotic.run_a4_te_asymptotic",
        lambda: rows,
    )
    summary = write_a4_te_asymptotic(tmp_path)
    assert summary["A4_acceptance_verdict"] == "PASS"
