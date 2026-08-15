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

## Accuracy research status

The independent directional-dispersion and material-support convergence study
is reported in the 2004 reproduction because Figures 5–6 reuse that propagation
model. At 20 Hz, median phase and group errors converge at approximately second
order over subdivisions 2–6, while the P95 directional anisotropy falls from
6.365% to 0.080%. Smooth-property point-versus-support differences also
decrease monotonically for both radial dual cells and tangential edge diamonds.

For Figure 7, the new material API can represent horizontally varying
ionosphere height/scale profiles and import three-dimensional conductivity and
permittivity volumes from a canonical NPZ grid. No Hermance conductivity volume
or equivalent observation product is present in this repository, so no
unverifiable substitute is introduced and the radar scaling verdict remains
**FAIL**. A future observational run must record dataset identity, units,
coordinate datum, interpolation policy, and checksum alongside the trace
archive.

## Reproduction

```bash
python -m verification.simpson_taflove_2004 --help
python -m verification.simpson_taflove_2006 --help
python -m verification.scientific_accuracy --help
```

Each production archive includes configuration, checksums, and run signatures.
Published panels are included only for technical comparison.
