# Ionosphere FDTD User Manual

This manual explains how to install, configure, run, and inspect the
`ionosphere-fdtd` solver. It documents supported user-facing behavior; the
scientific evidence for correctness remains in `docs/verification/`.

## Contents

1. [Installation](installation.md)
2. [Quick start](quickstart.md)
3. [Command-line reference](command-line-reference.md)
4. [Simulation configuration](simulation.md)
5. [Materials and sources](materials-and-sources.md)
6. [Backends and performance](backends.md)
7. [Visualization and output](visualization-and-output.md)
8. [Troubleshooting](troubleshooting.md)

## Interfaces

The project provides two installed commands:

| Command | Purpose |
|---|---|
| `ionosphere` | Run a simulation and print scalar diagnostics |
| `ionosphere-visualize` | Render maps, sections, meshes, animations, and receiver traces |

The Python API exposes the same solver, mesh, material, source, backend, and
visualization objects through `ionosphere_fdtd`.

## Units and field layout

All public values use SI units. The evolving arrays are backend-native NumPy
arrays or PyTorch tensors:

| Field | Shape association | Time |
|---|---|---|
| `er` | dual cell × radial node | integer electric step |
| `ht` | surface edge × radial node | magnetic half-step |
| `et` | surface edge × radial half-node | integer electric step |
| `hr` | primal triangle × radial half-node | magnetic half-step |

Use `simulation.electric_time_s` for electric fields and
`simulation.magnetic_time_s` for magnetic fields.
