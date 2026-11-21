# Handover: supervised rebar model (Diego)

Paste this file into your own Claude session as the starting brief. Everything it refers to is in this repo.

## Goal, for the presentation on Thu 26 Nov (freeze Wed 25 Nov night)

Train a **supervised segmentation model** that outlines every piece of rebar in a column cage, labelled by us as `bar · tie · hook_90 · hook_135`, and get real scores for the slides (precision, recall, mask mAP50 on frames it has never seen). The project is **only rebar**: one check, bar by bar, before the pour.

Supervised means the model learns from examples we labelled by hand. Two stages:

1. **Baseline on our own frames**, from the standard pretrained YOLOv8 weights. No open dataset outlines single bars in a cage: ConRebSeg (CC BY 4.0) outlines *patches* of exposed rebar in repair work, SORD is synthetic. Column Tie Detection and SteelBindings have boxes only.
2. **Optional warm-up**: first train on ConRebSeg (class `exposed_rebar`), then on our frames, same split and seed. Keep it only if it beats the baseline on the test frames. This stage makes bar-by-bar checking possible, and it gives the numbers for the slides.

## Status on 20 Nov 2026 (Akshat)

| Done | Where |
|---|---|
| Dataset research, licences checked; open-licence only for training | `datasets/CATALOGUE.md` |
| One script for every stage, from video to the live view | `pipeline.py`, guide in `PIPELINE.md` |
| SORD shards 0–1 downloaded and converted (200 images, ~24,000 objects) | `data/sord_yolo/` on Akshat's laptop (not in git) |
| 3-epoch CPU test training, to prove the pipeline | mask mAP50 0.093 / precision 0.17 / recall 0.23. **Not a real score.** |
| Live view: tracking, ArUco markers, mm scale, capture | `live/live.py`; markers in `live/markers_A4.png` |
| Shared code in `concrete_evidence/`, pinned `requirements.txt`, 26 tests run on every PR | `README.md`, "Working on the code" |
| Faces blurred in every saved frame (GDPR) | run `python -m concrete_evidence.privacy --fetch` once after install |

## Your steps (ticked on the team board)

The board is the source of truth for dates; this table matches it on 20 Nov.

| # | Step | Command / where | Due |
|---|---|---|---|
| 1 | Film 2–3 column-cage videos, 4 markers in view, slow, from above | phone | Sat 21 Nov |
| 2 | Extract frames (faces blurred automatically) | `python pipeline.py frames videos/*.mp4` | Sat 21 Nov |
| 3 | Upload to Roboflow | `python pipeline.py upload` (set `ROBOFLOW_API_KEY` in the terminal first, never in a file) | Sun 22 Nov |
| 4 | Label 150 frames as **polygons** | Roboflow, project `concrete-evidence-column-cages`. Smart Polygon helps | Sun 22 Nov |
| 5 | Optional: ConRebSeg warm-up, runs while you label | Colab, T4 GPU: `training/train_rebar_yolov8seg.ipynb`, Part B. Downloads ConRebSeg (22.6 GB) to Colab and checks it. Skip it if time is short | Sun 22 Nov |
| 6 | Generate a version: 70/20/10 split, blur + brightness augmentation | Roboflow | Mon 23 Nov |
| 7 | Baseline on our labels (Part A), plus the warm-up run if you did step 5; same split and seed, compare | same notebook, or `python pipeline.py pull --version 1` then `train --stage finetune` on a GPU | Mon 23 Nov |
| 8 | Evaluate and log the run on the team board | `python pipeline.py eval` → `runs/eval.json` | Mon 23 Nov |
| 9 | Export ONNX + `config.json`; check ONNX output = PyTorch output | `python pipeline.py export --format onnx` | Tue 24 Nov |
| 10 | Model on Hugging Face (`iaac-maai`) with a model card: data, licence, results, limits | huggingface.co | Tue 24 Nov |
| 11 | Numbers onto the computer-vision slides (the `[__]` boxes) | deck | Wed 25 Nov |

Akshat's model server (Mon 23) starts with the test model and switches to your model once it's on Hugging Face (Tue 24).

## Rules for labelling

- Every visible piece gets its own polygon. Two bars that cross are two polygons.
- A hidden part of a bar isn't outlined. Don't guess where it runs.
- `tie` is the wire at a crossing. `hook_90` / `hook_135` is the bent end of a stirrup.
- Keep about 15 frames from a cage you **didn't** train on, as the test set. That's the honest score for the slides.

## Things that will bite

- **No GPU on the laptops.** The MX230 is too weak; `pipeline.py train` refuses to run on the CPU unless you pass `--force-cpu`. Use Colab.
- **Dense images.** SORD frames hold up to ~430 objects; keep `max_det` ≥ 500 when predicting.
- **Weights and data never go into git** (`runs/`, `data/`, `*.pt` are ignored). Put `best.pt` on the team Drive: `MyDrive/ConcreteEvidence/runs`.
- **SORD is non-commercial.** Fine for a quick test; don't use SORD-trained weights for the model on Hugging Face or the app.

## Team board

Ticks, tasks and training runs are on the shared **Concrete Evidence Team Board** (ask Akshat for edit access). Log every run there, bad ones too.
