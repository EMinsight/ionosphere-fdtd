"""Vectorized 3-D geodesic FDTD time stepping."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .constants import C_0, EARTH_RADIUS_M, EPSILON_0, MU_0
from .materials import EarthIonosphereMaterial
from .mesh import GeodesicMesh, build_geodesic_mesh
from .sources import GaussianCurrent

FloatArray = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    """Geometry and integration controls for a simulation."""

    subdivision: int = 2
    radial_cells: int = 24
    minimum_altitude_m: float = -100_000.0
    maximum_altitude_m: float = 100_000.0
    earth_radius_m: float = EARTH_RADIUS_M
    courant_factor: float = 0.35
    time_step_s: float | None = None
    mesh_relaxations: int = 0
    radial_altitudes_m: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        if self.subdivision < 0:
            raise ValueError("subdivision must be non-negative")
        if self.radial_cells < 2:
            raise ValueError("radial_cells must be at least 2")
        if self.minimum_altitude_m >= self.maximum_altitude_m:
            raise ValueError("altitude bounds are reversed")
        if self.earth_radius_m + self.minimum_altitude_m <= 0.0:
            raise ValueError("minimum radius must be positive")
        if not 0.0 < self.courant_factor <= 1.0:
            raise ValueError("courant_factor must be in (0, 1]")
        if self.time_step_s is not None and self.time_step_s <= 0.0:
            raise ValueError("time_step_s must be positive")
        if self.radial_altitudes_m is not None:
            altitudes = np.asarray(self.radial_altitudes_m, dtype=np.float64)
            if len(altitudes) < 3 or not np.all(np.diff(altitudes) > 0.0):
                raise ValueError(
                    "radial_altitudes_m must contain at least three increasing values"
                )
            if (
                altitudes[0] != self.minimum_altitude_m
                or altitudes[-1] != self.maximum_altitude_m
            ):
                raise ValueError(
                    "custom radial altitudes must include the configured altitude bounds"
                )


class GeodesicFDTD:
    """Earth-ionosphere FDTD model using staggered geodesic radial planes.

    ``er`` and ``ht`` live on integer radial planes (TM-r), while ``hr`` and
    ``et`` live halfway between them (TE-r).  Magnetic fields are staggered by
    half a time step from electric fields, as in the Yee algorithm.
    """

    def __init__(
        self,
        config: SimulationConfig | None = None,
        material: EarthIonosphereMaterial | None = None,
        source: GaussianCurrent | None = None,
        mesh: GeodesicMesh | None = None,
    ) -> None:
        self.config = config or SimulationConfig()
        self.mesh = mesh or build_geodesic_mesh(
            self.config.subdivision, self.config.mesh_relaxations
        )
        if self.mesh.subdivision != self.config.subdivision:
            raise ValueError("provided mesh subdivision does not match config")
        self.material = material or EarthIonosphereMaterial()
        self.source = source

        if self.config.radial_altitudes_m is None:
            self.altitudes_m = np.linspace(
                self.config.minimum_altitude_m,
                self.config.maximum_altitude_m,
                self.config.radial_cells + 1,
            )
        else:
            self.altitudes_m = np.asarray(
                self.config.radial_altitudes_m, dtype=np.float64
            )
        self.radii_m = self.config.earth_radius_m + self.altitudes_m
        self.radial_midpoints_m = 0.5 * (self.radii_m[:-1] + self.radii_m[1:])
        self.radial_midpoint_altitudes_m = (
            self.radial_midpoints_m - self.config.earth_radius_m
        )
        self.radial_steps_m = np.diff(self.radii_m)

        self.maximum_stable_time_step_s = self._estimate_stable_time_step()
        self.time_step_s = (
            self.config.time_step_s
            if self.config.time_step_s is not None
            else self.maximum_stable_time_step_s
        )
        if self.time_step_s > self.maximum_stable_time_step_s * (1.0 + 1.0e-12):
            raise ValueError(
                f"time step {self.time_step_s:.6e} s exceeds conservative limit "
                f"{self.maximum_stable_time_step_s:.6e} s"
            )

        self.er = np.zeros((self.mesh.n_vertices, len(self.radii_m)))
        self.ht = np.zeros((self.mesh.n_edges, len(self.radii_m)))
        self.et = np.zeros((self.mesh.n_edges, len(self.radial_midpoints_m)))
        self.hr = np.zeros((self.mesh.n_faces, len(self.radial_midpoints_m)))

        self._prepare_geometry()
        self._prepare_material_coefficients()
        self.time_s = 0.0
        self.steps = 0

    def _estimate_stable_time_step(self) -> float:
        smallest_radius = float(self.radii_m.min())
        primal = smallest_radius * float(self.mesh.primal_edge_angles.min())
        dual = smallest_radius * float(self.mesh.dual_edge_angles.min())
        radial = float(self.radial_steps_m.min())
        inverse_length_squared = primal**-2 + dual**-2 + (2.0 / radial) ** 2
        return self.config.courant_factor / (C_0 * np.sqrt(inverse_length_squared))

    def _prepare_geometry(self) -> None:
        self._primal_lengths_tm = (
            self.mesh.primal_edge_angles[:, None] * self.radii_m[None, :]
        )
        self._dual_lengths_tm = (
            self.mesh.dual_edge_angles[:, None] * self.radii_m[None, :]
        )
        self._dual_areas_tm = (
            self.mesh.dual_cell_solid_angles[:, None] * self.radii_m[None, :] ** 2
        )
        self._primal_lengths_te = (
            self.mesh.primal_edge_angles[:, None] * self.radial_midpoints_m[None, :]
        )
        self._dual_lengths_te = (
            self.mesh.dual_edge_angles[:, None] * self.radial_midpoints_m[None, :]
        )
        self._face_areas_te = (
            self.mesh.face_solid_angles[:, None]
            * self.radial_midpoints_m[None, :] ** 2
        )

    def _prepare_material_coefficients(self) -> None:
        sigma_er, epsilon_r_er = self.material.sample(
            self.mesh.vertices, self.altitudes_m, self.config.earth_radius_m
        )
        sigma_et, epsilon_r_et = self.material.sample(
            self.mesh.edge_midpoints(),
            self.radial_midpoint_altitudes_m,
            self.config.earth_radius_m,
        )
        epsilon_er = EPSILON_0 * epsilon_r_er
        epsilon_et = EPSILON_0 * epsilon_r_et
        loss_er = sigma_er * self.time_step_s / (2.0 * epsilon_er)
        loss_et = sigma_et * self.time_step_s / (2.0 * epsilon_et)
        self._ca_er = (1.0 - loss_er) / (1.0 + loss_er)
        self._cb_er = self.time_step_s / (epsilon_er * (1.0 + loss_er))
        self._ca_et = (1.0 - loss_et) / (1.0 + loss_et)
        self._cb_et = self.time_step_s / (epsilon_et * (1.0 + loss_et))
        self.sigma_er = sigma_er
        self.sigma_et = sigma_et
        self.epsilon_r_er = epsilon_r_er
        self.epsilon_r_et = epsilon_r_et

    def step(self, count: int = 1) -> None:
        """Advance the fields by ``count`` complete leapfrog time steps."""

        if count < 0:
            raise ValueError("step count must be non-negative")
        for _ in range(count):
            self._update_magnetic_fields()
            self._update_electric_fields()
            self.steps += 1
            self.time_s = self.steps * self.time_step_s

    def _update_magnetic_fields(self) -> None:
        surface_gradient_er = (
            self.mesh.edge_difference(self.er) / self._primal_lengths_tm
        )

        radial_derivative_et = np.empty_like(self.ht)
        radial_derivative_et[:, 0] = 2.0 * self.et[:, 0] / self.radial_steps_m[0]
        radial_derivative_et[:, -1] = -2.0 * self.et[:, -1] / self.radial_steps_m[-1]
        if self.ht.shape[1] > 2:
            center_distance = (
                self.radial_midpoints_m[1:] - self.radial_midpoints_m[:-1]
            )
            radial_derivative_et[:, 1:-1] = np.diff(self.et, axis=1) / center_distance

        self.ht += (self.time_step_s / MU_0) * (
            surface_gradient_er - radial_derivative_et
        )

        electric_circulation = self.mesh.face_circulation(
            self.et * self._primal_lengths_te
        )
        self.hr -= (self.time_step_s / MU_0) * (
            electric_circulation / self._face_areas_te
        )

    def _update_electric_fields(self) -> None:
        magnetic_circulation = self.mesh.dual_cell_circulation(
            self.ht * self._dual_lengths_tm
        )
        curl_h_radial = magnetic_circulation / self._dual_areas_tm

        current_density = None
        if self.source is not None:
            vertex, layer = self.source.location(self)
            current_density = (
                vertex,
                layer,
                self.source.current_a(
                    self.time_s + 0.5 * self.time_step_s, self.time_step_s
                )
                / self._dual_areas_tm[vertex, layer],
            )

        self.er *= self._ca_er
        self.er += self._cb_er * curl_h_radial
        if current_density is not None:
            vertex, layer, value = current_density
            self.er[vertex, layer] -= self._cb_er[vertex, layer] * value

        surface_gradient_hr = (
            self.mesh.dual_edge_difference(self.hr) / self._dual_lengths_te
        )
        radial_derivative_ht = np.diff(self.ht, axis=1) / self.radial_steps_m[None, :]
        curl_h_tangential = surface_gradient_hr - radial_derivative_ht
        self.et *= self._ca_et
        self.et += self._cb_et * curl_h_tangential

    def diagnostics(self) -> dict[str, float | int]:
        """Return inexpensive scalar diagnostics without saving field data."""

        return {
            "step": self.steps,
            "time_s": self.time_s,
            "max_abs_er_v_m": float(np.max(np.abs(self.er))),
            "max_abs_et_v_m": float(np.max(np.abs(self.et))),
            "max_abs_hr_a_m": float(np.max(np.abs(self.hr))),
            "max_abs_ht_a_m": float(np.max(np.abs(self.ht))),
        }

    @property
    def memory_bytes(self) -> int:
        return int(self.er.nbytes + self.et.nbytes + self.hr.nbytes + self.ht.nbytes)
