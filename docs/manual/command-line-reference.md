# Command-Line Reference

## Simulation runner

`ionosphere` advances the solver and periodically prints scalar diagnostics.
List every option with:

```bash
uv run ionosphere --help
```

The principal option groups are:

| Group | Options |
|---|---|
| Work | `--steps`, `--report-every`, `--resume`, `--checkpoint`, `--checkpoint-every` |
| Grid | `--subdivision`, `--radial-cells`, `--surface-step`, `--courant` |
| Backend | `--backend`, `--device`, `--dtype`, `--torch-compile`, `--torch-compile-chunk-size`, `--torch-threads` |
| Source | `--source-current`, `--source-length`, `--source-frequency`, `--source-center`, `--source-width`, `--source-latitude`, `--source-longitude` |
| Anomaly | `--oil-anomaly`, `--anomaly-radius-km` |

`--surface-step SPACING_M` adds regularly spaced radial nodes within 5 km of
sea level. Because this creates abrupt transitions to the coarse grid, the CLI
selects the explicitly permitted first-order transition policy. Use the Python
API when a smoothly graded custom grid is required.

The built-in oil anomaly is centered near Alaska, extends from 2 km to 0.5 km
below sea level, and multiplies lithosphere conductivity by 0.1. A 40 km radius
is too small for coarse demonstration grids; the runner warns when no electric
sample intersects its support. For a visibly resolved smoke experiment:

```bash
uv run ionosphere \
  --subdivision 3 --radial-cells 40 --surface-step 1250 \
  --oil-anomaly --anomaly-radius-km 1200 \
  --source-frequency 20 --steps 1000
```

The enlarged anomaly is a numerical demonstration, not the published radar
geometry.

## Checkpoints and restart

Write a final checkpoint and refresh it every 1,000 completed steps:

```bash
uv run ionosphere \
  --steps 10000 --checkpoint run.npz --checkpoint-every 1000
```

Resume the embedded model and field state for 5,000 additional steps:

```bash
uv run ionosphere --resume run.npz --steps 5000 --checkpoint run.npz
```

`--steps` always means additional steps. On resume, the checkpoint owns the
grid, material, source, time step, and current step count. Backend options may
be changed, so a NumPy checkpoint can be resumed with, for example,
`--backend torch --device cuda`. With `--dtype auto`, restart preserves the
stored dtype; an explicit `--dtype` converts fields to that precision.

Checkpoint updates are atomic: the completed temporary archive replaces the
destination only after it has been written successfully. `--checkpoint-every`
requires `--checkpoint`, and the final state is always written even when the
requested step count is not an exact checkpoint interval.

## Visualization runner

`ionosphere-visualize` uses global simulation options followed by one required
subcommand:

```text
ionosphere-visualize [simulation options] COMMAND [render options]
```

| Command | Output |
|---|---|
| `surface` | Projected `Er` or `Hr` map |
| `section` | Great-circle distance–height `Er` section |
| `mesh` | Static 3-D topology or field surface |
| `animate` | GIF or MP4 field animation |
| `live` | Interactive advancing 3-D field |
| `traces` | One or more receiver time series |

Global `--steps` are warm-up steps performed before rendering or trace
recording. Options after the subcommand belong to that output mode. Show
subcommand-specific help by placing `--help` after its name:

```bash
uv run --extra visualization ionosphere-visualize surface --help
uv run --extra visualization ionosphere-visualize animate --help
```

Angles are in degrees. Receiver altitude and visualization `--altitude-km`
values are in kilometres; source coordinates use the model's configured
default altitude because the visualization runner exposes only source latitude
and longitude.

## Exit behavior

Invalid grids, unsupported backend/device/dtype combinations, unstable time
steps, and unresolved required arguments terminate with a nonzero status and a
diagnostic message. Normal runs print the selected mesh, backend, time step,
memory use, and field maxima.
