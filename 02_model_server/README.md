# Model server

One photo in, the rebar check out. `app.py` is a Gradio app, like the class example: a page for people and
`/predict` for programs (the Cloudflare app).

```bash
python 02_model_server/app.py          # http://127.0.0.1:7860
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

Settings (environment): `MODEL_PATH`, `MODEL_REPO` (Hugging Face repo with `best.pt`), `CLASS_RENAME`
(`skewer=bar` for the skewer test model), `DEPTH_FILTER=1`.

## Tested (21 Nov 2026, laptop CPU, Windows)

- Skewer test model (`skewer_best.pt`, `CLASS_RENAME=skewer=bar`) on `extra_01.jpg` through `gradio_client`:
  72 pieces outlined, check and fix list returned, annotated photo 101 kB. First call 13.5 s (includes warm-up).
- A request that isn't an image returns `{"error": "not a JPEG or PNG image"}`.
- **Memory: 568 MB with YOLO only** (PyTorch). Render's free plan has 512 MB, so this does not fit as it is.
  Depth Anything would add more. See the decision below.
