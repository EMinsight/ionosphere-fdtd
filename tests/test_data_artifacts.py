import json

import numpy as np
import pytest

from ionosphere_fdtd.data_artifacts import (
    DataArtifactError,
    DatasetProvenance,
    MeshMaterialArtifact,
    VariableProvenance,
    file_sha256,
)
from ionosphere_fdtd.mesh import build_geodesic_mesh
from ionosphere_fdtd.solver import GeodesicFDTD, SimulationConfig


def _provenance(tmp_path) -> DatasetProvenance:
    source = tmp_path / "synthetic-source.txt"
    source.write_text("controlled source values\n")
    return DatasetProvenance.from_file(
        source,
        dataset_id="test.synthetic.v1",
        title="Synthetic material fixture",
        version="1.0",
        source_url="https://example.invalid/material-v1",
        citation="Synthetic fixture generated for regression testing.",
        license="CC0-1.0",
        retrieved_at="2026-08-20T10:00:00Z",
        coordinate_reference_system="geocentric unit vectors; WGS 84 lat/lon",
        variables=(
            VariableProvenance(
                name="conductivity",
                source_units="S/m",
                canonical_units="S/m",
                conversion="identity",
            ),
            VariableProvenance(
                name="relative_permittivity",
                source_units="1",
                canonical_units="1",
                conversion="identity",
            ),
        ),
    )


def _artifact(tmp_path) -> tuple[MeshMaterialArtifact, GeodesicFDTD]:
    simulation = GeodesicFDTD(
        SimulationConfig(
            subdivision=0,
            radial_cells=2,
            minimum_altitude_m=-1_000.0,
            maximum_altitude_m=1_000.0,
        )
    )
    artifact = MeshMaterialArtifact.from_simulation(
        simulation,
        provenance=(_provenance(tmp_path),),
        interpolation="analytic fixture sampled at solver support points",
        processing_steps=(
            "normalize directions to geocentric unit vectors",
            "sample conductivity and relative permittivity in SI units",
        ),
    )
    return artifact, simulation


def test_dataset_provenance_hashes_exact_source_and_requires_timezone(tmp_path) -> None:
    provenance = _provenance(tmp_path)
    source = tmp_path / "synthetic-source.txt"

    assert provenance.source_sha256 == file_sha256(source)
    with pytest.raises(DataArtifactError, match="timezone"):
        DatasetProvenance(
            **{
                **{
                    name: getattr(provenance, name)
                    for name in provenance.__dataclass_fields__
                },
                "retrieved_at": "2026-08-20T10:00:00",
            }
        )


def test_mesh_material_round_trip_is_solver_native_and_read_only(tmp_path) -> None:
    artifact, original = _artifact(tmp_path)
    path = artifact.save(tmp_path / "mesh-material.npz")

    loaded = MeshMaterialArtifact.load(path)
    restored = GeodesicFDTD(
        original.config,
        mesh=original.mesh,
        material=loaded,
    )

    assert loaded.content_sha256 == artifact.content_sha256
    assert not loaded.sigma_er.flags.writeable
    np.testing.assert_array_equal(restored.sigma_er, original.sigma_er)
    np.testing.assert_array_equal(restored.sigma_et, original.sigma_et)
    np.testing.assert_array_equal(restored._ca_er, original._ca_er)
    np.testing.assert_array_equal(restored._cb_et, original._cb_et)
    with np.load(path, allow_pickle=False) as archive:
        metadata = json.loads(str(archive["metadata"].item()))
    assert metadata["format"] == "ionosphere-fdtd-mesh-material"
    assert metadata["provenance"][0]["license"] == "CC0-1.0"
    assert metadata["arrays"]["sigma_er"]["sha256"]


def test_mesh_material_rejects_corrupt_array(tmp_path) -> None:
    artifact, _ = _artifact(tmp_path)
    path = artifact.save(tmp_path / "valid.npz")
    with np.load(path, allow_pickle=False) as archive:
        arrays = {name: np.array(archive[name], copy=True) for name in archive.files}
    arrays["sigma_er"][0, 0] += 1.0
    corrupt = tmp_path / "corrupt.npz"
    np.savez_compressed(corrupt, **arrays)

    with pytest.raises(DataArtifactError, match="sigma_er checksum mismatch"):
        MeshMaterialArtifact.load(corrupt)


def test_mesh_material_rejects_mesh_and_sampling_policy_mismatch(tmp_path) -> None:
    artifact, original = _artifact(tmp_path)
    with pytest.raises(DataArtifactError, match="vertices do not match"):
        artifact.sample_mesh(
            build_geodesic_mesh(1),
            original.altitudes_m,
            original.config.earth_radius_m,
            radial_material_support="point",
            tangential_material_support="point",
            horizontal_anomaly_mode="point",
        )

    incompatible = SimulationConfig(
        subdivision=0,
        radial_cells=2,
        minimum_altitude_m=-1_000.0,
        maximum_altitude_m=1_000.0,
        radial_material_support="dual-cell",
    )
    with pytest.raises(DataArtifactError, match="sampling policy"):
        GeodesicFDTD(incompatible, mesh=original.mesh, material=artifact)
