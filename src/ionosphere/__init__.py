"""Geodesic finite-difference time-domain Earth-ionosphere model."""

from .materials import EarthIonosphereMaterial, SphericalAnomaly
from .mesh import GeodesicMesh, build_geodesic_mesh
from .solver import GeodesicFDTD, SimulationConfig
from .sources import GaussianCurrent
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
    "EarthIonosphereMaterial",
    "GaussianCurrent",
    "GeodesicFDTD",
    "GeodesicMesh",
    "RadialSection",
    "Receiver",
    "ReceiverTraces",
    "SimulationConfig",
    "SphericalAnomaly",
    "animate_surface_field",
    "build_geodesic_mesh",
    "plot_mesh_3d",
    "plot_radial_section",
    "plot_receiver_traces",
    "plot_surface_field",
    "record_receiver_traces",
    "run_live_surface",
    "sample_radial_section",
]
