# The app (Cloudflare)

A site engineer opens the app, signs in with the team password, photographs one column face with the 4 markers
in view, picks the zone and face, and gets the checked photo (red = named in a fault), the fix list, and every
fault to confirm or reject. Once each fault has a decision, they sign the face off.

| Part | What | Where |
|---|---|---|
| Page | `public/` (plain HTML, CSS, JS; the UI layer restyles it) | Cloudflare Pages |
| API | `functions/` | Pages Functions |
| Password | `functions/_middleware.js`, checked on the server; the cookie holds a hash, never the password | secret `APP_PASSWORD` |
| Model | `/api/check` calls the Render model server's `/predict` | `MODEL_URL` in `wrangler.toml` |
| Checks | one row per checked photo; one row per review decision (`schema.sql`) | D1 `concrete-evidence-db` |
| Photos | the checked photo (faces blurred, outlines drawn) and the full result JSON. **The original upload is never stored** | R2 `concrete-evidence-photos` |

## API

| Route | What it does |
|---|---|
| `POST /api/login`, `POST /api/logout` | sign in / out |
| `POST /api/check` | form: `photo`, `schedule` (JSON), `zone` (`end`/`middle`), `face` → the check; **503 `{waking: true}`** while Render wakes, the page retries for up to 3 minutes and says "the model is waking up" |
| `GET /api/checks` | the 30 latest checks |
| `GET /api/checks/<id>` | one check: schedule, every rule and its status, fixes, review decisions |
| `GET /api/photos/<id>` | the checked photo |
| `POST /api/reviews/<id>` | `{reviewer, decisions: [{fault_index, decision: confirm/reject, note}], sign_off}`; sign-off only when every fault is decided |

Everything except the login page answers **401** without the cookie.

## Run it locally

```bash
cd 03_app
npm install
cp .dev.vars.example .dev.vars      # choose a password; MODEL_URL=http://127.0.0.1:7860
npm run db:local                     # the tables, in a local D1
npm run dev                          # http://localhost:8788
```

The model server runs beside it: `python 02_model_server/app.py` (see `02_model_server/README.md`).

## Online (once)

```bash
npx wrangler login
npx wrangler d1 create concrete-evidence-db           # paste the id into wrangler.toml
npx wrangler r2 bucket create concrete-evidence-photos
npm run db:remote
npm run deploy   # makes lib/cities.gen.js from the city list, then wrangler pages deploy
npx wrangler pages secret put APP_PASSWORD
```

Set `MODEL_URL` in `wrangler.toml` to the Render address (no slash at the end). The first photo after 15 quiet
minutes waits about a minute while Render wakes.

## Tested locally (21 Nov 2026)

- Without login: `/api/checks` and `/api/photos/<id>` → 401, `/` → redirect to `/login`; wrong password → `/login?wrong=1`.
- One photo (skewer stand-in, 1280 × 960) through `/api/check` → model server → 72 pieces, 37 faults (a skewer mat
  against a column schedule, as expected), fix list; 2.1 s. Row in D1, photo (105 kB) and result in R2.
- A review decision saved in D1; sign-off refused until every fault is decided.
- The page in the browser: sign in, history, open a check with its photo and status.
