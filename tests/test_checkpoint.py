import json

import numpy as np
import pytest

from ionosphere_fdtd import CheckpointError
from ionosphere_fdtd.cli import main
from ionosphere_fdtd.materials import (
    EarthIonosphereMaterial,
    LayeredEarthIonosphereMaterial,
    SphericalAnomaly,
)
from ionosphere_fdtd.solver import GeodesicFDTD, SimulationConfig
from ionosphere_fdtd.sources import GaussianCurrent, TangentialGaussianCurrent


def checkpoint_config(**changes: object) -> SimulationConfig:
    values = dict(subdivision=1, radial_cells=6, courant_factor=0.25)
    values.update(changes)
    return SimulationConfig(**values)


def assert_same_state(first: GeodesicFDTD, second: GeodesicFDTD) -> None:
    assert second.config == first.config
    assert second.material == first.material
    assert second.source == first.source
    assert second.steps == first.steps
    assert second.time_s == pytest.approx(first.time_s)
    np.testing.assert_array_equal(second.mesh.vertices, first.mesh.vertices)
    for name in ("er", "et", "hr", "ht"):
        np.testing.assert_array_equal(
            second.to_numpy(getattr(second, name)),
            first.to_numpy(getattr(first, name)),
        )


def test_checkpoint_round_trip_and_continuation(tmp_path) -> None:
    material = EarthIonosphereMaterial(
        anomalies=(
            SphericalAnomaly(35.0, 126.0, 500_000.0, -20_000.0, -1_000.0, 0.5),
        )
    )
    source = GaussianCurrent(
        peak_current_a=2.0e6,
        center_time_s=0.01,
        one_over_e_half_width_s=0.02,
        carrier_frequency_hz=5.0,
    )
    uninterrupted = GeodesicFDTD(checkpoint_config(), material, source)
    resumed_source = GeodesicFDTD(checkpoint_config(), material, source)
    uninterrupted.step(12)
    resumed_source.step(5)

    path = resumed_source.save_checkpoint(tmp_path / "state.npz")
    resumed = GeodesicFDTD.load_checkpoint(path)
    assert_same_state(resumed_source, resumed)

    resumed.step(7)
    assert_same_state(uninterrupted, resumed)


def test_checkpoint_preserves_tangential_source_and_optimized_mesh(tmp_path) -> None:
    source = TangentialGaussianCurrent(
        azimuths_deg=(15.0, 90.0),
        line_lengths_m=(10_000.0, 20_000.0),
        edge_assignment="nearest",
    )
    simulation = GeodesicFDTD(
        checkpoint_config(mesh_optimization_steps=1), source=source, dtype="float32"
    )
    simulation.step(3)

    restored = GeodesicFDTD.load_checkpoint(
        simulation.save_checkpoint(tmp_path / "tangential.npz")
    )

    assert restored.backend.dtype_name == "float32"
    assert_same_state(simulation, restored)

    converted = GeodesicFDTD.load_checkpoint(
        tmp_path / "tangential.npz", dtype="float64"
    )
    assert converted.backend.dtype_name == "float64"
    for name in ("er", "et", "hr", "ht"):
        np.testing.assert_array_equal(
            converted.to_numpy(getattr(converted, name)),
            simulation.to_numpy(getattr(simulation, name)).astype(np.float64),
        )


def test_checkpoint_rejects_unsupported_material(tmp_path) -> None:
    material = LayeredEarthIonosphereMaterial(
        land_classifier=lambda directions: np.ones(len(directions), dtype=np.bool_)
    )
    simulation = GeodesicFDTD(checkpoint_config(), material=material)

    with pytest.raises(CheckpointError, match="EarthIonosphereMaterial only"):
        simulation.save_checkpoint(tmp_path / "unsupported.npz")


def test_checkpoint_rejects_wrong_version(tmp_path) -> None:
    simulation = GeodesicFDTD(checkpoint_config())
    original = simulation.save_checkpoint(tmp_path / "original.npz")
    with np.load(original, allow_pickle=False) as archive:
        arrays = {name: np.array(archive[name], copy=True) for name in archive.files}
    metadata = json.loads(str(arrays["metadata"].item()))
    metadata["version"] = 999
    arrays["metadata"] = np.asarray(json.dumps(metadata))
    invalid = tmp_path / "invalid.npz"
    np.savez_compressed(invalid, **arrays)

    with pytest.raises(CheckpointError, match="unsupported checkpoint version"):
        GeodesicFDTD.load_checkpoint(invalid)


def test_cli_writes_and_resumes_checkpoint(tmp_path, capsys) -> None:
    checkpoint = tmp_path / "cli-state.npz"
    assert main(
        [
            "--subdivision",
            "0",
            "--radial-cells",
            "4",
            "--steps",
            "3",
            "--report-every",
            "2",
            "--checkpoint-every",
            "2",
            "--checkpoint",
            str(checkpoint),
        ]
    ) == 0
    assert checkpoint.exists()
    assert GeodesicFDTD.load_checkpoint(checkpoint).steps == 3

    assert main(["--resume", str(checkpoint), "--steps", "2"]) == 0
    output = capsys.readouterr().out
    assert "step=     5" in output
