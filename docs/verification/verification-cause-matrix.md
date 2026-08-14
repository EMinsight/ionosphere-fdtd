# Propagation verification cause matrix

[한국어 번역](verification-cause-matrix.ko.md)

## Purpose

This report consolidates Stages 1–6 of the ordered Simpson–Taflove 2004
verification campaign. It separates measured numerical contributions from
hypotheses that were screened out and from model assumptions that remain
unresolved. Paper reproduction and solver physical validation are assessed
separately.

## Cause matrix

| Candidate cause | Evidence | Status | Consequence |
|---|---|---|---|
| Two-receiver ratio or phase-unwrap artifact | Stage 1 multi-receiver spatial regression retains the smooth disagreement. At subdivision 8 its phase-velocity MAE is `0.01075 c`, `0.01464 c`, and `0.01783 c` across the three bands. | Not dominant | The main phase residual is not created by the original pairwise estimator. |
| High-band modal mixture and transient extraction | Stage 1 complex regression RMS rises to `0.0910` over 375–500 Hz and `0.1126` over 400–500 Hz, while falling strongly with refinement. | Confirmed measurement uncertainty | Upper-band attenuation is less robust than phase velocity; pointwise attenuation discrepancies should not be assigned to one mechanism. |
| 5 km radial ionosphere staircase | Stage 2 phase errors are `0.00141–0.00187 c`, explaining about 10–13% of the Stage 1 band errors. Upper-band attenuation error is `0.04358 dB/Mm` versus `0.20931 dB/Mm` in Stage 1. | Confirmed secondary contributor | Radial refinement can improve part of the error but cannot remove its magnitude or frequency growth. |
| Horizontal geodesic operator dispersion | Stages 3 and the curl/Hodge follow-up find approximately second-order negative wavenumber error. Native level-8 upper-ELF TM MAE is `0.3388%`; its correlation with the Stage 1 phase residual is `0.857`. | Confirmed contributor | Horizontal refinement removes a substantial coarse-grid term, especially at high frequency, but does not explain the broad 1–2% phase offset. |
| Static mesh quality or Mesquite coordinates | Mesquite sharply reduces harmonic residuals but leaves the dispersion-bearing eigenvalues essentially unchanged; at `l=76` the level-8 TM error changes from `−0.4204%` to `−0.4237%`. | Screened out as dominant | Better eigenfunction consistency does not imply better propagation eigenvalues. |
| Bulk-Earth voxelization and lower boundary | Stage 4 surface impedance does not coherently improve attenuation and worsens phase velocity in all bands. Bulk and impedance models converge to the same uniform-Earth limit. | Not dominant | Retain surface impedance only as a control; do not replace the paper algorithm to obtain a fit. |
| Purely extrapolated level-9 trend | Stage 5 directly measures 400 Hz subdivision 9: `0.857661 c`, versus the second-order prediction `0.857687 c`. The remaining Bannister residual is `−0.015471 c`. | Extrapolation validated | Further horizontal refinement alone is not expected to reach Bannister; a full broadband level-9 run has low diagnostic value. |
| Geodesic versus merged latitude–longitude grid family | The Stage 6 operator screen converges at order `1.999`; at matched level-9 cell count its reconstructed merged-grid error is 1.39 times the geodesic error. | Not supported; limited screen | The available TM evidence does not show a grid-family advantage. A literal 3-D comparison still requires an authoritative merge-transition stencil. |
| Shared ionosphere/material/reference assumptions | A nonzero phase offset remains after bounding receiver, radial, horizontal-resolution, lower-boundary, and grid-family effects. The available paper inputs do not uniquely reconstruct every model detail. | Leading unresolved class, not a confirmed cause | Future work should test independently sourced ionosphere profiles and the meaning of the Bannister guide rather than tune numerical grids to the plot. |

## Quantitative attribution

At 375–500 Hz, the Stage 1 subdivision-8 phase-velocity MAE is `0.01783 c`.
The independent 5 km radial staircase accounts for `0.00187 c`, or about 10%.
The level-8 horizontal TM operator error is approximately 0.34% in wavenumber,
and the direct 400 Hz level-8-to-9 phase correction is `0.001714 c`. These
effects have the expected sign and are measurable, but the direct level-9
400 Hz residual remains `0.015471 c`.

The experiments do not form an additive error decomposition: radial,
horizontal, modal, and fitting errors interact in the full Maxwell solution.
The numbers above are controlled bounds and trend comparisons, not percentages
that may be summed to 100%.

## Final assessment

### Paper reproduction

Exact Simpson–Taflove figure reproduction remains limited. The published
information does not uniquely specify the adaptive latitude–longitude
transition stencil, all paper-specific material inputs, or every analysis
choice. The verification campaign therefore does not claim that the current
geodesic solver should reproduce the plotted Bannister agreement exactly.

### Solver physical validation

The solver shows consistent refinement behavior and passes the independent
controls exercised here:

- multi-receiver phase extraction is stable;
- radial error decreases under refinement;
- horizontal TM dispersion converges at approximately second order;
- the direct subdivision-9 point matches its prediction;
- uniform bulk and impedance lower boundaries share a refined limit; and
- both horizontal grid families approach the same spherical eigenvalue.

Physical validation is therefore stronger than exact paper reproduction. The
remaining offset should be reported as shared-model/reference uncertainty, not
silently attributed to one numerical defect.

## Recommended next work

1. Freeze the current Stage 1–6 artifacts as the numerical baseline.
2. Build an independent ionosphere-profile sensitivity matrix at 100, 250, and
   400 Hz, varying one physically sourced parameter at a time.
3. Compare each profile first with the radial eigenmode benchmark, then run a
   small number of matched 3-D narrow-band controls only when the radial screen
   predicts a material change.
4. Keep the separate 2006 Figure 7 normalization investigation outside this
   propagation cause matrix.

Do not tune ionosphere parameters, merge thresholds, or observation windows to
the published curves. Predeclare each profile source and acceptance criterion.

## Source reports

- [Stage 1: multi-receiver propagation constants](multi-receiver-propagation-constant.md)
- [Stage 2: radial eigenmode benchmark](radial-eigenmode.md)
- [Stage 3: scalar operator spectrum](operator-spectrum.md)
- [Curl/Hodge Maxwell follow-up](maxwell-spectrum.md)
- [Stage 4: surface-impedance control](surface-impedance.md)
- [Stage 5: subdivision-9 narrow band](narrow-band-subdivision-9.md)
- [Stage 6: merged latitude–longitude control](merged-latlon-control.md)
