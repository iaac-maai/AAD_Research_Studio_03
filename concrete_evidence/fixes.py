"""Turn each fault from the check into one instruction for the crew.

Read on a phone next to the cage, so one line each: what to do, where, and in
brackets why (what was found against what is needed). The element and face are
shown once with the result, not in every line.
Positions are in mm below the top tie in view, because the photo alone can't say
where the floor is. Every instruction waits for the same human review as its fault.
"""

from __future__ import annotations

import math


def _n(n: int, word: str) -> str:
    """'1 tie', '2 ties'."""
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _ids(item) -> str:
    return " and ".join(str(t) for t in item.get("track_ids", []))


def _ask(item: dict) -> str:
    """Drawing against the code: a question for the engineer, with the two numbers."""
    d, m, e = item.get("detail", ""), item.get("measured"), item.get("expected")
    if "hooks" in d:
        return f"Ask the engineer: the drawing has {m}° hooks, the code needs {e}°."
    if "mm ties" in d:
        return f"Ask the engineer: the drawing has Ø{m:g} ties, the code needs at least Ø{e:g}."
    if "ties every" in d:
        return f"Ask the engineer: the drawing has ties every {m:g} mm, the code allows {e:g} mm max."
    return "Ask the engineer before the pour."


def _fix(item: dict) -> str | None:
    c, m, e = item["check"], item.get("measured"), item.get("expected")
    if c == "bar_count":
        if m < e:
            return f"Add {_n(e - m, 'bar')} (found {m}, drawing needs {e})."
        return f"Check the {_n(m - e, 'extra bar')} before removing anything (found {m}, drawing needs {e})."
    if c == "spacing":
        if m > 1.5 * e:
            return f"Add a bar between bars {_ids(item)} (gap {m:g} mm, should be {e:g} mm)."
        return f"Move bars {_ids(item)} to {e:g} mm apart (now {m:g} mm)."
    if c == "bar_size":
        return f"Check bar {_ids(item)}: it looks Ø{round(m)}, the drawing says Ø{e:g}."
    if c == "tie_spacing":
        n = max(1, math.ceil(m / e) - 1)  # ties to add so no gap is over the limit
        return (f"Add {_n(n, 'tie')} {item['from_mm']:g}–{item['to_mm']:g} mm below the top tie "
                f"(gap {m:g} mm, max {e:g} mm here).")
    if c == "hook_angle":
        return f"Rebend hook {_ids(item)} to {e}° (now {m}°; 90° hooks open in earthquakes)."
    if c == "hook_tail":
        return f"Replace the tie with hook {_ids(item)} (tail {m:g} mm, needs {e:g} mm)."
    if c == "lap_length":
        return f"Add a splice bar beside bars {_ids(item)}, lapping each by {e:g} mm (overlap now {m:g} mm)."
    if c == "schedule_vs_code":
        return _ask(item)
    return None


def instructions(result: dict) -> list[str]:
    """One instruction per fault, in the order of the checks."""
    fails = [i for i in result["checks"] if i["status"] == "fail"]
    gap = any(i["check"] == "spacing" and i["measured"] > 1.5 * i["expected"] for i in fails)
    if gap:  # the gap line already says where to add the bar, so the bare count line would repeat it
        fails = [i for i in fails if not (i["check"] == "bar_count" and i["measured"] < i["expected"])]
    out, skip = [], set()
    for k, item in enumerate(fails):
        if k in skip:
            continue
        moved = _shifted_bar(item, fails[k + 1] if k + 1 < len(fails) else None)
        if moved:
            out.append(moved)
            skip.add(k + 1)
            continue
        text = _fix(item)
        if text:
            out.append(text)
    return out


def _shifted_bar(a: dict, b: dict | None) -> str | None:
    """One bar out of place makes two spacing faults side by side: one gap too wide, the next too
    narrow, sharing that bar. Say it once: which bar, how far, towards which neighbour."""
    if not b or a["check"] != "spacing" or b["check"] != "spacing":
        return None
    shared = set(a.get("track_ids", [])) & set(b.get("track_ids", []))
    e = a.get("expected")
    if len(shared) != 1 or not e or b.get("expected") != e:
        return None
    m1, m2 = a["measured"], b["measured"]
    if max(m1, m2) > 1.5 * e or (m1 - e) * (m2 - e) >= 0:
        return None  # a missing bar, or both gaps off the same way: not one shifted bar
    bar = shared.pop()
    wide = a if m1 > m2 else b  # move the bar towards the neighbour across the wide gap
    towards = next(t for t in wide["track_ids"] if t != bar)
    off = round(abs(m1 - m2) / 2)
    return f"Move bar {bar} {off:g} mm towards bar {towards} (gaps {m1:g} and {m2:g} mm, should be {e:g} mm)."
