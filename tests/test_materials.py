import numpy as np

from ionosphere.materials import EarthIonosphereMaterial, SphericalAnomaly


def test_profile_is_lithosphere_below_and_exponential_above() -> None:
    material = EarthIonosphereMaterial()
    sigma, epsilon_r = material.sample(
        np.asarray(((1.0, 0.0, 0.0),)),
        np.asarray((-1_000.0, 0.0, 80_000.0)),
        6_371_000.0,
    )
    assert sigma[0, 0] == material.lithosphere_conductivity_s_m
    assert sigma[0, 2] > sigma[0, 1]
    assert epsilon_r[0, 0] == material.lithosphere_relative_permittivity
    assert epsilon_r[0, 1] == material.atmosphere_relative_permittivity


def test_anomaly_changes_only_selected_volume() -> None:
    material = EarthIonosphereMaterial(
        anomalies=(
            SphericalAnomaly(0.0, 0.0, 100_000.0, -2_000.0, -500.0, 0.1),
        )
    )
    directions = np.asarray(((1.0, 0.0, 0.0), (-1.0, 0.0, 0.0)))
    sigma, _ = material.sample(directions, np.asarray((-1_000.0,)), 6_371_000.0)
    assert np.isclose(sigma[0, 0], 1.0e-4)
    assert np.isclose(sigma[1, 0], 1.0e-3)
