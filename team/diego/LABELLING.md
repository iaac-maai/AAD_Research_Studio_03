# Labelling notes

Four classes, all **polygons**: `bar · tie · hook_90 · hook_135`.

| Class | What it is | Label it |
|---|---|---|
| `bar` | A longitudinal bar | One polygon per visible bar. Two bars that cross are two polygons |
| `tie` | **The stirrup** (column tie / link): the closed loop around the longitudinal bars | One polygon per visible stirrup, without its bent ends |
| `hook_90` | Bent end of a stirrup at about 90° | Its own polygon, from the bend to the tip |
| `hook_135` | Bent end of a stirrup at about 135° (the seismic hook Eurocode 8 asks for) | Same |

**`tie` is the stirrup, not the tie-wire at a crossing.** Confirmed 21 Nov from the code: `concrete_evidence/check.py` (`check_ties`) sorts every `tie` along the column and measures the gaps against the Eurocode 8 tie spacing per zone. Tie-wire knots labelled as `tie` would be counted as extra stirrups and break that check. Tie-wire is **not labelled**. (`docs/HANDOVER_DIEGO.md` still says "the wire at a crossing": that line is out of date.)

## Rules

- Don't outline hidden parts; don't guess where a bar runs.
- Smart Polygon for the first outline, then fix the edges by hand.
- Box-only sets (SteelBindings, Column Tie, stirrups): `Lateral-Ties` / `Stirrup` / `Tie` boxes become `tie` polygons; delete `Beam`, `Column`, `No Tie`, `PartialTie` boxes.
- The photos of one fab-lab cage (about 15) are tagged `test` and never trained on.

## Web photos (source 3)

60 Wikimedia Commons photos, licences in `sources.csv` (CC0, public domain, CC BY, CC BY-SA). Many are **pile and footing cages** rather than columns: still useful for `bar` and `tie`, but hooks are rarely visible. Best for ties and hooks: `wm_103`, `wm_109`, `wm_110`, `wm_187`, `wm_207`, `wm_251`, `wm_253`, `wm_257`, `wm_258`, `wm_285`, `wm_309`. Faces get blurred before upload (`python -m concrete_evidence.privacy`).
