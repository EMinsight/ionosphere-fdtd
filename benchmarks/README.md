# Analytic-solution performance benchmarks

These source-checkout-only benchmarks measure representative A0--A4 runtime
workloads. They do not apply scientific acceptance thresholds and are not
collected by the default pytest run.

```bash
python -m benchmarks.analytic_solutions --repeats 3
python -m benchmarks.analytic_solutions --repeats 5 --output benchmark.json
```

Each repeat is an isolated workflow and includes setup as well as the reported
step count. A0, A1, A2, and A4 exercise production `GeodesicFDTD` paths. A3
times the periodic lossy auxiliary reference and is labeled accordingly; it
must not be compared as production spherical-solver throughput.
