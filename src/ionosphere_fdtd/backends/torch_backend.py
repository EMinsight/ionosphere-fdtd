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
        selected = edge_values[self.face_edges]
        signs = self.face_edge_signs
        while signs.ndim < selected.ndim:
            signs = signs.unsqueeze(-1)
        return self.torch.sum(selected * signs, dim=1)

    def dual_cell_circulation(self, edge_values: Any) -> Any:
        output_shape = (self.n_vertices,) + tuple(edge_values.shape[1:])
        result = self.torch.zeros(
            output_shape, dtype=edge_values.dtype, device=self.torch_device
        )
        result.index_add_(0, self.edges[:, 0], edge_values)
        result.index_add_(0, self.edges[:, 1], -edge_values)
        return result

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
