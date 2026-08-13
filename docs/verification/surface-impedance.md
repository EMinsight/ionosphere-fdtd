# Surface-impedance lower-boundary control

[한국어 번역](surface-impedance.ko.md)

## Hypothesis

The 5 km bulk-Earth cells may contribute materially to the remaining
attenuation and phase-velocity error. Replacing only that radial lower-boundary
representation with the exact impedance of the same uniform half-space should
move the result toward the Bannister reference if this hypothesis is correct.

## Method

A frequency-domain 1-D conservative TM generalized eigenproblem uses the same
Simpson–Taflove ionosphere profile in every control. The uniform Earth has
conductivity `0.001 S/m` and relative permittivity `10`. For the
`exp(+j omega t)` convention its passive half-space impedance is

```text
Zs(f) = sqrt(j omega mu_0 / (sigma + j omega epsilon_0 epsilon_r)).
```

The impedance control applies `Et = Zs (n x H)` as a Robin flux at sea level.
The primary comparison uses the solver's 5 km radial spacing over all 45 paper
frequencies. Auxiliary 200, 100, and 50 m grids test the continuous limit.
This is a diagnostic control, not a replacement for the published algorithm.

## Controls

1. `bulk`: 100 km of homogeneous Earth, terminated by zero flux.
2. `impedance`: the exact homogeneous half-space Robin condition at sea level.
3. `PEC`: zero flux at sea level, included to expose the total ground-loss
   effect.
4. Bannister attenuation and phase-velocity guides.

No topography is included. The auxiliary eigenproblem isolates radial material
and boundary discretization; it does not reproduce 3-D receiver fitting or
horizontal mesh dispersion.

## Results

The 5 km band mean absolute errors relative to Bannister are:

| Band (Hz) | Model | Attenuation MAE (dB/Mm) | Phase-velocity MAE (fraction of c) |
|---|---|---:|---:|
| 50–200 | Bulk | 0.04001 | 0.002194 |
| 50–200 | Impedance | 0.01228 | 0.005701 |
| 200–375 | Bulk | 0.06429 | 0.004853 |
| 200–375 | Impedance | 0.04826 | 0.007372 |
| 375–500 | Bulk | 0.07381 | 0.006373 |
| 375–500 | Impedance | 0.22264 | 0.008470 |

The impedance boundary improves attenuation in the low and middle bands but
worsens it in the upper band. It worsens phase velocity in every band. Thus it
does not produce the coherent approach to both Bannister observables required
to identify the lower boundary as the main cause.

The bulk/impedance difference collapses under radial refinement:

| Spacing | Maximum attenuation difference at 50/250/500 Hz (dB/Mm) | Maximum phase-velocity difference (fraction of c) |
|---:|---:|---:|
| 5000 m | 0.16216 | 0.004335 |
| 200 m | 0.004690 | 0.00003952 |
| 100 m | 0.001204 | 0.000009707 |
| 50 m | 0.0003057 | 0.000002446 |

The approximately fourfold decrease per halving from 200 to 50 m confirms
second-order convergence of the two formulations toward the same uniform-Earth
solution. The maximum production-grid eigen residual is below `1.2e-8`.

## Decision

Stage 4 does not support bulk-Earth voxelization as the dominant source of the
remaining common phase error. Its 5 km effect is measurable, but the exact
surface impedance does not improve phase velocity, and the two Earth models
share a common refined limit. Prioritize the ionosphere representation and
horizontal numerical dispersion. Keep the impedance boundary as a diagnostic
control only.

## Next experiment

Proceed to the planned narrow-band subdivision-9 measurements at 100, 250, and
400 Hz. Those direct measurements can distinguish the horizontal-resolution
trend from the radial and lower-boundary effects already bounded here.

## Verification

[`artifacts/surface-impedance/`](../../artifacts/surface-impedance/) contains
the arrays, CSV rows, plot, and metadata, including the refinement table. Run
the workflow with:

```bash
python -m verification.surface_impedance --output-dir artifacts/surface-impedance
```
