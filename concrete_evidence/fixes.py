"""Turn each fault from the check into one plain instruction for the crew.

The check says what is wrong ("ties 230 mm apart, at most 100 mm"); this says
what to do about it ("add a tie between ...").
Positions are in mm from the first tie in view, reading down the photo, because
the photo alone can't say where the floor is. Every instruction waits for the
same human review as the fault it comes from.
"""

from __future__ import annotations

import math


def _ids(item) -> str:
    return " and ".join(str(t) for t in item.get("track_ids", []))


def _fix(item: dict) -> str | None:
    c, m, e = item["check"], item.get("measured"), item.get("expected")
    if c == "bar_count":
        if m < e:
            return f"Add {e - m} bar(s): {m} seen, {e} scheduled. The spacing faults show where."
        return f"Check the {m - e} extra bar(s): {m} seen, {e} scheduled."
    if c == "spacing":
        if m > 1.5 * e:
            return f"Add the missing bar between bars {_ids(item)} (gap {m:g} mm, should be {e:g} mm)."
        return f"Move bars {_ids(item)} to {e:g} mm apart (now {m:g} mm)."
    if c == "bar_size":
        return f"Bar {_ids(item)} looks {m:g} mm: check it, and replace it with a {e:g} mm bar if it is wrong."
    if c == "tie_spacing":
        n = max(1, math.ceil(m / e) - 1)  # ties to add so no gap is over the limit
        where = f"between {item['from_mm']:g} and {item['to_mm']:g} mm from the first tie in view"
        return f"Add {n} tie(s) {where} (gap {m:g} mm, at most {e:g} mm in the {item.get('zone', '')} zone)."
    if c == "hook_angle":
        return f"Rebend hook {_ids(item)} to {e} degrees (now {m})."
    if c == "hook_tail":
        return f"Hook {_ids(item)} tail is about {m:g} mm, needs {e:g} mm: replace the tie."
    if c == "schedule_vs_code":
        return f"Ask the engineer before the pour: {item['detail']}."
    return None


def instructions(result: dict) -> list[str]:
    """One instruction per fault, prefixed with the element and face when known."""
    where = ", ".join(x for x in (result.get("element"), result.get("face") and f"face {result['face']}") if x)
    prefix = f"{where}: " if where else ""
    out = []
    for item in result["checks"]:
        if item["status"] == "fail":
            text = _fix(item)
            if text:
                out.append(prefix + text)
    return out
