"""Configurable radial Earth/atmosphere conductivity model."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from .constants import EPSILON_0

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]
LandClassifier = Callable[[FloatArray], BoolArray]
ReliefSampler = Callable[[FloatArray], FloatArray]

ETOPO5_SHAPE = (2_160, 4_320)
ETOPO5_SIZE_BYTES = 18_662_400
ETOPO5_SHA256 = (
    "471d3dd534144aa9a6551fe3e76320a06a45dade6fd8d45f7d6ad981d59f93c3"
)


@dataclass(frozen=True, slots=True)
class ETOPO5Relief:
    """NOAA-NGDC ETOPO5 cell-center elevations in their native 5′ grid."""

    path: Path
    elevations_m: NDArray[np.int16] = field(repr=False, compare=False)

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        verify_sha256: bool = True,
    ) -> ETOPO5Relief:
        """Memory-map the big-endian ``ETOPO5.DAT`` distribution file."""

        source = Path(path)
        try:
            size = source.stat().st_size
        except OSError as error:
            raise ValueError(f"cannot read ETOPO5 relief file: {source}") from error
        if size != ETOPO5_SIZE_BYTES:
            raise ValueError(
                f"ETOPO5 relief file must contain {ETOPO5_SIZE_BYTES} bytes, "
                f"got {size}"
            )
        if verify_sha256:
            with source.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if digest != ETOPO5_SHA256:
                raise ValueError(
                    "ETOPO5 relief SHA-256 mismatch: "
                    f"expected {ETOPO5_SHA256}, got {digest}"
                )
        elevations = np.memmap(
            source,
            dtype=">i2",
            mode="r",
            shape=ETOPO5_SHAPE,
        )
        return cls(path=source, elevations_m=elevations)

    def __call__(self, directions: FloatArray) -> FloatArray:
        """Bilinearly sample relief at unit Cartesian directions."""

        points = np.asarray(directions, dtype=np.float64)
        if points.ndim != 2 or points.shape[1] != 3:
            raise ValueError("directions must have shape (count, 3)")
        norms = np.linalg.norm(points, axis=1)
        if np.any(norms == 0.0):
            raise ValueError("relief directions must be nonzero")
        points = points / norms[:, None]
        longitude_deg = np.mod(
            np.rad2deg(np.arctan2(points[:, 1], points[:, 0])), 360.0
        )
        latitude_deg = np.rad2deg(
            np.arctan2(points[:, 2], np.hypot(points[:, 0], points[:, 1]))
        )

        row = np.clip((90.0 - latitude_deg) * 12.0, 0.0, ETOPO5_SHAPE[0] - 1)
        column = longitude_deg * 12.0
        row0 = np.floor(row).astype(np.int64)
        row1 = np.minimum(row0 + 1, ETOPO5_SHAPE[0] - 1)
        column0 = np.floor(column).astype(np.int64) % ETOPO5_SHAPE[1]
        column1 = (column0 + 1) % ETOPO5_SHAPE[1]
        row_fraction = row - row0
        column_fraction = column - np.floor(column)

        north_west = np.asarray(self.elevations_m[row0, column0], dtype=np.float64)
        north_east = np.asarray(self.elevations_m[row0, column1], dtype=np.float64)
        south_west = np.asarray(self.elevations_m[row1, column0], dtype=np.float64)
        south_east = np.asarray(self.elevations_m[row1, column1], dtype=np.float64)
        north = north_west + column_fraction * (north_east - north_west)
        south = south_west + column_fraction * (south_east - south_west)
        return north + row_fraction * (south - north)


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
    """Lithosphere and relief model from Simpson–Taflove (2004), Figure 6.

    A relief sampler uses actual surface elevation and bathymetry when supplied;
    the legacy land classifier retains a fixed-depth fallback.  Figure 6 gives
    bounded, conceptual oceanic and continental resistivity regions rather than
    a downloadable 3-D conductivity grid, so the exposed layer values use those
    bounds as representative profiles.  The ionosphere defaults use the 70-km
    reference height and 3.33-km scale height of the standard daytime profile.
    """

    land_classifier: LandClassifier | None = None
    surface_elevation_sampler: ReliefSampler | None = None
    ocean_depth_m: float = 5_000.0
    sea_water_resistivity_ohm_m: float = 0.3
    upper_crust_resistivity_ohm_m: float = 500.0
    asthenosphere_resistivity_ohm_m: float = 200.0
    lower_mantle_resistivity_ohm_m: float = 50.0
    asthenosphere_top_depth_m: float = 20_000.0
    asthenosphere_bottom_depth_m: float = 60_000.0
    lithosphere_relative_permittivity: float = 10.0
    sea_water_relative_permittivity: float = 80.0
    atmosphere_relative_permittivity: float = 1.0
    ionosphere_reference_height_m: float = 70_000.0
    ionosphere_scale_height_m: float = 3_330.0
    ionosphere_prefactor_hz: float = 2.5e5

    def __post_init__(self) -> None:
        if (self.land_classifier is None) == (
            self.surface_elevation_sampler is None
        ):
            raise ValueError(
                "provide exactly one of land_classifier or surface_elevation_sampler"
            )
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
        if self.surface_elevation_sampler is None:
            assert self.land_classifier is not None
            is_land = np.asarray(self.land_classifier(directions), dtype=np.bool_)
            surface_elevation_m = np.where(is_land, 0.0, -self.ocean_depth_m)
        else:
            surface_elevation_m = np.asarray(
                self.surface_elevation_sampler(directions), dtype=np.float64
            )
            is_land = surface_elevation_m >= 0.0
        if is_land.shape != (len(directions),):
            raise ValueError("surface data must return one value per direction")
        if not np.all(np.isfinite(surface_elevation_m)):
            raise ValueError("surface elevations must be finite")

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
        ocean_rock_resistivity = np.where(
            depth >= self.asthenosphere_bottom_depth_m,
            self.lower_mantle_resistivity_ohm_m,
            np.where(
                depth >= self.asthenosphere_top_depth_m,
                self.asthenosphere_resistivity_ohm_m,
                self.upper_crust_resistivity_ohm_m,
            ),
        )
        continent_rock_resistivity = np.where(
            depth >= self.asthenosphere_bottom_depth_m,
            self.lower_mantle_resistivity_ohm_m,
            self.upper_crust_resistivity_ohm_m,
        )
        rock_resistivity = np.where(
            is_land[:, None],
            continent_rock_resistivity[None, :],
            ocean_rock_resistivity[None, :],
        )
        below_surface = altitudes[None, :] < surface_elevation_m[:, None]
        sigma[below_surface] = 1.0 / rock_resistivity[below_surface]
        epsilon_r[below_surface] = self.lithosphere_relative_permittivity

        water_layers = (
            (~is_land)[:, None]
            & (altitudes[None, :] < 0.0)
            & (altitudes[None, :] >= surface_elevation_m[:, None])
        )
        sigma[water_layers] = 1.0 / self.sea_water_resistivity_ohm_m
        epsilon_r[water_layers] = self.sea_water_relative_permittivity
        return sigma, epsilon_r
