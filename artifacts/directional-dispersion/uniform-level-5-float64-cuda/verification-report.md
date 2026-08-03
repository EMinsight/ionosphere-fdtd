# Geodesic grid directional-dispersion measurement

Generated: 2026-08-03T13:38:56+09:00

## Reproduction command

```bash
uv run --extra pytorch --extra visualization ionosphere-measure-dispersion \
  --subdivision 5 \
  --steps 25023 \
  --azimuth-step-deg 30 \
  --backend torch \
  --device cuda:0 \
  --dtype float64 \
  --torch-compile \
  --synchronize-every 1024 \
  --output-dir artifacts/directional-dispersion/uniform-level-5-float64-cuda
```

## Configuration

| Item | Value |
|---|---:|
| Git revision | `4255efa-dirty` |
| subdivision | 5 |
| surface cells | 10,242 |
| radial cells | 40 |
| material | `uniform` |
| backend | `torch` |
| device | `cuda:0` |
| dtype | `float64` |
| compiled | `True` |
| azimuth spacing | 30° |
| azimuth count | 12 |
| receiver arcs | 45° / 90° |
| DFT cutoffs | 21,463–21,617 samples |
| elapsed | 53.0 s |

## Metrics

| Metric | Value |
|---|---:|
| `mean_azimuthal_relative_spread` | 0.0424167729 |
| `maximum_azimuthal_relative_spread` | 0.120832 |
| `maximum_azimuthal_spread_frequency_hz` | 406.901042 |
| `azimuthal_relative_rms` | 0.0247046396 |
| `mean_phase_velocity_mae_fraction_c` | 0.0813617766 |
| `mean_phase_velocity_max_error_fraction_c` | 0.191704501 |
| `mean_phase_velocity_max_error_frequency_hz` | 366.210938 |

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
