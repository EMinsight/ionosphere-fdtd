"""Surface-column ownership and halo plans for distributed FDTD meshes."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .mesh import FloatArray, GeodesicMesh, IntArray


@dataclass(frozen=True, slots=True)
class FieldHalo:
    """Global entity indices exchanged with one peer in the two field phases."""

    peer_rank: int
    er_vertices: IntArray
    et_edges: IntArray
    hr_faces: IntArray
    ht_edges: IntArray

    def __post_init__(self) -> None:
        for values in (
            self.er_vertices,
            self.et_edges,
            self.hr_faces,
            self.ht_edges,
        ):
            values.setflags(write=False)


@dataclass(frozen=True, slots=True)
class RankSurfacePartition:
    """Owned surface columns and peer-specific send/receive indices."""

    rank: int
    owned_vertices: IntArray
    owned_edges: IntArray
    owned_faces: IntArray
    ghost_vertices: IntArray
    ghost_edges: IntArray
    ghost_faces: IntArray
    receive_halos: tuple[FieldHalo, ...]
    send_halos: tuple[FieldHalo, ...]

    def __post_init__(self) -> None:
        for values in (
            self.owned_vertices,
            self.owned_edges,
            self.owned_faces,
            self.ghost_vertices,
            self.ghost_edges,
            self.ghost_faces,
        ):
            values.setflags(write=False)


@dataclass(frozen=True, slots=True)
class SurfacePartition:
    """Complete entity ownership and communication plan for one mesh."""

    face_owner: IntArray
    edge_owner: IntArray
    vertex_owner: IntArray
    face_costs: FloatArray
    part_capacities: FloatArray
    ranks: tuple[RankSurfacePartition, ...]

    def __post_init__(self) -> None:
        for values in (
            self.face_owner,
            self.edge_owner,
            self.vertex_owner,
            self.face_costs,
            self.part_capacities,
        ):
            values.setflags(write=False)

    @property
    def n_parts(self) -> int:
        return len(self.ranks)


@dataclass(frozen=True, slots=True)
class PartitionValidation:
    """Load and communication diagnostics for a surface partition."""

    normalized_face_loads: tuple[float, ...]
    relative_face_load_imbalance: float
    cut_edges: int
    halo_values_per_radial_column: int


def partition_surface_mesh(
    mesh: GeodesicMesh,
    *,
    seed_directions: FloatArray | None = None,
    part_capacities: FloatArray | None = None,
    face_costs: FloatArray | None = None,
) -> SurfacePartition:
    """Split one closed mesh into two connected surface-column domains.

    Adaptive leaf faces are costed directly, so refinement density contributes
    to the cut without assigning fixed coarse/fine GPU roles. The weighted
    great-circle cut separates the two seed directions and keeps each domain
    spatially compact. Entity ownership is then balanced deterministically,
    followed by exact Maxwell-dependency halo construction.
    """

    capacities = (
        np.ones(2, dtype=np.float64)
        if part_capacities is None
        else np.asarray(part_capacities, dtype=np.float64)
    )
    if capacities.shape != (2,) or not np.all(np.isfinite(capacities)):
        raise ValueError("part_capacities must contain two finite values")
    if np.any(capacities <= 0.0):
        raise ValueError("part capacities must be positive")

    costs = (
        np.ones(mesh.n_faces, dtype=np.float64)
        if face_costs is None
        else np.asarray(face_costs, dtype=np.float64)
    )
    if costs.shape != (mesh.n_faces,) or not np.all(np.isfinite(costs)):
        raise ValueError(f"face_costs must have shape ({mesh.n_faces},)")
    if np.any(costs <= 0.0):
        raise ValueError("face costs must be positive")

    if seed_directions is None:
        seeds = np.asarray(((1.0, 0.0, 0.0), (-1.0, 0.0, 0.0)))
    else:
        seeds = np.asarray(seed_directions, dtype=np.float64)
    if seeds.shape != (2, 3) or not np.all(np.isfinite(seeds)):
        raise ValueError("seed_directions must have shape (2, 3) and be finite")
    norms = np.linalg.norm(seeds, axis=1)
    if np.any(norms == 0.0):
        raise ValueError("partition seed directions must be non-zero")
    seeds = seeds / norms[:, None]
    axis = seeds[0] - seeds[1]
    axis_norm = float(np.linalg.norm(axis))
    if axis_norm <= 1.0e-12:
        raise ValueError("partition seed directions must be distinct")
    axis /= axis_norm

    scores = mesh.face_centers @ axis
    order = np.lexsort((np.arange(mesh.n_faces), -scores))
    cumulative = np.cumsum(costs[order])
    target = float(np.sum(costs) * capacities[0] / np.sum(capacities))
    split_candidates = np.arange(1, mesh.n_faces)
    split = int(
        split_candidates[
            np.argmin(np.abs(cumulative[split_candidates - 1] - target))
        ]
    )
    face_owner = np.ones(mesh.n_faces, dtype=np.int64)
    face_owner[order[:split]] = 0
    seed_faces = np.argmax(mesh.face_centers @ seeds.T, axis=0)
    if face_owner[seed_faces[0]] != 0 or face_owner[seed_faces[1]] != 1:
        raise ValueError("requested load split does not separate the seed regions")

    edge_owner = _balanced_edge_owners(mesh, face_owner, capacities)
    vertex_owner = _balanced_vertex_owners(mesh, face_owner, capacities)
    ranks = _build_rank_partitions(mesh, face_owner, edge_owner, vertex_owner)
    result = SurfacePartition(
        face_owner=np.array(face_owner, copy=True),
        edge_owner=edge_owner,
        vertex_owner=vertex_owner,
        face_costs=np.array(costs, copy=True),
        part_capacities=np.array(capacities, copy=True),
        ranks=ranks,
    )
    validate_surface_partition(mesh, result)
    return result


def validate_surface_partition(
    mesh: GeodesicMesh, partition: SurfacePartition
) -> PartitionValidation:
    """Validate ownership, connectivity, halo symmetry, and dependencies."""

    if partition.n_parts != 2:
        raise ValueError("surface partition currently requires exactly two parts")
    expected_shapes = (
        (partition.face_owner, mesh.n_faces, "face"),
        (partition.edge_owner, mesh.n_edges, "edge"),
        (partition.vertex_owner, mesh.n_vertices, "vertex"),
    )
    for owners, count, label in expected_shapes:
        if owners.shape != (count,) or np.any((owners < 0) | (owners >= 2)):
            raise ValueError(f"invalid {label} ownership")

    for rank in range(2):
        rank_plan = partition.ranks[rank]
        if rank_plan.rank != rank:
            raise ValueError("rank partitions are out of order")
        ownership = (
            (rank_plan.owned_vertices, partition.vertex_owner, "vertex"),
            (rank_plan.owned_edges, partition.edge_owner, "edge"),
            (rank_plan.owned_faces, partition.face_owner, "face"),
        )
        for indices, owners, label in ownership:
            if not np.array_equal(indices, np.flatnonzero(owners == rank)):
                raise ValueError(f"rank {rank} {label} ownership is inconsistent")
        _validate_connected_faces(mesh, partition.face_owner, rank)

        receive = _halo_by_peer(rank_plan.receive_halos)
        peer = 1 - rank
        received = receive.get(peer, _empty_halo(peer))
        sent_by_peer = _halo_by_peer(
            partition.ranks[peer].send_halos
        ).get(rank, _empty_halo(rank))
        for field in ("er_vertices", "et_edges", "hr_faces", "ht_edges"):
            if not np.array_equal(
                getattr(received, field), getattr(sent_by_peer, field)
            ):
                raise ValueError(f"rank {rank} {field} halo is not peer-symmetric")

        required_er = np.unique(mesh.edges[rank_plan.owned_edges].ravel())
        required_et = np.unique(mesh.face_edges[rank_plan.owned_faces].ravel())
        required_hr = np.unique(
            np.concatenate(
                (
                    mesh.edge_left_faces[rank_plan.owned_edges],
                    mesh.edge_right_faces[rank_plan.owned_edges],
                )
            )
        )
        owned_vertex_at_edge = np.any(
            partition.vertex_owner[mesh.edges] == rank, axis=1
        )
        required_ht = np.flatnonzero(owned_vertex_at_edge)
        requirements = (
            (required_er, partition.vertex_owner, received.er_vertices, "Er"),
            (required_et, partition.edge_owner, received.et_edges, "Et"),
            (required_hr, partition.face_owner, received.hr_faces, "Hr"),
            (required_ht, partition.edge_owner, received.ht_edges, "Ht"),
        )
        for required, owners, halo, label in requirements:
            expected = required[owners[required] != rank]
            if not np.array_equal(expected, halo):
                raise ValueError(f"{label} receive halo does not cover dependencies")
        if not np.array_equal(
            rank_plan.ghost_vertices, received.er_vertices
        ):
            raise ValueError("vertex ghost set is inconsistent")
        expected_ghost_edges = np.union1d(received.et_edges, received.ht_edges)
        if not np.array_equal(rank_plan.ghost_edges, expected_ghost_edges):
            raise ValueError("edge ghost set is inconsistent")
        if not np.array_equal(rank_plan.ghost_faces, received.hr_faces):
            raise ValueError("face ghost set is inconsistent")
    loads = tuple(
        float(np.sum(partition.face_costs[partition.face_owner == rank]))
        / float(partition.part_capacities[rank])
        for rank in range(2)
    )
    imbalance = abs(loads[0] - loads[1]) / (0.5 * (loads[0] + loads[1]))
    cut_edges = int(
        np.count_nonzero(
            partition.face_owner[mesh.edge_left_faces]
            != partition.face_owner[mesh.edge_right_faces]
        )
    )
    halo_values = sum(
        sum(
            len(getattr(halo, field))
            for field in ("er_vertices", "et_edges", "hr_faces", "ht_edges")
        )
        for rank in partition.ranks
        for halo in rank.receive_halos
    )
    return PartitionValidation(loads, float(imbalance), cut_edges, halo_values)


def _balanced_edge_owners(
    mesh: GeodesicMesh, face_owner: IntArray, capacities: FloatArray
) -> IntArray:
    left = face_owner[mesh.edge_left_faces]
    right = face_owner[mesh.edge_right_faces]
    owners = np.where(left == right, left, -1)
    boundary = np.flatnonzero(left != right)
    load = np.bincount(owners[owners >= 0], minlength=2).astype(np.float64)
    for edge in boundary:
        selected = int(np.argmin(load / capacities))
        owners[edge] = selected
        load[selected] += 1.0
    return np.asarray(owners, dtype=np.int64)


def _balanced_vertex_owners(
    mesh: GeodesicMesh, face_owner: IntArray, capacities: FloatArray
) -> IntArray:
    incidence_owner = np.repeat(face_owner, 3)
    incidence_vertex = mesh.faces.ravel()
    votes_zero = np.bincount(
        incidence_vertex,
        weights=incidence_owner == 0,
        minlength=mesh.n_vertices,
    )
    votes_one = np.bincount(
        incidence_vertex,
        weights=incidence_owner == 1,
        minlength=mesh.n_vertices,
    )
    owners = (votes_one > votes_zero).astype(np.int64)
    ties = np.flatnonzero(votes_zero == votes_one)
    owners[ties] = -1
    load = np.bincount(owners[owners >= 0], minlength=2).astype(np.float64)
    for vertex in ties:
        selected = int(np.argmin(load / capacities))
        owners[vertex] = selected
        load[selected] += 1.0
    return owners


def _build_rank_partitions(
    mesh: GeodesicMesh,
    face_owner: IntArray,
    edge_owner: IntArray,
    vertex_owner: IntArray,
) -> tuple[RankSurfacePartition, ...]:
    receives: list[dict[int, FieldHalo]] = []
    for rank in range(2):
        owned_faces = np.flatnonzero(face_owner == rank)
        owned_edges = np.flatnonzero(edge_owner == rank)
        owned_vertices = np.flatnonzero(vertex_owner == rank)
        needed_er = np.unique(mesh.edges[owned_edges].ravel())
        needed_et = np.unique(mesh.face_edges[owned_faces].ravel())
        needed_hr = np.unique(
            np.concatenate(
                (mesh.edge_left_faces[owned_edges], mesh.edge_right_faces[owned_edges])
            )
        )
        needed_ht = np.flatnonzero(
            np.any(vertex_owner[mesh.edges] == rank, axis=1)
        )
        peer = 1 - rank
        receives.append(
            {
                peer: FieldHalo(
                    peer,
                    needed_er[vertex_owner[needed_er] == peer],
                    needed_et[edge_owner[needed_et] == peer],
                    needed_hr[face_owner[needed_hr] == peer],
                    needed_ht[edge_owner[needed_ht] == peer],
                )
            }
        )

    ranks: list[RankSurfacePartition] = []
    for rank in range(2):
        peer = 1 - rank
        received = receives[rank][peer]
        peer_receive = receives[peer][rank]
        sent = FieldHalo(
            peer,
            np.array(peer_receive.er_vertices, copy=True),
            np.array(peer_receive.et_edges, copy=True),
            np.array(peer_receive.hr_faces, copy=True),
            np.array(peer_receive.ht_edges, copy=True),
        )
        ranks.append(
            RankSurfacePartition(
                rank=rank,
                owned_vertices=np.flatnonzero(vertex_owner == rank),
                owned_edges=np.flatnonzero(edge_owner == rank),
                owned_faces=np.flatnonzero(face_owner == rank),
                ghost_vertices=np.array(received.er_vertices, copy=True),
                ghost_edges=np.union1d(received.et_edges, received.ht_edges),
                ghost_faces=np.array(received.hr_faces, copy=True),
                receive_halos=(received,),
                send_halos=(sent,),
            )
        )
    return tuple(ranks)


def _validate_connected_faces(
    mesh: GeodesicMesh, face_owner: IntArray, rank: int
) -> None:
    selected = np.flatnonzero(face_owner == rank)
    visited = np.zeros(mesh.n_faces, dtype=np.bool_)
    stack = [int(selected[0])]
    visited[stack[0]] = True
    while stack:
        face = stack.pop()
        edges = mesh.face_edges[face]
        neighbours = np.concatenate(
            (mesh.edge_left_faces[edges], mesh.edge_right_faces[edges])
        )
        for neighbour in neighbours:
            index = int(neighbour)
            if face_owner[index] == rank and not visited[index]:
                visited[index] = True
                stack.append(index)
    if np.count_nonzero(visited & (face_owner == rank)) != len(selected):
        raise ValueError(f"rank {rank} face domain is disconnected")


def _halo_by_peer(halos: tuple[FieldHalo, ...]) -> dict[int, FieldHalo]:
    return {halo.peer_rank: halo for halo in halos}


def _empty_halo(peer_rank: int) -> FieldHalo:
    empty = np.empty(0, dtype=np.int64)
    return FieldHalo(peer_rank, empty, empty.copy(), empty.copy(), empty.copy())
