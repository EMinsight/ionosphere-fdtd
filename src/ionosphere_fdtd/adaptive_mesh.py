"""Static conforming local refinement for spherical geodesic meshes."""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass

import numpy as np
from numpy.typing import NDArray

from .mesh import (
    FloatArray,
    GeodesicMesh,
    IntArray,
    _arc_length,
    _build_edges,
    _normalize,
    _spherical_face_centers,
    build_geodesic_mesh,
    build_geodesic_mesh_from_topology,
)


@dataclass(frozen=True, slots=True)
class SphericalRefinementRegion:
    """A circular fine core with optional equal-width transition rings."""

    latitude_deg: float
    longitude_deg: float
    radius_deg: float
    target_subdivision: int
    transition_width_deg: float = 0.0
    label: str = ""

    def __post_init__(self) -> None:
        values = np.asarray(
            (
                self.latitude_deg,
                self.longitude_deg,
                self.radius_deg,
                self.transition_width_deg,
            ),
            dtype=np.float64,
        )
        if not np.all(np.isfinite(values)):
            raise ValueError("refinement-region coordinates and widths must be finite")
        if not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("refinement-region latitude must be in [-90, 90]")
        if not 0.0 < self.radius_deg <= 180.0:
            raise ValueError("refinement-region radius must be in (0, 180]")
        if not 0.0 <= self.transition_width_deg <= 180.0:
            raise ValueError("transition width must be in [0, 180]")
        if (
            isinstance(self.target_subdivision, bool)
            or not isinstance(self.target_subdivision, (int, np.integer))
            or self.target_subdivision < 0
        ):
            raise ValueError("target subdivision must be a non-negative integer")
        if not isinstance(self.label, str):
            raise ValueError("refinement-region label must be a string")

    def direction(self) -> FloatArray:
        """Return the unit Cartesian direction at the region center."""

        latitude = np.deg2rad(self.latitude_deg)
        longitude = np.deg2rad(self.longitude_deg)
        return np.asarray(
            (
                np.cos(latitude) * np.cos(longitude),
                np.cos(latitude) * np.sin(longitude),
                np.sin(latitude),
            )
        )


@dataclass(frozen=True, slots=True)
class AdaptiveMeshValidation:
    """Invariant measurements for a conforming adaptive spherical mesh."""

    maximum_adjacent_level_jump: int
    minimum_dual_edge_angle: float
    primal_area_error: float
    dual_area_error: float


def build_adaptive_geodesic_mesh(
    base_subdivision: int,
    regions: tuple[SphericalRefinementRegion, ...],
    *,
    orientation: str = "polar",
    relaxations_per_level: int = 2,
    optimization_steps_per_level: int = 1,
) -> GeodesicMesh:
    """Build one closed composite mesh with conforming local refinement.

    Marked faces receive red refinement. Their unmarked neighbours receive
    one- or two-edge transition triangulations, so every midpoint is shared
    and no hanging nodes remain. Repeating this operation produces multiple
    levels while keeping adjacent face levels within one. A projected Lloyd
    relaxation after each level restores a positive circumcentric Hodge star.
    """

    if (
        isinstance(base_subdivision, bool)
        or not isinstance(base_subdivision, (int, np.integer))
        or base_subdivision < 0
    ):
        raise ValueError("base subdivision must be a non-negative integer")
    if (
        isinstance(relaxations_per_level, bool)
        or not isinstance(relaxations_per_level, (int, np.integer))
        or relaxations_per_level < 1
    ):
        raise ValueError("relaxations_per_level must be a positive integer")
    if (
        isinstance(optimization_steps_per_level, bool)
        or not isinstance(optimization_steps_per_level, (int, np.integer))
        or optimization_steps_per_level < 0
    ):
        raise ValueError(
            "optimization_steps_per_level must be a non-negative integer"
        )
    if not isinstance(regions, tuple) or not all(
        isinstance(region, SphericalRefinementRegion) for region in regions
    ):
        raise ValueError("regions must be a tuple of SphericalRefinementRegion")

    base = build_geodesic_mesh(int(base_subdivision), orientation=orientation)
    active_regions = tuple(
        region
        for region in regions
        if region.target_subdivision > base_subdivision
    )
    if not active_regions:
        return base

    vertices = np.array(base.vertices, copy=True)
    faces = np.array(base.faces, copy=True)
    levels = np.full(len(faces), base_subdivision, dtype=np.int64)
    maximum_level = max(region.target_subdivision for region in active_regions)

    for _ in range(base_subdivision, maximum_level):
        desired = _desired_face_levels(vertices, faces, active_regions)
        marked = desired > levels
        if not np.any(marked):
            break
        previous_vertex_count = len(vertices)
        vertices, faces, levels = _refine_marked_faces(
            vertices, faces, levels, marked
        )
        new_vertices = np.arange(len(vertices)) >= previous_vertex_count
        transition_faces = np.any(new_vertices[faces], axis=1)
        movable = np.zeros(len(vertices), dtype=np.bool_)
        movable[np.unique(faces[transition_faces])] = True
        for _ in range(int(relaxations_per_level)):
            vertices = _relax_selected(vertices, faces, movable)
        if optimization_steps_per_level:
            vertices = _optimize_selected_edge_lengths(
                vertices,
                faces,
                movable,
                int(optimization_steps_per_level),
            )
        faces, levels = _enforce_local_delaunay(vertices, faces, levels)

    refinement_spec = {
        "algorithm": "conforming-red-transition-v2",
        "base_subdivision": int(base_subdivision),
        "orientation": orientation,
        "relaxations_per_level": int(relaxations_per_level),
        "optimization_steps_per_level": int(optimization_steps_per_level),
        "regions": [asdict(region) for region in regions],
    }
    mesh = build_geodesic_mesh_from_topology(
        vertices,
        faces,
        subdivision=int(base_subdivision),
        face_levels=levels,
        refinement_spec=refinement_spec,
        topology_kind="adaptive",
        normalize_vertices=False,
        require_well_centered=False,
    )
    validate_adaptive_mesh(mesh)
    return mesh


def validate_adaptive_mesh(mesh: GeodesicMesh) -> AdaptiveMeshValidation:
    """Validate 2:1 balance, area closure, and positive Hodge geometry."""

    if mesh.face_levels is None:
        raise ValueError("adaptive mesh validation requires face_levels")
    adjacent_jump = np.abs(
        mesh.face_levels[mesh.edge_left_faces]
        - mesh.face_levels[mesh.edge_right_faces]
    )
    maximum_jump = int(np.max(adjacent_jump, initial=0))
    if maximum_jump > 1:
        raise ValueError("adaptive mesh violates 2:1 face-level balance")

    tail = mesh.vertices[mesh.edges[:, 0]]
    head = mesh.vertices[mesh.edges[:, 1]]
    midpoint = _normalize(tail + head)
    left_normal = _normalize(np.cross(tail, head))
    left = mesh.face_centers[mesh.edge_left_faces]
    right = mesh.face_centers[mesh.edge_right_faces]
    left_coordinate = np.arctan2(
        np.einsum("ij,ij->i", left, left_normal),
        np.einsum("ij,ij->i", left, midpoint),
    )
    right_coordinate = np.arctan2(
        np.einsum("ij,ij->i", right, left_normal),
        np.einsum("ij,ij->i", right, midpoint),
    )
    signed_dual_angles = left_coordinate - right_coordinate
    minimum_dual_angle = float(np.min(signed_dual_angles))
    tolerance = 64.0 * np.finfo(np.float64).eps
    if minimum_dual_angle <= tolerance:
        raise ValueError("adaptive mesh has a non-positive circumcentric Hodge star")
    if not np.allclose(
        signed_dual_angles,
        mesh.dual_edge_angles,
        rtol=1.0e-12,
        atol=tolerance,
    ):
        raise ValueError("adaptive mesh dual-edge orientation is inconsistent")

    primal_error = float(abs(np.sum(mesh.face_solid_angles) - 4.0 * np.pi))
    dual_error = float(abs(np.sum(mesh.dual_cell_solid_angles) - 4.0 * np.pi))
    if primal_error > 1.0e-11 or dual_error > 1.0e-10:
        raise ValueError("adaptive mesh areas do not close on the sphere")
    edge_supports = mesh.edge_diamond_solid_angles()
    if np.any(edge_supports <= 0.0) or not np.isclose(
        np.sum(edge_supports), 4.0 * np.pi, rtol=0.0, atol=1.0e-10
    ):
        raise ValueError("adaptive edge supports are not positive and disjoint")
    return AdaptiveMeshValidation(
        maximum_adjacent_level_jump=maximum_jump,
        minimum_dual_edge_angle=minimum_dual_angle,
        primal_area_error=primal_error,
        dual_area_error=dual_error,
    )


def _desired_face_levels(
    vertices: FloatArray,
    faces: IntArray,
    regions: tuple[SphericalRefinementRegion, ...],
) -> IntArray:
    centers = _spherical_face_centers(vertices, faces)
    face_radius = np.max(
        _arc_length(
            np.repeat(centers, 3, axis=0),
            vertices[faces].reshape(-1, 3),
        ).reshape(-1, 3),
        axis=1,
    )
    desired = np.zeros(len(faces), dtype=np.int64)
    for region in regions:
        center_distance = np.arccos(
            np.clip(centers @ region.direction(), -1.0, 1.0)
        )
        effective_distance_deg = np.rad2deg(
            np.maximum(center_distance - face_radius, 0.0)
        )
        requested = np.full(len(faces), -1, dtype=np.int64)
        core = effective_distance_deg <= region.radius_deg
        requested[core] = region.target_subdivision
        if region.transition_width_deg > 0.0:
            outside = ~core
            rings = np.ceil(
                (effective_distance_deg[outside] - region.radius_deg)
                / region.transition_width_deg
            ).astype(np.int64)
            requested[outside] = region.target_subdivision - rings
        desired = np.maximum(desired, requested)
    return desired


def _refine_marked_faces(
    vertices: FloatArray,
    faces: IntArray,
    levels: IntArray,
    marked: NDArray[np.bool_],
) -> tuple[FloatArray, IntArray, IntArray]:
    points = [point.copy() for point in vertices]
    split_edges = {
        tuple(sorted((int(tail), int(head))))
        for face in faces[marked]
        for tail, head in (
            (face[0], face[1]),
            (face[1], face[2]),
            (face[2], face[0]),
        )
    }
    midpoint_indices: dict[tuple[int, int], int] = {}

    def midpoint(edge: tuple[int, int]) -> int:
        if edge not in midpoint_indices:
            midpoint_indices[edge] = len(points)
            points.append(_normalize(vertices[list(edge)].sum(axis=0)[None, :])[0])
        return midpoint_indices[edge]

    new_faces: list[tuple[int, int, int]] = []
    new_levels: list[int] = []
    for face, level in zip(faces, levels, strict=True):
        a, b, c = (int(value) for value in face)
        edges = (
            tuple(sorted((a, b))),
            tuple(sorted((b, c))),
            tuple(sorted((c, a))),
        )
        is_split = tuple(edge in split_edges for edge in edges)
        midpoints = tuple(
            midpoint(edge) if split else -1
            for edge, split in zip(edges, is_split, strict=True)
        )
        children = _transition_children((a, b, c), midpoints, is_split)
        new_faces.extend(children)
        child_level = int(level) + (1 if any(is_split) else 0)
        new_levels.extend([child_level] * len(children))
    return (
        np.asarray(points, dtype=np.float64),
        np.asarray(new_faces, dtype=np.int64),
        np.asarray(new_levels, dtype=np.int64),
    )


def _transition_children(
    face: tuple[int, int, int],
    midpoints: tuple[int, int, int],
    is_split: tuple[bool, bool, bool],
) -> list[tuple[int, int, int]]:
    a, b, c = face
    ab, bc, ca = midpoints
    split_count = sum(is_split)
    if split_count == 0:
        return [face]
    if split_count == 3:
        return [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
    if split_count == 1:
        if is_split[0]:
            return [(a, ab, c), (ab, b, c)]
        if is_split[1]:
            return [(b, bc, a), (bc, c, a)]
        return [(c, ca, b), (ca, a, b)]

    if not is_split[0]:
        x, y, z, xy, yz = b, c, a, bc, ca
    elif not is_split[1]:
        x, y, z, xy, yz = c, a, b, ca, ab
    else:
        x, y, z, xy, yz = a, b, c, ab, bc
    return [(y, yz, xy), (x, xy, z), (xy, yz, z)]


def _relax_selected(
    vertices: FloatArray,
    faces: IntArray,
    movable: NDArray[np.bool_],
) -> FloatArray:
    centers = _normalize(vertices[faces].sum(axis=1))
    accumulated = np.zeros_like(vertices)
    counts = np.zeros(len(vertices), dtype=np.int64)
    for corner in range(3):
        np.add.at(accumulated, faces[:, corner], centers)
        np.add.at(counts, faces[:, corner], 1)
    proposed = _normalize(accumulated / counts[:, None])
    result = np.array(vertices, copy=True)
    result[movable] = proposed[movable]
    return result


def _optimize_selected_edge_lengths(
    vertices: FloatArray,
    faces: IntArray,
    movable: NDArray[np.bool_],
    steps: int,
) -> FloatArray:
    edges = _build_edges(faces)[0]
    degree = np.bincount(edges.ravel(), minlength=len(vertices))
    selected = movable & (degree != 5)
    result = np.array(vertices, copy=True)
    tails = edges[:, 0]
    heads = edges[:, 1]
    for _ in range(steps):
        tail_vertices = result[tails]
        head_vertices = result[heads]
        dot = np.clip(
            np.einsum("ij,ij->i", tail_vertices, head_vertices), -1.0, 1.0
        )
        sine = np.linalg.norm(np.cross(tail_vertices, head_vertices), axis=1)
        lengths = np.arctan2(sine, dot)
        residual = lengths - float(np.mean(lengths))
        tail_gradient = (
            residual[:, None]
            * (dot[:, None] * tail_vertices - head_vertices)
            / sine[:, None]
        )
        head_gradient = (
            residual[:, None]
            * (dot[:, None] * head_vertices - tail_vertices)
            / sine[:, None]
        )
        gradient = np.zeros_like(result)
        np.add.at(gradient, tails, tail_gradient)
        np.add.at(gradient, heads, head_gradient)
        gradient /= degree[:, None]
        gradient -= np.einsum("ij,ij->i", gradient, result)[:, None] * result
        updated = _normalize(result - gradient)
        result[selected] = updated[selected]
    return result


def _enforce_local_delaunay(
    vertices: FloatArray,
    faces: IntArray,
    levels: IntArray,
) -> tuple[IntArray, IntArray]:
    """Apply deterministic Lawson flips until every dual edge is positive."""

    result = np.array(faces, dtype=np.int64, copy=True)
    result_levels = np.array(levels, dtype=np.int64, copy=True)
    adjacency: dict[tuple[int, int], list[int]] = {}

    def face_edges(face: IntArray) -> tuple[tuple[int, int], ...]:
        a, b, c = (int(value) for value in face)
        return (
            tuple(sorted((a, b))),
            tuple(sorted((b, c))),
            tuple(sorted((c, a))),
        )

    edges, _, _, left_faces, right_faces = _build_edges(result)
    for edge, left_face, right_face in zip(
        edges, left_faces, right_faces, strict=True
    ):
        adjacency[(int(edge[0]), int(edge[1]))] = [
            int(left_face),
            int(right_face),
        ]

    centers = _spherical_face_centers(vertices, result)
    tail = vertices[edges[:, 0]]
    head = vertices[edges[:, 1]]
    midpoint = _normalize(tail + head)
    left_normal = _normalize(np.cross(tail, head))
    left_centers = centers[left_faces]
    right_centers = centers[right_faces]
    signed_dual = np.arctan2(
        np.einsum("ij,ij->i", left_centers, left_normal),
        np.einsum("ij,ij->i", left_centers, midpoint),
    ) - np.arctan2(
        np.einsum("ij,ij->i", right_centers, left_normal),
        np.einsum("ij,ij->i", right_centers, midpoint),
    )
    tolerance = 256.0 * np.finfo(np.float64).eps
    bad_edges = edges[signed_dual <= tolerance]
    work = deque((int(edge[0]), int(edge[1])) for edge in bad_edges)
    queued = set(work)
    maximum_flips = max(1, 10 * len(adjacency))
    flips = 0

    def enqueue(edge: tuple[int, int]) -> None:
        if edge not in queued:
            queued.add(edge)
            work.append(edge)

    while work:
        edge = work.popleft()
        queued.remove(edge)
        adjacent = adjacency.get(edge)
        if adjacent is None or len(adjacent) != 2:
            continue
        first_index, second_index = adjacent
        a, b = edge
        first = result[first_index]
        second = result[second_index]

        def follows(face: IntArray, tail: int, head: int) -> bool:
            return any(
                int(face[corner]) == tail
                and int(face[(corner + 1) % 3]) == head
                for corner in range(3)
            )

        if follows(first, b, a):
            first_index, second_index = second_index, first_index
            first, second = second, first
        if not follows(first, a, b) or not follows(second, b, a):
            raise RuntimeError("adaptive face orientations are inconsistent")
        c = next(int(value) for value in first if value not in edge)
        d = next(int(value) for value in second if value not in edge)

        centers = _spherical_face_centers(
            vertices, np.asarray((first, second), dtype=np.int64)
        )
        midpoint = _normalize((vertices[a] + vertices[b])[None, :])[0]
        left_normal = _normalize(
            np.cross(vertices[a], vertices[b])[None, :]
        )[0]
        coordinates = np.arctan2(
            centers @ left_normal,
            centers @ midpoint,
        )
        if coordinates[0] - coordinates[1] > tolerance:
            continue

        replacement_edge = tuple(sorted((c, d)))
        if replacement_edge in adjacency:
            continue
        old_edges = set(face_edges(first)) | set(face_edges(second))
        for old_edge in old_edges:
            neighbours = adjacency[old_edge]
            neighbours[:] = [
                index
                for index in neighbours
                if index not in {first_index, second_index}
            ]
            if not neighbours:
                del adjacency[old_edge]

        result[first_index] = (c, d, b)
        result[second_index] = (d, c, a)
        replacement_level = max(
            int(result_levels[first_index]), int(result_levels[second_index])
        )
        result_levels[first_index] = replacement_level
        result_levels[second_index] = replacement_level
        changed_edges = set(face_edges(result[first_index])) | set(
            face_edges(result[second_index])
        )
        for changed_edge in changed_edges:
            neighbours = adjacency.setdefault(changed_edge, [])
            for index in (first_index, second_index):
                if changed_edge in face_edges(result[index]) and index not in neighbours:
                    neighbours.append(index)
            enqueue(changed_edge)
        if any(len(adjacency[changed_edge]) != 2 for changed_edge in changed_edges):
            raise RuntimeError("Delaunay flip broke the closed mesh topology")
        flips += 1
        if flips > maximum_flips:
            raise RuntimeError("adaptive Delaunay edge flips did not converge")

    return result, result_levels
