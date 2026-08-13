# Discrete spherical-operator spectrum

[한국어 번역](operator-spectrum.ko.md)

## Objective

Stage 3 measures horizontal numerical dispersion directly from the
circumcentric primal/dual scalar Laplacian induced by the FDTD metric factors.
It extends the former `l=1,2` checks through `l=100` on native polar and
Mesquite-optimized subdivision 6, 7, and 8 grids.

## Physical degree range

For a horizontally propagating ELF mode,

```text
l ~= beta R = 2*pi*f*R / v(f)
```

Using the same Bannister phase velocity as the propagation verification gives
`l=8.55785` at 50 Hz and `l=75.5659` at 500 Hz. The evaluated `l=1–100` range
therefore contains the complete physical band and extends beyond it to expose
the onset of under-resolution.

At every degree the diagnostic evaluates real `Y_l^0`, real `Y_l^l`, and
imaginary `Y_l^l`. It records the area-weighted Rayleigh effective eigenvalue,
effective wavenumber, and the residual after removing the fitted eigenvalue.
These zonal and sectoral modes sample distinct orientations but are not an
exhaustive enumeration of all `2l+1` orders.

## Results

| Grid | `l=9–75` eigenvalue MAE | `l=9–75` wavenumber MAE | `l=60–76` wavenumber MAE | `l=76` wavenumber error | `l=76` mode residual |
|---|---:|---:|---:|---:|---:|
| Native 6 | 4.7359% | 2.4141% | 5.1907% | −6.4102% | 1.4109% |
| Native 7 | 1.2174% | 0.6117% | 1.3221% | −1.6394% | 0.4656% |
| Native 8 | 0.3065% | 0.1534% | 0.3321% | −0.4122% | 0.1522% |
| Mesquite 6 | 4.7545% | 2.4238% | 5.2114% | −6.4334% | 0.5345% |
| Mesquite 7 | 1.2220% | 0.6140% | 1.3270% | −1.6448% | 0.1422% |
| Mesquite 8 | 0.3076% | 0.1540% | 0.3333% | −0.4135% | 0.0362% |

The mean wavenumber error is negative throughout the relevant range and grows
smoothly with degree. Native convergence orders averaged over `l=9–75` are
1.988 from subdivision 6 to 7 and 1.997 from 7 to 8. Over the upper ELF range,
the level-7-to-8 order is 1.993. Mesquite gives the same orders within 0.001.

Mesquite strongly improves eigenfunction consistency but does not improve the
Rayleigh eigenvalue. At `l=76`, it reduces the level-8 residual from 0.1522% to
0.0362%, while the wavenumber error changes from −0.4122% to −0.4135%. This
separates local/static consistency from the dispersion-bearing eigenvalue.

## Comparison with Stage 1 propagation

The native subdivision-8 scalar wavenumber error and the Stage 1 relative
phase-velocity residual have a frequency correlation coefficient of 0.856 over
the 45 common bins. Their magnitudes compare as follows:

| Frequency | Mapped degree | Scalar wavenumber error | Stage 1 relative velocity residual | Magnitude ratio |
|---:|---:|---:|---:|---:|
| 50.862630 Hz | 8.697 | −0.00594% | −1.3204% | 0.45% |
| 203.450521 Hz | 32.256 | −0.07540% | −1.5095% | 5.0% |
| 376.383464 Hz | 57.746 | −0.23886% | −1.8601% | 12.8% |
| 498.453776 Hz | 75.345 | −0.40508% | −1.4532% | 27.9% |

The matching sign and high-frequency growth provide a direct numerical
explanation for part of the upper-band mismatch. The scalar operator does not
explain the broad common offset or the full error magnitude, especially below
approximately 300 Hz.

## Decision gate

Horizontal scalar-operator dispersion is a confirmed high-frequency
contributor, with approximately second-order convergence. It is not a complete
explanation of the 3-D Maxwell propagation residual.

Mesquite reproduces the earlier pattern: it greatly improves static harmonic
consistency but leaves the relevant effective wavenumber nearly unchanged.
The next operator-level refinement should therefore analyze the complete
curl/Hodge Maxwell eigenproblem rather than infer Maxwell propagation solely
from the scalar Laplacian. In the ordered campaign, the present result also
permits Stage 4 to proceed as an independent lower-boundary control.

## Reproducibility and verification

`artifacts/operator-spectrum/` archives all three optimized coordinate sets,
their hashes and Mesquite metadata, per-degree CSV and NPZ results, the plot,
and summary metadata. The full test suite reports `234 passed, 2 skipped`.
`git diff --check` passes, all result arrays are finite, and the plot is an RGBA
`1980 x 1980` image.
