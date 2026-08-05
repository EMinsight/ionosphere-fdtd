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
        # Own backend constants independently of the public mesh object. This
        # prevents shallow NumPy aliasing from invalidating only part of the
        # precomputed geometry.
        self.edges = np.array(mesh.edges, dtype=np.int64, copy=True)
        self.face_edges = np.array(mesh.face_edges, dtype=np.int64, copy=True)
        self.face_edge_signs = np.array(
            mesh.face_edge_signs, dtype=self.dtype, copy=True
        )
        self.edge_left_faces = np.array(
            mesh.edge_left_faces, dtype=np.int64, copy=True
        )
        self.edge_right_faces = np.array(
            mesh.edge_right_faces, dtype=np.int64, copy=True
        )
        self.n_vertices = mesh.n_vertices
        self.vertex_edges, self.vertex_edge_signs = self._vertex_incidence(mesh)

    def _vertex_incidence(self, mesh: Any) -> tuple[np.ndarray, np.ndarray]:
        """Build a padded degree-six incidence table for dual-cell sums."""

        edge_indices = np.arange(len(self.edges), dtype=np.int64)
        vertices = np.concatenate((self.edges[:, 0], self.edges[:, 1]))
        incident_edges = np.concatenate((edge_indices, edge_indices))
        incident_signs = np.concatenate(
            (
                np.ones(len(self.edges), dtype=self.dtype),
                -np.ones(len(self.edges), dtype=self.dtype),
            )
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
        vertex_edges = np.zeros(
            (self.n_vertices, maximum_degree), dtype=np.int64
        )
        vertex_signs = np.zeros(
            (self.n_vertices, maximum_degree), dtype=self.dtype
        )
        vertex_edges[vertices, slots] = incident_edges
        vertex_signs[vertices, slots] = incident_signs
        return vertex_edges, vertex_signs

    def asarray(self, values: Any) -> np.ndarray:
        return np.array(values, dtype=self.dtype, copy=True)

    def index_array(self, values: Any) -> np.ndarray:
        return np.array(values, dtype=np.int64, copy=True)

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
        sign_shape = (self.n_vertices,) + (1,) * (edge_values.ndim - 1)
        result = edge_values[self.vertex_edges[:, 0]].copy()
        result *= self.vertex_edge_signs[:, 0].reshape(sign_shape)
        for slot in range(1, self.vertex_edges.shape[1]):
            result += edge_values[self.vertex_edges[:, slot]] * (
                self.vertex_edge_signs[:, slot].reshape(sign_shape)
            )
        return result

    def to_numpy(self, values: Array) -> np.ndarray:
        return np.asarray(values)

    def scalar(self, value: Array) -> float:
        return float(value)

    def max_abs(self, values: np.ndarray) -> float:
        return float(np.max(np.abs(values)))

    def nbytes(self, values: np.ndarray) -> int:
        return int(values.nbytes)
