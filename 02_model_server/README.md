# Model server

One photo in, the rebar check out. `app.py` is a Gradio app, like the class example: a page for people and
`/predict` for programs (the Cloudflare app). It runs the model on **ONNX Runtime, without PyTorch**, so it fits
Render's free plan (512 MB).

```bash
pip install -r 02_model_server/requirements.txt
python -m concrete_evidence.privacy --fetch     # the face-blur model, once
MODEL_PATH=models/best.onnx python 02_model_server/app.py   # http://127.0.0.1:7860
```

`/predict(image_b64, schedule_json, zone, face)` returns:

| Field | What it is |
|---|---|
| `check` | the result of `check.run()`: `faults`, every check with its status, `fixes` (plain instructions), `review: pending`, the Eurocode 8 limits used |
| `detections` | every piece: class, number, centre, length, width, angle, outline (`polygon`, px), mm when the markers are in view |
| `counts`, `markers_seen`, `mm_per_px` | what was found and the scale |
| `annotated_jpg_base64` | the photo with outlines: red = named in a fault |
| `model` | weights, class renames, whether the depth filter ran |
| `error` | only when the input is bad (not an image, schedule without `bar_diameter_mm`) |

## Settings (environment; on Render: the Environment tab)

| Name | What it does |
|---|---|
| `MODEL_PATH` | a local `.onnx` (ONNX Runtime) or `.pt` (needs Ultralytics); default `models/best.onnx` |
| `MODEL_REPO`, `MODEL_FILE` | download the model from Hugging Face instead, e.g. `iaac-maai/concrete-evidence-rebar` + `best.onnx` |
| `CLASS_RENAME` | model class = our class, e.g. `skewer=bar` for the skewer stand-in |
| `DEPTH_FILTER` | `1` runs Depth Anything V2 Small (ONNX, Apache-2.0) before YOLO. Off on the free plan (memory below) |

## A new model (Diego's `best.pt`)

```bash
python pipeline.py export --format onnx --model best.pt --check <a test photo>
```

`--check` runs the photo through PyTorch and the ONNX file and stops if they find a different number of pieces.
Then upload `best.onnx` to Hugging Face (`iaac-maai`) and set `MODEL_REPO`. Nothing else changes.

## Render

`render.yaml` at the repo root is the Blueprint: render.com → New → Blueprint → this repo → Frankfurt. Set
`MODEL_REPO` (and `CLASS_RENAME` for the stand-in) when Render asks. The free plan sleeps after 15 minutes; the
first call after that takes about a minute while it wakes. The Cloudflare app shows "the model is waking up".

## Tested (21 Nov 2026, laptop CPU, Windows; skewer stand-in on `extra_01.jpg`, 1280 × 960)

**ONNX = PyTorch:**

| | PyTorch (Ultralytics) | ONNX (`onnx_seg.py`) |
|---|---|---|
| pieces found | 72 | 72 |
| box shift, largest | | 4.8 px |
| outline overlap (IoU), median / lowest | | 0.993 / 0.894 |
| time per photo (model only) | 5.7 s | 0.2 s |

Against Ultralytics running the same ONNX file the boxes are identical (0 px). Depth Anything on ONNX against the
PyTorch one: correlation 1.000, the same near/far threshold, 99.8 % of pixels kept the same.

**Memory**, the whole server in a clean environment with only `requirements.txt` (no PyTorch), three calls:

| | Idle | Peak | Per call |
|---|---|---|---|
| PyTorch + Ultralytics (before) | | 568 MB | |
| **ONNX, depth filter off** | 195 MB | **350 MB** | 1.2 s (first 1.8 s) |
| ONNX, depth filter on | 296 MB | 592 MB | 3.6 s (first 4.5 s) |

So the free plan runs with `DEPTH_FILTER=0`. The depth filter needs a plan with 1 GB, or runs locally
(`pipeline.py analyse --depth-filter`). Version 1 (one column face) does not need it.

- A request that isn't an image returns `{"error": "not a JPEG or PNG image"}`.
