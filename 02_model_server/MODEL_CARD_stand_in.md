---
license: agpl-3.0
library_name: onnx
pipeline_tag: image-segmentation
tags:
  - yolov8
  - instance-segmentation
  - construction
  - rebar
  - stand-in
---

# Concrete Evidence: skewer stand-in (YOLOv8n-seg, ONNX)

**A stand-in, not the real rebar model.** It lets the Concrete Evidence app run end to end
(photo → Render model server → Cloudflare app) before the rebar model is trained. It finds
wooden skewers on a table, which the app treats as bars (`CLASS_RENAME=skewer=bar`).
The real model, trained on rebar photos, replaces it on Mon 23 Nov 2026.

IAAC MaAI 2026, AAD Research Studio 03, team Concrete Evidence (Akshat, Diego, Akanksha).

## What it is

| | |
|---|---|
| Architecture | Ultralytics YOLOv8n-seg, one class: `skewer` |
| File | `best.onnx`, 13.8 MB, opset 17, input `images` 1 × 3 × 640 × 640, fixed size |
| Exported with | Ultralytics 8.4.216, `simplify=True`, `dynamic=False` |
| Runs on | `onnxruntime` CPU, no PyTorch (`concrete_evidence/onnx_seg.py` in the repo) |

## Data

20 top-down photos of a 6 × 6 skewer mat (30 mm spacing) with two coloured stickers for scale,
taken by the team: 11 of the correct mat, 9 with one extra skewer. Labels were made
automatically from the design grid: 1,299 skewer pieces, cut between crossings.
16 photos to train, 4 held out. No people, no third-party images.

## Results

- 20 of 20 photos judged correctly (correct mat vs extra skewer), including the 4 held out.
- Every skewer within about 1 mm of the design, measured against the mat.
- ONNX vs PyTorch on one 1280 × 960 photo: 72 = 72 pieces, largest box shift 4.8 px,
  outline overlap (IoU) median 0.993; 0.2 s vs 5.7 s on a laptop CPU.

## Limits

- It has only seen skewers on a light table. On rebar, a site or people it will find nothing
  useful, or wrong pieces. **Do not use it to judge real reinforcement.**
- Tiny dataset, one mat, one lighting setup: the scores above say nothing about other scenes.
- It finds pieces, not faults: the bar, tie and hook rules live in the app's check
  (`concrete_evidence/`), and a person confirms every fault before a pour.

## Licence

AGPL-3.0, because the model is trained from Ultralytics YOLOv8 (AGPL-3.0).
The training photos are the team's own.

## How to use

```python
from huggingface_hub import hf_hub_download
from concrete_evidence.onnx_seg import OnnxSeg   # from the project repo
import cv2

model = OnnxSeg(hf_hub_download("iaac-maai/<this-repo>", "best.onnx"))
result = model.predict(cv2.imread("photo.jpg"), conf=0.25)[0]
print(len(result.boxes.xyxy), "pieces")
```

On Render the model server reads it with `MODEL_REPO=iaac-maai/<this-repo>` and `MODEL_FILE=best.onnx`.
