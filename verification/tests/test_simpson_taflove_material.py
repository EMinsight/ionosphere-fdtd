from dataclasses import fields

import numpy as np
import pytest

from ionosphere_fdtd.constants import EPSILON_0
from ionosphere_fdtd.materials import (
    LayeredEarthIonosphereMaterial,
    SphericalAnomaly,
)
from verification.simpson_taflove_2004.materials import (
    ETOPO5_SHAPE,
    ETOPO5_SIZE_BYTES,
    ETOPO5Relief,
    SimpsonTaflove2004Material,
)


def test_simpson_taflove_material_distinguishes_land_water_and_rock() -> None:
    material = SimpsonTaflove2004Material(
        land_classifier=lambda directions: directions[:, 0] > 0.0
    )
    directions = np.asarray(((1.0, 0.0, 0.0), (-1.0, 0.0, 0.0)))
    sigma, epsilon_r = material.sample(
        directions, np.asarray((-2_500.0, -30_000.0, 80_000.0)), 6_371_000.0
    )

    assert sigma[0, 0] == 1.0 / material.upper_crust_resistivity_ohm_m
    assert sigma[1, 0] == 1.0 / material.sea_water_resistivity_ohm_m
    assert sigma[0, 1] == 1.0 / material.upper_crust_resistivity_ohm_m
    assert sigma[1, 1] == 1.0 / material.asthenosphere_resistivity_ohm_m
    assert epsilon_r[1, 0] == material.sea_water_relative_permittivity
    assert sigma[0, 2] == sigma[1, 2]
    assert material.ionosphere_reference_height_m == 70_000.0
    assert material.ionosphere_scale_height_m == pytest.approx(1_000.0 / 0.3)
    assert material.deep_rock_resistivity_ohm_m == 500.0


def test_simpson_taflove_preset_is_numerically_identical_to_generic_layers() -> None:
    classifier = lambda directions: directions[:, 0] > 0.0
    paper = SimpsonTaflove2004Material(land_classifier=classifier)
    generic = LayeredEarthIonosphereMaterial(
        **{
            item.name: getattr(paper, item.name)
            for item in fields(LayeredEarthIonosphereMaterial)
        }
    )
    directions = np.asarray(((1.0, 0.0, 0.0), (-1.0, 0.0, 0.0)))
    altitudes = np.asarray((-70_000.0, -2_500.0, 0.0, 80_000.0))

    paper_point = paper.sample(directions, altitudes, 6_371_000.0)
    generic_point = generic.sample(directions, altitudes, 6_371_000.0)
    paper_cells = paper.sample_tangential_cells(
        directions, altitudes[:-1], altitudes[1:], 6_371_000.0
    )
    generic_cells = generic.sample_tangential_cells(
        directions, altitudes[:-1], altitudes[1:], 6_371_000.0
    )

    comparisons = (*zip(paper_point, generic_point), *zip(paper_cells, generic_cells))
    for paper_values, generic_values in comparisons:
        np.testing.assert_array_equal(paper_values, generic_values)


def test_simpson_taflove_material_matches_bannister_reference_value() -> None:
    material = SimpsonTaflove2004Material(
        land_classifier=lambda directions: np.ones(
            len(directions), dtype=np.bool_
        )
    )

    sigma, _ = material.sample(
        np.asarray(((1.0, 0.0, 0.0),)),
        np.asarray((material.ionosphere_reference_height_m,)),
        6_371_000.0,
    )

    assert sigma[0, 0] == pytest.approx(2.5e5 * EPSILON_0)


def test_simpson_taflove_material_applies_buried_anomaly() -> None:
    anomaly = SphericalAnomaly(
        latitude_deg=69.0,
        longitude_deg=-156.0,
        radius_m=50_000.0,
        altitude_min_m=-2_000.0,
        altitude_max_m=-500.0,
        conductivity_factor=0.1,
    )
    material = SimpsonTaflove2004Material(
        land_classifier=lambda directions: np.ones(len(directions), dtype=np.bool_),
        anomalies=(anomaly,),
    )
    directions = np.stack((anomaly.center, np.asarray((1.0, 0.0, 0.0))))
    sigma, _ = material.sample(
        directions,
        np.asarray((-1_250.0, 0.0)),
        6_371_000.0,
    )

    assert sigma[0, 0] == pytest.approx(0.1 / 500.0)
    assert sigma[1, 0] == pytest.approx(1.0 / 500.0)


def test_anomaly_background_limit_preserves_water() -> None:
    anomaly = SphericalAnomaly(
        latitude_deg=0.0,
        longitude_deg=0.0,
        radius_m=50_000.0,
        altitude_min_m=-2_000.0,
        altitude_max_m=-500.0,
        conductivity_factor=0.1,
        maximum_background_conductivity_s_m=0.01,
    )
    material = SimpsonTaflove2004Material(
        land_classifier=lambda directions: directions[:, 2] > 0.0,
        anomalies=(anomaly,),
    )
    offset = np.deg2rad(0.1)
    directions = np.asarray(
        (
            (np.cos(offset), 0.0, np.sin(offset)),
            (np.cos(offset), 0.0, -np.sin(offset)),
        )
    )
    sigma, _ = material.sample(
        directions,
        np.asarray((-1_250.0,)),
        6_371_000.0,
    )

    assert sigma[0, 0] == pytest.approx(0.1 / 500.0)
    assert sigma[1, 0] == pytest.approx(1.0 / material.sea_water_resistivity_ohm_m)


def test_etopo5_relief_reads_big_endian_grid_and_wraps_longitude(tmp_path) -> None:
    path = tmp_path / "ETOPO5.DAT"
    with path.open("wb") as stream:
        stream.truncate(ETOPO5_SIZE_BYTES)
    grid = np.memmap(path, dtype=">i2", mode="r+", shape=ETOPO5_SHAPE)
    grid[1_080, 0] = 1_200
    grid[1_080, -1] = -600
    grid[-1, :] = 100
    grid[-1, 0] = 300
    grid.flush()
    del grid

    relief = ETOPO5Relief.from_file(path, verify_sha256=False)
    directions = np.asarray(
        (
            (1.0, 0.0, 0.0),
            (
                np.cos(np.deg2rad(-1.0 / 24.0)),
                -np.sin(np.deg2rad(1.0 / 24.0)),
                0.0,
            ),
            (0.0, 0.0, -1.0),
        )
    )

    assert relief(directions)[0] == pytest.approx(1_200.0)
    assert relief(directions)[1] == pytest.approx(300.0)
    assert relief(directions)[2] == pytest.approx(100.0 + 200.0 / 4_320.0)


def test_relief_material_resolves_mountains_ocean_and_seafloor() -> None:
    material = SimpsonTaflove2004Material(
        surface_elevation_sampler=lambda directions: np.asarray(
            (1_500.0, -2_500.0)
        )
    )
    directions = np.asarray(((1.0, 0.0, 0.0), (-1.0, 0.0, 0.0)))
    sigma, epsilon_r = material.sample(
        directions,
        np.asarray((1_000.0, -1_000.0, -3_000.0, -70_000.0)),
        6_371_000.0,
    )

    assert sigma[0, 0] == 1.0 / material.upper_crust_resistivity_ohm_m
    assert epsilon_r[0, 0] == material.lithosphere_relative_permittivity
    assert epsilon_r[1, 0] == material.atmosphere_relative_permittivity
    assert sigma[1, 1] == 1.0 / material.sea_water_resistivity_ohm_m
    assert sigma[1, 2] == 1.0 / material.upper_crust_resistivity_ohm_m
    assert np.all(sigma[:, 3] == 1.0 / material.deep_rock_resistivity_ohm_m)


def test_fractional_tangential_interface_preserves_shallow_water_fraction() -> None:
    depths_m = np.asarray((-207.0, -4_538.0))
    material = SimpsonTaflove2004Material(
        surface_elevation_sampler=lambda directions: depths_m,
        tangential_interface_mode="fractional",
    )
    directions = np.asarray(((1.0, 0.0, 0.0), (-1.0, 0.0, 0.0)))

    sigma, epsilon_r = material.sample_tangential_cells(
        directions,
        np.asarray((-5_000.0,)),
        np.asarray((0.0,)),
        6_371_000.0,
    )

    water_fraction = -depths_m / 5_000.0
    rock_fraction = 1.0 - water_fraction
    expected_sigma = (
        rock_fraction / material.upper_crust_resistivity_ohm_m
        + water_fraction / material.sea_water_resistivity_ohm_m
    )
    expected_epsilon = (
        rock_fraction * material.lithosphere_relative_permittivity
        + water_fraction * material.sea_water_relative_permittivity
    )
    np.testing.assert_allclose(sigma[:, 0], expected_sigma)
    np.testing.assert_allclose(epsilon_r[:, 0], expected_epsilon)
    assert sigma[0, 0] > 1.0 / material.upper_crust_resistivity_ohm_m


@pytest.mark.parametrize("interface_mode", ("point", "fractional"))
def test_tangential_anomaly_preserves_radial_overlap(
    interface_mode: str,
) -> None:
    anomaly = SphericalAnomaly(
        latitude_deg=0.0,
        longitude_deg=0.0,
        radius_m=100_000.0,
        altitude_min_m=-1_825.0,
        altitude_max_m=-575.0,
        conductivity_factor=0.1,
    )
    material = SimpsonTaflove2004Material(
        land_classifier=lambda directions: np.ones(len(directions), dtype=np.bool_),
        anomalies=(anomaly,),
        tangential_interface_mode=interface_mode,
    )
    directions = np.asarray(((1.0, 0.0, 0.0),))
    lower = np.asarray((-2_500.0, -1_250.0, 0.0))
    upper = np.asarray((-1_250.0, 0.0, 1_250.0))

    sigma, _ = material.sample_tangential_cells(
        directions, lower, upper, 6_371_000.0
    )

    background_material = SimpsonTaflove2004Material(
        land_classifier=lambda directions: np.ones(len(directions), dtype=np.bool_),
        tangential_interface_mode=interface_mode,
    )
    background, _ = background_material.sample_tangential_cells(
        directions, lower, upper, 6_371_000.0
    )
    fractions = np.asarray((575.0 / 1_250.0, 675.0 / 1_250.0, 0.0))
    expected = background[0] * (1.0 + fractions * (0.1 - 1.0))
    np.testing.assert_allclose(sigma[0], expected, rtol=0.0, atol=1.0e-18)
    assert np.sum(fractions) == pytest.approx(1.0)


def test_point_tangential_interface_retains_midpoint_sampling() -> None:
    material = SimpsonTaflove2004Material(
        surface_elevation_sampler=lambda directions: np.asarray(
            (-207.0, -4_538.0)
        ),
        tangential_interface_mode="point",
    )
    directions = np.asarray(((1.0, 0.0, 0.0), (-1.0, 0.0, 0.0)))

    sigma, _ = material.sample_tangential_cells(
        directions,
        np.asarray((-5_000.0,)),
        np.asarray((0.0,)),
        6_371_000.0,
    )

    assert sigma[0, 0] == pytest.approx(
        1.0 / material.upper_crust_resistivity_ohm_m
    )
    assert sigma[1, 0] == pytest.approx(
        1.0 / material.sea_water_resistivity_ohm_m
    )


def test_minimum_ocean_depth_preserves_one_radial_water_cell() -> None:
    material = SimpsonTaflove2004Material(
        surface_elevation_sampler=lambda directions: np.asarray(
            (-207.0, -6_000.0, 300.0)
        ),
        minimum_ocean_depth_m=5_000.0,
    )
    directions = np.asarray(
        ((1.0, 0.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    )
    sigma, _ = material.sample(
        directions,
        np.asarray((-2_500.0, -5_000.0, -7_500.0)),
        6_371_000.0,
    )

    water = 1.0 / material.sea_water_resistivity_ohm_m
    rock = 1.0 / material.upper_crust_resistivity_ohm_m
    np.testing.assert_allclose(sigma[0], (water, water, rock))
    np.testing.assert_allclose(sigma[1], (water, water, rock))
    np.testing.assert_allclose(sigma[2], (rock, rock, rock))


def test_simpson_material_rejects_negative_minimum_ocean_depth() -> None:
    with pytest.raises(ValueError, match="minimum ocean depth"):
        SimpsonTaflove2004Material(
            land_classifier=lambda directions: np.ones(
                len(directions), dtype=np.bool_
            ),
            minimum_ocean_depth_m=-1.0,
        )


def test_fractional_tangential_interface_rejects_invalid_bounds() -> None:
    material = SimpsonTaflove2004Material(
        land_classifier=lambda directions: np.ones(len(directions), dtype=np.bool_),
        tangential_interface_mode="fractional",
    )
    directions = np.asarray(((1.0, 0.0, 0.0),))

    with pytest.raises(ValueError, match="upper bounds"):
        material.sample_tangential_cells(
            directions,
            np.asarray((0.0,)),
            np.asarray((0.0,)),
            6_371_000.0,
        )


def test_simpson_material_rejects_unknown_interface_mode() -> None:
    with pytest.raises(ValueError, match="tangential_interface_mode"):
        SimpsonTaflove2004Material(
            land_classifier=lambda directions: np.ones(
                len(directions), dtype=np.bool_
            ),
            tangential_interface_mode="unknown",
        )


@pytest.mark.parametrize(
    "parameter",
    (
        "ocean_depth_m",
        "sea_water_resistivity_ohm_m",
        "ionosphere_reference_height_m",
        "ionosphere_scale_height_m",
        "ionosphere_prefactor_hz",
        "minimum_ocean_depth_m",
    ),
)
def test_simpson_material_rejects_nonfinite_parameters(parameter: str) -> None:
    with pytest.raises(ValueError, match="finite"):
        SimpsonTaflove2004Material(
            land_classifier=lambda directions: np.ones(
                len(directions), dtype=np.bool_
            ),
            **{parameter: np.inf},
        )
