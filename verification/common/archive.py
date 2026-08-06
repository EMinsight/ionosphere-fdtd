"""Reliable NumPy archive output for long-running verification jobs."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import Any

import numpy as np


def save_npz_atomic(path: str | Path, **values: Any) -> Path:
    """Atomically write a compressed NPZ and return its actual path."""

    requested = Path(path)
    output = (
        requested
        if requested.suffix.lower() == ".npz"
        else Path(f"{requested}.npz")
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+b",
            prefix=f".{output.name}.",
            suffix=".tmp",
            dir=output.parent,
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            np.savez_compressed(stream, **values)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, output)
    except BaseException:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
    return output
