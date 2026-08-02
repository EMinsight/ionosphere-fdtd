"""Current sources for the radial electric-field update."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .solver import GeodesicFDTD


@dataclass(frozen=True, slots=True)
class GaussianCurrent:
    """Localized vertical current with a Gaussian (optionally modulated) pulse."""

    latitude_deg: float = 0.0
    longitude_deg: float = -47.0
    altitude_m: float = 2_500.0
    peak_current_a: float = 1.0e6
    center_time_s: float | None = None
    one_over_e_half_width_s: float | None = None
    carrier_frequency_hz: float = 0.0

    def location(self, simulation: GeodesicFDTD) -> tuple[int, int]:
        latitude = np.deg2rad(self.latitude_deg)
        longitude = np.deg2rad(self.longitude_deg)
        direction = np.asarray(
            (
                np.cos(latitude) * np.cos(longitude),
                np.cos(latitude) * np.sin(longitude),
                np.sin(latitude),
            )
        )
        vertex = int(np.argmax(simulation.mesh.vertices @ direction))
        layer = int(np.argmin(np.abs(simulation.altitudes_m - self.altitude_m)))
        return vertex, layer

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
