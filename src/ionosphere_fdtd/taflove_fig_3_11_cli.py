"""Generate Taflove Figure 3.11 media from an actual FDTD calculation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .backends import BackendUnavailableError
from .taflove_fig_3_11 import (
    FIGURE_3_11_COLOR_LIMIT_V_M,
    FIGURE_3_11_SOURCE_CURRENT_A,
    create_figure_3_11_simulation,
    record_figure_3_11_frames,
    render_figure_3_11_media,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/figure-3-11"))
    parser.add_argument("--subdivision", type=int, choices=range(0, 8), default=7)
    parser.add_argument("--backend", choices=("numpy", "torch"), default="torch")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--dtype", choices=("auto", "float32", "float64"), default="float32")
    parser.add_argument(
        "--torch-compile", action=argparse.BooleanOptionalAction, default=True
    )
    parser.add_argument("--torch-threads", type=int)
    parser.add_argument(
        "--source-current", type=float, default=FIGURE_3_11_SOURCE_CURRENT_A
    )
    parser.add_argument("--frames", type=int, default=250)
    parser.add_argument("--first-step", type=int, default=2_000)
    parser.add_argument("--steps-per-frame", type=int, default=150)
    parser.add_argument("--video-fps", type=int, default=25)
    parser.add_argument("--gif-frame-stride", type=int, default=2)
    parser.add_argument("--video-width", type=int, default=1_920)
    parser.add_argument("--video-height", type=int, default=1_080)
    parser.add_argument("--gif-width", type=int, default=1_280)
    parser.add_argument("--gif-height", type=int, default=640)
    parser.add_argument(
        "--color-limit", type=float, default=FIGURE_3_11_COLOR_LIMIT_V_M
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        simulation = create_figure_3_11_simulation(
            subdivision=args.subdivision,
            source_current_a=args.source_current,
            backend=args.backend,
            device=args.device,
            dtype=args.dtype,
            compile_step=args.torch_compile,
            torch_threads=args.torch_threads,
        )
    except BackendUnavailableError as error:
        raise SystemExit(str(error)) from error
    print(
        f"grid={simulation.mesh.n_vertices:,}x{simulation.config.radial_cells} "
        f"backend={simulation.backend.name} device={simulation.backend.device} "
        f"dtype={simulation.backend.dtype_name} dt={simulation.time_step_s:.3e}s"
    )
    frames = record_figure_3_11_frames(
        simulation,
        frame_count=args.frames,
        first_step=args.first_step,
        steps_per_frame=args.steps_per_frame,
        progress=_print_progress,
    )
    video = args.output_dir / "taflove-fig-3-11-gwangju-youtube.mp4"
    social = args.output_dir / "taflove-fig-3-11-gwangju-social.gif"
    render_figure_3_11_media(
        simulation,
        frames,
        video_output=video,
        gif_output=social,
        video_size=(args.video_width, args.video_height),
        gif_size=(args.gif_width, args.gif_height),
        video_fps=args.video_fps,
        gif_frame_stride=args.gif_frame_stride,
        color_limit=args.color_limit,
        progress=_print_progress,
    )
    print(f"video: {video}")
    print(f"social: {social}")
    return 0


def _print_progress(stage: str, completed: int, total: int) -> None:
    if completed == 1 or completed == total or completed % 10 == 0:
        print(f"{stage}: {completed}/{total}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
