# Simpson–Taflove 2004 Reproduction Verification

## Scope

This study evaluates Figures 7 and 8 of J. J. Simpson and A. Taflove,
“Three-dimensional FDTD modeling of impulsive ELF propagation about the entire
Earth-sphere,” *IEEE Transactions on Antennas and Propagation*, 52(2), 443–451,
2004 ([doi:10.1109/TAP.2004.823953](https://doi.org/10.1109/TAP.2004.823953)).

The verification has three separate objectives:

1. test the published qualitative phenomena and trends, including waveform
   morphology, arrival ordering, east–west nonidentity, and the frequency
   dependence of attenuation;
2. build an independently converged, physically defensible model with explicit
   input data and numerical assumptions; and
3. identify the unpublished information needed for exact numerical and
   curve-level reproduction.

Exact curve identity is not an acceptance target with the available sources.
Undisclosed inputs are not tuned solely to improve agreement with the plotted
samples. Exact reproduction should be reconsidered only if the authors' input
volume, final mesh, sampling rules, or raw traces become available.

## Reference and numerical models

The paper uses a Gaussian vertical current source on the equator at
$47^\circ$ W. Radial electric fields are observed $45^\circ$ and $90^\circ$
east and west of the source. The current reproduction uses the paper's
$3\ \mu\mathrm{s}$ time step, 40 nominal radial cells, 35,000 steps, the
published exponential ionosphere profile, and a 1 A source normalization.
The absolute Figure 7 amplitude is not an acceptance quantity because the
paper does not state the source-current amplitude.

ETOPO5 is used as a reproducible, period-appropriate reconstruction of the
paper's NOAA-NGDC “Global Relief CD-ROM” input. Its identity is verified by
SHA-256
`471d3dd534144aa9a6551fe3e76320a06a45dade6fd8d45f7d6ad981d59f93c3`.
The paper does not identify the exact relief product or preprocessing rules,
so ETOPO5 is not represented as the authors' recovered input.

The current material discretization conservatively averages radial material
over dual cells, resolves radial interfaces fractionally, and averages
tangential material over edge diamonds. The source centroid is exactly
2.5 km: its weights are distributed between the 0 and 5 km staggered radial
planes and sum to one. These choices are physically preferable to point
classification at discontinuities, but they need not match the paper's
unpublished voxelization.

The current-version rerun used source revision
`5b02bbc5ac9bd3eca2e97ea35a94b56eab8f66b2`, PyTorch CUDA, `float64`, the
unoptimized polar geodesic mesh, and subdivisions 6 and 7. The level-7 case has
163,842 surface cells, matching the paper's stated cell count but not its
merged latitude–longitude topology. The generated reports append `-dirty`
because the level-6 output directory already existed while level 7 ran; no
source file changed during either run.

The reported attenuation between receivers separated by $d$ is

$$
\alpha_{\mathrm{dB/Mm}}(f)
=\frac{20}{d_{\mathrm{Mm}}}
\log_{10}\!\left|\frac{E_1(f)}{E_2(f)}\right|.
$$

Each trace is truncated at its post-overshoot zero crossing before the DFT.
The diagnostic residuals use the 45 bins from 50.863 to 498.454 Hz implied by
the paper's 32,768-point transform and compare against the published Bannister
daytime guide.

## Results

| Criterion | Current evidence | Status |
|---|---|---|
| Figure 7 main pulse, positive overshoot, and slow tail | Present at all four receivers | **SUPPORTED** |
| Arrival ordering | A/A′ peaks at 7,514/7,703 steps; B/B′ at 14,687/14,648 | **SUPPORTED** |
| East–west nonidentity | Relative RMS is 52.38% at 45° and 144.61% at 90° | **SUPPORTED** |
| Published east–west peak ordering | Reproduced at 45° but reversed at 90° | **PARTIAL** |
| Figure 8 frequency trend | Both paths broadly increase in attenuation with frequency | **SUPPORTED** |
| Figure 8 pointwise agreement | East MAE/max 2.271/3.994; west 0.870/2.469 dB/Mm | Diagnostic mismatch |
| Independent refinement | Phase improves, but path attenuation and asymmetry do not change monotonically | **NOT YET CONVERGED** |
| Exact Figures 7–8 curves | Original inputs and observation rules are unavailable | **INFORMATION-LIMITED** |

The current solver reproduces the principal propagation phenomena: the
impulsive waveform structure, the near-before-far arrival order, material-driven
east–west differences, and increasing loss with frequency. It does not support
the paper's exact relative amplitudes or attenuation curves.

### Current refinement comparison

| Metric | Subdivision 6 | Subdivision 7 | Change |
|---|---:|---:|---:|
| Surface cells | 40,962 | 163,842 | $4\times$ |
| A–B attenuation MAE | 3.356 | 2.271 dB/Mm | −32.3% |
| A–B maximum residual | 5.566 | 3.994 dB/Mm | −28.2% |
| A′–B′ attenuation MAE | 0.708 | 0.870 dB/Mm | +22.9% |
| A′–B′ maximum residual | 3.983 | 2.469 dB/Mm | −38.0% |
| A–B phase-velocity MAE | 0.05477 | 0.03668 $c$ | −33.0% |
| A′–B′ phase-velocity MAE | 0.02615 | 0.01678 $c$ | −35.8% |
| 45° east–west relative RMS | 36.90% | 52.38% | +42.0% |
| 90° east–west relative RMS | 388.33% | 144.61% | −62.8% |

Phase velocity improves consistently under horizontal refinement, and three of
four attenuation error statistics improve. The west-path mean attenuation
error and quarter-path asymmetry worsen, however. Individual s6-to-s7 trace
changes range from 4.13% to 51.01% relative L2, with a 21.05% combined change.
Subdivision 7 is therefore a higher-resolution diagnostic, not a converged
independent prediction.

Complete configuration, metrics, trace hashes, and run times are stored in
`artifacts/verification/simpson-taflove-2004-current.json`. Existing
published-versus-reproduced comparison images under `docs/verification/images`
come from the earlier subdivision-8 point-support experiment and are retained
only as presentation diagnostics; they are not evidence for this rerun.

## Independent accuracy evidence

A separate 20 Hz local-symbol study evaluates the same circumcentric DEC
Laplacian used by the solver at 12 headings per dual cell. This test is
independent of the unavailable paper material volume.

![Directional dispersion anisotropy](images/directional-dispersion-anisotropy.png)

![Phase and group dispersion maps](images/directional-dispersion-errors.png)

| Subdivision | Median cells/wavelength | Median phase error | P95 anisotropy | Median group error |
|---:|---:|---:|---:|---:|
| 2 | 7.80 | 2.161% | 6.365% | 6.149% |
| 3 | 15.84 | 0.516% | 1.665% | 1.484% |
| 4 | 31.72 | 0.129% | 1.175% | 0.371% |
| 5 | 63.47 | 0.032% | 0.313% | 0.093% |
| 6 | 127.39 | 0.008% | 0.080% | 0.023% |

Median phase and group errors converge at approximately second order. For a
smooth synthetic material map, point-versus-finite-volume support disagreement
also decreases monotonically: radial dual-cell disagreement falls from 0.257%
to 0.0046%, and tangential edge-diamond disagreement from 0.167% to 0.0025%
over subdivisions 2–6.

This establishes convergence of the local spatial operator and smooth-material
support, not convergence of the heterogeneous global receiver traces. A final
independent physical model must additionally demonstrate horizontal, radial,
receiver-operator, and precision convergence; stability and conservation; and
documented provenance for every observational material input.

## Information required for exact reproduction

Exact numerical and curve-level reproduction would require an original source
package or equivalent author documentation containing at least:

- the exact NOAA relief product, edition, datum, resampling, shoreline
  classification, and terrain/bathymetry voxelization rules;
- the final merged latitude–longitude mesh coordinates and connectivity,
  including any smoothing or optimization procedure;
- the cellwise three-dimensional conductivity and permittivity realization,
  including every Hermance-derived lithosphere region and local conductor;
- the source-current amplitude and normalization, exact spatial projection,
  staggered-component assignment, waveform samples, and time origin;
- the receiver cells and radial plane, interpolation or averaging operator,
  and any component alignment or sign convention;
- numerical precision, boundary implementation, material-interface averaging,
  and the exact time-step/update ordering; and
- raw receiver traces and the complete truncation, windowing, and plotting
  pipeline used for Figures 7 and 8.

Without these items, multiple physically reasonable implementations satisfy
the article's description while producing different receiver amplitudes and
spectral ratios. Exact curve identity is consequently recorded as
information-limited rather than as an engineering objective for this
repository.

## Reproduction

```bash
python -m verification.simpson_taflove_2004 --help
python -m verification.scientific_accuracy --help
```

The production CLI records complete configuration and checksums with each
trace archive. Published panels are included only for source-attributed
technical comparison.
