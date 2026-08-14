# Visualization and Output

Install the visualization extra before using `ionosphere-visualize`:

```bash
uv sync --extra visualization
```

## Surface maps

```bash
uv run --extra visualization ionosphere-visualize \
  --subdivision 2 --radial-cells 24 --steps 1200 \
  surface --component er --scale symlog --output surface.png
```

Surface maps interpolate display values onto a regular longitude/latitude grid;
the solver fields are not modified. `er` and `hr` maps use symmetric color
limits about zero.

## Radial sections

```bash
uv run --extra visualization ionosphere-visualize \
  --subdivision 2 --radial-cells 24 --steps 1200 \
  section \
  --start-latitude 35.1595 --start-longitude 126.8526 \
  --end-latitude -35.1595 --end-longitude -53.1474 \
  --output section.png
```

## Mesh and interactive view

```bash
uv run --extra visualization ionosphere-visualize \
  --subdivision 2 --steps 0 \
  mesh --component topology --output mesh.png

uv run --extra visualization ionosphere-visualize \
  --subdivision 2 --radial-cells 24 --steps 0 \
  live --component er --steps-per-frame 10 --fps 20
```

In the live view, drag to rotate, use the wheel to zoom, and press `q` or close
the window to stop. Use `--no-earth-texture`, `--no-show-edges`, and
`--field-opacity` to simplify the display.

## Animations

```bash
uv run --extra visualization ionosphere-visualize \
  --subdivision 2 --radial-cells 24 --steps 1200 \
  animate --frames 120 --steps-per-frame 10 --fps 24 \
  --color-limit 4 --output field.mp4
```

Use an explicit color limit when comparing multiple runs. A nonzero warm-up is
usually needed before the first frame.

## Receiver traces

```bash
uv run --extra visualization ionosphere-visualize \
  --subdivision 2 --steps 40 \
  traces --trace-steps 4000 --sample-every 10 \
  --receiver 35.6762 139.6503 0 \
  --receiver 21.3069 -157.8583 0 \
  --output traces.png
```

Receiver buffers remain on the selected backend during stepping and are copied
to the host after recording. The solver also exposes
`record_er_observations()` and `record_h_observations()` for custom analyses.

## Python plotting API

```python
from ionosphere_fdtd import plot_surface_field, sample_radial_section

figure, axes, artist = plot_surface_field(
    simulation, "er", altitude_m=0.0, scale="symlog"
)
section = sample_radial_section(
    simulation, 35.1595, 126.8526, -35.1595, -53.1474
)
```

Call `simulation.to_numpy(field)` before passing backend-native arrays to other
host plotting or serialization libraries.
