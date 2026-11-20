# Pipeline: from site video to a live rebar check

One script, `pipeline.py`, runs every stage. Each stage reads what the stage before it wrote, so you can stop and pick up again at any point.

```
 FILM         LABEL                TRAIN                              SCORE      USE        CHECK
 ────         ─────                ─────                              ─────      ───        ─────
 markers ──► frames ──► upload ──► pretrain (ConRebSeg, real sites) ┐
                        (Roboflow:                                  ├─► eval ──► export ──► live ──C──► check ──► a person
                         label) ──► pull ──► train finetune ────────┘  (scores)  (phone)  (capture)  (vs bending   confirms
                                                                                                      schedule)    or rejects
```

## Setup (once per laptop)

```bash
py -3.13 -m venv .venv
.venv\Scripts\activate                       # bash: source .venv/Scripts/activate
pip install torch==2.15.0 torchvision==0.29.2 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python -m concrete_evidence.privacy --fetch   # face model (230 KB, MIT) for blurring workers' faces
```

Every saved frame has faces blurred first (GDPR). Without the face model, frame
extraction and captures stop with an error rather than save a face unblurred.

For the stages that talk to Roboflow, set your own key in the terminal. Never put it in a file.

```powershell
$env:ROBOFLOW_API_KEY = "..."
```

## The stages

| # | Stage | Command | What it gives you |
|---|---|---|---|
| 1 | **Markers** | `python pipeline.py markers` | `live/markers_A4.png`: ArUco ids 0–3, 100 mm, DICT_4X4_50. Print at 100 %, measure one, stick them just outside the cage corners. |
| 2 | **Film** | (phone) | Walk the cage slowly from above, the way the crew would. Vary light and angle. 30–60 s per cage. |
| 3 | **Frames** | `python pipeline.py frames videos/*.mp4` | `data/frames/`: one frame every 0.5 s, blurry and duplicate frames dropped. |
| 4 | **Upload** | `python pipeline.py upload` | Frames sent to the Roboflow project `concrete-evidence-column-cages`. |
| 5 | **Label** | (Roboflow) | Outline every piece as a polygon: `bar · tie · hook_90 · hook_135`. Smart Polygon speeds it up. Aim for 150–300 frames. Then **Generate** a version with blur/brightness augmentation. |
| 6 | **ConRebSeg** | `python pipeline.py conrebseg` | Real construction-site photos (DTU, CC BY 4.0), self-collected part only (no YouTube), `ExposedBars` as `bar`, converted to YOLO-seg in `data/conrebseg_yolo/` with its own train / val / test split. Download it into `data/conrebseg/` first (22.6 GB: `ConRebSeg.zip` + `samples.json`, see the notebook). `--limit 1000` for a quick run. SORD (`python pipeline.py sord`, synthetic, CC BY-NC) stays as an optional quick test. |
| 7 | **Pretrain** | `python pipeline.py train --stage pretrain` | The baseline, on ConRebSeg (`--data sord` for SORD): `runs/pretrain/weights/best.pt`. Needs a GPU: use the Colab notebook `training/train_rebar_yolov8seg.ipynb`, Part A. |
| 8 | **Pull** | `python pipeline.py pull --version 1` | Your labelled version in `data/ours/`. |
| 9 | **Fine-tune** | `python pipeline.py train --stage finetune` | `runs/finetune/weights/best.pt`, starting from the baseline weights, same seed. GPU / Colab (Part B of the notebook). |
| 10 | **Evaluate** | `python pipeline.py eval` | `runs/eval.json`: mask precision, recall, mAP per class. These are the numbers for the `[__]` boxes on the slides. |
| 11 | **Export** | `python pipeline.py export --format coreml` | Model for the phone (`coreml` iPhone/iPad, `tflite` Android, `onnx` server). |
| 12 | **Live** | `python pipeline.py live --source 0` | Webcam (or `--source video.mp4`, or a phone stream URL). Masks, a tracking ID per bar, markers, mm scale. Says **READY TO CHECK** when all 4 markers are in view and the camera is still; press **C** to save that frame and its detections in mm to `live/captures/` (faces blurred). |
| 13 | **Check** | `python pipeline.py check --schedule live/schedule_example.json` | The latest capture against the bar bending schedule: bar count (missing bar), bar size, spacing (shifted or missing bar), hook angle (90° vs 135°) and hook tail length. Writes `<capture>.check.json`, every fault with the bars' tracking ids, for a person to confirm or reject. |

Weights and data never go into git (`runs/`, `data/`, `*.pt` are ignored). Keep `best.pt` on the team Google Drive.

## Why two training stages

- **ConRebSeg** teaches what exposed rebar looks like on real sites: about 26,000 outlined bars in 12,000 photos, with dust, shadow and clutter. One class, `bar`.
- **Our labels** teach the classes we actually check (`bar`, `tie`, hooks) on real camera frames: blur, glare, our phone, our cages. Bar-by-bar checking needs this stage.

## Where the live view hands over to the checker

Live video is for aiming and the overlay. The measured check runs on one **captured** frame: all 4 markers visible, camera still. Each capture saves the photo, the annotated photo and a JSON with every detection's tracking id, class, centre, and length, width and direction taken from its mask, in px and mm.

## The check: formulas against the bending schedule

The engineer's bar bending schedule says what the cage must be. Write it as JSON (copy `live/schedule_example.json`): bar diameter, number of bars, spacing, hook angle and tail length as a multiple of the diameter, plus tolerances. Each check is a formula on the capture (`concrete_evidence/check.py`):

| Check | Fault when | Why it matters |
|---|---|---|
| Bar count | fewer or more bars than scheduled | a missing bar |
| Spacing | a gap between neighbouring parallel bars is off by more than the tolerance; over 1.5 × the spacing means a bar is probably missing or shifted | cover and load paths |
| Bar size | a bar's width is off the scheduled diameter (markers needed) | wrong bar delivered |
| Hook angle | a `hook_90` where the schedule says 135° | 90° stirrup hooks opened up in earthquakes, where 135° hooks hold |
| Hook tail | the hook's outline is shorter than factor × tie diameter | a short tail pulls out |

- **Scale:** the markers when they are in view. Without them, the scheduled bar diameter over the bars' median width in pixels (rougher, and bar size can't then be checked).
- **Tail factor:** the example uses 10 × the diameter. Check the figure your code requires (Eurocode 2 / 8 or local) before relying on it.
- **A person decides.** The result is never "approved". It lists faults for someone on site to confirm or reject: the camera can miss a bar hidden behind another (occlusion), and columns and beams fail in different ways.
- The checks assume a view close to top-down onto one layer of bars. Depth (Depth Anything) is the next step for telling the layers apart.

## Tested so far (20 Nov 2026, laptop CPU)

- SORD shards 0–1: 200 images, about 24,000 labelled objects, converted to YOLO-seg.
- 3-epoch CPU test training: the pipeline runs end to end. The scores are low, as expected from 3 epochs on 100 images. Use them only as proof that the pipeline works.
- `live.py` on a test video with markers pasted in: 4/4 markers found, scale measured at 1.053 mm/px (about 1.04 expected), READY shown only once the camera was still, captures saved. 0.7 fps on this laptop's CPU while training ran alongside; a phone with the exported model will be far faster.
- `check` on made-up captures (tests in `tests/test_check.py`): a missing bar, a shifted bar, a thin bar, a 90° hook and a short tail are each found; a cage as scheduled has none.
- Not tested yet: `upload` and `pull` (need the Roboflow key), GPU training, `export` to CoreML, `check` on a real capture from the trained model.
