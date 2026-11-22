# Monday 23 Nov: Diego's model in by 12:00 (tasks 13, 14)

Where we stand on Sunday 22 Nov:

| Part | State |
|---|---|
| Model server (Render) | live: https://concrete-evidence-model.onrender.com, stand-in `iaac-maai/concrete-evidence-stand-in` |
| App (Cloudflare) | live: https://concrete-evidence.pages.dev, team password; photos in D1 (R2 won't switch on for the account) |
| UI restyle | PR #22, preview https://ui-restyle.concrete-evidence.pages.dev; waits on the design review (Sun 23:00) |
| Result page (Akanksha) | not in yet; due Sun 12:00 |
| `call_api.ipynb` | done, `02_model_server/` |
| ROI-1555 email | drafted in `ROI1555_EMAIL.md`, not sent |

## 10:00 to 12:00: swap the model

Diego hands over `best.pt` (team Drive, `MyDrive/ConcreteEvidence/`) and `team/diego/RESULTS.md`.

1. **Read the scores first** (`RESULTS.md`): mask mAP50 per class, above all `hook_90` vs `hook_135`.
   If a class is near zero, say so in the app (README, limits), don't hide it.
2. **Export and check**, in the full venv (with PyTorch), photo = one held-out fab-lab photo:
   ```bash
   python pipeline.py export --format onnx --model D:/Akshat/models/best.pt --check <held-out photo>
   ```
   It stops if ONNX and PyTorch find a different number of pieces.
3. **Class names:** the ONNX metadata must say `bar, tie, hook_90, hook_135`.
   ```bash
   python -c "import onnxruntime as o; print(o.InferenceSession('best.onnx').get_modelmeta().custom_metadata_map['names'])"
   ```
   Different names → `CLASS_RENAME`, e.g. `Stirrup=tie`.
4. **Upload** to a new Hugging Face repo `iaac-maai/concrete-evidence-rebar` (public): `best.onnx` + a model card
   (copy `02_model_server/MODEL_CARD_stand_in.md`, replace data, scores and limits with Diego's; licence AGPL-3.0,
   data licences from `datasets/CATALOGUE.md`).
5. **Point Render at it**: in `render.yaml`, `MODEL_REPO: iaac-maai/concrete-evidence-rebar` and `CLASS_RENAME`
   empty (or the mapping from step 3). Branch, PR, merge: Render redeploys by itself (about 4 minutes).
6. **Check it live**: run `02_model_server/call_api.ipynb` with `CE_PHOTO` = a fab-lab photo, then one check in
   the app on the phone. Note pieces, faults and time in `RESULTS.md`.
7. Board: task 14 done, feed post.

If the real model is worse than useless on the fab-lab photos, keep the stand-in live and show both in the demo:
the app works end to end, the model is the part still learning.

## After 12:00

- UI restyle: fold in the review comments (PR #22), then merge.
- Result page: wire Akanksha's page in, or keep the built-in one (it already saves confirm / reject to D1).
- R2: if it switches on, `npx wrangler r2 bucket create concrete-evidence-photos` and uncomment the three lines in
  `03_app/wrangler.toml`. Photos already in D1 stay there.
- Proofs for the hand-in (`04_final/PROOFS.md`): D1 tables, 401 without login, `MODEL_URL` line, no secrets in git.
