import json
from pathlib import Path

import numpy as np
import pytest

from ionosphere_fdtd.mesh import build_geodesic_mesh
from ionosphere_fdtd.mesquite import (
    _fixed_vertex_flags,
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
    )
    path.chmod(0o755)
    return path


def test_vtk_round_trip_retains_vertex_order_and_fixed_flags(tmp_path: Path) -> None:
    mesh = build_geodesic_mesh(1)
    fixed = _fixed_vertex_flags(mesh, "poles")
    vtk = tmp_path / "mesh.vtk"

    _write_vtk(vtk, mesh, fixed)
    result = _read_vtk_points(vtk, mesh.n_vertices)

    np.testing.assert_allclose(result, mesh.vertices, rtol=0.0, atol=0.0)
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
    assert json.loads(str(np.load(archive)["metadata"]))["format_version"] == 1


def test_mesquite_rejects_unknown_fixed_mode(tmp_path: Path) -> None:
    mesh = build_geodesic_mesh(0)
    with pytest.raises(ValueError, match="fixed_vertices"):
        optimize_with_mesquite(mesh, tmp_path / "missing", fixed_vertices="anchors")
