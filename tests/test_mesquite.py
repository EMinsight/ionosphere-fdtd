import json
from pathlib import Path

import numpy as np
import pytest

from ionosphere_fdtd.mesh import build_geodesic_mesh
from ionosphere_fdtd.mesquite import (
    MESQUITE_OBJECTIVE,
    MESQUITE_VERTEX_MOVER,
    _array_sha256,
    _fixed_vertex_flags,
    _read_vtk_faces,
    _read_vtk_points,
    _write_vtk,
    load_optimized_mesh,
    optimize_with_mesquite,
    save_optimized_mesh,
)


def _copy_optimizer(path: Path) -> Path:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import shutil, sys\n"
        "shutil.copyfile(sys.argv[1], sys.argv[2])\n"
        "print('mesquite_version=Mesquite test')\n"
        f"print('objective={MESQUITE_OBJECTIVE}')\n"
        f"print('vertex_mover={MESQUITE_VERTEX_MOVER}')\n"
    )
    path.chmod(0o755)
    return path


def test_vtk_round_trip_retains_vertex_order_and_fixed_flags(tmp_path: Path) -> None:
    mesh = build_geodesic_mesh(1)
    fixed = _fixed_vertex_flags(mesh, "poles")
    vtk = tmp_path / "mesh.vtk"

    _write_vtk(vtk, mesh, fixed)
    result = _read_vtk_points(vtk, mesh.n_vertices)
    faces = _read_vtk_faces(vtk, mesh.n_faces)

    np.testing.assert_allclose(result, mesh.vertices, rtol=0.0, atol=0.0)
    np.testing.assert_array_equal(faces, mesh.faces)
    assert np.count_nonzero(fixed) == 2
    assert "SCALARS fixed int 1" in vtk.read_text()


def test_mesquite_runner_preserves_topology_with_copy_optimizer(
    tmp_path: Path,
) -> None:
    mesh = build_geodesic_mesh(1)
    executable = _copy_optimizer(tmp_path / "copy_optimizer")

    result = optimize_with_mesquite(mesh, executable, timeout_s=10.0)

    np.testing.assert_array_equal(result.mesh.faces, mesh.faces)
    np.testing.assert_allclose(result.mesh.vertices, mesh.vertices, atol=1.0e-15)
    assert result.fixed_vertex_count == 2
    assert result.maximum_displacement_rad == pytest.approx(0.0, abs=1.0e-7)


def test_optimized_mesh_archive_round_trip(tmp_path: Path) -> None:
    base = build_geodesic_mesh(1)
    executable = _copy_optimizer(tmp_path / "copy_optimizer")
    result = optimize_with_mesquite(base, executable, timeout_s=10.0)
    archive = save_optimized_mesh(
        tmp_path / "mesh.npz",
        result,
        orientation="polar",
        fixed_vertices="poles",
        movement_tolerance=1.0e-10,
        max_iterations=200,
        quality_before={"example": 1.0},
        quality_after={"example": 0.5},
    )

    loaded, metadata = load_optimized_mesh(
        archive,
        expected_subdivision=1,
        expected_orientation="polar",
    )

    np.testing.assert_allclose(loaded.vertices, base.vertices, atol=1.0e-15)
    assert metadata["quality_after"] == {"example": 0.5}
    stored = json.loads(str(np.load(archive)["metadata"]))
    assert stored["format_version"] == 2
    assert stored["vertices_sha256"] == _array_sha256(result.mesh.vertices)


def test_mesquite_rejects_unknown_fixed_mode(tmp_path: Path) -> None:
    mesh = build_geodesic_mesh(0)
    with pytest.raises(ValueError, match="fixed_vertices"):
        optimize_with_mesquite(mesh, tmp_path / "missing", fixed_vertices="anchors")


def test_optimized_mesh_archive_rejects_coordinate_tampering(tmp_path: Path) -> None:
    base = build_geodesic_mesh(1)
    executable = _copy_optimizer(tmp_path / "copy_optimizer")
    result = optimize_with_mesquite(base, executable, timeout_s=10.0)
    archive = save_optimized_mesh(
        tmp_path / "mesh.npz",
        result,
        orientation="polar",
        fixed_vertices="poles",
        movement_tolerance=1.0e-10,
        max_iterations=200,
        quality_before={},
        quality_after={},
    )
    with np.load(archive, allow_pickle=False) as values:
        vertices = values["vertices"].copy()
        metadata = values["metadata"].copy()
        stdout = values["optimizer_stdout"].copy()
    vertices[0, 0] = np.nextafter(vertices[0, 0], np.inf)
    np.savez_compressed(
        archive,
        vertices=vertices,
        metadata=metadata,
        optimizer_stdout=stdout,
    )

    with pytest.raises(ValueError, match="checksum"):
        load_optimized_mesh(archive)


def test_optimized_mesh_save_returns_normalized_npz_path(tmp_path: Path) -> None:
    base = build_geodesic_mesh(1)
    executable = _copy_optimizer(tmp_path / "copy_optimizer")
    result = optimize_with_mesquite(base, executable, timeout_s=10.0)

    archive = save_optimized_mesh(
        tmp_path / "mesh",
        result,
        orientation="polar",
        fixed_vertices="poles",
        movement_tolerance=1.0e-10,
        max_iterations=200,
        quality_before={},
        quality_after={},
    )

    assert archive == tmp_path / "mesh.npz"
    assert archive.is_file()
