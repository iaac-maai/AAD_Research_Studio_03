# Work plan: Diego, Sat 21 – Mon 23 Nov 2026

Paste this file into your Claude session as the brief. Repo: `iaac-maai/AAD_Research_Studio_03`. Read `team/README.md`, `team/TIMELINE.md`, `datasets/CATALOGUE.md` ("The plan without site access") and `docs/HANDOVER_DIEGO.md` first.

**Your role:** the data and the first trained model. We have no site access, so the labelled set comes from open data online, open-licence photos and a fab-lab mock-up. Akshat needs a first `best.pt` on **Mon 23 Nov, 10:00**.

**Where your work goes:** dataset checks, `sources.csv`, labelling notes, training scores → `team/diego/` (by pull request). The "Checked" column → `datasets/CATALOGUE.md`. Photos → Roboflow and the team Drive, **never GitHub**. `best.pt` → Drive (`MyDrive/ConcreteEvidence/runs`).

## In this order, with deadlines

**Bold deadlines block someone else:** if you're late, they wait. Yours are **the Roboflow version (Sun 20:00)** and **training started (Sun 21:00)**, so that **`best.pt` + scores are ready Mon 10:00**: Akshat swaps your model into the live app on Monday. You wait on Akanksha only for the mock-up (Sat 21:00) and the fab-lab session (Sun 14:00–17:00); everything else you can start now.

| # | Task | Waits on | Finish by | Who waits on it | Output |
|---|---|---|---|---|---|
| 1 | Logged in to Roboflow, open each "to check one by one" project in `datasets/CATALOGUE.md`: licence CC BY 4.0? labels polygons? | nobody: start now | Sat 18:00 | you (task 2) | "Checked" column in `datasets/CATALOGUE.md` |
| 2 | Fork the good ones into `concrete-evidence-column-cages`; map classes to `bar · tie · hook_90 · hook_135`, delete the rest | your task 1 | Sat 20:00 | you (tasks 5, 6) | one Roboflow project, our 4 classes |
| 3 | Collect 50+ open-licence column-cage photos: Wikimedia Commons ("rebar column", "reinforcement cage", "stirrup") and Flickr filtered to CC0 / CC BY / CC BY-SA. Cages before the pour only | nobody: start now (alongside 1) | Sat 20:00 | you (task 4) | photos → Drive; `team/diego/sources.csv` (file, URL, author, licence) |
| 4 | Upload: `python pipeline.py upload --folder <dir> --batch web_photos` (`ROBOFLOW_API_KEY` in the terminal only) | your task 3 | Sat 21:00 | you (task 5) | photos in Roboflow |
| 5 | Label as polygons (Smart Polygon helps) | your tasks 2, 4 | Sat 24:00 | you (task 9) | 100 labelled |
| 6 | Box-only sets (Column Tie, SteelBindings, stirrups): boxes → outlines with Smart Polygon, fix by hand | your task 2 | Sun 13:00 | you (task 9) | 100+ more labelled, mostly `tie` |
| 7 | Fab-lab session: photograph every face, 4 markers in view, correct and with the planted faults; upload and label | Akanksha's mock-up design (Sat 21:00) and build (Sun 14:00) | session **Sun 14:00–17:00**, labelled by Sun 19:00 | you (task 8) | photos uploaded and labelled |
| 8 | Hold out the photos of one mock-up cage (about 15) as the test set | your task 7 | Sun 19:00 | you (task 9) | tagged "test" |
| 9 | Generate a version: 70/20/10, blur + brightness augmentation | your tasks 5, 6, 8; 300+ images | **Sun 20:00** | you (task 10) | version 1 |
| 10 | Train the baseline in Colab: `training/train_rebar_yolov8seg.ipynb`, Part A, T4 GPU; `best.pt` to Drive | your task 9 | **started by Sun 21:00** (runs overnight) | Akshat (Mon) | `best.pt` on the Drive |
| 11 | Optional: same run on depth-filtered photos (`python pipeline.py depth data/ours --out data/ours_depth`), same seed | your task 9 | Sun 22:00 | the team (is depth worth it?) | second run |
| 12 | Write the scores: mask mAP50, precision, recall per class, above all `hook_90` vs `hook_135` | your task 10 | **Mon 10:00** | Akshat (swaps the model in by Mon 12:00) | `team/diego/RESULTS.md` + team board |
| 13 | Review the user-journey design (https://claude.ai/artifact/9Sx4wLkfzPwzhuerVaCcCE): does the flow make sense, should a site supervisor role be added? Leave comments on it | Akshat's design | Sun 23:00 | Akshat (UI layer by Tue) | comments on the design |

## Hand-offs

- **From Akanksha, Sat 21:00:** the mock-up build list and schedule, so the planted faults match it (needed before 7).
- **To Akshat, Mon 10:00:** Roboflow version number, `best.pt` on the Drive, `team/diego/RESULTS.md`.

## Rules

- Only openly licensed data. No Google Images, no YouTube frames. Credit every CC BY / CC BY-SA source in `sources.csv`.
- Never commit photos, data, weights or keys. The notebook asks for the Roboflow key with getpass: never paste it into a file or a chat.
- Labelling: every visible piece gets its own polygon; don't outline hidden parts; `hook_90` / `hook_135` = the bent end of a tie.
- Upload to GitHub as in `team/README.md`: branch, commit, pull request.
