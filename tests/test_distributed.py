from pathlib import Path

import numpy as np
import pytest

from ionosphere_fdtd.distributed import DistributedGeodesicFDTD
from ionosphere_fdtd.mesh import build_geodesic_mesh
from ionosphere_fdtd.partition import partition_surface_mesh
from ionosphere_fdtd.solver import GeodesicFDTD, SimulationConfig
from ionosphere_fdtd.sources import GaussianCurrent


def _distributed_worker(
    rank: int,
    rendezvous: str,
    output: str,
    backend: str = "gloo",
) -> None:
    import torch
    import torch.distributed as distributed

    if backend == "nccl":
        torch.cuda.set_device(rank)
    distributed.init_process_group(
        backend,
        init_method=f"file://{rendezvous}",
        rank=rank,
        world_size=2,
    )
    try:
        mesh = build_geodesic_mesh(0)
        partition = partition_surface_mesh(mesh)
        config = SimulationConfig(
            subdivision=0, radial_cells=4, courant_factor=0.2
        )
        source = GaussianCurrent(peak_current_a=1.0e6)
        simulation = DistributedGeodesicFDTD(
            partition,
            config=config,
            mesh=mesh,
            source=source,
            device="cpu" if backend == "gloo" else f"cuda:{rank}",
            dtype="float64",
        )
        radial_trace, tangential_trace = simulation.record_h_observations(
            np.asarray(((0,),), dtype=np.int64),
            np.asarray(((0,),), dtype=np.int64),
            np.asarray(((1.0,),)),
            np.asarray(((0,),), dtype=np.int64),
            np.asarray(((0,),), dtype=np.int64),
            np.asarray(((1.0,),)),
            8,
        )
        fields = {
            name: simulation.global_field(name)
            for name in ("er", "et", "hr", "ht")
        }
        memory = torch.tensor(
            (simulation.field_memory_bytes,),
            dtype=torch.int64,
            device=simulation.device,
        )
        gathered = [torch.zeros_like(memory) for _ in range(2)]
        distributed.all_gather(gathered, memory)
        if rank == 0:
            np.savez(
                output,
                **fields,
                local_field_memory_bytes=np.asarray(
                    [int(value.item()) for value in gathered]
                ),
                radial_trace=radial_trace,
                tangential_trace=tangential_trace,
            )
    finally:
        distributed.destroy_process_group()


def test_distributed_solver_requires_initialized_process_group() -> None:
    pytest.importorskip("torch")
    mesh = build_geodesic_mesh(0)
    partition = partition_surface_mesh(mesh)
    with pytest.raises(RuntimeError, match="initialize torch.distributed"):
        DistributedGeodesicFDTD(
            partition,
            config=SimulationConfig(subdivision=0, radial_cells=4),
            mesh=mesh,
            device="cpu",
        )


def test_two_rank_gloo_matches_single_torch_solver(tmp_path: Path) -> None:
    torch = pytest.importorskip("torch")
    if not torch.distributed.is_available():
        pytest.skip("torch.distributed is unavailable")
    rendezvous = tmp_path / "distributed-init"
    output = tmp_path / "distributed-fields.npz"
    torch.multiprocessing.start_processes(
        _distributed_worker,
        args=(str(rendezvous), str(output)),
        nprocs=2,
        join=True,
        start_method="spawn",
    )

    config = SimulationConfig(subdivision=0, radial_cells=4, courant_factor=0.2)
    reference = GeodesicFDTD(
        config,
        source=GaussianCurrent(peak_current_a=1.0e6),
        backend="torch",
        device="cpu",
        dtype="float64",
    )
    radial_trace, tangential_trace = reference.record_h_observations(
        np.asarray(((0,),), dtype=np.int64),
        np.asarray(((0,),), dtype=np.int64),
        np.asarray(((1.0,),)),
        np.asarray(((0,),), dtype=np.int64),
        np.asarray(((0,),), dtype=np.int64),
        np.asarray(((1.0,),)),
        8,
    )

    with np.load(output) as values:
        for name in ("er", "et", "hr", "ht"):
            np.testing.assert_allclose(
                values[name],
                reference.to_numpy(getattr(reference, name)),
                rtol=2.0e-13,
                atol=1.0e-24,
            )
        assert np.all(values["local_field_memory_bytes"] < reference.memory_bytes)
        np.testing.assert_allclose(
            values["radial_trace"], radial_trace, rtol=2.0e-13, atol=1.0e-24
        )
        np.testing.assert_allclose(
            values["tangential_trace"],
            tangential_trace,
            rtol=2.0e-13,
            atol=1.0e-24,
        )


def test_two_rank_nccl_matches_single_torch_solver(tmp_path: Path) -> None:
    torch = pytest.importorskip("torch")
    if (
        not torch.cuda.is_available()
        or torch.cuda.device_count() < 2
        or not torch.distributed.is_nccl_available()
    ):
        pytest.skip("two CUDA devices with NCCL are required")
    rendezvous = tmp_path / "nccl-init"
    output = tmp_path / "nccl-fields.npz"
    torch.multiprocessing.start_processes(
        _distributed_worker,
        args=(str(rendezvous), str(output), "nccl"),
        nprocs=2,
        join=True,
        start_method="spawn",
    )
    config = SimulationConfig(subdivision=0, radial_cells=4, courant_factor=0.2)
    reference = GeodesicFDTD(
        config,
        source=GaussianCurrent(peak_current_a=1.0e6),
        backend="torch",
        device="cpu",
        dtype="float64",
    )
    reference.step(8)

    with np.load(output) as values:
        for name in ("er", "et", "hr", "ht"):
            np.testing.assert_allclose(
                values[name],
                reference.to_numpy(getattr(reference, name)),
                rtol=2.0e-13,
                atol=1.0e-24,
            )
