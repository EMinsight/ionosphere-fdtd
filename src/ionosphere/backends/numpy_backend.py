"""NumPy implementation of the FDTD array backend."""

from __future__ import annotations

from typing import Any

import numpy as np

from .base import Array, ArrayBackend, BackendUnavailableError


class NumPyBackend(ArrayBackend):
    """Execute the FDTD update with host NumPy arrays."""

    name = "numpy"
    device = "cpu"

    def __init__(self, mesh: Any, *, device: str = "auto", dtype: str = "auto"):
        if device not in {"auto", "cpu"}:
            raise BackendUnavailableError(
                "the NumPy backend only supports device='cpu'"
            )
        if dtype == "auto":
            dtype = "float64"
        if dtype not in {"float32", "float64"}:
            raise ValueError("dtype must be 'auto', 'float32', or 'float64'")
        self.dtype = np.dtype(dtype)
        self.dtype_name = self.dtype.name
        self.edges = mesh.edges
        self.face_edges = mesh.face_edges
        self.face_edge_signs = mesh.face_edge_signs
        self.edge_left_faces = mesh.edge_left_faces
        self.edge_right_faces = mesh.edge_right_faces
        self.n_vertices = mesh.n_vertices

    def asarray(self, values: Any) -> np.ndarray:
        return np.asarray(values, dtype=self.dtype)

    def index_array(self, values: Any) -> np.ndarray:
        return np.asarray(values, dtype=np.int64)

    def zeros(self, shape: tuple[int, ...]) -> np.ndarray:
        return np.zeros(shape, dtype=self.dtype)

    def empty_like(self, values: np.ndarray) -> np.ndarray:
        return np.empty_like(values)

    def diff(self, values: np.ndarray, axis: int) -> np.ndarray:
        return np.diff(values, axis=axis)

    def edge_difference(self, vertex_values: np.ndarray) -> np.ndarray:
        return vertex_values[self.edges[:, 1]] - vertex_values[self.edges[:, 0]]

    def dual_edge_difference(self, face_values: np.ndarray) -> np.ndarray:
        return face_values[self.edge_left_faces] - face_values[self.edge_right_faces]

    def face_circulation(self, edge_values: np.ndarray) -> np.ndarray:
        selected = edge_values[self.face_edges]
        signs = self.face_edge_signs
        while signs.ndim < selected.ndim:
            signs = signs[..., None]
        return np.sum(selected * signs, axis=1)

    def dual_cell_circulation(self, edge_values: np.ndarray) -> np.ndarray:
        output_shape = (self.n_vertices,) + edge_values.shape[1:]
        result = np.zeros(output_shape, dtype=edge_values.dtype)
        np.add.at(result, self.edges[:, 0], edge_values)
        np.add.at(result, self.edges[:, 1], -edge_values)
        return result

    def to_numpy(self, values: Array) -> np.ndarray:
        return np.asarray(values)

    def scalar(self, value: Array) -> float:
        return float(value)

    def max_abs(self, values: np.ndarray) -> float:
        return float(np.max(np.abs(values)))

    def nbytes(self, values: np.ndarray) -> int:
        return int(values.nbytes)
