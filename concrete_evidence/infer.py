"""The whole check on one photo: what the model server and `pipeline.py analyse` run.

photo -> markers (mm scale) -> YOLO
outlines -> records in mm -> check against the schedule + Eurocode 8 -> fix list.

Live video is for aiming; this is for one photo someone uploads. The model is
passed in (anything with Ultralytics' `predict`), so the server loads it once and
tests can pass a stand-in.
"""

from __future__ import annotations

import cv2
import numpy as np

from .capture import counts, records_from_result
from .check import run as run_checks
from .markers import DEFAULT_MARKER_MM, MarkerDetector

GREEN, RED = (60, 170, 60), (40, 40, 220)


def analyse(image: np.ndarray, schedule: dict, model, zone: str | None = None,
            face: str | None = None, conf: float = 0.25, imgsz: int = 640, marker_mm: float = DEFAULT_MARKER_MM,
            rename: dict | None = None) -> dict:
    """Check one BGR photo. Returns the check result, the detections and an annotated BGR image.

    rename: model class -> our class, e.g. {"stirrup": "tie"} for Diego's model.
    """
    markers = MarkerDetector(marker_mm)
    found = markers.find(image)
    mm = markers.mm_per_px(found)

    result = model.predict(image, imgsz=imgsz, conf=conf, max_det=500, retina_masks=True, verbose=False)[0]
    dets = records_from_result(result, mm)
    for i, d in enumerate(dets, 1):  # one photo, no tracking: number the pieces
        d["class"] = (rename or {}).get(d["class"], d["class"])
        if d["track_id"] is None:
            d["track_id"] = i
    capture = {"mm_per_px": mm, "markers_seen": sorted(found), "detections": dets}
    check = run_checks(capture, schedule, zone=zone, face=face)

    return {"check": check, "detections": dets, "counts": counts(dets), "markers_seen": sorted(found),
            "mm_per_px": mm and round(mm, 4), "annotated": annotate(image, dets, check, found)}


def annotate(image: np.ndarray, dets: list[dict], check: dict, found: dict) -> np.ndarray:
    """The photo with every piece outlined: red if a fault names it, green otherwise, and its number."""
    view = image.copy()
    bad = {t for c in check["checks"] if c["status"] == "fail" for t in c.get("track_ids", [])}
    for d in dets:
        colour = RED if d["track_id"] in bad else GREEN
        if d.get("polygon"):
            pts = np.asarray(d["polygon"], dtype=np.int32).reshape(-1, 1, 2)
            cv2.polylines(view, [pts], True, colour, 2)
        else:
            cx, cy = d["centre_px"]
            w, h = d["size_px"]
            cv2.rectangle(view, (int(cx - w / 2), int(cy - h / 2)), (int(cx + w / 2), int(cy + h / 2)), colour, 2)
        cx, cy = (int(v) for v in d["centre_px"])
        cv2.putText(view, str(d["track_id"]), (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colour, 2, cv2.LINE_AA)
    MarkerDetector.draw(view, found)
    return view
