import numpy as np
import pytest

from ionosphere_fdtd.simpson_taflove_2006 import (
    PAPER_ENVELOPE_FWHM_S,
    PAPER_OIL_AREA_KM2,
    PAPER_OIL_CONDUCTIVITY_FACTOR,
    PAPER_OIL_MEDIAN_DEPTH_M,
    PAPER_OIL_RADIUS_M,
    PAPER_OIL_THICKNESS_M,
    RadarTraces,
    compute_radar_perturbation,
    create_radar_simulation,
    normalized_figure_5_traces,
    paper_anomalies,
    radar_field_metrics,
    radar_radial_altitudes_m,
    record_radar_traces,
)
from ionosphere_fdtd.simpson_taflove_2004 import ValidationTraces


def test_figure_5_normalization_preserves_four_individual_records() -> None:
    time = np.arange(3, dtype=np.float64)
    values = np.asarray(
        (
            (0.0, 0.0, 0.0, 0.0),
            (-2.0, -1.0, -0.5, -0.25),
            (1.0, 0.5, 0.25, 0.125),
        )
    )
    traces = ValidationTraces(
        time_steps=np.arange(3, dtype=np.int64),
        time_s=time,
        er_v_m=values,
        labels=("A", "A′", "B", "B′"),
    )

    normalized = normalized_figure_5_traces(traces)

    assert tuple(normalized) == ("A", "A′", "B", "B′")
    np.testing.assert_allclose(normalized["A"], -values[:, 0] / 2.0)
    np.testing.assert_allclose(normalized["A′"], -values[:, 1] / 2.0)
    np.testing.assert_allclose(normalized["B"], -values[:, 2] / 2.0)
    np.testing.assert_allclose(normalized["B′"], -values[:, 3] / 2.0)


def test_paper_oil_geometry_matches_area_depth_and_contrast() -> None:
    oil = paper_anomalies(include_oil=True)[1]

    assert np.pi * (PAPER_OIL_RADIUS_M / 1_000.0) ** 2 == pytest.approx(
        PAPER_OIL_AREA_KM2
    )
    assert oil.altitude_max_m - oil.altitude_min_m == pytest.approx(
        PAPER_OIL_THICKNESS_M
    )
    assert -0.5 * (oil.altitude_max_m + oil.altitude_min_m) == pytest.approx(
        PAPER_OIL_MEDIAN_DEPTH_M
    )
    assert oil.conductivity_factor == PAPER_OIL_CONDUCTIVITY_FACTOR
    assert oil.maximum_background_conductivity_s_m == 0.01


def test_radar_grid_refines_lithosphere_to_1_25_km() -> None:
    altitudes = np.asarray(radar_radial_altitudes_m())

    np.testing.assert_allclose(
        altitudes[(altitudes >= -5_000.0) & (altitudes <= 0.0)],
        (-5_000.0, -3_750.0, -2_500.0, -1_250.0, 0.0),
    )
    assert len(altitudes) - 1 == 43


def test_short_radar_run_records_three_surface_components() -> None:
    simulation = create_radar_simulation(
        include_oil=False,
        subdivision=0,
        material_model="natural-earth",
        backend="numpy",
        dtype="float64",
        compile_step=False,
    )
    traces = record_radar_traces(simulation, steps=3, case="reference")

    assert simulation.source is not None
    assert simulation.source.carrier_frequency_hz == 20.0
    assert simulation.source.peak_current_a == 300.0
    assert simulation.source.azimuths_deg == (0.0, 90.0)
    assert simulation.source.line_lengths_m == (22_500.0, 22_500.0)
    assert PAPER_ENVELOPE_FWHM_S == pytest.approx(42.5e-3)
    assert traces.hr_a_m.shape == (4,)
    assert traces.ht_east_a_m.shape == (4,)
    assert traces.ht_north_a_m.shape == (4,)


def test_radar_courant_factor_controls_automatic_time_step() -> None:
    conservative = create_radar_simulation(
        include_oil=False,
        subdivision=0,
        material_model="natural-earth",
        backend="numpy",
        dtype="float64",
        compile_step=False,
        courant_factor=0.4,
    )
    limit = create_radar_simulation(
        include_oil=False,
        subdivision=0,
        material_model="natural-earth",
        backend="numpy",
        dtype="float64",
        compile_step=False,
        courant_factor=1.0,
    )

    assert limit.time_step_s == pytest.approx(2.5 * conservative.time_step_s)


def test_pointwise_radar_normalization_has_expected_db_levels() -> None:
    time = np.linspace(0.0, 0.1, 101)
    base = np.sin(2.0 * np.pi * 20.0 * time)
    reference = RadarTraces(time, base, base, np.zeros_like(base), 0.0, "reference")
    anomaly = RadarTraces(
        time,
        11.0 * base,
        (1.0 + 10.0 ** (-30.0 / 20.0)) * base,
        np.zeros_like(base),
        0.0,
        "anomaly",
    )

    curves = compute_radar_perturbation(
        reference,
        anomaly,
        relative_stop_s=0.1,
    )

    np.testing.assert_allclose(curves.delta_hr_db[curves.valid_hr], 20.0)
    np.testing.assert_allclose(curves.delta_ht_db[curves.valid_ht], -30.0)
    metrics = radar_field_metrics(reference, anomaly, curves)
    assert metrics["delta_hr_peak_normalized_db"] == pytest.approx(20.0)
    assert metrics["delta_ht_peak_normalized_db"] == pytest.approx(-30.0)
