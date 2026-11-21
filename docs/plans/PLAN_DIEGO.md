# Work plan: Diego, Sat 21 – Sun 22 Nov 2026

Paste this file into your Claude session as the brief. Repo: `iaac-maai/AAD_Research_Studio_03`. Read `datasets/CATALOGUE.md` ("The plan without site access") and `docs/HANDOVER_DIEGO.md` first.

## Where the project is

- Concrete Evidence checks column rebar before the pour: photo → YOLOv8-seg outlines `bar · tie · hook_90 · hook_135` → measured in mm → checked against the schedule and Eurocode 8 → fix list.
- The pipeline is built. **The model is not trained yet: there is no labelled data.** That is your job this weekend.
- We have **no site access**, so we don't film on site. The labelled set comes from open data online, open-licence photos and a fab-lab mock-up.
- Presentation Thu 26 Nov. Akshat needs a first `best.pt` on Mon 23 Nov.

**Your role:** the data and the first trained model.

## Today, Sat 21 Nov

| # | Task | Done when |
|---|---|---|
| 1 | Logged in to Roboflow, open each "to check one by one" project in `datasets/CATALOGUE.md`: confirm the licence is CC BY 4.0 and the labels are polygons. Fork the good ones into `concrete-evidence-column-cages` | the "Checked" column filled in (yes / no + reason) |
| 2 | Map their classes to ours (`bar · tie · hook_90 · hook_135`); delete classes we don't use | one Roboflow project, our 4 classes only |
| 3 | Collect open-licence cage photos: Wikimedia Commons (search "rebar column", "reinforcement cage", "stirrup") and Flickr (licence filter: CC0, CC BY, CC BY-SA). Column cages before the pour only | 50+ photos + `sources.csv` (file, URL, author, licence) on the team Drive |
| 4 | Upload them: `python pipeline.py upload --folder <dir> --batch web_photos` (set `ROBOFLOW_API_KEY` in the terminal, never in a file) | in Roboflow, ready to label |
| 5 | Start labelling as polygons (Smart Polygon speeds it up) | 100 images labelled |

## Tomorrow, Sun 22 Nov

| # | Task | Done when |
|---|---|---|
| 6 | Box-only sets (Column Tie, SteelBindings, stirrups): turn the boxes into outlines with Smart Polygon, fix by hand, keep only the useful images | 100+ more labelled, mostly `tie` |
| 7 | Fab-lab mock-up session with the team (afternoon): photograph every face, 4 markers in view, correct cage and with planted faults (tie removed, hook bent to 90°, bar shifted). Video is fine: `python pipeline.py frames videos/*.mp4` | photos uploaded, labelled |
| 8 | Hold out the photos of one mock-up cage (about 15) as the test set | tagged "test" in Roboflow |
| 9 | Generate a version: 70/20/10, blur + brightness augmentation | version 1 exists, 300+ images |
| 10 | Start the baseline in Colab: `training/train_rebar_yolov8seg.ipynb`, Part A, T4 GPU. Runs overnight; `best.pt` saved to Drive | training running |
| 11 | Optional, if time: the same run on depth-filtered photos (`python pipeline.py depth data/ours --out data/ours_depth`), same seed, to compare | second run started |

## Hand-offs

- **To Akshat, Mon 23:** Roboflow version number, `best.pt` on the team Drive, scores (mask mAP50, precision, recall per class, above all `hook_90` vs `hook_135`) logged on the team board.
- **From Akanksha:** the mock-up build list and its schedule JSON (Sat), so the planted faults match the schedule.

## Rules

- Only openly licensed data. No Google Images, no YouTube frames, nothing without a licence. Credit every CC BY / CC BY-SA source in `sources.csv`.
- Never commit data, photos, weights or keys. The notebook asks for the Roboflow key with getpass: never paste it into a file or the chat.
- Labelling: every visible piece gets its own polygon; don't outline hidden parts; `hook_90` / `hook_135` = the bent end of a tie.
- Branch + PR for any repo change (e.g. the "Checked" column in the catalogue).
