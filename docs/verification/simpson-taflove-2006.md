# Simpson–Heikes–Taflove 2006 Reproduction Verification

## Scope

This study evaluates Figures 5–7 of J. J. Simpson, R. P. Heikes, and A. Taflove,
“FDTD Modeling of a Novel ELF Radar for Major Oil Deposits Using a
Three-Dimensional Geodesic Grid of the Earth-Ionosphere Waveguide,” *IEEE
Transactions on Antennas and Propagation*, 54(6), 1734–1741, 2006
([doi:10.1109/TAP.2006.875504](https://doi.org/10.1109/TAP.2006.875504)).

Figures 5–6 reuse the global propagation geometry of the 2004 study. Figure 7
models a 20 Hz tangential transmitter near Clam Lake and compares magnetic
fields in Alaska with and without a $4800\ \mathrm{km}^2$ subsurface oil body.

This verification has three deliberately separate objectives:

1. test whether the implementation reproduces the published qualitative
   phenomena and trends, including waveform timing, path ordering, weak
   tangential oil perturbations, and enhanced radial sensitivity;
2. build an independently converged, physically defensible model whose
   assumptions and input data are explicit; and
3. identify the unpublished information required for exact numerical and
   curve-level reproduction.

Exact agreement with the published samples is not an acceptance target with
the currently available sources. Undisclosed inputs are not tuned or inferred
solely to force curve agreement. The exact-reproduction question is reopened
only if the original input volume, mesh, sampling rules, or source package
becomes available.

## Numerical model

The paper-target baseline uses a subdivision-7 geodesic surface
(163,842 cells), 40 nominal radial cells, $5\ \mathrm{km}$ radial spacing,
PyTorch CUDA, and `float64`. The oil anomaly reduces conductivity by a factor
of 0.1 over a $1250\ \mathrm{m}$ vertical interval centered near
$1200\ \mathrm{m}$ depth. Horizontal anomaly support is conservative for both
TM dual cells and TE edge diamonds.

For Figure 7, normalized magnetic perturbation is evaluated as

$$
\Delta H_{tan}(t)=20\log_{10}
\left(
\frac{\|\mathbf H_{tan}^{\mathrm{oil}}(t)-
\mathbf H_{tan}^{\mathrm{ref}}(t)\|_2}
{\max_t \|\mathbf H_{tan}^{\mathrm{ref}}(t)\|_2}
\right),
$$

and analogously with absolute scalar differences for $H_r$. This
coordinate-invariant vector-difference definition is used because the
dissertation does not define a scalar direction for $H_{tan}$. Fixed east,
north, reference-principal-axis, and difference-of-vector-magnitudes
interpretations are also evaluated as sensitivities.

The dissertation body supports this peak-reference denominator, but the
Figure 26 caption attributes spikes to zero crossings of the reference
waveform, which instead implies an instantaneous denominator. Both
interpretations are therefore calculated below; neither is silently selected
to improve agreement.

## Results

![Figure 5 comparison](images/simpson-taflove-2006-fig-5-comparison.png)

![Figure 6 comparison](images/simpson-taflove-2006-fig-6-comparison.png)

![Figure 7 comparison](images/simpson-taflove-2006-fig-7-comparison.png)

The numerical comparisons below are retained as diagnostic evidence rather
than as a requirement to tune the independent model to the published pixels.

| Criterion | Reproduced result | Status |
|---|---:|---|
| Figure 5 morphology and arrival ordering | Reproduced | **SUPPORTED** |
| Figure 5 relative amplitudes/path similarity | Far peaks 0.31141/0.35571; path RMS 37.41%/18.47% | Diagnostic mismatch |
| Figure 6 east-path attenuation | MAE 0.921, maximum 3.020 dB/Mm | Diagnostic mismatch |
| Figure 6 west-path attenuation | MAE 0.284, maximum 2.125 dB/Mm | Diagnostic mismatch |
| Figure 7 weak tangential perturbation | Median $-43.253$ dB | **SUPPORTED** |
| Figure 7 fraction below $-25$ dB | 92.469% | Diagnostic mismatch |
| Figure 7 enhanced radial sensitivity | Positive published-scale crossings occur, but the value is mesh-sensitive | **PROVISIONAL** |
| Independent spatial convergence | Background $H_{tan}$ is stable; perturbation and $H_r$ are not | **NOT YET CONVERGED** |
| Exact Figures 5–7 curves | Original inputs and observation rules are unavailable | **INFORMATION-LIMITED** |

The implementation reproduces timing, qualitative waveform structure, and the
reported ordering in which the oil-induced tangential response is weak while
the radial response is much more sensitive. The radial claim remains
provisional because its magnitude has not converged. The model also does not
reproduce all published relative amplitudes or high-frequency attenuation.
These mismatches bound the present evidence; they are not targets for empirical
curve fitting.

## Dissertation supplement

The 2007 Simpson dissertation, *Three-Dimensional FDTD Modeling of Impulsive
Electromagnetic Propagation in the Global Earth-Ionosphere Waveguide*, was
reviewed as an additional primary source (PDF SHA-256
`b3a56bace95f6a59068d27830b25a698ca12d7498885799f5ff53e1cc0f4be45`).
Chapter 5 adds information that is absent from, or conflicts with, the 2006
article:

- the Figure 7 material grid is stated as approximately
  $63\times63\times5\ \mathrm{km}$;
- both daytime and nighttime Bannister exponential ionosphere profiles are
  stated to be present, whereas the article says that Figure 7 reuses the
  daytime profile from its validation section;
- dissertation Figure 15 supplies lithosphere resistivity classes, including
  $0.3\ \Omega\,\mathrm{m}$ seawater, a shallow continental class of
  $\leq10\ \Omega\,\mathrm{m}$, a resistive continental class of
  $\geq5000\ \Omega\,\mathrm{m}$, oceanic classes of $\leq5$, $\leq50$,
  $\geq500$, and $\leq200\ \Omega\,\mathrm{m}$, and a deep class of
  $\leq50\ \Omega\,\mathrm{m}$;
- the Laurentian Plateau is described as extending north from the Great Lakes
  to the Arctic and including much of Canada and Greenland; and
- the adjacent ionospheric-radar application states that dawn occurs at
  $0^\circ$ longitude and gives approximate effective reflection heights of
  48 km by day and 76 km by night.

The oil-field section does not explicitly say that it uses the adjacent
application's dawn orientation. The dissertation also does not provide a
cellwise Figure 15 volume, an exact Shield mask, the isolated conductor's
geographic location, or the horizontal shape of the hypothetical oil body.
The extracted information therefore defines a traceable hypothesis rather
than a unique recovered input volume.

### Dissertation-informed experiment

The dissertation-informed material uses separate continental and oceanic
profiles at the actual E-field sampling directions. Because Figure 15 is a
schematic with inequality-valued classes, its class limits are used as
representative values and visual boundaries are snapped to the nominal 5 km
radial grid. The continental hypothesis is 10 $\Omega\,\mathrm{m}$ from
0--5 km, 5000 $\Omega\,\mathrm{m}$ from 5--45 km, and
50 $\Omega\,\mathrm{m}$ below 45 km. The oceanic rock hypothesis is 5, 50,
500, 200, and 50 $\Omega\,\mathrm{m}$ over boundaries at 5, 10, 20, and
45 km below sea level. The geographically unspecified isolated conductor in
Figure 15 is omitted.

The ionosphere uses the established daytime profile ($H=70\ \mathrm{km}$,
scale $3.333\ \mathrm{km}$), the cited Bannister ambient-night representative
($H=92.8\ \mathrm{km}$, scale $2.47\ \mathrm{km}$), and a subsolar point at
$0^\circ$ N, $90^\circ$ E so that dawn occurs at $0^\circ$ longitude. The
profiles yield $3.011\times10^{-9}$ and $2.461\times10^{-9}\ \mathrm{S/m}$
at the dissertation's approximate day and night reflection heights,
respectively, providing a consistent independent check.

ETOPO5, the paper source, the $4800\ \mathrm{km}^2$ conservative oil support,
the $0.1$ conductivity factor, `float64`, and a Courant factor of 1 were held
fixed. This initial sweep used the former thin-shell, unoptimized mesh and
reference-principal-axis $H_{tan}$ implementation. The table reports the
caption-implied pointwise medians and the body-defined peak-normalized maxima
from the same traces.

| Subdivision | Reference $H_r$ peak | Pointwise median $\Delta H_{tan}$ | Pointwise median $\Delta H_r$ | Peak-normalized max $\Delta H_{tan}$ | Peak-normalized max $\Delta H_r$ |
|---:|---:|---:|---:|---:|---:|
| 4 | $1.249\times10^{-13}$ A/m | $-95.728$ dB | $-26.213$ dB | $-102.206$ dB | $-29.423$ dB |
| 5 | $7.403\times10^{-17}$ A/m | $-80.390$ dB | $+44.799$ dB | $-86.400$ dB | $+45.792$ dB |
| 6 | $3.186\times10^{-17}$ A/m | $-60.724$ dB | $+86.660$ dB | $-64.143$ dB | $+91.504$ dB |

The tangential perturbation remains below $-25$ dB for 99.774--99.975% of
valid pointwise samples, but the radial result does not converge. Its
peak-normalized maximum moves by about 121 dB from subdivision 4 to 6, crossing
the published $+20$ dB scale without approaching a stable value. The reference
$H_r$ peak also collapses by more than three orders of magnitude from
subdivision 4 to 5, while the anomaly-induced peak grows by about 83 times from
subdivision 5 to 6. A subdivision-4 control with the former $0^\circ$ subsolar
longitude changes the radial maximum by only 6.30 dB, so the dawn orientation
does not explain the nonconvergence.

This initial sweep does not justify subdivision 7. The possible effects of its
thin-shell geometry, unoptimized mesh, and inferred $H_{tan}$ direction are
isolated below.

### Geometry, mesh, and tangential-field review

The dissertation's update equations retain radial-coordinate-dependent edge
lengths and areas, so `full-spherical` is the closer implementation. It also
states that the geodesic cells were optimized to improve Laplace and wave
propagation accuracy, although it does not publish the final coordinates or
optimization parameters. The review therefore uses the repository's pinned
Sandia Mesquite build with a uniform shape-size objective, trust-region mover,
200 iterations, and the two polar vertices fixed. These are reproducible
hypothesis parameters, not recovered author inputs.

Mesquite improves mesh quality at every tested level. The primal-edge
coefficient of variation falls from about 0.0650 to 0.0431, 0.0426, and 0.0423
at subdivisions 4--6. The RMS adjacent-dual-area mismatch falls from
0.0455/0.0335/0.0241 to 0.0245/0.0133/0.0070, respectively.

The subdivision-4 factorial comparison uses the coordinate-invariant
vector-difference definition of $H_{tan}$ and the dissertation-body peak
normalization:

| Geometry | Mesh | Maximum $\Delta H_{tan}$ | Maximum $\Delta H_r$ |
|---|---|---:|---:|
| Thin shell | Unoptimized | $-101.303$ dB | $-29.423$ dB |
| Full spherical | Unoptimized | $-101.303$ dB | $-29.423$ dB |
| Thin shell | Mesquite | $-101.367$ dB | $-32.590$ dB |
| Full spherical | Mesquite | $-101.367$ dB | $-32.590$ dB |

Full-spherical curvature changes these peak ratios by less than 0.00003 dB at
subdivision 4. Mesh optimization has the larger effect, changing the radial
peak by about 3.17 dB, but it does not approach the published $+20$ dB result.

The combined full-spherical, Mesquite-optimized convergence sweep gives:

| Subdivision | Reference $H_r$ peak | Pointwise median $\Delta H_{tan}$ | Pointwise median $\Delta H_r$ | Peak-normalized max $\Delta H_{tan}$ | Peak-normalized max $\Delta H_r$ |
|---:|---:|---:|---:|---:|---:|
| 4 | $2.423\times10^{-13}$ A/m | $-98.526$ dB | $-32.233$ dB | $-101.367$ dB | $-32.590$ dB |
| 5 | $2.587\times10^{-14}$ A/m | $-83.148$ dB | $+0.676$ dB | $-85.984$ dB | $+1.811$ dB |
| 6 | $1.007\times10^{-16}$ A/m | $-60.823$ dB | $+58.659$ dB | $-61.487$ dB | $+66.485$ dB |

Optimization reduces the subdivision-4-to-6 radial-peak swing from about
121 dB to 99 dB, but the result still crosses the published scale without
converging. The reference $H_r$ peak still collapses by more than three orders
of magnitude. Across the five explicit $H_{tan}$ definitions, the
peak-normalized maximum ranges from $-112.241$ to $-101.141$ dB at subdivision
4, $-96.154$ to $-85.853$ dB at subdivision 5, and $-65.829$ to $-58.590$ dB
at subdivision 6. Every convention remains below $-25$ dB, and none can alter
$H_r$.

The review therefore changes the preferred implementation to full-spherical
geometry and vector-difference $H_{tan}$, and establishes Mesquite coordinates
as the appropriate production-mesh input. It does not establish converged
Figure 7 scaling, and subdivision 7 remains scientifically unjustified for a
final independent result. Complete settings, mesh checksums, quality metrics,
and sensitivity results are stored in
`artifacts/verification/simpson-taflove-2006-thesis.json`.

### Adaptive-mesh screening

The conforming composite mesh was rerun with a subdivision-7 global base and
1-degree refinement cores around the transmitter and oil receiver. The coarse
mesh targets subdivision 9 (329,520 faces, $dt=7.67037\times10^{-7}$ s); the
fine mesh targets subdivision 10 (335,574 faces,
$dt=6.00656\times10^{-7}$ s). All FDTD updates were retained while magnetic
observations were recorded every 32 steps. Independent target levels occupied
the two local GPUs concurrently because the shallow 44-layer problem measured
slower when split across NCCL ranks.

This is a `float32` screening run, not final precision evidence. A declared 5%
relative-L2 threshold was applied to all fields over the common 0--84.981 ms
half-step window:

| s9 to s10 relative-L2 change | Reference | Oil anomaly | Oil-induced perturbation |
|---|---:|---:|---:|
| $H_r$ | 109.989% | 246.394% | 197.213% |
| $H_{tan}$ vector | 0.102% | 0.104% | 7.975% |

The tangential background field is stable, but the tangential perturbation
misses the threshold and every radial quantity is strongly nonconvergent. At
s10, peak-normalized perturbations are $-55.544$ dB for $H_{tan}$ and
$+7.501$ dB for $H_r$; pointwise medians are $-53.688$ and $+8.992$ dB,
respectively. These values are not promoted into the main Figure 7 acceptance
table because the s9--s10 radial response fails the convergence screen.

The adaptive result therefore confirms that the earlier Figure 7 mismatch
cannot yet be treated as a resolved uniform-grid limitation. A full s9--s10
`float64` production rerun remains deferred; smaller precision controls and
radial and receiver-sampling convergence checks should precede it. Complete
metrics, mesh checksums, time steps, and run revisions are stored in
`artifacts/verification/simpson-taflove-2006-adaptive-float32/convergence.json`.

## Accuracy research status

The independent directional-dispersion and material-support convergence study
is reported in the 2004 reproduction because Figures 5–6 reuse that propagation
model. At 20 Hz, median phase and group errors converge at approximately second
order over subdivisions 2–6, while the P95 directional anisotropy falls from
6.365% to 0.080%. Smooth-property point-versus-support differences also
decrease monotonically for both radial dual cells and tangential edge diamonds.

For Figure 7, the material API directly exercises the dissertation's day/night
statement and the verification package contains an explicitly qualified Figure
15 piecewise hypothesis. The radar workflow now exposes full-spherical versus
thin-shell geometry, deterministic or externally optimized meshes, and five
explicit $H_{tan}$ definitions. It can also import three-dimensional
conductivity and permittivity volumes from a canonical NPZ grid. No cellwise
Hermance volume or equivalent observation product is present, so the schematic
hypothesis is not represented as a recovered global map and the radial scaling
remains provisional. A future observational run must record dataset identity,
units, coordinate datum, interpolation policy, and checksum alongside the trace
archive.

## Final verification position

### Qualitative phenomena and trends

The available evidence supports the propagation timing and waveform ordering
of Figures 5–6 and the Figure 7 trend that the tangential oil perturbation is
weak relative to the reference field. The implementation also produces radial
perturbations that can exceed the radial reference field, consistent with the
paper's proposed sensitivity mechanism. Because the radial waveform is not yet
mesh-converged, this last result is qualitative evidence rather than a
validated magnitude or detection-performance prediction.

### Independent physical model

Further work is directed toward an independently reproducible model, not a
pixel match. Its acceptance requires documented material datasets and receiver
operators, stable results under horizontal and radial refinement, a precision
check for the small radial signal, and conservation and stability tests. The
paper's disclosed 1.25 km near-surface radial spacing remains a benchmark case;
finer radial grids are convergence controls rather than attempts to reconstruct
an unpublished author grid.

The present adaptive result does not satisfy this standard: background
$H_{tan}$ changes by about 0.1%, but the tangential perturbation changes by
7.975% and all recorded $H_r$ quantities change by more than 100% from the s9
to s10 local refinement. Accordingly, no quantitative oil-detection claim is
accepted from these traces.

### Information required for exact reproduction

Exact numerical and curve-level reproduction would require an original source
package or equivalent author-supplied documentation containing at least:

- the final geodesic vertex coordinates and exact mesh-optimization software,
  objective, constraints, and stopping criteria;
- the cellwise three-dimensional conductivity and permittivity volume,
  including the Hermance-derived lithosphere mapping, Laurentian Plateau mask,
  isolated conductor, shoreline classification, and topography/bathymetry
  rasterization rules;
- the exact oil-body horizontal footprint, terrain-relative placement, radial
  subgrid transition, and component-specific subcell material assignment;
- the day/night ionosphere assignment and solar or terminator orientation used
  for the oil-field run;
- the transmitter-to-grid projection, source altitude, current-density
  normalization, waveform phase, and time origin;
- the observation triangle or cells, radial sampling plane, interpolation or
  averaging rule for $H_r$, scalar definition of $H_{tan}$, output cadence, and
  normalization implementation; and
- the numerical precision, time step, boundary treatment, raw reference and
  anomaly traces, and any post-processing applied before plotting.

Without these items, many distinct implementations are consistent with the
published description but produce different small $H_r$ reference signals and
therefore very different decibel ratios. Exact curve identity is consequently
recorded as information-limited rather than as an engineering objective for
this repository.

## Reproduction

```bash
python -m verification.simpson_taflove_2004 --help
python -m verification.simpson_taflove_2006 --help
python -m verification.simpson_taflove_2006.adaptive_run --help
python -m verification.scientific_accuracy --help
```

Each production archive includes configuration, checksums, and run signatures.
Published panels are included only for technical comparison.
