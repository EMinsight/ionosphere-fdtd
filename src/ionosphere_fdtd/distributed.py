"""Two-rank sharded PyTorch FDTD execution with P2P field halos."""

from __future__ import annotations

from dataclasses import dataclass
import os
from types import SimpleNamespace
from typing import Any

import numpy as np

from .constants import MU_0
from .materials import EarthIonosphereMaterial
from .mesh import GeodesicMesh
from .partition import FieldHalo, SurfacePartition
from .solver import GeodesicFDTD, SimulationConfig
from .sources import GaussianCurrent, TangentialGaussianCurrent


@dataclass(frozen=True, slots=True)
class _EntityLayout:
    global_indices: np.ndarray
    global_to_local: np.ndarray
    owned_count: int


class TorchDistributedHaloExchange:
    """Exchange packed electric or magnetic ghost rows with one peer."""

    def __init__(
        self,
        *,
        torch: Any,
        distributed: Any,
        device: Any,
        peer_rank: int,
        send_halo: FieldHalo,
        receive_halo: FieldHalo,
        vertex_layout: _EntityLayout,
        et_layout: _EntityLayout,
        face_layout: _EntityLayout,
        ht_layout: _EntityLayout,
    ) -> None:
        self.torch = torch
        self.distributed = distributed
        self.device = device
        self.peer_rank = peer_rank
        self._electric = self._phase_plan(
            (
                (send_halo.er_vertices, receive_halo.er_vertices, vertex_layout),
                (send_halo.et_edges, receive_halo.et_edges, et_layout),
            )
        )
        self._magnetic = self._phase_plan(
            (
                (send_halo.hr_faces, receive_halo.hr_faces, face_layout),
                (send_halo.ht_edges, receive_halo.ht_edges, ht_layout),
            )
        )

    def _phase_plan(
        self,
        values: tuple[tuple[np.ndarray, np.ndarray, _EntityLayout], ...],
    ) -> tuple[tuple[Any, Any], ...]:
        result = []
        for send_global, receive_global, layout in values:
            send_local = layout.global_to_local[send_global]
            receive_local = layout.global_to_local[receive_global]
            if np.any(send_local < 0) or np.any(receive_local < 0):
                raise ValueError("halo entity is absent from the local field layout")
            result.append(
                (
                    self.torch.as_tensor(
                        send_local, dtype=self.torch.long, device=self.device
                    ),
                    self.torch.as_tensor(
                        receive_local, dtype=self.torch.long, device=self.device
                    ),
                )
            )
        return tuple(result)

    def exchange_electric(self, er: Any, et: Any) -> None:
        self._exchange((er, et), self._electric, tag=100)

    def exchange_magnetic(self, hr: Any, ht: Any) -> None:
        self._exchange((hr, ht), self._magnetic, tag=200)

    def _exchange(
        self,
        fields: tuple[Any, Any],
        plan: tuple[tuple[Any, Any], ...],
        *,
        tag: int,
    ) -> None:
        send_parts = [
            field.index_select(0, indices).contiguous().view(-1)
            for field, (indices, _) in zip(fields, plan, strict=True)
        ]
        send_buffer = self.torch.cat(send_parts)
        receive_sizes = [
            int(indices.numel() * field.shape[1])
            for field, (_, indices) in zip(fields, plan, strict=True)
        ]
        receive_buffer = self.torch.empty(
            sum(receive_sizes), dtype=fields[0].dtype, device=self.device
        )
        operations = [
            self.distributed.P2POp(
                self.distributed.irecv,
                receive_buffer,
                self.peer_rank,
                tag=tag,
            ),
            self.distributed.P2POp(
                self.distributed.isend,
                send_buffer,
                self.peer_rank,
                tag=tag,
            ),
        ]
        for request in self.distributed.batch_isend_irecv(operations):
            request.wait()
        offset = 0
        for field, (_, receive_indices), size in zip(
            fields, plan, receive_sizes, strict=True
        ):
            rows = int(receive_indices.numel())
            if rows:
                values = receive_buffer[offset : offset + size].view(
                    rows, field.shape[1]
                )
                field.index_copy_(0, receive_indices, values)
            offset += size


class DistributedGeodesicFDTD:
    """Shard one geodesic FDTD model across exactly two torch ranks."""

    def __init__(
        self,
        partition: SurfacePartition,
        *,
        config: SimulationConfig,
        mesh: GeodesicMesh,
        material: EarthIonosphereMaterial | None = None,
        source: GaussianCurrent | TangentialGaussianCurrent | None = None,
        device: str | None = None,
        dtype: str = "float64",
    ) -> None:
        try:
            import torch
            import torch.distributed as distributed
        except ImportError as error:
            raise RuntimeError("distributed execution requires PyTorch") from error
        if not distributed.is_available() or not distributed.is_initialized():
            raise RuntimeError("initialize torch.distributed before the solver")
        if distributed.get_world_size() != partition.n_parts:
            raise ValueError("process-group size must match the surface partition")
        if partition.n_parts != 2:
            raise ValueError("distributed FDTD currently requires exactly two ranks")
        if dtype not in {"float32", "float64"}:
            raise ValueError("distributed dtype must be 'float32' or 'float64'")

        self.torch = torch
        self.distributed = distributed
        self.rank = distributed.get_rank()
        self.partition = partition
        self.rank_partition = partition.ranks[self.rank]
        self.config = config
        self.mesh = mesh
        self.material = material or EarthIonosphereMaterial()
        self.source = source
        self.dtype_name = dtype
        self.dtype = torch.float32 if dtype == "float32" else torch.float64
        backend_name = distributed.get_backend()
        if device is None:
            if backend_name == "nccl":
                local_rank = int(os.environ.get("LOCAL_RANK", self.rank))
                torch.cuda.set_device(local_rank)
                self.device = torch.device("cuda", local_rank)
            else:
                self.device = torch.device("cpu")
        else:
            self.device = torch.device(device)
            if self.device.type == "cuda" and self.device.index is None:
                self.device = torch.device("cuda", torch.cuda.current_device())
        if backend_name == "nccl" and self.device.type != "cuda":
            raise ValueError("the NCCL process group requires one CUDA device per rank")

        template = GeodesicFDTD(
            config,
            material=self.material,
            source=self.source,
            mesh=mesh,
            backend="numpy",
            dtype="float64",
        )
        self.time_step_s = template.time_step_s
        self.cfl_time_step_limit_s = template.cfl_time_step_limit_s
        self.maximum_stable_time_step_s = template.maximum_stable_time_step_s
        self.altitudes_m = template.altitudes_m
        self.radii_m = template.radii_m
        self.radial_midpoints_m = template.radial_midpoints_m
        self.radial_midpoint_altitudes_m = template.radial_midpoint_altitudes_m
        self.radial_steps_m = template.radial_steps_m
        self.radial_node_control_lengths_m = template.radial_node_control_lengths_m
        self.steps = 0
        self.time_s = 0.0
        self.compiled = False
        self.backend = SimpleNamespace(
            name="torch-distributed",
            device=str(self.device),
            dtype_name=dtype,
        )

        receive = self.rank_partition.receive_halos[0]
        self._vertex_layout = _layout(
            mesh.n_vertices,
            self.rank_partition.owned_vertices,
            receive.er_vertices,
        )
        self._et_layout = _layout(
            mesh.n_edges,
            self.rank_partition.owned_edges,
            receive.et_edges,
        )
        self._face_layout = _layout(
            mesh.n_faces,
            self.rank_partition.owned_faces,
            receive.hr_faces,
        )
        self._ht_layout = _layout(
            mesh.n_edges,
            self.rank_partition.owned_edges,
            receive.ht_edges,
        )
        radial_nodes = len(self.radii_m)
        radial_cells = len(self.radial_midpoints_m)
        self.er = self._zeros((len(self._vertex_layout.global_indices), radial_nodes))
        self.et = self._zeros((len(self._et_layout.global_indices), radial_cells))
        self.hr = self._zeros((len(self._face_layout.global_indices), radial_cells))
        self.ht = self._zeros((len(self._ht_layout.global_indices), radial_nodes))

        self._prepare_local_geometry(template)
        self._prepare_local_coefficients(template)
        self._prepare_local_sources(template)
        send = self.rank_partition.send_halos[0]
        self.halo_exchange = TorchDistributedHaloExchange(
            torch=torch,
            distributed=distributed,
            device=self.device,
            peer_rank=1 - self.rank,
            send_halo=send,
            receive_halo=receive,
            vertex_layout=self._vertex_layout,
            et_layout=self._et_layout,
            face_layout=self._face_layout,
            ht_layout=self._ht_layout,
        )

    def _zeros(self, shape: tuple[int, int]) -> Any:
        return self.torch.zeros(shape, dtype=self.dtype, device=self.device)

    def _tensor(self, values: Any) -> Any:
        return self.torch.as_tensor(values, dtype=self.dtype, device=self.device)

    def _indices(self, values: Any) -> Any:
        return self.torch.as_tensor(
            values, dtype=self.torch.long, device=self.device
        )

    def _prepare_local_geometry(self, template: GeodesicFDTD) -> None:
        owned_edges = self.rank_partition.owned_edges
        owned_faces = self.rank_partition.owned_faces
        owned_vertices = self.rank_partition.owned_vertices
        edge_endpoints = self._vertex_layout.global_to_local[
            self.mesh.edges[owned_edges]
        ]
        face_edges = self._et_layout.global_to_local[
            self.mesh.face_edges[owned_faces]
        ]
        left_faces = self._face_layout.global_to_local[
            self.mesh.edge_left_faces[owned_edges]
        ]
        right_faces = self._face_layout.global_to_local[
            self.mesh.edge_right_faces[owned_edges]
        ]
        if any(
            np.any(values < 0)
            for values in (edge_endpoints, face_edges, left_faces, right_faces)
        ):
            raise RuntimeError("partition halo does not cover a local curl stencil")
        self._edge_endpoints = self._indices(edge_endpoints)
        self._face_edges = self._indices(face_edges)
        self._face_edge_signs = self._tensor(
            self.mesh.face_edge_signs[owned_faces]
        )
        self._face_primal_edge_angles = self._tensor(
            self.mesh.primal_edge_angles[self.mesh.face_edges[owned_faces]]
        )
        self._edge_left_faces = self._indices(left_faces)
        self._edge_right_faces = self._indices(right_faces)
        self._primal_edge_angles = self._tensor(
            self.mesh.primal_edge_angles[owned_edges, None]
        )
        self._inverse_primal_edge_angles = 1.0 / self._primal_edge_angles
        self._dual_edge_angles = self._tensor(
            self.mesh.dual_edge_angles[owned_edges, None]
        )
        self._inverse_dual_edge_angles = 1.0 / self._dual_edge_angles
        self._inverse_face_solid_angles = self._tensor(
            1.0 / self.mesh.face_solid_angles[owned_faces, None]
        )
        self._inverse_dual_cell_solid_angles = self._tensor(
            1.0 / self.mesh.dual_cell_solid_angles[owned_vertices, None]
        )
        self._radii = self._tensor(template.radii_m)
        self._inverse_radii = self._tensor(1.0 / template.radii_m[None, :])
        self._radial_midpoints = self._tensor(template.radial_midpoints_m)
        self._inverse_radial_midpoints = self._tensor(
            1.0 / template.radial_midpoints_m[None, :]
        )
        self._radial_steps = self._tensor(template.radial_steps_m)
        self._radial_center_distances = self._tensor(
            template.radial_midpoints_m[1:] - template.radial_midpoints_m[:-1]
        )
        self._radial_node_control_lengths = self._tensor(
            template.radial_node_control_lengths_m
        )

        incident = [[] for _ in owned_vertices]
        vertex_slot = {int(vertex): slot for slot, vertex in enumerate(owned_vertices)}
        for global_edge, (tail, head) in enumerate(self.mesh.edges):
            for vertex, sign in ((int(tail), 1.0), (int(head), -1.0)):
                slot = vertex_slot.get(vertex)
                if slot is not None:
                    local_edge = self._ht_layout.global_to_local[global_edge]
                    if local_edge < 0:
                        raise RuntimeError("Ht halo does not cover vertex circulation")
                    incident[slot].append((int(local_edge), global_edge, sign))
        maximum_degree = max(len(values) for values in incident)
        incidence_edges = np.zeros((len(incident), maximum_degree), dtype=np.int64)
        incidence_global_edges = np.zeros_like(incidence_edges)
        incidence_signs = np.zeros((len(incident), maximum_degree))
        for vertex, values in enumerate(incident):
            for slot, (local_edge, global_edge, sign) in enumerate(values):
                incidence_edges[vertex, slot] = local_edge
                incidence_global_edges[vertex, slot] = global_edge
                incidence_signs[vertex, slot] = sign
        self._vertex_edges = self._indices(incidence_edges)
        self._vertex_edge_metric = self._tensor(
            incidence_signs
            * self.mesh.dual_edge_angles[incidence_global_edges]
        )

    def _prepare_local_coefficients(self, template: GeodesicFDTD) -> None:
        owned_vertices = self.rank_partition.owned_vertices
        owned_edges = self.rank_partition.owned_edges

        def rows(values: Any, indices: np.ndarray) -> Any:
            host = np.asarray(values)
            selected = host if host.shape[0] == 1 else host[indices]
            return self._tensor(selected)

        self._ca_er = rows(template._ca_er, owned_vertices)
        self._cb_er = rows(template._cb_er, owned_vertices)
        self._ca_et = rows(template._ca_et, owned_edges)
        self._cb_et = rows(template._cb_et, owned_edges)

    def _prepare_local_sources(self, template: GeodesicFDTD) -> None:
        self._source_distribution = None
        self._tangential_source_distribution = None
        if template._source_distribution is not None:
            vertices, layers, weights = (
                np.asarray(value) for value in template._source_distribution
            )
            selected = self.partition.vertex_owner[vertices] == self.rank
            self._source_distribution = (
                self._indices(self._vertex_layout.global_to_local[vertices[selected]]),
                self._indices(layers[selected]),
                self._tensor(weights[selected]),
                self._tensor(
                    self.mesh.dual_cell_solid_angles[vertices[selected]]
                ),
            )
        if template._tangential_source_distribution is not None:
            edges, layers, weights = (
                np.asarray(value) for value in template._tangential_source_distribution
            )
            selected = self.partition.edge_owner[edges] == self.rank
            self._tangential_source_distribution = (
                self._indices(self._et_layout.global_to_local[edges[selected]]),
                self._indices(layers[selected]),
                self._tensor(weights[selected]),
                self._tensor(self.mesh.dual_edge_angles[edges[selected]]),
            )

    def step(self, count: int = 1) -> None:
        if isinstance(count, bool) or not isinstance(count, (int, np.integer)):
            raise ValueError("step count must be an integer")
        if count < 0:
            raise ValueError("step count must be non-negative")
        for _ in range(int(count)):
            current = (
                0.0
                if self.source is None
                else self.source.current_a(
                    (self.steps + 0.5) * self.time_step_s, self.time_step_s
                )
            )
            self.halo_exchange.exchange_electric(self.er, self.et)
            self._update_magnetic_fields()
            self.halo_exchange.exchange_magnetic(self.hr, self.ht)
            self._update_electric_fields(current)
            self.steps += 1
            self.time_s = self.steps * self.time_step_s

    def _update_magnetic_fields(self) -> None:
        owned_edges = self._ht_layout.owned_count
        owned_faces = self._face_layout.owned_count
        surface_gradient_er = (
            self.er[self._edge_endpoints[:, 1]]
            - self.er[self._edge_endpoints[:, 0]]
        )
        surface_gradient_er *= self._inverse_primal_edge_angles
        surface_gradient_er *= self._inverse_radii
        values = self.et[:owned_edges]
        if self.config.geometry_mode == "full-spherical":
            values = values * self._radial_midpoints[None, :]
        radial_derivative = self.torch.empty_like(self.ht[:owned_edges])
        radial_derivative[:, 0] = 2.0 * values[:, 0] / self._radial_steps[0]
        radial_derivative[:, -1] = -2.0 * values[:, -1] / self._radial_steps[-1]
        if radial_derivative.shape[1] > 2:
            radial_derivative[:, 1:-1] = self.torch.diff(
                values, dim=1
            ) / self._radial_center_distances
        if self.config.geometry_mode == "full-spherical":
            radial_derivative *= self._inverse_radii
        self.ht[:owned_edges] += (
            surface_gradient_er - radial_derivative
        ) * (self.time_step_s / MU_0)

        edge_values = (
            self.et[self._face_edges] * self._face_primal_edge_angles[:, :, None]
        )
        circulation = self.torch.sum(
            edge_values * self._face_edge_signs[:, :, None], dim=1
        )
        circulation *= self._inverse_face_solid_angles
        circulation *= self._inverse_radial_midpoints
        self.hr[:owned_faces] -= circulation * (self.time_step_s / MU_0)

    def _update_electric_fields(self, current_a: float) -> None:
        owned_vertices = self._vertex_layout.owned_count
        owned_edges = self._et_layout.owned_count
        circulation = self.torch.sum(
            self.ht[self._vertex_edges] * self._vertex_edge_metric[:, :, None],
            dim=1,
        )
        circulation *= self._inverse_dual_cell_solid_angles
        circulation *= self._inverse_radii
        self.er[:owned_vertices] *= self._ca_er
        self.er[:owned_vertices] += circulation * self._cb_er
        if self._source_distribution is not None:
            vertices, layers, weights, areas = self._source_distribution
            density = (
                weights
                * current_a
                * self.source.vertical_element_length_m
                / areas
                / self._radii[layers] ** 2
                / self._radial_node_control_lengths[layers]
            )
            coefficient_rows = 0 if self._cb_er.shape[0] == 1 else vertices
            self.er[vertices, layers] -= (
                self._cb_er[coefficient_rows, layers] * density
            )

        gradient = (
            self.hr[self._edge_left_faces] - self.hr[self._edge_right_faces]
        )
        gradient *= self._inverse_dual_edge_angles
        gradient *= self._inverse_radial_midpoints
        values = self.ht[:owned_edges]
        if self.config.geometry_mode == "full-spherical":
            values = values * self._radii[None, :]
        radial_derivative = self.torch.diff(values, dim=1) / self._radial_steps[None, :]
        if self.config.geometry_mode == "full-spherical":
            radial_derivative *= self._inverse_radial_midpoints
        gradient -= radial_derivative
        self.et[:owned_edges] *= self._ca_et
        self.et[:owned_edges] += gradient * self._cb_et
        if self._tangential_source_distribution is not None:
            edges, layers, weights, dual_angles = self._tangential_source_distribution
            density = (
                weights
                * current_a
                / dual_angles
                / self._radial_midpoints[layers]
                / self._radial_steps[layers]
            )
            coefficient_rows = 0 if self._cb_et.shape[0] == 1 else edges
            self.et[edges, layers] -= self._cb_et[coefficient_rows, layers] * density

    def global_field(self, name: str) -> np.ndarray:
        """Collect one full field on every rank for diagnostics and tests."""

        layouts = {
            "er": (self.er, self._vertex_layout, self.mesh.n_vertices),
            "et": (self.et, self._et_layout, self.mesh.n_edges),
            "hr": (self.hr, self._face_layout, self.mesh.n_faces),
            "ht": (self.ht, self._ht_layout, self.mesh.n_edges),
        }
        if name not in layouts:
            raise ValueError("field must be er, et, hr, or ht")
        field, layout, global_count = layouts[name]
        result = self.torch.zeros(
            (global_count, field.shape[1]), dtype=self.dtype, device=self.device
        )
        global_owned = layout.global_indices[: layout.owned_count]
        result[self._indices(global_owned)] = field[: layout.owned_count]
        self.distributed.all_reduce(result)
        return result.detach().cpu().numpy()

    def record_h_observations(
        self,
        face_indices: np.ndarray,
        face_radial_layers: np.ndarray,
        face_weights: np.ndarray,
        edge_indices: np.ndarray,
        edge_radial_layers: np.ndarray,
        edge_weights: np.ndarray,
        steps: int,
        *,
        synchronize_every: int = 128,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Record distributed H observations with one final trace reduction."""

        del synchronize_every
        faces = np.asarray(face_indices, dtype=np.int64)
        face_layers = np.asarray(face_radial_layers, dtype=np.int64)
        radial_weights = np.asarray(face_weights, dtype=np.float64)
        edges = np.asarray(edge_indices, dtype=np.int64)
        edge_layers = np.asarray(edge_radial_layers, dtype=np.int64)
        tangential_weights = np.asarray(edge_weights, dtype=np.float64)
        if faces.ndim != 2 or face_layers.shape != faces.shape:
            raise ValueError("distributed face observations must have matching shapes")
        if edges.ndim != 2 or edge_layers.shape != edges.shape:
            raise ValueError("distributed edge observations must have matching shapes")
        if radial_weights.shape != faces.shape or tangential_weights.shape != edges.shape:
            raise ValueError("distributed observation weights must match their indices")
        if steps < 0:
            raise ValueError("observation step count must be non-negative")

        local_faces = self._face_layout.global_to_local[faces]
        local_edges = self._ht_layout.global_to_local[edges]
        face_owned = self.partition.face_owner[faces] == self.rank
        edge_owned = self.partition.edge_owner[edges] == self.rank
        safe_faces = np.where(face_owned, local_faces, 0)
        safe_edges = np.where(edge_owned, local_edges, 0)
        local_face_weights = np.where(face_owned, radial_weights, 0.0)
        local_edge_weights = np.where(edge_owned, tangential_weights, 0.0)
        backend_faces = self._indices(safe_faces)
        backend_face_layers = self._indices(face_layers)
        backend_face_weights = self._tensor(local_face_weights)
        backend_edges = self._indices(safe_edges)
        backend_edge_layers = self._indices(edge_layers)
        backend_edge_weights = self._tensor(local_edge_weights)
        radial_traces = self._zeros((steps + 1, faces.shape[0]))
        tangential_traces = self._zeros((steps + 1, edges.shape[0]))

        def sample(row: int) -> None:
            radial_traces[row] = self.torch.sum(
                self.hr[backend_faces, backend_face_layers]
                * backend_face_weights,
                dim=1,
            )
            tangential_traces[row] = self.torch.sum(
                self.ht[backend_edges, backend_edge_layers]
                * backend_edge_weights,
                dim=1,
            )

        sample(0)
        for row in range(1, steps + 1):
            self.step()
            sample(row)
        self.distributed.all_reduce(radial_traces)
        self.distributed.all_reduce(tangential_traces)
        return (
            radial_traces.detach().cpu().numpy(),
            tangential_traces.detach().cpu().numpy(),
        )

    @property
    def field_memory_bytes(self) -> int:
        return int(
            sum(field.numel() * field.element_size() for field in (self.er, self.et, self.hr, self.ht))
        )


def _layout(global_count: int, owned: np.ndarray, ghost: np.ndarray) -> _EntityLayout:
    indices = np.concatenate((owned, ghost)).astype(np.int64, copy=False)
    if len(np.unique(indices)) != len(indices):
        raise ValueError("owned and ghost entity sets overlap")
    lookup = np.full(global_count, -1, dtype=np.int64)
    lookup[indices] = np.arange(len(indices), dtype=np.int64)
    return _EntityLayout(indices, lookup, len(owned))


def initialize_torchrun_process_group(backend: str = "nccl") -> Any:
    """Initialize a two-rank ``torchrun`` group and return the local device."""

    try:
        import torch
        import torch.distributed as distributed
    except ImportError as error:
        raise RuntimeError("torchrun initialization requires PyTorch") from error
    if backend not in {"nccl", "gloo"}:
        raise ValueError("distributed backend must be 'nccl' or 'gloo'")
    local_rank = int(os.environ.get("LOCAL_RANK", "0"))
    if backend == "nccl":
        if not torch.cuda.is_available():
            raise RuntimeError("NCCL distributed execution requires CUDA")
        torch.cuda.set_device(local_rank)
        device = torch.device("cuda", local_rank)
    else:
        device = torch.device("cpu")
    if not distributed.is_initialized():
        distributed.init_process_group(backend=backend, init_method="env://")
    if distributed.get_world_size() != 2:
        raise ValueError("distributed FDTD currently requires two torchrun ranks")
    return device
