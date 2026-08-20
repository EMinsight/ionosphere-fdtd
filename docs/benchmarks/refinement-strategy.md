# Refinement and Time-Stepping Decision

## Decision

| Candidate | Decision | Reason |
|---|---|---|
| Static 2:1 radial h-refinement | Implemented | Reduces field/coefficient storage while retaining the existing conservative nonuniform stencil and one global leapfrog clock |
| Local time subcycling | Deferred | Does not reduce memory and would require flux-conservative coarse/fine time interfaces, extra NCCL schedules, and synchronized surface/plasma ADE histories |
| Dynamic AMR | Not selected | The media, source, receiver, coastline, ionosphere, and anomaly supports are known before a linear run; remeshing would invalidate mesh-bound data, partitions, checkpoints, and CUDA Graphs |

Static surface refinement and static radial refinement address the two justified
resolution requirements without introducing a moving interface. Dynamic AMR
would add interpolation error to a problem whose refinement indicators can be
computed from input data before the first step.

## Radial memory result

`build_refined_radial_grid()` starts from background cells, bisects every cell
intersecting a requested altitude interval until its target is met, and then
bisects neighbors until adjacent levels are 2:1 balanced. For a 0–100 km
atmosphere, 10 km background cells, and 1.25 km cells over 60–90 km, it creates
35 cells. A uniform grid with the same 1.25 km minimum step needs 80 cells.

On the accepted adaptive s7→s10 surface mesh (167,789 vertices, 503,361 edges,
335,574 faces), the four `float64` fields occupy approximately:

| Radial grid | Cells | Field storage |
|---|---:|---:|
| Static 2:1 refined | 35 | 0.399 GiB |
| Uniform 1.25 km | 80 | 0.905 GiB |

The static radial grid therefore removes about 56% of evolving-field storage
without reducing the CFL step relative to the equally resolved uniform grid.
Material coefficients see a similar radial scaling. Surface-impedance and
plasma ADE state are additional terms rather than part of this four-field
count.

## Why generic subcycling is deferred

The surface h-refinement is a conforming composite DEC mesh, not an overset
patch with an independent clock. Advancing fine faces more often would require
a temporally conservative exchange of every primal and dual interface flux.
The two-GPU implementation would also need multiple halo phases per coarse
step, and CUDA Graph capture would need one static graph for each schedule.

The cold-plasma path adds another constraint. For electron densities of
$10^8$, $10^9$, $10^{10}$, and $10^{11}\ \mathrm{m^{-3}}$, the explicit
$2/\omega_p$ limits are approximately 3.55 us, 1.12 us, 0.355 us, and 0.112 us.
If that limit dominates a real case, a local implicit or exponential coupled
`E–J` solve is a more direct next optimization than generic Maxwell
subcycling. It should be implemented only with an energy/passivity proof and a
measured end-to-end speedup.

## Acceptance evidence

Pytest verifies exact domain closure, requested interval resolution, overlapping
region priority, 2:1 balance, rejection of larger jumps, and 1,000 steps at the
full CFL limit without growth. The nonuniform radial adjoint and convergence
tests already cover the underlying solver stencil.
