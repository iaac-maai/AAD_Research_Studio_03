"""
Convert SORD (one COCO JSON per PNG) into YOLOv8-seg layout.

    python training/coco_to_yolo_seg.py --train data/sord/SORD-train-00000 data/sord/SORD-train-00001 \
                                        --val data/sord/SORD-valid-00000 --out data/sord_yolo

Writes:
    out/images/{train,val}/*.png   (symlinks, or copies if symlinks fail)
    out/labels/{train,val}/*.txt   (class x1 y1 x2 y2 ... normalised 0-1)
    out/data.yaml
Also handles a single big COCO file (standard layout) in any of the folders.
"""

import argparse
import json
import os
import shutil
from pathlib import Path

IMG_EXT = (".png", ".jpg", ".jpeg")


def find_image(json_path: Path, file_name: str | None) -> Path | None:
    cands = []
    if file_name:
        cands += [json_path.parent / file_name, json_path.parent / Path(file_name).name]
    cands += [json_path.with_suffix(e) for e in IMG_EXT]
    return next((c for c in cands if c.exists()), None)


def seg_to_polygon(seg, h, w):
    """Return one flat [x, y, x, y, ...] polygon in pixels, or None."""
    if isinstance(seg, list):
        polys = [p for p in seg if isinstance(p, list) and len(p) >= 6]
        if not polys:
            return None
        return max(polys, key=len)  # largest part
    if isinstance(seg, dict):  # RLE mask
        import cv2
        import numpy as np
        from pycocotools import mask as mu
        rle = mu.frPyObjects(seg, h, w) if isinstance(seg.get("counts"), list) else seg
        m = mu.decode(rle).astype(np.uint8)
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cs:
            return None
        c = max(cs, key=cv2.contourArea).reshape(-1, 2)
        return c.flatten().tolist() if len(c) >= 3 else None
    return None


def iter_coco(folders):
    """Yield (json_path, coco_dict) for every JSON under the folders."""
    for f in folders:
        for jp in sorted(Path(f).rglob("*.json")):
            try:
                d = json.loads(jp.read_text())
            except Exception as e:
                print(f"  skip {jp.name}: {e}")
                continue
            if isinstance(d, dict) and "annotations" in d:
                yield jp, d


def collect_classes(folders):
    names = {}
    for _, d in iter_coco(folders):
        for c in d.get("categories", []):
            names.setdefault(c["name"], None)
        for a in d["annotations"]:
            if "category_name" in a:
                names.setdefault(a["category_name"], None)
    return sorted(names)


def link(src: Path, dst: Path):
    if dst.exists():
        return
    try:
        os.symlink(src.resolve(), dst)
    except OSError:
        shutil.copy2(src, dst)


def convert(folders, split, out: Path, classes):
    cls_idx = {n: i for i, n in enumerate(classes)}
    (out / "images" / split).mkdir(parents=True, exist_ok=True)
    (out / "labels" / split).mkdir(parents=True, exist_ok=True)
    n_img = n_obj = 0
    for jp, d in iter_coco(folders):
        cat_name = {c["id"]: c["name"] for c in d.get("categories", [])}
        images = {im["id"]: im for im in d.get("images", [])}
        if not images:  # per-image JSON with no images block
            images = {None: {"id": None, "file_name": None}}
        by_img = {}
        for a in d["annotations"]:
            key = a.get("image_id") if a.get("image_id") in images else next(iter(images))
            by_img.setdefault(key, []).append(a)
        for iid, im in images.items():
            img_path = find_image(jp, im.get("file_name"))
            if img_path is None:
                continue
            w, h = im.get("width"), im.get("height")
            if not (w and h):
                from PIL import Image
                with Image.open(img_path) as I:
                    w, h = I.size
            lines = []
            for a in by_img.get(iid, []):
                name = a.get("category_name") or cat_name.get(a.get("category_id"))
                if name not in cls_idx:
                    continue
                poly = seg_to_polygon(a.get("segmentation"), h, w)
                if poly is None:
                    continue
                xy = [min(max(v / (w if i % 2 == 0 else h), 0.0), 1.0) for i, v in enumerate(poly)]
                lines.append(f"{cls_idx[name]} " + " ".join(f"{v:.6f}" for v in xy))
            stem = f"{jp.parent.name}__{img_path.stem}"
            link(img_path, out / "images" / split / f"{stem}{img_path.suffix}")
            (out / "labels" / split / f"{stem}.txt").write_text("\n".join(lines))
            n_img += 1
            n_obj += len(lines)
    print(f"[{split}] {n_img} images, {n_obj} instances")
    return n_img


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--train", nargs="+", required=True)
    p.add_argument("--val", nargs="+", required=True)
    p.add_argument("--out", default="data/sord_yolo")
    a = p.parse_args()
    out = Path(a.out)
    classes = collect_classes(a.train + a.val)
    print("classes:", classes)
    if not classes:
        raise SystemExit("No categories found - check the JSON files.")
    convert(a.train, "train", out, classes)
    convert(a.val, "val", out, classes)
    yaml = [f"path: {out.resolve()}", "train: images/train", "val: images/val", "names:"]
    yaml += [f"  {i}: {n}" for i, n in enumerate(classes)]
    (out / "data.yaml").write_text("\n".join(yaml) + "\n")
    print(f"wrote {out / 'data.yaml'}")


if __name__ == "__main__":
    main()
