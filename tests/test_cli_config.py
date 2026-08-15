from pathlib import Path

import pytest

from ionosphere_fdtd.cli import _parse_args as parse_simulation_args
from ionosphere_fdtd.viz_cli import _parse_args as parse_visualization_args


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "run.toml"
    path.write_text(text)
    return path


def test_simulation_toml_defaults_and_cli_precedence(tmp_path: Path) -> None:
    config = _write(
        tmp_path,
        """
[ionosphere]
steps = 1200
subdivision = 5
backend = "torch"
device = "cuda:0"
dtype = "float32"
torch_compile = true
checkpoint = "result.npz"
""",
    )

    args = parse_simulation_args(
        ["--config", str(config), "--steps", "25", "--device", "cpu"]
    )

    assert args.steps == 25
    assert args.subdivision == 5
    assert args.backend == "torch"
    assert args.device == "cpu"
    assert args.dtype == "float32"
    assert args.torch_compile is True
    assert args.checkpoint == Path("result.npz")


def test_visualization_toml_applies_global_and_command_tables(
    tmp_path: Path,
) -> None:
    config = _write(
        tmp_path,
        """
[visualization]
steps = 40
subdivision = 4
dtype = "float32"

[visualization.surface]
component = "hr"
altitude_km = 72.0
coastlines = true
output = "surface.png"
""",
    )

    args = parse_visualization_args(
        ["--config", str(config), "--steps", "3", "surface"]
    )

    assert args.steps == 3
    assert args.subdivision == 4
    assert args.dtype == "float32"
    assert args.command == "surface"
    assert args.component == "hr"
    assert args.altitude_km == 72.0
    assert args.coastlines is True
    assert args.output == Path("surface.png")


@pytest.mark.parametrize(
    "text",
    (
        "[ionosphere]\nunknown_parameter = 1\n",
        "[ionosphere]\nsubdivision = 99\n",
        "[ionosphere]\ntorch_compile = \"yes\"\n",
        "[ionosphere.extra]\nvalue = 1\n",
    ),
)
def test_invalid_simulation_toml_is_rejected(
    tmp_path: Path, text: str
) -> None:
    config = _write(tmp_path, text)

    with pytest.raises(SystemExit):
        parse_simulation_args(["--config", str(config)])


def test_missing_and_malformed_toml_are_rejected(tmp_path: Path) -> None:
    missing = tmp_path / "missing.toml"
    malformed = _write(tmp_path, "[ionosphere\nsteps = 10\n")

    with pytest.raises(SystemExit, match="cannot load TOML config"):
        parse_simulation_args(["--config", str(missing)])
    with pytest.raises(SystemExit, match="cannot load TOML config"):
        parse_simulation_args(["--config", str(malformed)])


def test_untyped_string_option_rejects_non_string_toml_value(
    tmp_path: Path,
) -> None:
    config = _write(tmp_path, "[ionosphere]\ndevice = 3\n")

    with pytest.raises(SystemExit, match="ionosphere.device must be str"):
        parse_simulation_args(["--config", str(config)])


def test_visualization_still_requires_output_when_toml_omits_it(
    tmp_path: Path,
) -> None:
    config = _write(tmp_path, "[visualization.surface]\ncomponent = \"er\"\n")

    with pytest.raises(SystemExit):
        parse_visualization_args(["--config", str(config), "surface"])


def test_explicit_receiver_replaces_toml_receiver_list(tmp_path: Path) -> None:
    config = _write(
        tmp_path,
        """
[visualization.traces]
receiver = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
output = "traces.png"
""",
    )

    args = parse_visualization_args(
        [
            "--config",
            str(config),
            "traces",
            "--receiver",
            "7",
            "8",
            "9",
        ]
    )

    assert args.receiver == [[7.0, 8.0, 9.0]]


def test_boolean_optional_action_accepts_false_from_toml(tmp_path: Path) -> None:
    config = _write(
        tmp_path,
        """
[visualization.mesh]
earth_texture = false
output = "mesh.png"
""",
    )

    args = parse_visualization_args(["--config", str(config), "mesh"])

    assert args.earth_texture is False


@pytest.mark.parametrize(
    "text, message",
    (
        (
            "[visualization.surfac]\noutput = 'surface.png'\n",
            "unknown table",
        ),
        (
            "[visualization.surface]\nunknown = 1\noutput = 'surface.png'\n",
            "unknown key",
        ),
        (
            "[visualization.traces]\nreceiver = [[1.0, 2.0]]\n"
            "output = 'traces.png'\n",
            "must contain 3 values",
        ),
    ),
)
def test_invalid_visualization_toml_is_rejected(
    tmp_path: Path, text: str, message: str
) -> None:
    config = _write(tmp_path, text)

    with pytest.raises(SystemExit, match=message):
        parse_visualization_args(["--config", str(config), "traces"])
