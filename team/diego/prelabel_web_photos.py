"""Pre-label the 60 Wikimedia cage photos with our first model, for review in Roboflow.

The model draws the first outlines; a person then fixes them in Roboflow's
annotate view (much faster than drawing 60 photos from scratch). Output is one
zip in YOLOv8-seg format that Roboflow reads with its labels, like the
synthetic zips.

    python prelabel_web_photos.py --weights best.pt --photos web_photos_roboflow \
        --out web_photos_prelabelled.zip

Stirrup loops keep the keyhole polygon (inside of the loop unlabelled), as in
LABELLING.md. Nothing here is a final label until someone has checked it.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "synthetic"))
from ce_boxes import mask_to_polygon, yolo_line  # noqa: E402

NAMES = ["bar", "stirrup", "hook_90", "hook_135"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--photos", required=True, help="folder with the .jpg photos")
    ap.add_argument("--out", default="web_photos_prelabelled.zip")
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--imgsz", type=int, default=640)
    a = ap.parse_args()

    from ultralytics import YOLO

    model = YOLO(a.weights)
    names = [model.names[i] for i in sorted(model.names)]
    rename = {"tie": "stirrup"}  # older models used "tie"
    names = [rename.get(n, n) for n in names]
    if set(names) != set(NAMES):
        print(f"warning: model classes {names} differ from {NAMES}")
    to_ours = {i: NAMES.index(n) for i, n in enumerate(names) if n in NAMES}

    photos = sorted(Path(a.photos).glob("*.jpg"))
    counts = dict.fromkeys(NAMES, 0)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "web_photos"
        (root / "train/images").mkdir(parents=True)
        (root / "train/labels").mkdir(parents=True)
        for p in photos:
            r = model.predict(str(p), imgsz=a.imgsz, conf=a.conf, max_det=500,
                              retina_masks=True, verbose=False)[0]
            h, w = r.orig_shape
            lines = []
            if r.masks is not None:
                for m, c in zip(r.masks.data.cpu().numpy(), r.boxes.cls.cpu().numpy().astype(int), strict=True):
                    if c not in to_ours:
                        continue
                    poly = mask_to_polygon(m, eps=1.5)
                    if poly is None or len(poly) < 3:
                        continue
                    lines.append(yolo_line(to_ours[c], poly.astype(np.float32), w, h))
                    counts[NAMES[to_ours[c]]] += 1
            shutil.copy(p, root / "train/images" / p.name)
            (root / "train/labels" / f"{p.stem}.txt").write_text("\n".join(lines))
            print(f"{p.name}: {len(lines)} outlines")
        (root / "data.yaml").write_text(
            "train: train/images\nval: train/images\n"
            f"nc: {len(NAMES)}\nnames: {NAMES}\n")
        out = Path(a.out).with_suffix("")
        shutil.make_archive(str(out), "zip", root)
    print(f"{len(photos)} photos -> {out}.zip  {counts}")


if __name__ == "__main__":
    main()
