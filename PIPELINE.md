# Pipeline: from site video to a live rebar check

One script, `pipeline.py`, runs every stage. Each stage reads what the stage before it wrote, so you can stop and pick up again at any point.

```
 FILM            LABEL               TRAIN                        CHECK              USE
 ────            ─────               ─────                        ─────              ───
 markers ──► frames ──► upload ──►  sord ──► train pretrain ─┐
                        (Roboflow:   (open, synthetic)        ├─► eval ──► export ──► live
                        label bars) ──► pull ──► train finetune ┘   (scores)  (phone)   (webcam / phone / video)
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
| 6 | **SORD** | `python pipeline.py sord --shards 2` | Open synthetic rebar set (CC BY-NC 4.0), converted to YOLO-seg in `data/sord_yolo/`. |
| 7 | **Pretrain** | `python pipeline.py train --stage pretrain` | `runs/pretrain/weights/best.pt`. Needs a GPU: use the Colab notebook `training/train_sord_yolov8seg.ipynb`. |
| 8 | **Pull** | `python pipeline.py pull --version 1` | Your labelled version in `data/ours/`. |
| 9 | **Fine-tune** | `python pipeline.py train --stage finetune` | `runs/finetune/weights/best.pt`, starting from the SORD weights. GPU / Colab (Part B of the notebook). |
| 10 | **Evaluate** | `python pipeline.py eval` | `runs/eval.json`: mask precision, recall, mAP per class. These are the numbers for the `[__]` boxes on the slides. |
| 11 | **Export** | `python pipeline.py export --format coreml` | Model for the phone (`coreml` iPhone/iPad, `tflite` Android, `onnx` server). |
| 12 | **Live** | `python pipeline.py live --source 0` | Webcam (or `--source video.mp4`, or a phone stream URL). Masks, a tracking ID per bar, markers, mm scale. Says **READY TO CHECK** when all 4 markers are in view and the camera is still; press **C** to save that frame and its detections in mm to `live/captures/`. |

Weights and data never go into git (`runs/`, `data/`, `*.pt` are ignored). Keep `best.pt` on the team Google Drive.

## Why two training stages

- **SORD** teaches what rebar looks like (thousands of bars, free labels), but it is rendered, and its classes are `intersection` (crossings) and `spacing` (the **gaps** between bars), not bars.
- **Our labels** teach the classes we actually check (`bar`, `tie`, hooks) on real camera frames: blur, glare, our phone, our cages. Bar-by-bar checking needs this stage.

## Where the live view hands over to the checker

Live video is for aiming and the overlay. The measured check (missing bar, spacing in mm) runs on one **captured** frame: all 4 markers visible, camera still. Each capture saves the photo, the annotated photo and a JSON with every detection's tracking id, class, centre and size in mm. That JSON is the input for the bar-by-bar comparison against the drawing.

## Tested so far (20 Nov 2026, laptop CPU)

- SORD shards 0–1: 200 images, about 24,000 labelled objects, converted to YOLO-seg.
- 3-epoch CPU test training: the pipeline runs end to end. The scores are low, as expected from 3 epochs on 100 images. Use them only as proof that the pipeline works.
- `live.py` on a test video with markers pasted in: 4/4 markers found, scale measured at 1.053 mm/px (about 1.04 expected), READY shown only once the camera was still, captures saved. 0.7 fps on this laptop's CPU while training ran alongside; a phone with the exported model will be far faster.
- Not tested yet: `upload` and `pull` (need the Roboflow key), GPU training, `export` to CoreML.
