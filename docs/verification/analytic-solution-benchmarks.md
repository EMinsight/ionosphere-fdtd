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
| A2 | Spherical surface harmonic in a lossless thin shell | Geodesic curl/Hodge metrics, TM/TE branches, leapfrog time integration | `lambda_l=l(l+1)/R^2`; `f_l=c sqrt(lambda_l)/(2 pi)`; exact leapfrog frequency | Full-field convergence runner complete |
| A3 | Plane wave in a homogeneous lossy medium | Permittivity, conductivity, attenuation and phase signs | `gamma=sqrt[j omega mu (sigma+j omega epsilon)]` | Periodic Yee auxiliary-geometry convergence complete |
| A4 | Vector spherical harmonics between two concentric PEC spheres | Full spherical radial metrics, all field components, radial PEC boundaries, modal frequency extraction | TE/TM spherical-Bessel determinant roots | Full-field measurements complete; strict acceptance FAILS on joint TE leakage order |

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

The auxiliary periodic one-dimensional Yee problem now measures the damped
Fourier mode directly. Both its decay rate and oscillation frequency converge
to their continuum references at second order. This auxiliary
case isolates the simultaneous loss and propagation update; it does not test
the spherical Hodge geometry, which A2 and A4 cover.

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

## Measured convergence

The initializer samples the analytic vector spherical harmonic at the actual
staggered electric-field degrees of freedom. It starts a standing wave with
`H=0`; the projector then measures its energy-weighted modal amplitude and
orthogonal leakage while the solver advances every field component normally.
No component is reset or suppressed after initialization.

| Case and quantity | Coarsest relative error | Finest relative error | Observed order |
|---|---:|---:|---:|
| A2 low TM frequency, subdivisions 1–4 | `-1.9382%` | `-0.03169%` | `1.9782` |
| A3 periodic decay rate, 64–512 cells | `+0.3633%` | `+0.005640%` | `2.0031` |
| A3 periodic frequency, 64–512 cells | `-0.5630%` | `-0.008753%` | `2.0024` |
| A4 first radial TE frequency, 8–32 radial cells | `-0.6161%` | `-0.03856%` | `1.9989` |
| A4 first radial TM frequency, 8–32 radial cells | `-0.6161%` | `-0.03858%` | `1.9987` |

The maximum measured off-mode electric-energy fraction is `0.0009570271`.
A2 supplies the horizontal geodesic refinement study, while the A4 TE and TM
runs isolate radial refinement at fixed angular subdivision 2.

Every A4 row is observed for five analytic mode periods. Radial convergence
holds angular subdivision 2 fixed and judges frequency, centered energy, and
PEC enforcement. Modal leakage is judged separately on the joint sequence
`(subdivision, radial cells) = (1, 8), (2, 16), (3, 32)`.

| A4 diagnostic | Coarse | Medium | Fine | Verdict |
|---|---:|---:|---:|---|
| TE centered-energy variation | `0.2995%` | `0.07198%` | `0.01439%` | PASS, order `2.1897` |
| TM centered-energy variation | `0.3093%` | `0.08176%` | `0.02416%` | PASS, order `1.8392` |
| TE joint modal leakage | `0.02347%` | `0.04121%` | `0.04406%` | FAIL, order `-0.4542` |
| TM joint modal leakage | `0.08704%` | `0.04486%` | `0.02134%` | PASS, order `1.0139` |
| PEC tangential trace residual | `0` | `0` | `0` | PASS, exactly enforced |

The low TM mode reused by A2 has monotonically decreasing leakage from
`0.09570%` to `0.003255%`. Separating the refinement directions resolves the
earlier TM leakage ambiguity, but the equally timed joint study exposes a TE
failure instead. The strict aggregate A4 verdict remains **FAIL** because the
analytic TE mode does not approach an invariant discrete modal subspace under
this sequence.

## Acceptance protocol

Use predeclared refinement sequences and fit `error=C h^p`; do not compare only
one grid.

1. A0 must remain at exact zero on every backend and supported dtype.
2. A1 must match the selected loss integrator's analytic amplification to
   roundoff for a curl-free field, including a stiff conductive case.
3. A2 discrete-time traces must match the leapfrog recurrence to roundoff.
   Continuum eigenvalue errors must decrease monotonically with an observed
   order near two on subdivisions 1–4.
4. A3 must recover positive attenuation and phase constant, with both errors
   decreasing under space/time refinement in the auxiliary channel.
5. A4 observes every radial mode for five analytic periods. On radial cells
   8–32 at angular subdivision 2, TE/TM frequency error and centered-energy
   variation must decrease monotonically, with fitted orders at least `1.8`
   and `1.5`, respectively. Joint TE/TM leakage on `(1,8)`, `(2,16)`, and
   `(3,32)` must have positive fitted order. Low-TM leakage must decrease
   monotonically, and the odd-ghost PEC trace must remain exactly zero.

No tolerance should be chosen from an observed production result. Initial
roundoff tolerances may scale with dtype; convergence gates should use order
and monotonicity before fixed percentage thresholds.

## Next implementation work

The analytic cases can now be placed according to their intended cost: compact
invariants and formula checks in pytest, convergence timing in benchmarks, and
the generated full-field evidence in verification. Production acceptance
thresholds should be declared separately from these exploratory measurements.

## Reproduction

[`artifacts/analytic-solutions/`](../../artifacts/analytic-solutions/) stores
the generated reference catalog. Rebuild it with:

```bash
python -m verification.analytic_solutions
python -m verification.analytic_solutions --full-field
```
