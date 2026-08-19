# Simpson–Heikes–Taflove 2006 Reproduction Verification

## Scope

This study evaluates Figures 5–7 of J. J. Simpson, R. P. Heikes, and A. Taflove,
“FDTD Modeling of a Novel ELF Radar for Major Oil Deposits Using a
Three-Dimensional Geodesic Grid of the Earth-Ionosphere Waveguide,” *IEEE
Transactions on Antennas and Propagation*, 54(6), 1734–1741, 2006
([doi:10.1109/TAP.2006.875504](https://doi.org/10.1109/TAP.2006.875504)).

Figures 5–6 reuse the global propagation geometry of the 2004 study. Figure 7
models a 20 Hz tangential transmitter near Clam Lake and compares magnetic
fields in Alaska with and without a $4800\ \mathrm{km}^2$ subsurface oil body.

## Numerical model

The production configuration uses a subdivision-7 geodesic surface
(163,842 cells), 40 nominal radial cells, $5\ \mathrm{km}$ radial spacing,
PyTorch CUDA, and `float64`. The oil anomaly reduces conductivity by a factor
of 0.1 over a $1250\ \mathrm{m}$ vertical interval centered near
$1200\ \mathrm{m}$ depth. Horizontal anomaly support is conservative for both
TM dual cells and TE edge diamonds.

For Figure 7, normalized magnetic perturbation is evaluated as

$$
\Delta H_q(t)=20\log_{10}
\left(
\frac{|H_q^{\mathrm{oil}}(t)-H_q^{\mathrm{ref}}(t)|}
{\max_t |H_q^{\mathrm{ref}}(t)|}
\right),
$$

where $q$ denotes the radial or tangential magnetic component.

## Results

![Figure 5 comparison](images/simpson-taflove-2006-fig-5-comparison.png)

![Figure 6 comparison](images/simpson-taflove-2006-fig-6-comparison.png)

![Figure 7 comparison](images/simpson-taflove-2006-fig-7-comparison.png)

| Criterion | Reproduced result | Verdict |
|---|---:|---|
| Figure 5 morphology and arrival ordering | Reproduced | **PASS** |
| Figure 5 relative amplitudes/path similarity | Far peaks 0.31141/0.35571; path RMS 37.41%/18.47% | **FAIL** |
| Figure 6 east-path attenuation | MAE 0.921, maximum 3.020 dB/Mm | **FAIL** |
| Figure 6 west-path attenuation | MAE 0.284, maximum 2.125 dB/Mm | **FAIL** |
| Figure 7 tangential perturbation median | $-43.253$ dB | **PASS** |
| Figure 7 fraction below $-25$ dB | 92.469% | **FAIL** |
| Figure 7 radial perturbation scale | Median $+126.000$ dB | **FAIL** |
| Complete Figures 5–7 reproduction | At least one quantitative criterion fails per figure | **FAIL** |

The implementation reproduces timing and qualitative waveform structure but
does not reproduce all published relative amplitudes, high-frequency
attenuation, or radar component scaling. Exact Mesquite parameters and the full
three-dimensional Hermance-derived conductivity model were not published, so
the report does not tune undisclosed inputs to force agreement.

## Dissertation supplement

The 2007 Simpson dissertation, *Three-Dimensional FDTD Modeling of Impulsive
Electromagnetic Propagation in the Global Earth-Ionosphere Waveguide*, was
reviewed as an additional primary source (PDF SHA-256
`b3a56bace95f6a59068d27830b25a698ca12d7498885799f5ff53e1cc0f4be45`).
Chapter 5 adds information that is absent from, or conflicts with, the 2006
article:

- the Figure 7 material grid is stated as approximately
  $63\times63\times5\ \mathrm{km}$;
- both daytime and nighttime Bannister exponential ionosphere profiles are
  stated to be present, whereas the article says that Figure 7 reuses the
  daytime profile from its validation section;
- dissertation Figure 15 supplies lithosphere resistivity classes, including
  $0.3\ \Omega\,\mathrm{m}$ seawater, a shallow continental class of
  $\leq10\ \Omega\,\mathrm{m}$, a resistive continental class of
  $\geq5000\ \Omega\,\mathrm{m}$, and a deep class of
  $\leq50\ \Omega\,\mathrm{m}$;
- the Laurentian Plateau is described as extending north from the Great Lakes
  to the Arctic and including much of Canada and Greenland.

The dissertation still does not give the simulation epoch or solar-terminator
orientation, a cellwise mapping from the Figure 15 classes, an exact Shield
mask, or the horizontal shape of the hypothetical oil body. The extracted
classes therefore define bounded hypotheses rather than a unique recovered
input volume.

### Dissertation-informed experiment

The layered material implementation now accepts direction-dependent
ionosphere reference-height and scale-height samplers. The 2006 workflow can
select a declared day/night solar hemisphere and can set the upper-crust,
asthenosphere, and deep-rock resistivities independently. The experiment used
the established daytime profile ($H=70\ \mathrm{km}$, scale
$3.333\ \mathrm{km}$), the cited Bannister ambient-night representative
($H=92.8\ \mathrm{km}$, scale $2.47\ \mathrm{km}$), and an explicitly
declared subsolar point at $0^\circ$ N, $0^\circ$ E. This longitude is an
assumption for sensitivity testing, not a recovered paper input.

ETOPO5, the paper source, the $4800\ \mathrm{km}^2$ conservative oil support,
the $0.1$ conductivity factor, `float64`, and a Courant factor of 1 were held
fixed. The two explicit Figure 15 continental limits were tested separately;
no intermediate resistivity was fitted to the published curve.

| Subdivision | Ionosphere | Upper crust | Median $\Delta H_{tan}$ | Below $-25$ dB | Median $\Delta H_r$ | Median advantage |
|---:|---|---:|---:|---:|---:|---:|
| 4 | day/night | $10\ \Omega\,\mathrm{m}$ | $-96.558$ dB | 99.993% | $+33.217$ dB | $+131.653$ dB |
| 4 | day/night | $500\ \Omega\,\mathrm{m}$ control | $-77.445$ dB | 99.948% | $+8.552$ dB | $+88.464$ dB |
| 4 | day/night | $5000\ \Omega\,\mathrm{m}$ | $-75.573$ dB | 99.961% | $-9.784$ dB | $+65.757$ dB |
| 4 | daytime | $500\ \Omega\,\mathrm{m}$ control | $-76.061$ dB | 99.919% | $+15.555$ dB | $+90.266$ dB |
| 6 | day/night | $10\ \Omega\,\mathrm{m}$ | $-63.013$ dB | 99.640% | $+121.480$ dB | $+187.198$ dB |
| 6 | day/night | $5000\ \Omega\,\mathrm{m}$ | $-47.670$ dB | 99.566% | $+73.143$ dB | $+119.360$ dB |

At subdivision 4, some radial metrics approach the published $+20$ dB scale.
Neither explicit Figure 15 hypothesis retains that behavior at subdivision 6:
the $10\ \Omega\,\mathrm{m}$ radial median changes by $+88.26$ dB and the
$5000\ \Omega\,\mathrm{m}$ median by $+82.93$ dB. Both also remain far from
the paper's approximate 45 dB radial-over-tangential advantage. This is not a
convergent candidate that can justify a costly subdivision-7 promotion.
The dissertation information narrows the missing-input diagnosis but does not
change the Figure 7 or complete-reproduction verdict from **FAIL**. Complete
machine-readable settings and results are stored in
`artifacts/verification/simpson-taflove-2006-thesis.json`.

## Accuracy research status

The independent directional-dispersion and material-support convergence study
is reported in the 2004 reproduction because Figures 5–6 reuse that propagation
model. At 20 Hz, median phase and group errors converge at approximately second
order over subdivisions 2–6, while the P95 directional anisotropy falls from
6.365% to 0.080%. Smooth-property point-versus-support differences also
decrease monotonically for both radial dual cells and tangential edge diamonds.

For Figure 7, the material API now directly exercises the dissertation's
day/night statement and can also import three-dimensional conductivity and
permittivity volumes from a canonical NPZ grid. No cellwise Hermance
conductivity volume or equivalent observation product is present in this
repository, so the resistivity classes are not converted into an invented
global map and the radar scaling verdict remains **FAIL**. A future
observational run must record dataset identity, units, coordinate datum,
interpolation policy, and checksum alongside the trace archive.

## Reproduction

```bash
python -m verification.simpson_taflove_2004 --help
python -m verification.simpson_taflove_2006 --help
python -m verification.scientific_accuracy --help
```

Each production archive includes configuration, checksums, and run signatures.
Published panels are included only for technical comparison.
