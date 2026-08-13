# Narrow-band subdivision-9 measurement

[한국어 번역](narrow-band-subdivision-9.ko.md)

## Hypothesis

The nonzero horizontal-continuum phase-velocity error inferred from
subdivisions 6–8 may be an extrapolation artifact. A direct subdivision-9
measurement should follow the predicted refinement trend if that inference is
credible.

## Method

A raised-cosine-ramped 400 Hz current drives the uniform-Earth validation
model. Five receivers at 30°, 45°, 60°, 75°, and 90° are sampled on each of
four azimuths. After 60 ms, ten complete periods are accumulated online as
`sum Er(t) exp(-j 2 pi f t)`; no receiver histories are stored. Complex
amplitudes are fitted in space after spherical-spreading correction.

Subdivisions 7 and 8 validate the narrow-band method against the existing
broadband multi-receiver results before subdivision 9 is interpreted. The
level-9 time step is `2.9 us`, because the paper's `3 us` step exceeds its
conservative CFL limit of `2.963467 us`. Levels 7–8 retain `3 us`.

Uniform material coefficients are proved horizontally identical and stored as
one broadcast radial row. This exact storage compression leaves the field
update unchanged and reduces level-9 persistent storage enough for the
installed 12 GiB GPU. The run uses CUDA `float32`; this precision and the
1.23% time-step change are limitations relative to the earlier broadband
CUDA `float64` runs.

## Controls

At 400 Hz, level 8 differs from its broadband result by `0.02311 dB/Mm` in
attenuation and `0.0007634 c` in phase velocity. Its complex spatial-regression
RMS is `0.003469`. Level 7 phase velocity agrees within `0.0000028 c`; its
attenuation differs by `0.1833 dB/Mm`, so phase convergence is the more robust
observable for the decision gate.

## Results

| Subdivision | Attenuation (dB/Mm) | Phase velocity (c) | Complex RMS | Runtime | Peak GPU memory |
|---:|---:|---:|---:|---:|---:|
| 7 | 7.32628 | 0.848986 | 0.014967 | 616.6 s | 0.605 GB |
| 8 | 7.15032 | 0.855947 | 0.003469 | 413.1 s | 1.800 GB |
| 9 | 7.10897 | 0.857661 | 0.000990 | 1991.6 s | 7.164 GB |

The observed orders from levels 7–9 are 2.089 for attenuation and 2.022 for
phase velocity. A second-order level-9 prediction formed only from levels 7–8
is `7.10633 dB/Mm` and `0.857687 c`. The direct result differs by only
`0.00264 dB/Mm` and `-0.0000259 c`.

The Bannister values at 400 Hz are `7.05500 dB/Mm` and `0.873132 c`. The
direct level-9 phase residual remains `-0.015471 c`. Independently fitting the
existing broadband level 6–8 errors predicts a level-9 error of `0.016376 c`
and a continuum limit of `0.015910 c`; the direct error is `0.000906 c`
smaller than that prediction but remains clearly nonzero.

## Decision

The direct level-9 point confirms the approximately second-order horizontal
refinement trend and supports the credibility of a nonzero horizontal-
continuum phase offset near 400 Hz. Horizontal resolution explains much of the
coarse-grid error, but further refinement alone is not expected to reach the
Bannister phase velocity.

An expensive full broadband level-9 paper reproduction is not justified by
this result: it would refine a trend whose remaining offset is already much
larger than the measured level-8-to-9 correction. The experiment satisfies the
Stage 5 gate with one prioritized high-band frequency; 100 and 250 Hz were not
run because each additional direct level-9 solve would require another long
GPU allocation and would not resolve the high-band continuum question more
directly than 400 Hz.

## Next experiment

If the verification campaign continues, proceed to the smallest useful Stage
6 merged latitude–longitude control at 400 Hz. It should use the same uniform
Earth, receiver geometry, and lock-in estimator so that grid-family dispersion
is the only intended change.

## Verification

[`artifacts/narrow-band/`](../../artifacts/narrow-band/) contains complex
amplitudes, per-azimuth fits, runtime and memory metadata, the aggregate CSV,
JSON summary, and convergence plot. The full test suite reports `240 passed, 2
skipped`; `git diff --check` passes.
