# Work plan: Akshat, Sat 21 – Sun 22 Nov 2026

Paste this file into your Claude session as the brief. Repo: `iaac-maai/AAD_Research_Studio_03`, local copy `D:\Akshat\concrete-evidence-2`. Read `README.md`, `PIPELINE.md` and `datasets/CATALOGUE.md` first.

## Where the project is

- Concrete Evidence checks column rebar before the pour: photo with ArUco markers → (Depth Anything filter) → YOLOv8-seg outlines `bar · tie · hook_90 · hook_135` → lines in mm → check against the bar bending schedule + Eurocode 8 → fix list → a person confirms.
- Built and merged: markers, frames, Roboflow upload/pull, training + eval + export, live view, check stage with Eurocode 8 tie zones and fix instructions (PR #8).
- Open: PR #9 depth filter, PR on `datasets-online` (plan without site access, these work plans).
- No site access: Diego builds the labelled set from open data + a fab-lab mock-up. No trained model yet.
- Presentation Thu 26 Nov, freeze Wed 25 Nov night.

**Your role:** the code, the model server and the app. **Goal: the app works end to end by Sun 22 Nov night**, with a stand-in model. You are not blocked by the data: Diego's trained model swaps in on Mon 23 Nov, and nothing else changes.

## Today, Sat 21 Nov

| # | Task | Done when |
|---|---|---|
| 1 | Merge PR #9 (depth filter) once CI is green; push and merge `datasets-online` | both on main, CI green |
| 2 | Email the ROI-1555 authors (Shao Lab, via the Hugging Face dataset page) asking permission to use the dataset for a student project; same email for the synthetic stirrup set | email sent by you |
| 3 | One function for the whole check on one photo: `concrete_evidence/infer.py` → `analyse(image, schedule, model, depth=None, zone, face)` returns masks, records, the check result and an annotated image. Reuse `markers`, `capture.records_from_result`, `check.run`, `depth.filter_image` | a test with a stand-in model passes; `pipeline.py analyse photo.jpg --schedule ...` prints the fix list |
| 4 | Model server skeleton in `02_model_server/` following the hackathon brief (`hackathon/docs/model_app/`): Gradio app, `/predict` takes a photo (base64) + schedule JSON + zone + face, returns the result JSON + annotated image. Start with `yolov8n-seg.pt` as the stand-in | runs locally, one sample request works (`call_api.ipynb`) |
| 5 | Memory check: YOLO + Depth Anything Small together on CPU. Render free = 512 MB RAM | number written in `02_model_server/README.md`; if over, depth filter off on the server by default |
| 6 | Cloudflare app skeleton in `03_app/` (start from `hackathon/docs/cloudflare_app/`), running locally with `npx wrangler pages dev`: password checked on the server (`functions/_middleware.js`, `APP_PASSWORD` in `.dev.vars`, gitignored), upload a photo + pick the schedule, zone and face → calls the local model server → stores the result in D1, the photo in R2 | one photo in, a result row out, locally |

## Tomorrow, Sun 22 Nov

| # | Task | Done when |
|---|---|---|
| 7 | Deploy the model server on Render (Blueprint, Frankfurt, `.python-version`, `0.0.0.0:$PORT`); call it from `call_api.ipynb` with outputs | Live URL answers; wake-up time noted in README |
| 8 | Deploy the app on Cloudflare: `wrangler d1 create`, `r2 bucket create`, schema, `pages deploy`, `pages secret put APP_PASSWORD`, `MODEL_URL` pointing at Render; "the model is waking up, about one minute" on 503 | live `*.pages.dev`; one row in D1 from the live app |
| 9 | Wire in Akanksha's result page (she builds the HTML/CSS): confirm / reject per fault saved to D1 | end to end on the live app with the stand-in model |
| 10 | Fab-lab mock-up session with the team (afternoon): help build, photograph each face with markers | photos on the team Drive |
| 11 | Update the team board: done ticks, Mon/Tue tasks | board current |

## Hand-offs

- **From Diego:** Roboflow version + first `best.pt` on Mon 23 → swap into the server (Hugging Face `iaac-maai`). The app itself doesn't change.
- **To Akanksha, Sat night:** the result JSON shape (fields of `check.run()` plus the annotated image) so she can build the result page against it.
- **From Akanksha:** confirmed Eurocode 8 values (Sat) → fix `concrete_evidence/codes.py` if needed; result-page wireframe (Sat night); mock-up schedule JSON (Sat).

## Rules

- Never commit data, photos, weights, `.env`, `.dev.vars`, passwords, tokens or API keys. Keys only in the terminal (`$env:ROBOFLOW_API_KEY`) or as Cloudflare/Render secrets.
- Only openly licensed data and models. Work on the D drive.
- Branch + PR for every change; CI (ruff + pytest) must pass. No AI co-author lines in commits.
