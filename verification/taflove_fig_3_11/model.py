"""Reproduce Taflove and Hagness Figure 3.11 with the FDTD solver.

The numerical parameters in this module are taken from the text immediately
preceding Figure 3.11.  The only intentional change is the source location:
Gwangju, Republic of Korea replaces the original equatorial source.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ionosphere_fdtd.solver import GeodesicFDTD, SimulationConfig
from ionosphere_fdtd.sources import (
    GWANGJU_LATITUDE_DEG,
    GWANGJU_LONGITUDE_DEG,
    GaussianCurrent,
)
from ionosphere_fdtd.visualization import (
    VisualizationDependencyError,
    _add_earth_underlay,
    _dual_polydata,
    _field_opacity_transfer,
    _pyvista_module,
)

FIGURE_3_11_TIME_STEP_S = 3.0e-6
FIGURE_3_11_RADIAL_CELLS = 40
FIGURE_3_11_COURANT_FACTOR = 0.4
FIGURE_3_11_SOURCE_CENTER_STEPS = 960
FIGURE_3_11_SOURCE_FULL_WIDTH_STEPS = 480
FIGURE_3_11_SOURCE_CURRENT_A = 1.0
FIGURE_3_11_COLOR_LIMIT_V_M = 6.0e-6

ProgressCallback = Callable[[str, int, int], None]


@dataclass(frozen=True, slots=True)
class Figure311Frames:
    """Surface radial-electric-field samples from one solver run."""

    steps: NDArray[np.int64]
    times_s: NDArray[np.float64]
    er_v_m: NDArray[np.float32]
    altitude_m: float


def create_figure_3_11_simulation(
    *,
    subdivision: int = 7,
    source_current_a: float = FIGURE_3_11_SOURCE_CURRENT_A,
    backend: str = "torch",
    device: str = "auto",
    dtype: str = "float32",
    compile_step: bool = True,
    torch_threads: int | None = None,
) -> GeodesicFDTD:
    """Create the Figure 3.11 setup with its source moved to Gwangju."""

    half_width_steps = 0.5 * FIGURE_3_11_SOURCE_FULL_WIDTH_STEPS
    return GeodesicFDTD(
        config=SimulationConfig(
            subdivision=subdivision,
            radial_cells=FIGURE_3_11_RADIAL_CELLS,
            courant_factor=FIGURE_3_11_COURANT_FACTOR,
            time_step_s=FIGURE_3_11_TIME_STEP_S,
            loss_integration="trapezoidal",
            geometry_mode="thin-shell",
        ),
        source=GaussianCurrent(
            latitude_deg=GWANGJU_LATITUDE_DEG,
            longitude_deg=GWANGJU_LONGITUDE_DEG,
            altitude_m=2_500.0,
            peak_current_a=source_current_a,
            vertical_element_length_m=5_000.0,
            center_time_s=(
                FIGURE_3_11_SOURCE_CENTER_STEPS * FIGURE_3_11_TIME_STEP_S
            ),
            one_over_e_half_width_s=(
                half_width_steps * FIGURE_3_11_TIME_STEP_S
            ),
        ),
        backend=backend,
        device=device,
        dtype=dtype,
        compile_step=compile_step,
        torch_threads=torch_threads,
    )


def record_figure_3_11_frames(
    simulation: GeodesicFDTD,
    *,
    frame_count: int = 250,
    first_step: int = 2_000,
    steps_per_frame: int = 150,
    altitude_m: float = 0.0,
    progress: ProgressCallback | None = None,
) -> Figure311Frames:
    """Advance the solver once and retain only display surface samples."""

    if frame_count < 1:
        raise ValueError("frame_count must be positive")
    if first_step < simulation.steps:
        raise ValueError("first_step precedes the current simulation step")
    if steps_per_frame < 1:
        raise ValueError("steps_per_frame must be positive")

    radial_index = int(np.argmin(np.abs(simulation.altitudes_m - altitude_m)))
    field_altitude_m = float(simulation.altitudes_m[radial_index])
    targets = first_step + steps_per_frame * np.arange(frame_count, dtype=np.int64)
    samples = np.empty(
        (frame_count, simulation.mesh.n_vertices), dtype=np.float32
    )
    for index, target in enumerate(targets):
        _advance_in_batches(simulation, int(target), batch_size=128)
        samples[index] = simulation.to_numpy(simulation.er[:, radial_index])
        if progress is not None:
            progress("simulate", index + 1, frame_count)
    return Figure311Frames(
        steps=targets,
        times_s=targets.astype(np.float64) * simulation.time_step_s,
        er_v_m=samples,
        altitude_m=field_altitude_m,
    )


def _advance_in_batches(
    simulation: GeodesicFDTD, target_step: int, *, batch_size: int
) -> None:
    """Advance to an absolute step without a large accelerator work queue."""

    while simulation.steps < target_step:
        simulation.step(min(batch_size, target_step - simulation.steps))
        _synchronize_accelerator(simulation)


def _synchronize_accelerator(simulation: GeodesicFDTD) -> None:
    simulation.backend.synchronize()


def render_figure_3_11_media(
    simulation: GeodesicFDTD,
    frames: Figure311Frames,
    *,
    video_output: str | Path,
    gif_output: str | Path,
    video_size: tuple[int, int] = (1_920, 1_080),
    gif_size: tuple[int, int] = (1_280, 640),
    video_fps: int = 25,
    gif_frame_stride: int = 2,
    color_limit: float | None = FIGURE_3_11_COLOR_LIMIT_V_M,
    field_opacity: float = 0.9,
    progress: ProgressCallback | None = None,
) -> tuple[Path, Path]:
    """Render one set of computed frames to YouTube MP4 and looping GIF."""

    if video_fps < 1:
        raise ValueError("video_fps must be positive")
    if gif_frame_stride < 1:
        raise ValueError("gif_frame_stride must be positive")
    if min(*video_size, *gif_size) < 1:
        raise ValueError("output dimensions must be positive")
    if not 0.0 < field_opacity <= 1.0:
        raise ValueError("field_opacity must be in (0, 1]")
    if frames.er_v_m.ndim != 2 or frames.er_v_m.shape[1] != simulation.mesh.n_vertices:
        raise ValueError("recorded field shape does not match the simulation mesh")

    try:
        import imageio.v2 as imageio
        from PIL import Image
    except ImportError as error:
        raise VisualizationDependencyError(
            "install the visualization extra: uv sync --extra visualization"
        ) from error

    video_path = Path(video_output)
    gif_path = Path(gif_output)
    video_path.parent.mkdir(parents=True, exist_ok=True)
    gif_path.parent.mkdir(parents=True, exist_ok=True)

    limit = color_limit or _robust_common_color_limit(frames.er_v_m)
    pv = _pyvista_module()
    radius_km = (simulation.config.earth_radius_m + frames.altitude_m) / 1.0e3
    dataset = _dual_polydata(pv, simulation.mesh, radius_km)
    scalar_name = "Er (V/m)"
    dataset.cell_data[scalar_name] = frames.er_v_m[0]

    plotter = pv.Plotter(off_screen=True, window_size=video_size)
    plotter.set_background("white")
    _add_earth_underlay(plotter, simulation, frames.altitude_m, 1.0)
    plotter.add_mesh(
        dataset,
        scalars=scalar_name,
        clim=(-limit, limit),
        cmap="RdBu_r",
        lighting=False,
        opacity=_field_opacity_transfer(field_opacity),
        scalar_bar_args={
            "title": scalar_name,
            "vertical": True,
            "position_x": 0.88,
            "position_y": 0.28,
            "width": 0.035,
            "height": 0.44,
            "n_labels": 3,
            "color": "black",
        },
        name="field-overlay",
    )

    video_writer: Any | None = None
    gif_writer: Any | None = None
    try:
        video_writer = imageio.get_writer(
            video_path,
            format="FFMPEG",
            mode="I",
            fps=video_fps,
            codec="libx264",
            quality=8,
            macro_block_size=1,
            output_params=["-movflags", "+faststart"],
        )
        gif_writer = imageio.get_writer(
            gif_path,
            mode="I",
            duration=round(1_000 * gif_frame_stride / video_fps),
            loop=0,
            palettesize=64,
            subrectangles=True,
        )
        for index, (time_s, values) in enumerate(
            zip(frames.times_s, frames.er_v_m, strict=True)
        ):
            dataset.cell_data[scalar_name] = values
            dataset.Modified()
            plotter.add_text(
                f"t = {1.0e3 * time_s:6.2f} ms   ·   step {int(frames.steps[index]):,}",
                position=(video_size[0] - 390, video_size[1] - 115),
                font_size=11,
                color="black",
                name="time",
            )
            _set_wavefront_camera(plotter, simulation, float(time_s), radius_km)
            rendered = np.asarray(plotter.screenshot(return_img=True))[..., :3]
            video_writer.append_data(rendered)
            if index % gif_frame_stride == 0:
                social = _center_crop(rendered, gif_size[0] / gif_size[1])
                resized = Image.fromarray(social).resize(
                    gif_size, resample=Image.Resampling.LANCZOS
                )
                gif_writer.append_data(np.asarray(resized))
            if progress is not None:
                progress("render", index + 1, len(frames.times_s))
    finally:
        if video_writer is not None:
            video_writer.close()
        if gif_writer is not None:
            gif_writer.close()
        plotter.close()
    return video_path, gif_path


def _robust_common_color_limit(values: NDArray[np.float32]) -> float:
    per_frame = np.asarray(
        [np.quantile(np.abs(frame), 0.997) for frame in values], dtype=np.float64
    )
    positive = per_frame[per_frame > 0.0]
    limit = float(np.quantile(positive, 0.75)) if positive.size else 0.0
    if limit == 0.0:
        limit = float(np.max(np.abs(values), initial=0.0))
    return limit if limit > 0.0 else 1.0


def _set_wavefront_camera(
    plotter: Any,
    simulation: GeodesicFDTD,
    time_s: float,
    radius_km: float,
) -> None:
    if simulation.source is None:
        plotter.camera_position = "iso"
        return
    source = simulation.source.direction()
    east = np.asarray((-source[1], source[0], 0.0), dtype=np.float64)
    east /= np.linalg.norm(east)
    center_time = simulation.source.center_time_s or 0.0
    antipode_time = center_time + np.pi * simulation.config.earth_radius_m / 299_792_458.0
    phase = np.clip((time_s - center_time) / (antipode_time - center_time), 0.0, 1.0)
    phase = phase * phase * (3.0 - 2.0 * phase)
    angle = np.pi * phase
    direction = np.cos(angle) * source + np.sin(angle) * east
    view_up = np.asarray((0.0, 0.0, 1.0))
    if abs(float(direction @ view_up)) > 0.95:
        view_up = np.asarray((0.0, 1.0, 0.0))
    plotter.camera_position = (
        3.65 * radius_km * direction,
        (0.0, 0.0, 0.0),
        view_up,
    )


def _center_crop(image: NDArray[np.uint8], target_aspect: float) -> NDArray[np.uint8]:
    height, width = image.shape[:2]
    source_aspect = width / height
    if source_aspect < target_aspect:
        target_height = max(1, round(width / target_aspect))
        start = (height - target_height) // 2
        return image[start : start + target_height]
    target_width = max(1, round(height * target_aspect))
    start = (width - target_width) // 2
    return image[:, start : start + target_width]
