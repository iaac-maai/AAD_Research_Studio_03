# Work plan: Akanksha, Sat 21 – Sun 22 Nov 2026

Paste this file into your Claude session as the brief. Repo: `iaac-maai/AAD_Research_Studio_03`. Read `README.md`, `PIPELINE.md` (sections "The check" and "Depth Anything before YOLO") and `concrete_evidence/codes.py` first.

## Where the project is

- Concrete Evidence checks column rebar before the pour: photo → Depth Anything greys out the background → YOLOv8-seg outlines `bar · tie · hook_90 · hook_135` → measured in mm with the ArUco markers → checked against the bar bending schedule + Eurocode 8 → fix list → a person confirms.
- Your doc "Next Steps and What the App Does" is now the product story. Built from it: Eurocode 8 tie limits per column zone, tie-spacing checks, fix instructions (`codes.py`, `check.py`, `fixes.py`).
- **No site access.** The model is not trained yet (Diego is building the labelled set). There is no phone app: the model runs on a Render server, the app on Cloudflare.
- Presentation Thu 26 Nov.

**Your role:** the engineering rules, the mock-up, the result page of the app, the depth test and the product story. The team wants the app working by **Sun 22 Nov night**.

## Today, Sat 21 Nov

| # | Task | Done when |
|---|---|---|
| 1 | Update your doc: "film real cages" → online data + fab-lab mock-up; "the AI half is built" → "the pipeline is built, the model trains next"; the model runs on the server, not the phone; add a **Thursday demo scope**: one column face, one photo → steps 1, 3, 4, 5, 6 + a saved result. Guided capture of every face, rechecks and the floor tracker → "Later" | doc updated, shared with the team |
| 2 | Check the Eurocode 8 values in `concrete_evidence/codes.py` against the code text: EN 1998-1 5.4.3.2.2 (DCM), 5.5.3.2.2 (DCH), EN 1992-1-1 9.5.3, and the Spanish national annex if it changes them. Also the 135° hook with a 10 × tie diameter tail | a short note to Akshat: each clause, value confirmed or corrected |
| 3 | Design the fab-lab mock-up: a small column cage the lab can build in one afternoon (rebar or threaded rod + tie wire), size, bar and tie diameters, tie spacing per zone. Write its schedule as JSON like `live/schedule_example.json`, and list the planted faults (one tie missing in the end zone, one hook at 90°, one bar shifted) | build list + `live/schedule_mockup.json` sent to Akshat and Diego |
| 4 | Read the fix instructions in `concrete_evidence/fixes.py`: would a site foreman understand them? Rewrite the sentences that don't read well | suggestions sent to Akshat |
| 5 | Wireframe the result page for the app: photo with green / red overlay, fix list, "pending review" with confirm / reject per fault, sign-off | a sketch (Miro or paper photo) to Akshat |

## Tomorrow, Sun 22 Nov

| # | Task | Done when |
|---|---|---|
| 6 | Build the result page in Akshat's `03_app/` (HTML + CSS, plain JS): the photo with the overlay, the fix list, confirm / reject per fault, sign-off. Build it against the sample result JSON Akshat sends Sat night; he wires it to the database | page renders a sample result; PR open |
| 7 | Fab-lab session with the team (afternoon): build the mock-up, print the markers (`python pipeline.py markers`, check one measures 100 mm), photograph every face, correct and with the planted faults | photos on the team Drive |
| 8 | Depth test on the mock-up photos: `python pipeline.py depth <photos> --out <dir> --preview --slices 2`. Does it keep the cage and grey the background? Does it cut off any bars? | 5 before/after pictures + 3 lines on what works and what doesn't |
| 9 | Pitch story draft for Thursday: the problem (90° hooks opening in earthquakes), what the app does (your 9 steps), what version 1 covers, what it does not do | outline of the slides |

## Hand-offs

- **To Akshat, Sat:** confirmed Eurocode 8 values, mock-up schedule JSON, fix-wording suggestions, result-page wireframe.
- **From Akshat, Sat night:** a sample result JSON for the result page.
- **To Akshat, Sun:** the result page as a PR into `03_app/`.
- **To Diego, Sat:** the mock-up build list, so the planted faults are photographed and labelled.
- **To everyone, Sun night:** the depth-test pictures and the pitch outline.

## Rules

- Only openly licensed data. Never commit photos, data, weights, passwords or API keys.
- Any repo change (e.g. `schedule_mockup.json`, `codes.py` corrections) on a branch + PR; CI must pass.
- Depth Anything: only the Small model (Apache-2.0). Base and Large are non-commercial.
