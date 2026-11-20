# Handover: supervised rebar model (Diego)

Paste this file into your own Claude session as the starting brief. Everything it refers to is in this repo.

## Goal, for next week's presentation

Train a **supervised segmentation model** that outlines every piece of rebar in a column cage, labelled by us as `bar · tie · hook_90 · hook_135`, and get real scores for the slides (precision, recall, mask mAP50 on frames it has never seen). The project is **only rebar**: one check, bar by bar, before the pour.

Supervised means the model learns from examples we labelled by hand. Two stages:

1. **Pre-train on SORD**: open synthetic rebar images, CC BY-NC 4.0. They teach what rebar looks like. Their classes are `intersection` and `spacing` (the gaps between bars), not bars.
2. **Fine-tune on our frames**: the classes we actually check, on real camera frames. This stage makes bar-by-bar checking possible, and it gives the numbers for the slides.

## Status on 20 Nov 2026 (Akshat)

| Done | Where |
|---|---|
| Dataset research, licences checked; open-licence only for training | `datasets/CATALOGUE.md` |
| One script for every stage, from video to the live view | `pipeline.py`, guide in `PIPELINE.md` |
| SORD shards 0–1 downloaded and converted (200 images, ~24,000 objects) | `data/sord_yolo/` on Akshat's laptop (not in git) |
| 3-epoch CPU test training, to prove the pipeline | mask mAP50 0.093 / precision 0.17 / recall 0.23. **Not a real score.** |
| Live view: tracking, ArUco markers, mm scale, capture | `live/live.py`; markers in `live/markers_A4.png` |

## Your steps (ticked on the team board)

| # | Step | Command / where | Due |
|---|---|---|---|
| 1 | Film 2–3 column-cage videos, 4 markers in view, slow, from above | phone | Sat 21 Nov |
| 2 | Extract frames | `python pipeline.py frames videos/*.mp4` | Sat 21 Nov |
| 3 | Upload to Roboflow | `python pipeline.py upload` (set `ROBOFLOW_API_KEY` in the terminal first, never in a file) | Sun 22 Nov |
| 4 | Label 150 frames as **polygons** | Roboflow, project `concrete-evidence-column-cages`. Smart Polygon helps | Mon 23 Nov |
| 5 | Generate a version: 70/20/10 split, blur + brightness augmentation | Roboflow | Mon 23 Nov |
| 6 | Pre-train on SORD | Colab, T4 GPU: `training/train_sord_yolov8seg.ipynb`, Part A | Mon 23 Nov |
| 7 | Fine-tune on our labels | same notebook, Part B, or `python pipeline.py pull --version 1` then `train --stage finetune` on a GPU | Tue 24 Nov |
| 8 | Evaluate and log the run on the team board | `python pipeline.py eval` → `runs/eval.json` | Tue 24 Nov |
| 9 | Numbers onto the computer-vision slides (the `[__]` boxes) | deck | Wed 25 Nov |

## Rules for labelling

- Every visible piece gets its own polygon. Two bars that cross are two polygons.
- A hidden part of a bar isn't outlined. Don't guess where it runs.
- `tie` is the wire at a crossing. `hook_90` / `hook_135` is the bent end of a stirrup.
- Keep about 15 frames from a cage you **didn't** train on, as the test set. That's the honest score for the slides.

## Things that will bite

- **No GPU on the laptops.** The MX230 is too weak; `pipeline.py train` refuses to run on the CPU unless you pass `--force-cpu`. Use Colab.
- **Dense images.** SORD frames hold up to ~430 objects; keep `max_det` ≥ 500 when predicting.
- **Weights and data never go into git** (`runs/`, `data/`, `*.pt` are ignored). Put `best.pt` on the team Drive: `MyDrive/ConcreteEvidence/runs`.
- **SORD is non-commercial.** Fine for the studio; don't ship SORD-trained weights in a product.

## Team board

Ticks, tasks and training runs are on the shared **Concrete Evidence Team Board** (ask Akshat for edit access). Log every run there, bad ones too.
