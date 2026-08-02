"""Configurable radial Earth/atmosphere conductivity model."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from .constants import EPSILON_0

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]
LandClassifier = Callable[[FloatArray], BoolArray]


@dataclass(frozen=True, slots=True)
class SphericalAnomaly:
    """Multiplicative conductivity anomaly in a spherical lithosphere volume."""

    latitude_deg: float
    longitude_deg: float
    radius_m: float
    altitude_min_m: float
    altitude_max_m: float
    conductivity_factor: float
    relative_permittivity: float | None = None

    def __post_init__(self) -> None:
        if self.radius_m <= 0.0:
            raise ValueError("anomaly radius_m must be positive")
        if self.altitude_min_m > self.altitude_max_m:
            raise ValueError("anomaly altitude bounds are reversed")
        if self.conductivity_factor <= 0.0:
            raise ValueError("conductivity_factor must be positive")

    @property
    def center(self) -> FloatArray:
        latitude = np.deg2rad(self.latitude_deg)
        longitude = np.deg2rad(self.longitude_deg)
        return np.asarray(
            (
                np.cos(latitude) * np.cos(longitude),
                np.cos(latitude) * np.sin(longitude),
                np.sin(latitude),
            ),
            dtype=np.float64,
        )


@dataclass(frozen=True, slots=True)
class EarthIonosphereMaterial:
    """Small, data-free approximation to the paper's daytime material model.

    The lower half-space is a homogeneous lossy lithosphere.  Above sea level,
    conductivity follows the commonly used exponential form
    ``2.5e5 * epsilon_0 * exp((h-H')/zeta)``.  All parameters are exposed so
    measured profiles can replace these defaults later without changing the
    FDTD solver.
    """

    lithosphere_conductivity_s_m: float = 1.0e-3
    lithosphere_relative_permittivity: float = 10.0
    atmosphere_relative_permittivity: float = 1.0
    ionosphere_reference_height_m: float = 74_000.0
    ionosphere_scale_height_m: float = 6_000.0
    ionosphere_prefactor_hz: float = 2.5e5
    anomalies: tuple[SphericalAnomaly, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.lithosphere_conductivity_s_m < 0.0:
            raise ValueError("lithosphere conductivity cannot be negative")
        if self.lithosphere_relative_permittivity < 1.0:
            raise ValueError("lithosphere relative permittivity must be >= 1")
        if self.atmosphere_relative_permittivity < 1.0:
            raise ValueError("atmosphere relative permittivity must be >= 1")
        if self.ionosphere_scale_height_m <= 0.0:
            raise ValueError("ionosphere scale height must be positive")

    def sample(
        self,
        directions: FloatArray,
        altitudes_m: FloatArray,
        earth_radius_m: float,
    ) -> tuple[FloatArray, FloatArray]:
        """Return ``(conductivity, relative_permittivity)`` on a tensor grid."""

        altitudes = np.asarray(altitudes_m, dtype=np.float64)
        sigma_air = (
            self.ionosphere_prefactor_hz
            * EPSILON_0
            * np.exp(
                np.clip(
                    (altitudes - self.ionosphere_reference_height_m)
                    / self.ionosphere_scale_height_m,
                    -80.0,
                    80.0,
                )
            )
        )
        below_ground = altitudes < 0.0
        sigma_profile = np.where(
            below_ground, self.lithosphere_conductivity_s_m, sigma_air
        )
        epsilon_profile = np.where(
            below_ground,
            self.lithosphere_relative_permittivity,
            self.atmosphere_relative_permittivity,
        )
        sigma = np.broadcast_to(sigma_profile, (len(directions), len(altitudes))).copy()
        epsilon_r = np.broadcast_to(
            epsilon_profile, (len(directions), len(altitudes))
        ).copy()

        for anomaly in self.anomalies:
            angular_radius = anomaly.radius_m / earth_radius_m
            inside_horizontal = np.arccos(
                np.clip(directions @ anomaly.center, -1.0, 1.0)
            ) <= angular_radius
            inside_vertical = (altitudes >= anomaly.altitude_min_m) & (
                altitudes <= anomaly.altitude_max_m
            )
            inside = inside_horizontal[:, None] & inside_vertical[None, :]
            sigma[inside] *= anomaly.conductivity_factor
            if anomaly.relative_permittivity is not None:
                epsilon_r[inside] = anomaly.relative_permittivity
        return sigma, epsilon_r


@dataclass(frozen=True, slots=True)
class SimpsonTaflove2004Material:
    """Data-light approximation to the material model in Simpson–Taflove (2004).

    Figure 6 reports bounded resistivity regions rather than a complete numeric
    Earth model.  This implementation uses the reported boundary values, a
    5-km ocean layer, and a caller-provided land classifier.  It therefore
    reproduces the paper's land/ocean mechanism while making the missing NOAA
    relief data explicit instead of presenting the approximation as exact.
    The ionosphere defaults use the representative 70-km reference height and
    3.33-km scale height of the standard daytime exponential profile; callers
    can override both when path-specific Bannister parameters are available.
    """

    land_classifier: LandClassifier
    ocean_depth_m: float = 5_000.0
    sea_water_resistivity_ohm_m: float = 0.3
    upper_crust_resistivity_ohm_m: float = 500.0
    asthenosphere_resistivity_ohm_m: float = 200.0
    lower_mantle_resistivity_ohm_m: float = 500.0
    asthenosphere_top_depth_m: float = 20_000.0
    asthenosphere_bottom_depth_m: float = 60_000.0
    lithosphere_relative_permittivity: float = 10.0
    sea_water_relative_permittivity: float = 80.0
    atmosphere_relative_permittivity: float = 1.0
    ionosphere_reference_height_m: float = 70_000.0
    ionosphere_scale_height_m: float = 3_330.0
    ionosphere_prefactor_hz: float = 2.5e5

    def __post_init__(self) -> None:
        positive = (
            self.ocean_depth_m,
            self.sea_water_resistivity_ohm_m,
            self.upper_crust_resistivity_ohm_m,
            self.asthenosphere_resistivity_ohm_m,
            self.lower_mantle_resistivity_ohm_m,
            self.asthenosphere_top_depth_m,
            self.asthenosphere_bottom_depth_m,
            self.ionosphere_scale_height_m,
        )
        if any(value <= 0.0 for value in positive):
            raise ValueError("material lengths and resistivities must be positive")
        if self.asthenosphere_top_depth_m >= self.asthenosphere_bottom_depth_m:
            raise ValueError("asthenosphere depth bounds are reversed")
        if min(
            self.lithosphere_relative_permittivity,
            self.sea_water_relative_permittivity,
            self.atmosphere_relative_permittivity,
        ) < 1.0:
            raise ValueError("relative permittivity must be >= 1")

    def sample(
        self,
        directions: FloatArray,
        altitudes_m: FloatArray,
        earth_radius_m: float,
    ) -> tuple[FloatArray, FloatArray]:
        """Return conductivity and permittivity on the requested tensor grid."""

        del earth_radius_m
        directions = np.array(directions, dtype=np.float64, copy=True)
        directions /= np.linalg.norm(directions, axis=1, keepdims=True)
        altitudes = np.asarray(altitudes_m, dtype=np.float64)
        is_land = np.asarray(self.land_classifier(directions), dtype=np.bool_)
        if is_land.shape != (len(directions),):
            raise ValueError("land_classifier must return one boolean per direction")

        sigma_air = (
            self.ionosphere_prefactor_hz
            * EPSILON_0
            * np.exp(
                np.clip(
                    (altitudes - self.ionosphere_reference_height_m)
                    / self.ionosphere_scale_height_m,
                    -80.0,
                    80.0,
                )
            )
        )
        sigma = np.broadcast_to(
            sigma_air, (len(directions), len(altitudes))
        ).copy()
        epsilon_r = np.full_like(sigma, self.atmosphere_relative_permittivity)

        depth = np.maximum(-altitudes, 0.0)
        rock_resistivity = np.where(
            (depth >= self.asthenosphere_top_depth_m)
            & (depth < self.asthenosphere_bottom_depth_m),
            self.asthenosphere_resistivity_ohm_m,
            np.where(
                depth >= self.asthenosphere_bottom_depth_m,
                self.lower_mantle_resistivity_ohm_m,
                self.upper_crust_resistivity_ohm_m,
            ),
        )
        below_surface = altitudes < 0.0
        sigma[:, below_surface] = 1.0 / rock_resistivity[below_surface]
        epsilon_r[:, below_surface] = self.lithosphere_relative_permittivity

        water_layers = (
            (~is_land)[:, None]
            & (altitudes[None, :] < 0.0)
            & (altitudes[None, :] >= -self.ocean_depth_m)
        )
        sigma[water_layers] = 1.0 / self.sea_water_resistivity_ohm_m
        epsilon_r[water_layers] = self.sea_water_relative_permittivity
        return sigma, epsilon_r
