import numpy as np
import pytest

from ionosphere_fdtd.materials import (
    EarthIonosphereMaterial,
    LayeredEarthIonosphereMaterial,
    SphericalAnomaly,
    conservative_anomaly_fractions,
)


def test_conservative_anomaly_fractions_preserve_configured_area() -> None:
    anomaly = SphericalAnomaly(
        latitude_deg=0.0,
        longitude_deg=0.0,
        radius_m=40_000.0,
        altitude_min_m=-2_000.0,
        altitude_max_m=-500.0,
        conductivity_factor=0.1,
        target_area_m2=np.pi * 40_000.0**2,
    )
    directions = np.asarray(
        ((1.0, 0.0, 0.0), (0.999, 0.0447, 0.0), (0.0, 1.0, 0.0))
    )
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    areas = np.asarray((0.01, 0.02, 4.0 * np.pi - 0.03))

    fractions = conservative_anomaly_fractions(
        directions, areas, anomaly, 6_371_000.0
    )

    represented_area = fractions @ areas * 6_371_000.0**2
    assert np.all((fractions >= 0.0) & (fractions <= 1.0))
    assert represented_area == pytest.approx(np.pi * anomaly.radius_m**2)


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


def test_layered_material_fractionally_samples_shallow_water() -> None:
    material = LayeredEarthIonosphereMaterial(
        surface_elevation_sampler=lambda directions: np.full(
            len(directions), -200.0
        ),
        tangential_interface_mode="fractional",
    )
    sigma, epsilon_r = material.sample_tangential_cells(
        np.asarray(((1.0, 0.0, 0.0),)),
        np.asarray((-5_000.0,)),
        np.asarray((0.0,)),
        6_371_000.0,
    )
    water_fraction = 200.0 / 5_000.0
    expected_sigma = (
        (1.0 - water_fraction) / material.upper_crust_resistivity_ohm_m
        + water_fraction / material.sea_water_resistivity_ohm_m
    )
    expected_epsilon = (
        (1.0 - water_fraction) * material.lithosphere_relative_permittivity
        + water_fraction * material.sea_water_relative_permittivity
    )
    assert sigma[0, 0] == pytest.approx(expected_sigma)
    assert epsilon_r[0, 0] == pytest.approx(expected_epsilon)


@pytest.mark.parametrize(
    ("parameter", "value"),
    (
        ("lithosphere_conductivity_s_m", np.inf),
        ("ionosphere_reference_height_m", -np.inf),
        ("ionosphere_scale_height_m", np.inf),
        ("ionosphere_prefactor_hz", np.nan),
    ),
)
def test_default_material_rejects_nonfinite_parameters(
    parameter: str, value: float
) -> None:
    with pytest.raises(ValueError, match="finite"):
        EarthIonosphereMaterial(**{parameter: value})
