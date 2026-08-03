import numpy as np
import pytest

from ionosphere_fdtd.directional_dispersion import (
    compute_directional_phase_velocity,
    destination_direction,
    directional_dispersion_metrics,
    record_directional_traces,
)
from ionosphere_fdtd.simpson_taflove_2004 import (
    PAPER_DFT_SIZE,
    PAPER_TIME_STEP_S,
    ValidationTraces,
    create_validation_simulation,
)
from ionosphere_fdtd.sources import geographic_direction


def test_cardinal_destinations_follow_requested_great_circle_arcs() -> None:
    source = geographic_direction(0.0, -47.0)
    north = destination_direction(source, 0.0, 45.0)
    east = destination_direction(source, 90.0, 45.0)
    west = destination_direction(source, 270.0, 45.0)

    np.testing.assert_allclose(
        north, geographic_direction(45.0, -47.0), atol=1.0e-15
    )
    np.testing.assert_allclose(
        east, geographic_direction(0.0, -2.0), atol=1.0e-15
    )
    np.testing.assert_allclose(
        west, geographic_direction(0.0, -92.0), atol=1.0e-15
    )


def test_short_directional_record_has_near_far_pair_per_azimuth() -> None:
    simulation = create_validation_simulation(
        subdivision=0,
        material_model="uniform",
        backend="numpy",
        dtype="float64",
        compile_step=False,
    )
    traces = record_directional_traces(
        simulation,
        azimuths_deg=(0.0, 90.0),
        steps=3,
    )

    assert traces.er_v_m.shape == (4, 4)
    assert traces.labels == ("near-00", "far-00", "near-01", "far-01")


def test_directional_phase_velocity_recovers_isotropic_delay() -> None:
    count = 25_024
    time_steps = np.arange(count, dtype=np.int64)
    near = -np.exp(-((time_steps - 3_000) / 300.0) ** 2)
    far = -np.exp(-((time_steps - 9_000) / 300.0) ** 2)
    traces = ValidationTraces(
        time_steps=time_steps,
        time_s=time_steps * PAPER_TIME_STEP_S,
        er_v_m=np.column_stack((near, far, near, far, near, far)),
        labels=(
            "near-00",
            "far-00",
            "near-01",
            "far-01",
            "near-02",
            "far-02",
        ),
    )
    truncations = dict.fromkeys(traces.labels, count)
    azimuths = (0.0, 120.0, 240.0)

    curves = compute_directional_phase_velocity(
        traces,
        azimuths,
        truncations=truncations,
    )
    padded = compute_directional_phase_velocity(
        traces,
        azimuths,
        n_fft=2 * PAPER_DFT_SIZE,
        truncations=truncations,
    )
    expected = (
        0.25
        * np.pi
        * 6_371_000.0
        / (6_000 * PAPER_TIME_STEP_S)
        / 299_792_458.0
    )
    metrics = directional_dispersion_metrics(curves)

    np.testing.assert_allclose(curves.velocity_fraction_c, expected, rtol=1.0e-13)
    np.testing.assert_allclose(
        padded.velocity_fraction_c,
        curves.velocity_fraction_c,
        rtol=1.0e-13,
    )
    assert metrics["maximum_azimuthal_relative_spread"] == pytest.approx(0.0)
    assert metrics["azimuthal_relative_rms"] == pytest.approx(0.0)
