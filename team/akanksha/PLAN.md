# Work plan: Akanksha, Sat 21 – Sun 22 Nov 2026

Paste this file into your Claude session as the brief. Repo: `iaac-maai/AAD_Research_Studio_03`. Read `team/README.md`, `PIPELINE.md` ("The check" and "Depth Anything before YOLO") and `concrete_evidence/codes.py` first.

**Your role:** the engineering rules, the fab-lab mock-up, the app's result page, the depth test and the pitch story. The team wants the app working by **Sun 22 Nov night**.

**Where your work goes:** Eurocode 8 note, mock-up design, wireframe, depth-test pictures (small), pitch outline → `team/akanksha/`. The mock-up schedule → `live/schedule_mockup.json`. Corrections to the limits → `concrete_evidence/codes.py`. The result page → `03_app/`. All by pull request. Full-size photos → team Drive, never GitHub.

## In this order

| # | Task | Needs first | Done when | Goes to | When |
|---|---|---|---|---|---|
| 1 | Check the Eurocode 8 values in `codes.py` against the code text: EN 1998-1 5.4.3.2.2 (DCM), 5.5.3.2.2 (DCH), EN 1992-1-1 9.5.3, Spanish national annex; the 135° hook with a 10 × tie-diameter tail. First, because the check uses them | — | each clause: confirmed or corrected | `team/akanksha/EC8_CHECK.md` (+ a PR to `codes.py` if wrong) | Sat |
| 2 | Design the fab-lab mock-up: a small column cage the lab can build in one afternoon (rebar or threaded rod + tie wire): size, bar and tie diameters, tie spacing per zone; the planted faults (one tie missing in the end zone, one hook at 90°, one bar shifted). Diego needs it before Sunday | 1 | build list + schedule | `team/akanksha/MOCKUP.md`, `live/schedule_mockup.json` | Sat |
| 3 | Update your doc "Next Steps and What the App Does": online data + mock-up instead of filming; "the pipeline is built, the model trains next"; the model runs on the server, not the phone; a **Thursday demo scope** (one face, one photo → steps 1, 3, 4, 5, 6 + saved result; the rest "Later") | — | updated, shared | `team/akanksha/NEXT_STEPS.md` (or the link) | Sat |
| 4 | Read the fix instructions in `concrete_evidence/fixes.py`: would a site foreman understand them? Rewrite the ones that don't read well | — | suggestions | `team/akanksha/FIX_WORDING.md` | Sat |
| 5 | Wireframe the result page: photo with green / red overlay, fix list, "pending review" with confirm / reject per fault, sign-off | — | a sketch | `team/akanksha/wireframe.png` | Sat |
| 6 | Build the result page (HTML + CSS, plain JS) against Akshat's sample result (`team/akshat/sample_result.json`) | 5, Akshat's sample | page shows the sample | `03_app/` (PR) | Sun morning |
| 7 | Fab-lab session: build the mock-up, print the markers (`python pipeline.py markers`, check one measures 100 mm), photograph every face, correct and with the planted faults | 2 | photos on the Drive | Drive | Sun afternoon |
| 8 | Depth test on the mock-up photos: `python pipeline.py depth <photos> --out <dir> --preview --slices 2`. Keeps the cage? Cuts off bars? | 7 | 5 before/after pictures + 3 lines | `team/akanksha/DEPTH_TEST.md` (pictures under 1 MB each) | Sun evening |
| 9 | Pitch outline for Thursday: the problem (90° hooks opening in earthquakes), what the app does (your 9 steps), what version 1 covers, what it does not do | 3 | outline | `team/akanksha/PITCH.md` | Sun night |

## Hand-offs

- **To Akshat, Sat:** 1 (Eurocode 8), 4 (fix wording), 5 (wireframe).
- **To Diego, Sat:** 2 (mock-up build list + schedule), before the Sunday photos.
- **From Akshat, Sat evening:** `team/akshat/sample_result.json` for the result page.
- **To Akshat, Sun:** the result page as a PR into `03_app/`.

## Rules

- Only openly licensed data. Never commit full-size photos, data, weights, passwords or API keys.
- Depth Anything: only the Small model (Apache-2.0). Base and Large are non-commercial.
- Upload to GitHub as in `team/README.md`: branch, commit, pull request.
