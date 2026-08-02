from datetime import datetime, timezone

import numpy as np
import pytest

from ionosphere_fdtd.simpson_taflove_2004 import (
    PAPER_DFT_TRUNCATIONS,
    PAPER_RECEIVERS,
    PAPER_SOURCE_CENTER_STEPS,
    PAPER_SOURCE_FULL_WIDTH_STEPS,
    PAPER_TIME_STEP_S,
    ValidationTraces,
    compute_attenuation,
    create_validation_simulation,
    record_validation_traces,
    trace_metrics,
)
from ionosphere_fdtd.simpson_taflove_2004_report import (
    ValidationRunSummary,
    write_validation_report,
)


def test_paper_setup_uses_delta_t_pulse_parameters() -> None:
    simulation = create_validation_simulation(
        subdivision=1,
        material_model="uniform",
        backend="numpy",
        dtype="float64",
        compile_step=False,
    )

    assert simulation.time_step_s == pytest.approx(PAPER_TIME_STEP_S)
    assert simulation.config.radial_cells == 40
    assert simulation.source is not None
    assert simulation.source.latitude_deg == 0.0
    assert simulation.source.longitude_deg == -47.0
    assert simulation.source.center_time_s == pytest.approx(
        PAPER_SOURCE_CENTER_STEPS * PAPER_TIME_STEP_S
    )
    assert simulation.source.one_over_e_half_width_s == pytest.approx(
        0.5 * PAPER_SOURCE_FULL_WIDTH_STEPS * PAPER_TIME_STEP_S
    )


def test_receiver_longitudes_follow_east_and_west_quarter_arcs() -> None:
    assert [(receiver.label, receiver.longitude_deg) for receiver in PAPER_RECEIVERS] == [
        ("A", -2.0),
        ("A′", -92.0),
        ("B", 43.0),
        ("B′", -137.0),
    ]


def test_short_validation_record_has_four_interpolated_receivers() -> None:
    simulation = create_validation_simulation(
        subdivision=0,
        material_model="uniform",
        backend="numpy",
        dtype="float64",
        compile_step=False,
    )
    traces = record_validation_traces(simulation, steps=3)

    assert traces.er_v_m.shape == (4, 4)
    assert traces.time_steps.tolist() == [0, 1, 2, 3]
    assert traces.labels == ("A", "A′", "B", "B′")


def test_attenuation_recovers_known_spectral_ratio() -> None:
    count = max(PAPER_DFT_TRUNCATIONS.values()) + 1
    time_steps = np.arange(count, dtype=np.int64)
    time = time_steps * PAPER_TIME_STEP_S
    wave = -np.exp(-((time - 0.02) / 0.003) ** 2)
    values = np.column_stack((wave, wave, 0.5 * wave, 0.25 * wave))
    traces = ValidationTraces(
        time_steps=time_steps,
        time_s=time,
        er_v_m=values,
        labels=("A", "A′", "B", "B′"),
    )

    curves = compute_attenuation(traces)
    index = int(np.argmin(np.abs(curves.frequency_hz - 200.0)))
    assert curves.path_ab_db_per_mm[index] > 0.0
    assert curves.path_apbp_db_per_mm[index] > curves.path_ab_db_per_mm[index]

    metrics = trace_metrics(traces)
    assert metrics["A_negative_peak_step"] == int(np.argmin(wave))
    assert metrics["quarter_east_west_relative_rms"] == pytest.approx(0.0)


def test_markdown_report_records_configuration_results_and_artifacts(tmp_path) -> None:
    figure_7 = tmp_path / "fig-7.png"
    figure_8 = tmp_path / "fig-8.png"
    summary = ValidationRunSummary(
        generated_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
        command="uv run ionosphere-verify-2004 --subdivision 7",
        git_revision="abc1234",
        subdivision=7,
        surface_cells=163_842,
        radial_cells=40,
        time_step_s=3.0e-6,
        steps=35_000,
        material_model="natural-earth",
        backend="torch",
        device="mps",
        dtype="float32",
        compiled=True,
        elapsed_s=609.5,
        metrics={
            "path_ab_mean_absolute_error_db_per_mm": 6.146,
            "path_apbp_mean_absolute_error_db_per_mm": 5.991,
            "A_negative_peak_step": 8_800,
        },
        figure_7=figure_7,
        figure_8=figure_8,
    )

    report = write_validation_report(summary, tmp_path / "report.md")
    text = report.read_text(encoding="utf-8")

    assert "정량 검증 상태: **실패**" in text
    assert "163,842" in text
    assert "6.146 dB/Mm" in text
    assert "![Figure 7 verification](fig-7.png)" in text
    assert "uv run ionosphere-verify-2004" in text
