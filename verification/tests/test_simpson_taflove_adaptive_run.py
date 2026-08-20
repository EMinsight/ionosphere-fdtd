import pytest

from verification.simpson_taflove_2006.adaptive_run import _parser, main


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
