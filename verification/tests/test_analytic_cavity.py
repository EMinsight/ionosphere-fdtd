import numpy as np

from ionosphere_fdtd.constants import EARTH_RADIUS_M
from ionosphere_fdtd.solver import GeodesicFDTD, SimulationConfig
from verification.analytic_solutions.cavity import VacuumMaterial, build_electric_mode, initialize_electric_standing_mode, project_electric_mode


def _simulation() -> GeodesicFDTD:
    return GeodesicFDTD(
        SimulationConfig(
            subdivision=1, radial_cells=8,
            minimum_altitude_m=0.0, maximum_altitude_m=100_000.0,
            earth_radius_m=EARTH_RADIUS_M, courant_factor=0.2,
            geometry_mode="full-spherical",
        ), material=VacuumMaterial(), dtype="float64",
    )


def test_cavity_initializer_projects_to_unit_amplitude() -> None:
    for polarization in ("TE", "TM"):
        simulation = _simulation()
        mode = build_electric_mode(simulation, 1, polarization=polarization)
        initialize_electric_standing_mode(simulation, mode)
        projection = project_electric_mode(simulation, mode)
        np.testing.assert_allclose(projection.amplitude, 1.0, rtol=0.0, atol=3e-16)
        assert projection.relative_leakage < 3e-16
        assert np.all(np.isfinite(mode.er_v_m))
        assert np.all(np.isfinite(mode.et_v_m))
