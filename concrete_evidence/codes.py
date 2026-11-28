"""Code limits for column ties: Eurocode 2 for every column, Eurocode 8 on top in seismic zones.

These are the recommended values as we read them. National annexes can change
some of them (see team/akanksha/EC8_CHECK.md), so every result carries
`verify: True`: an engineer checks the figures against the code text before
anyone relies on them.

Which code: `ductility` says it.
  "none" (or "DCL")  no seismic detailing: Eurocode 2 only. EC8 lets low-ductility (DCL)
                     buildings be detailed to EC2 alone (EN 1998-1 5.3), and in very low
                     seismicity zones EC8 need not be applied at all (3.2.1(5)).
  "DCM", "DCH"       Eurocode 8 medium / high ductility, on top of Eurocode 2: every limit is
                     the stricter of the two codes (in practice Eurocode 8 at the ends).

Column ties (hoops), EN 1992-1-1:2004 and EN 1998-1:2004:
  tie spacing away from the column ends (all cases)
      s <= min(20 x smallest longitudinal bar, smallest column side, 400 mm)   EN 1992-1-1 9.5.3(3)
      Spain: s <= min(15 x smallest longitudinal bar, 300 mm, smallest side)    Código Estructural, Anejo 19 9.5.3(3)
  tie diameter (all cases): at least max(6 mm, bar / 4)                     EN 1992-1-1 9.5.3(1)
  column ends, Eurocode 2 only
      within the larger column side of a slab or beam: s <= 0.6 x the spacing above  9.5.3(4)
  column ends, Eurocode 8 (the critical region)
      DCM  l_cr = max(longest column side, clear height / 6, 450 mm)          EN 1998-1 5.4.3.2.2(4)
      DCH  l_cr = max(1.5 x longest column side, clear height / 6, 600 mm)    EN 1998-1 5.5.3.2.2(4)
      clear height / longest side < 3: the whole column is critical           5.4.3.2.2(5), 5.5.3.2.2(5)
      DCM  s <= min(b0 / 2, 175 mm, 8 x smallest longitudinal bar)            EN 1998-1 5.4.3.2.2(11)
      DCH  s <= min(b0 / 3, 125 mm, 6 x smallest longitudinal bar)            EN 1998-1 5.5.3.2.2(12)
      b0 = smallest side of the confined core, to the tie centreline
      bars held by a tie corner or cross-tie: at most 200 mm (DCM) / 150 mm (DCH) apart
      DCH tie diameter also at least 0.4 x bar (same steel grade for bars and ties)
  hooks, Eurocode 8: 135 degrees, tail at least 10 x tie diameter           EN 1998-1 5.6.1(2)P
  hooks, Eurocode 2 only: 135 degrees with tail >= max(5 x tie, 50 mm), or 90 degrees with
      tail >= max(10 x tie, 70 mm)                                        EN 1992-1-1 8.5, Anejo 19 8.5 (fig. A19.8.5)

Laps (Eurocode 2), any bar:
  lap length l0 = alpha6 x lbd, never less than
      l0,min = max(0.3 x alpha6 x lb,rqd, 15 x bar diameter, 200 mm)   EN 1992-1-1 8.7.3(1)
      The full l0 needs the design stress and concrete, so it comes from the schedule; without it we
      check the floor max(15 x diameter, 200 mm) only.
  clear gap between lapped bars at most 4 x bar diameter or 50 mm      EN 1992-1-1 8.7.2(3)
"""

from __future__ import annotations

SOURCE_EC2 = "Eurocode 2 (EN 1992-1-1), recommended values: verify against your national annex"
SOURCE_EC8 = "Eurocode 8 (EN 1998-1) + Eurocode 2 (EN 1992-1-1), recommended values: verify against your national annex"
SEISMIC = ("DCM", "DCH")
NON_SEISMIC = ("NONE", "DCL")


def lap_min(bar_diameter_mm: float) -> float:
    """The Eurocode 2 floor for a lap length, in mm, without the design values: max(15 x diameter, 200 mm)."""
    return max(15.0 * float(bar_diameter_mm), 200.0)


def lap_max_gap(bar_diameter_mm: float) -> float:
    """The largest clear gap between two lapped bars, in mm: 4 x diameter or 50 mm."""
    return max(4.0 * float(bar_diameter_mm), 50.0)


def column_ties(column_mm, cover_mm: float, bar_diameter_mm: float, tie_diameter_mm: float,
                clear_height_mm: float | None = None, ductility: str = "DCM", country: str | None = None) -> dict:
    """The largest tie spacing allowed in each zone of a column, plus hook and tie rules, in mm.

    cover_mm is the nominal cover to the tie (the outermost steel). `hook_angle` is None
    when the code asks for no particular hook angle (Eurocode 2 only); then
    `hook_tail_min_by_angle_mm` gives the tail each bend needs. country "ES" uses the Spanish
    values (Código Estructural, Anejo 19).
    """
    b, h = (float(v) for v in column_mm)
    dbl, dbw = float(bar_diameter_mm), float(tie_diameter_mm)
    b0 = min(b, h) - 2 * float(cover_mm) - dbw  # confined core, to the tie centreline
    if b0 <= 0:
        raise ValueError(f"column {b:g} x {h:g} mm with {cover_mm:g} mm cover leaves no core")
    hc, lcl = max(b, h), float(clear_height_mm or 0)
    duct = str(ductility or "DCM").upper()
    spain = str(country or "").upper() == "ES"
    if spain:  # Anejo 19 9.5.3(3): s <= min(15 x smallest bar, 300 mm, smallest side)
        middle = min(15 * dbl, 300.0, min(b, h))
    else:
        middle = min(20 * dbl, min(b, h), 400.0)
    tie_min = max(6.0, dbl / 4)
    annex = ", Spanish values (Código Estructural, Anejo 19)" if spain else ""
    if duct in NON_SEISMIC:
        return {"code": "EC2", "ductility": "none", "core_mm": round(b0, 1), "critical_length_mm": round(hc, 1),
                "whole_column_critical": False,
                "tie_spacing_max_mm": {"end": round(0.6 * middle, 1), "middle": round(middle, 1)},
                "engaged_bar_spacing_max_mm": None, "tie_diameter_min_mm": round(tie_min, 1),
                "hook_angle": None, "hook_tail_min_mm": None,
                "hook_tail_min_by_angle_mm": {135: round(max(5 * dbw, 50.0), 1), 90: round(max(10 * dbw, 70.0), 1)},
                "country": "ES" if spain else None, "source": SOURCE_EC2 + annex, "verify": True}
    if duct == "DCH":
        end = min(b0 / 3, 125.0, 6 * dbl)
        l_cr = max(1.5 * hc, lcl / 6, 600.0)
        engaged, tie_min = 150.0, max(tie_min, 0.4 * dbl)
    elif duct == "DCM":
        end = min(b0 / 2, 175.0, 8 * dbl)
        l_cr = max(hc, lcl / 6, 450.0)
        engaged = 200.0
    else:
        raise ValueError("ductility must be none, DCL, DCM or DCH")
    end = min(end, 0.6 * middle)  # Eurocode 2's end rule still applies under Eurocode 8: take the stricter
    whole = bool(lcl) and lcl / hc < 3  # a short column: critical over its full height
    if whole:
        middle, l_cr = end, lcl
    return {"code": "EC8", "ductility": duct, "core_mm": round(b0, 1), "critical_length_mm": round(l_cr, 1),
            "whole_column_critical": whole,
            "tie_spacing_max_mm": {"end": round(end, 1), "middle": round(middle, 1)},
            "engaged_bar_spacing_max_mm": engaged, "tie_diameter_min_mm": round(tie_min, 1),
            "hook_angle": 135, "hook_tail_min_mm": round(10 * dbw, 1), "hook_tail_min_by_angle_mm": None,
            "country": "ES" if spain else None, "source": SOURCE_EC8 + annex, "verify": True}
