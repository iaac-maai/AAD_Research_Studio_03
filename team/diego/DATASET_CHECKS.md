# Dataset checks: Roboflow Universe (task 1)

Checked by Diego, Sat 21 Nov 2026, on each project page logged in to Roboflow.

Our Roboflow project: **`concrete-evidence-column-cages`** (instance segmentation), workspace `diegos-workspace-puwbt`, slug `concrete-evidence-column-cages-ft8gc`. Classes: `bar · tie · hook_90 · hook_135`.

## Source 1: sets with outlines

| Project | Licence | Labels | Images | Classes | Verdict |
|---|---|---|---|---|---|
| [roomsegment/rebar-seg](https://universe.roboflow.com/roomsegment/rebar-seg) | CC BY 4.0 | **Polygons**, one per bar | 701 (6 versions) | `rebar` | **Use.** All 701 cloned; `rebar` → `bar`. Mostly slab and wall meshes, not column cages: good for `bar`, teaches nothing about ties or hooks |
| [sitevision-tnmlg/rebar-3dl2l](https://universe.roboflow.com/sitevision-tnmlg/rebar-3dl2l) | CC BY 4.0 | **Polygons**, one per bar | 358 (2 versions) | `rebar`, `rebars` | **Use.** Column starter bars and cages on site: the closest to our columns. 36 cloned so far; `rebar` → `bar` |
| [ntu-ks0ac/rebar-segment-ysgc1](https://universe.roboflow.com/ntu-ks0ac/rebar-segment-ysgc1) | CC BY 4.0 | Boxes | 100 | `intersection`, `spacing` | **Skip.** Boxes of crossings and gaps; none of our classes |
| [new-workspace-eeam1/yolo-eio1c](https://universe.roboflow.com/new-workspace-eeam1/yolo-eio1c) | CC BY 4.0 | Boxes | 73 | `rebar-cross`, `tie-wire` | **Skip.** Tie-wire is not our `tie` (see `LABELLING.md`) |
| [capstone-04lit/rebar-intersection-detect](https://universe.roboflow.com/capstone-04lit/rebar-intersection-detect) | CC BY 4.0 | Boxes | 99 | `intersection` | **Skip.** Crossings only |

## Source 2: box-only sets (boxes → outlines with Smart Polygon)

| Project | Licence | Status |
|---|---|---|
| [stirrup-recognition-dataset](https://universe.roboflow.com/jiawens-workspace/stirrup-recognition-dataset) | CC BY 4.0 | **Use.** One box per loose stirrup on a plain floor, hooks visible: the best source for `tie` and hooks. Forked to `diegos-workspace-puwbt/stirrup-recognition-dataset-w9jig`, version 1 (no preprocessing). `box_to_polygons.ipynb` turns the boxes into `tie` outlines with SAM 2.1 |
| [Column Tie Detection](https://universe.roboflow.com/column-tie-detection/custom-workflow-object-detection-yhfbh) | CC BY 4.0 | **Skip.** Its `Tie` / `No Tie` / `PartialTie` boxes are small boxes on **tie-wire knots at bar crossings**, not stirrups |
| [steelbinding-for-rcc/SteelBindings](https://universe.roboflow.com/steelbinding-for-rcc/steelbindings) | CC BY 4.0 | **Weak.** `Stirrup` / `Lateral-Ties` boxes cover a whole zone of stirrups, not one each. 303 cloned into "Unassigned"; leave them out of the dataset (or label a few by hand) |

## Project state, Sat 21 Nov 15:30

- 1,040 images in the project; 737 in the dataset (701 rebar-seg + 36 SiteVision), 303 SteelBindings unassigned.
- `bar`: 15,104 outlines. `tie`, `hook_90`, `hook_135`: 0. **All tie and hook labels still have to come from us** (source 2, web photos, fab lab).

## Credits (CC BY 4.0)

- rebar-seg, by roomsegment, Roboflow Universe (2024).
- Rebar, by SiteVision, Roboflow Universe.
- SteelBindings, by steelbinding-for-rcc, Roboflow Universe.
- stirrup-recognition-dataset, by jiawens Workspace, Roboflow Universe.
