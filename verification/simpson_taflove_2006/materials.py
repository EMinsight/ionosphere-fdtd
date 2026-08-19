"""Dissertation-informed material hypotheses for the 2006 radar study."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..simpson_taflove_2004.materials import SimpsonTaflove2004Material


@dataclass(frozen=True, slots=True)
class HermanceFigure15Material(SimpsonTaflove2004Material):
    """Piecewise hypothesis digitized from dissertation Figure 15.

    Figure 15 is a schematic with inequality-valued resistivity classes, not a
    cellwise global model. The class limits are used as representative values,
    and the visually indicated boundaries are snapped to the nominal 5 km
    radial grid. The isolated continental conductor marked in the figure is
    intentionally omitted because its location is not specified.
    """

    continental_surface_resistivity_ohm_m: float = 10.0
    continental_surface_bottom_depth_m: float = 5_000.0
    continental_crust_resistivity_ohm_m: float = 5_000.0
    continental_crust_bottom_depth_m: float = 45_000.0
    ocean_sediment_resistivity_ohm_m: float = 5.0
    ocean_sediment_bottom_depth_m: float = 5_000.0
    ocean_lower_crust_resistivity_ohm_m: float = 50.0
    ocean_lower_crust_bottom_depth_m: float = 10_000.0
    ocean_resistive_mantle_resistivity_ohm_m: float = 500.0
    ocean_resistive_mantle_bottom_depth_m: float = 20_000.0
    ocean_asthenosphere_resistivity_ohm_m: float = 200.0
    ocean_asthenosphere_bottom_depth_m: float = 45_000.0
    figure_15_deep_resistivity_ohm_m: float = 50.0

    def __post_init__(self) -> None:
        super(HermanceFigure15Material, self).__post_init__()
        parameters = (
            self.continental_surface_resistivity_ohm_m,
            self.continental_surface_bottom_depth_m,
            self.continental_crust_resistivity_ohm_m,
            self.continental_crust_bottom_depth_m,
            self.ocean_sediment_resistivity_ohm_m,
            self.ocean_sediment_bottom_depth_m,
            self.ocean_lower_crust_resistivity_ohm_m,
            self.ocean_lower_crust_bottom_depth_m,
            self.ocean_resistive_mantle_resistivity_ohm_m,
            self.ocean_resistive_mantle_bottom_depth_m,
            self.ocean_asthenosphere_resistivity_ohm_m,
            self.ocean_asthenosphere_bottom_depth_m,
            self.figure_15_deep_resistivity_ohm_m,
        )
        if not all(np.isfinite(value) and value > 0.0 for value in parameters):
            raise ValueError("Figure 15 material parameters must be positive")
        if not (
            self.ocean_sediment_bottom_depth_m
            < self.ocean_lower_crust_bottom_depth_m
            < self.ocean_resistive_mantle_bottom_depth_m
            < self.ocean_asthenosphere_bottom_depth_m
        ):
            raise ValueError("Figure 15 ocean depth bounds must increase")
        if not (
            self.continental_surface_bottom_depth_m
            < self.continental_crust_bottom_depth_m
        ):
            raise ValueError("Figure 15 continental depth bounds must increase")

    def _rock_resistivity(
        self, is_land: np.ndarray, altitudes_m: np.ndarray
    ) -> np.ndarray:
        """Return Figure 15 classes at each E-field sampling direction."""

        depth = np.maximum(-np.asarray(altitudes_m, dtype=np.float64), 0.0)
        continent = np.select(
            (
                depth < self.continental_surface_bottom_depth_m,
                depth < self.continental_crust_bottom_depth_m,
            ),
            (
                self.continental_surface_resistivity_ohm_m,
                self.continental_crust_resistivity_ohm_m,
            ),
            default=self.figure_15_deep_resistivity_ohm_m,
        )
        ocean = np.select(
            (
                depth < self.ocean_sediment_bottom_depth_m,
                depth < self.ocean_lower_crust_bottom_depth_m,
                depth < self.ocean_resistive_mantle_bottom_depth_m,
                depth < self.ocean_asthenosphere_bottom_depth_m,
            ),
            (
                self.ocean_sediment_resistivity_ohm_m,
                self.ocean_lower_crust_resistivity_ohm_m,
                self.ocean_resistive_mantle_resistivity_ohm_m,
                self.ocean_asthenosphere_resistivity_ohm_m,
            ),
            default=self.figure_15_deep_resistivity_ohm_m,
        )
        return np.where(
            np.asarray(is_land)[:, None], continent[None, :], ocean[None, :]
        )
