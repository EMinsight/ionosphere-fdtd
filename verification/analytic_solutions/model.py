"""Closed-form and scalar-root reference solutions applicable to the solver."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy.optimize import brentq
from scipy.special import spherical_jn, spherical_yn

from ionosphere_fdtd.constants import C_0, EPSILON_0, MU_0


@dataclass(frozen=True, slots=True)
class PropagationConstant:
    frequency_hz: float
    beta_rad_per_m: float
    attenuation_np_per_m: float
    phase_velocity_m_per_s: float


def conductive_relaxation(
    time_s: np.ndarray | float,
    *,
    initial_e_v_m: float,
    conductivity_s_m: float,
    relative_permittivity: float = 1.0,
) -> np.ndarray:
    """Exact curl-free electric relaxation in a homogeneous conductor."""

    if conductivity_s_m < 0.0 or relative_permittivity <= 0.0:
        raise ValueError("conductivity must be nonnegative and permittivity positive")
    time = np.asarray(time_s, dtype=np.float64)
    return initial_e_v_m * np.exp(
        -conductivity_s_m * time / (EPSILON_0 * relative_permittivity)
    )


def homogeneous_medium_propagation_constant(
    frequency_hz: float,
    *,
    conductivity_s_m: float = 0.0,
    relative_permittivity: float = 1.0,
    relative_permeability: float = 1.0,
) -> PropagationConstant:
    """Exact plane-wave propagation for the ``exp(+j omega t)`` convention."""

    if frequency_hz <= 0.0 or conductivity_s_m < 0.0:
        raise ValueError("frequency must be positive and conductivity nonnegative")
    if relative_permittivity <= 0.0 or relative_permeability <= 0.0:
        raise ValueError("relative material parameters must be positive")
    omega = 2.0 * np.pi * frequency_hz
    if conductivity_s_m == 0.0:
        velocity = C_0 / np.sqrt(relative_permittivity * relative_permeability)
        return PropagationConstant(
            frequency_hz, omega / velocity, 0.0, velocity
        )
    gamma = np.sqrt(
        1j
        * omega
        * MU_0
        * relative_permeability
        * (conductivity_s_m + 1j * omega * EPSILON_0 * relative_permittivity)
    )
    if gamma.real < 0.0:
        gamma = -gamma
    attenuation = float(gamma.real)
    beta = float(abs(gamma.imag))
    return PropagationConstant(
        frequency_hz, beta, attenuation, omega / beta
    )


def spherical_surface_eigenvalue(degree: int, radius_m: float) -> float:
    if degree < 0 or radius_m <= 0.0:
        raise ValueError("degree must be nonnegative and radius positive")
    return degree * (degree + 1.0) / radius_m**2


def spherical_surface_frequency_hz(
    degree: int, radius_m: float, wave_speed_m_s: float = C_0
) -> float:
    return wave_speed_m_s * np.sqrt(
        spherical_surface_eigenvalue(degree, radius_m)
    ) / (2.0 * np.pi)


def leapfrog_frequency_hz(
    angular_frequency_rad_s: float, time_step_s: float
) -> float:
    """Exact frequency of the centered leapfrog oscillator recurrence."""

    argument = 0.5 * angular_frequency_rad_s * time_step_s
    if argument < 0.0 or argument > 1.0:
        raise ValueError("oscillator is outside the leapfrog stability interval")
    return np.arcsin(argument) / (np.pi * time_step_s)


def pec_spherical_shell_wavenumbers(
    degree: int,
    inner_radius_m: float,
    outer_radius_m: float,
    *,
    polarization: str,
    count: int = 3,
    maximum_frequency_hz: float = 10_000.0,
) -> np.ndarray:
    """Return vector-spherical-harmonic roots for two concentric PEC walls.

    TE roots have zero tangential electric radial function at both walls. TM
    roots have zero derivative of ``r z_l(k r)`` at both walls.
    """

    if degree < 1 or not 0.0 < inner_radius_m < outer_radius_m:
        raise ValueError("degree and shell radii are invalid")
    if polarization not in {"TE", "TM"} or count < 1:
        raise ValueError("polarization must be TE or TM and count positive")

    def radial(kind: str, x: np.ndarray | float) -> np.ndarray | float:
        function = spherical_jn if kind == "j" else spherical_yn
        if polarization == "TE":
            return function(degree, x)
        return function(degree, x) + x * function(degree, x, derivative=True)

    def determinant(k: float) -> float:
        ka = k * inner_radius_m
        kb = k * outer_radius_m
        return float(radial("j", ka) * radial("y", kb) - radial("y", ka) * radial("j", kb))

    maximum_k = 2.0 * np.pi * maximum_frequency_hz / C_0
    approximate_spacing = np.pi / (outer_radius_m - inner_radius_m)
    samples = max(20_000, int(80.0 * maximum_k / approximate_spacing))
    grid = np.linspace(maximum_k / samples, maximum_k, samples)
    values = np.asarray([determinant(value) for value in grid])
    roots = []
    for left, right, f_left, f_right in zip(grid[:-1], grid[1:], values[:-1], values[1:]):
        if np.isfinite(f_left) and np.isfinite(f_right) and f_left * f_right < 0.0:
            root = brentq(determinant, left, right, xtol=1e-15, rtol=1e-13)
            if not roots or abs(root - roots[-1]) > 1e-10 * root:
                roots.append(root)
                if len(roots) == count:
                    break
    if len(roots) != count:
        raise RuntimeError("requested PEC shell roots were not bracketed")
    return np.asarray(roots)


def pec_spherical_shell_frequencies_hz(*args, **kwargs) -> np.ndarray:
    return C_0 * pec_spherical_shell_wavenumbers(*args, **kwargs) / (2.0 * np.pi)
