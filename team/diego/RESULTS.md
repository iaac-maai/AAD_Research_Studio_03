# Results: first rebar segmentation model (baseline)

Diego, Mon 23 Nov 2026. This is the model for Akshat's swap at 12:00.

## The model

| | |
|---|---|
| Weights | `best.pt`, in Drive: `MyDrive/ConcreteEvidence/runs/ours_baseline/weights/best.pt` (not in git) |
| Architecture | YOLOv8n-seg (3.4 M parameters), started from the standard `yolov8n-seg.pt` |
| Classes | `bar · stirrup · hook_90 · hook_135` |
| Data | Roboflow `diegos-workspace-puwbt/concrete-evidence-column-cages-ft8gc`, **version 1**: 1,157 images, split 1,005 train / 89 valid / 63 test |
| Sources | rebar-seg 701 + SiteVision 36 (real photos, CC BY 4.0), synthetic cages 300 + synthetic mock-up 120 (train only, see `SYNTHETIC.md`) |
| Training | `training/train_rebar_yolov8seg.ipynb` Part A, Colab T4, imgsz 640, batch 8, up to 100 epochs, patience 20, seed 0, about 2.3 h |
| Speed | 8.6 ms per image on a T4 (inference only) |

## Score on the test photos (63 real photos, never seen in training)

| Class | Instances | Box P | Box R | Box mAP50 | Box mAP50-95 | **Mask P** | **Mask R** | **Mask mAP50** | Mask mAP50-95 |
|---|---|---|---|---|---|---|---|---|---|
| bar | 1,321 | 0.910 | 0.792 | 0.889 | 0.703 | **0.816** | **0.704** | **0.748** | 0.396 |

**Headline for the board: mask mAP50 0.748, precision 0.816, recall 0.704 (bars, real photos).**

## What this does and does not show

- **Bars work on real photos.** On the test photos the model finds about 7 out of 10 bars, and about 8 out of 10 of its outlines are real bars.
- **The outlines are rough at the edges.** Mask mAP50-95 is 0.396, against 0.703 for the boxes. Bars are thin, so an outline a few pixels too wide already scores low at the strict thresholds. This is enough to count bars and find crossings, but not to measure bar diameter from the mask.
- **Stirrups and hooks are not measured yet.** All 63 test photos come from the real-photo sets, and those only have bars. In this version the stirrup and hook labels come only from the synthetic renders, and those are all in training. So this test cannot say whether the model tells a 90° hook from a 135° hook on a real cage. That number needs real labelled photos (next steps 1 and 2).
- **Dense site cages are harder.** On a close-up of a dense column cage the confidences drop to 0.27–0.5 and some bars are missed, while clean mesh photos score 0.7–0.95.

## For the app (Akshat)

- The model's class is called `stirrup`. If the app still expects `tie`, set `CLASS_RENAME=stirrup=tie` (as in `team/akshat/MONDAY.md`).
- Start with `conf=0.25` and `max_det=500`, the same as the evaluation.
- Until stirrups and hooks have a real test score, treat the hook-type check as a demo, not a measured result.

## Next steps

1. **60 Wikimedia photos** (`sources.csv`): pre-label them with this model (`prelabel_web_photos.py`), fix the outlines in Roboflow, and use them as a real test for stirrups and hooks.
2. **Fab-lab mock-up** (after Akanksha's session): about 15 photos of the one cage, all in the test set. This is the honest score for the demo.
3. Then train version 2 with both added, and compare it with this baseline on the same test photos.
