"""Check one captured frame against the bar bending schedule.

The schedule is what the engineer says the cage must be (JSON, see
live/schedule_example.json): bar diameter, number of bars, spacing, hook angle
and how long a hook's tail must be, as a multiple of the bar diameter.

Every check is a formula on the detections in mm. The result never says
"approved": a person on site confirms or rejects each fault (human in the
loop), because the camera can miss a hidden bar or read one wrongly.

Column ties: with the column size in the schedule, the code limits (Eurocode 2, plus
Eurocode 8 unless the schedule says ductility "none")
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

from . import axis, codes, location

DEFAULTS = {
    "spacing_tol_mm": 25.0,   # bars: how far a gap may be off the drawing. Wide on purpose: only a bar
                              # clearly out of place or missing is reported, not mm the camera can't see
    "diameter_tol_mm": 5.0,   # bars: only an obvious size mix-up (e.g. 10 for 16), not neighbouring sizes
    "tie_tol_mm": 10.0,       # ties: how far a gap may go over its limit (ties and hooks are the focus)
    "hook_angle": 135,        # stirrups and ties in columns and beams: 135 degree hooks
    "hook_tail_factor": 10,   # tail at least this many bar diameters; check your code (EC2 / EC8 / local)
    "parallel_deg": 20.0,     # bars within this angle of the main direction count as one layer
    "bend_tol_deg": 20.0,     # a measured bend this far off the scheduled hook angle is a fault to confirm
    "lap_parallel_deg": 10.0, # two bars this close to parallel, side by side, may be a lap
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
    # across the axis when the outline has one (the width the page shows), else the box's short side
    widths = [d.get("thickness_px") or d["width_px"] for d in capture.get("detections", [])
              if d.get("class") == BAR and (d.get("thickness_px") or d.get("width_px"))]
    if widths:
        return float(schedule["bar_diameter_mm"]) / median(widths), "diameter"
    return None, "none"


def _item(check, status, detail, measured=None, expected=None, track_ids=()):
    return {"check": check, "status": status, "detail": detail, "measured": measured,
            "expected": expected, "track_ids": [t for t in track_ids if t is not None]}


def _layer(bars, s):
    """The bars running in the main direction (one layer of a mat or face); all bars when there are no outlines."""
    angles = [b["angle_deg"] for b in bars if b.get("angle_deg") is not None]
    if len(angles) < 2:
        return list(bars)
    main = _main_angle(angles)
    return [b for b in bars if b.get("angle_deg") is None or _angle_gap(b["angle_deg"], main) <= s["parallel_deg"]]


def _one_per_position(bars, laps):
    """Bars lapped side by side stand in one bar position: keep the longest of each lapped group (the bar that
    runs on), drop the others. Groups chain (a bar lapped on both sides), so they are joined first."""
    group = {b["track_id"]: b["track_id"] for b in bars}

    def root(i):
        while group[i] != i:
            i = group[i]
        return i

    for a, b in laps:
        if a in group and b in group:
            group[root(a)] = root(b)
    best = {}
    for b in bars:
        r = root(b["track_id"])
        if r not in best or (b.get("length_px") or 0) > (best[r].get("length_px") or 0):
            best[r] = b
    return list(best.values())


def check_count(bars, s, laps=frozenset()):
    """Bars in the main direction (bars running across, e.g. the other way of a slab mat, aren't counted).
    Two bars lapped side by side stand in one bar position, so each lap counts once."""
    n_exp = s.get("bar_count")
    if not n_exp:
        return []
    n = len(_one_per_position(_layer(bars, s), laps))
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


def check_spacing(bars, s, mm, laps=frozenset()):
    """Gaps between neighbouring bars across the layer. `laps` are pairs of ids lapped side by side
    (check_laps): they stand in one bar position (the bar that runs on), so they give one gap, not two."""
    sp = s.get("bar_spacing_mm")
    if not sp or len(bars) < 2:
        return []
    angles = [b["angle_deg"] for b in bars if b.get("angle_deg") is not None]
    if len(angles) < 2:
        return [_item("spacing", "unknown", "no mask outlines in this capture, so spacing can't be measured")]
    main = _main_angle(angles)
    layer = _one_per_position([b for b in bars if b.get("angle_deg") is not None
                               and _angle_gap(b["angle_deg"], main) <= s["parallel_deg"]], laps)
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


def place_rules(s):
    """Where the column is (schedule "city", or "lat"/"lon" from the photo) and which rules follow,
    or None when the schedule gives no place. The engineer's own "ductility" always wins."""
    if not (s.get("city") or (s.get("lat") is not None and s.get("lon") is not None)):
        return None
    return location.rules_for(s.get("city"), s.get("country"), s.get("lat"), s.get("lon"), s.get("ductility"))


def code_limits(s, place=None):
    """Code limits for this column (codes.py), or None when the schedule lacks the column size."""
    if not s.get("column_mm"):
        return None
    ductility = (place or {}).get("ductility") or s.get("ductility", "DCM")
    country = (place or {}).get("national_annex") or s.get("country")
    return codes.column_ties(s["column_mm"], s.get("cover_mm", 30), s["bar_diameter_mm"],
                             s.get("tie_diameter_mm") or 8, s.get("clear_height_mm"), ductility, country)


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
                             f"{_code_name(limits)} allows at most {cap:g} mm", float(want), cap))
    if limits["hook_angle"] and int(s["hook_angle"]) != limits["hook_angle"]:
        out.append(_item("schedule_vs_code", "fail", f"schedule asks for {s['hook_angle']} degree hooks; "
                         f"Eurocode 8 needs {limits['hook_angle']}", int(s["hook_angle"]), limits["hook_angle"]))
    tie = s.get("tie_diameter_mm")
    if tie and limits.get("tie_diameter_min_mm") and float(tie) < limits["tie_diameter_min_mm"]:
        out.append(_item("schedule_vs_code", "fail", f"schedule asks for {float(tie):g} mm ties; "
                         f"{_code_name(limits)} needs at least {limits['tie_diameter_min_mm']:g} mm",
                         float(tie), limits["tie_diameter_min_mm"]))
    return out


def _code_name(limits) -> str:
    if limits.get("code") == "EC2":
        return "Eurocode 2"
    return f"Eurocode 8 ({limits['ductility']})"


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
    tol, out = float(s["tie_tol_mm"]), []
    first = pos[0][0]
    for (p0, t0), (p1, t1) in zip(pos, pos[1:], strict=False):
        gap = round(float(p1 - p0), 1)
        if gap > limit + tol:
            item = _item("tie_spacing", "fail", f"ties {gap} mm apart in the {zone} zone, at most {limit:g} mm",
                         gap, limit, [t0, t1])
            item.update(from_mm=round(float(p0 - first), 1), to_mm=round(float(p1 - first), 1), zone=zone)
            out.append(item)
    return out or [_item("tie_spacing", "pass", f"{len(pos) - 1} tie gap(s), all within {limit:g} mm ({zone} zone)")]


def check_hooks(dets, s, mm, limits=None):
    """Hook angle and tail. The model names the hook (hook_90 / hook_135); the axis polyline measures the bend
    and the tail (axis.py). Without an axis the tail falls back to the outline length, an upper estimate."""
    hooks = [d for d in dets if str(d.get("class", "")).startswith("hook_")]
    if not hooks:
        return [_item("hooks", "unknown", "no hooks seen in this frame")]
    want, tol = int(s["hook_angle"]), float(s["bend_tol_deg"])
    by_angle = (limits or {}).get("hook_tail_min_by_angle_mm")  # Eurocode 2 only: the tail depends on the bend
    out = []
    for h in hooks:
        angle = int(h["class"].split("_")[1]) if h["class"].split("_")[1].isdigit() else None
        tail_min = float(s["hook_tail_factor"]) * float(s.get("tie_diameter_mm") or s["bar_diameter_mm"])
        if by_angle and angle in by_angle:  # the code's tail for this bend, raised only by a drawing that asks for more
            tail_min = max(by_angle[angle], tail_min if s.get("_tail_on_drawing") else 0)
        bend = max(h["bends_deg"]) if h.get("bends_deg") else None
        seen = f" (measured bend about {bend:.0f} degrees in the photo)" if bend is not None else ""
        if angle != want:
            out.append(_item("hook_angle", "fail", f"{angle} degree hook, scheduled {want}{seen}", angle, want,
                             [h["track_id"]]))
        elif bend is not None and abs(bend - want) > tol:
            out.append(_item("hook_angle", "fail",
                             f"hook bent about {bend:.0f} degrees in the photo, scheduled {want} ± {tol:g}: "
                             "check it square-on, a slanted view changes the angle", round(bend), want,
                             [h["track_id"]]))
        t_px = axis.tail_px(h) if h.get("segments_px") else h.get("length_px")
        if t_px:
            tail = round(t_px * mm, 1)
            if tail < tail_min:
                out.append(_item("hook_tail", "fail", f"hook tail about {tail} mm, needs at least {tail_min:g} mm",
                                 tail, tail_min, [h["track_id"]]))
    return out or [_item("hooks", "pass", f"{len(hooks)} hook(s), all {want} degrees and long enough")]


def _ends(d):
    """The two ends of a piece's axis (or of its rotated box when there is no axis), in px."""
    if d.get("axis_px") and len(d["axis_px"]) >= 2:
        return np.array(d["axis_px"][0], float), np.array(d["axis_px"][-1], float)
    if d.get("axis_centre_px") and d.get("length_px") and d.get("angle_deg") is not None:
        c, half = np.array(d["axis_centre_px"], float), d["length_px"] / 2
        u = np.array([np.cos(np.radians(d["angle_deg"])), np.sin(np.radians(d["angle_deg"]))])
        return c - u * half, c + u * half
    return None


def check_laps(bars, s, mm):
    """Lapped bars: two parallel bars side by side whose ends are staggered. The overlap is measured along
    their axes and checked against the schedule's lap length, or at least the Eurocode 2 floor
    l0,min = max(15 x diameter, 200 mm) when the schedule gives none. No model training: it's a formula."""
    phi = float(s["bar_diameter_mm"])
    near = codes.lap_max_gap(phi) + phi          # centre to centre: clear gap allowed plus one bar
    if s.get("bar_spacing_mm"):                  # neighbours at the scheduled spacing are a layer, not a lap
        near = min(near, 0.5 * float(s["bar_spacing_mm"]))
    need = float(s.get("lap_length_mm") or codes.lap_min(phi))
    src = "schedule" if s.get("lap_length_mm") else "Eurocode 2 minimum, max(15 x diameter, 200 mm)"
    pieces = [(b, e) for b in bars if (e := _ends(b)) is not None]
    out = []
    for i, (a, (a0, a1)) in enumerate(pieces):
        for b, (b0, b1) in pieces[i + 1:]:
            ua, ub = a1 - a0, b1 - b0
            la, lb = np.linalg.norm(ua), np.linalg.norm(ub)
            if la == 0 or lb == 0:
                continue
            ua, ub = ua / la, ub / lb
            if abs(float(np.dot(ua, ub))) < np.cos(np.radians(s["lap_parallel_deg"])):
                continue
            if np.dot(ua, ub) < 0:
                b0, b1 = b1, b0
            n = np.array([-ua[1], ua[0]])
            across = abs(float(np.dot((b0 + b1) / 2 - (a0 + a1) / 2, n))) * mm
            if across > near:
                continue
            ta, tb = (0.0, float(la)), tuple(sorted((float(np.dot(b0 - a0, ua)), float(np.dot(b1 - a0, ua)))))
            overlap = (min(ta[1], tb[1]) - max(ta[0], tb[0])) * mm
            # a lap shows as staggered ends: at least one bar ends beside the other. A starter usually starts at
            # the slab surface with its column bar, so only its top end is staggered; that is still a lap.
            # Both ends level (often both cut by the photo's edge) shows no lap: two bars, too close.
            m = 2 * phi
            staggered = abs(ta[0] - tb[0]) * mm > m or abs(ta[1] - tb[1]) * mm > m
            if overlap <= 0 or not staggered:
                continue
            ov = round(overlap, 1)
            ids = sorted((a["track_id"], b["track_id"]), key=str)
            status = "fail" if ov < need else "pass"
            word = "need at least" if status == "fail" else "at least"
            out.append(_item("lap_length", status, f"bars overlap about {ov} mm, {word} {need:g} mm ({src})",
                             ov, need, ids))
    return out


def run(capture: dict, schedule: dict, zone: str | None = None, face: str | None = None) -> dict:
    """All checks for one capture. Returns a result that waits for a person's review.

    zone ("end" or "middle") and face (e.g. "A" or "north") say where the photo was taken;
    they default to the capture's own fields, then to "end" (the strictest) and "".
    """
    from .fixes import instructions

    # a drawing that asks for its own tail length (not just the default, which callers may have merged in)
    own_tail = schedule.get("hook_tail_factor") not in (None, DEFAULTS["hook_tail_factor"])
    s = {**DEFAULTS, **schedule, "_tail_on_drawing": own_tail}
    zone = zone or capture.get("zone") or "end"
    if zone not in ZONES:
        raise ValueError(f"zone must be one of {ZONES}")
    face = face or capture.get("face") or ""
    place = place_rules(s)
    limits = code_limits(s, place)
    if limits and limits["hook_angle"]:  # Eurocode 8: tails at least 10 x tie diameter
        s["hook_tail_factor"] = max(float(s["hook_tail_factor"]), 10.0)
    dets = capture.get("detections", [])
    bars = [d for d in dets if d.get("class") == BAR]
    mm, source = scale(capture, s)
    items = check_schedule_vs_code(s, limits)
    if mm is None:
        items += [_item("scale", "unknown", "no markers and no bar outlines: nothing can be measured")]
    else:
        laps = check_laps(bars, s, mm)
        pairs = frozenset(tuple(i["track_ids"]) for i in laps)
        items += (check_count(bars, s, pairs) + check_diameter(bars, s, mm, source) + check_spacing(bars, s, mm, pairs)
                  + check_ties(dets, bars, s, mm, limits, zone) + check_hooks(dets, s, mm, limits) + laps)
    faults = [i for i in items if i["status"] == "fail"]
    result = {"element": s.get("element", ""), "face": face, "zone": zone, "place": place,
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
    if result.get("place"):
        lines.append(f"Place: {result['place']['note']}")
    lines.append("Review: pending. Confirm or reject each fault before the pour.")
    return "\n".join(lines)
