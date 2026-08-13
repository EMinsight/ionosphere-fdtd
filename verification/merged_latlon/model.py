"""Conservative cell-centered Laplacian on an adaptively merged sphere grid."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from numpy.typing import NDArray
from scipy.special import sph_harm_y

from ionosphere_fdtd.constants import EARTH_RADIUS_M


@dataclass(frozen=True, slots=True)
class MergedLatLonGrid:
    equatorial_longitudes: int
    latitude_edges_rad: NDArray[np.float64]
    band_longitudes: NDArray[np.int64]
    offsets: NDArray[np.int64]
    latitude_rad: NDArray[np.float64]
    longitude_rad: NDArray[np.float64]
    area_m2: NDArray[np.float64]
    edge_left: NDArray[np.int64]
    edge_right: NDArray[np.int64]
    edge_conductance: NDArray[np.float64]

    @property
    def cell_count(self) -> int:
        return len(self.area_m2)


@dataclass(frozen=True, slots=True)
class HarmonicResult:
    degree: int
    eigenvalue: float
    relative_eigenvalue_error: float
    relative_wavenumber_error: float
    residual: float
    energy: float


def build_merged_grid(equatorial_longitudes: int) -> MergedLatLonGrid:
    if equatorial_longitudes < 16 or equatorial_longitudes % 2:
        raise ValueError("equatorial_longitudes must be an even integer >= 16")
    latitude_count = equatorial_longitudes // 2
    latitude_edges = np.linspace(-0.5 * np.pi, 0.5 * np.pi, latitude_count + 1)
    latitude_centers = 0.5 * (latitude_edges[:-1] + latitude_edges[1:])
    target = equatorial_longitudes * np.maximum(np.cos(latitude_centers), 4.0 / equatorial_longitudes)
    # Merge only after the east-west width has fallen below one half of the
    # equatorial width; every transition then doubles the represented span.
    merge_power = np.maximum(0, np.floor(np.log2(equatorial_longitudes / target))).astype(int)
    band_longitudes = np.maximum(4, equatorial_longitudes // (2**merge_power)).astype(np.int64)
    offsets = np.concatenate(([0], np.cumsum(band_longitudes))).astype(np.int64)
    latitude = np.repeat(latitude_centers, band_longitudes)
    longitude = np.concatenate([
        (np.arange(count) + 0.5) * 2.0 * np.pi / count - np.pi
        for count in band_longitudes
    ])
    band_area = 2.0 * np.pi * EARTH_RADIUS_M**2 * np.diff(np.sin(latitude_edges))
    area = np.repeat(band_area / band_longitudes, band_longitudes)
    left = []
    right = []
    conductance = []
    dlat = np.pi / latitude_count
    for band, count in enumerate(band_longitudes):
        ids = offsets[band] + np.arange(count)
        left.extend(ids.tolist())
        right.extend(np.roll(ids, -1).tolist())
        conductance.extend(np.full(count, dlat / (np.cos(latitude_centers[band]) * 2.0 * np.pi / count)).tolist())
    for band in range(latitude_count - 1):
        south = int(band_longitudes[band]); north = int(band_longitudes[band + 1])
        fine = max(south, north); overlap = 2.0 * np.pi / fine
        for index in range(fine):
            south_index = index * south // fine
            north_index = index * north // fine
            left.append(int(offsets[band] + south_index))
            right.append(int(offsets[band + 1] + north_index))
            conductance.append(float(np.cos(latitude_edges[band + 1]) * overlap / dlat))
    return MergedLatLonGrid(
        equatorial_longitudes, latitude_edges, band_longitudes, offsets,
        latitude, longitude, area, np.asarray(left), np.asarray(right),
        np.asarray(conductance),
    )


def apply_negative_laplacian(grid: MergedLatLonGrid, values: NDArray[np.float64]) -> NDArray[np.float64]:
    values = np.asarray(values, dtype=np.float64)
    if values.shape != (grid.cell_count,):
        raise ValueError("values must contain one scalar per cell")
    flux = grid.edge_conductance * (values[grid.edge_left] - values[grid.edge_right])
    result = np.zeros_like(values)
    np.add.at(result, grid.edge_left, flux)
    np.add.at(result, grid.edge_right, -flux)
    return result / grid.area_m2


def harmonic_result(grid: MergedLatLonGrid, degree: int, order: int | None = None) -> HarmonicResult:
    if degree < 1:
        raise ValueError("degree must be positive")
    order = degree if order is None else order
    colatitude = 0.5 * np.pi - grid.latitude_rad
    values = sph_harm_y(degree, order, colatitude, grid.longitude_rad).real
    applied = apply_negative_laplacian(grid, values)
    norm = np.sum(grid.area_m2 * values**2)
    eigenvalue = float(np.sum(grid.area_m2 * values * applied) / norm)
    exact = degree * (degree + 1.0) / EARTH_RADIUS_M**2
    residual = float(np.sqrt(np.sum(grid.area_m2 * (applied - eigenvalue * values) ** 2) / np.sum(grid.area_m2 * applied**2)))
    energy = float(np.sum(grid.area_m2 * values * applied))
    return HarmonicResult(
        degree, eigenvalue, eigenvalue / exact - 1.0,
        np.sqrt(eigenvalue / exact) - 1.0, residual, energy,
    )


def conservative_cfl_bound_s(grid: MergedLatLonGrid, wave_speed_m_s: float) -> float:
    diagonal = np.zeros(grid.cell_count)
    np.add.at(diagonal, grid.edge_left, grid.edge_conductance)
    np.add.at(diagonal, grid.edge_right, grid.edge_conductance)
    maximum_eigenvalue_bound = 2.0 * np.max(diagonal / grid.area_m2)
    return float(2.0 / (wave_speed_m_s * np.sqrt(maximum_eigenvalue_bound)))
