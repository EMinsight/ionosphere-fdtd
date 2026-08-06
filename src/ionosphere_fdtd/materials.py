"""Configurable radial Earth/atmosphere conductivity model."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace

import numpy as np
from numpy.typing import NDArray

from .constants import EPSILON_0

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]
LandClassifier = Callable[[FloatArray], BoolArray]
ReliefSampler = Callable[[FloatArray], FloatArray]

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
    maximum_background_conductivity_s_m: float | None = None
    target_area_m2: float | None = None

    def __post_init__(self) -> None:
        finite = (
            self.latitude_deg,
            self.longitude_deg,
            self.radius_m,
            self.altitude_min_m,
            self.altitude_max_m,
            self.conductivity_factor,
        )
        if not all(np.isfinite(value) for value in finite):
            raise ValueError("anomaly geometry and conductivity must be finite")
        if not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("anomaly latitude must be in [-90, 90]")
        if self.radius_m <= 0.0:
            raise ValueError("anomaly radius_m must be positive")
        if self.altitude_min_m > self.altitude_max_m:
            raise ValueError("anomaly altitude bounds are reversed")
        if self.conductivity_factor <= 0.0:
            raise ValueError("conductivity_factor must be positive")
        if self.relative_permittivity is not None and (
            not np.isfinite(self.relative_permittivity)
            or self.relative_permittivity <= 0.0
        ):
            raise ValueError("relative permittivity must be finite and positive")
        if (
            self.maximum_background_conductivity_s_m is not None
            and (
                not np.isfinite(self.maximum_background_conductivity_s_m)
                or self.maximum_background_conductivity_s_m <= 0.0
            )
        ):
            raise ValueError(
                "maximum background conductivity must be finite and positive"
            )
        if self.target_area_m2 is not None and (
            not np.isfinite(self.target_area_m2) or self.target_area_m2 <= 0.0
        ):
            raise ValueError("target anomaly area must be finite and positive")

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


def _apply_spherical_anomalies(
    sigma: FloatArray,
    epsilon_r: FloatArray,
    directions: FloatArray,
    altitudes_m: FloatArray,
    earth_radius_m: float,
    anomalies: tuple[SphericalAnomaly, ...],
) -> None:
    """Apply configured spherical-volume overrides in place."""

    for anomaly in anomalies:
        angular_radius = anomaly.radius_m / earth_radius_m
        inside_horizontal = np.arccos(
            np.clip(directions @ anomaly.center, -1.0, 1.0)
        ) <= angular_radius
        inside_vertical = (altitudes_m >= anomaly.altitude_min_m) & (
            altitudes_m <= anomaly.altitude_max_m
        )
        inside = inside_horizontal[:, None] & inside_vertical[None, :]
        if anomaly.maximum_background_conductivity_s_m is not None:
            inside &= sigma <= anomaly.maximum_background_conductivity_s_m
        sigma[inside] *= anomaly.conductivity_factor
        if anomaly.relative_permittivity is not None:
            epsilon_r[inside] = anomaly.relative_permittivity


def _apply_cell_averaged_spherical_anomalies(
    sigma: FloatArray,
    epsilon_r: FloatArray,
    directions: FloatArray,
    lower_altitudes_m: FloatArray,
    upper_altitudes_m: FloatArray,
    earth_radius_m: float,
    anomalies: tuple[SphericalAnomaly, ...],
) -> None:
    """Apply radial overlap fractions for tangential electric cells."""

    widths = upper_altitudes_m - lower_altitudes_m
    for anomaly in anomalies:
        angular_radius = anomaly.radius_m / earth_radius_m
        inside_horizontal = np.arccos(
            np.clip(directions @ anomaly.center, -1.0, 1.0)
        ) <= angular_radius
        overlap = np.clip(
            np.minimum(upper_altitudes_m, anomaly.altitude_max_m)
            - np.maximum(lower_altitudes_m, anomaly.altitude_min_m),
            0.0,
            widths,
        )
        fraction = inside_horizontal[:, None] * (overlap / widths)[None, :]
        if anomaly.maximum_background_conductivity_s_m is not None:
            fraction = np.where(
                sigma <= anomaly.maximum_background_conductivity_s_m,
                fraction,
                0.0,
            )
        sigma *= 1.0 + fraction * (anomaly.conductivity_factor - 1.0)
        if anomaly.relative_permittivity is not None:
            epsilon_r *= 1.0 - fraction
            epsilon_r += fraction * anomaly.relative_permittivity


def conservative_anomaly_fractions(
    directions: FloatArray,
    support_solid_angles: FloatArray,
    anomaly: SphericalAnomaly,
    earth_radius_m: float,
) -> FloatArray:
    """Rasterize a circular anomaly while preserving its configured area."""

    points = np.asarray(directions, dtype=np.float64)
    areas = np.asarray(support_solid_angles, dtype=np.float64)
    if points.shape != (len(areas), 3) or np.any(areas <= 0.0):
        raise ValueError("anomaly supports must have positive areas and directions")
    target = (
        anomaly.target_area_m2 / earth_radius_m**2
        if anomaly.target_area_m2 is not None
        else 2.0 * np.pi * (1.0 - np.cos(anomaly.radius_m / earth_radius_m))
    )
    if target > float(np.sum(areas)):
        raise ValueError("anomaly area exceeds the available spherical supports")
    distance = np.arccos(np.clip(points @ anomaly.center, -1.0, 1.0))
    order = np.argsort(distance, kind="stable")
    fractions = np.zeros(len(areas), dtype=np.float64)
    remaining = target
    for index in order:
        if remaining <= 0.0:
            break
        covered = min(float(areas[index]), remaining)
        fractions[index] = covered / areas[index]
        remaining -= covered
    if remaining > 64.0 * np.finfo(np.float64).eps * target:
        raise RuntimeError("conservative anomaly rasterization did not close")
    return fractions


def apply_fractional_point_anomalies(
    sigma: FloatArray,
    epsilon_r: FloatArray,
    altitudes_m: FloatArray,
    anomalies: tuple[SphericalAnomaly, ...],
    horizontal_fractions: tuple[FloatArray, ...],
) -> None:
    """Apply support-area fractions to point-sampled radial electric fields."""

    for anomaly, horizontal in zip(anomalies, horizontal_fractions, strict=True):
        inside_vertical = (altitudes_m >= anomaly.altitude_min_m) & (
            altitudes_m <= anomaly.altitude_max_m
        )
        fraction = horizontal[:, None] * inside_vertical[None, :]
        _mix_anomaly_fraction(sigma, epsilon_r, fraction, anomaly)


def apply_fractional_cell_anomalies(
    sigma: FloatArray,
    epsilon_r: FloatArray,
    lower_altitudes_m: FloatArray,
    upper_altitudes_m: FloatArray,
    anomalies: tuple[SphericalAnomaly, ...],
    horizontal_fractions: tuple[FloatArray, ...],
) -> None:
    """Apply horizontal area and radial overlap fractions to Et cells."""

    widths = upper_altitudes_m - lower_altitudes_m
    for anomaly, horizontal in zip(anomalies, horizontal_fractions, strict=True):
        overlap = np.clip(
            np.minimum(upper_altitudes_m, anomaly.altitude_max_m)
            - np.maximum(lower_altitudes_m, anomaly.altitude_min_m),
            0.0,
            widths,
        )
        fraction = horizontal[:, None] * (overlap / widths)[None, :]
        _mix_anomaly_fraction(sigma, epsilon_r, fraction, anomaly)


def _mix_anomaly_fraction(
    sigma: FloatArray,
    epsilon_r: FloatArray,
    fraction: FloatArray,
    anomaly: SphericalAnomaly,
) -> None:
    if anomaly.maximum_background_conductivity_s_m is not None:
        fraction = np.where(
            sigma <= anomaly.maximum_background_conductivity_s_m,
            fraction,
            0.0,
        )
    sigma *= 1.0 + fraction * (anomaly.conductivity_factor - 1.0)
    if anomaly.relative_permittivity is not None:
        epsilon_r *= 1.0 - fraction
        epsilon_r += fraction * anomaly.relative_permittivity


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
        parameters = (
            self.lithosphere_conductivity_s_m,
            self.lithosphere_relative_permittivity,
            self.atmosphere_relative_permittivity,
            self.ionosphere_reference_height_m,
            self.ionosphere_scale_height_m,
            self.ionosphere_prefactor_hz,
        )
        if not all(np.isfinite(value) for value in parameters):
            raise ValueError("material parameters must be finite")
        if self.lithosphere_conductivity_s_m < 0.0:
            raise ValueError("lithosphere conductivity cannot be negative")
        if self.lithosphere_relative_permittivity < 1.0:
            raise ValueError("lithosphere relative permittivity must be >= 1")
        if self.atmosphere_relative_permittivity < 1.0:
            raise ValueError("atmosphere relative permittivity must be >= 1")
        if self.ionosphere_scale_height_m <= 0.0:
            raise ValueError("ionosphere scale height must be positive")
        if self.ionosphere_prefactor_hz < 0.0:
            raise ValueError("ionosphere prefactor cannot be negative")

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

        _apply_spherical_anomalies(
            sigma,
            epsilon_r,
            directions,
            altitudes,
            earth_radius_m,
            self.anomalies,
        )
        return sigma, epsilon_r


@dataclass(frozen=True, slots=True)
class LayeredEarthIonosphereMaterial:
    """Configurable relief-aware ocean, rock, atmosphere, and ionosphere layers.

    A relief sampler provides surface elevation and bathymetry when supplied;
    a land classifier provides a fixed-ocean-depth fallback. Conductivity,
    permittivity, depth bounds, and exponential-ionosphere parameters remain
    explicit so applications can define a documented material preset without
    coupling the FDTD solver to a particular study.
    """

    land_classifier: LandClassifier | None = None
    surface_elevation_sampler: ReliefSampler | None = None
    ocean_depth_m: float = 5_000.0
    sea_water_resistivity_ohm_m: float = 0.3
    upper_crust_resistivity_ohm_m: float = 500.0
    asthenosphere_resistivity_ohm_m: float = 200.0
    deep_rock_resistivity_ohm_m: float = 500.0
    asthenosphere_top_depth_m: float = 20_000.0
    asthenosphere_bottom_depth_m: float = 60_000.0
    lithosphere_relative_permittivity: float = 10.0
    sea_water_relative_permittivity: float = 80.0
    atmosphere_relative_permittivity: float = 1.0
    ionosphere_reference_height_m: float = 70_000.0
    ionosphere_scale_height_m: float = 1_000.0 / 0.3
    ionosphere_prefactor_hz: float = 2.5e5
    anomalies: tuple[SphericalAnomaly, ...] = field(default_factory=tuple)
    tangential_interface_mode: str = "point"
    minimum_ocean_depth_m: float = 0.0

    def __post_init__(self) -> None:
        if (self.land_classifier is None) == (
            self.surface_elevation_sampler is None
        ):
            raise ValueError(
                "provide exactly one of land_classifier or surface_elevation_sampler"
            )
        parameters = (
            self.ocean_depth_m,
            self.sea_water_resistivity_ohm_m,
            self.upper_crust_resistivity_ohm_m,
            self.asthenosphere_resistivity_ohm_m,
            self.deep_rock_resistivity_ohm_m,
            self.asthenosphere_top_depth_m,
            self.asthenosphere_bottom_depth_m,
            self.lithosphere_relative_permittivity,
            self.sea_water_relative_permittivity,
            self.atmosphere_relative_permittivity,
            self.ionosphere_reference_height_m,
            self.ionosphere_scale_height_m,
            self.ionosphere_prefactor_hz,
            self.minimum_ocean_depth_m,
        )
        if not all(np.isfinite(value) for value in parameters):
            raise ValueError("material parameters must be finite")
        positive = (
            self.ocean_depth_m,
            self.sea_water_resistivity_ohm_m,
            self.upper_crust_resistivity_ohm_m,
            self.asthenosphere_resistivity_ohm_m,
            self.deep_rock_resistivity_ohm_m,
            self.asthenosphere_top_depth_m,
            self.asthenosphere_bottom_depth_m,
            self.ionosphere_scale_height_m,
        )
        if any(value <= 0.0 for value in positive):
            raise ValueError("material lengths and resistivities must be positive")
        if self.minimum_ocean_depth_m < 0.0:
            raise ValueError("minimum ocean depth cannot be negative")
        if self.ionosphere_prefactor_hz < 0.0:
            raise ValueError("ionosphere prefactor cannot be negative")
        if self.asthenosphere_top_depth_m >= self.asthenosphere_bottom_depth_m:
            raise ValueError("asthenosphere depth bounds are reversed")
        if min(
            self.lithosphere_relative_permittivity,
            self.sea_water_relative_permittivity,
            self.atmosphere_relative_permittivity,
        ) < 1.0:
            raise ValueError("relative permittivity must be >= 1")
        if self.tangential_interface_mode not in {"point", "fractional"}:
            raise ValueError(
                "tangential_interface_mode must be 'point' or 'fractional'"
            )

    def _surface_geometry(
        self, directions: FloatArray
    ) -> tuple[FloatArray, BoolArray, FloatArray]:
        """Normalize directions and return land flags and surface elevations."""

        normalized = np.array(directions, dtype=np.float64, copy=True)
        normalized /= np.linalg.norm(normalized, axis=1, keepdims=True)
        if self.surface_elevation_sampler is None:
            assert self.land_classifier is not None
            is_land = np.asarray(self.land_classifier(normalized), dtype=np.bool_)
            surface_elevation_m = np.where(is_land, 0.0, -self.ocean_depth_m)
        else:
            surface_elevation_m = np.asarray(
                self.surface_elevation_sampler(normalized), dtype=np.float64
            )
            is_land = surface_elevation_m >= 0.0
        if is_land.shape != (len(normalized),):
            raise ValueError("surface data must return one value per direction")
        if not np.all(np.isfinite(surface_elevation_m)):
            raise ValueError("surface elevations must be finite")
        surface_elevation_m = np.where(
            is_land,
            surface_elevation_m,
            np.minimum(surface_elevation_m, -self.minimum_ocean_depth_m),
        )
        return normalized, is_land, surface_elevation_m

    def _rock_resistivity(
        self, is_land: BoolArray, altitudes_m: FloatArray
    ) -> FloatArray:
        """Return representative rock resistivity at requested altitudes."""

        depth = np.maximum(-altitudes_m, 0.0)
        ocean = np.where(
            depth >= self.asthenosphere_bottom_depth_m,
            self.deep_rock_resistivity_ohm_m,
            np.where(
                depth >= self.asthenosphere_top_depth_m,
                self.asthenosphere_resistivity_ohm_m,
                self.upper_crust_resistivity_ohm_m,
            ),
        )
        continent = np.where(
            depth >= self.asthenosphere_bottom_depth_m,
            self.deep_rock_resistivity_ohm_m,
            self.upper_crust_resistivity_ohm_m,
        )
        return np.where(is_land[:, None], continent[None, :], ocean[None, :])

    def sample(
        self,
        directions: FloatArray,
        altitudes_m: FloatArray,
        earth_radius_m: float,
    ) -> tuple[FloatArray, FloatArray]:
        """Return conductivity and permittivity on the requested tensor grid."""

        directions, is_land, surface_elevation_m = self._surface_geometry(
            directions
        )
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
        sigma = np.broadcast_to(
            sigma_air, (len(directions), len(altitudes))
        ).copy()
        epsilon_r = np.full_like(sigma, self.atmosphere_relative_permittivity)

        rock_resistivity = self._rock_resistivity(is_land, altitudes)
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
        _apply_spherical_anomalies(
            sigma,
            epsilon_r,
            directions,
            altitudes,
            earth_radius_m,
            self.anomalies,
        )
        return sigma, epsilon_r

    def sample_tangential_cells(
        self,
        directions: FloatArray,
        lower_altitudes_m: FloatArray,
        upper_altitudes_m: FloatArray,
        earth_radius_m: float,
    ) -> tuple[FloatArray, FloatArray]:
        """Return cell-averaged properties parallel to radial interfaces."""

        lower = np.asarray(lower_altitudes_m, dtype=np.float64)
        upper = np.asarray(upper_altitudes_m, dtype=np.float64)
        if lower.ndim != 1 or upper.shape != lower.shape:
            raise ValueError("radial cell bounds must be matching 1-D arrays")
        if np.any(upper <= lower):
            raise ValueError("radial cell upper bounds must exceed lower bounds")
        midpoints = 0.5 * (lower + upper)
        if self.tangential_interface_mode == "point":
            background = replace(self, anomalies=())
            sigma, epsilon_r = background.sample(
                directions, midpoints, earth_radius_m
            )
            normalized = np.array(directions, dtype=np.float64, copy=True)
            normalized /= np.linalg.norm(normalized, axis=1, keepdims=True)
            _apply_cell_averaged_spherical_anomalies(
                sigma,
                epsilon_r,
                normalized,
                lower,
                upper,
                earth_radius_m,
                self.anomalies,
            )
            return sigma, epsilon_r

        directions, is_land, surface = self._surface_geometry(directions)
        width = upper - lower
        lower_2d = lower[None, :]
        upper_2d = upper[None, :]
        width_2d = width[None, :]
        surface_2d = surface[:, None]

        rock_thickness = np.clip(
            np.minimum(upper_2d, surface_2d) - lower_2d,
            0.0,
            width_2d,
        )
        water_thickness = np.where(
            (~is_land)[:, None],
            np.clip(
                np.minimum(upper_2d, 0.0)
                - np.maximum(lower_2d, surface_2d),
                0.0,
                width_2d,
            ),
            0.0,
        )
        air_floor = np.where(is_land, surface, 0.0)[:, None]
        air_thickness = np.clip(
            upper_2d - np.maximum(lower_2d, air_floor),
            0.0,
            width_2d,
        )
        fractions = np.stack(
            (
                rock_thickness / width_2d,
                water_thickness / width_2d,
                air_thickness / width_2d,
            )
        )
        if not np.allclose(fractions.sum(axis=0), 1.0, atol=1.0e-12):
            raise RuntimeError("radial material fractions do not close")

        sigma_air = (
            self.ionosphere_prefactor_hz
            * EPSILON_0
            * np.exp(
                np.clip(
                    (midpoints - self.ionosphere_reference_height_m)
                    / self.ionosphere_scale_height_m,
                    -80.0,
                    80.0,
                )
            )
        )
        sigma_rock = 1.0 / self._rock_resistivity(is_land, midpoints)
        sigma = (
            fractions[0] * sigma_rock
            + fractions[1] / self.sea_water_resistivity_ohm_m
            + fractions[2] * sigma_air[None, :]
        )
        epsilon_r = (
            fractions[0] * self.lithosphere_relative_permittivity
            + fractions[1] * self.sea_water_relative_permittivity
            + fractions[2] * self.atmosphere_relative_permittivity
        )
        _apply_cell_averaged_spherical_anomalies(
            sigma,
            epsilon_r,
            directions,
            lower,
            upper,
            earth_radius_m,
            self.anomalies,
        )
        return sigma, epsilon_r
