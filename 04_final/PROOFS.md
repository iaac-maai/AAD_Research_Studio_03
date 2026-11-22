# Proofs

Each proof is a command and its real output, run on Sun 22 Nov 2026 against the live app
(https://concrete-evidence.pages.dev) and model server (https://concrete-evidence-model.onrender.com).

## 1. Database (Cloudflare D1)

```bash
npx wrangler d1 execute concrete-evidence-db --remote --command "SELECT name FROM sqlite_master WHERE type='table'"
```

```
_cf_KV
checks
reviews
files
```

`checks` holds one row per photo checked, `reviews` one row per person's decision on a fault, `files` the checked
photo and the result JSON (R2 does not switch on for our account, so files are stored as BLOBs in D1; see
`03_app/lib/storage.js`). Row count on Sun 22 Nov 17:15: 0 checks (no logged-in check on the live site yet).

## 2. Locked on the server

The password is checked in `03_app/functions/_middleware.js`, not in the page. Without the login cookie:

```bash
curl -si https://concrete-evidence.pages.dev/api/checks | head -1
```

```
HTTP/1.1 401 Unauthorized
```

| Route, no login | Status |
|---|---|
| `/api/checks` | 401 |
| `/api/check` | 401 |
| `/api/photos/x` | 401 |
| `/` (the page) | 302 to `/login` |

A wrong password redirects to `/login?wrong=1`. The password is the Cloudflare secret `APP_PASSWORD`; it is
not in git or in `wrangler.toml`.

## 3. Connected to Render

`03_app/wrangler.toml`:

```toml
MODEL_URL = "https://concrete-evidence-model.onrender.com"
```

The page never calls Render; `functions/api/check.js` does, on the server, and shows "the model is waking up"
while Render starts (about one minute after 15 minutes idle).

Direct call to the model server (`02_model_server/call_api.ipynb`), stand-in model, one test photo: 72 pieces,
37 faults, 20 s, fix text e.g. "Remove or recheck 69 extra longitudinal bar(s). The photo shows 72; the schedule
requires 3."

**To add:** screenshot of one live result in the app, after a logged-in check (`04_final/screenshots/`).

## 4. No secrets in git

`03_app/.gitignore` ignores `.dev.vars`:

```bash
git check-ignore -v 03_app/.dev.vars
```

```
03_app/.gitignore:3:.dev.vars	03_app/.dev.vars
```

Search of the full git history (all branches, 74 commits) for Hugging Face and GitHub tokens, Cloudflare API
tokens, API keys and private keys: no matches. The only password line in history is the placeholder
`APP_PASSWORD=choose-a-local-password` in `03_app/.dev.vars.example`. No model weights (`.pt`, `.onnx`) or
site photos are tracked; the two tracked images are the printable marker sheet and Akanksha's wireframe.
Cloudflare: `APP_PASSWORD` is a Pages secret (encrypted), `MODEL_URL` a plain variable.

## 5–6. User accounts

Not built: one team password, by design for the hackathon.
