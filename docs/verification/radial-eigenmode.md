# Independent radial eigenmode benchmark

[한국어 번역](radial-eigenmode.ko.md)

## Objective

This Stage 2 control measures the error introduced when the continuous
exponential ionosphere is represented by cell-centered radial staircases. It
does not use a 3-D FDTD result as its reference.

## Independent formulation

For the stratified isotropic atmosphere, the horizontal magnetic field of the
TM mode satisfies

```text
d/dz[(1/epsilon_c) dH/dz] + k0^2 H = beta^2 H/epsilon_c
```

where `epsilon_c = 1 - j sigma/(omega epsilon_0)`. A conservative 100 m
finite-volume discretization converts this equation into a complex generalized
eigenproblem. The calculation selects the fundamental mode with physical
phase velocity and positive attenuation. Zero normal flux is imposed at sea
level and 100 km, matching the closed radial extent of the 3-D uniform control.
This isolates the ionosphere profile; it does not claim to reproduce finite
ground impedance.

The continuous reference samples

```text
sigma(z) / epsilon_0 = 2.5e5 exp[(z - 70 km) / 3.3333333333333335 km]
```

on the 100 m analysis grid. The 5.0, 2.5, 1.25, and 0.625 km models hold the
cell-center conductivity constant over each radial cell while retaining the
same 100 m eigenproblem grid. This separates material-profile staircase error
from eigenproblem resolution.

## Results

Mean absolute errors relative to the continuous reference are:

| Frequency band | Radial spacing | Attenuation MAE | Phase-velocity MAE |
|---|---:|---:|---:|
| 50–200 Hz | 5.0 km | 0.003379 dB/Mm | 0.001409 c |
| 50–200 Hz | 2.5 km | 0.001770 dB/Mm | 0.000269 c |
| 50–200 Hz | 1.25 km | 0.001026 dB/Mm | 0.0000339 c |
| 50–200 Hz | 0.625 km | 0.000549 dB/Mm | 0.00000835 c |
| 200–375 Hz | 5.0 km | 0.010159 dB/Mm | 0.001815 c |
| 200–375 Hz | 2.5 km | 0.001731 dB/Mm | 0.000351 c |
| 200–375 Hz | 1.25 km | 0.001629 dB/Mm | 0.0000612 c |
| 200–375 Hz | 0.625 km | 0.001008 dB/Mm | 0.00000243 c |
| 375–500 Hz | 5.0 km | 0.043581 dB/Mm | 0.001868 c |
| 375–500 Hz | 2.5 km | 0.001765 dB/Mm | 0.000405 c |
| 375–500 Hz | 1.25 km | 0.001287 dB/Mm | 0.0000783 c |
| 375–500 Hz | 0.625 km | 0.001184 dB/Mm | 0.00000781 c |

The 5 km phase-velocity error is smooth and stays near 0.0013–0.0019 c. Its
attenuation error grows toward the upper band and reaches approximately
−0.056 dB/Mm at 498.453776 Hz.

## Reference-grid convergence

The continuous calculation was repeated at representative low, middle, and
high frequencies with 200, 100, and 50 m analysis spacing. The 100-to-50 m
phase-velocity changes are 0.0000800 c at 50.862630 Hz, 0.0000571 c at
254.313151 Hz, and 0.0000467 c at 498.453776 Hz. The corresponding attenuation
changes are 0.000568, 0.002196, and 0.003870 dB/Mm. These changes are below the
5 km staircase errors used in the decision gate. The maximum archived complex
eigen residual is `1.66e-8`.

## Decision gate

The Stage 1 subdivision-8 multi-receiver phase-velocity MAE was 0.01075 c,
0.01464 c, and 0.01783 c in the same three bands. The independent 5 km radial
staircase produces only 0.00141 c, 0.00182 c, and 0.00187 c. It explains roughly
13%, 12%, and 10% of those band errors, respectively, and cannot explain their
full magnitude or high-frequency growth.

For attenuation, the 5 km radial error is also smaller than the Stage 1 error:
0.00338 versus 0.07356 dB/Mm, 0.01016 versus 0.05693 dB/Mm, and 0.04358 versus
0.20931 dB/Mm. Radial profile discretization contributes measurably in the
upper band but is not the dominant remaining cause.

Stage 2 therefore does not identify 5 km radial ionosphere discretization as a
major explanation of the 3-D residual. Priority moves to Stage 3, direct
spectral analysis of the horizontal discrete operator.

## Archived outputs and verification

`artifacts/radial-eigenmode/` contains the complete NPZ, CSV, plot, and metadata
record. The full test suite reports `232 passed, 2 skipped`; `git diff --check`
passes. The plot is an RGBA `2160 x 1440` image.
