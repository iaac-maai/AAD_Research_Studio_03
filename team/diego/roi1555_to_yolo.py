"""ROI-1555 (LabelMe polygons) -> YOLOv8-seg zip for our Roboflow project.

    python roi1555_to_yolo.py --src ROI-1555 --out roi1555_yolo

straight -> bar, hoop -> stirrup. ROI labels each visible PIECE as its own
polygon and gives the pieces of one object the same label ("hoop-3" twice =
one stirrup seen in two pieces). Pieces with the same label are merged into
one instance and joined by thin bridges across the hidden parts, the same as
our synthetic labels, so one stirrup = one instance. Stirrup loops keep the
keyhole polygon (inside of the loop unlabelled), as in LABELLING.md.

Split: the 1,260-photo set 90 % train / 10 % valid (seed 0); the three test
scenes from the paper (scen1-3, 295 photos) go to test, so the test set has
real stirrups. Photos are renamed roi_<folder>_<n>.jpg (the folders reuse names).

Licence: the dataset card has no licence. Used for this course project only
(research use), images not redistributed; permission email to the authors in
ROI1555.md.
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "synthetic"))
from ce_boxes import mask_to_polygon, yolo_line  # noqa: E402

CLS = {"straight": 0, "hoop": 1}
NAMES = ["bar", "stirrup", "hook_90", "hook_135"]


def bridge(m: np.ndarray) -> np.ndarray:
    """Join the visible pieces of one object with 2 px bridges (as in synthetic/make_cages.py)."""
    n, cc, st, _ = cv2.connectedComponentsWithStats(m)
    keep = [k for k in range(1, n) if st[k, cv2.CC_STAT_AREA] >= 25]
    out = np.isin(cc, keep).astype(np.uint8)
    if len(keep) <= 1:
        return out
    pts = {}
    for k in keep:
        cs, _ = cv2.findContours((cc == k).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = np.concatenate(cs)[:, 0, :]
        pts[k] = c[:: max(1, len(c) // 40)]
    done, todo = [keep[0]], keep[1:]
    while todo:
        best = None
        for a in done:
            for b in todo:
                d = ((pts[a][:, None, :] - pts[b][None, :, :]) ** 2).sum(-1)
                i, j = np.unravel_index(int(d.argmin()), d.shape)
                if best is None or d[i, j] < best[0]:
                    best = (d[i, j], pts[a][i], pts[b][j], b)
        cv2.line(out, tuple(int(v) for v in best[1]), tuple(int(v) for v in best[2]), 1, 2)
        done.append(best[3])
        todo.remove(best[3])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", default="roi1555_yolo")
    ap.add_argument("--val", type=float, default=0.1)
    a = ap.parse_args()
    src, out = Path(a.src), Path(a.out)

    main_set = sorted((src / "1260").rglob("*.jpg"))
    random.Random(0).shuffle(main_set)
    n_val = round(len(main_set) * a.val)
    split = {p: ("valid" if i < n_val else "train") for i, p in enumerate(main_set)}
    for scene in ("scen1", "scen2", "scen3"):
        split.update({p: "test" for p in (src / scene).rglob("*.jpg")})

    for img, sp in split.items():
        d = json.loads(img.with_suffix(".json").read_text())
        w, h = d["imageWidth"], d["imageHeight"]
        groups = defaultdict(list)  # "hoop-3" -> its pieces
        for s in d["shapes"]:
            if len(s["points"]) >= 3:
                groups[s["label"]].append(np.array(s["points"], np.float32))
        lines = []
        for lab, pieces in groups.items():
            m = np.zeros((h, w), np.uint8)
            cv2.fillPoly(m, [p.round().astype(np.int32) for p in pieces], 1)
            poly = mask_to_polygon(bridge(m), min_area=40, eps=1.2)
            if poly is not None and len(poly) >= 3:
                lines.append(yolo_line(CLS[lab.split("-")[0]], poly.astype(np.float32), w, h))
        name = f"roi_{img.relative_to(src).parts[0]}_{img.stem}"
        (out / sp / "images").mkdir(parents=True, exist_ok=True)
        (out / sp / "labels").mkdir(parents=True, exist_ok=True)
        shutil.copy(img, out / sp / "images" / f"{name}.jpg")
        (out / sp / "labels" / f"{name}.txt").write_text("\n".join(lines))

    (out / "data.yaml").write_text(
        "train: train/images\nval: valid/images\ntest: test/images\n"
        f"nc: {len(NAMES)}\nnames: {NAMES}\n")
    shutil.make_archive(str(out), "zip", out)
    print(f"{len(split)} photos -> {out}.zip")


if __name__ == "__main__":
    main()
