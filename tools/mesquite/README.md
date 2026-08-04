# Mesquite sphere optimizer

This directory builds Sandia's latest archived Mesquite master snapshot and a
small adapter for the project's closed triangular unit-sphere meshes. The
upstream source is pinned to official commit
`7ae51c8e8617c67e63018c8a7effc0f5455f58b4` and verified before extraction.
The source identifies itself as Mesquite 2.99.

Build it outside the Python package with:

```console
python tools/mesquite/build.py
```

The adapter uses `SphericalDomain`, fixes vertices marked by the input VTK
file, and invokes Mesquite's uniform target-size and ideal-shape wrapper. That
wrapper evaluates `TShapeSizeB1`, aggregates it with `PMeanP(1)`, and moves
vertices with `TrustRegion`. It changes vertex coordinates only; connectivity
is retained.

The upstream build has a standalone-CMake bookkeeping bug: it invokes
`TRIBITS_EXCLUDE_FILES` even when Trilinos is absent. The build script defines
that no-op bookkeeping macro in the downloaded build tree. No Mesquite
optimization code is modified.

Mesquite is licensed under LGPL-2.1-or-later; its license remains in the
downloaded source tree. This repository does not redistribute the Mesquite
source or binary.
