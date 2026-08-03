import numpy as np
import pytest

from ionosphere_fdtd.materials import EarthIonosphereMaterial
from ionosphere_fdtd.solver import GeodesicFDTD, SimulationConfig
from ionosphere_fdtd.sources import GaussianCurrent, TangentialGaussianCurrent


def small_config(**changes: object) -> SimulationConfig:
    values = dict(subdivision=1, radial_cells=6, courant_factor=0.25)
    values.update(changes)
    return SimulationConfig(**values)


def test_zero_fields_are_stationary() -> None:
    simulation = GeodesicFDTD(config=small_config())
    simulation.step(3)
    assert not np.any(simulation.er)
    assert not np.any(simulation.et)
    assert not np.any(simulation.hr)
    assert not np.any(simulation.ht)


def test_gaussian_source_launches_finite_fields() -> None:
    simulation = GeodesicFDTD(
        config=small_config(), source=GaussianCurrent(peak_current_a=1.0e6)
    )
    simulation.step(80)
    assert np.isfinite(simulation.er).all()
    assert np.isfinite(simulation.ht).all()
    assert np.max(np.abs(simulation.er)) > 0.0
    assert np.max(np.abs(simulation.ht)) > 0.0
    assert simulation.time_s == pytest.approx(80 * simulation.time_step_s)


def test_default_source_is_located_in_gwangju() -> None:
    source = GaussianCurrent()
    assert source.latitude_deg == pytest.approx(35.1595)
    assert source.longitude_deg == pytest.approx(126.8526)


def test_source_distribution_preserves_exact_direction() -> None:
    source = GaussianCurrent()
    simulation = GeodesicFDTD(config=small_config(), source=source)
    vertices, _, weights = source.distribution(simulation)
    represented = weights @ simulation.mesh.vertices[vertices]
    represented /= np.linalg.norm(represented)
    assert weights.sum() == pytest.approx(1.0)
    assert np.all(weights >= 0.0)
    assert represented @ source.direction() == pytest.approx(1.0)


def test_source_distribution_preserves_exact_staggered_altitude() -> None:
    source = GaussianCurrent(altitude_m=2_500.0)
    simulation = GeodesicFDTD(config=small_config(), source=source)
    vertices, layers, weights = source.staggered_distribution(simulation)
    represented_altitude = weights @ simulation.altitudes_m[layers]
    horizontal_weights = np.asarray(
        [weights[vertices == vertex].sum() for vertex in np.unique(vertices)]
    )

    assert represented_altitude == pytest.approx(source.altitude_m)
    assert weights.sum() == pytest.approx(1.0)
    assert horizontal_weights.sum() == pytest.approx(1.0)
    assert len(np.unique(layers)) == 2


def test_staggered_source_update_preserves_total_current() -> None:
    source = GaussianCurrent(altitude_m=2_500.0)
    simulation = GeodesicFDTD(config=small_config(), source=source)
    vertices, layers, expected_weights = source.staggered_distribution(simulation)

    simulation._update_electric_fields(1.0)
    represented_currents = (
        -simulation.er[vertices, layers]
        * simulation._dual_areas_tm[vertices, layers]
        / simulation._cb_er[vertices, layers]
    )

    np.testing.assert_allclose(represented_currents, expected_weights)
    assert represented_currents.sum() == pytest.approx(1.0)


def test_tangential_source_update_uses_dual_face_current_density() -> None:
    source = TangentialGaussianCurrent(
        altitude_m=0.0,
        peak_current_a=1.0,
        azimuths_deg=(0.0, 90.0),
        line_lengths_m=(22_500.0, 22_500.0),
    )
    simulation = GeodesicFDTD(config=small_config(), source=source)
    edges, layers, expected_weights = source.edge_distribution(simulation)

    simulation._update_electric_fields(1.0)
    represented_currents = (
        -simulation.et[edges, layers]
        * simulation._dual_face_areas_te[edges, layers]
        / simulation._cb_et[edges, layers]
    )

    np.testing.assert_allclose(represented_currents, expected_weights)


def test_tangential_source_rejects_mismatched_ground_lines() -> None:
    with pytest.raises(ValueError, match="line_lengths_m must match"):
        TangentialGaussianCurrent(
            azimuths_deg=(0.0, 90.0),
            line_lengths_m=(22_500.0,),
        )


def test_nearest_edge_source_uses_at_most_one_edge_per_ground_line() -> None:
    source = TangentialGaussianCurrent(
        azimuths_deg=(0.0, 90.0),
        line_lengths_m=(22_500.0, 22_500.0),
        edge_assignment="nearest",
    )
    simulation = GeodesicFDTD(config=small_config(), source=source)
    _, _, weights = source.edge_distribution(simulation)

    assert np.count_nonzero(weights) <= 2


def test_requested_unstable_time_step_is_rejected() -> None:
    baseline = GeodesicFDTD(config=small_config())
    with pytest.raises(ValueError, match="exceeds conservative limit"):
        GeodesicFDTD(
            config=small_config(time_step_s=2.0 * baseline.maximum_stable_time_step_s)
        )


def test_simulation_config_rejects_unknown_mesh_orientation() -> None:
    with pytest.raises(ValueError, match="mesh_orientation"):
        small_config(mesh_orientation="sideways")


def test_nonuniform_radial_grid_advances() -> None:
    altitudes = (
        -100_000.0,
        -5_000.0,
        -1_250.0,
        0.0,
        1_250.0,
        5_000.0,
        100_000.0,
    )
    simulation = GeodesicFDTD(
        config=small_config(radial_altitudes_m=altitudes),
        source=GaussianCurrent(),
    )
    simulation.step(5)
    assert np.allclose(simulation.altitudes_m, altitudes)
    assert np.isfinite(simulation.er).all()


def test_modulated_source_uses_frequency_scaled_default_envelope() -> None:
    source = GaussianCurrent(carrier_frequency_hz=20.0, peak_current_a=1.0)
    assert source.current_a(0.1, 1.0e-6) == pytest.approx(1.0)


def test_loss_coefficient_damps_uncoupled_radial_field() -> None:
    material = EarthIonosphereMaterial(lithosphere_conductivity_s_m=1.0e-2)
    simulation = GeodesicFDTD(config=small_config(), material=material)
    simulation.er[:, 0] = 1.0
    expected = simulation._ca_er[:, 0].copy()
    simulation.step()
    assert np.allclose(simulation.er[:, 0], expected)


def test_backend_native_observation_recording_includes_initial_state() -> None:
    simulation = GeodesicFDTD(
        config=small_config(), source=GaussianCurrent(peak_current_a=1.0e6)
    )
    traces = simulation.record_er_observations(
        np.asarray(((0, 1, 2),), dtype=np.int64),
        np.asarray((3,), dtype=np.int64),
        np.asarray(((0.2, 0.3, 0.5),)),
        5,
        synchronize_every=2,
    )

    assert traces.shape == (6, 1)
    assert traces[0, 0] == 0.0
    assert simulation.steps == 5
    assert np.isfinite(traces).all()


def test_backend_native_h_recording_includes_initial_state() -> None:
    simulation = GeodesicFDTD(
        config=small_config(), source=GaussianCurrent(peak_current_a=1.0e6)
    )
    hr, ht = simulation.record_h_observations(
        np.asarray(((0,),), dtype=np.int64),
        np.asarray(((2,),), dtype=np.int64),
        np.asarray(((1.0,),)),
        np.asarray(((0, 1, 2),), dtype=np.int64),
        np.asarray(((2, 2, 2),), dtype=np.int64),
        np.asarray(((0.2, -0.3, 0.5),)),
        5,
        synchronize_every=2,
    )

    assert hr.shape == (6, 1)
    assert ht.shape == (6, 1)
    assert hr[0, 0] == 0.0
    assert ht[0, 0] == 0.0
    assert simulation.steps == 5
    assert np.isfinite(hr).all()
    assert np.isfinite(ht).all()
