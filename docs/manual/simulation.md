# Simulation Configuration

## Geometry

`SimulationConfig` controls the surface mesh, radial grid, time step, material
sampling, boundary condition, and geometry compatibility mode.

| Option | Default | Meaning |
|---|---:|---|
| `subdivision` | 2 | Recursive icosahedral surface refinement |
| `radial_cells` | 24 | Number of radial intervals |
| `minimum_altitude_m` | −100,000 | Lower radial boundary |
| `maximum_altitude_m` | 100,000 | Upper radial boundary |
| `earth_radius_m` | 6,371,000 | Reference Earth radius |
| `courant_factor` | 0.35 | Fraction of the conservative CFL limit |
| `time_step_s` | `None` | Explicit step, validated against the CFL limit |

The default radial nodes are uniform. Supply a strictly increasing tuple through
`radial_altitudes_m` for a custom grid; its length must be
`radial_cells + 1` and it must include both configured altitude bounds.

Smoothly graded nodes use `radial_grid_policy="smooth"`. Abrupt subgridding is
first-order at the transition and requires an explicit
`radial_grid_policy="allow-abrupt"` selection.

## Maxwell layout

For an oriented primal surface edge, the solver advances

```text
Ht += dt / mu0 * (d_surface Er - d_radial Et)
Hr -= dt / mu0 * curl_surface Et
Er  = Ca * Er + Cb * (curl_surface Ht - Jr)
Et  = Ca * Et + Cb * (d_dual Hr - d_radial Ht)
```

`geometry_mode="full-spherical"` uses

$$
\frac{1}{r}\frac{\partial(rE_t)}{\partial r}
\quad\text{and}\quad
\frac{1}{r}\frac{\partial(rH_t)}{\partial r}.
$$

`geometry_mode="thin-shell"` retains radius-independent radial differences for
paper compatibility. New physical simulations should normally use
`full-spherical`.

## Conductive integration

The default `loss_integration="exponential"` uses

$$
q=\frac{\sigma\Delta t}{\epsilon},\qquad
C_a=e^{-q},\qquad
C_b=\frac{\Delta t}{\epsilon}\frac{1-e^{-q}}{q},
$$

with the continuous $q=0$ limit. Use `trapezoidal` only when compatibility with
a legacy discretization is required.

## Boundaries and stability

The supported radial boundary is PEC. Odd tangential-electric ghost cells place
the tangential electric trace at zero on both radial boundaries. The solver
computes a geometry- and material-aware CFL limit and rejects an explicit
`time_step_s` above `courant_factor * cfl_time_step_limit_s`.

## Material support controls

| Option | Choices | Purpose |
|---|---|---|
| `radial_material_support` | `point`, `dual-cell` | Sample `Er` material at a vertex or average over its dual cell |
| `tangential_material_support` | `point`, `edge-diamond` | Sample `Et` material at an edge midpoint or average over its diamond |
| `horizontal_anomaly_mode` | `point`, `conservative-nearest` | Point-select or conservatively assign anomaly area |

The averaging modes are valuable at discontinuous coastlines and anomaly
boundaries but cost more during setup.

## Mesh controls

`mesh_orientation` accepts `polar` or `native`. `mesh_relaxations` and
`mesh_optimization_steps` alter coordinates while preserving topology. Do not
combine these controls with an explicitly supplied `GeodesicMesh`.

## Diagnostics and memory

```python
values = simulation.diagnostics()
print(values["cfl_time_step_limit_s"])
print(values["field_memory_bytes"])
print(simulation.persistent_backend_bytes)
```

`memory_bytes` counts the four evolving fields. `persistent_backend_bytes`
also includes material coefficients, geometry, and topology resident on the
selected backend.
