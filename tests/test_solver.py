import numpy as np
import pytest

from ionosphere.materials import EarthIonosphereMaterial
from ionosphere.solver import GeodesicFDTD, SimulationConfig
from ionosphere.sources import GaussianCurrent


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


def test_requested_unstable_time_step_is_rejected() -> None:
    baseline = GeodesicFDTD(config=small_config())
    with pytest.raises(ValueError, match="exceeds conservative limit"):
        GeodesicFDTD(
            config=small_config(time_step_s=2.0 * baseline.maximum_stable_time_step_s)
        )


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
