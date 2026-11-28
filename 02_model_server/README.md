# Model server

One photo in, the rebar check out. `app.py` is a Gradio app, like the class example: a page for people and
`/predict` for programs (the Cloudflare app). It runs the model on **ONNX Runtime, without PyTorch**, so it fits
Render's free plan (512 MB).

```bash
pip install -r 02_model_server/requirements.txt
MODEL_PATH=models/best.onnx python 02_model_server/app.py   # http://127.0.0.1:7860
```

`/predict(image_b64, schedule_json, zone, face)` returns:

| Field | What it is |
|---|---|
| `check` | the result of `check.run()`: `faults`, every check with its status, `fixes` (plain instructions), `review: pending`, the Eurocode 8 limits used |
| `detections` | every piece: class, number, centre, length, width, angle, outline (`polygon`, px), mm when the markers are in view |
| `counts`, `markers_seen`, `mm_per_px` | what was found and the scale |
| `annotated_jpg_base64` | the photo with outlines: red = named in a fault |
| `model` | weights and class renames |
| `error` | only when the input is bad (not an image, schedule without `bar_diameter_mm`) |

## Settings (environment; on Render: the Environment tab)

| Name | What it does |
|---|---|
| `MODEL_PATH` | a local `.onnx` (ONNX Runtime) or `.pt` (needs Ultralytics); default `models/best.onnx` |
| `MODEL_REPO`, `MODEL_FILE` | download the model from Hugging Face instead, e.g. `iaac-maai/concrete-evidence-rebar` + `best.onnx` |
| `HF_TOKEN` | only if the Hugging Face repo is private: a read token, set as a secret in Render (never in a file) |
| `CLASS_RENAME` | model class = our class: `stirrup=tie` for Diego's model |

## A new model (Diego's `best.pt`)

```bash
python pipeline.py export --format onnx --model best.pt --check <a test photo>
```

`--check` runs the photo through PyTorch and the ONNX file and stops if they find a different number of pieces.
Then upload `best.onnx` to Hugging Face (`iaac-maai`) and set `MODEL_REPO`. Nothing else changes.

## Call it

[`call_api.ipynb`](call_api.ipynb) sends one photo to the live server with `gradio_client` and prints the answer
(outputs saved, no photo). Live: https://concrete-evidence-model.onrender.com, endpoint `/predict`.

## Render

`render.yaml` at the repo root is the Blueprint: render.com → New → Blueprint → this repo → Frankfurt. Set
`MODEL_REPO` and `CLASS_RENAME` when Render asks. The free plan sleeps after 15 minutes; the
first call after that takes about a minute while it wakes. The Cloudflare app shows "the model is waking up".

A wrong repo name stops the server with one clear line.

## Tested (21 Nov 2026, laptop CPU, Windows; the first test model on `extra_01.jpg`, 1280 × 960)

**ONNX = PyTorch:**

| | PyTorch (Ultralytics) | ONNX (`onnx_seg.py`) |
|---|---|---|
| pieces found | 72 | 72 |
| box shift, largest | | 4.8 px |
| outline overlap (IoU), median / lowest | | 0.993 / 0.894 |
| time per photo (model only) | 5.7 s | 0.2 s |

Against Ultralytics running the same ONNX file the boxes are identical (0 px).

**Memory**, the whole server in a clean environment with only `requirements.txt` (no PyTorch), three calls:

| | Idle | Peak | Per call |
|---|---|---|---|
| PyTorch + Ultralytics (before) | | 568 MB | |
| **ONNX** | 195 MB | **350 MB** | 1.2 s (first 1.8 s) |


- A request that isn't an image returns `{"error": "not a JPEG or PNG image"}`.
