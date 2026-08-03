# Simpson–Heikes–Taflove 2006 Figures 5–7 Verification

> Final reproduction status: **FAIL**

Verification performed on 2026-08-03 (Asia/Seoul).

## Executive summary

This study tests whether the present three-dimensional geodesic FDTD
implementation can reproduce Figures 5, 6, and 7 of Simpson, Heikes, and
Taflove (2006). The production calculations use PyTorch on NVIDIA CUDA GPUs
with `float64` fields.

Figure 5 is reproduced qualitatively: the quarter-antipode and half-antipode
responses have the published arrival ordering, relative peak amplitude,
overshoot, and slow-tail morphology. Follow-up CUDA `float64` experiments rule
out the paper's plain radial Yee coupling and pentagon orientation as primary
causes; ionosphere scale height changes the residual but does not remove it
without worsening other metrics. Figure 6 follows the published daytime
attenuation trend in mean, but it fails the paper's pointwise ±0.5 dB/Mm
statement near the upper end of the 50–500 Hz comparison window. The east and
west mean absolute errors are 0.387 and 0.589 dB/Mm, while their maximum
absolute errors are 1.746 and 2.016 dB/Mm.

Figure 7 reproduces only the direction of the claimed sensitivity. Its
`ΔHtan` median is −35.75 dB and 99.70% of nonsingular samples are below
−25 dB, but `ΔHr` has a +100.30 dB median rather than a curve peaking near
+20 dB. The computed 136.03 dB median radial-over-tangential advantage is not
the paper's approximate 45 dB. The failure comes from a nearly zero reference
`Hr`, not an unusually large radial scattered field. Consequently the three
figures are not reproduced as a complete quantitative set.

## Target paper and source record

The target is J. J. Simpson, R. P. Heikes, and A. Taflove, “FDTD Modeling of a
Novel ELF Radar for Major Oil Deposits Using a Three-Dimensional Geodesic Grid
of the Earth-Ionosphere Waveguide,” *IEEE Transactions on Antennas and
Propagation*, 54(6), 1734–1741, 2006,
[doi:10.1109/TAP.2006.875504](https://doi.org/10.1109/TAP.2006.875504).

The supplied eight-page PDF, `/home/kwchun/simpson.pdf`, has SHA-256 digest
`b33632d3eb8c004c69f8d5100792966583206cb62374df298651ce9560f31952`.
The published panels used in the comparisons below are cropped from pages 5,
6, and 7 of that supplied file. They are © 2006 IEEE and are included only as
source-attributed technical excerpts.

## Acceptance criteria

The paper supplies different levels of quantitative detail for the three
figures, so the criteria are separated:

| Figure | Criterion |
|---|---|
| 5 | Qualitative waveform morphology, arrival order, and near/far amplitude ratio; absolute amplitude is arbitrary in the paper. |
| 6 | Both calculated paths remain within approximately ±0.5 dB/Mm of the Bannister daytime result over 50–500 Hz. |
| 7 | `ΔHtan` is more than 25 dB below its reference at almost every nonsingular time, `ΔHr` reaches approximately +20 dB, and radial sensing offers about 45 dB more sensitivity. |

The Figure 7 body text and caption are internally inconsistent about
normalization. The body says the difference is divided by the peak Model-A
field, but the caption attributes the plotted spikes to zero crossings of the
reference waveform. A peak-normalized difference cannot have those poles.
The verification therefore follows the caption and the actual plot:

```text
ΔH(t) = |H_B(t) - H_A(t)| / |H_A(t)|
```

Values within `1e-6` of the reference peak are excluded from scalar summaries,
while the rendered curve retains the approach to the zero-crossing spikes.

## Numerical model

### Figures 5 and 6

| Item | Implemented value |
|---|---:|
| Surface grid | subdivision 7, 163,842 geodesic dual cells |
| Radial domain | −100 to +100 km |
| Radial cells | 40 at 5 km |
| Time step | 3.0 μs |
| Recorded steps / time | 40,000 / 0.120 s |
| Source | 5 km vertical current at 0° N, 47° W |
| Gaussian `1/e` full width / center | `480 Δt` / `960 Δt` |
| Receivers | A/A′ at ±45° and B/B′ at ±90° along the equator |
| Surface data | NOAA-NGDC ETOPO5, bilinear sampling |
| Ionosphere | 70 km reference height, 3.33 km scale height |
| Backend | compiled PyTorch, CUDA, float64 |
| Wall time | 937.6 s |

The source is barycentrically distributed in the horizontal plane and linearly
staggered between the 0 and 5 km `Er` planes, preserving its exact 2.5 km
centroid and total current.

### Figure 7

| Item | Implemented value |
|---|---:|
| Surface grid | subdivision 7, 163,842 geodesic dual cells |
| Nominal radial grid | 5 km from −100 to +100 km |
| Near-surface lithosphere subgrid | 1.25 km from −5 to 0 km |
| Actual radial cells | 43 |
| Stable time step | 2.083689715 μs at Courant factor 1.0 |
| Simulated time / steps | 0.1616 s / 77,542 |
| Transmitter | Clam Lake, Wisconsin, 46.5° N, 90.9° W |
| Ground lines | 22.5 km north–south and east–west, 300 A each |
| Pulse | 20 Hz carrier, 42.5 ms Gaussian-envelope FWHM |
| Oil-field center | 69° N, 156° W |
| Oil-field footprint | circular equivalent of 4,800 km², radius 39.088 km |
| Oil-field depth | 1.25 km thick at median depth 1.2 km |
| Conductivity contrast | 0.1 times surrounding strata |
| Backend | compiled PyTorch, two CUDA GPUs, float64 |
| Production revision | `1e3d939` |
| Wall time | 1,832.2 s reference / 2,249.0 s anomaly |

The ground-line source is projected onto all three oriented primal edges of
the containing face. Each contribution is scaled by `L/Δl`, which preserves
the specified `I·L` current moment on a line shorter than one surface edge.
Those three edges are 55.59, 64.78, and 55.59 km long, so the 22.5 km source
is genuinely subcell rather than silently expanded to an entire edge.
The surface `Hr` sample is linearly interpolated between its two staggered
radial planes. East and north `Htan` are reconstructed by a local least-squares
inverse of the surrounding oriented dual-edge samples; a fixed principal
reference polarization is then used for the signed tangential waveform.

The paper gives a Canadian Shield conductivity of `2.4e-4 S/m`, but does not
publish its exact grid mask. Both models therefore use the same documented
2,500 km cap approximation centered over Canada. This choice cancels partly in
the reference/anomaly difference but remains a reproducibility limitation.

## Figure 5: temporal response

![Published and reproduced Figure 5](images/simpson-taflove-2006-fig-5-comparison.png)

The reproduced averaged A/A′ pulse peaks at 22.710 ms and the averaged B/B′
pulse at 43.482 ms. The far/near normalized peak ratio is 0.34385, compared
with approximately 0.39 by visual reading of the published panel. The computed
waveforms also show the negative overshoot and subsequent slow tail.

The exact east and west quarter-path traces do not coincide: their relative
RMS difference is 8.22%, reflecting the ETOPO5 land/ocean asymmetry. The two
half-path traces coincide to floating-point precision because they meet at the
same antipodal observation point in this grid representation.

| Figure 5 criterion | Published behavior | Reproduction | Result |
|---|---|---|---:|
| Arrival ordering | Quarter-antipode response precedes half-antipode response | Near/far peaks at 22.710/43.482 ms | **PASS** |
| Main-pulse timing | Peaks occur at the corresponding locations in the published panel | Both peaks visually align with the published traces | **PASS** |
| Waveform morphology | Negative main pulse, opposite-sign overshoot, and slow tail | All three features are present | **PASS** |
| East/west asymmetry | East and west quarter-path traces are similar but not identical | Quarter-path relative RMS difference is 8.22% | **PASS** |
| Far/near peak ratio | Approximately 0.39 by visual reading | 0.34385, approximately 12% lower | **FAIL** |
| Far slow-tail magnitude at 0.12 s | Approximately 0.10 by visual reading | Approximately 0.045 in the archived reproduction plot | **FAIL** |
| Overall qualitative reproduction | Ordering and characteristic waveform shape | Required qualitative features are reproduced | **PASS** |
| Exact plot reproduction | Relative peak and tail magnitudes also agree | Peak ratio and far-tail magnitude remain too small | **FAIL** |

Figure 5 is therefore a **qualitative pass**. It is not assigned an absolute
amplitude error because the paper labels the vertical scale as arbitrary and
does not state the current amplitude for this validation pulse. The exact-plot
failure is based only on normalized relative quantities, not absolute field
strength.

### Follow-up diagnosis of the Figure 5 mismatch

#### Geographic locator correction and material isolation

The original production run contained a geographic face-selection defect. A
direction and its antipode both satisfied the unsigned spherical-triangle
test, and the first candidate was selected. The requested source and receiver
longitudes were therefore represented as follows:

| Location | Requested longitude | Previously represented longitude |
|---|---:|---:|
| Source | −47° | +133° |
| A | −2° | +178° |
| A′ | −92° | +88° |
| B | +43° | −137° |
| B′ | −137° | −137° |

The common 180° shift preserved the source-to-A/A′/B distances and concealed
the error in arrival times, while B and B′ collapsed onto one observation.
The face candidate is now selected by its positive alignment with the requested
direction. Regression tests cover the paper source and all four receivers and
require the antipodal B/B′ observations to use distinct faces. Consequently,
all Figure 5–6 production metrics recorded before this correction require a
new level-7 calculation.

Before repeating that expensive run, three corrected-location subdivision-5
cases isolated the material contribution. Each used 40,000 steps, CUDA
`float64`, and one common normalization over the four individual records.

| Material | B / B′ peak | B / B′ tail at 0.12 s | Quarter / half east-west RMS |
|---|---:|---:|---:|
| Uniform lithosphere | 0.37691 / 0.37855 | 0.07200 / 0.07194 | 5.2% / 1.9% |
| Fixed-depth Natural Earth land/ocean | 0.38240 / 0.38539 | 0.07481 / 0.07466 | 5.2% / 1.9% |
| ETOPO5 relief and representative rock profiles | 0.11120 / 0.39237 | 0.02238 / 0.06673 | 30.8% / 235.9% |

The uniform and fixed-depth land/ocean models recover the published far-peak
scale of approximately 0.39 and keep east/west paths similar. Adding ETOPO5
and the representative 500/200/50 Ω·m profiles strongly suppresses the eastern
B path while leaving B′ near the published peak. This identifies the current
relief/lithosphere discretization, rather than the core FDTD update, as the
dominant source of the corrected-location path asymmetry. The exact
Hermance-derived cellwise conductivity used by the paper remains unavailable.

#### Radial coupling is the paper's intentional thin-shell approximation

A review of Taflove and Hagness, Chapter 3, Section 3.6.8, and the supplied
2006 paper changes the interpretation of the radial update. Chapter 3 derives
the Yee scheme from integral Ampere and Faraday contours. Opposite contour
segments have the same length on a Cartesian Yee cell, so their circulation
reduces to a plain field difference divided by the cell increment. Simpson,
Heikes, and Taflove explicitly say that their alternating geodesic TE and TM
planes are coupled in the radial direction by “regular Yee-type updates.”
Their equations (5)–(7) and (10)–(12) then use
`Δt/(μ0 Δr) [E(k+1/2) - E(k-1/2)]` and
`Δt/(ε0 Δr) [H(k+1) - H(k)]`, without radius-weighted fields.

The implementation uses those same plain radial differences. A fully spherical
curl over a thick shell would instead contain `(1/r) ∂(rEt)/∂r` and
`(1/r) ∂(rHt)/∂r`, but adding them would depart from the target algorithm. The
paper treats the 200-km domain as a stack of locally prismatic Yee cells around
an Earth radius of approximately 6,371 km. This is an intentional thin-shell
approximation, not an accidental omission in the reproduction.

As a numerical check, a paired subdivision-5 ETOPO5 calculation replaced only
the radial differences with their radius-weighted counterparts. Both runs used
CUDA `float64` and 40,000 steps. The normalized four-trace RMS change was only
`3.39e-6`; the common absolute peak changed by 0.053%, peak times were
unchanged, and the far/near ratio changed from 0.386870128 to 0.386869895.
Radial metric weighting therefore cannot explain the Figure 5 mismatch even if
the continuum spherical form is preferred for another application.

#### Rigid polar-orientation A/B test

The paper places one pentagonal cell at each geographic pole, whereas the
native mesh orientation does not. A selectable `polar` orientation was added
which rigidly rotates the existing icosahedron before subdivision. It changes
neither topology nor metric terms: sorted primal-edge lengths and dual-cell
areas agree with the native orientation to floating-point precision.

One paper-scale polar run used the same 163,842 cells, ETOPO5 model, 3.33-km
ionosphere scale height, CUDA `float64`, and 40,000 steps as the production
case. It required 922.4 seconds.

| Level-7 result | Native orientation | Polar orientation |
|---|---:|---:|
| Near peak time | 22.710 ms | 22.713 ms |
| Far peak time | 43.482 ms | 43.479 ms |
| Far/near peak ratio | 0.34385 | 0.34599 |
| Quarter-path east/west relative RMS | 8.215% | 8.054% |
| East/west attenuation MAE | 0.387 / 0.589 dB/Mm | 0.399 / 0.572 dB/Mm |
| East/west attenuation maximum error | 1.746 / 2.016 dB/Mm | 1.954 / 1.930 dB/Mm |

The polar run has normalized near/far tails of 0.02823/0.05150 at 0.12 s.
The far/near ratio changes by only 0.6%, and neither waveform timing nor
attenuation improves consistently. Incorrect placement of the pentagons is
therefore rejected as the primary cause. The unavailable mesh optimization
and exact axial orientation can still change individual sampled material
values, but a rigid paper-like orientation does not resolve Figure 5.

#### Conductivity-profile sensitivity

Subdivision-5 screening varied one parameter at a time around the production
ETOPO5 model. All cases used CUDA `float64` and 40,000 steps. Rock-conductive
and rock-resistive multiply all three 500/200/50 Ω·m rock resistivities by 0.5
and 2.0, respectively.

| Variant | Near / far peak time | Far/near peak ratio | Near / far tail at 0.12 s |
|---|---:|---:|---:|
| 70 km, 3.33 km baseline | 23.535 / 44.421 ms | 0.38687 | 0.03267 / 0.05962 |
| Reference height 68 km | 23.673 / 44.724 ms | 0.38300 | 0.03240 / 0.05684 |
| Reference height 72 km | 23.409 / 44.142 ms | 0.39102 | 0.03301 / 0.06269 |
| Scale height 3.00 km | 23.178 / 43.593 ms | 0.40291 | 0.03315 / 0.06965 |
| Scale height 3.67 km | 23.931 / 45.354 ms | 0.37231 | 0.03305 / 0.05459 |
| Rock-conductive | 23.535 / 44.418 ms | 0.38659 | 0.03273 / 0.05982 |
| Rock-resistive | 23.538 / 44.421 ms | 0.38743 | 0.03259 / 0.05928 |

The factor-of-four rock-resistivity span changes the far/near ratio by less
than 0.001, so the representative lithosphere values are not the dominant
control at this resolution. Ionosphere scale height is much more influential.
The most promising 3.00-km case was therefore repeated at level 7. It moved the
far/near ratio from 0.34385 to 0.35361 and produced a 0.05959 far tail at
0.12 s, but it also advanced the near/far peaks to 22.362/42.606 ms. It still
does not reach the published visual estimates of approximately 0.39 for the
peak ratio and 0.10 for the far tail.

Moreover, the level-7 3.00-km case increased the east/west maximum attenuation
errors to 2.346/2.838 dB/Mm, versus 1.746/2.016 dB/Mm at 3.33 km. Its west-path
mean error improved, but the pointwise benchmark became worse. The standard
3.33-km Bannister value is therefore retained rather than tuning the
ionosphere to one panel. The remaining Figure 5 difference is most consistent
with the paper's unavailable optimized mesh coordinates, exact conductivity
discretization, and material samples, rather than an error in the FDTD radial
coupling.

## Figure 6: daytime attenuation

![Published and reproduced Figure 6](images/simpson-taflove-2006-fig-6-comparison.png)

Each receiver record is truncated at its post-overshoot zero crossing, as
specified by the paper. The adaptive cutoffs are 22,922 samples for A, 23,287
for A′, and 24,081 for both B and B′. A 32,768-point DFT provides 45 fixed bins
from 50.862630 to 498.453776 Hz. The reference line evaluates Bannister's
daytime attenuation equations with the same 70 km height and 3.33 km scale
height rather than fitting pixels from the plot.

| Path | Mean absolute error | Maximum absolute error | Worst frequency | ±0.5 dB/Mm result |
|---|---:|---:|---:|---:|
| A–B, east | 0.387 dB/Mm | 1.746 dB/Mm | 498.454 Hz | **FAIL** |
| A′–B′, west | 0.589 dB/Mm | 2.016 dB/Mm | 447.591 Hz | **FAIL** |

The reproduced curves follow the published trend over most of the valid band,
but the pointwise criterion fails. At 396.729 Hz the east result differs from
the reference by only +0.013 dB/Mm; at 498.454 Hz it is −1.746 dB/Mm. The west
curve reaches its +2.016 dB/Mm maximum residual at 447.591 Hz. This oscillatory
upper-band error is consistent with the high-frequency spatial-dispersion
residual documented in the separate 2004 verification.

## Figure 7: oil-field radar response

![Published and reproduced Figure 7](images/simpson-taflove-2006-fig-7-comparison.png)

The paper-scale result is mixed. The tangential curve is approximately flat at
−36 dB away from its reference zero crossings. Its median is −35.749 dB, and
99.698% of nonsingular samples are below −25 dB. This satisfies the paper's
stated tangential suppression criterion.

The radial curve does not reproduce the published scale or morphology. It is
above the plot's +30 dB limit for almost the entire window, with a +100.304 dB
median and +118.548 dB 95th percentile. The median radial-over-tangential
advantage is 136.028 dB, not approximately 45 dB.

| Metric | Paper behavior | Reproduction | Result |
|---|---:|---:|---:|
| Median pointwise `ΔHtan` | mostly below −25 dB | −35.749 dB | **PASS** |
| Fraction of `ΔHtan < −25 dB` | almost every time | 99.698% | **PASS** |
| Pointwise `ΔHr` scale | reaches about +20 dB | +100.304 dB median | **FAIL** |
| Median `ΔHr−ΔHtan` | about 45 dB | 136.028 dB | **FAIL** |

The absolute fields identify the mechanism:

| Quantity | Peak magnitude |
|---|---:|
| Reference `Htan` | `3.1393e-12 A/m` |
| Oil-model `Htan` | `3.0889e-12 A/m` |
| Absolute `Htan` difference | `5.0390e-14 A/m` |
| Reference `Hr` | `1.0635e-20 A/m` |
| Oil-model `Hr` | `1.7823e-15 A/m` |
| Absolute `Hr` difference | `1.7823e-15 A/m` |

The tangential scattered field is actually 28.02 dB stronger than the radial
scattered field. The apparent radial advantage is caused by the reference
`Hr` being almost seven orders of magnitude smaller than the radial scattered
field. Applying the body text's peak normalization instead of the caption's
pointwise normalization gives −35.890 dB for `ΔHtan` and +104.485 dB for
`ΔHr`; it therefore fails the published +20 dB scale under either reading.

Figure 7 is a **quantitative fail**, although it qualitatively confirms that a
buried conductivity anomaly can generate a radial magnetic component while
only weakly perturbing the dominant tangential reference field.

## Failure analysis and corrective work

The initial implementation could not perform Figure 7 as stated. The following
issues were found and corrected before the production result was accepted:

1. The solver could inject only radial current and record only `Er`. A
   tangential ground-line source and backend-native `Hr`/signed-`Htan` recorder
   were added. Recording stays on the CUDA device until the run completes.
2. The ETOPO5 layered lithosphere could not carry a local anomaly. The common
   spherical-volume anomaly mechanism was extended to that material without
   replacing its relief, ocean, or depth profiles. A subsequent material audit
   found that a broad lateral cap could also multiply seawater; both the Shield
   and oil anomalies are now restricted to background conductivity at or below
   `0.01 S/m`, leaving water layers unchanged.
3. The 1.25 km subgrid reduced the conservative time step from the 3 μs used by
   Figures 5–6. A paired level-5 CUDA float64 experiment showed that Courant
   factors 0.4 and 1.0 agree in field maxima to about `1e-8` relative and in
   perturbation metrics within 0.001 dB; the stable 1.0 setting reduces the
   production run from 193,759 to 77,542 steps.
4. The first tangential source projection preserved direction but not the
   subcell line moment. Scaling each edge by the line-length/edge-length ratio
   corrected the absolute field. A second paired level-5 run showed that the
   normalized sensitivity ordering was unchanged, ruling out source amplitude
   as the cause of the coarse-grid discrepancy.
5. A second source-deposition hypothesis snapped each north–south/east–west
   line to its nearest geodesic edge instead of projecting it over three edges.
   At level 5 it produced a reference `Hr` peak of `1.06e-19 A/m` and a
   peak-normalized radial perturbation of +99.35 dB, the same pathological
   scale as the projected source. Edge cancellation was therefore rejected as
   the primary cause and the direction-preserving projection was retained.
6. At subdivision 5 the 39.1 km-radius oil body contains no electric vertex and
   is represented only on nearby edges. That deliberately coarse diagnostic
   produced a qualitatively correct but grossly exaggerated radial advantage.
   The final result therefore uses the paper-scale subdivision 7, where two
   electric vertices and five electric edges lie inside the circular footprint.

At level 7 the two selected dual cells have a combined area of 7,013.6 km²,
larger than the disk's geometric 4,800 km² because material sampling is binary
at geodesic electric-field points. The five selected edge samples and both
selected vertices are over land in ETOPO5 (elevations 250–450 m). This removes
water contamination but leaves a disclosed horizontal voxelization error.

The final-code resolution study confirms that this is not a smooth convergent
observable:

| Subdivision | Cells | Peak-normalized `ΔHtan` | Peak-normalized `ΔHr` | Reference `Hr` peak |
|---:|---:|---:|---:|---:|
| 5 | 10,242 | −64.103 dB | +95.341 dB | `1.679e-19 A/m` |
| 6 | 40,962 | −49.932 dB | +125.269 dB | `2.081e-20 A/m` |
| 7 | 163,842 | −35.890 dB | +104.485 dB | `1.064e-20 A/m` |

The radial value moves by +29.93 dB and then −20.78 dB under successive
refinement, while the tangential perturbation grows monotonically. The oil
disk is represented by a different small set of binary electric samples at
each level, so no Richardson-style convergence order can be assigned. This
rules out interpreting the level-7 mismatch as a simple remaining truncation
error that could safely be extrapolated to the paper's curve.

The remaining Figure 6 error cannot be removed by float64 precision, DFT
zero-padding, source staggering, or ETOPO5 relief. Those cases were already
isolated in the 2004 campaign. Horizontal refinement reduces the mean error,
but the present geodesic dual grid must be retained, and the paper's exact
Hermance-derived three-dimensional conductivity realization is not published.
The final high-frequency mismatch is therefore reported rather than tuned
away.

## Reproduction commands

Figures 5 and 6 use the exact ETOPO5 level-7 trace configuration:

```bash
.venv/bin/python -m ionosphere_fdtd.simpson_taflove_2004_cli \
  --subdivision 7 --mesh-orientation native \
  --steps 40000 --material etopo5 \
  --etopo5-path data/ETOPO5.DAT --backend torch --device cuda:1 \
  --dtype float64 --dft-window adaptive \
  --ionosphere-reference-height-km 70 \
  --ionosphere-scale-height-km 3.33 --torch-compile \
  --synchronize-every 1024 \
  --output-dir artifacts/simpson-taflove-2006/figure-5-level-7-float64-cuda

.venv/bin/python -m ionosphere_fdtd.simpson_taflove_2006_cli \
  figures-5-6 \
  --traces artifacts/simpson-taflove-2006/figure-5-level-7-float64-cuda/simpson-taflove-2004-traces.npz \
  --output-dir artifacts/simpson-taflove-2006/figures-5-6
```

The polar-orientation diagnostic changes `--mesh-orientation native` to
`--mesh-orientation polar`. The production-resolution ionosphere sensitivity
case keeps the native orientation and changes only
`--ionosphere-scale-height-km 3.33` to `3.00`.

The paired Figure 7 runs were:

```bash
.venv/bin/python -m ionosphere_fdtd.simpson_taflove_2006_cli radar-run \
  --case reference --subdivision 7 --material etopo5 \
  --etopo5-path data/ETOPO5.DAT --backend torch --device cuda:1 \
  --dtype float64 --torch-compile --courant 1.0 \
  --source-edge-assignment projected --synchronize-every 1024 \
  --output artifacts/simpson-taflove-2006/level-7-courant-1-float64-cuda/reference.npz

.venv/bin/python -m ionosphere_fdtd.simpson_taflove_2006_cli radar-run \
  --case anomaly --subdivision 7 --material etopo5 \
  --etopo5-path data/ETOPO5.DAT --backend torch --device cuda:0 \
  --dtype float64 --torch-compile --courant 1.0 \
  --source-edge-assignment projected --synchronize-every 1024 \
  --output artifacts/simpson-taflove-2006/level-7-courant-1-float64-cuda/anomaly.npz

.venv/bin/python -m ionosphere_fdtd.simpson_taflove_2006_cli analyze-radar \
  --reference artifacts/simpson-taflove-2006/level-7-courant-1-float64-cuda/reference.npz \
  --anomaly artifacts/simpson-taflove-2006/level-7-courant-1-float64-cuda/anomaly.npz \
  --figure artifacts/simpson-taflove-2006/level-7-courant-1-float64-cuda/figure-7.png
```

## Reproducibility limits

- NOAA ETOPO5 relief is exact to the archived file and checksum already
  documented in the 2004 report, but the paper's complete three-dimensional
  Hermance conductivity mapping is not available.
- The exact Canadian Shield boundary and the oil-field footprint shape are not
  published. The implementation uses a disclosed cap for the former and a
  circular equal-area footprint for the latter. Point sampling maps that disk
  to 7,013.6 km² of dual-cell area at level 7; no undocumented conductivity
  retuning is used to force an effective 4,800 km² voxel area.
- The paper uses an optimized geodesic grid. This project retains its existing
  recursively subdivided geodesic dual grid, as required. The production result
  is not tuned by changing topology or orientation; a disclosed rigid-rotation
  diagnostic tests the paper-like polar placement without changing any metric.
- Figure 7 does not define source phase, Gaussian center time, or a formal
  error norm. The simulation begins three Gaussian `1/e` half-widths before the
  envelope center, and its displayed time is referenced to that center.
- The contradictory Figure 7 normalization statements prevent a unique
  literal reproduction. The selected pointwise definition is the only one
  consistent with the published spikes.

## Final conclusion

The current implementation can qualitatively reproduce Figure 5 and the broad
Figure 6 attenuation trend. It cannot meet Figure 6's pointwise ±0.5 dB/Mm
claim, and it cannot reproduce Figure 7's +20 dB radial perturbation or roughly
45 dB sensitivity advantage. The final status is therefore **FAIL**.

The corrective work did produce reusable, tested capabilities: physically
scaled horizontal ground-line sources, CUDA-native radial/tangential magnetic
recording, buried anomalies in the ETOPO5 layered material, protected water
layers, and a reproducible Figure 5–7 analysis CLI. Precision, time-step
stability, source moment, nearest-edge deposition, radial metric weighting, and
rigid polar orientation were tested and rejected as explanations for the
remaining discrepancy.

The strongest remaining causes are inputs that cannot be reconstructed from
the paper: its optimized cell locations, exact three-dimensional lithosphere
conductivity realization, Canadian Shield mask, horizontal subcell treatment
of the 4,800 km² body, and exact ground-line deposition. With the required
current geodesic dual grid retained, forcing the published Figure 7 values
would require undocumented material or normalization tuning and would not be a
valid verification.
