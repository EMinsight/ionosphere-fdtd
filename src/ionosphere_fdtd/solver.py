"""Vectorized 3-D geodesic FDTD time stepping."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .backends import ArrayBackend, create_backend
from .constants import C_0, EARTH_RADIUS_M, EPSILON_0, MU_0
from .materials import EarthIonosphereMaterial
from .mesh import GeodesicMesh, build_geodesic_mesh
from .sources import GaussianCurrent, TangentialGaussianCurrent


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
    mesh_orientation: str = "polar"
    radial_altitudes_m: tuple[float, ...] | None = None
    tangential_material_support: str = "point"

    def __post_init__(self) -> None:
        if self.subdivision < 0:
            raise ValueError("subdivision must be non-negative")
        if self.radial_cells < 2:
            raise ValueError("radial_cells must be at least 2")
        if self.mesh_orientation not in {"native", "polar"}:
            raise ValueError("mesh_orientation must be 'native' or 'polar'")
        if self.tangential_material_support not in {"point", "edge-diamond"}:
            raise ValueError(
                "tangential_material_support must be 'point' or 'edge-diamond'"
            )
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
        source: GaussianCurrent | TangentialGaussianCurrent | None = None,
        mesh: GeodesicMesh | None = None,
        backend: str = "numpy",
        device: str = "auto",
        dtype: str = "auto",
        compile_step: bool = False,
        torch_threads: int | None = None,
    ) -> None:
        self.config = config or SimulationConfig()
        self.mesh = mesh or build_geodesic_mesh(
            self.config.subdivision,
            self.config.mesh_relaxations,
            self.config.mesh_orientation,
        )
        if self.mesh.subdivision != self.config.subdivision:
            raise ValueError("provided mesh subdivision does not match config")
        self.backend: ArrayBackend = create_backend(
            backend,
            self.mesh,
            device=device,
            dtype=dtype,
            torch_threads=torch_threads,
        )
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

        self.er = self.backend.zeros((self.mesh.n_vertices, len(self.radii_m)))
        self.ht = self.backend.zeros((self.mesh.n_edges, len(self.radii_m)))
        self.et = self.backend.zeros(
            (self.mesh.n_edges, len(self.radial_midpoints_m))
        )
        self.hr = self.backend.zeros(
            (self.mesh.n_faces, len(self.radial_midpoints_m))
        )

        self._prepare_geometry()
        self._prepare_material_coefficients()
        self._source_distribution = None
        self._tangential_source_distribution = None
        if isinstance(self.source, TangentialGaussianCurrent):
            edges, layers, weights = self.source.edge_distribution(self)
            self._tangential_source_distribution = (
                self.backend.index_array(edges),
                self.backend.index_array(layers),
                self.backend.asarray(weights),
            )
        elif self.source is not None:
            vertices, layers, weights = self.source.staggered_distribution(self)
            self._source_distribution = (
                self.backend.index_array(vertices),
                self.backend.index_array(layers),
                self.backend.asarray(weights),
            )
        self.time_s = 0.0
        self.steps = 0
        self.compiled = compile_step
        self._field_step = (
            self.backend.compile_step(self._advance_fields)
            if compile_step
            else self._advance_fields
        )

    def _estimate_stable_time_step(self) -> float:
        smallest_radius = float(self.radii_m.min())
        primal = smallest_radius * float(self.mesh.primal_edge_angles.min())
        dual = smallest_radius * float(self.mesh.dual_edge_angles.min())
        radial = float(self.radial_steps_m.min())
        inverse_length_squared = primal**-2 + dual**-2 + (2.0 / radial) ** 2
        return self.config.courant_factor / (C_0 * np.sqrt(inverse_length_squared))

    def _prepare_geometry(self) -> None:
        primal_lengths_tm = (
            self.mesh.primal_edge_angles[:, None] * self.radii_m[None, :]
        )
        dual_lengths_tm = (
            self.mesh.dual_edge_angles[:, None] * self.radii_m[None, :]
        )
        dual_areas_tm = (
            self.mesh.dual_cell_solid_angles[:, None] * self.radii_m[None, :] ** 2
        )
        primal_lengths_te = (
            self.mesh.primal_edge_angles[:, None] * self.radial_midpoints_m[None, :]
        )
        dual_lengths_te = (
            self.mesh.dual_edge_angles[:, None] * self.radial_midpoints_m[None, :]
        )
        face_areas_te = (
            self.mesh.face_solid_angles[:, None]
            * self.radial_midpoints_m[None, :] ** 2
        )
        self._primal_lengths_tm = self.backend.asarray(primal_lengths_tm)
        self._dual_lengths_tm = self.backend.asarray(dual_lengths_tm)
        self._dual_areas_tm = self.backend.asarray(dual_areas_tm)
        self._primal_lengths_te = self.backend.asarray(primal_lengths_te)
        self._dual_lengths_te = self.backend.asarray(dual_lengths_te)
        self._face_areas_te = self.backend.asarray(face_areas_te)
        self._radial_steps = self.backend.asarray(self.radial_steps_m)
        self._dual_face_areas_te = (
            self._dual_lengths_te * self._radial_steps[None, :]
        )
        self._radial_center_distances = self.backend.asarray(
            self.radial_midpoints_m[1:] - self.radial_midpoints_m[:-1]
        )

    def _prepare_material_coefficients(self) -> None:
        sigma_er, epsilon_r_er = self.material.sample(
            self.mesh.vertices, self.altitudes_m, self.config.earth_radius_m
        )
        def sample_tangential(
            directions: NDArray[np.float64],
        ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
            sample_cells = getattr(self.material, "sample_tangential_cells", None)
            if sample_cells is None:
                return self.material.sample(
                    directions,
                    self.radial_midpoint_altitudes_m,
                    self.config.earth_radius_m,
                )
            return sample_cells(
                directions,
                self.altitudes_m[:-1],
                self.altitudes_m[1:],
                self.config.earth_radius_m,
            )

        edge_midpoints = self.mesh.edge_midpoints()
        if self.config.tangential_material_support == "point":
            sigma_et, epsilon_r_et = sample_tangential(edge_midpoints)
        else:
            endpoints = self.mesh.vertices[self.mesh.edges]
            left = self.mesh.face_centers[self.mesh.edge_left_faces]
            right = self.mesh.face_centers[self.mesh.edge_right_faces]
            support_directions = (
                edge_midpoints + endpoints[:, 0] + left,
                edge_midpoints + left + endpoints[:, 1],
                edge_midpoints + endpoints[:, 1] + right,
                edge_midpoints + right + endpoints[:, 0],
            )
            sigma_et = np.zeros(
                (self.mesh.n_edges, len(self.radial_midpoints_m)),
                dtype=np.float64,
            )
            epsilon_r_et = np.zeros_like(sigma_et)
            for directions in support_directions:
                directions /= np.linalg.norm(directions, axis=1, keepdims=True)
                support_sigma, support_epsilon = sample_tangential(directions)
                sigma_et += 0.25 * support_sigma
                epsilon_r_et += 0.25 * support_epsilon
        epsilon_er = EPSILON_0 * epsilon_r_er
        epsilon_et = EPSILON_0 * epsilon_r_et
        loss_er = sigma_er * self.time_step_s / (2.0 * epsilon_er)
        loss_et = sigma_et * self.time_step_s / (2.0 * epsilon_et)
        self._ca_er = self.backend.asarray((1.0 - loss_er) / (1.0 + loss_er))
        self._cb_er = self.backend.asarray(
            self.time_step_s / (epsilon_er * (1.0 + loss_er))
        )
        self._ca_et = self.backend.asarray((1.0 - loss_et) / (1.0 + loss_et))
        self._cb_et = self.backend.asarray(
            self.time_step_s / (epsilon_et * (1.0 + loss_et))
        )
        self.sigma_er = self.backend.asarray(sigma_er)
        self.sigma_et = self.backend.asarray(sigma_et)
        self.epsilon_r_er = self.backend.asarray(epsilon_r_er)
        self.epsilon_r_et = self.backend.asarray(epsilon_r_et)

    def step(self, count: int = 1) -> None:
        """Advance the fields by ``count`` complete leapfrog time steps."""

        if count < 0:
            raise ValueError("step count must be non-negative")
        if self.compiled and count:
            currents = self._source_currents(count)
            for offset in range(count):
                self._field_step(currents[offset])
            self.steps += count
            self.time_s = self.steps * self.time_step_s
            return
        for _ in range(count):
            current_a = (
                self.source.current_a(
                    self.time_s + 0.5 * self.time_step_s,
                    self.time_step_s,
                )
                if self.source is not None
                else 0.0
            )
            self._field_step(current_a)
            self.steps += 1
            self.time_s = self.steps * self.time_step_s

    def _source_currents(self, count: int) -> Any:
        if self.source is None:
            return self.backend.zeros((count,))
        values = np.fromiter(
            (
                self.source.current_a(
                    (self.steps + offset + 0.5) * self.time_step_s,
                    self.time_step_s,
                )
                for offset in range(count)
            ),
            dtype=np.float64,
            count=count,
        )
        return self.backend.asarray(values)

    def _advance_fields(self, current_a: Any) -> None:
        self._update_magnetic_fields()
        self._update_electric_fields(current_a)

    def _update_magnetic_fields(self) -> None:
        surface_gradient_er = self.backend.edge_difference(
            self.er
        ) / self._primal_lengths_tm

        radial_derivative_et = self.backend.empty_like(self.ht)
        radial_derivative_et[:, 0] = 2.0 * self.et[:, 0] / self._radial_steps[0]
        radial_derivative_et[:, -1] = -2.0 * self.et[:, -1] / self._radial_steps[-1]
        if self.ht.shape[1] > 2:
            radial_derivative_et[:, 1:-1] = self.backend.diff(
                self.et, axis=1
            ) / self._radial_center_distances

        surface_gradient_er -= radial_derivative_et
        surface_gradient_er *= self.time_step_s / MU_0
        self.ht += surface_gradient_er
        del surface_gradient_er, radial_derivative_et

        electric_circulation = self.backend.face_circulation(
            self.et * self._primal_lengths_te
        )
        electric_circulation /= self._face_areas_te
        electric_circulation *= self.time_step_s / MU_0
        self.hr -= electric_circulation

    def _update_electric_fields(self, current_a: Any = 0.0) -> None:
        magnetic_circulation = self.backend.dual_cell_circulation(
            self.ht * self._dual_lengths_tm
        )
        magnetic_circulation /= self._dual_areas_tm

        current_density = None
        if self.source is not None and self._source_distribution is not None:
            vertices, layers, weights = self._source_distribution
            current_density = (
                weights * current_a / self._dual_areas_tm[vertices, layers]
            )

        self.er *= self._ca_er
        magnetic_circulation *= self._cb_er
        self.er += magnetic_circulation
        if current_density is not None:
            vertices, layers, _ = self._source_distribution
            self.er[vertices, layers] -= (
                self._cb_er[vertices, layers] * current_density
            )

        surface_gradient_hr = self.backend.dual_edge_difference(
            self.hr
        ) / self._dual_lengths_te
        radial_derivative_ht = self.backend.diff(
            self.ht, axis=1
        ) / self._radial_steps[None, :]
        surface_gradient_hr -= radial_derivative_ht
        del radial_derivative_ht
        self.et *= self._ca_et
        surface_gradient_hr *= self._cb_et
        self.et += surface_gradient_hr
        if self._tangential_source_distribution is not None:
            edges, layers, weights = self._tangential_source_distribution
            current_density = (
                weights * current_a / self._dual_face_areas_te[edges, layers]
            )
            self.et[edges, layers] -= self._cb_et[edges, layers] * current_density

    def diagnostics(self) -> dict[str, float | int | str]:
        """Return inexpensive scalar diagnostics without saving field data."""

        return {
            "step": self.steps,
            "time_s": self.time_s,
            "backend": self.backend.name,
            "device": self.backend.device,
            "dtype": self.backend.dtype_name,
            "compiled": self.compiled,
            "max_abs_er_v_m": self.backend.max_abs(self.er),
            "max_abs_et_v_m": self.backend.max_abs(self.et),
            "max_abs_hr_a_m": self.backend.max_abs(self.hr),
            "max_abs_ht_a_m": self.backend.max_abs(self.ht),
        }

    def to_numpy(self, values: Any) -> NDArray[np.generic]:
        """Expose values as a host NumPy array for analysis or plotting."""

        return self.backend.to_numpy(values)

    def field_value(self, field: str, *indices: int) -> float:
        """Read one field value without exposing backend scalar semantics."""

        try:
            values = getattr(self, field)
        except AttributeError as error:
            raise ValueError("field must be er, et, hr, or ht") from error
        if field not in {"er", "et", "hr", "ht"}:
            raise ValueError("field must be er, et, hr, or ht")
        return self.backend.scalar(values[indices])

    def record_er_observations(
        self,
        vertex_indices: NDArray[np.int64],
        radial_layers: NDArray[np.int64],
        weights: NDArray[np.float64],
        steps: int,
        *,
        synchronize_every: int = 128,
    ) -> NDArray[np.generic]:
        """Advance and record weighted ``Er`` observations without host syncs.

        Each row of ``vertex_indices`` and ``weights`` describes one receiver.
        The returned first row is the initial field, followed by one row per
        completed time step.  Keeping the trace buffer on the backend is much
        faster than reading individual MPS or CUDA scalars every step.
        """

        vertices = np.asarray(vertex_indices, dtype=np.int64)
        layers = np.asarray(radial_layers, dtype=np.int64)
        sample_weights = np.asarray(weights, dtype=np.float64)
        if steps < 0:
            raise ValueError("step count must be non-negative")
        if synchronize_every < 1:
            raise ValueError("synchronize_every must be positive")
        if vertices.ndim != 2 or sample_weights.shape != vertices.shape:
            raise ValueError("vertex_indices and weights must have matching 2-D shapes")
        if layers.shape != (vertices.shape[0],):
            raise ValueError("radial_layers must contain one layer per observation")
        if np.any(vertices < 0) or np.any(vertices >= self.mesh.n_vertices):
            raise ValueError("observation vertex index is out of range")
        if np.any(layers < 0) or np.any(layers >= len(self.radii_m)):
            raise ValueError("observation radial layer is out of range")
        if not np.allclose(sample_weights.sum(axis=1), 1.0):
            raise ValueError("observation weights must sum to one")

        backend_vertices = self.backend.index_array(vertices)
        backend_layers = self.backend.index_array(layers)
        backend_weights = self.backend.asarray(sample_weights)
        traces = self.backend.zeros((steps + 1, vertices.shape[0]))

        def sample(row: int) -> None:
            selected = self.er[backend_vertices, backend_layers[:, None]]
            traces[row] = (selected * backend_weights).sum(axis=1)

        sample(0)
        currents = self._source_currents(steps)
        for offset in range(steps):
            self._field_step(currents[offset])
            self.steps += 1
            self.time_s = self.steps * self.time_step_s
            sample(offset + 1)
            if (offset + 1) % synchronize_every == 0:
                self.backend.synchronize()
        self.backend.synchronize()
        return self.to_numpy(traces)

    def record_h_observations(
        self,
        face_indices: NDArray[np.int64],
        face_radial_layers: NDArray[np.int64],
        face_weights: NDArray[np.float64],
        edge_indices: NDArray[np.int64],
        edge_radial_layers: NDArray[np.int64],
        edge_weights: NDArray[np.float64],
        steps: int,
        *,
        synchronize_every: int = 128,
    ) -> tuple[NDArray[np.generic], NDArray[np.generic]]:
        """Advance while recording weighted radial and tangential H samples."""

        faces = np.asarray(face_indices, dtype=np.int64)
        face_layers = np.asarray(face_radial_layers, dtype=np.int64)
        radial_weights = np.asarray(face_weights, dtype=np.float64)
        edges = np.asarray(edge_indices, dtype=np.int64)
        edge_layers = np.asarray(edge_radial_layers, dtype=np.int64)
        tangential_weights = np.asarray(edge_weights, dtype=np.float64)
        if steps < 0:
            raise ValueError("step count must be non-negative")
        if synchronize_every < 1:
            raise ValueError("synchronize_every must be positive")
        if faces.ndim != 2 or radial_weights.shape != faces.shape:
            raise ValueError("face indices and weights must have matching 2-D shapes")
        if edges.ndim != 2 or tangential_weights.shape != edges.shape:
            raise ValueError("edge indices and weights must have matching 2-D shapes")
        if face_layers.shape != faces.shape:
            raise ValueError("face radial layers must match the face indices")
        if edge_layers.shape != edges.shape:
            raise ValueError("edge radial layers must match the edge indices")
        if np.any(faces < 0) or np.any(faces >= self.mesh.n_faces):
            raise ValueError("observation face index is out of range")
        if np.any(edges < 0) or np.any(edges >= self.mesh.n_edges):
            raise ValueError("observation edge index is out of range")
        if np.any(face_layers < 0) or np.any(face_layers >= self.hr.shape[1]):
            raise ValueError("radial H observation layer is out of range")
        if np.any(edge_layers < 0) or np.any(edge_layers >= self.ht.shape[1]):
            raise ValueError("tangential H observation layer is out of range")

        backend_faces = self.backend.index_array(faces)
        backend_face_layers = self.backend.index_array(face_layers)
        backend_radial_weights = self.backend.asarray(radial_weights)
        backend_edges = self.backend.index_array(edges)
        backend_edge_layers = self.backend.index_array(edge_layers)
        backend_tangential_weights = self.backend.asarray(tangential_weights)
        radial_traces = self.backend.zeros((steps + 1, faces.shape[0]))
        tangential_traces = self.backend.zeros((steps + 1, edges.shape[0]))

        def sample(row: int) -> None:
            selected_hr = self.hr[backend_faces, backend_face_layers]
            radial_traces[row] = (
                selected_hr * backend_radial_weights
            ).sum(axis=1)
            selected_ht = self.ht[backend_edges, backend_edge_layers]
            tangential_traces[row] = (
                selected_ht * backend_tangential_weights
            ).sum(axis=1)

        sample(0)
        currents = self._source_currents(steps)
        for offset in range(steps):
            self._field_step(currents[offset])
            self.steps += 1
            self.time_s = self.steps * self.time_step_s
            sample(offset + 1)
            if (offset + 1) % synchronize_every == 0:
                self.backend.synchronize()
        self.backend.synchronize()
        return self.to_numpy(radial_traces), self.to_numpy(tangential_traces)

    @property
    def memory_bytes(self) -> int:
        return sum(
            self.backend.nbytes(field)
            for field in (self.er, self.et, self.hr, self.ht)
        )
