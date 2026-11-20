"""Check one captured frame against the bar bending schedule.

The schedule is what the engineer says the cage must be (JSON, see
live/schedule_example.json): bar diameter, number of bars, spacing, hook angle
and how long a hook's tail must be, as a multiple of the bar diameter.

Every check is a formula on the detections in mm. The result never says
"approved": a person on site confirms or rejects each fault (human in the
loop), because the camera can miss a hidden bar or read one wrongly.

Scale, in order of preference:
  1. markers   the 4 ArUco markers (mm_per_px saved with the capture)
  2. diameter  no markers: the scheduled bar diameter over the bars' median
               width in pixels. Rougher, and it can't then check bar size.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median

import numpy as np

DEFAULTS = {
    "spacing_tol_mm": 10.0,   # how far a gap may be off the scheduled spacing
    "diameter_tol_mm": 4.0,   # how far a bar's measured width may be off its diameter
    "hook_angle": 135,        # stirrups and ties in columns and beams: 135 degree hooks
    "hook_tail_factor": 10,   # tail at least this many bar diameters; check your code (EC2 / EC8 / local)
    "parallel_deg": 20.0,     # bars within this angle of the main direction count as one layer
}
BAR = "bar"


def load_schedule(path: str | Path) -> dict:
    s = {**DEFAULTS, **json.loads(Path(path).read_text())}
    if not s.get("bar_diameter_mm"):
        raise ValueError("schedule needs bar_diameter_mm")
    return s


def _angle_gap(a: float, b: float) -> float:
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def scale(capture: dict, schedule: dict) -> tuple[float | None, str]:
    """mm per pixel and where it came from: 'markers', 'diameter' or 'none'."""
    if capture.get("mm_per_px"):
        return float(capture["mm_per_px"]), "markers"
    widths = [d["width_px"] for d in capture.get("detections", []) if d.get("class") == BAR and d.get("width_px")]
    if widths:
        return float(schedule["bar_diameter_mm"]) / median(widths), "diameter"
    return None, "none"


def _item(check, status, detail, measured=None, expected=None, track_ids=()):
    return {"check": check, "status": status, "detail": detail, "measured": measured,
            "expected": expected, "track_ids": [t for t in track_ids if t is not None]}


def check_count(bars, s):
    n_exp = s.get("bar_count")
    if not n_exp:
        return []
    n = len(bars)
    if n == n_exp:
        return [_item("bar_count", "pass", f"{n} bars, as scheduled", n, n_exp)]
    word = "missing" if n < n_exp else "extra"
    return [_item("bar_count", "fail", f"{abs(n_exp - n)} bar(s) {word}: {n} seen, {n_exp} scheduled", n, n_exp)]


def check_diameter(bars, s, mm, source):
    if source != "markers":
        return [_item("bar_size", "unknown", "no markers in view, so bar size can't be measured independently")]
    d, tol = float(s["bar_diameter_mm"]), float(s["diameter_tol_mm"])
    out = []
    for b in bars:
        if not b.get("width_px"):
            continue
        w = round(b["width_px"] * mm, 1)
        if abs(w - d) > tol:
            out.append(_item("bar_size", "fail", f"bar looks {w} mm wide, scheduled {d:g} mm", w, d, [b["track_id"]]))
    return out or [_item("bar_size", "pass", f"all bars within {tol:g} mm of {d:g} mm")]


def check_spacing(bars, s, mm):
    sp = s.get("bar_spacing_mm")
    if not sp or len(bars) < 2:
        return []
    angles = [b["angle_deg"] for b in bars if b.get("angle_deg") is not None]
    if len(angles) < 2:
        return [_item("spacing", "unknown", "no mask outlines in this capture, so spacing can't be measured")]
    main = float(np.degrees(np.angle(np.mean(np.exp(2j * np.radians(angles))))) / 2) % 180.0
    layer = [b for b in bars
             if b.get("angle_deg") is not None and _angle_gap(b["angle_deg"], main) <= s["parallel_deg"]]
    # distance across the bars: project each bar's centre onto the direction normal to them
    nx, ny = -np.sin(np.radians(main)), np.cos(np.radians(main))
    if nx < -1e-9 or (abs(nx) <= 1e-9 and ny < 0):  # read left to right (top to bottom for flat bars)
        nx, ny = -nx, -ny
    pos = sorted(((b["axis_centre_px"][0] * nx + b["axis_centre_px"][1] * ny) * mm, b["track_id"]) for b in layer)
    tol, out = float(s["spacing_tol_mm"]), []
    for (p0, t0), (p1, t1) in zip(pos, pos[1:], strict=False):
        gap = round(float(p1 - p0), 1)
        if abs(gap - sp) <= tol:
            continue
        if gap > 1.5 * sp:
            detail = f"gap of {gap} mm: a bar is probably missing or shifted here"
        else:
            detail = f"gap of {gap} mm, scheduled {sp:g} ± {tol:g} mm"
        out.append(_item("spacing", "fail", detail, gap, sp, sorted((t0, t1), key=str)))
    return out or [_item("spacing", "pass", f"{len(pos) - 1} gaps, all {sp:g} ± {tol:g} mm")]


def check_hooks(dets, s, mm):
    hooks = [d for d in dets if str(d.get("class", "")).startswith("hook_")]
    if not hooks:
        return [_item("hooks", "unknown", "no hooks seen in this frame")]
    want = int(s["hook_angle"])
    tail_min = float(s["hook_tail_factor"]) * float(s.get("tie_diameter_mm") or s["bar_diameter_mm"])
    out = []
    for h in hooks:
        angle = int(h["class"].split("_")[1]) if h["class"].split("_")[1].isdigit() else None
        if angle != want:
            out.append(_item("hook_angle", "fail", f"{angle} degree hook, scheduled {want}", angle, want,
                             [h["track_id"]]))
        if h.get("length_px"):
            tail = round(h["length_px"] * mm, 1)  # outline length: bend plus tail, so an upper estimate
            if tail < tail_min:
                out.append(_item("hook_tail", "fail", f"hook about {tail} mm long, needs at least {tail_min:g} mm",
                                 tail, tail_min, [h["track_id"]]))
    return out or [_item("hooks", "pass", f"{len(hooks)} hook(s), all {want} degrees and long enough")]


def run(capture: dict, schedule: dict) -> dict:
    """All checks for one capture. Returns a result that waits for a person's review."""
    s = {**DEFAULTS, **schedule}
    dets = capture.get("detections", [])
    bars = [d for d in dets if d.get("class") == BAR]
    mm, source = scale(capture, s)
    if mm is None:
        items = [_item("scale", "unknown", "no markers and no bar outlines: nothing can be measured")]
    else:
        items = (check_count(bars, s) + check_diameter(bars, s, mm, source)
                 + check_spacing(bars, s, mm) + check_hooks(dets, s, mm))
    faults = [i for i in items if i["status"] == "fail"]
    return {"element": s.get("element", ""), "scale": {"mm_per_px": mm and round(mm, 4), "source": source},
            "faults": len(faults), "checks": items,
            "review": {"status": "pending", "by": None, "note": "a person confirms or rejects each fault on site"}}


def summary(result: dict) -> str:
    lines = [f"{result['element'] or 'element'}: {result['faults']} fault(s), "
             f"scale {result['scale']['mm_per_px']} mm/px from {result['scale']['source']}"]
    for i in result["checks"]:
        ids = f" (bars {', '.join(map(str, i['track_ids']))})" if i["track_ids"] else ""
        lines.append(f"  [{i['status']:>7}] {i['check']}: {i['detail']}{ids}")
    lines.append("Review: pending. Confirm or reject each fault before the pour.")
    return "\n".join(lines)
