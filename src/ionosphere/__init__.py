"""Geodesic finite-difference time-domain Earth-ionosphere model."""

from .materials import EarthIonosphereMaterial, SphericalAnomaly
from .mesh import GeodesicMesh, build_geodesic_mesh
from .solver import GeodesicFDTD, SimulationConfig
from .sources import GaussianCurrent

__all__ = [
    "EarthIonosphereMaterial",
    "GaussianCurrent",
    "GeodesicFDTD",
    "GeodesicMesh",
    "SimulationConfig",
    "SphericalAnomaly",
    "build_geodesic_mesh",
]
