# Merged latitude–longitude operator control

[한국어 번역](merged-latlon-control.ko.md)

## Hypothesis

The paper's adaptively merged latitude–longitude grid may have substantially
smaller 400 Hz horizontal dispersion than the geodesic grid at equivalent
resolution, explaining part of the remaining phase-velocity gap.

## Method

The first Stage 6 gate implements the smallest dispersion-bearing TM control:
a conservative cell-centered spherical Laplacian. Latitude bands are uniform,
longitude is periodic, and adjacent east–west cells merge by powers of two
whenever `cos(latitude)` crosses successive halves. Nonconforming band
interfaces exchange one conservative finite-volume flux over their exact
shared arc.

The 400 Hz Bannister velocity maps to spherical-harmonic degree 61. Real
sectoral `Y_61^61` is sampled at cell centers, and its Rayleigh value and full
operator residual are measured. Equatorial longitude counts 320, 640, 1280,
and 2560 give 39,830, 159,830, 638,550, and 2,556,310 cells, within 3% of
geodesic subdivisions 6–9.

This is a horizontal operator screen, not the complete paper-style 3-D Maxwell
solver. The 2004 paper specifies adaptive east–west combination and periodic
longitude, but does not publish a complete machine-reconstructable transition
mask. The power-of-two threshold is therefore an explicit untuned assumption.

## Verification controls

- Spherical cell areas close to `4 pi R^2` within `1.11e-16` relative error.
- A constant field is an exact null mode and total discrete flux is conserved.
- The quadratic operator energy is positive.
- The Gershgorin CFL bound is finite and positive.
- Sectoral-harmonic error decreases monotonically under refinement.
- Full harmonic residual falls from `0.001408` to `0.00002054`.

These checks cover conservation, symmetry of the weighted operator, energy
sign, stability bound, and a known spherical eigenvalue benchmark. Attenuation
and lossy 3-D energy evolution are outside this screen and are not reported.

## Results

| Equivalent subdivision | Merged cells | Merged wavenumber error | Geodesic wavenumber error | Merged residual |
|---:|---:|---:|---:|---:|
| 6 | 39,830 | −5.8228% | −4.1833% | 0.001408 |
| 7 | 159,830 | −1.4757% | −1.0612% | 0.0003340 |
| 8 | 638,550 | −0.3702% | −0.2663% | 0.00008243 |
| 9 | 2,556,310 | −0.09262% | −0.06657% extrapolated | 0.00002054 |

The merged-grid convergence order is 1.999. Its error is consistently about
1.39 times the geodesic error at matched cell count. Both discretizations
approach the same continuum eigenvalue, but the reconstructed merged grid does
not approach it faster.

## Decision

This screen does not support grid-family dispersion as the cause of the
non-Bannister phase offset. The merged grid is not substantially better at
equivalent resolution; on the resolved TM branch it is modestly worse.

A full 3-D merged-grid implementation is not justified solely to test the
claim that its horizontal stencil removes the 400 Hz error. Such an
implementation would still be needed to compare attenuation and full-vector
polarization, so Stage 6 is limited rather than a literal paper reproduction.
The present evidence instead prioritizes assumptions shared by both grids:
the radial ionosphere/material profile and its relation to the Bannister guide.

## Next experiment

Do not tune the merge thresholds or transition fluxes to Bannister. If further
work is required, obtain an authoritative transition mask or source code before
building the full 3-D solver. Otherwise, consolidate Stages 1–6 into a cause
matrix separating confirmed numerical effects from shared-model uncertainty.

## Verification

[`artifacts/merged-latlon/`](../../artifacts/merged-latlon/) contains arrays,
CSV values, metadata, and the convergence plot. Run the screen with:

```bash
python -m verification.merged_latlon
```
