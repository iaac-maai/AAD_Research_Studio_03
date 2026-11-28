# Concrete Evidence

*"Catch it before you cast it."* IAAC MaAI 2026, AAD Research Studio 03: Akshat, Diego, Akanksha.

A site engineer photographs one face of a column cage before the pour. The app outlines every bar, tie and hook,
measures them along each bar's axis, checks them against the bar bending schedule and Eurocode 2 / Eurocode 8
(the rules picked from where the site is), and lists each fault with a plain fix. A person confirms or rejects
every fault and signs the face off. The app never approves a cage on its own.

```
phone photo ──► Cloudflare app (03_app) ──► model server on Render (02_model_server) ──► Diego's model (Hugging Face)
                  │  password, D1 rows,         markers → mm scale, outlines → axis lines,
                  │  checked photo + result      check vs schedule + Eurocode, fix list
                  └─► reviewer confirms or rejects each fault, signs off
```

| Live | Where |
|---|---|
| App | Cloudflare Pages, `concrete-evidence` (password from the team) |
| Model server | https://concrete-evidence-model.onrender.com (`/predict`; sleeps after 15 min, ~1 min to wake) |
| Model | [`iaac-maai/concrete-evidence-rebar`](https://huggingface.co/iaac-maai/concrete-evidence-rebar): YOLOv8n-seg, ONNX, `bar · hook_135 · hook_90 · stirrup` |

## What is in the repo

**The product** (runs on every photo):

| Folder | What it does |
|---|---|
| [`03_app/`](03_app/README.md) | the website: sign in, upload a photo, see the faults, confirm or reject, sign off. Pages + Functions + D1 |
| [`02_model_server/`](02_model_server/README.md) | the Gradio server on Render: one photo in, the check out (ONNX Runtime, no PyTorch) |
| `concrete_evidence/` | the shared Python: `markers` (mm scale), `onnx_seg` (runs the model), `axis` (axis polylines, bends), `capture` (pieces in mm), `check` (the rules), `codes` (Eurocode limits), `location` (city or GPS → country and seismic zone, `reference/`), `fixes` (fix wording), `infer` (the whole check on one photo) |
| `live/` | `schedule.schema.json` (the schedule format, shared with the form and the PDF reader), example schedules, the marker sheet |
| `tests/` | the tests; they run on every pull request (`.github/workflows/ci.yml`) |
| `render.yaml` | the Render Blueprint for the model server |

**The training kit** (not used by the app; for the next model, e.g. fine-tuning on the mock-up photos):

| Folder | What it does |
|---|---|
| [`PIPELINE.md`](PIPELINE.md), `pipeline.py` | every stage from video to a trained, exported model, and the check from the command line |
| `training/`, `datasets/` | Colab notebook, frame extractor, label converters, dataset downloads and [catalogue](datasets/CATALOGUE.md) |
| `concrete_evidence/conrebseg.py`, `convert.py`, `frames.py` | dataset conversion and frame picking |
| `live/live.py` | live camera view on a laptop: tracking, markers, capture a frame for the check |
| `team/` | each person's notes and scripts (Diego's data sources and synthetic cages, Akanksha's Eurocode and PDF notes) |
| `docs/rebar_process_timeline.html` | the 20 steps of the rebar process, the faults at each and the feature that catches them |

## Working on the code

```bash
pip install -r requirements-dev.txt     # light: no torch, enough for the tests
ruff check .
python -m pytest
```

`requirements.txt` pins everything for training and the live view; Python in `.python-version` (3.13).
Every pull request runs the same lint and tests on GitHub. Merge only when the check is green.
Never commit photos, data, weights, `.env`, `.dev.vars`, passwords or keys.

## Photos and people

Photos are stored as uploaded, with the outlines drawn (no face blurring). Photograph the cage, not the crew,
and don't share photos with people in them outside the team.

## Licence

AGPL-3.0 ([LICENSE](LICENSE)), the same as Ultralytics YOLOv8, which the model is trained and run with.
If the app serves the model to other people, its source has to stay open to them.
Datasets keep their own licences: see [datasets/CATALOGUE.md](datasets/CATALOGUE.md).
