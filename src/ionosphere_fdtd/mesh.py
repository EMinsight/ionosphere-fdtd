"""Icosahedral geodesic mesh and its triangular/dual-cell geometry.

The triangular primal mesh supports the TE-r plane.  Its dual cells support
the TM-r plane and have five sides at the twelve original icosahedron
vertices and six sides everywhere else.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


@dataclass(frozen=True, slots=True)
class GeodesicMesh:
    """Topology and unit-sphere metric terms for a geodesic mesh."""

    vertices: FloatArray
    faces: IntArray
    edges: IntArray
    face_edges: IntArray
    face_edge_signs: IntArray
    edge_left_faces: IntArray
    edge_right_faces: IntArray
    face_centers: FloatArray
    primal_edge_angles: FloatArray
    dual_edge_angles: FloatArray
    face_solid_angles: FloatArray
    dual_cell_solid_angles: FloatArray
    vertex_degree: IntArray
    subdivision: int

    def __post_init__(self) -> None:
        # ``frozen=True`` protects attribute bindings but not array contents.
        # Geometry and topology are coupled through precomputed Hodge factors,
        # so partial mutation would invalidate the discrete Maxwell operator.
        for values in (
            self.vertices,
            self.faces,
            self.edges,
            self.face_edges,
            self.face_edge_signs,
            self.edge_left_faces,
            self.edge_right_faces,
            self.face_centers,
            self.primal_edge_angles,
            self.dual_edge_angles,
            self.face_solid_angles,
            self.dual_cell_solid_angles,
            self.vertex_degree,
        ):
            values.setflags(write=False)

    @property
    def n_vertices(self) -> int:
        return int(self.vertices.shape[0])

    @property
    def n_edges(self) -> int:
        return int(self.edges.shape[0])

    @property
    def n_faces(self) -> int:
        return int(self.faces.shape[0])

    def edge_midpoints(self) -> FloatArray:
        points = self.vertices[self.edges].sum(axis=1)
        return _normalize(points)

    def edge_diamond_solid_angles(self) -> FloatArray:
        """Return the disjoint primal-face area associated with each edge."""

        tail = self.vertices[self.edges[:, 0]]
        head = self.vertices[self.edges[:, 1]]
        left = self.face_centers[self.edge_left_faces]
        right = self.face_centers[self.edge_right_faces]
        return _spherical_triangle_area(tail, head, left) + _spherical_triangle_area(
            tail, head, right
        )

    def edge_diamond_quadrant_solid_angles(self) -> FloatArray:
        """Return the four spherical support areas around every edge midpoint."""

        tail = self.vertices[self.edges[:, 0]]
        head = self.vertices[self.edges[:, 1]]
        midpoint = self.edge_midpoints()
        left = self.face_centers[self.edge_left_faces]
        right = self.face_centers[self.edge_right_faces]
        return np.column_stack(
            (
                _spherical_triangle_area(midpoint, tail, left),
                _spherical_triangle_area(midpoint, left, head),
                _spherical_triangle_area(midpoint, head, right),
                _spherical_triangle_area(midpoint, right, tail),
            )
        )

    def dual_cell_wedge_quadrature(
        self,
        vertex_indices: IntArray,
        edge_indices: IntArray,
    ) -> tuple[FloatArray, FloatArray]:
        """Return one area-weighted quadrature point per dual-cell wedge.

        Each requested vertex-edge incidence defines the spherical triangle
        bounded by the primal vertex and the circumcenters on either side of
        the edge. These disjoint wedges exactly partition every polygonal dual
        cell. The normalized triangle centroid is the quadrature direction and
        the exact spherical triangle area is its integration weight.
        """

        vertices = np.asarray(vertex_indices, dtype=np.int64)
        edges = np.asarray(edge_indices, dtype=np.int64)
        if vertices.ndim != 1 or edges.shape != vertices.shape:
            raise ValueError("dual-cell wedge indices must be matching 1-D arrays")
        if np.any(vertices < 0) or np.any(vertices >= self.n_vertices):
            raise ValueError("dual-cell wedge vertex index is out of bounds")
        if np.any(edges < 0) or np.any(edges >= self.n_edges):
            raise ValueError("dual-cell wedge edge index is out of bounds")
        if np.any(~np.any(self.edges[edges] == vertices[:, None], axis=1)):
            raise ValueError("dual-cell wedge vertex must be incident to its edge")

        vertex_points = self.vertices[vertices]
        left = self.face_centers[self.edge_left_faces[edges]]
        right = self.face_centers[self.edge_right_faces[edges]]
        directions = _normalize(vertex_points + left + right)
        areas = _spherical_triangle_area(vertex_points, left, right)
        return directions, areas

    def face_circulation(self, edge_values: FloatArray) -> FloatArray:
        """Counter-clockwise circulation around every primal triangle."""

        selected = edge_values[self.face_edges]
        signs = self.face_edge_signs.astype(edge_values.dtype, copy=False)
        while signs.ndim < selected.ndim:
            signs = signs[..., None]
        return np.sum(selected * signs, axis=1)

    def dual_cell_circulation(self, dual_edge_values: FloatArray) -> FloatArray:
        """Counter-clockwise circulation around every polygonal dual cell.

        A positive dual-edge value points from the right primal face to the
        left primal face.  With that convention it contributes positively to
        the cell at the tail of the corresponding primal edge.
        """

        output_shape = (self.n_vertices,) + dual_edge_values.shape[1:]
        result = np.zeros(output_shape, dtype=dual_edge_values.dtype)
        np.add.at(result, self.edges[:, 0], dual_edge_values)
        np.add.at(result, self.edges[:, 1], -dual_edge_values)
        return result

    def edge_difference(self, vertex_values: FloatArray) -> FloatArray:
        """Head-minus-tail difference along oriented primal edges."""

        return vertex_values[self.edges[:, 1]] - vertex_values[self.edges[:, 0]]

    def dual_edge_difference(self, face_values: FloatArray) -> FloatArray:
        """Left-minus-right difference across oriented primal edges."""

        return face_values[self.edge_left_faces] - face_values[self.edge_right_faces]


def build_geodesic_mesh(
    subdivision: int = 2,
    relaxations: int = 0,
    orientation: str = "polar",
    optimization_steps: int = 0,
) -> GeodesicMesh:
    """Build a recursively bisected icosahedral mesh on the unit sphere.

    ``subdivision=0`` gives 12 dual cells; each increment quarters every
    primal triangular face.  Thus the dual-cell count is
    ``10 * 4**subdivision + 2``.  Small MacBook runs normally use levels 1-2;
    level 3 gives the 642-cell grid shown in the cited papers.  The default
    orientation places an antipodal pair of pentagonal cells at the geographic
    poles; ``native`` retains the unrotated Cartesian icosahedron.
    """

    if subdivision < 0:
        raise ValueError("subdivision must be non-negative")
    if relaxations < 0:
        raise ValueError("relaxations must be non-negative")
    if optimization_steps < 0:
        raise ValueError("optimization_steps must be non-negative")
    if orientation not in {"native", "polar"}:
        raise ValueError("orientation must be 'native' or 'polar'")

    vertices, faces = _subdivided_icosahedron(subdivision, orientation)
    for _ in range(relaxations):
        vertices = _relax(vertices, faces)
    if optimization_steps:
        vertices = _optimize_edge_lengths(vertices, faces, optimization_steps)
    return _assemble_geodesic_mesh(vertices, faces, subdivision)


def build_geodesic_mesh_from_vertices(
    subdivision: int,
    vertices: FloatArray,
    *,
    orientation: str = "polar",
) -> GeodesicMesh:
    """Build the standard topology using externally optimized coordinates.

    The coordinates must correspond, in the original vertex order, to the
    recursively subdivided icosahedron at ``subdivision``. Small radial drift
    introduced by mesh-file serialization is normalized away, but inputs that
    are not already on the unit sphere are rejected.
    """

    if subdivision < 0:
        raise ValueError("subdivision must be non-negative")
    if orientation not in {"native", "polar"}:
        raise ValueError("orientation must be 'native' or 'polar'")
    _, faces = _subdivided_icosahedron(subdivision, orientation)
    coordinates = np.asarray(vertices, dtype=np.float64)
    expected_shape = (10 * 4**subdivision + 2, 3)
    if coordinates.shape != expected_shape:
        raise ValueError(
            f"optimized vertices must have shape {expected_shape}, "
            f"got {coordinates.shape}"
        )
    if not np.all(np.isfinite(coordinates)):
        raise ValueError("optimized vertices must be finite")
    radii = np.linalg.norm(coordinates, axis=1)
    if not np.allclose(radii, 1.0, rtol=0.0, atol=1.0e-7):
        raise ValueError("optimized vertices must lie on the unit sphere")
    return _assemble_geodesic_mesh(
        coordinates / radii[:, None],
        faces,
        subdivision,
        require_well_centered=True,
    )


def _subdivided_icosahedron(
    subdivision: int, orientation: str
) -> tuple[FloatArray, IntArray]:
    vertices, faces = _icosahedron()
    if orientation == "polar":
        vertices = _polar_orientation(vertices)
    for _ in range(subdivision):
        vertices, faces = _subdivide(vertices, faces)
    return vertices, faces


def _assemble_geodesic_mesh(
    vertices: FloatArray,
    faces: IntArray,
    subdivision: int,
    *,
    require_well_centered: bool = False,
) -> GeodesicMesh:
    faces = _orient_faces(vertices, faces)

    face_centers = _spherical_face_centers(vertices, faces)
    (
        edges,
        face_edges,
        face_edge_signs,
        left_faces,
        right_faces,
    ) = _build_edges(faces)

    primal_angles = _arc_length(vertices[edges[:, 0]], vertices[edges[:, 1]])
    dual_angles = _arc_length(face_centers[left_faces], face_centers[right_faces])
    face_areas = _spherical_triangle_area(
        vertices[faces[:, 0]], vertices[faces[:, 1]], vertices[faces[:, 2]]
    )
    dual_areas, degree = _dual_geometry(
        vertices,
        face_centers,
        edges,
        left_faces,
        right_faces,
    )

    if not np.all(degree >= 5):
        raise RuntimeError("invalid closed geodesic topology")
    if not np.all(np.isfinite(primal_angles)) or not np.all(primal_angles > 0.0):
        raise ValueError("geodesic mesh contains degenerate primal edges")
    if not np.all(np.isfinite(dual_angles)) or not np.all(dual_angles > 0.0):
        raise ValueError("geodesic mesh contains degenerate dual edges")
    if not np.all(np.isfinite(face_areas)) or not np.all(face_areas > 0.0):
        raise ValueError("geodesic mesh contains degenerate primal faces")
    if not np.all(np.isfinite(dual_areas)) or not np.all(dual_areas > 0.0):
        raise ValueError("geodesic mesh contains degenerate dual cells")
    if require_well_centered:
        _validate_well_centered_faces(vertices, faces, face_centers)
    if not np.isclose(face_areas.sum(), 4.0 * np.pi, rtol=1e-11):
        raise RuntimeError("primal face areas do not cover the unit sphere")
    if not np.isclose(dual_areas.sum(), 4.0 * np.pi, rtol=1e-10):
        raise RuntimeError("dual cell areas do not cover the unit sphere")

    return GeodesicMesh(
        vertices=vertices,
        faces=faces,
        edges=edges,
        face_edges=face_edges,
        face_edge_signs=face_edge_signs,
        edge_left_faces=left_faces,
        edge_right_faces=right_faces,
        face_centers=face_centers,
        primal_edge_angles=primal_angles,
        dual_edge_angles=dual_angles,
        face_solid_angles=face_areas,
        dual_cell_solid_angles=dual_areas,
        vertex_degree=degree,
        subdivision=subdivision,
    )


def _normalize(values: FloatArray) -> FloatArray:
    return values / np.linalg.norm(values, axis=-1, keepdims=True)


def _icosahedron() -> tuple[FloatArray, IntArray]:
    phi = (1.0 + np.sqrt(5.0)) / 2.0
    vertices = np.asarray(
        [
            (-1, phi, 0),
            (1, phi, 0),
            (-1, -phi, 0),
            (1, -phi, 0),
            (0, -1, phi),
            (0, 1, phi),
            (0, -1, -phi),
            (0, 1, -phi),
            (phi, 0, -1),
            (phi, 0, 1),
            (-phi, 0, -1),
            (-phi, 0, 1),
        ],
        dtype=np.float64,
    )
    faces = np.asarray(
        [
            (0, 11, 5),
            (0, 5, 1),
            (0, 1, 7),
            (0, 7, 10),
            (0, 10, 11),
            (1, 5, 9),
            (5, 11, 4),
            (11, 10, 2),
            (10, 7, 6),
            (7, 1, 8),
            (3, 9, 4),
            (3, 4, 2),
            (3, 2, 6),
            (3, 6, 8),
            (3, 8, 9),
            (4, 9, 5),
            (2, 4, 11),
            (6, 2, 10),
            (8, 6, 7),
            (9, 8, 1),
        ],
        dtype=np.int64,
    )
    return _normalize(vertices), _orient_faces(_normalize(vertices), faces)


def _polar_orientation(vertices: FloatArray) -> FloatArray:
    """Rotate one antipodal icosahedron pair onto the geographic poles.

    Vertex 5 becomes the North Pole, its antipode becomes the South Pole, and
    adjacent vertex 9 fixes the otherwise arbitrary axial rotation at 0°
    longitude.  Rotation preserves the mesh topology and every metric term.
    """

    source = vertices[5]
    target = np.asarray((0.0, 0.0, 1.0))
    axis = np.cross(source, target)
    sine = np.linalg.norm(axis)
    cosine = float(source @ target)
    skew = np.asarray(
        (
            (0.0, -axis[2], axis[1]),
            (axis[2], 0.0, -axis[0]),
            (-axis[1], axis[0], 0.0),
        )
    )
    rotation = np.eye(3) + skew + skew @ skew * ((1.0 - cosine) / sine**2)
    rotated = vertices @ rotation.T

    reference_longitude = np.arctan2(rotated[9, 1], rotated[9, 0])
    twist_cosine = np.cos(-reference_longitude)
    twist_sine = np.sin(-reference_longitude)
    twist = np.asarray(
        (
            (twist_cosine, -twist_sine, 0.0),
            (twist_sine, twist_cosine, 0.0),
            (0.0, 0.0, 1.0),
        )
    )
    return rotated @ twist.T


def _orient_faces(vertices: FloatArray, faces: IntArray) -> IntArray:
    result = faces.copy()
    a, b, c = (vertices[result[:, index]] for index in range(3))
    inward = np.einsum("ij,ij->i", np.cross(b - a, c - a), a + b + c) < 0.0
    result[inward, 1], result[inward, 2] = (
        result[inward, 2].copy(),
        result[inward, 1].copy(),
    )
    return result


def _subdivide(vertices: FloatArray, faces: IntArray) -> tuple[FloatArray, IntArray]:
    points = [row.copy() for row in vertices]
    midpoint_indices: dict[tuple[int, int], int] = {}

    def midpoint(first: int, second: int) -> int:
        key = (min(first, second), max(first, second))
        if key not in midpoint_indices:
            midpoint_indices[key] = len(points)
            points.append(_normalize((vertices[first] + vertices[second])[None, :])[0])
        return midpoint_indices[key]

    new_faces: list[tuple[int, int, int]] = []
    for first, second, third in faces:
        ab = midpoint(int(first), int(second))
        bc = midpoint(int(second), int(third))
        ca = midpoint(int(third), int(first))
        new_faces.extend(
            [
                (int(first), ab, ca),
                (int(second), bc, ab),
                (int(third), ca, bc),
                (ab, bc, ca),
            ]
        )
    return np.asarray(points), np.asarray(new_faces, dtype=np.int64)


def _relax(vertices: FloatArray, faces: IntArray) -> FloatArray:
    centers = _normalize(vertices[faces].sum(axis=1))
    accumulated = np.zeros_like(vertices)
    counts = np.zeros(vertices.shape[0], dtype=np.int64)
    for corner in range(3):
        np.add.at(accumulated, faces[:, corner], centers)
        np.add.at(counts, faces[:, corner], 1)
    return _normalize(accumulated / counts[:, None])


def _optimize_edge_lengths(
    vertices: FloatArray,
    faces: IntArray,
    steps: int,
) -> FloatArray:
    """Reduce spherical edge-length variance without changing the topology.

    This deterministic projected edge-quality optimizer is inspired by the
    Mesquite metrics cited by Simpson, Heikes, and Taflove. Each step descends
    the squared deviation from the global mean great-circle edge length and
    projects the displacement back onto the unit sphere. The twelve
    degree-five vertices remain fixed, preserving the base-icosahedron anchors
    and, in the polar orientation, the exact polar cell centers.

    It is intentionally separate from the legacy face-centroid relaxation.
    The paper does not publish the Mesquite objective, weights, or optimized
    coordinates, so callers must opt in to this reproducible approximation.
    """

    edges = _build_edges(faces)[0]
    degree = np.bincount(edges.ravel(), minlength=len(vertices))
    fixed = degree == 5
    result = vertices.copy()
    tails = edges[:, 0]
    heads = edges[:, 1]

    for _ in range(steps):
        tail_vertices = result[tails]
        head_vertices = result[heads]
        dot = np.clip(
            np.einsum("ij,ij->i", tail_vertices, head_vertices),
            -1.0,
            1.0,
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
        gradient[fixed] = 0.0
        result = _normalize(result - gradient)
        result[fixed] = vertices[fixed]

    return result


def _spherical_face_centers(vertices: FloatArray, faces: IntArray) -> FloatArray:
    a, b, c = (vertices[faces[:, index]] for index in range(3))
    centers = _normalize(np.cross(b - a, c - a))
    reverse = np.einsum("ij,ij->i", centers, a + b + c) < 0.0
    centers[reverse] *= -1.0
    return centers


def _build_edges(
    faces: IntArray,
) -> tuple[IntArray, IntArray, IntArray, IntArray, IntArray]:
    edge_lookup: dict[tuple[int, int], int] = {}
    edge_faces: list[list[tuple[int, int]]] = []
    face_edges = np.empty((faces.shape[0], 3), dtype=np.int64)
    face_signs = np.empty_like(face_edges)

    for face_index, (a, b, c) in enumerate(faces):
        for local_index, (tail, head) in enumerate(((a, b), (b, c), (c, a))):
            key = (min(int(tail), int(head)), max(int(tail), int(head)))
            sign = 1 if (int(tail), int(head)) == key else -1
            edge_index = edge_lookup.setdefault(key, len(edge_lookup))
            if edge_index == len(edge_faces):
                edge_faces.append([])
            edge_faces[edge_index].append((face_index, sign))
            face_edges[face_index, local_index] = edge_index
            face_signs[face_index, local_index] = sign

    if any(
        len(adjacent) != 2 or {sign for _, sign in adjacent} != {-1, 1}
        for adjacent in edge_faces
    ):
        raise RuntimeError("geodesic mesh is not a closed two-manifold")

    edges = np.asarray(list(edge_lookup), dtype=np.int64)
    left = np.empty(edges.shape[0], dtype=np.int64)
    right = np.empty_like(left)
    for edge_index, adjacent in enumerate(edge_faces):
        for face_index, sign in adjacent:
            if sign == 1:
                left[edge_index] = face_index
            else:
                right[edge_index] = face_index
    return edges, face_edges, face_signs, left, right


def _validate_well_centered_faces(
    vertices: FloatArray,
    faces: IntArray,
    face_centers: FloatArray,
) -> None:
    """Require every circumcenter to lie inside its spherical triangle.

    The FDTD Hodge stars store unsigned primal and dual minor-arc lengths.  That
    convention is valid only when adjacent circumcenters lie on opposite sides
    of their shared primal edge.  Requiring a well-centered triangulation is a
    deliberately stronger and inexpensive condition that guarantees that
    crossing for externally optimized coordinates.
    """

    triangles = vertices[faces]
    halfspace = np.column_stack(
        tuple(
            np.einsum(
                "ij,ij->i",
                np.cross(triangles[:, corner], triangles[:, (corner + 1) % 3]),
                face_centers,
            )
            for corner in range(3)
        )
    )
    tolerance = 64.0 * np.finfo(np.float64).eps
    invalid = np.flatnonzero(np.any(halfspace <= tolerance, axis=1))
    if len(invalid):
        raise ValueError(
            "optimized vertices must form a well-centered spherical mesh; "
            f"{len(invalid)} circumcenter(s) lie outside or on a primal face"
        )


def _arc_length(first: FloatArray, second: FloatArray) -> FloatArray:
    cross_norm = np.linalg.norm(np.cross(first, second), axis=1)
    dot = np.einsum("ij,ij->i", first, second)
    return np.arctan2(cross_norm, dot)


def _spherical_triangle_area(a: FloatArray, b: FloatArray, c: FloatArray) -> FloatArray:
    numerator = np.abs(np.einsum("ij,ij->i", a, np.cross(b, c)))
    denominator = (
        1.0
        + np.einsum("ij,ij->i", a, b)
        + np.einsum("ij,ij->i", b, c)
        + np.einsum("ij,ij->i", c, a)
    )
    return 2.0 * np.arctan2(numerator, denominator)


def _dual_geometry(
    vertices: FloatArray,
    face_centers: FloatArray,
    edges: IntArray,
    left_faces: IntArray,
    right_faces: IntArray,
) -> tuple[FloatArray, IntArray]:
    """Compute circumcentric dual areas from edge-local spherical wedges."""

    left_centers = face_centers[left_faces]
    right_centers = face_centers[right_faces]
    dual_area = np.zeros(vertices.shape[0], dtype=np.float64)
    for endpoint in range(2):
        vertex_indices = edges[:, endpoint]
        wedges = _spherical_triangle_area(
            vertices[vertex_indices], left_centers, right_centers
        )
        np.add.at(dual_area, vertex_indices, wedges)
    degree = np.bincount(edges.ravel(), minlength=len(vertices))
    return dual_area, degree
