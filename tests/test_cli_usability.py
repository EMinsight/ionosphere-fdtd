from pathlib import Path
import sys

import pytest

from ionosphere_fdtd.cli import _parser, main
from ionosphere_fdtd.cli_common import package_version


def test_help_shows_defaults_units_and_reversible_compile(capsys) -> None:
    with pytest.raises(SystemExit, match="0"):
        _parser().parse_args(["--help"])

    output = capsys.readouterr().out
    assert "--torch-compile | --no-torch-compile" in output
    assert "number of field steps to advance (default: 100)" in output
    assert "peak source current in amperes" in output
    assert "source carrier frequency in hertz" in output


def test_version_reports_distribution_version(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["ionosphere"])
    with pytest.raises(SystemExit, match="0"):
        _parser().parse_args(["--version"])

    assert capsys.readouterr().out.strip() == f"ionosphere {package_version()}"


def test_dry_run_does_not_step_or_write_checkpoint(
    tmp_path: Path, capsys
) -> None:
    checkpoint = tmp_path / "should-not-exist.npz"

    assert (
        main(
            [
                "--subdivision",
                "0",
                "--radial-cells",
                "4",
                "--steps",
                "17",
                "--checkpoint",
                str(checkpoint),
                "--dry-run",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    assert "dry-run: validated 17 requested steps" in output
    assert "no field steps or checkpoints written" in output
    assert not checkpoint.exists()
