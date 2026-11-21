"""Depth Anything before YOLO: grey out what is far behind the cage.

Site photos are cluttered: formwork, scaffolding, the next column, the street.
Depth Anything V2 Small (Apache-2.0) guesses from one photo how near each pixel
is. We keep the near part (the cage) and paint everything behind it plain grey,
then YOLO runs on that cleaned photo. YOLO itself is unchanged.

It can also cut the kept part into depth slices, nearest first: one image per
layer of bars, for footings and slabs where layers stack.

Two rules that matter:
  * Train and run on the same kind of image. If the live view filters, the
    training images must be filtered too: `python pipeline.py depth data/ours
    --out data/ours_depth` does a whole YOLO dataset and keeps its labels.
  * Depth from one photo is relative (nearer / farther, no units) and rough.
    The kept area is grown by a margin so bar edges are never cut off.

The model (about 100 MB) downloads from Hugging Face on first use, pinned to a
revision. Only the Small size is Apache-2.0; Base and Large are non-commercial.
"""

from __future__ import annotations

import cv2
import numpy as np

MODEL_ID = "depth-anything/Depth-Anything-V2-Small-hf"
REVISION = "5426e4f0f36572d16453bbda7a8389317b1bef99"  # Apache-2.0, checked 21 Nov 2026
GREY = 114  # the padding grey YOLO itself uses, so greyed areas look like "nothing"


class DepthAnything:
    """Depth Anything V2 Small. Call it on a BGR photo to get nearness, 0 (far) to 1 (near)."""

    def __init__(self, model_id: str = MODEL_ID, revision: str = REVISION, device: str | None = None):
        import torch  # heavy: only when depth is used
        from transformers import AutoImageProcessor, AutoModelForDepthEstimation

        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = AutoImageProcessor.from_pretrained(model_id, revision=revision)
        self.model = AutoModelForDepthEstimation.from_pretrained(model_id, revision=revision).to(self.device).eval()

    def __call__(self, bgr: np.ndarray) -> np.ndarray:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        inputs = self.processor(images=rgb, return_tensors="pt").to(self.device)
        with self.torch.no_grad():
            out = self.model(**inputs).predicted_depth  # relative inverse depth: bigger = nearer
        d = self.torch.nn.functional.interpolate(out[:, None], size=bgr.shape[:2], mode="bicubic",
                                                 align_corners=False)[0, 0]
        return normalise(d.cpu().numpy())


def normalise(depth: np.ndarray) -> np.ndarray:
    """Nearness to 0..1, ignoring the 2% most extreme pixels at each end."""
    d = np.asarray(depth, dtype=np.float32)
    lo, hi = np.percentile(d, (2, 98))
    if hi - lo < 1e-6:
        return np.zeros_like(d)
    return np.clip((d - lo) / (hi - lo), 0.0, 1.0)


def near_mask(near: np.ndarray, threshold: float | None = None, margin_px: int = 15,
              min_area: float = 0.01) -> tuple[np.ndarray, float]:
    """The near part of the photo as a 0/1 mask, and the threshold used.

    threshold: nearness to keep (0..1); None splits near from far automatically (Otsu).
    margin_px: the kept area grows by this much, so thin bars at its edge stay whole.
    min_area: drop kept blobs smaller than this fraction of the photo (noise).
    """
    u8 = (np.clip(near, 0, 1) * 255).astype(np.uint8)
    if threshold is None:
        t, mask = cv2.threshold(u8, 0, 1, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        threshold = t / 255.0
    else:
        mask = (u8 >= int(round(threshold * 255))).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)  # fill the small holes between bars
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    keep = np.zeros_like(mask)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= min_area * mask.size:
            keep[lab == i] = 1
    if margin_px > 0 and keep.any():
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * margin_px + 1, 2 * margin_px + 1))
        keep = cv2.dilate(keep, k)
    return keep, float(threshold)


def grey_out(bgr: np.ndarray, mask: np.ndarray, value: int = GREY) -> np.ndarray:
    """The photo with everything outside the mask painted plain grey."""
    out = bgr.copy()
    out[mask == 0] = value
    return out


def layer_masks(near: np.ndarray, mask: np.ndarray, n: int) -> list[np.ndarray]:
    """Split the kept area into n depth slices, nearest first (k-means on nearness)."""
    vals = near[mask > 0].astype(np.float32).reshape(-1, 1)
    if n < 2 or len(vals) < n:
        return [mask.copy()]
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 1e-4)
    _, _, centres = cv2.kmeans(vals, n, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    centres = np.sort(centres.ravel())[::-1]  # nearest first
    # each pixel goes to its closest centre
    idx = np.argmin(np.abs(near[..., None] - centres[None, None, :]), axis=-1)
    return [((idx == i) & (mask > 0)).astype(np.uint8) for i in range(n)]


def filter_image(bgr: np.ndarray, near: np.ndarray, threshold: float | None = None, margin_px: int = 15,
                 slices: int = 0) -> dict:
    """Everything the depth step gives YOLO: the filtered photo, its mask, and optional layer photos."""
    mask, t = near_mask(near, threshold, margin_px)
    if not mask.any():  # nothing stood out as near: don't throw the photo away
        mask[:] = 1
    out = {"image": grey_out(bgr, mask), "mask": mask, "threshold": round(t, 3),
           "kept": round(float(mask.mean()), 3), "layers": []}
    if slices:
        out["layers"] = [grey_out(bgr, m) for m in layer_masks(near, mask, slices)]
    return out


def preview(near: np.ndarray) -> np.ndarray:
    """A colour picture of the depth: warm = near, cool = far."""
    return cv2.applyColorMap((np.clip(near, 0, 1) * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)


IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def filter_folder(estimate, src, out, threshold: float | None = None, margin_px: int = 15, slices: int = 0,
                  previews: bool = False) -> dict:
    """Filter one photo, a folder of photos, or a whole YOLO dataset into out.

    estimate: a callable BGR photo -> nearness (a DepthAnything, or a stand-in in tests).
    Folders keep their layout. Label .txt files are copied unchanged (greying out moves
    nothing), and a data.yaml gets its path pointed at out, so YOLO trains on it as is.
    """
    import json
    import shutil
    from pathlib import Path

    src, out = Path(src), Path(out)
    files = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.suffix.lower() in IMAGE_EXT)
    root = src.parent if src.is_file() else src
    log = {}
    for f in files:
        rel = f.relative_to(root)
        img = cv2.imread(str(f))
        if img is None:
            continue
        near = estimate(img)
        res = filter_image(img, near, threshold, margin_px, slices)
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(dst), res["image"])
        if previews:
            pv = out / "_preview" / rel.parent
            pv.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(pv / f"{f.stem}_depth.png"), preview(near))
        for i, layer in enumerate(res["layers"], 1):
            lv = out / "_layers" / rel.parent
            lv.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(lv / f"{f.stem}_layer{i}{f.suffix}"), layer)
        log[str(rel).replace("\\", "/")] = {"threshold": res["threshold"], "kept": res["kept"]}
    if src.is_dir():
        for t in src.rglob("*.txt"):
            dst = out / t.relative_to(src)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(t, dst)
        y = src / "data.yaml"
        if y.exists():
            lines = [f"path: {out.resolve()}" if ln.startswith("path:") else ln
                     for ln in y.read_text(encoding="utf-8").splitlines()]
            if not any(ln.startswith("path:") for ln in lines):
                lines.insert(0, f"path: {out.resolve()}")
            (out / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    out.mkdir(parents=True, exist_ok=True)
    summary = {"model": MODEL_ID, "revision": REVISION, "margin_px": margin_px, "images": len(log), "files": log}
    (out / "depth_filter.json").write_text(json.dumps(summary, indent=2))
    return summary
