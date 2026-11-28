"""Blur faces before a frame leaves the phone or laptop.

Site photos show workers. Under GDPR a face is personal data, so every frame
we save, label or upload has faces blurred first (ConRebSeg does the same).

Detector: YuNet (OpenCV's FaceDetectorYN), a small face detector from
opencv_zoo, MIT licence, about 230 KB. OpenCV 5 no longer ships the old Haar
cascades. Fetch the model once:

    python -m concrete_evidence.privacy --fetch

It goes to models/ in the repo (gitignored), or to $CE_MODELS if set.
If the model is missing, blur_faces raises instead of saving a frame unblurred.
It can still miss tiny or hidden faces: look at frames before sharing them
outside the team.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import urllib.request
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

MODEL_NAME = "face_detection_yunet_2023mar.onnx"
MODEL_URL = f"https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/{MODEL_NAME}"
MODEL_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"  # 227 KB, 2026-11-20


def model_path() -> Path:
    base = os.environ.get("CE_MODELS") or Path(__file__).resolve().parents[1] / "models"
    return Path(base) / MODEL_NAME


def fetch(force: bool = False) -> Path:
    """Download the YuNet model once. Returns its path."""
    path = model_path()
    if path.exists() and not force:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    urllib.request.urlretrieve(MODEL_URL, tmp)  # fixed https URL
    digest = hashlib.sha256(tmp.read_bytes()).hexdigest()
    if MODEL_SHA256 and digest != MODEL_SHA256:
        tmp.unlink()
        raise RuntimeError(f"{MODEL_NAME}: checksum {digest} doesn't match the pinned one")
    tmp.replace(path)
    print(f"{path} ({path.stat().st_size // 1024} KB, sha256 {digest})")
    return path


@lru_cache(maxsize=1)
def _detector():
    path = model_path()
    if not path.exists():
        raise FileNotFoundError(f"Face model missing: {path}. Run: python -m concrete_evidence.privacy --fetch")
    return cv2.FaceDetectorYN.create(str(path), "", (320, 320), 0.6, 0.3, 5000)


DETECT_MAX_SIDE = 1280  # YuNet's memory grows with the input: a 2400 x 1800 photo alone takes ~340 MB


def find_faces(frame: np.ndarray, min_size: int = 12) -> list[tuple[int, int, int, int]]:
    """Return face boxes (x, y, w, h) in pixels of `frame`. Large photos are searched at
    DETECT_MAX_SIDE so the free 512 MB server keeps its memory; the boxes are scaled back."""
    img = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR) if frame.ndim == 2 else frame
    s = min(1.0, DETECT_MAX_SIDE / max(img.shape[:2]))
    if s < 1.0:
        img = cv2.resize(img, (round(img.shape[1] * s), round(img.shape[0] * s)), interpolation=cv2.INTER_AREA)
    det = _detector()
    det.setInputSize((img.shape[1], img.shape[0]))
    _, faces = det.detect(img)
    if faces is None:
        return []
    boxes = [tuple(int(round(v / s)) for v in f[:4]) for f in faces]
    return [b for b in boxes if min(b[2], b[3]) >= min_size]


def blur_boxes(frame: np.ndarray, boxes, pad: float = 0.25) -> np.ndarray:
    """Return a copy of the frame with each box (plus padding) strongly blurred."""
    out = frame.copy()
    H, W = out.shape[:2]
    for (x, y, w, h) in boxes:
        px, py = int(w * pad), int(h * pad)
        x0, y0 = max(0, x - px), max(0, y - py)
        x1, y1 = min(W, x + w + px), min(H, y + h + py)
        if x1 <= x0 or y1 <= y0:
            continue
        roi = out[y0:y1, x0:x1]
        k = max(15, (max(x1 - x0, y1 - y0) // 3) | 1)  # odd kernel, scales with the face
        out[y0:y1, x0:x1] = cv2.GaussianBlur(roi, (k, k), 0)
    return out


def blur_faces(frame: np.ndarray) -> tuple[np.ndarray, int]:
    """Blur every face found. Returns (new frame, number of faces blurred)."""
    boxes = find_faces(frame)
    if not boxes:
        return frame, 0
    return blur_boxes(frame, boxes), len(boxes)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Fetch the face model used to blur workers' faces.")
    p.add_argument("--fetch", action="store_true")
    p.add_argument("--force", action="store_true", help="download again even if present")
    args = p.parse_args()
    if args.fetch:
        fetch(force=args.force)
    else:
        print(model_path(), "present" if model_path().exists() else "missing")
