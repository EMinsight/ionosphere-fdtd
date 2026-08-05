"""PyTorch implementation of the FDTD array backend."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from .base import Array, ArrayBackend, BackendUnavailableError


class TorchBackend(ArrayBackend):
    """Execute the FDTD update with PyTorch tensors on CPU, MPS, or CUDA."""

    name = "torch"

    def __init__(
        self,
        mesh: Any,
        *,
        device: str = "auto",
        dtype: str = "auto",
        threads: int | None = None,
    ):
        try:
            import torch
        except ImportError as error:
            raise BackendUnavailableError(
                "install the PyTorch backend with: uv sync --extra pytorch"
            ) from error

        self.torch = torch
        self.torch_device = self._resolve_device(device)
        self.device = str(self.torch_device)
        if dtype == "auto":
            dtype = "float32"
        if dtype not in {"float32", "float64"}:
            raise ValueError("dtype must be 'auto', 'float32', or 'float64'")
        if self.torch_device.type == "mps" and dtype == "float64":
            raise BackendUnavailableError(
                "the MPS backend does not support float64; use dtype='float32'"
            )
        if threads is not None:
            if isinstance(threads, bool) or threads < 1:
                raise ValueError("torch_threads must be a positive integer")
            if self.torch_device.type != "cpu":
                raise BackendUnavailableError(
                    "torch_threads is only valid for the PyTorch CPU backend"
                )
            torch.set_num_threads(threads)
        self.threads = (
            torch.get_num_threads() if self.torch_device.type == "cpu" else None
        )
        self.dtype = torch.float32 if dtype == "float32" else torch.float64
        self.dtype_name = dtype
        self.edges = self.index_array(mesh.edges)
        self.face_edges = self.index_array(mesh.face_edges)
        self.face_edge_signs = self.asarray(mesh.face_edge_signs)
        self.edge_left_faces = self.index_array(mesh.edge_left_faces)
        self.edge_right_faces = self.index_array(mesh.edge_right_faces)
        self.n_vertices = mesh.n_vertices
        self.vertex_edges, self.vertex_edge_signs = self._vertex_incidence(mesh)

    def _vertex_incidence(self, mesh: Any) -> tuple[Any, Any]:
        """Build a deterministic padded degree-six dual incidence table."""

        edge_indices = np.arange(len(mesh.edges), dtype=np.int64)
        vertices = np.concatenate((mesh.edges[:, 0], mesh.edges[:, 1]))
        incident_edges = np.concatenate((edge_indices, edge_indices))
        incident_signs = np.concatenate(
            (np.ones(len(mesh.edges)), -np.ones(len(mesh.edges)))
        )
        order = np.argsort(vertices, kind="stable")
        vertices = vertices[order]
        incident_edges = incident_edges[order]
        incident_signs = incident_signs[order]
        counts = np.bincount(vertices, minlength=self.n_vertices)
        if not np.array_equal(counts, mesh.vertex_degree):
            raise RuntimeError("mesh vertex degree does not match edge incidence")
        offsets = np.cumsum(np.concatenate(([0], counts[:-1])))
        slots = np.arange(len(vertices)) - np.repeat(offsets, counts)
        maximum_degree = int(counts.max())
        vertex_edges = np.zeros((self.n_vertices, maximum_degree), dtype=np.int64)
        vertex_signs = np.zeros((self.n_vertices, maximum_degree))
        vertex_edges[vertices, slots] = incident_edges
        vertex_signs[vertices, slots] = incident_signs
        return self.index_array(vertex_edges), self.asarray(vertex_signs)

    def compile_step(
        self, step: Callable[[Array], None]
    ) -> Callable[[Array], None]:
        """Compile a static-shape field step with TorchInductor."""

        return self.torch.compile(step, fullgraph=True, dynamic=False)

    def synchronize(self) -> None:
        if self.torch_device.type == "mps":
            self.torch.mps.synchronize()
        elif self.torch_device.type == "cuda":
            self.torch.cuda.synchronize(self.torch_device)

    def _resolve_device(self, requested: str) -> Any:
        torch = self.torch
        requested = requested.lower()
        if requested == "gpu":
            requested = "cuda"
        if requested == "auto":
            if torch.cuda.is_available():
                requested = "cuda"
            elif torch.backends.mps.is_available():
                requested = "mps"
            else:
                requested = "cpu"
        if requested == "mps" and not torch.backends.mps.is_available():
            reason = (
                "PyTorch was not built with MPS support"
                if not torch.backends.mps.is_built()
                else "MPS is unavailable on this macOS device"
            )
            raise BackendUnavailableError(reason)
        if requested.startswith("cuda") and not torch.cuda.is_available():
            raise BackendUnavailableError("CUDA is unavailable in this PyTorch runtime")
        try:
            device = torch.device(requested)
        except (RuntimeError, ValueError) as error:
            raise BackendUnavailableError(
                f"unsupported PyTorch device: {requested}"
            ) from error
        if device.type not in {"cpu", "mps", "cuda"}:
            raise BackendUnavailableError(
                "PyTorch device must be cpu, mps, cuda, cuda:N, or gpu"
            )
        if (
            device.type == "cuda"
            and device.index is not None
            and device.index >= torch.cuda.device_count()
        ):
            raise BackendUnavailableError(
                f"CUDA device index {device.index} is unavailable; "
                f"found {torch.cuda.device_count()} device(s)"
            )
        return device

    def asarray(self, values: Any) -> Any:
        return self.torch.as_tensor(
            values, dtype=self.dtype, device=self.torch_device
        )

    def index_array(self, values: Any) -> Any:
        return self.torch.as_tensor(
            values, dtype=self.torch.long, device=self.torch_device
        )

    def zeros(self, shape: tuple[int, ...]) -> Any:
        return self.torch.zeros(
            shape, dtype=self.dtype, device=self.torch_device
        )

    def empty_like(self, values: Any) -> Any:
        return self.torch.empty_like(values)

    def diff(self, values: Any, axis: int) -> Any:
        return self.torch.diff(values, dim=axis)

    def edge_difference(self, vertex_values: Any) -> Any:
        return vertex_values[self.edges[:, 1]] - vertex_values[self.edges[:, 0]]

    def dual_edge_difference(self, face_values: Any) -> Any:
        return face_values[self.edge_left_faces] - face_values[self.edge_right_faces]

    def face_circulation(self, edge_values: Any) -> Any:
        sign_shape = (self.face_edges.shape[0],) + (1,) * (
            edge_values.ndim - 1
        )
        result = edge_values[self.face_edges[:, 0]]
        result.mul_(self.face_edge_signs[:, 0].reshape(sign_shape))
        for corner in (1, 2):
            term = edge_values[self.face_edges[:, corner]]
            term.mul_(self.face_edge_signs[:, corner].reshape(sign_shape))
            result.add_(term)
        return result

    def dual_cell_circulation(self, edge_values: Any) -> Any:
        selected = edge_values[self.vertex_edges]
        sign_shape = self.vertex_edge_signs.shape + (1,) * (
            edge_values.ndim - 1
        )
        return self.torch.sum(
            selected * self.vertex_edge_signs.reshape(sign_shape), dim=1
        )

    def to_numpy(self, values: Array) -> np.ndarray:
        if not self.torch.is_tensor(values):
            return np.asarray(values)
        return values.detach().cpu().numpy()

    def scalar(self, value: Array) -> float:
        return float(value.detach().item())

    def max_abs(self, values: Any) -> float:
        return float(self.torch.max(self.torch.abs(values)).detach().item())

    def nbytes(self, values: Any) -> int:
        return int(values.numel() * values.element_size())
