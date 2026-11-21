# Work plan: Akshat, Sat 21 – Sun 22 Nov 2026

Paste this file into your Claude session as the brief. Repo: `iaac-maai/AAD_Research_Studio_03`, local copy `D:\Akshat\concrete-evidence-2`. Read `README.md`, `PIPELINE.md`, `team/README.md` first.

**Your role:** the code, the model server and the app. **Goal: the app works end to end by Sun 22 Nov night** with a stand-in model; Diego's trained model swaps in on Mon 23 Nov and nothing else changes.

**Where your work goes:** notes, memory tests, sample results → `team/akshat/`. Code → `concrete_evidence/`, `02_model_server/`, `03_app/` by pull request.

## In this order

| # | Task | Needs first | Done when | Goes to | Status |
|---|---|---|---|---|---|
| 1 | Merge the depth filter (#9) and the datasets plan (#10) | — | on main | — | done |
| 2 | One function for the whole check on one photo (`infer.py`) + `pipeline.py analyse` | — | test passes; prints the fix list | `concrete_evidence/`, `pipeline.py` | done (branch `analyse-server`) |
| 3 | Model server, Gradio, `/predict` | 2 | one sample request works locally | `02_model_server/` | done locally (branch `analyse-server`) |
| 4 | Memory check | 3 | number in the server README | `02_model_server/README.md` | done: **568 MB with PyTorch, over Render's 512 MB** |
| 5 | Server on ONNX Runtime, no PyTorch: YOLO-seg and Depth Anything Small as ONNX; check ONNX = PyTorch output | 4 | memory under 512 MB; outputs match | `concrete_evidence/`, `02_model_server/` | in progress |
| 6 | Send Akanksha a sample result (JSON + annotated photo) for the result page | 3 | file in the repo | `team/akshat/sample_result.json` | Sat evening |
| 7 | Email the ROI-1555 authors (Shao Lab) for permission; same email for the synthetic stirrup set | — | sent | note in `team/akshat/` | Sat (you) |
| 8 | Cloudflare app skeleton, running locally (`npx wrangler pages dev`): password checked on the server, upload photo + schedule, zone, face → model server → result in D1, photo in R2 | 3 | one photo in, one row out, locally | `03_app/` | Sat night |
| 9 | Deploy the model server on Render (Blueprint, Frankfurt, `0.0.0.0:$PORT`); `call_api.ipynb` with outputs | 5 | live URL answers; wake-up time in README | `02_model_server/` | Sun morning |
| 10 | Deploy the app on Cloudflare: D1, R2, schema, `pages deploy`, `APP_PASSWORD` secret, `MODEL_URL` → Render; "the model is waking up" on 503 | 8, 9 | live `*.pages.dev`; one row in D1 from the live app | `03_app/` | Sun midday |
| 11 | Fab-lab mock-up session with the team | Akanksha's build list | photos on the Drive | Drive | Sun afternoon |
| 12 | Wire in Akanksha's result page: confirm / reject per fault saved to D1 | 10, her page | end to end on the live app | `03_app/` | Sun evening |
| 13 | Update the team board and write tomorrow's plan | — | board current | `team/akshat/` | Sun night |

## Hand-offs

- **To Akanksha (6):** the sample result, Sat evening.
- **From Akanksha:** confirmed Eurocode 8 values (fix `codes.py` if needed), the result page as a PR into `03_app/` (Sun).
- **From Diego, Mon 23:** first `best.pt` → export to ONNX → Hugging Face `iaac-maai` → the server's `MODEL_REPO`.

## Rules

- Never commit data, photos, weights, `.env`, `.dev.vars`, passwords, tokens or API keys. Keys only in the terminal or as Cloudflare / Render secrets.
- Only openly licensed data and models. Work on the D drive.
- Branch + PR for every change; the check must pass.
