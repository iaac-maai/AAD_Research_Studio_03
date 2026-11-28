"""Measure a rebar cage from one photo: count, spacing, stirrup sides and angles.

Diego, Sat 28 Nov 2026. Follows the feedback from Nacho and Rasha (no ArUco needed for a first scale):

  outlines (YOLO-seg)  ->  centre line (skeleton)  ->  bar width in px  =  bar diameter
  scale = known diameter (from the plans, default 12 mm) / width in px

Steps
  1. Outlines come from the model (--weights best.pt) or from a YOLO-seg label file (--labels, for testing
     with ground truth).
  2. Bars: one line fit per outline, grouped into directions (k-means on the doubled angle), pieces of the
     same bar merged when they sit on the same line.
  3. Scale per bar from its own width, so it follows the perspective (near bars look thicker).
  4. Spacing between neighbouring bars of each direction, measured on the centre row/column of the photo,
     in mm with the local scale of the two bars. Green = within tolerance, red = check.
     Tolerance is against --spacing (mm, from the plans) if given, else against the median spacing.
  5. Stirrups: corner polygon of the centre line -> side lengths (mm) and corner angles; spacing between
     stirrups along the main bar direction.
  6. Optional --depth: Depth Anything V2 Small gives a depth map; each bar gets the median depth of its
     own pixels and bars are split into 2 layers (top/bottom) when the two depth groups are far enough
     apart. Counts and spacing are then reported per layer.

Output: <out>.jpg (annotated photo) and <out>.json (all numbers).

Limits (say these in the demo): the scale assumes every bar has the diameter given; bars seen at a slant
or far from the centre of the photo get a rougher scale; depth from Depth Anything is relative, not mm.
ArUco markers (fab-lab photos) are the planned cross-check of the diameter scale.

Usage
  python measure_cage.py photo.jpg --weights best.pt --diameter 12 --spacing 150 --depth --out result
  python measure_cage.py photo.jpg --labels photo.txt --diameter 12 --out result
"""
import argparse
import json

import cv2
import numpy as np
from skimage.morphology import skeletonize

FONT = cv2.FONT_HERSHEY_SIMPLEX
NAMES = {0: "bar", 1: "stirrup", 2: "hook_90", 3: "hook_135"}  # our Roboflow class order
RENAME = {"tie": "stirrup"}
DIR_COL = [(0, 140, 255), (255, 160, 0)]  # BGR: orange, light blue
LAYER_COL = {"top": (0, 170, 255), "bottom": (160, 60, 200)}
STIR_COL = (200, 120, 40)
OK, BAD = (40, 150, 40), (0, 0, 200)


# ---------------------------------------------------------------- loading outlines
def from_labels(path, w, h):
    out = []
    for line in open(path):
        v = line.split()
        if len(v) < 7:
            continue
        pts = (np.array(v[1:], float).reshape(-1, 2) * [w, h]).round().astype(np.int32)
        out.append((NAMES.get(int(v[0]), v[0]), pts))
    return out


def from_model(weights, img, conf):
    from ultralytics import YOLO
    model = YOLO(weights)
    r = model.predict(img, conf=conf, max_det=500, retina_masks=True, verbose=False)[0]
    out = []
    if r.masks is None:
        return out
    for c, poly in zip(r.boxes.cls.int().tolist(), r.masks.xy, strict=True):
        name = RENAME.get(r.names[c], r.names[c])
        if len(poly) >= 3:
            out.append((name, poly.round().astype(np.int32)))
    return out


def depth_map(img):
    from PIL import Image
    from transformers import pipeline
    pipe = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf")
    d = np.array(pipe(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))["predicted_depth"], np.float32)
    d = cv2.resize(d.squeeze(), (img.shape[1], img.shape[0]))
    lo, hi = np.percentile(d, 1), np.percentile(d, 99)
    return np.clip((d - lo) / (hi - lo + 1e-6), 0, 1)  # 0 far, 1 near (Depth Anything gives inverse depth)


# ---------------------------------------------------------------- geometry helpers
def mask_of(pts, h, w):
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [pts], 1)
    return m


def width_px(m):
    """Typical bar width: twice the distance from the centre line to the edge."""
    sk = skeletonize(m > 0)
    if not sk.any():
        return 0.0
    dist = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    return float(np.median(2 * dist[sk]))


def kmeans(x, k):
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-4)
    _, lab, cen = cv2.kmeans(np.float32(x), k, None, crit, 10, cv2.KMEANS_PP_CENTERS)
    return lab.ravel(), cen


def label(img, txt, org, bg=(30, 30, 30), s=0.55, fg=(255, 255, 255)):
    (tw, th), _ = cv2.getTextSize(txt, FONT, s, 1)
    x, y = int(org[0]), int(org[1])
    cv2.rectangle(img, (x - 3, y - th - 5), (x + tw + 3, y + 4), bg, -1)
    cv2.putText(img, txt, (x, y), FONT, s, fg, 1, cv2.LINE_AA)


# ---------------------------------------------------------------- bars
def bar_pieces(objs, h, w, dep):
    pieces = []
    for name, pts in objs:
        if name != "bar":
            continue
        m = mask_of(pts, h, w)
        ys, xs = np.nonzero(m)
        if len(xs) < 50:
            continue
        vx, vy, cx, cy = cv2.fitLine(np.column_stack([xs, ys]).astype(np.float32), cv2.DIST_L2, 0, .01, .01).ravel()
        pieces.append(dict(m=m, v=(vx, vy), c=(cx, cy), ang=float(np.degrees(np.arctan2(vy, vx)) % 180),
                           w=width_px(m), z=float(np.median(dep[m > 0])) if dep is not None else None))
    return pieces


def group_directions(pieces):
    """2 directions if the angles really split in two (mesh or cage seen from the side), else 1."""
    if len(pieces) < 4:
        return np.zeros(len(pieces), int)
    a = np.radians([p["ang"] for p in pieces])
    lab, cen = kmeans(np.column_stack([np.cos(2 * a), np.sin(2 * a)]), 2)
    sep = abs(np.degrees(np.arctan2(cen[0, 1], cen[0, 0]) - np.arctan2(cen[1, 1], cen[1, 0]))) / 2
    sep = min(sep, 180 - sep)
    return lab if sep > 20 and min(np.bincount(lab, minlength=2)) >= 2 else np.zeros(len(pieces), int)


def merge_into_bars(pieces, dirs, h, w):
    """Pieces whose lines cross the centre row/column at about the same point are one bar."""
    bars = []
    for g in sorted(set(dirs)):
        grp = [p for p, d in zip(pieces, dirs, strict=True) if d == g]
        vert = np.mean([abs(p["v"][1]) for p in grp]) > np.mean([abs(p["v"][0]) for p in grp])
        ref = h / 2 if vert else w / 2
        for p in grp:
            (ux, uy), (cx, cy) = p["v"], p["c"]
            p["icpt"] = cx + (ref - cy) * ux / (uy or 1e-6) if vert else cy + (ref - cx) * uy / (ux or 1e-6)
        grp.sort(key=lambda p: p["icpt"])
        mw = np.median([p["w"] for p in grp]) or 1
        gaps = np.diff([p["icpt"] for p in grp])
        big = gaps[gaps > 4 * mw]
        G = np.median(big) if len(big) else 8 * mw
        clusters = [[grp[0]]]
        for p in grp[1:]:
            if p["icpt"] - np.mean([q["icpt"] for q in clusters[-1]]) < 0.5 * G:
                clusters[-1].append(p)
            else:
                clusters.append([p])
        for c in clusters:
            m = np.zeros((h, w), np.uint8)
            for p in c:
                m |= p["m"]
            zs = [p["z"] for p in c if p["z"] is not None]
            bars.append(dict(dir=int(g), m=m, vert=bool(vert), ref=float(ref), pieces=len(c),
                             v=tuple(map(float, c[0]["v"])),
                             icpt=float(np.mean([p["icpt"] for p in c])),
                             w=float(np.median([p["w"] for p in c])), z=float(np.median(zs)) if zs else None))
    return bars


def split_layers(bars, min_gap=0.12):
    """Top/bottom layer from depth; only if the two depth groups are clearly apart."""
    zs = np.array([b["z"] for b in bars if b["z"] is not None])
    if len(zs) < 4:
        return False
    lab, cen = kmeans(zs.reshape(-1, 1), 2)
    if abs(cen[0, 0] - cen[1, 0]) < min_gap or min(np.bincount(lab, minlength=2)) < 2:
        return False
    near = int(np.argmax(cen.ravel()))
    for b, k in zip(bars, lab, strict=True):
        b["layer"] = "top" if k == near else "bottom"  # nearest to the camera = top layer
    return True


def spacings(bars, diam, target, tol):
    out = []
    keys = sorted({(b["dir"], b.get("layer", "all")) for b in bars})
    for d, layer in keys:
        G = sorted([b for b in bars if b["dir"] == d and b.get("layer", "all") == layer], key=lambda b: b["icpt"])
        for b0, b1 in zip(G, G[1:], strict=False):
            px = b1["icpt"] - b0["icpt"]
            mm = px * diam / max((b0["w"] + b1["w"]) / 2, 1e-6)  # local scale from the two bars' width
            out.append(dict(dir=d, layer=layer, a=b0, b=b1, px=float(px), mm=float(mm)))
    for d, layer in keys:
        row = [s for s in out if s["dir"] == d and s["layer"] == layer]
        ref = target or (float(np.median([s["mm"] for s in row])) if row else 0)
        for s in row:
            s["ref"] = ref
            s["ok"] = bool(abs(s["mm"] - ref) <= tol * ref)
    return out


# ---------------------------------------------------------------- stirrups
def stirrup_shape(pts, h, w, diam, min_side_mm=40):
    m = mask_of(pts, h, w)
    wpx = width_px(m)
    if wpx <= 0:
        return None
    mmpx = diam / wpx
    sk = cv2.dilate(skeletonize(m > 0).astype(np.uint8), np.ones((3, 3), np.uint8))
    cs, hier = cv2.findContours(sk, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return None
    i = max(range(len(cs)), key=lambda k: cv2.contourArea(cs[k]))
    closed = hier is not None and hier[0][i][2] >= 0  # the centre line makes a loop
    outer = cs[i]
    poly = cv2.approxPolyDP(outer, 0.02 * cv2.arcLength(outer, True), True)[:, 0, :].astype(float)
    n = len(poly)
    sides = [float(np.linalg.norm(poly[(k + 1) % n] - poly[k]) * mmpx) for k in range(n)]
    corners = []
    for k in range(n):
        if min(sides[k - 1], sides[k]) < min_side_mm:
            continue
        v1, v2 = poly[k - 1] - poly[k], poly[(k + 1) % n] - poly[k]
        cosang = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        deg = float(np.degrees(np.arccos(np.clip(cosang, -1, 1))))
        if deg < 30:  # the line turns back on itself: end of the visible part, not a corner
            continue
        if any(np.linalg.norm(poly[k] - np.array(c["xy"])) < 3 * wpx for c in corners):
            continue  # an open line is traced on both sides: same corner twice
        corners.append(dict(xy=poly[k].round().astype(int).tolist(), deg=deg))
    # sides are only reliable when the whole loop is visible; an open (partly hidden) stirrup is traced twice
    sides = [x for x in sides if x >= min_side_mm] if closed else []
    ys, xs = np.nonzero(m)
    return dict(m=m, poly=poly, w=wpx, mmpx=mmpx, c=(float(xs.mean()), float(ys.mean())), closed=bool(closed),
                sides_mm=sides, corners=corners)


def stirrup_spacing(stirrups, bars, diam):
    """Distance between consecutive stirrups along the main bar direction (the column axis)."""
    if len(stirrups) < 2:
        return []
    if bars:  # column axis = mean direction of the most common bar direction
        main = max({b["dir"] for b in bars}, key=lambda d: sum(b["dir"] == d for b in bars))
        vs = [b["v"] for b in bars if b["dir"] == main]
        vs = [v if v[0] * vs[0][0] + v[1] * vs[0][1] >= 0 else (-v[0], -v[1]) for v in vs]
        axis = np.mean(vs, axis=0)
        axis = axis / (np.linalg.norm(axis) + 1e-6)
    else:
        axis = np.array([0, 1.0])
    S = sorted(stirrups, key=lambda s: np.dot(s["c"], axis))
    out = []
    for s0, s1 in zip(S, S[1:], strict=False):
        px = float(np.dot(np.subtract(s1["c"], s0["c"]), axis))
        out.append(dict(a=s0, b=s1, px=px, mm=float(px * diam / ((s0["w"] + s1["w"]) / 2))))
    return out


# ---------------------------------------------------------------- drawing + report
def draw(img, bars, sp, stirrups, ssp, layered, diam):
    a = img.copy()
    ov = a.copy()
    for b in bars:
        ov[b["m"] > 0] = LAYER_COL[b["layer"]] if layered else DIR_COL[b["dir"] % 2]
    for s in stirrups:
        ov[s["m"] > 0] = STIR_COL
    a = cv2.addWeighted(ov, .55, a, .45, 0)
    for s in stirrups:
        cv2.polylines(a, [s["poly"].round().astype(np.int32)], s["closed"], (0, 255, 255), 2)
        for c in s["corners"]:
            label(a, f"{c['deg']:.0f} deg", (c["xy"][0] + 6, c["xy"][1] - 6), bg=(90, 60, 20), s=.45)
    off = {}
    for s in sp:
        k = (s["dir"], s["layer"])
        o = off.setdefault(k, 30 * len(off))
        b0, b1 = s["a"], s["b"]
        if b0["vert"]:
            p0, p1 = (b0["icpt"], b0["ref"] + o), (b1["icpt"], b0["ref"] + o)
        else:
            p0, p1 = (b0["ref"] + o, b0["icpt"]), (b0["ref"] + o, b1["icpt"])
        p0, p1 = tuple(int(t) for t in p0), tuple(int(t) for t in p1)
        cv2.arrowedLine(a, p0, p1, (0, 255, 255), 2, tipLength=.15)
        cv2.arrowedLine(a, p1, p0, (0, 255, 255), 2, tipLength=.15)
        mid = ((p0[0] + p1[0]) // 2 - 12, (p0[1] + p1[1]) // 2 - 6)
        label(a, f"{s['mm']:.0f}", mid, bg=OK if s["ok"] else BAD, s=.45)
    for s in ssp:
        p0 = tuple(int(t) for t in s["a"]["c"])
        p1 = tuple(int(t) for t in s["b"]["c"])
        cv2.line(a, p0, p1, (255, 255, 255), 1, cv2.LINE_AA)
        label(a, f"{s['mm']:.0f} mm", ((p0[0] + p1[0]) // 2 + 8, (p0[1] + p1[1]) // 2), bg=STIR_COL, s=.45)
    y = 32
    lines = [f"bar diameter {diam:g} mm (from plans) -> scale from each bar's width"]
    if layered:
        for L in ("top", "bottom"):
            lines.append(f"{L} layer: {sum(b.get('layer') == L for b in bars)} bars")
    else:
        for d in sorted({b['dir'] for b in bars}):
            lines.append(f"direction {'AB'[d]}: {sum(b['dir'] == d for b in bars)} bars")
    lines.append(f"stirrups: {len(stirrups)}")
    for t in lines:
        label(a, t, (12, y), s=.6)
        y += 30
    return a


def report(path, img, diam, target, tol, bars, sp, stirrups, ssp, layered, source):
    widths = [b["w"] for b in bars] + [s["w"] for s in stirrups]
    res = dict(
        image=path, outlines_from=source, diameter_mm=diam, spacing_target_mm=target, tolerance=tol,
        scale_mm_per_px=dict(min=round(diam / max(widths), 3), max=round(diam / min(widths), 3)) if widths else None,
        layers_from_depth=layered,
        bars=dict(total=len(bars), per_group={}),
        spacing=[dict(direction="AB"[s["dir"]], layer=s["layer"], mm=round(s["mm"]), ok=s["ok"], ref_mm=round(s["ref"]))
                 for s in sp],
        stirrups=[dict(fully_visible=s["closed"], sides_mm=[round(x) for x in s["sides_mm"]],
                       corner_deg=[round(c["deg"]) for c in s["corners"]])
                  for s in stirrups],
        stirrup_spacing_mm=[round(s["mm"]) for s in ssp],
        stirrup_spacing_note=("a value under 3 diameters means two stirrups at the same height (double stirrup "
                              "or a second cage in the photo), not a spacing")
        if any(s["mm"] < 3 * diam for s in ssp) else None,
        checks_to_review=sum(not s["ok"] for s in sp),
        notes=["scale assumes all bars have the given diameter",
               "spacing measured on the centre row/column of the photo",
               "depth layers are relative (Depth Anything), not mm"],
    )
    for b in bars:
        k = f"{b.get('layer', 'all')}/{'AB'[b['dir']]}"
        res["bars"]["per_group"][k] = res["bars"]["per_group"].get(k, 0) + 1
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--weights", help="YOLOv8-seg best.pt")
    src.add_argument("--labels", help="YOLO-seg label file (ground truth, for testing)")
    ap.add_argument("--diameter", type=float, default=12.0, help="bar diameter in mm, from the plans")
    ap.add_argument("--spacing", type=float, default=None, help="spacing from the plans in mm (else median)")
    ap.add_argument("--tol", type=float, default=0.15, help="allowed spacing deviation (0.15 = 15 %%)")
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--depth", action="store_true", help="split bars into 2 layers with Depth Anything V2")
    ap.add_argument("--out", default="measure_result")
    a = ap.parse_args()

    img = cv2.imread(a.image)
    h, w = img.shape[:2]
    objs = from_labels(a.labels, w, h) if a.labels else from_model(a.weights, img, a.conf)
    dep = depth_map(img) if a.depth else None

    pieces = bar_pieces(objs, h, w, dep)
    bars = merge_into_bars(pieces, group_directions(pieces), h, w) if pieces else []
    layered = split_layers(bars) if a.depth else False
    sp = spacings(bars, a.diameter, a.spacing, a.tol)
    stirrups = [s for s in (stirrup_shape(p, h, w, a.diameter) for n, p in objs if n == "stirrup") if s]
    ssp = stirrup_spacing(stirrups, bars, a.diameter)

    cv2.imwrite(a.out + ".jpg", draw(img, bars, sp, stirrups, ssp, layered, a.diameter), [cv2.IMWRITE_JPEG_QUALITY, 88])
    res = report(a.image, img, a.diameter, a.spacing, a.tol, bars, sp, stirrups, ssp, layered,
                 "labels" if a.labels else "model")
    json.dump(res, open(a.out + ".json", "w"), indent=2)
    print(json.dumps({k: res[k] for k in ("bars", "checks_to_review", "stirrup_spacing_mm", "scale_mm_per_px")}))


if __name__ == "__main__":
    main()
