"""Physics-led diagnostics for long-running verification simulations."""

from .model import (
    HorizontalRegion,
    PhysicsDiagnosticSampler,
    PhysicsSnapshot,
    record_er_observations_with_diagnostics,
    save_physics_snapshots,
)
from .tensorboard import TensorBoardPhysicsRecorder

__all__ = [
    "PhysicsDiagnosticSampler",
    "PhysicsSnapshot",
    "HorizontalRegion",
    "TensorBoardPhysicsRecorder",
    "record_er_observations_with_diagnostics",
    "save_physics_snapshots",
]
