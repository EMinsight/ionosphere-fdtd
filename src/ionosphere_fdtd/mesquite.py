"""Offline optimization of geodesic vertices with Sandia Mesquite."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any

import numpy as np

from .mesh import (
    FloatArray,
    GeodesicMesh,
    build_geodesic_mesh_from_vertices,
)

MESQUITE_COMMIT = "7ae51c8e8617c67e63018c8a7effc0f5455f58b4"
MESQUITE_ARCHIVE_SHA256 = (
    "64cb1162807a1e99e3bfc6288ccf91b3dc43dbf30fabeda6c3126021e18a0a4a"
)
MESQUITE_OBJECTIVE = "uniform-shape-size:TShapeSizeB1:PMeanP(1)"
MESQUITE_VERTEX_MOVER = "TrustRegion"


@dataclass(frozen=True, slots=True)
class MesquiteOptimization:
    """One externally optimized mesh and its reproducibility metadata."""

    mesh: GeodesicMesh
    elapsed_s: float
    maximum_displacement_rad: float
    executable_sha256: str
    stdout: str
    fixed_vertex_count: int


def optimize_with_mesquite(
    mesh: GeodesicMesh,
    executable: str | Path,
    *,
    orientation: str = "polar",
    fixed_vertices: str = "poles",
    movement_tolerance: float = 1.0e-10,
    max_iterations: int = 200,
    timeout_s: float = 1_800.0,
) -> MesquiteOptimization:
    """Optimize coordinates without changing the supplied mesh topology."""

    if fixed_vertices not in {"none", "poles", "pentagons"}:
        raise ValueError("fixed_vertices must be 'none', 'poles', or 'pentagons'")
    if movement_tolerance <= 0.0:
        raise ValueError("movement_tolerance must be positive")
    if max_iterations < 1:
        raise ValueError("max_iterations must be positive")
    if timeout_s <= 0.0:
        raise ValueError("timeout_s must be positive")

    optimizer = Path(executable).expanduser().resolve()
    if not optimizer.is_file():
        raise FileNotFoundError(f"Mesquite optimizer does not exist: {optimizer}")
    if not optimizer.stat().st_mode & 0o111:
        raise PermissionError(f"Mesquite optimizer is not executable: {optimizer}")

    fixed = _fixed_vertex_flags(mesh, fixed_vertices)
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="ionosphere-mesquite-") as directory:
        root = Path(directory)
        input_vtk = root / "input.vtk"
        output_vtk = root / "output.vtk"
        _write_vtk(input_vtk, mesh, fixed)
        try:
            completed = subprocess.run(
                [
                    str(optimizer),
                    str(input_vtk),
                    str(output_vtk),
                    f"{movement_tolerance:.17g}",
                    str(max_iterations),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except subprocess.CalledProcessError as error:
            detail = (error.stderr or error.stdout or "").strip()
            raise RuntimeError(f"Mesquite optimization failed: {detail}") from error
        except subprocess.TimeoutExpired as error:
            raise TimeoutError(
                f"Mesquite optimization exceeded {timeout_s:g} seconds"
            ) from error
        coordinates = _read_vtk_points(output_vtk, mesh.n_vertices)

    coordinates[fixed] = mesh.vertices[fixed]
    optimized = build_geodesic_mesh_from_vertices(
        mesh.subdivision,
        coordinates,
        orientation=orientation,
    )
    dot = np.clip(np.sum(mesh.vertices * optimized.vertices, axis=1), -1.0, 1.0)
    return MesquiteOptimization(
        mesh=optimized,
        elapsed_s=time.perf_counter() - started,
        maximum_displacement_rad=float(np.max(np.arccos(dot))),
        executable_sha256=_file_sha256(optimizer),
        stdout=completed.stdout,
        fixed_vertex_count=int(np.count_nonzero(fixed)),
    )


def save_optimized_mesh(
    path: str | Path,
    result: MesquiteOptimization,
    *,
    orientation: str,
    fixed_vertices: str,
    movement_tolerance: float,
    max_iterations: int,
    quality_before: dict[str, float],
    quality_after: dict[str, float],
) -> Path:
    """Store optimized vertices and enough metadata to audit their origin."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    metadata: dict[str, Any] = {
        "format_version": 1,
        "optimizer": "Sandia Mesquite",
        "mesquite_commit": MESQUITE_COMMIT,
        "mesquite_archive_sha256": MESQUITE_ARCHIVE_SHA256,
        "mesquite_objective": MESQUITE_OBJECTIVE,
        "mesquite_vertex_mover": MESQUITE_VERTEX_MOVER,
        "optimizer_executable_sha256": result.executable_sha256,
        "subdivision": result.mesh.subdivision,
        "orientation": orientation,
        "fixed_vertices": fixed_vertices,
        "fixed_vertex_count": result.fixed_vertex_count,
        "movement_tolerance": movement_tolerance,
        "max_iterations": max_iterations,
        "elapsed_s": result.elapsed_s,
        "maximum_displacement_rad": result.maximum_displacement_rad,
        "quality_before": quality_before,
        "quality_after": quality_after,
    }
    np.savez_compressed(
        destination,
        vertices=result.mesh.vertices,
        metadata=np.asarray(json.dumps(metadata, sort_keys=True)),
    )
    return destination


def load_optimized_mesh(
    path: str | Path,
    *,
    expected_subdivision: int | None = None,
    expected_orientation: str | None = None,
) -> tuple[GeodesicMesh, dict[str, Any]]:
    """Load an optimized-coordinate archive and rebuild all mesh metrics."""

    source = Path(path)
    try:
        with np.load(source, allow_pickle=False) as archive:
            vertices = np.asarray(archive["vertices"], dtype=np.float64)
            metadata = json.loads(str(archive["metadata"]))
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid optimized mesh archive: {source}") from error
    if metadata.get("format_version") != 1:
        raise ValueError("unsupported optimized mesh format")
    subdivision = int(metadata["subdivision"])
    orientation = str(metadata["orientation"])
    if expected_subdivision is not None and subdivision != expected_subdivision:
        raise ValueError(
            f"optimized mesh subdivision {subdivision} does not match "
            f"requested subdivision {expected_subdivision}"
        )
    if expected_orientation is not None and orientation != expected_orientation:
        raise ValueError(
            f"optimized mesh orientation {orientation!r} does not match "
            f"requested orientation {expected_orientation!r}"
        )
    mesh = build_geodesic_mesh_from_vertices(
        subdivision,
        vertices,
        orientation=orientation,
    )
    return mesh, metadata


def _fixed_vertex_flags(mesh: GeodesicMesh, mode: str) -> np.ndarray:
    if mode == "none":
        return np.zeros(mesh.n_vertices, dtype=np.bool_)
    if mode == "pentagons":
        return mesh.vertex_degree == 5
    flags = (mesh.vertex_degree == 5) & np.isclose(
        np.abs(mesh.vertices[:, 2]), 1.0, rtol=0.0, atol=1.0e-13
    )
    if np.count_nonzero(flags) != 2:
        raise ValueError("the mesh does not have pentagonal cells at both poles")
    return flags


def _write_vtk(path: Path, mesh: GeodesicMesh, fixed: np.ndarray) -> None:
    if fixed.shape != (mesh.n_vertices,):
        raise ValueError("fixed flags do not match the mesh vertices")
    with path.open("w", encoding="ascii") as stream:
        stream.write(
            "# vtk DataFile Version 3.0\n"
            "ionosphere-fdtd geodesic grid\n"
            "ASCII\n"
            "DATASET UNSTRUCTURED_GRID\n"
            f"POINTS {mesh.n_vertices} double\n"
        )
        np.savetxt(stream, mesh.vertices, fmt="%.17g")
        stream.write(f"CELLS {mesh.n_faces} {4 * mesh.n_faces}\n")
        cells = np.column_stack(
            (np.full(mesh.n_faces, 3, dtype=np.int64), mesh.faces)
        )
        np.savetxt(stream, cells, fmt="%d")
        stream.write(f"CELL_TYPES {mesh.n_faces}\n")
        np.savetxt(stream, np.full(mesh.n_faces, 5, dtype=np.int8), fmt="%d")
        stream.write(
            f"POINT_DATA {mesh.n_vertices}\n"
            "SCALARS fixed int 1\n"
            "LOOKUP_TABLE default\n"
        )
        np.savetxt(stream, fixed.astype(np.int8), fmt="%d")


def _read_vtk_points(path: Path, expected_count: int) -> FloatArray:
    values: list[float] = []
    with path.open("r", encoding="ascii") as stream:
        for line in stream:
            fields = line.split()
            if fields and fields[0] == "POINTS":
                if len(fields) != 3 or int(fields[1]) != expected_count:
                    raise ValueError("Mesquite output has the wrong vertex count")
                break
        else:
            raise ValueError("Mesquite output does not contain VTK points")
        for line in stream:
            values.extend(float(value) for value in line.split())
            if len(values) >= 3 * expected_count:
                break
    if len(values) != 3 * expected_count:
        raise ValueError("Mesquite output contains incomplete vertex coordinates")
    coordinates = np.asarray(values, dtype=np.float64).reshape(expected_count, 3)
    if not np.all(np.isfinite(coordinates)):
        raise ValueError("Mesquite output contains non-finite coordinates")
    return coordinates


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
