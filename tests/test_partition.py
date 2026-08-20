import numpy as np
import pytest

from ionosphere_fdtd.adaptive_mesh import (
    SphericalRefinementRegion,
    build_adaptive_geodesic_mesh,
)
from ionosphere_fdtd.partition import (
    partition_surface_mesh,
    validate_surface_partition,
)


SOURCE = SphericalRefinementRegion(46.5, -90.9, 8.0, 3, 8.0, "source")
OIL = SphericalRefinementRegion(69.0, -156.0, 8.0, 3, 8.0, "oil")


@pytest.fixture(scope="module")
def partitioned_mesh():
    mesh = build_adaptive_geodesic_mesh(1, (SOURCE, OIL))
    partition = partition_surface_mesh(
        mesh,
        seed_directions=np.stack((SOURCE.direction(), OIL.direction())),
    )
    return mesh, partition


def test_partition_separates_refined_regions_and_balances_leaf_work(
    partitioned_mesh,
) -> None:
    mesh, partition = partitioned_mesh
    source_face = int(np.argmax(mesh.face_centers @ SOURCE.direction()))
    oil_face = int(np.argmax(mesh.face_centers @ OIL.direction()))
    validation = validate_surface_partition(mesh, partition)

    assert partition.face_owner[source_face] == 0
    assert partition.face_owner[oil_face] == 1
    assert validation.relative_face_load_imbalance <= 2.0 / mesh.n_faces
    assert validation.cut_edges > 0
    assert validation.halo_values_per_radial_column > 0


def test_partition_owns_every_entity_once_and_keeps_arrays_read_only(
    partitioned_mesh,
) -> None:
    mesh, partition = partitioned_mesh
    for owners, count in (
        (partition.vertex_owner, mesh.n_vertices),
        (partition.edge_owner, mesh.n_edges),
        (partition.face_owner, mesh.n_faces),
    ):
        assert owners.shape == (count,)
        assert set(np.unique(owners)) == {0, 1}
        assert not owners.flags.writeable
    for rank in partition.ranks:
        assert not np.intersect1d(rank.owned_vertices, rank.ghost_vertices).size
        assert not np.intersect1d(rank.owned_edges, rank.ghost_edges).size
        assert not np.intersect1d(rank.owned_faces, rank.ghost_faces).size
        for values in (
            rank.owned_vertices,
            rank.owned_edges,
            rank.owned_faces,
            rank.ghost_vertices,
            rank.ghost_edges,
            rank.ghost_faces,
        ):
            assert not values.flags.writeable


def test_partition_halos_are_peer_symmetric_and_dependency_minimal(
    partitioned_mesh,
) -> None:
    _, partition = partitioned_mesh
    first, second = partition.ranks
    first_receive = first.receive_halos[0]
    second_send = second.send_halos[0]
    second_receive = second.receive_halos[0]
    first_send = first.send_halos[0]

    for name in ("er_vertices", "et_edges", "hr_faces", "ht_edges"):
        np.testing.assert_array_equal(
            getattr(first_receive, name), getattr(second_send, name)
        )
        np.testing.assert_array_equal(
            getattr(second_receive, name), getattr(first_send, name)
        )


def test_partition_honors_asymmetric_capacity_target() -> None:
    mesh = build_adaptive_geodesic_mesh(1, (SOURCE, OIL))
    partition = partition_surface_mesh(
        mesh,
        seed_directions=np.stack((SOURCE.direction(), OIL.direction())),
        part_capacities=np.asarray((1.0, 1.5)),
    )
    counts = np.bincount(partition.face_owner, minlength=2)

    assert counts[1] > counts[0]
    assert counts[1] / counts[0] == pytest.approx(1.5, rel=0.04)


def test_partition_rejects_invalid_seeds_capacities_and_costs() -> None:
    mesh = build_adaptive_geodesic_mesh(1, (SOURCE, OIL))
    with pytest.raises(ValueError, match="distinct"):
        partition_surface_mesh(
            mesh, seed_directions=np.ones((2, 3), dtype=np.float64)
        )
    with pytest.raises(ValueError, match="capacities"):
        partition_surface_mesh(mesh, part_capacities=np.asarray((1.0, 0.0)))
    with pytest.raises(ValueError, match="face_costs"):
        partition_surface_mesh(mesh, face_costs=np.ones(mesh.n_faces - 1))
