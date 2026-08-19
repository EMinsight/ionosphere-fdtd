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

The dissertation body supports this peak-reference denominator, but the
Figure 26 caption attributes spikes to zero crossings of the reference
waveform, which instead implies an instantaneous denominator. Both
interpretations are therefore calculated below; neither is silently selected
to improve agreement.

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
  $\geq5000\ \Omega\,\mathrm{m}$, oceanic classes of $\leq5$, $\leq50$,
  $\geq500$, and $\leq200\ \Omega\,\mathrm{m}$, and a deep class of
  $\leq50\ \Omega\,\mathrm{m}$;
- the Laurentian Plateau is described as extending north from the Great Lakes
  to the Arctic and including much of Canada and Greenland; and
- the adjacent ionospheric-radar application states that dawn occurs at
  $0^\circ$ longitude and gives approximate effective reflection heights of
  48 km by day and 76 km by night.

The oil-field section does not explicitly say that it uses the adjacent
application's dawn orientation. The dissertation also does not provide a
cellwise Figure 15 volume, an exact Shield mask, the isolated conductor's
geographic location, or the horizontal shape of the hypothetical oil body.
The extracted information therefore defines a traceable hypothesis rather
than a unique recovered input volume.

### Dissertation-informed experiment

The dissertation-informed material uses separate continental and oceanic
profiles at the actual E-field sampling directions. Because Figure 15 is a
schematic with inequality-valued classes, its class limits are used as
representative values and visual boundaries are snapped to the nominal 5 km
radial grid. The continental hypothesis is 10 $\Omega\,\mathrm{m}$ from
0--5 km, 5000 $\Omega\,\mathrm{m}$ from 5--45 km, and
50 $\Omega\,\mathrm{m}$ below 45 km. The oceanic rock hypothesis is 5, 50,
500, 200, and 50 $\Omega\,\mathrm{m}$ over boundaries at 5, 10, 20, and
45 km below sea level. The geographically unspecified isolated conductor in
Figure 15 is omitted.

The ionosphere uses the established daytime profile ($H=70\ \mathrm{km}$,
scale $3.333\ \mathrm{km}$), the cited Bannister ambient-night representative
($H=92.8\ \mathrm{km}$, scale $2.47\ \mathrm{km}$), and a subsolar point at
$0^\circ$ N, $90^\circ$ E so that dawn occurs at $0^\circ$ longitude. The
profiles yield $3.011\times10^{-9}$ and $2.461\times10^{-9}\ \mathrm{S/m}$
at the dissertation's approximate day and night reflection heights,
respectively, providing a consistent independent check.

ETOPO5, the paper source, the $4800\ \mathrm{km}^2$ conservative oil support,
the $0.1$ conductivity factor, `float64`, and a Courant factor of 1 were held
fixed. The table reports the caption-implied pointwise medians and the
body-defined peak-normalized maxima from the same traces.

| Subdivision | Reference $H_r$ peak | Pointwise median $\Delta H_{tan}$ | Pointwise median $\Delta H_r$ | Peak-normalized max $\Delta H_{tan}$ | Peak-normalized max $\Delta H_r$ |
|---:|---:|---:|---:|---:|---:|
| 4 | $1.249\times10^{-13}$ A/m | $-95.728$ dB | $-26.213$ dB | $-102.206$ dB | $-29.423$ dB |
| 5 | $7.403\times10^{-17}$ A/m | $-80.390$ dB | $+44.799$ dB | $-86.400$ dB | $+45.792$ dB |
| 6 | $3.186\times10^{-17}$ A/m | $-60.724$ dB | $+86.660$ dB | $-64.143$ dB | $+91.504$ dB |

The tangential perturbation remains below $-25$ dB for 99.774--99.975% of
valid pointwise samples, but the radial result does not converge. Its
peak-normalized maximum moves by about 121 dB from subdivision 4 to 6, crossing
the published $+20$ dB scale without approaching a stable value. The reference
$H_r$ peak also collapses by more than three orders of magnitude from
subdivision 4 to 5, while the anomaly-induced peak grows by about 83 times from
subdivision 5 to 6. A subdivision-4 control with the former $0^\circ$ subsolar
longitude changes the radial maximum by only 6.30 dB, so the dawn orientation
does not explain the nonconvergence.

The layered Figure 15 hypothesis therefore does not justify subdivision 7 and
does not change the Figure 7 or complete-reproduction verdict from **FAIL**.
Complete machine-readable settings and both normalization results are stored in
`artifacts/verification/simpson-taflove-2006-thesis.json`.

## Accuracy research status

The independent directional-dispersion and material-support convergence study
is reported in the 2004 reproduction because Figures 5–6 reuse that propagation
model. At 20 Hz, median phase and group errors converge at approximately second
order over subdivisions 2–6, while the P95 directional anisotropy falls from
6.365% to 0.080%. Smooth-property point-versus-support differences also
decrease monotonically for both radial dual cells and tangential edge diamonds.

For Figure 7, the material API now directly exercises the dissertation's
day/night statement and the verification package contains an explicitly
qualified Figure 15 piecewise hypothesis. It can also import three-dimensional
conductivity and permittivity volumes from a canonical NPZ grid. No cellwise
Hermance volume or equivalent observation product is present, so the schematic
hypothesis is not represented as a recovered global map and the radar scaling
verdict remains **FAIL**. A future observational run must record dataset
identity, units, coordinate datum, interpolation policy, and checksum alongside
the trace archive.

## Reproduction

```bash
python -m verification.simpson_taflove_2004 --help
python -m verification.simpson_taflove_2006 --help
python -m verification.scientific_accuracy --help
```

Each production archive includes configuration, checksums, and run signatures.
Published panels are included only for technical comparison.
