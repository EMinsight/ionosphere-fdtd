# Curl/Hodge Maxwell operator spectrum

[한국어 번역](maxwell-spectrum.ko.md)

## Objective and formulation

This follow-up applies the complete horizontal DEC one-form operator
`d delta + delta d` to edge electric-field degrees of freedom. It uses the
same `edge_difference`, `face_circulation`, `dual_cell_circulation`, and
primal/dual length Hodge factors as the FDTD updates. The analysis covers
`l=1–100` on native and Mesquite subdivision 6–8 grids; the physically mapped
50–500 Hz range remains `l=8.56–75.57`.

TM trial fields are exact edge gradients of real sectoral `Y_l^l` sampled at
vertices. TE trial fields are Hodge co-gradients of real sectoral harmonics
sampled at face centers. Rayleigh values and full operator residuals are saved
for both polarizations.

This is a matrix-free projected Maxwell eigenanalysis, not an exhaustive
global eigensolve over the approximately 1.97 million level-8 edge unknowns.
The residual quantifies whether each projected value can be treated as an
eigenvalue.

## Results

| Grid | ELF TM wavenumber MAE | ELF TE projected MAE | Upper-ELF TM MAE | Upper-ELF TE projected MAE | Upper-ELF splitting |
|---|---:|---:|---:|---:|---:|
| Native 6 | 2.4549% | 0.8092% | 5.2760% | 1.7853% | 6.7304% |
| Native 7 | 0.6233% | 0.1989% | 1.3477% | 0.4440% | 1.7908% |
| Native 8 | 0.1565% | 0.0480% | 0.3388% | 0.1091% | 0.4582% |
| Mesquite 6 | 2.4767% | 0.8272% | 5.3255% | 1.8076% | 6.7801% |
| Mesquite 7 | 0.6282% | 0.2074% | 1.3587% | 0.4537% | 1.7933% |
| Mesquite 8 | 0.1576% | 0.0519% | 0.3414% | 0.1135% | 0.4547% |

At `l=76`, native level 8 gives a TM wavenumber error of −0.4204% and a TE
projected error of −0.1368%. Mesquite changes them to −0.4237% and −0.1414%,
respectively. Coordinate optimization therefore does not improve the
dispersion-bearing Rayleigh values.

The TM result agrees closely with the preceding scalar result because exact
DEC maps preserve the gradient branch. Its correlation with the Stage 1
relative phase-velocity residual is 0.857. At 498.453776 Hz it accounts for
28.4% of the observed residual magnitude; at 376.383464 Hz it accounts for
13.1%.

## Residual qualification

For native level 8, the TM residual is 1.34% at `l=9` and 0.615% at `l=76`.
Mesquite reduces it to 0.700% and 0.0114%. The TM branch is therefore a stable
projected eigenmode, especially on optimized coordinates.

The face-center TE construction has much larger residuals: 86.6% at `l=9` and
19.9% at `l=76` for native level 8, reduced to 32.6% and 14.1% by Mesquite.
Its Rayleigh values show polarization splitting but are not accurate enough to
claim precise TE eigenvalues. A rigorous TE spectrum would require solving the
dual-face scalar eigenproblem or a global block eigensystem rather than
sampling continuum harmonics at face centers.

## Assessment

The complete curl/Hodge operator confirms that the well-resolved TM Maxwell
branch has the same approximately second-order high-frequency dispersion found
by the scalar diagnostic. Mesquite improves eigenfunction consistency without
improving its eigenvalue. This strengthens the conclusion that horizontal
operator dispersion contributes to the upper-band residual but cannot explain
the broad 1–2% phase-velocity offset by itself.

The current experiment does not close the TE branch quantitatively. The next
operator-specific step, if pursued, should construct and solve the dual-face
generalized eigenproblem. For the ordered verification campaign, the robust TM
result is sufficient to stop attributing the full residual to scalar/static
mesh quality and proceed to the Stage 4 lower-boundary control.

## Verification

`artifacts/maxwell-spectrum/` contains all numerical arrays, CSV rows, plot,
and configuration metadata. The full test suite reports `236 passed, 2
skipped`; `git diff --check` passes. All arrays are finite and the plot is an
RGBA `1980 x 1980` image.
