import os
from pathlib import Path
import tempfile

import pytest


os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ionosphere-matplotlib")
)
matplotlib = pytest.importorskip("matplotlib")
pytest.importorskip("cartopy")
matplotlib.use("Agg")

from ionosphere_fdtd.cli import main as simulation_main
from ionosphere_fdtd.solver import GeodesicFDTD
from ionosphere_fdtd.viz_cli import main as visualization_main


CONFIG = Path(__file__).parents[1] / "configs" / "ionosphere.example.toml"


def test_documented_starter_creates_checkpoint_and_surface_plot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    assert simulation_main(["--config", str(CONFIG)]) == 0
    checkpoint = tmp_path / "artifacts/runs/demo.npz"
    assert checkpoint.exists()
    assert GeodesicFDTD.load_checkpoint(checkpoint).steps == 200

    assert visualization_main(["--config", str(CONFIG), "surface"]) == 0
    image = tmp_path / "artifacts/figures/demo-surface.png"
    assert image.stat().st_size > 0

    output = capsys.readouterr().out
    assert f"checkpoint={checkpoint.relative_to(tmp_path)} loaded_step=200" in output
