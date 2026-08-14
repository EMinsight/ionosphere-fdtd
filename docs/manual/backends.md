# Backends and Performance

## Supported combinations

| Backend | Device | Dtypes | Notes |
|---|---|---|---|
| NumPy | CPU | `float32`, `float64` | Default is `float64` |
| PyTorch | CPU | `float32`, `float64` | Thread count is configurable |
| PyTorch | CUDA | `float32`, `float64` | `cuda:N` selects a specific GPU |
| PyTorch | Metal/MPS | `float32` | `float64` is unsupported |

`device="auto"` chooses CUDA, then MPS, then CPU. The `gpu` alias means CUDA.

## CLI examples

```bash
# NumPy CPU
uv run ionosphere --backend numpy --device cpu --dtype float64 --steps 1000

# PyTorch CPU with one intra-op thread
uv run --extra pytorch ionosphere \
  --backend torch --device cpu --torch-threads 1 --dtype float32 --steps 1000

# NVIDIA CUDA
uv run --extra pytorch ionosphere \
  --backend torch --device cuda --dtype float32 --steps 1000

# Apple Metal
uv run --extra pytorch ionosphere \
  --backend torch --device mps --dtype float32 --steps 1000
```

## Compilation

`--torch-compile` captures several static field steps in each PyTorch compiled
graph. The default `--torch-compile-chunk-size 8` turns, for example, 80 time
steps into 10 compiled calls instead of 80. A remainder shorter than the chunk
uses the compiled single-step graph, so every requested count is supported
without compiling a new graph shape.

Larger chunks reduce Python dispatch and accelerator launch overhead but
increase compilation time and graph size. Benchmark powers of two such as 4,
8, 16, and 32 on the target grid and device. Compilation has a significant
first-use cost and is intended for long runs with fixed shapes. Warm up with at
least one complete chunk before timing, and compare eager and compiled
execution as separate experiments.

## Choosing a backend

- Use NumPy CPU for installation checks, small grids, and transparent analysis.
- Benchmark NumPy and PyTorch CPU for small and medium grids; framework overhead
  can exceed the arithmetic saved by an accelerator.
- Use CUDA or MPS when the grid and step count are large enough to amortize
  kernel-launch overhead.
- Use `float64` for quantitative verification. Use `float32` when memory and
  throughput matter and the resulting numerical tolerance is acceptable.

## Benchmarking

Run the standardized backend matrix:

```bash
uv run --extra pytorch python -m benchmarks.backend_matrix \
  --subdivision 2 --radial-cells 16 \
  --steps 200 --warmup-steps 20 --repeats 3 \
  --dtype float32 --torch-compile --torch-compile-chunk-size 8
```

The benchmark excludes setup and transfers from the timed region and
synchronizes CUDA/MPS before stopping the clock. See
[the backend comparison](../benchmarks/backend-comparison.md) for the full
method and reference run.
