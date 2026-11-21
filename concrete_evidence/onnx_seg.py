"""YOLOv8-seg on ONNX Runtime: the same answers as Ultralytics, without PyTorch.

Render's free plan has 512 MB of memory; PyTorch + Ultralytics alone use more.
So the server runs the exported model (`python pipeline.py export`) with
onnxruntime, and this file does what Ultralytics does around the network:
letterbox the photo to 640, keep boxes above the confidence, non-maximum
suppression, then build each outline from the 32 mask prototypes.

`OnnxSeg(path).predict(image)` returns a result shaped like Ultralytics' one
(`boxes.xyxy / cls / conf / id`, `masks.xy`, `names`), so `infer.analyse` and
`capture.records_from_result` work unchanged with either.
"""

from __future__ import annotations

import ast

import cv2
import numpy as np

PAD = 114  # Ultralytics' letterbox grey


class _Arr:
    """Just enough of a torch tensor for records_from_result: .tolist(), .int(), len()."""

    def __init__(self, a):
        self.a = np.asarray(a)

    def tolist(self):
        return self.a.tolist()

    def int(self):
        return _Arr(self.a.astype(np.int64))

    def __len__(self):
        return len(self.a)


class _Boxes:
    def __init__(self, xyxy, conf, cls):
        self.xyxy, self.conf, self.cls, self.id = _Arr(xyxy), _Arr(conf), _Arr(cls), None

    def __len__(self):
        return len(self.xyxy)


class _Masks:
    def __init__(self, xy):
        self.xy = xy


class Result:
    def __init__(self, xyxy, conf, cls, polygons, names, shape):
        self.boxes = _Boxes(xyxy, conf, cls)
        self.masks = _Masks(polygons) if len(xyxy) else None
        self.names, self.orig_shape = names, shape


def letterbox(bgr: np.ndarray, size: int = 640) -> tuple[np.ndarray, float, tuple[float, float]]:
    """Resize keeping the aspect ratio, pad to size x size with grey. Returns image, scale, (pad x, pad y)."""
    h, w = bgr.shape[:2]
    r = min(size / h, size / w)
    nw, nh = int(round(w * r)), int(round(h * r))
    px, py = (size - nw) / 2, (size - nh) / 2
    img = cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_LINEAR) if (nw, nh) != (w, h) else bgr
    top, bottom = int(round(py - 0.1)), int(round(py + 0.1))
    left, right = int(round(px - 0.1)), int(round(px + 0.1))
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(PAD, PAD, PAD))
    return img, r, (left, top)


def nms(xyxy: np.ndarray, conf: np.ndarray, cls: np.ndarray, iou: float, max_det: int) -> np.ndarray:
    """Indices kept by per-class NMS (classes shifted apart, as Ultralytics does)."""
    if not len(xyxy):
        return np.zeros(0, dtype=int)
    b = xyxy.astype(np.float64) + cls[:, None] * 7680.0
    area = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    order = np.argsort(-conf, kind="stable")
    keep = []
    while len(order) and len(keep) < max_det:
        i, rest = order[0], order[1:]
        keep.append(i)
        w = (np.minimum(b[i, 2], b[rest, 2]) - np.maximum(b[i, 0], b[rest, 0])).clip(0)
        h = (np.minimum(b[i, 3], b[rest, 3]) - np.maximum(b[i, 1], b[rest, 1])).clip(0)
        inter = w * h
        order = rest[inter / (area[i] + area[rest] - inter + 1e-9) <= iou]
    return np.asarray(keep, dtype=int)


def outline(logits: np.ndarray, box, r: float, pad: tuple[float, float], stride: float, shape) -> np.ndarray | None:
    """One instance's outline in photo pixels, from its mask logits in prototype space.

    Only the box is resampled (not the whole photo), so 500 pieces on a 12 MP photo stay cheap.
    """
    H, W = shape
    # pixels with x1 <= column < x2 (and the same for rows), as Ultralytics' crop_mask keeps
    x1, y1 = max(int(np.ceil(box[0])), 0), max(int(np.ceil(box[1])), 0)
    x2, y2 = min(int(np.ceil(box[2])), W), min(int(np.ceil(box[3])), H)
    if x2 - x1 < 2 or y2 - y1 < 2:
        return None
    k = r / stride  # photo pixel -> prototype pixel
    m = np.float32([[k, 0, (x1 * r + pad[0]) / stride + 0.5 * k - 0.5],
                    [0, k, (y1 * r + pad[1]) / stride + 0.5 * k - 0.5]])
    crop = cv2.warpAffine(logits, m, (x2 - x1, y2 - y1), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                          borderMode=cv2.BORDER_REPLICATE)
    bw = (crop > 0).astype(np.uint8)  # sigmoid > 0.5
    cs, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cs:
        return None
    c = max(cs, key=cv2.contourArea).reshape(-1, 2).astype(np.float32)
    return c + np.float32([x1, y1])


def compare(pt_model, onnx_model, bgr: np.ndarray, imgsz: int = 640, conf: float = 0.25) -> dict:
    """Run one photo through the PyTorch model and its ONNX export; how far apart are they?

    Pieces are paired by nearest box. Outline overlap (IoU) is measured on filled outlines.
    """
    kw = {"imgsz": imgsz, "conf": conf, "max_det": 500}
    a = pt_model.predict(bgr, retina_masks=True, verbose=False, **kw)[0]
    b = onnx_model.predict(bgr, **kw)[0]
    pa = np.asarray(a.boxes.xyxy.cpu().numpy() if len(a.boxes) else np.zeros((0, 4)))
    pb = np.asarray(b.boxes.xyxy.tolist() if len(b.boxes) else np.zeros((0, 4)))
    out = {"pytorch": len(pa), "onnx": len(pb), "same_count": len(pa) == len(pb)}
    if not len(pa) or not len(pb):
        return out
    H, W = bgr.shape[:2]
    shift, ious = [], []
    for i, p in enumerate(pa):
        j = int(np.argmin(np.abs(pb - p).sum(1)))
        shift.append(float(np.abs(pb[j] - p).max()))
        m1, m2 = np.zeros((H, W), np.uint8), np.zeros((H, W), np.uint8)
        if a.masks is not None and len(a.masks.xy[i]) > 2:
            cv2.fillPoly(m1, [np.asarray(a.masks.xy[i], np.int32)], 1)
        if b.masks is not None and len(b.masks.xy[j]) > 2:
            cv2.fillPoly(m2, [np.asarray(b.masks.xy[j], np.int32)], 1)
        u = int((m1 | m2).sum())
        ious.append(float((m1 & m2).sum()) / u if u else 1.0)
    out.update({"box_shift_px_max": round(max(shift), 2), "outline_iou_median": round(float(np.median(ious)), 3),
                "outline_iou_min": round(float(min(ious)), 3)})
    return out


class OnnxSeg:
    """An exported YOLOv8-seg model. `predict(bgr)` -> [Result], like Ultralytics' YOLO.predict."""

    def __init__(self, path: str, threads: int | None = None):
        import onnxruntime as ort

        opts = ort.SessionOptions()
        opts.enable_cpu_mem_arena = False  # hand memory back after each photo: Render has 512 MB
        if threads:
            opts.intra_op_num_threads = threads
        self.session = ort.InferenceSession(str(path), opts, providers=["CPUExecutionProvider"])
        meta = self.session.get_modelmeta().custom_metadata_map
        self.names = ast.literal_eval(meta["names"]) if "names" in meta else {}
        self.input = self.session.get_inputs()[0].name
        shape = self.session.get_inputs()[0].shape
        self.imgsz = int(shape[-1]) if isinstance(shape[-1], int) else 640

    def predict(self, bgr: np.ndarray, imgsz: int | None = None, conf: float = 0.25, iou: float = 0.5,
                max_det: int = 300, **_) -> list[Result]:
        size = self.imgsz  # a static export only takes its own size
        lb, r, pad = letterbox(bgr, size)
        x = cv2.cvtColor(lb, cv2.COLOR_BGR2RGB).transpose(2, 0, 1)[None].astype(np.float32) / 255.0
        pred, protos = self.session.run(None, {self.input: x})
        pred, protos = pred[0].T, protos[0]  # (8400, 4 + nc + 32), (32, 160, 160)
        nm = protos.shape[0]
        nc = pred.shape[1] - 4 - nm
        scores = pred[:, 4:4 + nc]
        cls = scores.argmax(1)
        best = scores[np.arange(len(scores)), cls]
        sel = best > conf
        pred, cls, best = pred[sel], cls[sel], best[sel]
        cx, cy, w, h = pred[:, 0], pred[:, 1], pred[:, 2], pred[:, 3]
        boxes = np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], 1)
        keep = nms(boxes, best, cls, iou, max_det)
        boxes, best, cls, coef = boxes[keep], best[keep], cls[keep], pred[keep, 4 + nc:]

        H, W = bgr.shape[:2]
        orig = boxes.copy()  # letterbox -> photo pixels
        orig[:, [0, 2]] = ((orig[:, [0, 2]] - pad[0]) / r).clip(0, W)
        orig[:, [1, 3]] = ((orig[:, [1, 3]] - pad[1]) / r).clip(0, H)

        stride = size / protos.shape[-1]
        flat = protos.reshape(nm, -1)
        polys = []
        for i in range(len(orig)):
            logits = (coef[i] @ flat).reshape(protos.shape[1:]).astype(np.float32)
            p = outline(logits, orig[i], r, pad, stride, (H, W))
            polys.append(p if p is not None else np.zeros((0, 2), np.float32))
        return [Result(orig, best, cls, polys, self.names, (H, W))]
