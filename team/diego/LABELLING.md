# Labelling notes

Four classes, all **polygons**: `bar · stirrup · hook_90 · hook_135`.

| Class | What it is | Label it |
|---|---|---|
| `bar` | A longitudinal bar | One polygon per visible bar. Two bars that cross are two polygons |
| `stirrup` | **The stirrup** (column tie / link): the closed loop around the longitudinal bars | One polygon per visible stirrup, **including** its bent ends (that's what Segment Anything outlines from a box, so hand and auto labels match). Leave the inside of the loop unlabelled |
| `hook_90` | Bent end of a stirrup at about 90° | Its own polygon, from the bend to the tip, drawn **on top of** the `stirrup` (overlap is fine in instance segmentation) |
| `hook_135` | Bent end of a stirrup at about 135° (the seismic hook Eurocode 8 asks for) | Same |

**The class is called `stirrup` (renamed from `tie` on 22 Nov 2026).** "Tie" was ambiguous: it was read both as the stirrup and as the tie-wire at a crossing. The Roboflow project now uses `stirrup`; it had 0 labels when renamed, so nothing was lost. Tie-wire at crossings is **not labelled**.

**For the app (Akshat):** `concrete_evidence/check.py` still calls this class `tie` internally (`check_ties` measures the gaps between stirrups against the Eurocode 8 spacing per zone). No code change needed: set `CLASS_RENAME=stirrup=tie` on the model server when Diego's model goes in (as `team/akshat/MONDAY.md` step 3 already allows).

## Rules

- Don't outline hidden parts; don't guess where a bar runs.
- Smart Polygon for the first outline, then fix the edges by hand.
- Box-only sets: only **stirrup-recognition** is worth converting (one box per stirrup). `box_to_polygons.ipynb` does it with SAM 2.1 and uploads the outlines as `stirrup` (batch `sam_stirrups`). Column Tie Detection boxes are tie-wire knots, and SteelBindings boxes cover whole zones of stirrups: neither is used.
- The photos of one fab-lab cage (about 15) are tagged `test` and never trained on.

## Web photos (source 3)

60 Wikimedia Commons photos, licences in `sources.csv` (CC0, public domain, CC BY, CC BY-SA). Many are **pile and footing cages** rather than columns: still useful for `bar` and `stirrup`, but hooks are rarely visible. Best for stirrups and hooks: `wm_103`, `wm_109`, `wm_110`, `wm_187`, `wm_207`, `wm_251`, `wm_253`, `wm_257`, `wm_258`, `wm_285`, `wm_309`. Faces get blurred before upload (`python -m concrete_evidence.privacy`).
