"""Array-backend contract for the geodesic FDTD time integrator."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

import numpy as np
from numpy.typing import NDArray

Array = Any


class BackendUnavailableError(RuntimeError):
    """Raised when a requested compute backend or device cannot be used."""


class ArrayBackend(ABC):
    """Minimal tensor operations required by the FDTD update loop."""

    name: str
    device: str
    dtype_name: str

    def compile_step(
        self, step: Callable[[Array], None]
    ) -> Callable[[Array], None]:
        """Compile a tensor-only field step when supported."""

        raise BackendUnavailableError(
            f"the {self.name} backend does not support compiled field steps"
        )

    @abstractmethod
    def asarray(self, values: Any) -> Array:
        """Move floating-point values to this backend."""

    @abstractmethod
    def index_array(self, values: Any) -> Array:
        """Move integer indices to this backend."""

    @abstractmethod
    def zeros(self, shape: tuple[int, ...]) -> Array:
        """Allocate a floating-point zero array."""

    @abstractmethod
    def empty_like(self, values: Array) -> Array:
        """Allocate an uninitialized array matching ``values``."""

    @abstractmethod
    def diff(self, values: Array, axis: int) -> Array:
        """Return adjacent differences along an axis."""

    @abstractmethod
    def edge_difference(self, vertex_values: Array) -> Array:
        """Return head-minus-tail values on primal edges."""

    @abstractmethod
    def dual_edge_difference(self, face_values: Array) -> Array:
        """Return left-minus-right values across primal edges."""

    @abstractmethod
    def face_circulation(self, edge_values: Array) -> Array:
        """Sum oriented edge values around primal faces."""

    @abstractmethod
    def dual_cell_circulation(self, edge_values: Array) -> Array:
        """Accumulate oriented dual-edge values around dual cells."""

    @abstractmethod
    def to_numpy(self, values: Array) -> NDArray[np.generic]:
        """Expose values as a host NumPy array, copying when necessary."""

    @abstractmethod
    def scalar(self, value: Array) -> float:
        """Convert a scalar backend value to a Python float."""

    @abstractmethod
    def max_abs(self, values: Array) -> float:
        """Return the maximum absolute value as a Python float."""

    @abstractmethod
    def nbytes(self, values: Array) -> int:
        """Return allocated field bytes."""
