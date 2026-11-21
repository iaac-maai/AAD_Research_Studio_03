# Work plan: Akshat, Sat 21 – Mon 23 Nov 2026

Paste this file into your Claude session as the brief. Repo: `iaac-maai/AAD_Research_Studio_03`, local copy `D:\Akshat\concrete-evidence-2`. Read `README.md`, `PIPELINE.md`, `team/README.md`, `team/TIMELINE.md` first.

**Your role:** the code, the model server and the app. **Goal: the app works end to end by Sun 22 Nov night** with a stand-in model; Diego's trained model swaps in on Mon 23 Nov and nothing else changes.

**Where your work goes:** notes, memory tests, sample results → `team/akshat/`. Code → `concrete_evidence/`, `02_model_server/`, `03_app/` by pull request.

## In this order, with deadlines

**Bold deadlines block someone else:** if you're late, they wait. You're the app chain: **ONNX server (Sat 20:00) → Render (Sun 11:00) → Cloudflare (Sun 13:00) → result page wired in (Sun 21:00)**. You wait on Akanksha's result page (Sun 12:00) and on Diego's `best.pt` (Mon 10:00). Render, Cloudflare and Hugging Face need your own logins.

| # | Task | Waits on | Finish by | Who waits on it | Output |
|---|---|---|---|---|---|
| 1 | Merge the depth filter and the datasets plan | — | done ✅ | — | on main |
| 2 | One function for the whole check on one photo (`infer.py`) + `pipeline.py analyse` | — | done ✅ (branch `analyse-server`) | — | `concrete_evidence/`, `pipeline.py` |
| 3 | Model server, Gradio, `/predict` | 2 | done ✅ (branch `analyse-server`) | — | `02_model_server/` |
| 4 | Memory check | 3 | done ✅: 568 MB with PyTorch, over Render's 512 MB | — | `02_model_server/README.md` |
| 5 | Server on ONNX Runtime, no PyTorch. ONNX = PyTorch checked ✅ (same 72 pieces, outlines 99 %, 0.2 s vs 5.7 s; depth identical). Left: memory under 512 MB, tests, `render.yaml`, PR | 4 | **Sat 20:00** | you (task 9) | `concrete_evidence/`, `02_model_server/` |
| 6 | Sample result for Akanksha | 3 | done ✅ | Akanksha (result page) | `team/akshat/sample_result.json` |
| 7 | Email the ROI-1555 authors (Shao Lab) for permission; same email for the synthetic stirrup set | nobody | Sat 20:00 | Diego (more data, if yes) | note in `team/akshat/` |
| 8 | Cloudflare app skeleton, running locally (`npx wrangler pages dev`): password checked on the server, upload photo + schedule, zone, face → model server → result in D1, photo in R2 | 3 | Sat 24:00 | you (task 10) | `03_app/` |
| 9 | Deploy the model server on Render (Blueprint, Frankfurt, `0.0.0.0:$PORT`); stand-in model on Hugging Face `iaac-maai`; `call_api.ipynb` with outputs | 5; your Hugging Face + Render logins | **Sun 11:00** | you (task 10) | live URL, wake-up time in README |
| 10 | Deploy the app on Cloudflare: D1, R2, schema, `pages deploy`, `APP_PASSWORD` secret, `MODEL_URL` → Render; "the model is waking up" on 503 | 8, 9; your Cloudflare login | **Sun 13:00** | you (task 12) | live `*.pages.dev`, one row in D1 |
| 11 | Fab-lab mock-up session with the team | Akanksha's mock-up design (Sat 21:00) | Sun 14:00–17:00 | Diego (labels the photos) | photos on the Drive |
| 12 | Wire in Akanksha's result page: confirm / reject per fault saved to D1 | 10; her page (Sun 12:00) | **Sun 21:00** | the team: app done end to end | live app |
| 13 | Update the team board and write Monday's plan | — | Sun 23:00 | the team | `team/akshat/` |
| 14 | Swap in Diego's model: export `best.pt` to ONNX, check ONNX = PyTorch, upload to Hugging Face, set `MODEL_REPO` | Diego's `best.pt` (Mon 10:00) | Mon 12:00 | the team (Thursday demo) | live app on the real model |

## Hand-offs

- **From Akanksha, Sat 23:00:** confirmed Eurocode 8 values (fix `codes.py` if needed), fix-wording suggestions. **Sun 12:00:** the result page as a PR into `03_app/`.
- **From Diego, Mon 10:00:** the first `best.pt` → export to ONNX → Hugging Face `iaac-maai` → the server's `MODEL_REPO`.
- **To Akanksha:** the sample result is done.

## Rules

- Never commit data, photos, weights, `.env`, `.dev.vars`, passwords, tokens or API keys. Keys only in the terminal or as Cloudflare / Render secrets.
- Only openly licensed data and models. Work on the D drive.
- Branch + PR for every change; the check must pass.
