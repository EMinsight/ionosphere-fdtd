# Ionosphere geodesic FDTD

NumPy and PyTorch implementation of a three-dimensional geodesic
finite-difference time-domain (FDTD) model for the Earth-ionosphere waveguide.
It provides spherical primal-dual mesh generation, lossy-material updates, a
vertical current source, and a staggered 3-D solver.

The implementation follows three ideas from the project references:

- Randall et al. (2002): recursively bisect an icosahedron and project the new
  vertices onto the sphere.  The triangular primal mesh has a dual mesh with
  exactly 12 pentagons and otherwise hexagonal cells.
- Taflove and Hagness, Chapter 3: use integral Ampere/Faraday contours and the
  staggered Yee leapfrog update for conductive, nonmagnetic media. The general
  solver integrates conductive decay exponentially; paper reproduction helpers
  retain the references' trapezoidal coefficient.
- Simpson et al. (2006): alternate radial TM planes (`Er`, tangential `Ht`) and
  TE planes (`Hr`, tangential `Et`) and couple them with regular radial Yee
  differences.

The package includes projected surface maps, great-circle radial sections,
receiver traces, interactive 3-D geodesic meshes, and GIF/MP4 animations.

## Installation

Python 3.11 or newer is required.

```bash
uv sync --extra test --extra visualization --extra pytorch
```

All commands below are launched through `uv run`; no virtual-environment path
or separate `pip` invocation is needed.

## Quick run on a MacBook

The default is deliberately small: subdivision level 2 gives 162 surface
cells and 24 radial cells between 100 km below and 100 km above sea level.

```bash
uv run ionosphere --steps 200
```

NumPy on the CPU remains the default.  Select PyTorch explicitly to run on a
Mac GPU through Metal:

```bash
uv run --extra pytorch ionosphere \
  --backend torch --device mps --steps 200
```

For long PyTorch runs, compile the static field update after selecting the
grid, device, and precision.  The first step includes compilation warm-up:

```bash
uv run --extra pytorch ionosphere \
  --backend torch --device mps --torch-compile --steps 20000
```

PyTorch accepts `cpu`, `mps`, `cuda`, `cuda:N`, and the `gpu` alias for CUDA.
`--device auto` chooses CUDA first, then MPS, then CPU.  Automatic precision is
`float64` on NumPy and `float32` on every PyTorch device; override it with
`--dtype float32` or `--dtype float64`.  MPS does not support `float64`, while
PyTorch CPU and CUDA can use explicit `float64` for quantitative comparisons.
For the deliberately small default grid, accelerator dispatch overhead can
outweigh its benefit, so compare NumPy CPU and MPS before choosing a backend for
long runs.

PyTorch CPU uses its process-wide default intra-op thread count unless it is
overridden.  The small level-2 grid is typically faster with one thread, while
larger grids should be benchmarked with several values:

```bash
uv run --extra pytorch ionosphere \
  --backend torch --device cpu --torch-threads 1 --steps 20000
```

Useful variants:

```bash
# Very small smoke run: 42 surface cells
uv run ionosphere --subdivision 1 --radial-cells 16 --steps 100

# The 642-cell surface grid illustrated in the papers
uv run ionosphere --subdivision 3 --radial-cells 40 --steps 1000

# Add the paper-like 1.25 km near-surface radial refinement, a low-conductivity
# Alaska-like lithosphere anomaly, and a 20 Hz carrier.  The expanded 1,200 km
# anomaly radius is only for a resolvable laptop-scale demonstration.
uv run ionosphere --surface-step 1250 --oil-anomaly \
  --anomaly-radius-km 1200 --source-frequency 20 --steps 150000
```

Surface cell counts are `10 * 4**level + 2`:

| Level | Dual cells | Approximate center spacing |
| ---: | ---: | ---: |
| 0 | 12 | 7,054 km |
| 1 | 42 | 3,765 km |
| 2 | 162 | 1,910 km |
| 3 | 642 | 962 km |
| 4 | 2,562 | 482 km |
| 5 | 10,242 | 241 km |

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

The general solver defaults to full spherical radial curls,
`d_radial Et = (1/r) d(r Et)/dr` and likewise for `Ht`. Set
`geometry_mode="thin-shell"` to use the radius-independent radial differences
of the paper implementations; all bundled paper reproduction helpers pin that
compatibility mode explicitly.

For every electric component the default exponential midpoint update uses

```text
q  = sigma*dt/epsilon
Ca = exp(-q)
Cb = dt/epsilon * (1 - exp(-q))/q
```

with the continuous limit `Cb = dt/epsilon` at `q = 0`. This is second-order
for midpoint Maxwell forcing, exactly resolves unforced conductive decay, and
does not retain the sign-alternating stiff mode of trapezoidal integration.
Set `loss_integration="trapezoidal"` when reproducing legacy coefficients.

All surface derivatives use actual primal/dual arc lengths and spherical cell
areas at the relevant radius.  The two radial ends impose zero tangential
electric field (PEC termination); in normal use both boundaries lie inside
strongly conducting Earth/ionosphere regions.  A conservative geometry-aware
Courant estimate selects `dt`, and an explicitly larger user time step is
rejected.

The default radial nodes are uniform.  `--surface-step 1250` adds a 1.25 km
nonuniform subgrid within 5 km of sea level, matching the factor-four radial
refinement used for the paper's shallow oil anomaly while retaining coarse
cells elsewhere. The Python API accepts smoothly graded increasing custom nodes
through `SimulationConfig.radial_altitudes_m`; such grids retain second-order
radial convergence and the discrete energy identity. Abrupt subgridding is a
deliberate first-order transition and must be enabled with
`radial_grid_policy="allow-abrupt"`, as done by the paper-specific factor-four
radar grid.

## Material and source model

`EarthIonosphereMaterial` currently supplies a data-free baseline:

- homogeneous lithosphere: conductivity `1e-3 S/m`, relative permittivity 10;
- atmosphere/ionosphere: relative permittivity 1 and exponential daytime
  conductivity
  `2.5e5 * epsilon0 * exp((height - 74 km) / 6 km)`;
- optional spherical subsurface conductivity anomalies.

These values and anomaly volumes are configurable.  Material sampling is
isolated from the solver so alternative ionospheric and crustal profiles can
be supplied without changing the field-update equations.

`GaussianCurrent` defaults to Gwangju, Republic of Korea (`35.1595° N`,
`126.8526° E`).  It distributes vertical current among the three dual cells of
the containing primal triangle using barycentric weights. The radial coordinate
uses linear cloud-in-cell weights on adjacent staggered `Er` planes. Deposition
is normalized by each radial control length, preserving the configured current
moment `peak_current_a * vertical_element_length_m` under radial refinement; the
default element is 5 km long. Location, amplitude, element length, Gaussian
width/center, and optional carrier frequency are configurable. With a
carrier and no
explicit width, the 1/e half-width is `0.5 / frequency` (25 ms at 20 Hz, close
to the paper's 42.5 ms FWHM envelope).  Use `--source-width` and
`--source-center` to override it.  The CLI warns when an anomaly is smaller than
the selected surface grid.  The same warning covers an anomaly thinner than the
selected radial spacing.

## Python API

```python
from ionosphere_fdtd import GeodesicFDTD, GaussianCurrent, SimulationConfig

simulation = GeodesicFDTD(
    SimulationConfig(subdivision=2, radial_cells=24),
    source=GaussianCurrent(carrier_frequency_hz=20.0),
    backend="torch",
    device="mps",
)
simulation.step(1000)
print(simulation.diagnostics())
```

The public field arrays are backend-native NumPy arrays or PyTorch tensors:

- `er[dual_cell, radial_node]`
- `ht[edge, radial_node]`
- `et[edge, radial_half_node]`
- `hr[triangle, radial_half_node]`

All values use SI units.

Use `simulation.to_numpy(simulation.er)` when analysis, plotting, or export code
requires a host NumPy array.  `simulation.field_value("er", vertex, layer)`
reads an individual value without depending on backend scalar behavior.

## Visualization

Visualization dependencies are optional.  Static maps, sections, and traces
use Matplotlib and Cartopy.  The 3-D topology and animations use PyVista/VTK.
Backend tensors are copied to CPU only when a frame or plot is rendered; the
FDTD update remains on the selected device.

Render a projected `Er` map after 1,200 warm-up steps:

```bash
uv run --extra visualization ionosphere-visualize \
  --subdivision 2 --radial-cells 24 --steps 1200 \
  surface --scale symlog --output surface.png
```

Render a Gwangju-to-antipode distance-height section:

```bash
uv run --extra visualization ionosphere-visualize \
  --subdivision 2 --radial-cells 24 --steps 1200 \
  section --start-latitude 35.1595 --start-longitude 126.8526 \
  --end-latitude -35.1595 --end-longitude -53.1474 --output section.png
```

Inspect the pentagon/hexagon dual mesh over the bundled Earth day-map texture:

```bash
uv run --extra visualization ionosphere-visualize \
  --subdivision 2 --steps 0 mesh --component topology --output mesh.png
```

Watch the solver advance in a responsive, interactive 3-D window:

```bash
uv run --extra visualization ionosphere-visualize \
  --subdivision 2 --radial-cells 24 --steps 0 \
  live --component er --steps-per-frame 10 --fps 20
```

The same live view can advance the field on Apple Silicon MPS:

```bash
uv run --extra pytorch --extra visualization ionosphere-visualize \
  --backend torch --device mps \
  --subdivision 2 --radial-cells 24 --steps 0 \
  live --component er --steps-per-frame 10 --fps 20
```

Drag to rotate, use the mouse wheel to zoom, and press `q` or close the window
to stop.  The bundled PyVista Earth day-map is rendered beneath the geodesic
grid.  Field cells become transparent near zero and increasingly opaque with
amplitude, leaving geography visible beneath propagating waves.  A yellow
marker identifies the exact source location, which defaults to Gwangju.  Use
`--no-earth-texture` for the original field-only globe, `--no-show-edges` to
hide grid lines, or `--field-opacity 0.6` to reveal more of the map.

By default, the symmetric color range follows the current field amplitude.
Add `--color-limit 4` for a fixed scale, or `--frames 1000` to stop calculation
after a known number of display updates while leaving the final field available
for inspection.  Smaller `--steps-per-frame` values improve UI responsiveness;
larger values advance simulation time faster between renders.

Write a fixed-color-scale animation.  Warm-up steps should produce a nonzero
field before the first frame; an explicit `--color-limit` makes runs directly
comparable.

```bash
uv run --extra visualization ionosphere-visualize \
  --subdivision 2 --radial-cells 24 --steps 1200 \
  animate --frames 120 --steps-per-frame 10 --fps 24 \
  --color-limit 4 --output field.mp4
```

Reproduce Taflove and Hagness Figure 3.11 with the source moved from the
original equatorial location to Gwangju.  This command performs the FDTD run
once, records only the sea-level `Er` surface, and renders those same computed
frames as a 1920x1080 YouTube MP4 and a looping 1280x640 social GIF.  It uses
the 1 A Gaussian source and fixed `Er = ±6 µV/m` color range shown by Figures
1.1 and 3.11; only the source location and requested white background differ:

```bash
uv run --extra pytorch --extra visualization ionosphere-figure-3-11 \
  --backend torch --device mps --torch-compile
```

![Taflove Figure 3.11 reproduction with an ELF source in Gwangju](artifacts/taflove/fig-3-11-gwangju.gif)

The default level-7 grid has the paper's 163,842 surface cells and 40 radial
cells, so it is a several-minute calculation on Apple Silicon.  For a quick
rendering check before the paper-resolution run, add `--subdivision 4
--frames 20 --first-step 8000 --steps-per-frame 300`.

Receiver traces are sampled in memory without retaining the full field history:

```bash
uv run --extra visualization ionosphere-visualize \
  --subdivision 2 --steps 40 traces \
  --trace-steps 4000 --sample-every 10 \
  --receiver 35.6762 139.6503 0 \
  --receiver 21.3069 -157.8583 0 --output traces.png
```

The Python API exposes the same operations:

```python
from ionosphere_fdtd import plot_surface_field, sample_radial_section

figure, axes, artist = plot_surface_field(
    simulation, "er", altitude_m=0.0, scale="symlog"
)
section = sample_radial_section(
    simulation, 35.1595, 126.8526, -35.1595, -53.1474
)
```

Surface maps use display-only spherical IDW interpolation onto a regular
longitude/latitude grid before projection.  This avoids false triangles at the
map seam; the solver's geodesic values are not modified.  `Er`/`Hr` maps and
animations always use a symmetric color scale about zero.  The optional
`--coastlines` flag may cause Cartopy to download Natural Earth data on first
use.

## Tests

```bash
uv run --extra test --extra visualization --extra pytorch pytest -q
```

The tests cover icosphere counts, pentagon/hexagon topology, exact
boundary-of-boundary cancellation, spherical area closure, material/anomaly
selection, zero-field invariance, conductive damping, source launching, and
Courant-limit rejection.  Backend tests compare NumPy and PyTorch CPU fields
and exercise MPS or CUDA when the corresponding device is available.
Visualization tests additionally cover coordinate
conversion, projected maps, radial interpolation, receiver sampling, and
PyVista point/cell associations.  The GIF render test is opt-in because CI must
provide a working OpenGL context:

```bash
IONOSPHERE_TEST_PYVISTA_RENDER=1 \
  uv run --extra test --extra visualization --extra pytorch pytest -q
```

## References

1. D. A. Randall et al., “Climate Modeling with Spherical Geodesic Grids,”
   *Computing in Science & Engineering*, 4(5), 32-41, 2002.
2. J. J. Simpson and A. Taflove, “Three-dimensional FDTD modeling of impulsive
   ELF propagation about the entire Earth-sphere,” *IEEE TAP*, 52(2), 443–451,
   2004.
3. J. J. Simpson, R. P. Heikes, and A. Taflove, “FDTD modeling of a novel ELF
   Radar for major oil deposits using a three-dimensional geodesic grid of the
   Earth-ionosphere waveguide,” *IEEE TAP*, 54(6), 1734-1741, 2006.
4. A. Taflove and S. C. Hagness, *Computational Electrodynamics: The
   Finite-Difference Time-Domain Method*, 3rd ed., Chapter 3, 2005.
