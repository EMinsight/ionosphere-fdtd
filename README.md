# Ionosphere geodesic FDTD

NumPy implementation of a three-dimensional geodesic finite-difference
time-domain (FDTD) model for the Earth-ionosphere waveguide.  It replaces the
incomplete `cpu.cc` prototype with a working spherical mesh, lossy-material
updates, a vertical current source, and a staggered 3-D solver.

The implementation follows three ideas from the project references:

- Randall et al. (2002): recursively bisect an icosahedron and project the new
  vertices onto the sphere.  The triangular primal mesh has a dual mesh with
  exactly 12 pentagons and otherwise hexagonal cells.
- Taflove and Hagness, Chapter 3: use integral Ampere/Faraday contours and the
  staggered Yee leapfrog update, including the trapezoidal loss coefficient
  for conductive, nonmagnetic media.
- Simpson et al. (2006): alternate radial TM planes (`Er`, tangential `Ht`) and
  TE planes (`Hr`, tangential `Et`) and couple them with regular radial Yee
  differences.

Visualization and field-data persistence are intentionally not implemented
yet.  The CLI reports only scalar diagnostics.

## Installation

Python 3.11 or newer is required.

```bash
uv sync --extra test
```

Alternatively:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
```

## Quick run on a MacBook

The default is deliberately small: subdivision level 2 gives 162 surface
cells and 24 radial cells between 100 km below and 100 km above sea level.

```bash
.venv/bin/python -m ionosphere --steps 200
```

Useful variants:

```bash
# Very small smoke run: 42 surface cells
.venv/bin/python -m ionosphere --subdivision 1 --radial-cells 16 --steps 100

# The 642-cell surface grid illustrated in the papers
.venv/bin/python -m ionosphere --subdivision 3 --radial-cells 40 --steps 1000

# Add the paper-like 1.25 km near-surface radial refinement, a low-conductivity
# Alaska-like lithosphere anomaly, and a 20 Hz carrier.  The expanded 1,200 km
# anomaly radius is only for a resolvable laptop-scale demonstration.
.venv/bin/python -m ionosphere --surface-step 1250 --oil-anomaly \
  --anomaly-radius-km 1200 --source-frequency 20 --steps 150000
```

Surface cell counts are `10 * 4**level + 2`:

| Level | Dual cells | Approximate center spacing |
| ---: | ---: | ---: |
| 0 | 12 | 3,717 km |
| 1 | 42 | 3,717 km |
| 2 | 162 | 1,910 km |
| 3 | 642 | 962 km |
| 4 | 2,562 | 482 km |
| 5 | 10,242 | 241 km |

The paper's validation grid used 163,842 cells per radial plane and 40 radial
cells.  That resolution is intentionally not the default for a laptop.  The
small defaults exercise the complete algorithm but are not sufficient for a
quantitatively converged 50-500 Hz propagation study.

## Numerical layout

Let the oriented primal edge point from vertex `tail` to `head`.  Its positive
dual direction points from the right adjacent triangle to the left triangle.
The solver applies these vectorized integral updates:

```text
Ht += dt / mu0 * (d_surface Er - d_radial Et)
Hr -= dt / mu0 * curl_surface Et
Er  = Ca * Er + Cb * (curl_surface Ht - Jr)
Et  = Ca * Et + Cb * (d_dual Hr - d_radial Ht)
```

For every electric component,

```text
Ca = (1 - sigma*dt/(2*epsilon)) / (1 + sigma*dt/(2*epsilon))
Cb = dt/epsilon / (1 + sigma*dt/(2*epsilon))
```

All surface derivatives use actual primal/dual arc lengths and spherical cell
areas at the relevant radius.  The two radial ends impose zero tangential
electric field (PEC termination); in normal use both boundaries lie inside
strongly conducting Earth/ionosphere regions.  A conservative geometry-aware
Courant estimate selects `dt`, and an explicitly larger user time step is
rejected.

The default radial nodes are uniform.  `--surface-step 1250` adds a 1.25 km
nonuniform subgrid within 5 km of sea level, matching the factor-four radial
refinement used for the paper's shallow oil anomaly while retaining coarse
cells elsewhere.  The Python API also accepts any strictly increasing custom
node sequence through `SimulationConfig.radial_altitudes_m`.

## Material and source model

`EarthIonosphereMaterial` currently supplies a data-free baseline:

- homogeneous lithosphere: conductivity `1e-3 S/m`, relative permittivity 10;
- atmosphere/ionosphere: relative permittivity 1 and exponential daytime
  conductivity
  `2.5e5 * epsilon0 * exp((height - 74 km) / 6 km)`;
- optional spherical subsurface conductivity anomalies.

These values and anomaly volumes are configurable.  They isolate data choices
from the solver so measured ionospheric profiles, bathymetry, topography,
oceans, or gridded crustal conductivity can be added later.

`GaussianCurrent` injects a vertical current into the closest dual cell and
radial plane.  Its location, amplitude, Gaussian width/center, and optional
carrier frequency are configurable.  With a carrier and no explicit width,
the 1/e half-width is `0.5 / frequency` (25 ms at 20 Hz, close to the paper's
42.5 ms FWHM envelope).  Use `--source-width` and `--source-center` to override
it.  The CLI warns when an anomaly is smaller than the selected surface grid.
The same warning covers an anomaly thinner than the selected radial spacing.

## Python API

```python
from ionosphere import GeodesicFDTD, GaussianCurrent, SimulationConfig

simulation = GeodesicFDTD(
    SimulationConfig(subdivision=2, radial_cells=24),
    source=GaussianCurrent(carrier_frequency_hz=20.0),
)
simulation.step(1000)
print(simulation.diagnostics())
```

The public field arrays are:

- `er[dual_cell, radial_node]`
- `ht[edge, radial_node]`
- `et[edge, radial_half_node]`
- `hr[triangle, radial_half_node]`

All values use SI units.

## Tests

```bash
.venv/bin/pytest -q
```

The tests cover icosphere counts, pentagon/hexagon topology, exact
boundary-of-boundary cancellation, spherical area closure, material/anomaly
selection, zero-field invariance, conductive damping, source launching, and
Courant-limit rejection.

## Current scientific limits

This repository now contains a complete runnable 3-D algorithm, but it does
not claim reproduction of the paper's validation curves at the laptop default
resolution.  Such reproduction additionally requires the paper-scale grid,
NOAA topography/bathymetry, the referenced Hermance crust profile, the exact
Bannister ionosphere profile, long observation records, and DFT/windowing.
Those are data ingestion, validation, visualization, and persistence tasks
reserved for the next stage.

## References

1. D. A. Randall et al., “Climate Modeling with Spherical Geodesic Grids,”
   *Computing in Science & Engineering*, 4(5), 32-41, 2002.
2. J. J. Simpson, R. P. Heikes, and A. Taflove, “FDTD modeling of a novel ELF
   Radar for major oil deposits using a three-dimensional geodesic grid of the
   Earth-ionosphere waveguide,” *IEEE TAP*, 54(6), 1734-1741, 2006.
3. A. Taflove and S. C. Hagness, *Computational Electrodynamics: The
   Finite-Difference Time-Domain Method*, 3rd ed., Chapter 3, 2005.
