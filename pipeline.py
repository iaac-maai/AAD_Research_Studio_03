"""
Concrete Evidence - one pipeline, from site video to a live rebar check.

    python pipeline.py <stage> [options]

Stages, in order:
  markers    print the 4 ArUco markers (A4, 100 mm)
  frames     site / mock-up videos -> sharp, non-duplicate frames to label
  upload     send those frames to the Roboflow project for labelling      (needs ROBOFLOW_API_KEY)
  conrebseg  unpack + convert ConRebSeg (repair sites, CC BY 4.0): optional warm-up, exposed_rebar patches
  sord       download + convert SORD (synthetic, CC BY-NC): optional, for quick tests
  pull       download your labelled Roboflow version as YOLO-seg           (needs ROBOFLOW_API_KEY)
  depth      Depth Anything before YOLO: grey out what is far behind the cage (photos or a whole dataset)
  train      fine-tune on your labels (the baseline), or an optional warm-up on ConRebSeg / SORD
  eval       score a model on a dataset's val split -> JSON
  export     best.pt -> CoreML (iPhone) / TFLite (Android) / ONNX (server)
  live       run the model on a webcam, phone stream or video; press C to capture a frame
  check      a captured frame against the bar bending schedule -> faults for a person to confirm
  analyse    the whole check on one photo (what the model server runs): photo -> faults + fix list

Example run, start to finish:
  python pipeline.py markers
  python pipeline.py frames videos/*.mp4
  python pipeline.py upload
      ... label bar / tie / hook_90 / hook_135 in Roboflow, then Generate a version ...
  python pipeline.py pull --version 1
  python pipeline.py depth data/ours --out data/ours_depth   # optional: train on depth-filtered photos
  python pipeline.py train --stage finetune          # baseline; better in Colab (GPU)
  python pipeline.py eval
  python pipeline.py export --format coreml
  python pipeline.py live --source 0                 # add --depth-filter if you trained on data/ours_depth
  python pipeline.py check --schedule live/schedule_example.json     # latest capture
  python pipeline.py check --schedule live/schedule_example.json --zone middle --face A
  python pipeline.py analyse photo.jpg --schedule live/schedule_example.json --face A

The API key is read from the environment only. Never write it into a file in this repo.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

# Roboflow project the team labels in: Diego's workspace (the forks and labels live there).
# Override with RF_WORKSPACE / RF_PROJECT in the terminal to use another copy.
RF_WORKSPACE = os.environ.get("RF_WORKSPACE", "diegos-workspace-puwbt")
RF_PROJECT = os.environ.get("RF_PROJECT", "concrete-evidence-column-cages-ft8gc")

PATHS = {
    "frames": ROOT / "data" / "frames",
    "sord": ROOT / "data" / "sord",
    "sord_yolo": ROOT / "data" / "sord_yolo",
    "conrebseg": ROOT / "data" / "conrebseg",
    "conrebseg_yolo": ROOT / "data" / "conrebseg_yolo",
    "ours": ROOT / "data" / "ours",
    "runs": ROOT / "runs",
    "captures": ROOT / "live" / "captures",
}
PRETRAIN = PATHS["runs"] / "pretrain" / "weights" / "best.pt"
FINETUNE = PATHS["runs"] / "finetune" / "weights" / "best.pt"


def run(*args):
    print("$", " ".join(str(a) for a in args))
    subprocess.run([str(a) for a in args], check=True, cwd=ROOT)


def need_key():
    key = os.environ.get("ROBOFLOW_API_KEY")
    if not key:
        raise SystemExit("Set ROBOFLOW_API_KEY first (Roboflow > Settings > API Keys).\n"
                         "  PowerShell: $env:ROBOFLOW_API_KEY = \"...\"\n  bash: export ROBOFLOW_API_KEY=...")
    return key


def best_model():
    for p in (FINETUNE, PRETRAIN):
        if p.exists():
            return p
    return "yolov8n-seg.pt"


def has_gpu():
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


# ------------------------------------------------------------------ stages ---

def st_markers(a):
    run(PY, "live/make_markers.py", "--mm", a.mm)


def st_frames(a):
    run(PY, "training/extract_frames.py", *a.videos, "--out", PATHS["frames"], "--every", a.every)


def st_upload(a):
    from roboflow import Roboflow
    imgs = sorted(p for p in Path(a.folder).glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    if not imgs:
        raise SystemExit(f"No images in {a.folder}. Run: python pipeline.py frames VIDEO ...")
    proj = Roboflow(api_key=need_key()).workspace(RF_WORKSPACE).project(RF_PROJECT)
    for i, p in enumerate(imgs, 1):
        proj.upload(str(p), batch_name=a.batch, tag_names=[a.batch])
        print(f"  {i}/{len(imgs)} {p.name}")
    print(f"Uploaded {len(imgs)} images to {RF_PROJECT}, batch '{a.batch}'. Label them in Roboflow.")


def st_sord(a):
    run(PY, "datasets/download_datasets.py", "--sord-shards", a.shards, "--skip-roboflow")
    shards = sorted(str(p) for p in PATHS["sord"].glob("SORD-train-*") if p.is_dir())
    if len(shards) < 2:
        raise SystemExit("Need at least 2 shards (one is held out for validation).")
    run(PY, "training/coco_to_yolo_seg.py", "--train", *shards[:-1], "--val", shards[-1],
        "--out", PATHS["sord_yolo"])


def st_conrebseg(a):
    from concrete_evidence import conrebseg as crs
    root = PATHS["conrebseg"]
    if not (root / "samples.json").exists():
        raise SystemExit(f"{root / 'samples.json'} not found. Download ConRebSeg first (datasets/CATALOGUE.md).")
    if not a.skip_extract:
        zp = root / "ConRebSeg.zip"
        if not zp.exists():
            raise SystemExit(f"{zp} not found. Download it first, or pass --skip-extract if already unpacked.")
        print(f"unpacked {crs.extract(zp, root)} new images (self-collected only, no YouTube)")
    stats = crs.convert(root, PATHS["conrebseg_yolo"], limit=a.limit)
    print(json.dumps(stats, indent=2))
    print(f"wrote {PATHS['conrebseg_yolo'] / 'data.yaml'}")


def st_depth(a):
    from concrete_evidence import depth as dp
    src = Path(a.source)
    if not src.exists():
        raise SystemExit(f"{src} not found: give a photo, a folder of photos or a YOLO dataset folder.")
    out = Path(a.out) if a.out else src.with_name(src.stem + "_depth")
    print(f"loading {dp.MODEL_ID} (Apache-2.0); first run downloads about 100 MB")
    model = dp.DepthAnything(device=a.device)
    res = dp.filter_folder(model, src, out, a.threshold, a.margin, a.slices, a.preview)
    kept = [f["kept"] for f in res["files"].values()]
    avg = f", on average {100 * sum(kept) / len(kept):.0f}% of each photo kept" if kept else ""
    print(f"{res['images']} photo(s) filtered{avg} -> {out}")


def st_pull(a):
    from roboflow import Roboflow
    proj = Roboflow(api_key=need_key()).workspace(RF_WORKSPACE).project(RF_PROJECT)
    proj.version(a.version).download("yolov8", location=str(PATHS["ours"]), overwrite=True)
    print(f"Labelled data in {PATHS['ours']} (data.yaml inside)")


def st_train(a):
    if a.stage == "pretrain":
        data, start, name = PATHS[f"{a.data}_yolo"] / "data.yaml", a.model or "yolov8n-seg.pt", "pretrain"
    else:
        # The baseline starts from the standard pretrained weights. A warm-up (ConRebSeg / SORD) is opt-in
        # with --model runs/pretrain/weights/best.pt, so the two can be compared on the same split.
        data, name = PATHS["ours"] / "data.yaml", "finetune"
        start = a.model or "yolov8n-seg.pt"
    if not Path(data).exists():
        raise SystemExit(f"{data} not found. Run the 'conrebseg', 'sord' or 'pull' stage first.")
    device = a.device or ("0" if has_gpu() else "cpu")
    if device == "cpu" and not a.force_cpu:
        raise SystemExit("No CUDA GPU here. Train in Colab (training/train_rebar_yolov8seg.ipynb),\n"
                         "or add --force-cpu for a short test run (e.g. --epochs 3 --imgsz 640).")
    from ultralytics import YOLO  # imported late so the checks above run without it

    YOLO(str(start)).train(data=str(data), epochs=a.epochs, imgsz=a.imgsz, batch=a.batch,
                           patience=a.patience, device=device, project=str(PATHS["runs"]),
                           name=name, exist_ok=True)
    print(f"Weights: {PATHS['runs'] / name / 'weights' / 'best.pt'}")


def st_eval(a):
    from ultralytics import YOLO
    model = a.model or best_model()
    data = a.data or next((PATHS[k] / "data.yaml" for k in ("ours", "conrebseg_yolo", "sord_yolo")
                           if (PATHS[k] / "data.yaml").exists()), PATHS["ours"] / "data.yaml")
    m = YOLO(str(model)).val(data=str(data), imgsz=a.imgsz, split="val", plots=False, verbose=False)
    res = {"model": str(model), "data": str(data),
           "box_mAP50": round(float(m.box.map50), 4), "mask_mAP50": round(float(m.seg.map50), 4),
           "mask_mAP50_95": round(float(m.seg.map), 4),
           "mask_precision": round(float(m.seg.mp), 4), "mask_recall": round(float(m.seg.mr), 4),
           "per_class_mask_mAP50_95": {m.names[i]: round(float(v), 4) for i, v in enumerate(m.seg.maps)}}
    out = PATHS["runs"] / "eval.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2), f"\nwrote {out}")


def st_export(a):
    from ultralytics import YOLO
    model = a.model or best_model()
    extra = {"simplify": True, "opset": 17, "dynamic": False} if a.format == "onnx" else {}
    path = YOLO(str(model)).export(format=a.format, imgsz=a.imgsz, **extra)
    print(f"Exported {model} -> {path}")
    if a.format == "onnx" and a.check:  # same photo through both: do they agree?
        import cv2

        from concrete_evidence.onnx_seg import OnnxSeg, compare
        img = cv2.imread(a.check)
        if img is None:
            raise SystemExit(f"Could not read the photo {a.check}")
        res = compare(YOLO(str(model)), OnnxSeg(path), img, imgsz=a.imgsz)
        print(json.dumps(res, indent=2))
        if not res["same_count"]:
            raise SystemExit("ONNX and PyTorch found a different number of pieces: check the export")


def st_live(a):
    args = ["live/live.py", "--model", a.model or best_model(), "--source", a.source, "--imgsz", a.imgsz]
    if a.auto:
        args.append("--auto")
    if a.depth_filter:
        args.append("--depth-filter")
    run(PY, *args)


def st_check(a):
    from concrete_evidence.check import load_schedule, summary
    from concrete_evidence.check import run as run_checks
    if a.capture:
        cap_path = Path(a.capture)
    else:
        caps = sorted(p for p in PATHS["captures"].glob("*.json") if not p.name.endswith(".check.json"))
        if not caps:
            raise SystemExit(f"No captures in {PATHS['captures']}. Run the live view and press C first.")
        cap_path = caps[-1]
    try:
        schedule = load_schedule(a.schedule)
    except (OSError, ValueError) as e:
        raise SystemExit(f"Schedule {a.schedule}: {e}") from e
    try:
        result = run_checks(json.loads(cap_path.read_text()), schedule, zone=a.zone, face=a.face)
    except ValueError as e:
        raise SystemExit(str(e)) from e
    result["capture"] = cap_path.name
    out = cap_path.with_suffix(".check.json")
    out.write_text(json.dumps(result, indent=2))
    print(summary(result), f"\nwrote {out}")


def st_analyse(a):
    import cv2

    from concrete_evidence.check import load_schedule, summary
    from concrete_evidence.infer import analyse
    img = cv2.imread(a.photo)
    if img is None:
        raise SystemExit(f"Could not read the photo {a.photo}")
    try:
        schedule = load_schedule(a.schedule)
    except (OSError, ValueError) as e:
        raise SystemExit(f"Schedule {a.schedule}: {e}") from e
    weights = str(a.model or best_model())
    if weights.endswith(".onnx"):  # ONNX Runtime, as on the server
        from concrete_evidence.onnx_seg import OnnxSeg
        model = OnnxSeg(weights)
    else:
        from ultralytics import YOLO
        model = YOLO(weights)
    depth = None
    if a.depth_filter:
        from concrete_evidence.depth import DepthAnything
        depth = DepthAnything()
    try:
        rename = dict(kv.split("=", 1) for kv in a.rename)
        out = analyse(img, schedule, model, depth=depth, zone=a.zone, face=a.face, conf=a.conf, imgsz=a.imgsz,
                      rename=rename)
    except (FileNotFoundError, ValueError) as e:
        raise SystemExit(str(e)) from e
    stem = Path(a.photo).with_suffix("")
    cv2.imwrite(f"{stem}_checked.jpg", out.pop("annotated"))
    Path(f"{stem}_checked.json").write_text(json.dumps(out, indent=2))
    print(summary(out["check"]), f"\nwrote {stem}_checked.jpg and {stem}_checked.json")


# --------------------------------------------------------------------- cli ---

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="stage_cmd", required=True)

    s = sub.add_parser("markers", help="print ArUco markers"); s.add_argument("--mm", type=float, default=100)
    s.set_defaults(fn=st_markers)

    s = sub.add_parser("frames", help="videos -> frames to label")
    s.add_argument("videos", nargs="+"); s.add_argument("--every", type=float, default=0.5)
    s.set_defaults(fn=st_frames)

    s = sub.add_parser("upload", help="frames -> Roboflow")
    s.add_argument("--folder", default=str(PATHS["frames"])); s.add_argument("--batch", default="site_frames")
    s.set_defaults(fn=st_upload)

    s = sub.add_parser("conrebseg", help="unpack + convert ConRebSeg (real sites)")
    s.add_argument("--limit", type=int, default=None, help="at most N images per split, for a quick run")
    s.add_argument("--skip-extract", action="store_true"); s.set_defaults(fn=st_conrebseg)

    s = sub.add_parser("sord", help="download + convert SORD"); s.add_argument("--shards", type=int, default=2)
    s.set_defaults(fn=st_sord)

    s = sub.add_parser("pull", help="labelled Roboflow version -> data/ours")
    s.add_argument("--version", type=int, required=True); s.set_defaults(fn=st_pull)

    s = sub.add_parser("depth", help="Depth Anything before YOLO: grey out the far background")
    s.add_argument("source", help="a photo, a folder of photos, or a YOLO dataset folder (labels are kept)")
    s.add_argument("--out", default=None, help="default: <source>_depth next to it")
    s.add_argument("--threshold", type=float, default=None, help="nearness to keep, 0-1 (default: automatic)")
    s.add_argument("--margin", type=int, default=15, help="grow the kept area by this many px")
    s.add_argument("--slices", type=int, default=0, help="also write N depth slices (layers), nearest first")
    s.add_argument("--preview", action="store_true", help="also write colour depth pictures")
    s.add_argument("--device", default=None); s.set_defaults(fn=st_depth)

    s = sub.add_parser("train", help="fine-tune on our labels, or an optional warm-up")
    s.add_argument("--stage", choices=["pretrain", "finetune"], required=True)
    s.add_argument("--data", choices=["conrebseg", "sord"], default="conrebseg", help="pretraining set")
    s.add_argument("--model", default=None); s.add_argument("--epochs", type=int, default=50)
    s.add_argument("--imgsz", type=int, default=640); s.add_argument("--batch", type=int, default=8)
    s.add_argument("--patience", type=int, default=15); s.add_argument("--device", default=None)
    s.add_argument("--force-cpu", action="store_true"); s.set_defaults(fn=st_train)

    s = sub.add_parser("eval", help="score a model -> runs/eval.json")
    s.add_argument("--model", default=None); s.add_argument("--data", default=None)
    s.add_argument("--imgsz", type=int, default=640); s.set_defaults(fn=st_eval)

    s = sub.add_parser("export", help="best.pt -> phone / server format")
    s.add_argument("--format", default="coreml", choices=["coreml", "tflite", "onnx"])
    s.add_argument("--model", default=None); s.add_argument("--imgsz", type=int, default=640)
    s.add_argument("--check", default=None, metavar="PHOTO", help="onnx: compare ONNX with PyTorch on this photo")
    s.set_defaults(fn=st_export)

    s = sub.add_parser("live", help="run on webcam / stream / video")
    s.add_argument("--source", default="0"); s.add_argument("--model", default=None)
    s.add_argument("--imgsz", type=int, default=640); s.add_argument("--auto", action="store_true")
    s.add_argument("--depth-filter", action="store_true", help="Depth Anything before YOLO on every frame")
    s.set_defaults(fn=st_live)

    s = sub.add_parser("check", help="captured frame vs bending schedule -> faults")
    s.add_argument("capture", nargs="?", default=None, help="capture JSON (default: the latest in live/captures)")
    s.add_argument("--schedule", required=True, help="bar bending schedule JSON (see live/schedule_example.json)")
    s.add_argument("--zone", choices=["end", "middle"], default=None,
                   help="column zone in the photo: end (near a floor, the default) or middle")
    s.add_argument("--face", default=None, help="which face of the column, e.g. A or north")
    s.set_defaults(fn=st_check)

    s = sub.add_parser("analyse", help="the whole check on one photo -> faults + fix list")
    s.add_argument("photo"); s.add_argument("--schedule", required=True)
    s.add_argument("--model", default=None); s.add_argument("--zone", choices=["end", "middle"], default=None)
    s.add_argument("--face", default=None); s.add_argument("--conf", type=float, default=0.25)
    s.add_argument("--imgsz", type=int, default=640)
    s.add_argument("--depth-filter", action="store_true", help="Depth Anything before YOLO")
    s.add_argument("--rename", nargs="*", default=[], help="model class=our class, e.g. skewer=bar")
    s.set_defaults(fn=st_analyse)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
