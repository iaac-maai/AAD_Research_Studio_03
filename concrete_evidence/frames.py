"""Pick frames worth labelling from site or mock-up videos."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

THUMB = (160, 120)


def sharpness(gray: np.ndarray) -> float:
    """Variance of the Laplacian: low means blurry."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def thumb(gray: np.ndarray) -> np.ndarray:
    return cv2.resize(gray, THUMB, interpolation=cv2.INTER_AREA)


def change(a: np.ndarray, b: np.ndarray) -> float:
    """Mean absolute grey-level change between two thumbnails."""
    return float(np.mean(cv2.absdiff(a, b)))


def fit_long_side(frame: np.ndarray, max_side: int) -> np.ndarray:
    h, w = frame.shape[:2]
    s = max_side / max(h, w)
    if s >= 1:
        return frame
    return cv2.resize(frame, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)


@dataclass
class ExtractResult:
    kept: int = 0
    blurry: int = 0
    duplicates: int = 0


def extract(video: str | Path, out_dir: str | Path, every_s: float = 0.5, min_sharp: float = 80.0,
            min_change: float = 6.0, max_side: int = 1600, blur_faces: bool = True) -> ExtractResult:
    """Save one frame every `every_s` seconds, minus blurry ones and near-duplicates.

    Faces are blurred before saving unless blur_faces=False (see privacy.py).
    """
    from .privacy import blur_faces as _blur

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise FileNotFoundError(f"can't open video {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    step = max(1, int(round(fps * every_s)))
    res, idx, last = ExtractResult(), 0, None
    stem = Path(video).stem
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            idx += 1
            if (idx - 1) % step:
                continue
            frame = fit_long_side(frame, max_side)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if sharpness(gray) < min_sharp:
                res.blurry += 1
                continue
            t = thumb(gray)
            if last is not None and change(t, last) < min_change:
                res.duplicates += 1
                continue
            last = t
            if blur_faces:
                frame, _ = _blur(frame)
            cv2.imwrite(str(out / f"{stem}_{idx:06d}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            res.kept += 1
    finally:
        cap.release()
    return res
