"""
Turn site or mock-up videos into frames worth labelling.

    python training/extract_frames.py cage_walk.mp4 more.mov --out data/frames --every 0.5

Keeps one frame every --every seconds, then drops frames that are
  - blurry (variance of the Laplacian below --min-sharp), and
  - near-duplicates of the last kept frame (mean pixel change below --min-change).
Upload what's left to the Roboflow project and label bar / tie / hook_90 / hook_135.
"""

import argparse
from pathlib import Path

import cv2
import numpy as np


def sharpness(gray):
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("videos", nargs="+")
    p.add_argument("--out", default="data/frames")
    p.add_argument("--every", type=float, default=0.5, help="seconds between candidate frames")
    p.add_argument("--min-sharp", type=float, default=80.0, help="blur cut-off; raise it to keep fewer frames")
    p.add_argument("--min-change", type=float, default=6.0, help="duplicate cut-off (mean grey-level change)")
    p.add_argument("--max-side", type=int, default=1600, help="resize so the long side is at most this")
    a = p.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    total_kept = 0
    for v in a.videos:
        cap = cv2.VideoCapture(v)
        if not cap.isOpened():
            print(f"skip {v}: can't open")
            continue
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        step = max(1, int(round(fps * a.every)))
        stem, idx, kept, blurry, dupes, last = Path(v).stem, 0, 0, 0, 0, None
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            idx += 1
            if (idx - 1) % step:
                continue
            h, w = frame.shape[:2]
            s = a.max_side / max(h, w)
            if s < 1:
                frame = cv2.resize(frame, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if sharpness(gray) < a.min_sharp:
                blurry += 1
                continue
            small = cv2.resize(gray, (160, 120))
            if last is not None and float(np.mean(cv2.absdiff(small, last))) < a.min_change:
                dupes += 1
                continue
            last = small
            cv2.imwrite(str(out / f"{stem}_{idx:06d}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            kept += 1
        cap.release()
        total_kept += kept
        print(f"{v}: kept {kept}, dropped {blurry} blurry and {dupes} near-duplicates")
    print(f"{total_kept} frames in {out}")


if __name__ == "__main__":
    main()
