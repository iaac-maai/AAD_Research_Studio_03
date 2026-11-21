# Work plan: Akanksha, Sat 21 – Sun 22 Nov 2026

Paste this file into your Claude session as the brief. Repo: `iaac-maai/AAD_Research_Studio_03`. Read `team/README.md`, `team/TIMELINE.md`, `PIPELINE.md` ("The check" and "Depth Anything before YOLO") and `concrete_evidence/codes.py` first.

**Your role:** the engineering rules, the fab-lab mock-up, the app's result page, the depth test and the pitch story. The team wants the app working by **Sun 22 Nov night**.

**Where your work goes:** Eurocode 8 note, mock-up design, wireframe, depth-test pictures (small), pitch outline → `team/akanksha/`. The mock-up schedule → `live/schedule_mockup.json`. Corrections to the limits → `concrete_evidence/codes.py`. The result page → `03_app/`. All by pull request. Full-size photos → team Drive, never GitHub.

## In this order, with deadlines

**Bold deadlines block someone else:** if you're late, they wait. Your two most important ones are **the mock-up design (Sat 21:00)**, because Diego's photos and the fab-lab session need it, and **the result page (Sun 12:00)**, because Akshat wires it into the live app on Sunday evening. You wait on nobody to start.

| # | Task | Waits on | Finish by | Who waits on it | Output |
|---|---|---|---|---|---|
| 1 | Check the Eurocode 8 values in `codes.py` against the code text: EN 1998-1 5.4.3.2.2 (DCM), 5.5.3.2.2 (DCH), EN 1992-1-1 9.5.3, Spanish national annex; the 135° hook with a 10 × tie-diameter tail | nobody: start now | **Sat 18:00** | you (task 2), Akshat (the check uses them) | `team/akanksha/EC8_CHECK.md` (+ a PR to `codes.py` if wrong) |
| 2 | Design the fab-lab mock-up: a small column cage the lab can build in one afternoon: size, bar and tie diameters, tie spacing per zone; the planted faults (one tie missing in the end zone, one hook at 90°, one bar shifted) | your task 1 | **Sat 21:00** | Diego (fab-lab photos, test set), the fab-lab session | `team/akanksha/MOCKUP.md`, `live/schedule_mockup.json` |
| 3 | Update "Next Steps and What the App Does": online data + mock-up instead of filming; "the pipeline is built, the model trains next"; the model runs on the server; a Thursday demo scope (one face, one photo → steps 1, 3, 4, 5, 6 + saved result; the rest "Later") | nobody | Sat 23:00 | you (task 9) | `team/akanksha/NEXT_STEPS.md` |
| 4 | Read the fix instructions in `concrete_evidence/fixes.py`: would a site foreman understand them? Rewrite the ones that don't read well | nobody | Sat 23:00 | Akshat (merges the wording Sun) | `team/akanksha/FIX_WORDING.md` |
| 5 | Wireframe the result page: photo with green / red overlay, fix list, "pending review" with confirm / reject per fault, sign-off | nobody | Sat 23:00 | you (task 6) | `team/akanksha/wireframe.png` |
| 6 | Build the result page (HTML + CSS, plain JS) against `team/akshat/sample_result.json` | your task 5; Akshat's sample (ready ✅) | **Sun 12:00** | Akshat (wires it in Sun evening) | `03_app/` (PR) |
| 7 | Fab-lab session: print the markers (`python pipeline.py markers`, check one measures 100 mm) by Sun 13:00; build the mock-up, photograph every face, correct and with the planted faults | your task 2; lab materials | **Sun 14:00–17:00** | Diego (labels the photos by Sun 19:00) | photos on the Drive |
| 8 | Depth test on the mock-up photos: `python pipeline.py depth <photos> --out <dir> --preview --slices 2`. Keeps the cage? Cuts off bars? | your task 7 | Sun 20:00 | the team (depth on or off) | `team/akanksha/DEPTH_TEST.md` (5 before/after pictures under 1 MB + 3 lines) |
| 9 | Pitch outline for Thursday: the problem (90° hooks opening in earthquakes), what the app does (your 9 steps), what version 1 covers, what it does not do | your task 3 | Sun 23:00 | the team (Thursday) | `team/akanksha/PITCH.md` |
| 10 | Review the user-journey design (https://claude.ai/artifact/9Sx4wLkfzPwzhuerVaCcCE): does the flow make sense, should a site supervisor role be added? Does the worker screen match your result page? Leave comments on it | Akshat's design | Sun 23:00 | Akshat (UI layer by Tue) | comments on the design |

## Hand-offs

- **To Diego, Sat 21:00:** the mock-up build list and schedule, before the Sunday photos.
- **To Akshat, Sat 23:00:** confirmed Eurocode 8 values, the fix-wording suggestions.
- **To Akshat, Sun 12:00:** the result page as a PR into `03_app/`.
- **From Akshat:** `team/akshat/sample_result.json` is ready.

## Rules

- Only openly licensed data. Never commit full-size photos, data, weights, passwords or API keys.
- Depth Anything: only the Small model (Apache-2.0). Base and Large are non-commercial.
- Upload to GitHub as in `team/README.md`: branch, commit, pull request.
