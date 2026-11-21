"""Code limits for column ties: Eurocode 8 (earthquake) on top of Eurocode 2.

These are the recommended values as we read them. National annexes can change
them, so every result carries `verify: True`: an engineer checks the figures
against the code text before anyone relies on them.

Column ties (hoops), EN 1998-1 and EN 1992-1-1:
  critical region (both ends of a column), length
      l_cr = max(longest column side, clear height / 6, 450 mm)       EN 1998-1 5.4.3.2.2(4)
  tie spacing in the critical region, medium ductility (DCM)
      s <= min(b0 / 2, 175 mm, 8 x smallest longitudinal bar)         EN 1998-1 5.4.3.2.2(11)
  high ductility (DCH)
      s <= min(b0 / 3, 125 mm, 6 x smallest longitudinal bar)         EN 1998-1 5.5.3.2.2(12)
      b0 = smallest side of the confined core, to the tie centreline
  tie spacing outside the critical region (Eurocode 2)
      s <= min(20 x smallest longitudinal bar, smallest column side, 400 mm)   EN 1992-1-1 9.5.3(3)
  hooks: 135 degrees, tail at least 10 x tie diameter                 EN 1998-1 5.4.3.2.2(11) / 5.5.3.2.2(12)
"""

from __future__ import annotations

SOURCE = "Eurocode 8 (EN 1998-1) + Eurocode 2 (EN 1992-1-1), recommended values: verify against your national annex"


def column_ties(column_mm, cover_mm: float, bar_diameter_mm: float, tie_diameter_mm: float,
                clear_height_mm: float | None = None, ductility: str = "DCM") -> dict:
    """The largest tie spacing allowed in each zone of a column, plus hook rules, in mm."""
    b, h = (float(v) for v in column_mm)
    dbl, dbw = float(bar_diameter_mm), float(tie_diameter_mm)
    b0 = min(b, h) - 2 * float(cover_mm) - dbw  # confined core, to the tie centreline
    if b0 <= 0:
        raise ValueError(f"column {b:g} x {h:g} mm with {cover_mm:g} mm cover leaves no core")
    duct = ductility.upper()
    if duct == "DCH":
        end = min(b0 / 3, 125.0, 6 * dbl)
    elif duct == "DCM":
        end = min(b0 / 2, 175.0, 8 * dbl)
    else:
        raise ValueError("ductility must be DCM or DCH")
    middle = min(20 * dbl, min(b, h), 400.0)
    l_cr = max(b, h, (clear_height_mm or 0) / 6, 450.0)
    return {"ductility": duct, "core_mm": round(b0, 1), "critical_length_mm": round(l_cr, 1),
            "tie_spacing_max_mm": {"end": round(end, 1), "middle": round(middle, 1)},
            "hook_angle": 135, "hook_tail_min_mm": round(10 * dbw, 1), "source": SOURCE, "verify": True}
