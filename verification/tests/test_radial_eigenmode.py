import numpy as np
import pytest

from verification.radial_eigenmode.model import (
    conductivity_s_m,
    discretized_conductivity_s_m,
    solve_tm_mode,
)


def test_exponential_profile_has_requested_scale_height() -> None:
    heights=np.asarray((70_000.0,70_000.0+1_000.0/0.3))
    sigma=conductivity_s_m(heights)
    assert sigma[1]/sigma[0]==pytest.approx(np.e)


def test_discretized_profile_uses_cell_centers() -> None:
    sampled=discretized_conductivity_s_m(np.asarray((1.0,4_999.0,5_001.0)),5_000.0)
    assert sampled[0]==sampled[1]
    assert sampled[2]>sampled[1]
    assert sampled[0]==pytest.approx(conductivity_s_m(np.asarray(2_500.0)))


def test_tm_mode_solver_converges_to_physical_fundamental() -> None:
    beta,residual=solve_tm_mode(250.0)
    velocity=2*np.pi*250.0/beta.real/299_792_458.0
    attenuation=-20/np.log(10)*beta.imag*1e6
    assert velocity==pytest.approx(0.83758,rel=2e-4)
    assert attenuation==pytest.approx(4.6276,rel=2e-4)
    assert residual<1e-8
