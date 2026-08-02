import numpy as np
import pytest

from ionosphere_fdtd.taflove_fig_3_11 import (
    FIGURE_3_11_SOURCE_CURRENT_A,
    FIGURE_3_11_SOURCE_CENTER_STEPS,
    FIGURE_3_11_SOURCE_FULL_WIDTH_STEPS,
    FIGURE_3_11_TIME_STEP_S,
    _center_crop,
    create_figure_3_11_simulation,
    record_figure_3_11_frames,
)
from ionosphere_fdtd.sources import GWANGJU_LATITUDE_DEG, GWANGJU_LONGITUDE_DEG


def test_figure_3_11_setup_preserves_paper_timing_at_gwangju() -> None:
    assert FIGURE_3_11_SOURCE_CENTER_STEPS == 960
    assert FIGURE_3_11_SOURCE_FULL_WIDTH_STEPS == 480
    simulation = create_figure_3_11_simulation(
        subdivision=1,
        backend="numpy",
        dtype="float64",
        compile_step=False,
    )

    assert simulation.config.radial_cells == 40
    assert simulation.time_step_s == pytest.approx(FIGURE_3_11_TIME_STEP_S)
    assert simulation.source is not None
    assert simulation.source.latitude_deg == pytest.approx(GWANGJU_LATITUDE_DEG)
    assert simulation.source.longitude_deg == pytest.approx(GWANGJU_LONGITUDE_DEG)
    assert simulation.source.altitude_m == pytest.approx(2_500.0)
    assert simulation.source.peak_current_a == pytest.approx(
        FIGURE_3_11_SOURCE_CURRENT_A
    )
    assert simulation.source.center_time_s == pytest.approx(
        FIGURE_3_11_SOURCE_CENTER_STEPS * FIGURE_3_11_TIME_STEP_S
    )
    assert simulation.source.one_over_e_half_width_s == pytest.approx(
        0.5 * FIGURE_3_11_SOURCE_FULL_WIDTH_STEPS * FIGURE_3_11_TIME_STEP_S
    )


def test_recording_advances_once_and_keeps_surface_only() -> None:
    simulation = create_figure_3_11_simulation(
        subdivision=0,
        backend="numpy",
        dtype="float64",
        compile_step=False,
    )
    frames = record_figure_3_11_frames(
        simulation, frame_count=3, first_step=2, steps_per_frame=4
    )

    assert frames.steps.tolist() == [2, 6, 10]
    assert frames.times_s == pytest.approx(frames.steps * simulation.time_step_s)
    assert frames.er_v_m.shape == (3, simulation.mesh.n_vertices)
    assert frames.er_v_m.dtype == np.float32
    assert simulation.steps == 10


def test_center_crop_changes_16_by_9_to_two_by_one() -> None:
    image = np.zeros((90, 160, 3), dtype=np.uint8)
    cropped = _center_crop(image, 2.0)
    assert cropped.shape == (80, 160, 3)
