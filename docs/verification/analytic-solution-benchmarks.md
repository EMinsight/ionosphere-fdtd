# Analytic Maxwell Solver Verification (A0–A4)

## Purpose

This report verifies the geodesic FDTD solver against solutions derived from
Maxwell's equations and explicit boundary conditions. The cases progress from
exact invariants to full-vector modes in a concentric spherical PEC cavity.
All reported production runs use `float64` fields.

| Case | Model | Primary solver feature | Result |
|---|---|---|---|
| A0 | Source-free zero field | Storage, updates, boundaries | **PASS** |
| A1 | Homogeneous conductive relaxation | Loss integration and material coefficients | **PASS** |
| A2 | Spherical surface harmonic | Geodesic curl/Hodge and leapfrog dispersion | **PASS** |
| A3 | Homogeneous lossy plane wave | Simultaneous propagation and attenuation | **PASS** |
| A4 | Concentric PEC spherical cavity | Full-vector TE/TM modes and radial boundaries | **PASS** |

## A0: source-free zero field

With no sources and zero initial conditions,

$$
\mathbf{E}(\mathbf{x},0)=\mathbf{0},\qquad
\mathbf{H}(\mathbf{x},0)=\mathbf{0},
$$

Maxwell's equations give the exact solution

$$
\mathbf{E}(\mathbf{x},t)=\mathbf{0},\qquad
\mathbf{H}(\mathbf{x},t)=\mathbf{0}.
$$

The solver preserves every field array exactly. This invariant is checked by
default pytest because it is deterministic and requires no convergence study.

## A1: homogeneous conductive relaxation

For a spatially curl-free electric field in a homogeneous isotropic medium,
Ampère's law reduces to

$$
\epsilon\frac{d\mathbf{E}}{dt}+\sigma\mathbf{E}=0,
\qquad \epsilon=\epsilon_0\epsilon_r.
$$

The analytic solution is

$$
\mathbf{E}(t)=\mathbf{E}_0
\exp\!\left(-\frac{\sigma t}{\epsilon}\right),
\qquad
\tau=\frac{\epsilon}{\sigma}.
$$

The exponential loss update matches this amplification, remains passive, and
stays finite in the stiff-conductivity limit. Pytest owns these fast contracts;
the analytic catalog records representative reference values.

## A2: spherical surface harmonics

On a sphere of radius $R$, a scalar spherical harmonic satisfies

$$
-\Delta_S Y_\ell^m
=\lambda_\ell Y_\ell^m,
\qquad
\lambda_\ell=\frac{\ell(\ell+1)}{R^2}.
$$

For wave speed $c$, the continuum angular frequency and frequency are

$$
\omega_\ell=c\sqrt{\lambda_\ell},
\qquad
f_\ell=\frac{c}{2\pi R}\sqrt{\ell(\ell+1)}.
$$

If the spatial discretization produces $\lambda_h$, centered leapfrog time
integration has the exact discrete frequency

$$
\omega_{h,\Delta t}
=\frac{2}{\Delta t}
\sin^{-1}\!\left(\frac{c\Delta t\sqrt{\lambda_h}}{2}\right).
$$

The low-TM full-field sequence uses subdivisions 1–4. Its relative frequency
error decreases from $-1.9382\%$ to $-0.03169\%$, with observed order
$p=1.9782$. Maximum off-mode electric-energy leakage decreases from
$0.09570\%$ to $0.003255\%$.

## A3: homogeneous lossy propagation

For the $e^{+j\omega t}$ convention in a homogeneous medium,

$$
\gamma=\alpha+j\beta
=\sqrt{j\omega\mu\left(\sigma+j\omega\epsilon\right)},
$$

where $\alpha$ is attenuation and $\beta$ is phase constant. The phase
velocity is

$$
v_p=\frac{\omega}{\beta}.
$$

At $f=400\ \mathrm{Hz}$, $\sigma=10^{-3}\ \mathrm{S/m}$, and
$\epsilon_r=10$, the reference values are

$$
\alpha=1.25649725\times10^{-3}\ \mathrm{Np/m},
$$

$$
\beta=1.25677689\times10^{-3}\ \mathrm{rad/m},
\qquad
v_p=1.99977748\times10^6\ \mathrm{m/s}.
$$

A periodic one-dimensional Yee auxiliary geometry isolates this material and
time-update test without introducing spherical point-source spreading. Over
64–512 cells, attenuation and frequency errors converge with orders $2.0031$
and $2.0024$, respectively. A3 therefore verifies the update equations, not
the geodesic Hodge geometry covered by A2 and A4.

## A4: concentric PEC spherical cavity

Let the cavity occupy $a<r<b$ with perfect electric conductors at both radial
boundaries. The vector spherical-harmonic radial factor is

$$
z_\ell(kr)=A j_\ell(kr)+B y_\ell(kr),
$$

where $j_\ell$ and $y_\ell$ are spherical Bessel functions. Nontrivial TE
solutions require

$$
\det\begin{pmatrix}
j_\ell(ka) & y_\ell(ka)\\
j_\ell(kb) & y_\ell(kb)
\end{pmatrix}=0.
$$

For TM modes, define

$$
D z_\ell(x)=\frac{d}{dx}\left[xz_\ell(x)\right].
$$

The TM roots satisfy

$$
\det\begin{pmatrix}
D j_\ell(ka) & D y_\ell(ka)\\
D j_\ell(kb) & D y_\ell(kb)
\end{pmatrix}=0,
\qquad
f=\frac{ck}{2\pi}.
$$

For $a=6371\ \mathrm{km}$, $b=a+100\ \mathrm{km}$, and $\ell=1$:

| Polarization | First three frequencies (Hz) |
|---|---|
| TE | 1498.99913, 2997.94300, 4496.89915 |
| TM | 10.50912, 1498.99913, 2997.94300 |

The initializer samples the analytic vector mode at the actual staggered
electric degrees of freedom and starts a standing wave with $\mathbf{H}=0$.
The solver advances all field components without resetting or suppressing any
component. The projector measures energy-weighted amplitude and orthogonal
leakage.

The final asymptotic TE sequence was declared as subdivision/radial-cell pairs
$(2,16)$, $(3,32)$, and $(4,64)$, with every case observed for five analytic
periods.

| Quantity | $(2,16)$ | $(3,32)$ | $(4,64)$ | Order | Result |
|---|---:|---:|---:|---:|---|
| Relative frequency error | $-0.15417\%$ | $-0.03855\%$ | $-0.009638\%$ | 1.99979 | **PASS** |
| Centered-energy variation | $0.07198\%$ | $0.01436\%$ | $0.00009418\%$ | 4.78900 | **PASS** |
| Modal leakage | $0.04121\%$ | $0.04406\%$ | $0.03524\%$ | 0.11302 | **PASS** |
| PEC tangential trace residual | 0 | 0 | 0 | — | **PASS** |

The radial TE and TM frequency studies independently converge with orders
1.9989 and 1.9987. The odd-ghost construction enforces the tangential PEC trace
exactly.

## Test placement

| Layer | Responsibility | A0–A4 content |
|---|---|---|
| Default pytest | Fast deterministic contracts | Invariants, formulas, loss update, initializer/projector, and gate logic |
| `verification/` | Scientific evidence and acceptance | A2 full field, A3 periodic convergence, A4 radial/asymptotic full field |
| `benchmarks/` | Runtime only | Representative A0–A4 workflows; never used for PASS/FAIL |

## Reproduction

```bash
python -m pytest -q
python -m verification.analytic_solutions --full-field
python -m verification.analytic_solutions --operator-analysis
python -m verification.analytic_solutions --a4-asymptotic
```

Generated data are stored in
[`artifacts/analytic-solutions/`](../../artifacts/analytic-solutions/).
