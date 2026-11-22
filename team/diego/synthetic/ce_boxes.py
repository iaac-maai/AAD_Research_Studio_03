"""Boxes -> polygon outlines with Segment Anything (SAM 2.1), for Roboflow box-only sets.

A stirrup is a closed loop: its mask has a hole. YOLO-seg and Roboflow polygons
can't have holes, so each hole is joined to the outer edge by a thin cut
("keyhole"), giving one polygon that leaves the inside of the loop unlabelled.
"""
from __future__ import annotations

import cv2
import numpy as np


def _nearest(a: np.ndarray, b: np.ndarray) -> tuple[int, int]:
    """Indices (i in a, j in b) of the closest pair of points."""
    d = ((a[:, None, :].astype(np.float32) - b[None, :, :]) ** 2).sum(-1)
    i, j = np.unravel_index(int(d.argmin()), d.shape)
    return int(i), int(j)


def mask_to_polygon(mask: np.ndarray, min_area: float = 50.0, eps: float = 1.0) -> np.ndarray | None:
    """Largest component of a binary mask -> one polygon (N, 2) px, holes keyholed in."""
    m = (mask > 0.5).astype(np.uint8)
    contours, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if not contours or hier is None:
        return None
    hier = hier[0]
    outers = [i for i, h in enumerate(hier) if h[3] < 0]
    o = max(outers, key=lambda i: cv2.contourArea(contours[i]))
    if cv2.contourArea(contours[o]) < min_area:
        return None
    poly = cv2.approxPolyDP(contours[o], eps, True)[:, 0, :]
    holes = [i for i, h in enumerate(hier) if h[3] == o and cv2.contourArea(contours[i]) >= min_area]
    for h in sorted(holes, key=lambda i: -cv2.contourArea(contours[i])):
        hole = cv2.approxPolyDP(contours[h], eps, True)[:, 0, :]
        i, j = _nearest(poly, hole)
        hole = np.roll(hole, -j, axis=0)
        # walk the outer edge to i, jump in, go round the hole, come back out
        poly = np.concatenate([poly[: i + 1], hole, hole[:1], poly[i:]], axis=0)
    return poly


def fill_ratio(mask: np.ndarray, box) -> float:
    x1, y1, x2, y2 = (int(round(v)) for v in box)
    roi = mask[max(0, y1):y2, max(0, x1):x2]
    return float((roi > 0.5).mean()) if roi.size else 0.0


def yolo_line(cls: int, poly: np.ndarray, w: int, h: int) -> str:
    xy = (poly / np.array([w, h], dtype=np.float32)).clip(0, 1).reshape(-1)
    return f"{cls} " + " ".join(f"{v:.6f}" for v in xy)
