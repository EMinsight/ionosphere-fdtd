import pytest

from verification.simpson_taflove_2006.distributed_run import _parser, main


def test_distributed_radar_parser_defaults_to_production_mesh() -> None:
    args = _parser().parse_args(
        ["--output-dir", "unused", "--etopo5-path", "ETOPO5.DAT"]
    )

    assert args.base_subdivision == 7
    assert args.target_subdivision == 10
    assert args.capacities == (1.0, 1.0)
    assert args.dtype == "float64"
    assert args.cuda_graph_chunk_size == 32
    assert args.sample_every == 32


def test_distributed_radar_rejects_invalid_levels_before_initializing_nccl() -> None:
    with pytest.raises(SystemExit, match="must exceed"):
        main(
            [
                "--output-dir",
                "unused",
                "--material",
                "natural-earth",
                "--base-subdivision",
                "2",
                "--target-subdivision",
                "2",
            ]
        )


def test_distributed_radar_rejects_negative_cuda_graph_chunk() -> None:
    with pytest.raises(SystemExit, match="must be nonnegative"):
        main(
            [
                "--output-dir",
                "unused",
                "--material",
                "natural-earth",
                "--cuda-graph-chunk-size",
                "-1",
            ]
        )


def test_distributed_radar_rejects_invalid_sample_stride() -> None:
    with pytest.raises(SystemExit, match="must be positive"):
        main(
            [
                "--output-dir",
                "unused",
                "--material",
                "natural-earth",
                "--sample-every",
                "0",
            ]
        )
