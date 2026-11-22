"""Synthetic column-cage renders with exact instance labels (bar, stirrup, hook_90, hook_135).

Each image: a random column cage (section, height, bars, stirrups, hooks), a random camera,
sun + ambient light, a procedural site background, optional ArUco markers. Labels come
from per-instance depth renders compared with the full scene depth, then turned into
YOLO-seg polygons (stirrup loops keyholed so the inside stays unlabelled).

    PYOPENGL_PLATFORM=egl python make_cages.py --n 250 --out out_dir --seed 7
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
import cv2
import numpy as np
import pyrender
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ce_boxes import mask_to_polygon, yolo_line  # noqa: E402

NAMES = ["bar", "stirrup", "hook_90", "hook_135"]
W, H = 960, 720


# ---------- geometry ----------
def tube(points, r, sections=10):
    """Polyline -> one mesh: a cylinder per segment plus a sphere at each joint."""
    parts = []
    pts = [np.asarray(p, float) for p in points]
    for a, b in zip(pts[:-1], pts[1:], strict=True):
        v = b - a
        L = float(np.linalg.norm(v))
        if L < 1e-6:
            continue
        c = trimesh.creation.cylinder(radius=r, height=L, sections=sections)
        z = np.array([0, 0, 1.0])
        d = v / L
        ax = np.cross(z, d)
        s = np.linalg.norm(ax)
        T = np.eye(4)
        if s > 1e-8:
            T[:3, :3] = trimesh.transformations.rotation_matrix(math.atan2(s, float(np.dot(z, d))), ax / s)[:3, :3]
        elif np.dot(z, d) < 0:
            T[:3, :3] = np.diag([1, -1, -1])
        T[:3, 3] = (a + b) / 2
        c.apply_transform(T)
        parts.append(c)
    for p in pts[1:-1]:
        sp = trimesh.creation.icosphere(subdivisions=1, radius=r)
        sp.apply_translation(p)
        parts.append(sp)
    return trimesh.util.concatenate(parts)


def rounded_rect(hx, hz, y, rc, n=4):
    """Closed rounded rectangle in the XZ plane at height y (stirrup path), starting at corner (-hx,-hz)."""
    pts = []
    corners = [(hx, -hz, -math.pi / 2), (hx, hz, 0), (-hx, hz, math.pi / 2), (-hx, -hz, math.pi)]
    for cx, cz, a0 in corners:
        ox = cx - math.copysign(rc, cx)
        oz = cz - math.copysign(rc, cz)
        for k in range(n + 1):
            a = a0 + (math.pi / 2) * k / n
            pts.append((ox + rc * math.cos(a), y, oz + rc * math.sin(a)))
    return pts


def build_cage(rng):
    b = rng.uniform(0.25, 0.5)
    h = b * rng.uniform(0.8, 1.4)
    height = rng.uniform(1.2, 2.4)
    db = rng.choice([0.012, 0.016, 0.020, 0.025])
    ds = rng.choice([0.008, 0.010])
    cover = 0.03
    hx, hz = b / 2 - cover - ds, h / 2 - cover - ds
    nx, nz = int(rng.integers(2, 5)), int(rng.integers(2, 5))
    inst = []  # (class, mesh, colour)
    base = np.array([0.30, 0.19, 0.12]) if rng.random() < 0.75 else np.array([0.26, 0.26, 0.27])

    def rust():
        return np.clip(base * rng.uniform(0.7, 1.25) + rng.normal(0, 0.02, 3), 0, 1)

    shifted = rng.random() < 0.25
    bars = []
    for i in range(nx):
        for j in range(nz):
            if 0 < i < nx - 1 and 0 < j < nz - 1:
                continue
            x = -hx + db / 2 + (2 * hx - db) * i / (nx - 1)
            z = -hz + db / 2 + (2 * hz - db) * j / (nz - 1)
            bars.append([x, z])
    if shifted:
        k = int(rng.integers(len(bars)))
        bars[k][0] += rng.uniform(0.02, 0.05) * rng.choice([-1, 1])
    top = height + rng.uniform(0.1, 0.4)
    for x, z in bars:
        inst.append(("bar", tube([(x, -0.05, z), (x, top, z)], db / 2, 14), rust()))
    # stirrups: dense near the ends
    end, mid = rng.uniform(0.06, 0.12), rng.uniform(0.15, 0.25)
    ys, y = [], 0.05
    while y < height - 0.05:
        ys.append(y)
        y += end if (y < 0.45 or y > height - 0.45) else mid
    missing = int(rng.integers(len(ys))) if rng.random() < 0.3 else -1
    p90 = rng.uniform(0.15, 0.55)
    rc = max(ds * 2.5, db / 2 + ds)
    sx, sz = hx + ds / 2 + db / 2 * 0 + 0.0, hz + ds / 2
    for k, y in enumerate(ys):
        if k == missing:
            continue
        col = rust()
        path = rounded_rect(sx, sz, y, rc)
        n = 4
        corner = np.array([-sx, y, -sz])
        # sharp closing corner at (-sx,-sz): both ends of the bar meet there
        body = [tuple(corner)] + path[: len(path) - n] + [tuple(corner)]
        tail = max(10 * ds, 0.075)
        hook90 = rng.random() < p90
        o = 1.6 * ds
        if hook90:  # tails bent 90 deg, running along the two sides, just inside the legs
            a0 = corner + np.array([o, 0, 0])
            a1 = corner + np.array([0, 0, o])
            t0 = [a0, a0 + np.array([0, 0, 1.0]) * tail]
            t1 = [a1, a1 + np.array([1.0, 0, 0]) * tail]
            hc = "hook_90"
        else:       # tails bent 135 deg, both pointing diagonally into the core
            d = np.array([1.0, 0, 1.0]) / math.sqrt(2)
            a0 = corner + np.array([o, 0, 0])
            a1 = corner + np.array([0, 0, o])
            t0 = [a0, a0 + d * tail]
            t1 = [a1, a1 + d * tail]
            hc = "hook_135"
        tm0, tm1 = tube(t0, ds / 2), tube(t1, ds / 2)
        inst.append(("stirrup", trimesh.util.concatenate([tube(body, ds / 2), tm0, tm1]), col))
        inst.append((hc, tm0, col))
        inst.append((hc, tm1, col))
    return inst, (b, h, height)


# ---------- backgrounds ----------
def noise(rng, h, w, scale):
    small = rng.random((max(2, h // scale), max(2, w // scale))).astype(np.float32)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)


def background(rng):
    kind = rng.choice(["concrete", "formwork", "site", "sky", "soil"], p=[.3, .2, .15, .2, .15])
    if kind == "concrete":
        g = 0.55 + 0.15 * noise(rng, H, W, 64) + 0.08 * noise(rng, H, W, 6)
        img = np.dstack([g * rng.uniform(.95, 1.05), g, g * rng.uniform(.9, 1.0)])
    elif kind == "formwork":
        base = np.array(rng.choice([[0.75, 0.55, 0.3], [0.85, 0.72, 0.4], [0.6, 0.45, 0.3]]))
        img = np.ones((H, W, 3), np.float32) * base
        y = 0
        while y < H:
            hh = int(rng.integers(60, 160))
            img[y:y + hh] *= rng.uniform(0.85, 1.1)
            img[y:y + 2] *= 0.6
            y += hh
        img *= (0.9 + 0.1 * noise(rng, H, W, 8))[..., None]
    elif kind == "site":
        img = np.ones((H, W, 3), np.float32) * np.array([0.6, 0.62, 0.65])
        for _ in range(int(rng.integers(6, 14))):
            x0, y0 = int(rng.integers(0, W)), int(rng.integers(0, H))
            cv2.rectangle(img, (x0, y0), (x0 + int(rng.integers(40, 400)), y0 + int(rng.integers(40, 300))),
                          tuple(float(v) for v in np.full(3, rng.uniform(0.3, 0.8)) * rng.uniform(0.9, 1.1, 3)), -1)
        img = cv2.GaussianBlur(img, (0, 0), rng.uniform(3, 9))
    elif kind == "soil":
        g = 0.35 + 0.2 * noise(rng, H, W, 40) + 0.12 * noise(rng, H, W, 4)
        img = np.dstack([g * 0.75, g * 0.85, g])[..., ::-1].copy()
    else:
        t = np.linspace(0, 1, H, dtype=np.float32)[:, None]
        top, bot = np.array([0.45, 0.62, 0.9]), np.array([0.85, 0.88, 0.92])
        img = (top * (1 - t)[..., None] + bot * t[..., None]) * np.ones((H, W, 1), np.float32)
        gy = int(H * rng.uniform(0.55, 0.85))
        img[gy:] = np.array([0.55, 0.5, 0.45]) * (0.85 + 0.15 * noise(rng, H - gy, W, 10))[..., None]
    return np.clip(img, 0, 1)


ARUCO = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)


def paste_markers(img, rng):
    if rng.random() > 0.6:
        return img
    s = int(rng.integers(50, 110))
    for (x, y) in [(20, 20), (W - s - 20, 20), (20, H - s - 20), (W - s - 20, H - s - 20)]:
        if rng.random() < 0.85:
            m = cv2.aruco.generateImageMarker(ARUCO, int(rng.integers(0, 50)), s - 12)
            m = cv2.copyMakeBorder(m, 6, 6, 6, 6, cv2.BORDER_CONSTANT, value=255)
            x = int(np.clip(x + rng.integers(-10, 30), 0, W - s))
            y = int(np.clip(y + rng.integers(-10, 30), 0, H - s))
            img[y:y + s, x:x + s] = (m[..., None] / 255.0)
    return img


# ---------- rendering ----------
def look_at(eye, target):
    f = target - eye
    f /= np.linalg.norm(f)
    up = np.array([0, 1.0, 0])
    r = np.cross(f, up)
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = r, u, -f, eye
    return M


def render_one(rng, renderer):
    inst, (b, h, height) = build_cage(rng)
    scene = pyrender.Scene(bg_color=[0, 0, 0, 0], ambient_light=rng.uniform(0.25, 0.5, 3))
    nodes, extra = [], []
    for _cls, mesh, col in inst:
        mat = pyrender.MetallicRoughnessMaterial(baseColorFactor=[*col, 1.0], metallicFactor=rng.uniform(0.3, 0.8),
                                                 roughnessFactor=rng.uniform(0.4, 0.8))
        nodes.append(scene.add(pyrender.Mesh.from_trimesh(mesh, material=mat, smooth=False)))
    if rng.random() < 0.5:  # slab / footing under the cage
        slab = trimesh.creation.box(extents=[3, 0.1, 3])
        slab.apply_translation([0, -0.1, 0])
        g = rng.uniform(0.45, 0.7)
        extra.append(scene.add(pyrender.Mesh.from_trimesh(slab, material=pyrender.MetallicRoughnessMaterial(
            baseColorFactor=[g, g, g * 0.97, 1.0], roughnessFactor=0.95))))
    if rng.random() < 0.4:  # close-up on the hook corner of one stirrup
        target = np.array([-b / 2 + 0.06, rng.uniform(0.1, 0.9) * height, -h / 2 + 0.06])
        dist = rng.uniform(0.3, 0.8)
    else:
        target = np.array([rng.uniform(-b / 4, b / 4), rng.uniform(0.25, 0.75) * height, rng.uniform(-h / 4, h / 4)])
        dist = rng.uniform(0.6, 1.7)
    az, el = rng.uniform(0, 2 * math.pi), math.radians(rng.uniform(-15, 35))
    eye = target + dist * np.array([math.cos(el) * math.cos(az), math.sin(el), math.cos(el) * math.sin(az)])
    cam = pyrender.PerspectiveCamera(yfov=math.radians(rng.uniform(45, 70)), aspectRatio=W / H)
    scene.add(cam, pose=look_at(eye, target))
    sun = look_at(target + np.array([rng.uniform(-2, 2), rng.uniform(1.5, 3), rng.uniform(-2, 2)]), target)
    light = pyrender.DirectionalLight(color=[1.0, rng.uniform(.9, 1), rng.uniform(.8, 1)], intensity=rng.uniform(2, 5))
    scene.add(light, pose=sun)
    color, depth = renderer.render(scene, flags=pyrender.RenderFlags.RGBA)
    # per-instance visibility
    labels = []
    for nd in nodes + extra:
        nd.mesh.is_visible = False
    for (cls, _, _), nd in zip(inst, nodes, strict=True):
        nd.mesh.is_visible = True
        d = renderer.render(scene, flags=pyrender.RenderFlags.DEPTH_ONLY)
        nd.mesh.is_visible = False
        vis = (d > 0) & (np.abs(d - depth) < 2e-3)
        if vis.sum() < 60:
            continue
        labels.append((cls, vis.astype(np.uint8)))
    for nd in nodes + extra:
        nd.mesh.is_visible = True
    # compose on background
    bg = paste_markers(background(rng), rng)
    a = color[..., 3:4].astype(np.float32) / 255.0
    img = color[..., :3].astype(np.float32) / 255.0 * a + bg * (1 - a)
    img = np.clip(img * rng.uniform(0.75, 1.2) + rng.normal(0, rng.uniform(0.005, 0.03), img.shape), 0, 1)
    if rng.random() < 0.35:
        img = cv2.GaussianBlur(img, (0, 0), rng.uniform(0.6, 1.6))
    return (img[..., ::-1] * 255).astype(np.uint8), labels


def bridge(m):
    """Join the visible pieces of one instance with 2 px bridges (along occluded parts), so it is one polygon."""
    n, cc, st, cen = cv2.connectedComponentsWithStats(m)
    keep = [k for k in range(1, n) if st[k, cv2.CC_STAT_AREA] >= 25]
    if len(keep) <= 1:
        return (np.isin(cc, keep)).astype(np.uint8)
    out = np.isin(cc, keep).astype(np.uint8)
    pts = {}
    for k in keep:
        cs, _ = cv2.findContours((cc == k).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = np.concatenate(cs)[:, 0, :]
        pts[k] = c[:: max(1, len(c) // 40)]
    done, todo = [keep[0]], keep[1:]
    while todo:  # nearest-neighbour chain (a small spanning tree)
        best = None
        for a in done:
            for b in todo:
                d = ((pts[a][:, None, :] - pts[b][None, :, :]) ** 2).sum(-1)
                i, j = np.unravel_index(int(d.argmin()), d.shape)
                if best is None or d[i, j] < best[0]:
                    best = (d[i, j], pts[a][i], pts[b][j], b)
        cv2.line(out, tuple(int(v) for v in best[1]), tuple(int(v) for v in best[2]), 1, 2)
        done.append(best[3]); todo.remove(best[3])
    return out


def to_lines(labels):
    lines = []
    for cls, m in labels:
        if m.sum() < 60:
            continue
        poly = mask_to_polygon(bridge(m), min_area=40, eps=1.2)
        if poly is None or len(poly) < 4:
            continue
        lines.append(yolo_line(NAMES.index(cls), poly, W, H))
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=250)
    ap.add_argument("--out", default="synthetic")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--start", type=int, default=0)
    a = ap.parse_args()
    out = Path(a.out)
    (out / "train" / "images").mkdir(parents=True, exist_ok=True)
    (out / "train" / "labels").mkdir(parents=True, exist_ok=True)
    names = "".join(f"- {n}\n" for n in NAMES)
    (out / "data.yaml").write_text(f"names:\n{names}nc: {len(NAMES)}\ntrain: train/images\nval: train/images\n")
    renderer = pyrender.OffscreenRenderer(W, H)
    counts = dict.fromkeys(NAMES, 0)
    for i in range(a.start, a.start + a.n):
        rng = np.random.default_rng(a.seed * 100003 + i)
        img, labels = render_one(rng, renderer)
        lines = to_lines(labels)
        if not lines:
            continue
        name = f"syn_{i:04d}"
        quality = [cv2.IMWRITE_JPEG_QUALITY, int(rng.integers(75, 95))]
        cv2.imwrite(str(out / "train" / "images" / f"{name}.jpg"), img, quality)
        (out / "train" / "labels" / f"{name}.txt").write_text("\n".join(lines) + "\n")
        for ln in lines:
            counts[NAMES[int(ln.split()[0])]] += 1
        if i % 25 == 0:
            print(i, counts, flush=True)
    print("done", counts)


if __name__ == "__main__":
    main()
