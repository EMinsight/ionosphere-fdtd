# Analytic-solution benchmark suite

[한국어 번역](analytic-solution-benchmarks.ko.md)

## Objective

Future solver validation will use problems whose reference solutions follow
from Maxwell's equations and the declared boundary conditions, not curves from
a particular paper. This catalog separates continuum analytic solutions from
exact discrete-time solutions and orders the cases from component checks to a
full-vector spherical-cavity benchmark.

## Prepared cases

| ID | Analytic model | Solver features exercised | Reference quantity | Readiness |
|---|---|---|---|---|
| A0 | Zero fields and vacuum static field | Field storage, source-free update, boundaries | Fields remain exactly unchanged | Existing automated invariant |
| A1 | Curl-free field in a homogeneous conductor | Material sampling, lossy E update, precision | `E(t)=E0 exp[-sigma t/(epsilon_0 epsilon_r)]` | Formula, tests, and current update path ready |
| A2 | Spherical surface harmonic in a lossless thin shell | Geodesic curl/Hodge metrics, TM/TE branches, leapfrog time integration | `lambda_l=l(l+1)/R^2`; `f_l=c sqrt(lambda_l)/(2 pi)`; exact leapfrog frequency | Formula and component tests ready; production convergence runner next |
| A3 | Plane wave in a homogeneous lossy medium | Permittivity, conductivity, attenuation and phase signs | `gamma=sqrt[j omega mu (sigma+j omega epsilon)]` | Formula and tests ready; requires a plane-wave/periodic auxiliary geometry for end-to-end use |
| A4 | Vector spherical harmonics between two concentric PEC spheres | Full spherical radial metrics, all field components, radial PEC boundaries, modal frequency extraction | TE/TM spherical-Bessel determinant roots | Root solver ready; staggered-field initializer and projection runner are the next implementation target |

The A1 implementation uses `EPSILON_0 * relative_permittivity`.

## Analytic references

### A1: homogeneous conductive relaxation

For a spatially curl-free electric field with no impressed current,

```text
epsilon dE/dt + sigma E = 0,
E(t) = E0 exp(-sigma t / epsilon).
```

This is an exact test of the exponential loss integrator. With trapezoidal
loss integration, compare instead with its known rational amplification
factor so physical-model and discrete-integrator error are not mixed.

### A2: lossless spherical surface modes

For a scalar spherical harmonic `Y_l^m`,

```text
-Delta_S Y_l^m = l(l+1)/R^2 Y_l^m.
```

The continuum angular frequency is `omega_l=c sqrt(l(l+1))/R`. Once a spatial
discrete eigenvalue `lambda_h` is measured, the centered leapfrog recurrence
has the exact numerical frequency

```text
omega_dt = (2/dt) asin(c dt sqrt(lambda_h) / 2).
```

The first comparison measures spatial convergence to the continuum value. The
second compares the time trace with the exact discrete recurrence at machine
precision. Keeping these tests separate identifies whether an error comes from
space or time.

### A3: homogeneous lossy propagation

For the `exp(+j omega t)` convention,

```text
gamma = alpha + j beta
      = sqrt[j omega mu (sigma + j omega epsilon)].
```

At 400 Hz with `sigma=0.001 S/m` and `epsilon_r=10`, the prepared reference is
`alpha=0.00125649725 Np/m`, `beta=0.00125677689 rad/m`, and phase velocity
`1.99977748e6 m/s`. This case is useful for verifying attenuation sign and
material coefficients, but the global spherical grid does not supply a pure
periodic plane-wave channel. It should remain an auxiliary geometry rather
than be inferred from a point-source global waveform.

### A4: concentric PEC spherical cavity

Let the inner and outer radii be `a` and `b`. A radial function is a linear
combination of spherical Bessel functions `j_l(kr)` and `y_l(kr)`. The PEC
roots satisfy

```text
TE: det [[j_l(ka), y_l(ka)], [j_l(kb), y_l(kb)]] = 0
TM: replace each z_l(x) by d[x z_l(x)]/dx.
```

For `a=6371 km`, `b=a+100 km`, and `l=1`, the first three prepared roots are:

| Polarization | Frequencies (Hz) |
|---|---|
| TE | 1498.99913, 2997.94300, 4496.89915 |
| TM | 10.50912, 1498.99913, 2997.94300 |

The low TM root exercises horizontal Earth-scale propagation; the approximately
1499 Hz roots exercise the first radial standing wave. This makes A4 the best
single end-to-end problem for distinguishing horizontal, radial, polarization,
boundary, and time-integration errors.

## Acceptance protocol

Use predeclared refinement sequences and fit `error=C h^p`; do not compare only
one grid.

1. A0 must remain at exact zero on every backend and supported dtype.
2. A1 must match the selected loss integrator's analytic amplification to
   roundoff for a curl-free field, including a stiff conductive case.
3. A2 discrete-time traces must match the leapfrog recurrence to roundoff.
   Continuum eigenvalue errors must decrease monotonically with an observed
   order near two on subdivisions 5–8.
4. A3 must recover positive attenuation and phase constant, with both errors
   decreasing under space/time refinement in the auxiliary channel.
5. A4 must recover both the low TM and first radial TE modes. Frequency error,
   mode-projection leakage, energy drift, and PEC tangential-field residual
   must all decrease under refinement.

No tolerance should be chosen from an observed production result. Initial
roundoff tolerances may scale with dtype; convergence gates should use order
and monotonicity before fixed percentage thresholds.

## Implementation order

The immediate next change should implement the A4 staggered vector-spherical-
harmonic initializer and modal projection at small subdivisions. A2 should run
alongside it as a cheaper regression. A3 should be deferred until a periodic
or otherwise exact plane-wave auxiliary geometry exists; using the global
point-source solution would invalidate its analytic assumptions.

## Reproduction

[`artifacts/analytic-solutions/`](../../artifacts/analytic-solutions/) stores
the generated reference catalog. Rebuild it with:

```bash
python -m verification.analytic_solutions
```
