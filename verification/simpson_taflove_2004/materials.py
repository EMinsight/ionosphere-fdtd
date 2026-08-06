"""Paper-specific material inputs for Simpson and Taflove (2004)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from ionosphere_fdtd.materials import (
    FloatArray,
    LandClassifier,
    LayeredEarthIonosphereMaterial,
    ReliefSampler,
    SphericalAnomaly,
)

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
        result = north + row_fraction * (south - north)

        # Longitude is undefined at an exact pole. The south-most ETOPO5 row
        # is not longitudinally constant, so choosing atan2(0, 0)'s arbitrary
        # longitude would make a polar mesh vertex orientation-dependent.
        polar = np.hypot(points[:, 0], points[:, 1]) <= (
            64.0 * np.finfo(np.float64).eps
        )
        if np.any(polar):
            pole_rows = np.where(points[polar, 2] >= 0.0, 0, ETOPO5_SHAPE[0] - 1)
            result[polar] = np.asarray(
                [
                    np.mean(self.elevations_m[index], dtype=np.float64)
                    for index in pole_rows
                ]
            )
        return result


@dataclass(frozen=True, slots=True)
class SimpsonTaflove2004Material(LayeredEarthIonosphereMaterial):
    """Figure 6 layers with the cited Bannister daytime ionosphere profile."""

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
