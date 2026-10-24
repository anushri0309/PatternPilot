"""
Geometry utilities for pattern drafting:
- Perpendicular polygon offset (seam allowance)
- Notch placement helpers
- Point-on-segment interpolation
"""

import math


def _unit_vector(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return (0.0, 0.0)
    return (dx / length, dy / length)


def _line_intersection(p1, d1, p2, d2):
    """
    Intersect two infinite lines: p1 + t*d1 and p2 + u*d2.
    Returns (x, y) or None if parallel.
    """
    denom = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(denom) < 1e-9:
        return None
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    t = (dx * d2[1] - dy * d2[0]) / denom
    return (p1[0] + t * d1[0], p1[1] + t * d1[1])


def offset_polygon(points, allowances):
    """
    Offset a closed polygon outward by per-edge allowances.

    points: list of (x, y) in cm, closed implicitly (last connects to first)
    allowances: list of floats, one per edge. Edge i goes from points[i]
                to points[(i+1) % n]. Positive = outward.

    Returns: list of (x, y) offset vertices, same length as points.

    Note: This is a simple miter offset. It works for convex and mildly
    concave polygons (which all pattern pieces are). For highly concave
    shapes it can produce self-intersections, but pattern pieces do not
    have those at the seam-allowance scale.
    """
    n = len(points)
    if n < 3:
        return list(points)
    if len(allowances) != n:
        raise ValueError(f"allowances must have {n} entries, got {len(allowances)}")

    # Determine polygon orientation (signed area)
    area = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    ccw = area > 0

    # For each edge, compute its outward normal
    edge_normals = []
    for i in range(n):
        p1 = points[i]
        p2 = points[(i + 1) % n]
        ux, uy = _unit_vector(p1, p2)
        # Outward normal: rotate edge direction by -90 for CCW, +90 for CW
        if ccw:
            nx, ny = uy, -ux
        else:
            nx, ny = -uy, ux
        edge_normals.append((nx, ny))

    # Offset each vertex by intersecting the two adjacent offset lines
    result = []
    for i in range(n):
        prev_edge = (i - 1) % n
        curr_edge = i

        p_prev = points[i]
        n_prev = edge_normals[prev_edge]
        a_prev = allowances[prev_edge]

        p_curr = points[i]
        n_curr = edge_normals[curr_edge]
        a_curr = allowances[curr_edge]

        # Two offset lines through the vertex, direction = edge direction
        d_prev = _unit_vector(points[prev_edge], points[(prev_edge + 1) % n])
        d_curr = _unit_vector(points[curr_edge], points[(curr_edge + 1) % n])

        line1_p = (p_prev[0] + n_prev[0] * a_prev, p_prev[1] + n_prev[1] * a_prev)
        line2_p = (p_curr[0] + n_curr[0] * a_curr, p_curr[1] + n_curr[1] * a_curr)

        inter = _line_intersection(line1_p, d_prev, line2_p, d_curr)
        if inter is None:
            # Parallel edges (collinear) — just push out by average
            avg = (a_prev + a_curr) / 2
            result.append((p_curr[0] + n_curr[0] * avg,
                           p_curr[1] + n_curr[1] * avg))
        else:
            result.append(inter)

    return result


def point_on_segment(p1, p2, t):
    """Return the point at parameter t in [0,1] along segment p1->p2."""
    return (p1[0] + t * (p2[0] - p1[0]),
            p1[1] + t * (p2[1] - p1[1]))


def notch_marker(center, direction, depth=0.8, width=0.6):
    """
    Return three points forming a V-notch marker on a seam edge.
    center: (x, y) point on the stitching line
    direction: (dx, dy) unit vector pointing INTO the piece
    Returns: list of 3 (x, y) points
    """
    cx, cy = center
    dx, dy = direction
    # Perpendicular for the two arms of the V
    px, py = -dy, dx
    tip = (cx + dx * depth, cy + dy * depth)
    left = (cx - px * width, cy - py * width)
    right = (cx + px * width, cy + py * width)
    return [left, tip, right]