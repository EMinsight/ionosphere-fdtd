# Final Simpson–Taflove 2004 Verification Report

> Final quantitative status: **FAIL**

Verification completed on 2026-08-03 (Asia/Seoul).

## Executive summary

This study tested whether the geodesic FDTD implementation reproduces the
time-domain receiver waveforms in Figure 7 and the frequency-dependent
attenuation in Figure 8 of Simpson and Taflove (2004). The implementation
reproduces the expected negative main pulse followed by an overshoot and slow
tail, and its attenuation and phase-velocity errors decrease with spatial
refinement. It does not, however, satisfy the paper's strict pointwise
attenuation tolerances over the complete 50–500 Hz band.

The authoritative comparison uses Bannister's source equations rather than a
fit read from the published plot. At subdivision 8, the mean absolute
attenuation errors are 0.274 dB/Mm on A–B and 0.275 dB/Mm on A′–B′. Their
maximum absolute errors are 1.218 and 1.225 dB/Mm, respectively, both at
478.109 Hz. The maxima exceed the paper's reported ±0.5 dB/Mm A–B and
±1.0 dB/Mm A′–B′ agreement ranges. The remaining failure is concentrated in
the oscillatory 400–500 Hz residual.

The investigation ruled out floating-point precision, FFT zero-padding, DFT
cutoff selection, source-plane rounding, and missing relief as primary causes.
Uniform-model and azimuthal studies show that spatial dispersion is real and
convergent. At the paper-scale subdivision-7 geodesic grid, directional
anisotropy is already small—no more than 0.295% over the evaluated band—so the
remaining absolute residual also includes isotropic spatial dispersion and
differences in the finite radial and crustal models.

## Scope and acceptance criteria

The target study is:

J. J. Simpson and A. Taflove, “Three-dimensional FDTD modeling of impulsive
ELF propagation about the entire Earth-sphere,” *IEEE Transactions on Antennas
and Propagation*, 52(2), 443–451, 2004,
[doi:10.1109/TAP.2004.823953](https://doi.org/10.1109/TAP.2004.823953).

The verification covers:

- Figure 7 waveform shape and receiver arrival behavior at A, A′, B, and B′;
- Figure 8 attenuation from the A–B and A′–B′ spectral ratios;
- phase velocity and arrival-time convergence in a laterally uniform model;
- sensitivity to precision, FFT length, DFT cutoff, surface relief, crustal
  profiles, source staggering, and horizontal grid direction;
- subdivisions 6–8, from 40,962 to 655,362 surface cells.

The strict quantitative decision is based on the pointwise Figure 8 residual:

| Path | Required agreement over evaluated frequencies |
|---|---:|
| A–B | within ±0.5 dB/Mm |
| A′–B′ | within ±1.0 dB/Mm |

Figure 7 is assessed qualitatively because the paper does not specify the
source-current amplitude. The computed traces use a 1 A normalization;
spectral attenuation ratios do not depend on that amplitude.

## Reference equations and evaluation frequencies

Figure 8's “Previous Results” curve is the daytime model from P. R. Bannister,
“ELF Propagation Update,” *IEEE Journal of Oceanic Engineering*, OE-9(3),
179–188, 1984,
[doi:10.1109/JOE.1984.1145609](https://doi.org/10.1109/JOE.1984.1145609).

The final attenuation reference evaluates Bannister equations (5), (7), and
(8) with `H = 70 km` and `ξ₀ = ξ₁ = 1 / 0.3 km`. This produces approximately
1.5 dB/Mm at 75 Hz and 16.6 dB/Mm at 1000 Hz, as reported by Bannister. The
earlier manually fitted curve, `0.0265 f^0.938`, is retained only as historical
context and is not used for the final decision.

The comparison uses bins 5–49 of the paper-compatible 32,768-point DFT with
`Δt = 3 μs`: 45 fixed frequencies from 50.862630 to 498.453776 Hz. Results from
a 65,536-point zero-padded transform are resampled at these same frequencies.
Phase velocity is compared with Bannister equation (4).

## Simulation configuration

| Item | Value |
|---|---:|
| Radial domain | −100 to +100 km relative to sea level |
| Radial cells | 40 at 5 km spacing |
| Time step | 3.0 μs |
| Production steps | 25,023 |
| Source position | equator, 47° W |
| Source extent | 5 km vertical current element |
| Source centroid | 2.5 km, linearly staggered between 0 and 5 km `Er` planes |
| Gaussian `1/e` full width | `480 Δt` |
| Gaussian center | `960 Δt` |
| A / A′ distance | 45° east / west from the source |
| B / B′ distance | 90° east / west from the source |
| Ionosphere reference height | 70 km |
| Ionosphere scale height | 3.33 km |
| DFT window | adaptive post-overshoot zero crossing |
| Production backend | PyTorch compiled update on CUDA |
| Production precision | float64 |

Surface cell counts are 40,962, 163,842, and 655,362 for subdivisions 6, 7,
and 8. Subdivision 7 matches the paper's 163,842 cells per radial plane.

## Investigation history

### Baseline and precision check

The initial level-7 Apple MPS `float32` run used the earlier 74 km reference
height, 6 km scale height, fixed paper cutoffs, and a Natural Earth land mask.
It reproduced the broad pulse and slow-tail morphology but arrived late and
gave attenuation MAEs of 6.146 dB/Mm on A–B and 5.991 dB/Mm on A′–B′.

An otherwise matched CUDA `float64` run produced 6.148 and 5.992 dB/Mm. The
changes of 0.002 and 0.001 dB/Mm are negligible relative to the residual, so
insufficient floating-point precision was rejected as the cause.

### Ionosphere and DFT-window correction

The earlier ionosphere was too gradual, delaying the main pulse and removing
the positive overshoot and zero crossing needed by the paper's DFT procedure.
Using a 70 km reference height and 3.33 km scale height restored that waveform
structure. Each computed trace is now truncated at its own post-overshoot zero
crossing rather than at a cutoff copied from a waveform with a different
arrival time.

At corrected level 7, the negative peaks moved from steps 8,760 and 18,222 to
approximately 7,513 and 14,459 for A and B. The authoritative fixed-frequency
attenuation MAEs fell from about 6 dB/Mm to 0.387 and 0.399 dB/Mm. This was the
largest improvement in the verification campaign.

### Authoritative attenuation convergence

The following table supersedes attenuation metrics in older automatically
generated reports that used the deprecated plot-fit reference. Every value
below uses Bannister's source equations and the same 45 fixed frequencies.

| Subdivision | Surface cells | A–B MAE / maximum | Maximum frequency | A′–B′ MAE / maximum | Maximum frequency |
|---:|---:|---:|---:|---:|---:|
| 6 | 40,962 | 0.681 / 2.282 dB/Mm | 396.729 Hz | 0.696 / 2.420 dB/Mm | 447.591 Hz |
| 7 | 163,842 | 0.387 / 2.708 dB/Mm | 488.281 Hz | 0.399 / 2.753 dB/Mm | 488.281 Hz |
| 8 | 655,362 | 0.274 / 1.218 dB/Mm | 478.109 Hz | 0.275 / 1.225 dB/Mm | 478.109 Hz |

Subdivision 8 reduces the level-7 mean error by approximately 29% on A–B and
31% on A′–B′. The level-7 A–B residual at 488.281 Hz falls from
+2.708 dB/Mm to +0.731 dB/Mm at level 8. The worst error moves to 478.109 Hz,
where it remains above both strict limits. Refinement therefore improves the
overall result without producing a monotonic reduction at every high-frequency
sample.

The level-8 run used approximately 10.1 GB of peak allocated GPU memory during
compiled preflight and completed 25,023 steps in 3,477.9 seconds on an NVIDIA
GeForce RTX 3060. Its negative peaks were at steps 7,489 for A/A′ and 14,446
for B/B′; adaptive cutoffs were 21,788, 21,722, 22,436, and 22,436 samples.

## Uniform-model phase and arrival convergence

Laterally varying surface materials were removed to separate grid dispersion
from natural east–west asymmetry. Complex spectra were formed as
`A·conj(B)` and `A′·conj(B′)`, unwrapped from DC, and converted to phase
velocity over the additional 45° great-circle distance.

| Subdivision | A–B phase MAE / maximum | A′–B′ phase MAE / maximum | Peak velocity A–B / A′–B′ | Quarter-arc east–west RMS |
|---:|---:|---:|---:|---:|
| 6 | 0.0357 / 0.0941 c | 0.0388 / 0.1034 c | 0.8040 / 0.8025 c | 1.500e-2 |
| 7 | 0.0189 / 0.0504 c | 0.0195 / 0.0521 c | 0.8007 / 0.8003 c | 3.892e-3 |
| 8 | 0.0142 / 0.0276 c | 0.0143 / 0.0280 c | 0.7994 / 0.7993 c | 1.014e-3 |

The observed orders for maximum phase-velocity error are 0.90 and 0.87 on
A–B, and 0.99 and 0.90 on A′–B′, for level 6→7 and 7→8. The quarter-arc
east–west RMS difference converges at orders 1.95 and 1.94. Thus the absolute
high-frequency phase error converges at approximately first order, while
uniform-model directional symmetry is restored at approximately second order.
The mean phase-error order is not yet asymptotic: it drops from about one for
level 6→7 to about 0.4 for level 7→8.

## NOAA ETOPO5 and crustal-profile check

The archived big-endian NOAA-NGDC `ETOPO5.DAT` input contains a
2,160×4,320 cell-centered, five-arc-minute elevation and bathymetry grid. The
loader verifies its 18,662,400-byte size and SHA-256 digest
`471d3dd534144aa9a6551fe3e76320a06a45dade6fd8d45f7d6ad981d59f93c3`,
then bilinearly samples it at each geodesic material point.

Hermance (1995) is the source of the bounded conceptual section reused in the
paper's Figure 6, not a distributable global 3-D conductivity data set. The
implemented material therefore uses the shown 0.3 Ω·m seawater and
representative 500/200/50 Ω·m oceanic and continental depth profiles. Local
≤5/≤10 Ω·m conductors in the figure cannot be reproduced because their
positions and volumes are not specified numerically.

| Level-7 material | Quarter-arc east–west RMS | A / A′ peak steps | A–B / A′–B′ attenuation MAE | A–B / A′–B′ maximum error |
|---|---:|---:|---:|---:|
| Uniform | 0.00389 | 7,514 / 7,510 | 0.412 / 0.427 dB/Mm | 1.838 / 1.890 dB/Mm |
| ETOPO5 + Figure 6 profiles | 0.08220 | 7,546 / 7,589 | 0.387 / 0.590 dB/Mm | 1.747 / 2.020 dB/Mm |

The sampled level-7 relief ranges from −9.69 to +6.30 km and is 28.9% land.
Real relief and separate oceanic/continental profiles split the A/A′ peaks by
43 steps and increase the quarter-arc east–west RMS by a factor of about 21.
This reproduces material-driven directional asymmetry, but it does not bring
the pointwise attenuation residuals inside the paper's ranges.

## Staggered source-placement check

The paper's 5 km vertical source is centered at 2.5 km, halfway between this
solver's 0 and 5 km staggered `Er` planes. The corrected implementation
combines three horizontal barycentric weights with 0.5/0.5 radial
cloud-in-cell weights, preserving both the exact 2,500 m centroid and total
current over six `Er` degrees of freedom.

| Placement | Represented centroid | Trace RMS change | Quarter-arc east–west RMS | A–B / A′–B′ MAE | A–B / A′–B′ maximum |
|---|---:|---:|---:|---:|---:|
| Nearest plane | 0 m | reference | 0.082197 | 0.387016 / 0.589615 | 1.7465 / 2.0198 dB/Mm |
| Linear staggered | 2,500 m | 5.496e-4 | 0.082151 | 0.386878 / 0.589475 | 1.7458 / 2.0160 dB/Mm |

All main-pulse peak steps are unchanged. Correct source placement removes a
real geometric error but has negligible effect on the remaining validation
residual.

## Geodesic-grid directional dispersion

The existing geodesic dual grid was retained. In a laterally uniform model,
phase velocity was measured between matched 45° and 90° receivers along 12
azimuths separated by 30°. The continuum solution is azimuth-independent, so
deviation from the azimuthal mean isolates grid directionality.

| Subdivision | Mean azimuthal spread | Maximum spread | 375–500 Hz mean / maximum spread |
|---:|---:|---:|---:|
| 5 | 4.2417% | 12.0832% | 11.107 / 12.083% |
| 6 | 0.4492% | 1.2344% | 0.992 / 1.234% |
| 7 | 0.0970% | 0.2947% | 0.214 / 0.295% |

The level 6→7 observed orders are 2.21 for mean spread and 2.07 for maximum
spread. At level 7, the mean and maximum spread below 375 Hz are 0.0494% and
0.133%. Reanalysis with one common DFT cutoff for all directions leaves the
level-7 mean spread at 0.0967–0.0973%, ruling out adaptive-window selection as
the source of the convergence. The detailed directional study and retained
artifacts are available in the
[directional-dispersion report](../../artifacts/directional-dispersion/grid-convergence/verification-report.md).

The geodesic and merged latitude–longitude grids cannot have identical
dispersion relations without replacing the horizontal discretization.
Nevertheless, directional error is measurable and decreases at approximately
second order. Because the level-7 maximum directional spread is only 0.295%
while the maximum mean phase-velocity error remains about 0.051 c, horizontal
anisotropy alone cannot explain the full high-frequency mismatch.

## Robustness checks

| Check | Result | Interpretation |
|---|---:|---|
| float32 MPS vs float64 CUDA baseline MAE | ≤0.002 dB/Mm change | Precision is not the cause |
| 32,768 vs 65,536 FFT at fixed frequencies | approximately `1e-12` relative agreement | Zero-padding is not the cause |
| Adaptive cutoff shifted by ±16 samples | approximately 0.01 dB/Mm maximum-error change | Cutoff choice is not the cause |
| Nearest-plane vs staggered source | 5.496e-4 trace-relative RMS | Source rounding is not the cause |
| Uniform symmetry under refinement | approximately second-order convergence | Grid directionality is controlled by resolution |

## Reproduction commands

Run the corrected paper-scale natural-Earth case with CUDA `float64`:

```bash
uv run --extra pytorch --extra visualization ionosphere-verify-2004 \
  --subdivision 7 --steps 25023 \
  --material natural-earth \
  --backend torch --device cuda:0 --dtype float64 --torch-compile \
  --dft-window adaptive \
  --ionosphere-reference-height-km 70 \
  --ionosphere-scale-height-km 3.33 \
  --synchronize-every 1024 \
  --output-dir artifacts/simpson-taflove-2004/level-7-reproduction
```

Run the ETOPO5 material case after placing the verified source file at
`data/ETOPO5.DAT`:

```bash
uv run --extra pytorch --extra visualization ionosphere-verify-2004 \
  --subdivision 7 --steps 25023 \
  --material etopo5 --etopo5-path data/ETOPO5.DAT \
  --backend torch --device cuda:0 --dtype float64 --torch-compile \
  --dft-window adaptive \
  --ionosphere-reference-height-km 70 \
  --ionosphere-scale-height-km 3.33 \
  --synchronize-every 1024 \
  --output-dir artifacts/simpson-taflove-2004/etopo5-level-7-reproduction
```

These commands regenerate per-run figures, compressed traces, metrics, and a
Markdown report. The consolidated scalar results above remain the archival
record; generated Simpson–Taflove artifacts are not retained in the repository.

## Final assessment

The implementation passes structural and qualitative checks:

- it launches and propagates the expected global ELF pulse;
- corrected ionosphere parameters restore the expected pulse sequence;
- attenuation, phase velocity, arrival time, and symmetry all improve under
  refinement;
- ETOPO5 relief and bounded crustal profiles create physically plausible
  east–west asymmetry;
- the source is positioned at its exact staggered centroid with conserved
  current;
- directional grid error is quantified and converges at approximately second
  order.

It fails the final quantitative reproduction criterion because subdivision 8
still has 1.218 and 1.225 dB/Mm maximum attenuation errors, exceeding the
required 0.5 and 1.0 dB/Mm limits. The residual is dominated by 400–500 Hz.
Likely contributors are isotropic high-frequency spatial dispersion, the
finite 5 km radial discretization, unavailable local crustal structures from
the conceptual Hermance section, and the unavoidable difference between the
paper's adaptive merged latitude–longitude grid and this implementation's
geodesic dual grid.

This result must therefore be described as a convergent, qualitatively correct
verification with a failed strict pointwise reproduction—not as a successful
reproduction of Figures 7 and 8.
