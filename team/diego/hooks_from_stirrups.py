"""First-pass hook labels from stirrup outlines (geometry, no model).

A stirrup is a closed loop whose two ends bend inwards. On the outline's
centre line (skeleton) those ends are the two loose branches. For each branch:

- walk from the loose tip back to where it joins the loop;
- compare its direction with the loop at that point:
  tail almost parallel to a side  -> hook_90  (the tail runs along the side)
  tail at about 45 deg to the sides -> hook_135 (the tail points into the core);
- the tail's own outline (the stirrup mask around that branch) becomes the polygon.

Perspective, overlapping stirrups and hidden tips cause mistakes, so these are
pre-labels for a person to check, never final labels.

Tried on 20 ROI-1555 photos (27 Nov): it found fewer than a third of the
hooks, and about half of what it marked was right. Tails that lie along a side
merge with the loop in the outline, and occlusions look like loose ends. Kept
as an experiment, not used for labels. Hook labelling is paused; the team is
discussing a hook polygon of side + bend + tail (V for 135, L for 90) instead
of the tail alone.
"""
from __future__ import annotations

import cv2
import numpy as np
from skimage.morphology import skeletonize

N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _neighbours(sk: np.ndarray, y: int, x: int) -> list[tuple[int, int]]:
    h, w = sk.shape
    return [(y + dy, x + dx) for dy, dx in N8 if 0 <= y + dy < h and 0 <= x + dx < w and sk[y + dy, x + dx]]


def _walk(sk: np.ndarray, tip: tuple[int, int], max_len: int) -> tuple[list[tuple[int, int]], bool]:
    """From a loose tip along the skeleton until a junction. Returns the path and whether a junction was hit."""
    path, prev, cur = [tip], None, tip
    for _ in range(max_len):
        nb = [p for p in _neighbours(sk, *cur) if p != prev and p not in path[-3:]]
        if len(nb) != 1:
            return path, len(nb) >= 2
        prev, cur = cur, nb[0]
        path.append(cur)
    return path, False


def _direction(pts: list[tuple[int, int]]) -> np.ndarray:
    a = np.array(pts, dtype=np.float32)
    v = a[-1] - a[0]
    n = np.linalg.norm(v)
    return v / n if n else v


def _angle(u: np.ndarray, v: np.ndarray) -> float:
    """Angle between two lines (0-90 deg, direction ignored)."""
    c = abs(float(np.dot(u, v)))
    return float(np.degrees(np.arccos(min(1.0, c))))


def find_hooks(mask: np.ndarray, min_frac: float = 0.06, max_frac: float = 0.45) -> list[dict]:
    """Hooks of one stirrup mask. Each: {'cls': 'hook_90'|'hook_135', 'angle': deg, 'poly': (N,2) px}."""
    m = (mask > 0).astype(np.uint8)
    ys, xs = np.nonzero(m)
    if len(ys) < 50:
        return []
    size = float(np.hypot(xs.max() - xs.min(), ys.max() - ys.min()))
    sk = skeletonize(m.astype(bool))
    dist = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    thick = float(np.median(dist[sk])) if sk.any() else 2.0

    tips = [(int(y), int(x)) for y, x in zip(*np.nonzero(sk), strict=True) if len(_neighbours(sk, int(y), int(x))) == 1]
    cands = []
    for tip in tips:
        path, joined = _walk(sk, tip, int(size * max_frac) + 5)
        length = len(path)
        if not joined or length < size * min_frac:
            continue  # a stub of skeleton noise, or a bar end that never meets the loop
        junction = path[-1]
        tail_dir = _direction(path[: max(3, int(length * 0.8))])
        # the loop's directions at the junction: short walks along the other branches
        arms = []
        for nb in _neighbours(sk, *junction):
            if nb in path:
                continue
            arm, prev, cur = [junction, nb], junction, nb
            for _ in range(int(max(8, length * 0.6))):
                nxt = [p for p in _neighbours(sk, *cur) if p != prev and p not in arm]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]
                arm.append(cur)
            if len(arm) > 4:
                arms.append(_direction(arm))
        if not arms:
            continue
        ang = min(_angle(tail_dir, a) for a in arms)
        cls = "hook_90" if ang < 25 else "hook_135" if ang < 70 else None
        if cls is None:
            continue
        # tail outline: the stirrup mask around the tail's centre line, plus the bend
        band = np.zeros_like(m)
        for y, x in path:
            cv2.circle(band, (x, y), int(round(thick * 1.8)) + 1, 1, -1)
        band &= m
        cnts, _ = cv2.findContours(band, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            continue
        c = max(cnts, key=cv2.contourArea)
        poly = cv2.approxPolyDP(c, 1.0, True)[:, 0, :]
        if len(poly) >= 3:
            cands.append({"cls": cls, "angle": ang, "poly": poly, "len": length})
    # a stirrup has two ends: keep the two longest tails
    return sorted(cands, key=lambda d: -d["len"])[:2]
