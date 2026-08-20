"""Provenance-preserving, mesh-native material data artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .mesh import GeodesicMesh


MESH_MATERIAL_FORMAT = "ionosphere-fdtd-mesh-material"
MESH_MATERIAL_VERSION = 1
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class DataArtifactError(ValueError):
    """Raised when material data provenance or content is invalid."""


@dataclass(frozen=True, slots=True)
class VariableProvenance:
    """Units and conversion record for one source variable."""

    name: str
    source_units: str
    canonical_units: str
    conversion: str

    def __post_init__(self) -> None:
        if not all(
            isinstance(value, str) and value.strip()
            for value in (
                self.name,
                self.source_units,
                self.canonical_units,
                self.conversion,
            )
        ):
            raise DataArtifactError("variable provenance fields must be nonempty")


@dataclass(frozen=True, slots=True)
class DatasetProvenance:
    """Identity, rights, coordinates, and checksum for one source dataset."""

    dataset_id: str
    title: str
    version: str
    source_url: str
    citation: str
    license: str
    retrieved_at: str
    source_sha256: str
    coordinate_reference_system: str
    variables: tuple[VariableProvenance, ...]

    def __post_init__(self) -> None:
        textual = (
            self.dataset_id,
            self.title,
            self.version,
            self.source_url,
            self.citation,
            self.license,
            self.retrieved_at,
            self.coordinate_reference_system,
        )
        if not all(isinstance(value, str) and value.strip() for value in textual):
            raise DataArtifactError("dataset provenance fields must be nonempty")
        if _SHA256_PATTERN.fullmatch(self.source_sha256) is None:
            raise DataArtifactError("source_sha256 must be a lowercase SHA-256")
        try:
            retrieved = datetime.fromisoformat(
                self.retrieved_at.replace("Z", "+00:00")
            )
        except ValueError as error:
            raise DataArtifactError("retrieved_at must be ISO 8601") from error
        if retrieved.tzinfo is None:
            raise DataArtifactError("retrieved_at must include a timezone")
        variables = tuple(self.variables)
        if not variables or not all(
            isinstance(value, VariableProvenance) for value in variables
        ):
            raise DataArtifactError("dataset provenance requires variable records")
        names = [value.name for value in variables]
        if len(set(names)) != len(names):
            raise DataArtifactError("dataset variable names must be unique")
        object.__setattr__(self, "variables", variables)

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        **metadata: Any,
    ) -> DatasetProvenance:
        """Build a source record after hashing the exact downloaded file."""

        return cls(source_sha256=file_sha256(path), **metadata)


@dataclass(frozen=True, slots=True)
class MeshMaterialArtifact:
    """Material properties sampled at one solver mesh and radial grid."""

    mesh_vertices_sha256: str
    mesh_faces_sha256: str
    radial_altitudes_m: NDArray[np.float64]
    earth_radius_m: float
    radial_material_support: str
    tangential_material_support: str
    horizontal_anomaly_mode: str
    sigma_er: NDArray[np.float64]
    epsilon_r_er: NDArray[np.float64]
    sigma_et: NDArray[np.float64]
    epsilon_r_et: NDArray[np.float64]
    provenance: tuple[DatasetProvenance, ...]
    interpolation: str
    processing_steps: tuple[str, ...]

    def __post_init__(self) -> None:
        for digest in (self.mesh_vertices_sha256, self.mesh_faces_sha256):
            if _SHA256_PATTERN.fullmatch(digest) is None:
                raise DataArtifactError("mesh checksums must be lowercase SHA-256")
        altitudes = np.asarray(self.radial_altitudes_m, dtype=np.float64)
        if (
            altitudes.ndim != 1
            or len(altitudes) < 3
            or not np.all(np.isfinite(altitudes))
            or not np.all(np.diff(altitudes) > 0.0)
        ):
            raise DataArtifactError("radial altitudes must be finite and increasing")
        if not np.isfinite(self.earth_radius_m) or self.earth_radius_m <= 0.0:
            raise DataArtifactError("earth radius must be finite and positive")
        if self.radial_material_support not in {"point", "dual-cell"}:
            raise DataArtifactError("invalid radial material support")
        if self.tangential_material_support not in {"point", "edge-diamond"}:
            raise DataArtifactError("invalid tangential material support")
        if self.horizontal_anomaly_mode not in {"point", "conservative-nearest"}:
            raise DataArtifactError("invalid horizontal anomaly mode")
        provenance = tuple(self.provenance)
        if not provenance or not all(
            isinstance(value, DatasetProvenance) for value in provenance
        ):
            raise DataArtifactError("mesh material requires dataset provenance")
        if len({value.dataset_id for value in provenance}) != len(provenance):
            raise DataArtifactError("dataset identifiers must be unique")
        processing = tuple(self.processing_steps)
        if not processing or not all(
            isinstance(value, str) and value.strip() for value in processing
        ):
            raise DataArtifactError("processing steps must be nonempty strings")
        if not isinstance(self.interpolation, str) or not self.interpolation.strip():
            raise DataArtifactError("interpolation policy must be nonempty")

        radial_layers = len(altitudes)
        arrays = {
            "sigma_er": np.asarray(self.sigma_er, dtype=np.float64),
            "epsilon_r_er": np.asarray(self.epsilon_r_er, dtype=np.float64),
            "sigma_et": np.asarray(self.sigma_et, dtype=np.float64),
            "epsilon_r_et": np.asarray(self.epsilon_r_et, dtype=np.float64),
        }
        if arrays["sigma_er"].shape != arrays["epsilon_r_er"].shape:
            raise DataArtifactError("radial material array shapes do not match")
        if arrays["sigma_et"].shape != arrays["epsilon_r_et"].shape:
            raise DataArtifactError("tangential material array shapes do not match")
        if arrays["sigma_er"].ndim != 2 or arrays["sigma_er"].shape[1] != radial_layers:
            raise DataArtifactError("radial material arrays have invalid shape")
        if (
            arrays["sigma_et"].ndim != 2
            or arrays["sigma_et"].shape[1] != radial_layers - 1
        ):
            raise DataArtifactError("tangential material arrays have invalid shape")
        if (
            not np.all(np.isfinite(arrays["sigma_er"]))
            or not np.all(np.isfinite(arrays["sigma_et"]))
            or np.any(arrays["sigma_er"] < 0.0)
            or np.any(arrays["sigma_et"] < 0.0)
        ):
            raise DataArtifactError(
                "conductivity arrays must be finite and nonnegative"
            )
        if (
            not np.all(np.isfinite(arrays["epsilon_r_er"]))
            or not np.all(np.isfinite(arrays["epsilon_r_et"]))
            or np.any(arrays["epsilon_r_er"] <= 0.0)
            or np.any(arrays["epsilon_r_et"] <= 0.0)
        ):
            raise DataArtifactError("permittivity arrays must be finite and positive")

        altitudes = _readonly_copy(altitudes)
        object.__setattr__(self, "radial_altitudes_m", altitudes)
        for name, values in arrays.items():
            object.__setattr__(self, name, _readonly_copy(values))
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "processing_steps", processing)

    @classmethod
    def from_simulation(
        cls,
        simulation: Any,
        *,
        provenance: tuple[DatasetProvenance, ...],
        interpolation: str,
        processing_steps: tuple[str, ...],
    ) -> MeshMaterialArtifact:
        """Freeze the validated material samples prepared by a solver."""

        return cls(
            mesh_vertices_sha256=mesh_vertices_sha256(simulation.mesh),
            mesh_faces_sha256=mesh_faces_sha256(simulation.mesh),
            radial_altitudes_m=simulation.altitudes_m,
            earth_radius_m=simulation.config.earth_radius_m,
            radial_material_support=simulation.config.radial_material_support,
            tangential_material_support=(
                simulation.config.tangential_material_support
            ),
            horizontal_anomaly_mode=simulation.config.horizontal_anomaly_mode,
            sigma_er=simulation.sigma_er,
            epsilon_r_er=simulation.epsilon_r_er,
            sigma_et=simulation.sigma_et,
            epsilon_r_et=simulation.epsilon_r_et,
            provenance=provenance,
            interpolation=interpolation,
            processing_steps=processing_steps,
        )

    def sample_mesh(
        self,
        mesh: GeodesicMesh,
        radial_altitudes_m: NDArray[np.float64],
        earth_radius_m: float,
        *,
        radial_material_support: str,
        tangential_material_support: str,
        horizontal_anomaly_mode: str,
    ) -> tuple[
        NDArray[np.float64],
        NDArray[np.float64],
        NDArray[np.float64],
        NDArray[np.float64],
    ]:
        """Return properties only when all mesh and sampling identities match."""

        if mesh_vertices_sha256(mesh) != self.mesh_vertices_sha256:
            raise DataArtifactError("material artifact mesh vertices do not match")
        if mesh_faces_sha256(mesh) != self.mesh_faces_sha256:
            raise DataArtifactError("material artifact mesh faces do not match")
        if not np.array_equal(radial_altitudes_m, self.radial_altitudes_m):
            raise DataArtifactError("material artifact radial grid does not match")
        if earth_radius_m != self.earth_radius_m:
            raise DataArtifactError("material artifact Earth radius does not match")
        requested = (
            radial_material_support,
            tangential_material_support,
            horizontal_anomaly_mode,
        )
        stored = (
            self.radial_material_support,
            self.tangential_material_support,
            self.horizontal_anomaly_mode,
        )
        if requested != stored:
            raise DataArtifactError("material artifact sampling policy does not match")
        if self.sigma_er.shape[0] != mesh.n_vertices:
            raise DataArtifactError("material artifact radial entity count is invalid")
        if self.sigma_et.shape[0] != mesh.n_edges:
            raise DataArtifactError(
                "material artifact tangential entity count is invalid"
            )
        return self.sigma_er, self.epsilon_r_er, self.sigma_et, self.epsilon_r_et

    @property
    def content_sha256(self) -> str:
        """Return a stable checksum over metadata and all material arrays."""

        metadata = self._metadata(include_array_checksums=True)
        canonical = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def save(self, path: str | Path) -> Path:
        """Atomically write the portable, pickle-free NPZ artifact."""

        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        arrays: dict[str, Any] = {
            "metadata": np.asarray(
                json.dumps(self._metadata(include_array_checksums=True), sort_keys=True)
            ),
            "radial_altitudes_m": self.radial_altitudes_m,
        }
        arrays.update(
            (name, getattr(self, name))
            for name in ("sigma_er", "epsilon_r_er", "sigma_et", "epsilon_r_et")
        )
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=destination.parent,
                prefix=f".{destination.name}.",
                delete=False,
            ) as temporary:
                temporary_name = temporary.name
                np.savez_compressed(temporary, **arrays)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_name, destination)
        finally:
            if temporary_name is not None and os.path.exists(temporary_name):
                os.unlink(temporary_name)
        return destination

    @classmethod
    def load(cls, path: str | Path) -> MeshMaterialArtifact:
        """Load and checksum-verify a mesh-native material artifact."""

        source = Path(path)
        required = {
            "metadata",
            "radial_altitudes_m",
            "sigma_er",
            "epsilon_r_er",
            "sigma_et",
            "epsilon_r_et",
        }
        try:
            with np.load(source, allow_pickle=False) as archive:
                missing = required.difference(archive.files)
                if missing:
                    raise DataArtifactError(
                        "material artifact is missing: "
                        + ", ".join(sorted(missing))
                    )
                metadata = json.loads(str(archive["metadata"].item()))
                arrays = {
                    name: np.array(archive[name], copy=True)
                    for name in required.difference({"metadata"})
                }
        except DataArtifactError:
            raise
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
            raise DataArtifactError(
                f"cannot read material artifact {source}: {error}"
            ) from error
        if metadata.get("format") != MESH_MATERIAL_FORMAT:
            raise DataArtifactError("unsupported material artifact format")
        if metadata.get("version") != MESH_MATERIAL_VERSION:
            raise DataArtifactError("unsupported material artifact version")
        checksums = metadata.get("arrays")
        if not isinstance(checksums, dict):
            raise DataArtifactError("material artifact array metadata is invalid")
        for name, values in arrays.items():
            record = checksums.get(name)
            if not isinstance(record, dict):
                raise DataArtifactError(f"material artifact lacks {name} metadata")
            if record.get("shape") != list(values.shape):
                raise DataArtifactError(f"material artifact {name} shape mismatch")
            if record.get("sha256") != array_sha256(values):
                raise DataArtifactError(f"material artifact {name} checksum mismatch")
        try:
            provenance = tuple(
                DatasetProvenance(
                    **{
                        **record,
                        "variables": tuple(
                            VariableProvenance(**variable)
                            for variable in record["variables"]
                        ),
                    }
                )
                for record in metadata["provenance"]
            )
            sampling = metadata["sampling"]
            mesh = metadata["mesh"]
            return cls(
                mesh_vertices_sha256=mesh["vertices_sha256"],
                mesh_faces_sha256=mesh["faces_sha256"],
                radial_altitudes_m=arrays["radial_altitudes_m"],
                earth_radius_m=sampling["earth_radius_m"],
                radial_material_support=sampling["radial_material_support"],
                tangential_material_support=(
                    sampling["tangential_material_support"]
                ),
                horizontal_anomaly_mode=sampling["horizontal_anomaly_mode"],
                sigma_er=arrays["sigma_er"],
                epsilon_r_er=arrays["epsilon_r_er"],
                sigma_et=arrays["sigma_et"],
                epsilon_r_et=arrays["epsilon_r_et"],
                provenance=provenance,
                interpolation=metadata["interpolation"],
                processing_steps=tuple(metadata["processing_steps"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise DataArtifactError(
                f"invalid material artifact metadata: {error}"
            ) from error

    def _metadata(self, *, include_array_checksums: bool) -> dict[str, Any]:
        arrays = {
            name: getattr(self, name)
            for name in (
                "radial_altitudes_m",
                "sigma_er",
                "epsilon_r_er",
                "sigma_et",
                "epsilon_r_et",
            )
        }
        array_metadata = {
            name: {
                "shape": list(values.shape),
                "dtype": "float64",
                **({"sha256": array_sha256(values)} if include_array_checksums else {}),
            }
            for name, values in arrays.items()
        }
        return {
            "format": MESH_MATERIAL_FORMAT,
            "version": MESH_MATERIAL_VERSION,
            "mesh": {
                "vertices_sha256": self.mesh_vertices_sha256,
                "faces_sha256": self.mesh_faces_sha256,
            },
            "sampling": {
                "earth_radius_m": self.earth_radius_m,
                "radial_material_support": self.radial_material_support,
                "tangential_material_support": self.tangential_material_support,
                "horizontal_anomaly_mode": self.horizontal_anomaly_mode,
            },
            "provenance": [asdict(value) for value in self.provenance],
            "interpolation": self.interpolation,
            "processing_steps": list(self.processing_steps),
            "arrays": array_metadata,
        }


def file_sha256(path: str | Path) -> str:
    """Hash a source file without loading it into memory."""

    try:
        with Path(path).open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError as error:
        raise DataArtifactError(f"cannot hash source file {path}: {error}") from error


def array_sha256(values: NDArray[np.generic]) -> str:
    """Hash an array in canonical little-endian C order."""

    array = np.asarray(values)
    if np.issubdtype(array.dtype, np.floating):
        canonical = np.asarray(array, dtype="<f8", order="C")
    elif np.issubdtype(array.dtype, np.integer):
        canonical = np.asarray(array, dtype="<i8", order="C")
    else:
        raise DataArtifactError("only numeric arrays can be checksummed")
    return hashlib.sha256(canonical.tobytes()).hexdigest()


def mesh_vertices_sha256(mesh: GeodesicMesh) -> str:
    """Return the stable coordinate checksum for a mesh."""

    return array_sha256(mesh.vertices)


def mesh_faces_sha256(mesh: GeodesicMesh) -> str:
    """Return the stable topology checksum for a mesh."""

    return array_sha256(mesh.faces)


def _readonly_copy(values: NDArray[np.generic]) -> NDArray[np.float64]:
    result = np.array(values, dtype=np.float64, order="C", copy=True)
    result.setflags(write=False)
    return result
