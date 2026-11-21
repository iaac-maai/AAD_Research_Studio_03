"""Check one captured frame against the bar bending schedule.

The schedule is what the engineer says the cage must be (JSON, see
live/schedule_example.json): bar diameter, number of bars, spacing, hook angle
and how long a hook's tail must be, as a multiple of the bar diameter.

Every check is a formula on the detections in mm. The result never says
"approved": a person on site confirms or rejects each fault (human in the
loop), because the camera can miss a hidden bar or read one wrongly.

Column ties: with the column size in the schedule, the Eurocode 8 limits
(codes.py) are added on top. Ties are checked zone by zone ("end" near the
floors, "middle" between); the capture or the CLI says which zone the photo shows.
Every fault also gets a plain fix instruction (fixes.py).

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

from . import codes

DEFAULTS = {
    "spacing_tol_mm": 10.0,   # how far a gap may be off the scheduled spacing
    "diameter_tol_mm": 4.0,   # how far a bar's measured width may be off its diameter
    "hook_angle": 135,        # stirrups and ties in columns and beams: 135 degree hooks
    "hook_tail_factor": 10,   # tail at least this many bar diameters; check your code (EC2 / EC8 / local)
    "parallel_deg": 20.0,     # bars within this angle of the main direction count as one layer
}
BAR, TIE = "bar", "tie"
ZONES = ("end", "middle")


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
    main = _main_angle(angles)
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


def _main_angle(angles):
    return float(np.degrees(np.angle(np.mean(np.exp(2j * np.radians(angles))))) / 2) % 180.0


def code_limits(s):
    """Eurocode 8 limits for this column, or None when the schedule lacks the column size."""
    if not s.get("column_mm"):
        return None
    return codes.column_ties(s["column_mm"], s.get("cover_mm", 30), s["bar_diameter_mm"],
                             s.get("tie_diameter_mm") or 8, s.get("clear_height_mm"), s.get("ductility", "DCM"))


def check_schedule_vs_code(s, limits):
    """Does the schedule itself ask for more than the code allows? A design question, not a site fix."""
    if not limits:
        return []
    out = []
    for zone in ZONES:
        want = (s.get("tie_spacing_mm") or {}).get(zone)
        cap = limits["tie_spacing_max_mm"][zone]
        if want and float(want) > cap:
            out.append(_item("schedule_vs_code", "fail",
                             f"schedule asks for ties every {float(want):g} mm in the {zone} zone; "
                             f"Eurocode 8 ({limits['ductility']}) allows at most {cap:g} mm", float(want), cap))
    if int(s["hook_angle"]) != limits["hook_angle"]:
        out.append(_item("schedule_vs_code", "fail", f"schedule asks for {s['hook_angle']} degree hooks; "
                         "Eurocode 8 needs 135", int(s["hook_angle"]), 135))
    return out


def tie_limit(s, limits, zone):
    """The largest tie gap allowed in this zone: the schedule, capped by the code."""
    want = (s.get("tie_spacing_mm") or {}).get(zone)
    cap = limits["tie_spacing_max_mm"][zone] if limits else None
    vals = [float(v) for v in (want, cap) if v]
    return min(vals) if vals else None


def check_ties(dets, bars, s, mm, limits, zone):
    """Gaps between neighbouring ties, measured along the column's bars."""
    ties = [d for d in dets if d.get("class") == TIE and d.get("axis_centre_px")]
    limit = tie_limit(s, limits, zone)
    if limit is None:
        return []
    if not ties:
        return [_item("tie_spacing", "unknown", "no ties seen in this frame")]
    if len(ties) < 2:
        return [_item("tie_spacing", "unknown", "only one tie in view: frame two or more to measure a gap")]
    bar_angles = [b["angle_deg"] for b in bars if b.get("angle_deg") is not None]
    if bar_angles:
        axis = _main_angle(bar_angles)
    else:  # no bars outlined: the column runs across the ties
        tie_angles = [t["angle_deg"] for t in ties if t.get("angle_deg") is not None] or [0.0]
        axis = (_main_angle(tie_angles) + 90) % 180
    ux, uy = np.cos(np.radians(axis)), np.sin(np.radians(axis))
    if uy < -1e-9 or (abs(uy) <= 1e-9 and ux < 0):  # read top to bottom
        ux, uy = -ux, -uy
    pos = sorted(((t["axis_centre_px"][0] * ux + t["axis_centre_px"][1] * uy) * mm, t["track_id"]) for t in ties)
    tol, out = float(s["spacing_tol_mm"]), []
    first = pos[0][0]
    for (p0, t0), (p1, t1) in zip(pos, pos[1:], strict=False):
        gap = round(float(p1 - p0), 1)
        if gap > limit + tol:
            item = _item("tie_spacing", "fail", f"ties {gap} mm apart in the {zone} zone, at most {limit:g} mm",
                         gap, limit, [t0, t1])
            item.update(from_mm=round(float(p0 - first), 1), to_mm=round(float(p1 - first), 1), zone=zone)
            out.append(item)
    return out or [_item("tie_spacing", "pass", f"{len(pos) - 1} tie gap(s), all within {limit:g} mm ({zone} zone)")]


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


def run(capture: dict, schedule: dict, zone: str | None = None, face: str | None = None) -> dict:
    """All checks for one capture. Returns a result that waits for a person's review.

    zone ("end" or "middle") and face (e.g. "A" or "north") say where the photo was taken;
    they default to the capture's own fields, then to "end" (the strictest) and "".
    """
    from .fixes import instructions

    s = {**DEFAULTS, **schedule}
    zone = zone or capture.get("zone") or "end"
    if zone not in ZONES:
        raise ValueError(f"zone must be one of {ZONES}")
    face = face or capture.get("face") or ""
    limits = code_limits(s)
    if limits:
        s["hook_tail_factor"] = max(float(s["hook_tail_factor"]), 10.0)
    dets = capture.get("detections", [])
    bars = [d for d in dets if d.get("class") == BAR]
    mm, source = scale(capture, s)
    items = check_schedule_vs_code(s, limits)
    if mm is None:
        items += [_item("scale", "unknown", "no markers and no bar outlines: nothing can be measured")]
    else:
        items += (check_count(bars, s) + check_diameter(bars, s, mm, source) + check_spacing(bars, s, mm)
                  + check_ties(dets, bars, s, mm, limits, zone) + check_hooks(dets, s, mm))
    faults = [i for i in items if i["status"] == "fail"]
    result = {"element": s.get("element", ""), "face": face, "zone": zone,
              "scale": {"mm_per_px": mm and round(mm, 4), "source": source},
              "code": limits, "faults": len(faults), "checks": items,
              "review": {"status": "pending", "by": None, "note": "a person confirms or rejects each fault on site"}}
    result["fixes"] = instructions(result)
    return result


def summary(result: dict) -> str:
    lines = [f"{result['element'] or 'element'}: {result['faults']} fault(s), "
             f"scale {result['scale']['mm_per_px']} mm/px from {result['scale']['source']}"]
    for i in result["checks"]:
        ids = f" (ids {', '.join(map(str, i['track_ids']))})" if i["track_ids"] else ""
        lines.append(f"  [{i['status']:>7}] {i['check']}: {i['detail']}{ids}")
    if result.get("fixes"):
        lines.append("To fix:")
        lines += [f"  - {f}" for f in result["fixes"]]
    if result.get("code"):
        lines.append(f"Limits: {result['code']['source']}")
    lines.append("Review: pending. Confirm or reject each fault before the pour.")
    return "\n".join(lines)
