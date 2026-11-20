"""ConRebSeg (DTU, CC BY 4.0) -> YOLO-seg.

ConRebSeg: real construction-site photos with exposed rebar, segmented.
Schmidt & Nalpantidis (2025), Automation in Construction 171. Data DOI 10.11583/DTU.26213762.

The download is ConRebSeg.zip (the images) and samples.json, a FiftyOne export:
one record per image with its split tag (train / val / test) and every object's
label, bounding box (0-1, x y w h) and mask. Each mask covers only its box and is
stored as a zlib-compressed .npy array, base64 in the JSON.

We keep the self-collected sequences (langebro, vester_sogade) and skip the
YouTube frames, which have no clear licence. Labels kept by default:
ExposedBars -> bar. Person, car and truck are dropped: the project is only rebar.
"""

from __future__ import annotations

import base64
import io
import json
import zipfile
import zlib
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from .convert import _link, polygon_line

DEFAULT_CLASSES = {"ExposedBars": "bar"}
SPLITS = ("train", "val", "test")
SELF_COLLECTED = ("data/langebro/", "data/vester_sogade/")


def decode_mask(b64: str) -> np.ndarray:
    """A FiftyOne mask (base64 of zlib-compressed .npy) -> 2-D uint8 array."""
    arr = np.load(io.BytesIO(zlib.decompress(base64.b64decode(b64))), allow_pickle=False)
    return (arr > 0).astype(np.uint8)


def encode_mask(mask: np.ndarray) -> str:
    """The reverse of decode_mask (used by the tests)."""
    buf = io.BytesIO()
    np.save(buf, mask.astype(bool), allow_pickle=False)
    return base64.b64encode(zlib.compress(buf.getvalue())).decode()


def _mask_b64(det: dict) -> str | None:
    m = det.get("mask")
    if isinstance(m, dict):
        m = m.get("$binary", {}).get("base64")
    return m if isinstance(m, str) else None


def det_polygon(det: dict, width: int, height: int, min_area: float = 20.0):
    """The object's outline in image pixels, flat [x, y, ...], or None if too small."""
    b64 = _mask_b64(det)
    if not b64:
        return None
    mask = decode_mask(b64)
    x0, y0 = det["bounding_box"][0] * width, det["bounding_box"][1] * height
    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cs = [c for c in cs if cv2.contourArea(c) >= min_area]
    if not cs:
        return None
    c = cv2.approxPolyDP(max(cs, key=cv2.contourArea), 1.0, True).reshape(-1, 2).astype(float)
    if len(c) < 3:
        return None
    c[:, 0] += x0
    c[:, 1] += y0
    return c.flatten().tolist()


def split_of(sample: dict) -> str | None:
    return next((t for t in sample.get("tags", []) if t in SPLITS), None)


def iter_samples(samples_json: str | Path, include_youtube: bool = False):
    data = json.loads(Path(samples_json).read_text(encoding="utf-8"))
    for s in data["samples"] if isinstance(data, dict) else data:
        fp = s.get("filepath", "")
        if include_youtube or fp.startswith(SELF_COLLECTED):
            yield s


def extract(zip_path: str | Path, root: str | Path, include_youtube: bool = False) -> int:
    """Unpack the images we use from ConRebSeg.zip into root. Returns files written."""
    root, n = Path(root), 0
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if info.is_dir() or not (include_youtube or any(p in name for p in SELF_COLLECTED)):
                continue
            dst = root / name
            if dst.resolve().is_relative_to(root.resolve()) and not dst.exists():  # no paths outside root
                dst.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(dst, "wb") as out:
                    out.write(src.read())
                n += 1
    return n


def find_image(root: Path, filepath: str) -> Path | None:
    for cand in (root / filepath, root / filepath.removeprefix("data/"), root / "ConRebSeg" / filepath):
        if cand.exists():
            return cand
    return None


def convert(root: str | Path, out: str | Path, classes: dict[str, str] | None = None,
            limit: int | None = None, include_youtube: bool = False) -> dict:
    """samples.json + unpacked images under root -> YOLO-seg in out. Returns counts."""
    root, out = Path(root), Path(out)
    classes = classes or DEFAULT_CLASSES
    names = sorted(set(classes.values()))
    idx = {n: i for i, n in enumerate(names)}
    stats, per_split = Counter(), Counter()
    for split in SPLITS:
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)
    for s in iter_samples(root / "samples.json", include_youtube):
        split = split_of(s)
        if split is None or (limit and per_split[split] >= limit):
            continue
        img = find_image(root, s["filepath"])
        if img is None:
            stats["missing_image"] += 1
            continue
        w, h = s["metadata"]["width"], s["metadata"]["height"]
        lines = []
        for det in (s.get("gt_annotations") or {}).get("detections", []):
            name = classes.get(det.get("label"))
            if name is None:
                stats["dropped_" + str(det.get("label"))] += 1
                continue
            poly = det_polygon(det, w, h)
            if poly is None:
                stats["too_small"] += 1
                continue
            lines.append(polygon_line(idx[name], poly, w, h))
        stem = "__".join(Path(s["filepath"]).with_suffix("").parts[1:])  # langebro__run_x__frame
        _link(img, out / "images" / split / f"{stem}{img.suffix}")
        (out / "labels" / split / f"{stem}.txt").write_text("\n".join(lines))
        per_split[split] += 1
        stats["instances"] += len(lines)
    yaml = [f"path: {out.resolve()}", "train: images/train", "val: images/val", "test: images/test", "names:"]
    yaml += [f"  {i}: {n}" for i, n in enumerate(names)]
    (out / "data.yaml").write_text("\n".join(yaml) + "\n")
    return {**{f"images_{k}": v for k, v in per_split.items()}, **stats}
