"""Geodesic finite-difference time-domain Earth-ionosphere model."""

from .backends import (
    ArrayBackend,
    BackendUnavailableError,
    NumPyBackend,
    TorchBackend,
    create_backend,
)
from .checkpoint import CheckpointError
from .materials import (
    EarthIonosphereMaterial,
    LayeredEarthIonosphereMaterial,
    SphericalAnomaly,
)
from .mesh import GeodesicMesh, build_geodesic_mesh
from .solver import GeodesicFDTD, SimulationConfig
from .sources import GaussianCurrent, TangentialGaussianCurrent
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
    "ArrayBackend",
    "BackendUnavailableError",
    "CheckpointError",
    "EarthIonosphereMaterial",
    "LayeredEarthIonosphereMaterial",
    "GaussianCurrent",
    "TangentialGaussianCurrent",
    "GeodesicFDTD",
    "GeodesicMesh",
    "NumPyBackend",
    "RadialSection",
    "Receiver",
    "ReceiverTraces",
    "SimulationConfig",
    "SphericalAnomaly",
    "TorchBackend",
    "animate_surface_field",
    "build_geodesic_mesh",
    "create_backend",
    "plot_mesh_3d",
    "plot_radial_section",
    "plot_receiver_traces",
    "plot_surface_field",
    "record_receiver_traces",
    "run_live_surface",
    "sample_radial_section",
]
