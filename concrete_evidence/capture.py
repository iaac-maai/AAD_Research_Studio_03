"""Pieces of the live view that don't need the model: stillness and records."""

from __future__ import annotations

import cv2
import numpy as np

from .frames import change, thumb


class Stillness:
    """True once the camera has been held still for `frames` frames in a row."""

    def __init__(self, frames: int = 8, threshold: float = 2.5):
        self.frames, self.threshold = frames, threshold
        self._prev: np.ndarray | None = None
        self.count = 0

    def update(self, frame: np.ndarray) -> tuple[bool, float | None]:
        gray = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        t = thumb(gray)
        diff = None if self._prev is None else change(t, self._prev)
        self._prev = t
        self.count = self.count + 1 if (diff is not None and diff < self.threshold) else 0
        return self.count >= self.frames, diff


def shape(polygon) -> dict | None:
    """Length, width and direction of a mask outline, from its smallest rotated rectangle.

    length_px is the long side (along the bar), width_px the short side (about the bar's
    diameter seen from above), angle_deg the long side's direction, 0-180 degrees.
    """
    pts = np.asarray(polygon, dtype=np.float32).reshape(-1, 2)
    if len(pts) < 3:
        return None
    (cx, cy), (w, h), a = cv2.minAreaRect(pts)
    if w < h:
        w, h, a = h, w, a + 90.0
    return {"length_px": round(float(w), 1), "width_px": round(float(h), 1),
            "angle_deg": round(float(a) % 180.0, 1), "axis_centre_px": [round(float(cx), 1), round(float(cy), 1)]}


def record(track_id, cls_name: str, conf: float, xyxy, mm_per_px: float | None, polygon=None) -> dict:
    """One detection as a plain dict: id, class, confidence, centre and size in px (and mm).

    With the mask outline (polygon), also its length, width and direction (see shape()),
    and the outline itself in whole pixels, so an app can draw it.
    """
    x1, y1, x2, y2 = (float(v) for v in xyxy)
    d = {"track_id": track_id, "class": cls_name, "conf": round(float(conf), 3),
         "centre_px": [round((x1 + x2) / 2, 1), round((y1 + y2) / 2, 1)],
         "size_px": [round(x2 - x1, 1), round(y2 - y1, 1)]}
    s = shape(polygon) if polygon is not None else None
    if s:
        d.update(s)
        d["polygon"] = [[round(float(x)), round(float(y))] for x, y in np.asarray(polygon).reshape(-1, 2)]
    if mm_per_px:
        d["centre_mm"] = [round(v * mm_per_px, 1) for v in d["centre_px"]]
        d["size_mm"] = [round(v * mm_per_px, 1) for v in d["size_px"]]
        if s:
            d["length_mm"] = round(s["length_px"] * mm_per_px, 1)
            d["width_mm"] = round(s["width_px"] * mm_per_px, 1)
    return d


def records_from_result(result, mm_per_px: float | None) -> list[dict]:
    """Detections from an Ultralytics result, as records (with mask shape when masks exist)."""
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return []
    ids = boxes.id.int().tolist() if boxes.id is not None else [None] * len(boxes)
    masks = getattr(result, "masks", None)
    polys = list(masks.xy) if masks is not None else [None] * len(boxes)
    return [record(ids[k], result.names[c], conf, xyxy, mm_per_px, polys[k])
            for k, (xyxy, c, conf) in enumerate(zip(boxes.xyxy.tolist(), boxes.cls.int().tolist(),
                                                     boxes.conf.tolist(), strict=True))]


def counts(records: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in records:
        out[r["class"]] = out.get(r["class"], 0) + 1
    return out
