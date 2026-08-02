"""Backend selection for NumPy and PyTorch FDTD execution."""

from __future__ import annotations

from typing import Any

from .base import Array, ArrayBackend, BackendUnavailableError
from .numpy_backend import NumPyBackend
from .torch_backend import TorchBackend


def create_backend(
    name: str,
    mesh: Any,
    *,
    device: str = "auto",
    dtype: str = "auto",
) -> ArrayBackend:
    """Create a configured array backend without importing torch eagerly."""

    normalized = name.lower()
    if normalized == "numpy":
        return NumPyBackend(mesh, device=device, dtype=dtype)
    if normalized in {"torch", "pytorch"}:
        return TorchBackend(mesh, device=device, dtype=dtype)
    raise ValueError("backend must be 'numpy' or 'torch'")


__all__ = [
    "Array",
    "ArrayBackend",
    "BackendUnavailableError",
    "NumPyBackend",
    "TorchBackend",
    "create_backend",
]
