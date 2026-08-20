"""Geodesic finite-difference time-domain Earth-ionosphere model."""

from .adaptive_mesh import (
    AdaptiveMeshValidation,
    SphericalRefinementRegion,
    build_adaptive_geodesic_mesh,
    validate_adaptive_mesh,
)
from .backends import (
    ArrayBackend,
    BackendUnavailableError,
    NumPyBackend,
    TorchBackend,
    create_backend,
)
from .checkpoint import CheckpointError
from .data_artifacts import (
    DataArtifactError,
    DatasetProvenance,
    MeshMaterialArtifact,
    VariableProvenance,
)
from .distributed import (
    DistributedGeodesicFDTD,
    TorchDistributedHaloExchange,
    initialize_torchrun_process_group,
)
from .materials import (
    EarthIonosphereMaterial,
    GriddedMaterial,
    LayeredEarthIonosphereMaterial,
    SphericalAnomaly,
    SpatialEarthIonosphereMaterial,
)
from .mesh import (
    GeodesicMesh,
    build_geodesic_mesh,
    build_geodesic_mesh_from_topology,
)
from .partition import (
    FieldHalo,
    PartitionValidation,
    RankSurfacePartition,
    SurfacePartition,
    partition_surface_mesh,
    validate_surface_partition,
)
from .solver import GeodesicFDTD, SimulationConfig
from .sources import GaussianCurrent, TangentialGaussianCurrent
from .surface_impedance import ConductiveHalfSpaceSurface
from .visualization import (
    RadialSection,
    Receiver,
    ReceiverTraces,
    animate_surface_field,
    plot_mesh_3d,
    plot_radial_section,
    plot_receiver_traces,
    plot_surface_field,
    record_receiver_traces,
    run_live_surface,
    sample_radial_section,
)

__all__ = [
    "AdaptiveMeshValidation",
    "ArrayBackend",
    "BackendUnavailableError",
    "CheckpointError",
    "ConductiveHalfSpaceSurface",
    "DataArtifactError",
    "DatasetProvenance",
    "DistributedGeodesicFDTD",
    "EarthIonosphereMaterial",
    "FieldHalo",
    "GriddedMaterial",
    "LayeredEarthIonosphereMaterial",
    "MeshMaterialArtifact",
    "GaussianCurrent",
    "TangentialGaussianCurrent",
    "GeodesicFDTD",
    "GeodesicMesh",
    "NumPyBackend",
    "PartitionValidation",
    "RadialSection",
    "Receiver",
    "ReceiverTraces",
    "RankSurfacePartition",
    "SimulationConfig",
    "SphericalRefinementRegion",
    "SphericalAnomaly",
    "SurfacePartition",
    "SpatialEarthIonosphereMaterial",
    "TorchBackend",
    "TorchDistributedHaloExchange",
    "VariableProvenance",
    "animate_surface_field",
    "build_geodesic_mesh",
    "build_geodesic_mesh_from_topology",
    "build_adaptive_geodesic_mesh",
    "create_backend",
    "initialize_torchrun_process_group",
    "plot_mesh_3d",
    "partition_surface_mesh",
    "plot_radial_section",
    "plot_receiver_traces",
    "plot_surface_field",
    "record_receiver_traces",
    "run_live_surface",
    "sample_radial_section",
    "validate_adaptive_mesh",
    "validate_surface_partition",
]
