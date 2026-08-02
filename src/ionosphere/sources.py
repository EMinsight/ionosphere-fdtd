"""Current sources for the radial electric-field update."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from .solver import GeodesicFDTD

GWANGJU_LATITUDE_DEG = 35.1595
GWANGJU_LONGITUDE_DEG = 126.8526


def geographic_direction(
    latitude_deg: float, longitude_deg: float
) -> NDArray[np.float64]:
    """Return a unit vector for a geographic latitude and longitude."""

    latitude = np.deg2rad(latitude_deg)
    longitude = np.deg2rad(longitude_deg)
    return np.asarray(
        (
            np.cos(latitude) * np.cos(longitude),
            np.cos(latitude) * np.sin(longitude),
            np.sin(latitude),
        ),
        dtype=np.float64,
    )


def geographic_distribution(
    simulation: GeodesicFDTD,
    latitude_deg: float,
    longitude_deg: float,
    altitude_m: float,
) -> tuple[NDArray[np.int64], int, NDArray[np.float64]]:
    """Return triangle vertices, radial layer, and barycentric weights."""

    direction = geographic_direction(latitude_deg, longitude_deg)
    faces = simulation.mesh.faces
    triangles = simulation.mesh.vertices[faces]
    signs = np.column_stack(
        tuple(
            np.einsum(
                "ij,j->i",
                np.cross(triangles[:, edge], triangles[:, (edge + 1) % 3]),
                direction,
            )
            for edge in range(3)
        )
    )
    inside = np.all(signs >= -1.0e-12, axis=1) | np.all(
        signs <= 1.0e-12, axis=1
    )
    candidates = np.flatnonzero(inside)
    face_index = (
        int(candidates[0])
        if len(candidates)
        else int(np.argmax(simulation.mesh.face_centers @ direction))
    )
    vertices = faces[face_index]
    point_a, point_b, point_c = simulation.mesh.vertices[vertices]
    normal = np.cross(point_b - point_a, point_c - point_a)
    intersection = direction * float((normal @ point_a) / (normal @ direction))
    edge_ab = point_b - point_a
    edge_ac = point_c - point_a
    point_offset = intersection - point_a
    dot_ab_ab = float(edge_ab @ edge_ab)
    dot_ab_ac = float(edge_ab @ edge_ac)
    dot_ac_ac = float(edge_ac @ edge_ac)
    dot_offset_ab = float(point_offset @ edge_ab)
    dot_offset_ac = float(point_offset @ edge_ac)
    denominator = dot_ab_ab * dot_ac_ac - dot_ab_ac**2
    weight_b = (
        dot_ac_ac * dot_offset_ab - dot_ab_ac * dot_offset_ac
    ) / denominator
    weight_c = (
        dot_ab_ab * dot_offset_ac - dot_ab_ac * dot_offset_ab
    ) / denominator
    weights = np.asarray((1.0 - weight_b - weight_c, weight_b, weight_c))
    weights = np.clip(weights, 0.0, None)
    weights /= weights.sum()
    layer = int(np.argmin(np.abs(simulation.altitudes_m - altitude_m)))
    return vertices.copy(), layer, weights


@dataclass(frozen=True, slots=True)
class GaussianCurrent:
    """Localized vertical current with a Gaussian (optionally modulated) pulse."""

    latitude_deg: float = GWANGJU_LATITUDE_DEG
    longitude_deg: float = GWANGJU_LONGITUDE_DEG
    altitude_m: float = 2_500.0
    peak_current_a: float = 1.0e6
    center_time_s: float | None = None
    one_over_e_half_width_s: float | None = None
    carrier_frequency_hz: float = 0.0

    def direction(self) -> NDArray[np.float64]:
        """Return the exact geographic source direction."""

        return geographic_direction(self.latitude_deg, self.longitude_deg)

    def location(self, simulation: GeodesicFDTD) -> tuple[int, int]:
        """Return the nearest surface vertex and radial layer."""

        direction = self.direction()
        vertex = int(np.argmax(simulation.mesh.vertices @ direction))
        layer = int(np.argmin(np.abs(simulation.altitudes_m - self.altitude_m)))
        return vertex, layer

    def distribution(
        self, simulation: GeodesicFDTD
    ) -> tuple[NDArray[np.int64], int, NDArray[np.float64]]:
        """Distribute current over the triangle containing the exact location."""

        return geographic_distribution(
            simulation,
            self.latitude_deg,
            self.longitude_deg,
            self.altitude_m,
        )

    def current_a(self, time_s: float, dt_s: float) -> float:
        if self.one_over_e_half_width_s is not None:
            half_width = self.one_over_e_half_width_s
        elif self.carrier_frequency_hz:
            # At 20 Hz this is 25 ms, close to the 42.5 ms FWHM Gaussian
            # envelope used for the radar example in Simpson et al.
            half_width = 0.5 / self.carrier_frequency_hz
        else:
            half_width = 12.0 * dt_s
        center = (
            self.center_time_s
            if self.center_time_s is not None
            else max(4.0 * half_width, 36.0 * dt_s)
        )
        envelope = np.exp(-((time_s - center) / half_width) ** 2)
        if self.carrier_frequency_hz:
            envelope *= np.cos(2.0 * np.pi * self.carrier_frequency_hz * (time_s - center))
        return float(self.peak_current_a * envelope)
