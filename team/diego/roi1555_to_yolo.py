"""ROI-1555 (LabelMe polygons) -> YOLOv8-seg zip for our Roboflow project.

    python roi1555_to_yolo.py --src ROI-1555 --out roi1555_yolo

straight -> bar, hoop -> stirrup. The hoop outlines already follow the steel
and leave the inside of the loop empty, as in LABELLING.md. Hooks are inside
the hoop outline, without a label of their own.

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
from pathlib import Path

CLS = {"straight": 0, "hoop": 1}
NAMES = ["bar", "stirrup", "hook_90", "hook_135"]


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
        lines = []
        for s in d["shapes"]:
            pts = s["points"]
            if len(pts) < 3:
                continue
            xy = " ".join(f"{min(max(x / w, 0), 1):.6f} {min(max(y / h, 0), 1):.6f}" for x, y in pts)
            lines.append(f"{CLS[s['label'].split('-')[0]]} {xy}")
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
