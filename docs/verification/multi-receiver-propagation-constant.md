# Multi-receiver propagation-constant verification

[한국어 번역](multi-receiver-propagation-constant.ko.md)

## Objective

This diagnostic separates propagation attenuation and phase error from the
source spectrum and two-receiver spectral-ratio artifacts. It uses a laterally
uniform Earth–ionosphere waveguide and fits the complex receiver spectrum over
distance.

## Method

The production conditions match the directional-dispersion control: a uniform
material model, 40 radial cells at 5 km spacing, a 3 μs time step, 25,023
updates, CUDA `float64`, and the 45 paper-compatible bins from 50.862630 to
498.453776 Hz. Subdivisions 6, 7, and 8 were evaluated.

Twelve great-circle paths at 30° azimuth intervals each contain receivers at
30°, 45°, 60°, 75°, and 90° arc distance. Before regression, the spherical
spreading factor

```text
G(d) = 1 / sqrt(sin(d / R))
```

is removed. Linear least squares fits log amplitude and unwrapped spatial phase
against distance. The phase is branch-stabilized by removing the Bannister
reference slope before unwrapping and restoring it afterward; the fitted slope
is not constrained to the reference value.

## Results

| Subdivision | Attenuation MAE | Phase-velocity MAE | Mean complex regression RMS | 375–500 Hz RMS |
|---:|---:|---:|---:|---:|
| 6 | 0.433071 dB/Mm | 0.0338621 c | 0.136438 | 0.429621 |
| 7 | 0.160093 dB/Mm | 0.0185494 c | 0.0398981 | 0.122997 |
| 8 | 0.106496 dB/Mm | 0.0142647 c | 0.0292820 | 0.0910130 |

For subdivision 8, the band-separated results are:

| Frequency band | Attenuation MAE | Phase-velocity MAE | Complex regression RMS |
|---|---:|---:|---:|
| 50–200 Hz | 0.0735581 dB/Mm | 0.0107487 c | 0.00174516 |
| 200–375 Hz | 0.0569331 dB/Mm | 0.0146422 c | 0.00637322 |
| 375–500 Hz | 0.209314 dB/Mm | 0.0178281 c | 0.0910130 |
| 400–500 Hz | 0.257302 dB/Mm | 0.0181618 c | 0.112557 |

The subdivision-8 maximum mean regression residual is 0.294146 at
498.453776 Hz. Its maximum attenuation error is 0.638339 dB/Mm at
498.453776 Hz, and its maximum phase-velocity error is 0.0242784 c at
488.281250 Hz.

## Pairwise comparison

The same traces were also analyzed with a 45°–90° receiver pair. At
subdivision 8, the multi-receiver and pairwise phase velocities differ by only
0.000116 c on average over 50–200 Hz, 0.000117 c over 200–375 Hz, and
0.001463 c over 375–500 Hz. The phase discrepancy therefore does not arise
primarily from the former two-receiver ratio.

Attenuation is more measurement-sensitive in the upper band. The two methods
differ by 0.123208 dB/Mm on average over 375–500 Hz and 0.151226 dB/Mm over
400–500 Hz.

## Decision gate

Both fitted attenuation and phase velocity retain smooth, frequency-dependent
disagreement with Bannister while improving under horizontal refinement. This
supports discrete propagation/model dispersion as the next priority. The
phase result is stable against replacing the pairwise ratio with multi-point
regression.

The regression residual grows strongly above approximately 400 Hz, although it
also decreases substantially from subdivision 6 to 8. High-frequency modal
mixture, transient extraction, and finite spatial resolution remain relevant
to attenuation extraction in that band. Stage 2 should therefore test the
independent radial discretization contribution before assigning the remaining
common error to the horizontal Maxwell operator.

## Archived outputs

Each level directory under `artifacts/propagation-constant/` contains:

- `receiver-traces.npz`: all 60 time-domain receiver records;
- `propagation-constant-fit.npz`: spectra, fitted constants, and residuals;
- `propagation-constant-fit.csv`: per-frequency and per-azimuth fit values;
- `propagation-constant-fit.png`: attenuation, phase velocity, and residual plots;
- `metadata.json`: complete command, grid and backend configuration, DFT cutoffs,
  Git revision, elapsed time, and summary metrics.

## Verification

The complete test suite reports `229 passed, 2 skipped`. `git diff --check`
passes. All archived fit arrays contain finite values, and each rendered plot is
an RGBA `2160 x 1440` image.
