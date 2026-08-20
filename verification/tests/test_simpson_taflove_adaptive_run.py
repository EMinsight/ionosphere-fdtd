import pytest

import numpy as np

from verification.simpson_taflove_2006.adaptive_run import _parser, _save_pair, main
from verification.simpson_taflove_2006.model import RadarTraces


def test_adaptive_runner_defaults_to_decimated_float32_pair() -> None:
    args = _parser().parse_args(
        [
            "--output-dir",
            "unused",
            "--target-subdivision",
            "10",
            "--etopo5-path",
            "ETOPO5.DAT",
        ]
    )

    assert args.base_subdivision == 7
    assert args.dtype == "float32"
    assert args.compile_chunk_size == 32
    assert args.sample_every == 32


def test_adaptive_runner_rejects_invalid_level_before_building_mesh() -> None:
    with pytest.raises(SystemExit, match="must exceed"):
        main(
            [
                "--output-dir",
                "unused",
                "--target-subdivision",
                "7",
                "--material",
                "natural-earth",
            ]
        )


def test_adaptive_runner_rejects_invalid_chunks_before_building_mesh() -> None:
    with pytest.raises(SystemExit, match="must be positive"):
        main(
            [
                "--output-dir",
                "unused",
                "--target-subdivision",
                "9",
                "--material",
                "natural-earth",
                "--sample-every",
                "0",
            ]
        )


def test_adaptive_runner_rejects_mismatched_pair_before_saving(tmp_path) -> None:
    def traces(case: str, signature: str) -> RadarTraces:
        values = np.zeros(1)
        return RadarTraces(values, values, values, values, 0.0, case, signature)

    with pytest.raises(ValueError, match="signatures do not match"):
        _save_pair(
            {
                "reference": traces("reference", "clean"),
                "anomaly": traces("anomaly", "dirty"),
            },
            tmp_path,
            9,
        )
    assert not list(tmp_path.iterdir())
