# Work plan: Diego, Sat 21 – Sun 22 Nov 2026

Paste this file into your Claude session as the brief. Repo: `iaac-maai/AAD_Research_Studio_03`. Read `team/README.md`, `datasets/CATALOGUE.md` ("The plan without site access") and `docs/HANDOVER_DIEGO.md` first.

**Your role:** the data and the first trained model. We have no site access, so the labelled set comes from open data online, open-licence photos and a fab-lab mock-up. Akshat needs a first `best.pt` on Mon 23 Nov.

**Where your work goes:** dataset checks, `sources.csv`, labelling notes, training scores → `team/diego/` (by pull request). The "Checked" column → `datasets/CATALOGUE.md`. Photos → Roboflow and the team Drive, **never GitHub**. `best.pt` → Drive (`MyDrive/ConcreteEvidence/runs`).

## In this order

| # | Task | Needs first | Done when | Goes to | When |
|---|---|---|---|---|---|
| 1 | Logged in to Roboflow, open each "to check one by one" project in `datasets/CATALOGUE.md`: licence CC BY 4.0? labels polygons? | — | yes / no + reason for each | `datasets/CATALOGUE.md` ("Checked" column) | Sat |
| 2 | Fork the good ones into `concrete-evidence-column-cages`; map their classes to `bar · tie · hook_90 · hook_135`, delete the rest | 1 | one project, our 4 classes | Roboflow | Sat |
| 3 | Collect open-licence column-cage photos: Wikimedia Commons ("rebar column", "reinforcement cage", "stirrup") and Flickr filtered to CC0 / CC BY / CC BY-SA. Cages before the pour only | — | 50+ photos + `sources.csv` (file, URL, author, licence) | photos → Drive; `team/diego/sources.csv` | Sat |
| 4 | Upload them: `python pipeline.py upload --folder <dir> --batch web_photos` (`ROBOFLOW_API_KEY` in the terminal only) | 3 | in Roboflow | Roboflow | Sat |
| 5 | Label as polygons (Smart Polygon helps) | 2, 4 | 100 labelled | Roboflow | Sat night |
| 6 | Box-only sets (Column Tie, SteelBindings, stirrups): boxes → outlines with Smart Polygon, fix by hand | 2 | 100+ more labelled, mostly `tie` | Roboflow | Sun morning |
| 7 | Fab-lab mock-up session: photograph every face, 4 markers in view, correct and with the planted faults | Akanksha's build list | photos uploaded and labelled | Roboflow, Drive | Sun afternoon |
| 8 | Hold out the photos of one mock-up cage (about 15) as the test set | 7 | tagged "test" | Roboflow | Sun afternoon |
| 9 | Generate a version: 70/20/10, blur + brightness augmentation | 5, 6, 8; 300+ images | version 1 exists | Roboflow | Sun evening |
| 10 | Train the baseline in Colab: `training/train_rebar_yolov8seg.ipynb`, Part A, T4 GPU; `best.pt` to Drive | 9 | training running overnight | Drive | Sun night |
| 11 | Optional: same run on depth-filtered photos (`python pipeline.py depth data/ours --out data/ours_depth`), same seed | 9 | second run started | Drive | Sun night |
| 12 | Write the scores: mask mAP50, precision, recall per class, above all `hook_90` vs `hook_135` | 10 | `team/diego/RESULTS.md` + team board | `team/diego/` | Mon morning |

## Hand-offs

- **From Akanksha, Sat:** the mock-up build list and schedule, so the planted faults match it (needed before 7).
- **To Akshat, Mon 23:** Roboflow version number, `best.pt` on the Drive, `team/diego/RESULTS.md`.

## Rules

- Only openly licensed data. No Google Images, no YouTube frames. Credit every CC BY / CC BY-SA source in `sources.csv`.
- Never commit photos, data, weights or keys. The notebook asks for the Roboflow key with getpass: never paste it into a file or a chat.
- Labelling: every visible piece gets its own polygon; don't outline hidden parts; `hook_90` / `hook_135` = the bent end of a tie.
- Upload to GitHub as in `team/README.md`: branch, commit, pull request.
