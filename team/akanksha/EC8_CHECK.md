# Code check: Eurocode 2 and Eurocode 8 in `concrete_evidence/codes.py`

Akanksha. Checked against EN 1992-1-1:2004 and EN 1998-1:2004 (+A1:2013), **recommended values**.
**Spanish values verified from the official documents; European recommended values not yet checked against the printed EN text** (see "Still to verify"). Every result keeps `verify: true`: the app assists a person on site; the project's engineer decides.

## Which code applies

- **Eurocode 2** applies to every concrete column.
- **Eurocode 8** adds stricter rules on top in seismic zones. In very low seismicity (recommended a_g·S ≤ 0.05g, EN 1998-1 3.2.1(5)) it need not be applied, and low-ductility (DCL) buildings may be detailed to Eurocode 2 alone (5.3).
- The schedule says which: `"ductility": "none"` (or `"DCL"`) = Eurocode 2 only; `"DCM"` / `"DCH"` = Eurocode 8 on top of Eurocode 2.

## Rules in the code

| Rule | Value | Clause |
|---|---|---|
| Tie spacing away from the column ends (all cases) | min(20 × bar Ø, smallest column side, 400 mm) | EN 1992-1-1 9.5.3(3) |
| Tie diameter (all cases) | ≥ max(6 mm, bar Ø / 4) | EN 1992-1-1 9.5.3(1) |
| Column ends, Eurocode 2 only | 0.6 × the spacing above, within the larger column side of a slab or beam | EN 1992-1-1 9.5.3(4) |
| End-zone (critical region) length, DCM | max(longest side, clear height / 6, 450 mm) | EN 1998-1 5.4.3.2.2(4) |
| End-zone length, DCH | max(1.5 × longest side, clear height / 6, 600 mm) | EN 1998-1 5.5.3.2.2(4) |
| Short column: clear height / longest side < 3 | the whole height is an end zone | EN 1998-1 5.4.3.2.2(5), 5.5.3.2.2(5) |
| End-zone tie spacing, DCM | min(b₀ / 2, 175 mm, 8 × bar Ø) | EN 1998-1 5.4.3.2.2(11) |
| End-zone tie spacing, DCH | min(b₀ / 3, 125 mm, 6 × bar Ø) | EN 1998-1 5.5.3.2.2(12) |
| b₀ | smallest side of the confined core, to the tie centreline = min side − 2 × cover − tie Ø (cover measured to the tie) | EN 1998-1 5.4.3.2.2 |
| Bars held by a tie corner or cross-tie | ≤ 200 mm (DCM), ≤ 150 mm (DCH) apart | EN 1998-1 5.4.3.2.2(11), 5.5.3.2.2(12) |
| Tie diameter, DCH | also ≥ 0.4 × bar Ø (same steel grade) | EN 1998-1 5.5.3.2.2(12) |
| Hooks, Eurocode 8 | 135°, tail ≥ 10 × tie Ø | EN 1998-1 5.6.1(2)P |

## Corrections made (compared with the first version of this note)

1. **DCH end-zone length** used the DCM formula. Now max(1.5 h_c, H/6, 600).
2. **Short columns** were not handled. Now the whole height is an end zone.
3. **Hook clause** pointed to the spacing clauses; the rule is 5.6.1(2)P. The 10 × tie Ø tail is the code requirement itself, not an extra QA rule.
4. **Eurocode 2 only** mode added for non-seismic sites: ends at 0.6 × the middle spacing, no 135° hook requirement.
5. The schedule is now also checked for **too-thin ties**.

## Examples (400 × 400 mm, Ø16 bars, Ø8 ties, 30 mm cover, clear height 3000 mm)

| | End-zone length | End-zone ties | Middle ties | Hooks |
|---|---|---|---|---|
| Eurocode 2 only | 400 mm | ≤ 192 mm | ≤ 320 mm | no angle required |
| DCM | 500 mm | ≤ 128 mm | ≤ 320 mm | 135°, tail ≥ 80 mm |
| DCH | 600 mm | ≤ 96 mm | ≤ 320 mm | 135°, tail ≥ 80 mm |

All three are in `tests/test_ties.py`.

## Not checked by the app (say so in the pitch)

- EC2 9.5.3(4): the 0.6 reduction also at **lapped joints** of bars over 14 mm. A photo can't see laps reliably.
- Concrete cover, confinement amount (ω_wd, EN 1998-1 5.4.3.2.2(8)), beams, slabs, walls.
- The engaged-bar and tie-diameter limits are checked against the **schedule**, not measured in the photo.

## Spain (verified from the official documents)

| Rule | Spain | Source |
|---|---|---|
| Tie spacing away from the ends | min(15 × smallest bar Ø, 300 mm, smallest side), stricter than 20 × Ø / 400 mm | Código Estructural, Anejo 19, 9.5.3(3), p. 907; AN/UNE-EN 1992-1-1 9.5.3(3) |
| Near slabs, beams and laps | × 0.6; laps when bars are over 14 mm, with at least 3 ties along the lap | Anejo 19, 9.5.3(4) |
| Hooks, Eurocode 2 only | 135° with tail ≥ 5 × tie Ø and ≥ 50 mm, or 90° with tail ≥ 10 × tie Ø and ≥ 70 mm | Anejo 19, 8.5, fig. A19.8.5, p. 883 |
| Very low seismicity (Eurocode 8 not needed) | ag,R < 0.04 g | AN/UNE-EN 1998-1 3.2.1(5) |
| Low seismicity | ag·S ≤ 0.1 g | AN/UNE-EN 1998-1 3.2.1(4) |
| Ductility classes | no geographic limits | AN/UNE-EN 1998-1 5.2.1(5) |
| Seismic values | ag,R and K on a 0.1° grid (table AN.5), interpolated from the nearest grid points | AN/UNE-EN 1998-1 3.2.1(2), AN.5 |
| Seismic standard in force | NCSE-02 (NCSR-23 withdrawn, Dec 2025) | ACIES, 20 Jul 2026 |

**Barcelona:** ag,R ≈ 0.084 g, so Eurocode 8 applies (above the 0.04 g very-low limit).

## Location-based rules (in the code)

The schedule gives only the site city (or the photo's GPS). `concrete_evidence/location.py` finds the country and coordinates (GeoNames city list, CC BY 4.0); in Spain it reads ag,R from the annex grid (`concrete_evidence/reference/es_seismic_grid.csv`, 4,697 points taken from table AN.5): under 0.04 g Eurocode 2 only, otherwise Eurocode 8 (DCM unless the engineer chooses), with the Spanish values above. Outside Spain: European recommended values, said in the result. A place outside the grid (e.g. Madrid) gets Eurocode 8 (DCM) and a note to ask the engineer. The engineer's own choice of ductility always wins.

## Still to verify (needs a person or a document)

1. Every value above against the **printed** EN 1992-1-1 and EN 1998-1 (library or tutor).
2. ~~Spain~~: done, see above. Still open: spot-check a few rows of `es_seismic_grid.csv` against the printed table AN.5 (it was read from the PDF text).
