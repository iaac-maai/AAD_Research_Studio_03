"""The axis of a bar: a polyline down the middle of its mask, cut where the bar bends.

Feedback from Rasha and Nacho (26 Nov): segment the rebar, put a polyline on its axis, cut it by angle and measure
every segment. Training only has to find the steel; the measuring is geometry:

    mask ──► thin to a 1 px skeleton ──► longest path through it ──► straighten into segments
         └─► distance to the edge along the skeleton = half the bar's thickness

What comes out, in pixels (capture.record adds mm when the scale is known):
  axis_px       the corner points of the polyline, end to end
  segments_px   the length of each straight segment
  bends_deg     how far the bar turns at each corner: 90 for a 90 degree hook, 135 for a 135 degree hook
  thickness_px  the bar's thickness (twice the median distance from the axis to the edge)
  axis_length_px the length along the axis, ends included

Limits: angles and lengths are measured in the photo's plane. A bend seen at a slant looks sharper or
flatter than it is, so every bend is a reading to confirm, not a verdict.
"""

from __future__ import annotations

from collections import deque

import cv2
import numpy as np

MIN_BEND_DEG = 15.0  # turns smaller than this are noise along a straight bar, not a bend


def _thin(mask: np.ndarray) -> np.ndarray:
    """Zhang-Suen thinning: a 0/1 mask down to a 1 px wide skeleton."""
    img = np.pad((mask > 0).astype(np.uint8), 1)
    while True:
        changed = False
        for step in (0, 1):
            p2, p3, p4 = img[:-2, 1:-1], img[:-2, 2:], img[1:-1, 2:]
            p5, p6, p7 = img[2:, 2:], img[2:, 1:-1], img[2:, :-2]
            p8, p9, c = img[1:-1, :-2], img[:-2, :-2], img[1:-1, 1:-1]
            ring = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            b = sum(r.astype(np.int16) for r in ring[:8])
            a = sum(((ring[i] == 0) & (ring[i + 1] == 1)).astype(np.int16) for i in range(8))
            if step == 0:
                kill = (c == 1) & (b >= 2) & (b <= 6) & (a == 1) & (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else:
                kill = (c == 1) & (b >= 2) & (b <= 6) & (a == 1) & (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
            if kill.any():
                img[1:-1, 1:-1][kill] = 0
                changed = True
        if not changed:
            return img[1:-1, 1:-1]


def _longest_path(skel: np.ndarray) -> np.ndarray:
    """The longest route through a skeleton, as ordered (x, y) pixels: two breadth-first searches."""
    ys, xs = np.nonzero(skel)
    if len(xs) == 0:
        return np.empty((0, 2))
    index = {(x, y): i for i, (x, y) in enumerate(zip(xs.tolist(), ys.tolist(), strict=True))}
    pts = list(index)
    steps = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]

    def bfs(start):
        parent = {start: None}
        queue, last = deque([start]), start
        while queue:
            last = queue.popleft()
            x, y = pts[last]
            for dx, dy in steps:
                j = index.get((x + dx, y + dy))
                if j is not None and j not in parent:
                    parent[j] = last
                    queue.append(j)
        return last, parent

    far, _ = bfs(0)
    end, parent = bfs(far)
    path, k = [], end
    while k is not None:
        path.append(pts[k])
        k = parent[k]
    return np.array(path, dtype=np.float32)


def _turn(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """How far the direction turns at b, going a -> b -> c, in degrees (0 = straight on)."""
    u, v = b - a, c - b
    nu, nv = np.linalg.norm(u), np.linalg.norm(v)
    if nu == 0 or nv == 0:
        return 0.0
    return float(np.degrees(np.arccos(np.clip(np.dot(u, v) / (nu * nv), -1.0, 1.0))))


def measure(polygon, min_bend_deg: float = MIN_BEND_DEG) -> dict | None:
    """Axis polyline, segment lengths, bends and thickness of one mask outline, in pixels."""
    pts = np.asarray(polygon, dtype=np.float32).reshape(-1, 2)
    if len(pts) < 3:
        return None
    x0, y0 = np.floor(pts.min(0)) - 2
    w, h = (np.ceil(pts.max(0)) - [x0, y0] + 3).astype(int)
    if w * h > 25_000_000:  # a runaway outline: skip rather than stall the server
        return None
    mask = np.zeros((h, w), np.uint8)
    cv2.fillPoly(mask, [np.round(pts - [x0, y0]).astype(np.int32)], 1)
    if mask.sum() < 6:
        return None
    path = _longest_path(_thin(mask))
    if len(path) < 2:
        return None
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 3)
    half = float(np.median(dist[path[:, 1].astype(int), path[:, 0].astype(int)]))
    thickness = max(1.0, 2 * half)

    # straighten: keep the corners, then drop corners that barely turn
    corners = cv2.approxPolyDP(path.reshape(-1, 1, 2), max(2.0, 0.75 * thickness), False).reshape(-1, 2)
    corners = [c for c in corners]
    changed = True
    while changed and len(corners) > 2:
        changed = False
        turns = [_turn(corners[i - 1], corners[i], corners[i + 1]) for i in range(1, len(corners) - 1)]
        k = int(np.argmin(turns))
        if turns[k] < min_bend_deg:
            del corners[k + 1]
            changed = True
    corners = np.array(corners, dtype=np.float64)

    # the skeleton stops about half a thickness short of each end: put that back
    for end, nxt in ((0, 1), (-1, -2)):
        d = corners[end] - corners[nxt]
        n = np.linalg.norm(d)
        if n > 0:
            corners[end] = corners[end] + d / n * half
    corners += [x0, y0]

    segs = [float(np.linalg.norm(corners[i + 1] - corners[i])) for i in range(len(corners) - 1)]
    bends = [_turn(corners[i - 1], corners[i], corners[i + 1]) for i in range(1, len(corners) - 1)]
    return {"axis_px": [[round(float(x), 1), round(float(y), 1)] for x, y in corners],
            "segments_px": [round(s, 1) for s in segs],
            "bends_deg": [round(b, 1) for b in bends],
            "thickness_px": round(thickness, 1),
            "axis_length_px": round(sum(segs), 1)}


def tail_px(m: dict) -> float | None:
    """A hook's tail: the shorter of its two end segments (the other end runs on into the tie)."""
    segs = m.get("segments_px") or []
    if not segs:
        return None
    return min(segs[0], segs[-1]) if len(segs) > 1 else segs[0]
