# Geodesic grid directional-dispersion measurement

Generated: 2026-08-03T13:56:03+09:00

## Reproduction command

```bash
uv run --extra pytorch --extra visualization ionosphere-measure-dispersion \
  --subdivision 7 \
  --steps 25023 \
  --azimuth-step-deg 30 \
  --backend torch \
  --device cuda:0 \
  --dtype float64 \
  --torch-compile \
  --synchronize-every 1024 \
  --output-dir artifacts/directional-dispersion/uniform-level-7-float64-cuda
```

## Configuration

| Item | Value |
|---|---:|
| Git revision | `4255efa-dirty` |
| subdivision | 7 |
| surface cells | 163,842 |
| radial cells | 40 |
| material | `uniform` |
| backend | `torch` |
| device | `cuda:0` |
| dtype | `float64` |
| compiled | `True` |
| azimuth spacing | 30° |
| azimuth count | 12 |
| receiver arcs | 45° / 90° |
| DFT cutoffs | 21,506–21,572 samples |
| elapsed | 797.6 s |

## Metrics

| Metric | Value |
|---|---:|
| `mean_azimuthal_relative_spread` | 0.000970268199 |
| `maximum_azimuthal_relative_spread` | 0.00294703348 |
| `maximum_azimuthal_spread_frequency_hz` | 498.453776 |
| `azimuthal_relative_rms` | 0.000366147804 |
| `mean_phase_velocity_mae_fraction_c` | 0.0189460969 |
| `mean_phase_velocity_max_error_fraction_c` | 0.0509568375 |
| `mean_phase_velocity_max_error_frequency_hz` | 498.453776 |

![Directional phase velocity](directional-phase-velocity.png)

- [Per-frequency and per-azimuth values](directional-phase-velocity.csv)
- [Receiver traces](directional-traces.npz)

## Interpretation

The material and ionosphere are laterally uniform, so the continuum solution is
azimuth-independent. Deviation from the azimuth mean therefore measures grid
directionality. The difference between the azimuth mean and Bannister equation
(4) measures the combined frequency dispersion of the spatial discretization
and the finite radial material model. No latitude–longitude grid is introduced;
this experiment measures the existing geodesic dual grid unchanged.
