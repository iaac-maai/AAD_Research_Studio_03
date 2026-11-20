"""Segmentation labels -> YOLO-seg.

Reads LabelMe JSON (one per image, what SORD and Roboflow's LabelMe export use)
or COCO JSON (one big file, or one per image). Writes
    out/images/{train,val}/*   (symlinks, or copies where symlinks aren't allowed)
    out/labels/{train,val}/*.txt   (class x1 y1 x2 y2 ... normalised 0-1)
    out/data.yaml
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

IMG_EXT = (".png", ".jpg", ".jpeg")


def find_image(json_path: Path, file_name: str | None) -> Path | None:
    cands: list[Path] = []
    if file_name:
        cands += [json_path.parent / file_name, json_path.parent / Path(file_name).name]
    cands += [json_path.with_suffix(e) for e in IMG_EXT]
    return next((c for c in cands if c.exists()), None)


def seg_to_polygon(seg, h: int, w: int):
    """One flat [x, y, x, y, ...] polygon in pixels (the largest part), or None."""
    if isinstance(seg, list):
        polys = [p for p in seg if isinstance(p, list) and len(p) >= 6]
        return max(polys, key=len) if polys else None
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


def labelme_to_coco(d: dict) -> dict:
    """LabelMe JSON -> a minimal one-image COCO dict. Rectangles become 4-point polygons."""
    anns = []
    for sh in d.get("shapes", []):
        pts = sh.get("points") or []
        if sh.get("shape_type", "polygon") == "rectangle" and len(pts) == 2:
            (x1, y1), (x2, y2) = pts
            pts = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
        if len(pts) < 3:
            continue
        anns.append({"image_id": 1, "category_name": sh["label"],
                     "segmentation": [[v for xy in pts for v in xy]]})
    return {"images": [{"id": 1, "file_name": d.get("imagePath"),
                        "width": d.get("imageWidth"), "height": d.get("imageHeight")}],
            "annotations": anns, "categories": []}


def iter_coco(folders):
    """Yield (json_path, coco_dict) for every label JSON under the folders."""
    for f in folders:
        for jp in sorted(Path(f).rglob("*.json")):
            try:
                d = json.loads(jp.read_text())
            except Exception as e:  # noqa: BLE001 - skip unreadable files, keep going
                print(f"  skip {jp.name}: {e}")
                continue
            if isinstance(d, dict) and "shapes" in d:
                d = labelme_to_coco(d)
            if isinstance(d, dict) and "annotations" in d:
                yield jp, d


def collect_classes(folders) -> list[str]:
    names: dict[str, None] = {}
    for _, d in iter_coco(folders):
        for c in d.get("categories", []):
            names.setdefault(c["name"], None)
        for a in d["annotations"]:
            if "category_name" in a:
                names.setdefault(a["category_name"], None)
    return sorted(names)


def polygon_line(cls_idx: int, poly, w: int, h: int) -> str:
    """A YOLO-seg label line: class index, then x y pairs normalised to 0-1 and clipped."""
    xy = [min(max(v / (w if i % 2 == 0 else h), 0.0), 1.0) for i, v in enumerate(poly)]
    return f"{cls_idx} " + " ".join(f"{v:.6f}" for v in xy)


def _link(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    try:
        os.symlink(src.resolve(), dst)
    except OSError:
        shutil.copy2(src, dst)


def convert(folders, split: str, out: Path, classes: list[str]) -> tuple[int, int]:
    """Write one split. Returns (images, instances)."""
    cls_idx = {n: i for i, n in enumerate(classes)}
    (out / "images" / split).mkdir(parents=True, exist_ok=True)
    (out / "labels" / split).mkdir(parents=True, exist_ok=True)
    n_img = n_obj = 0
    for jp, d in iter_coco(folders):
        cat_name = {c["id"]: c["name"] for c in d.get("categories", [])}
        images = {im["id"]: im for im in d.get("images", [])} or {None: {"id": None, "file_name": None}}
        by_img: dict = {}
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
                with Image.open(img_path) as img:
                    w, h = img.size
            lines = []
            for a in by_img.get(iid, []):
                name = a.get("category_name") or cat_name.get(a.get("category_id"))
                if name not in cls_idx:
                    continue
                poly = seg_to_polygon(a.get("segmentation"), h, w)
                if poly is not None:
                    lines.append(polygon_line(cls_idx[name], poly, w, h))
            stem = f"{jp.parent.name}__{img_path.stem}"
            _link(img_path, out / "images" / split / f"{stem}{img_path.suffix}")
            (out / "labels" / split / f"{stem}.txt").write_text("\n".join(lines))
            n_img += 1
            n_obj += len(lines)
    return n_img, n_obj


def build(train, val, out: str | Path) -> Path:
    """Convert train and val folders and write data.yaml. Returns the yaml path."""
    out = Path(out)
    classes = collect_classes(list(train) + list(val))
    if not classes:
        raise ValueError("No categories found - check the JSON files.")
    print("classes:", classes)
    for split, folders in (("train", train), ("val", val)):
        n_img, n_obj = convert(folders, split, out, classes)
        print(f"[{split}] {n_img} images, {n_obj} instances")
    yaml = [f"path: {out.resolve()}", "train: images/train", "val: images/val", "names:"]
    yaml += [f"  {i}: {n}" for i, n in enumerate(classes)]
    (out / "data.yaml").write_text("\n".join(yaml) + "\n")
    return out / "data.yaml"
