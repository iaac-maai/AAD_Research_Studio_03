"""
Concrete Evidence - one pipeline, from site video to a live rebar check.

    python pipeline.py <stage> [options]

Stages, in order:
  markers    print the 4 ArUco markers (A4, 100 mm)
  frames     site / mock-up videos -> sharp, non-duplicate frames to label
  upload     send those frames to the Roboflow project for labelling      (needs ROBOFLOW_API_KEY)
  sord       download + convert SORD, the open synthetic pre-training set
  pull       download your labelled Roboflow version as YOLO-seg           (needs ROBOFLOW_API_KEY)
  train      pretrain on SORD, or fine-tune on your labels
  eval       score a model on a dataset's val split -> JSON
  export     best.pt -> CoreML (iPhone) / TFLite (Android) / ONNX (server)
  live       run the model on a webcam, phone stream or video

Example run, start to finish:
  python pipeline.py markers
  python pipeline.py frames videos/*.mp4
  python pipeline.py upload
      ... label bar / tie / hook_90 / hook_135 in Roboflow, then Generate a version ...
  python pipeline.py sord --shards 2
  python pipeline.py train --stage pretrain          # better in Colab (GPU)
  python pipeline.py pull --version 1
  python pipeline.py train --stage finetune
  python pipeline.py eval
  python pipeline.py export --format coreml
  python pipeline.py live --source 0

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

# Roboflow project the team labels in (see training/move_images_to_roboflow.ipynb)
RF_WORKSPACE = "akshat-dayal-students-iaac-net"
RF_PROJECT = "concrete-evidence-column-cages"

PATHS = {
    "frames": ROOT / "data" / "frames",
    "sord": ROOT / "data" / "sord",
    "sord_yolo": ROOT / "data" / "sord_yolo",
    "ours": ROOT / "data" / "ours",
    "runs": ROOT / "runs",
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


def st_pull(a):
    from roboflow import Roboflow
    proj = Roboflow(api_key=need_key()).workspace(RF_WORKSPACE).project(RF_PROJECT)
    proj.version(a.version).download("yolov8", location=str(PATHS["ours"]), overwrite=True)
    print(f"Labelled data in {PATHS['ours']} (data.yaml inside)")


def st_train(a):
    if a.stage == "pretrain":
        data, start, name = PATHS["sord_yolo"] / "data.yaml", a.model or "yolov8n-seg.pt", "pretrain"
    else:
        data, name = PATHS["ours"] / "data.yaml", "finetune"
        start = a.model or (PRETRAIN if PRETRAIN.exists() else "yolov8n-seg.pt")
    if not Path(data).exists():
        raise SystemExit(f"{data} not found. Run the 'sord' or 'pull' stage first.")
    device = a.device or ("0" if has_gpu() else "cpu")
    if device == "cpu" and not a.force_cpu:
        raise SystemExit("No CUDA GPU here. Train in Colab (training/train_sord_yolov8seg.ipynb),\n"
                         "or add --force-cpu for a short test run (e.g. --epochs 3 --imgsz 640).")
    from ultralytics import YOLO  # imported late so the checks above run without it

    YOLO(str(start)).train(data=str(data), epochs=a.epochs, imgsz=a.imgsz, batch=a.batch,
                           patience=a.patience, device=device, project=str(PATHS["runs"]),
                           name=name, exist_ok=True)
    print(f"Weights: {PATHS['runs'] / name / 'weights' / 'best.pt'}")


def st_eval(a):
    from ultralytics import YOLO
    model = a.model or best_model()
    data = a.data or (PATHS["ours"] / "data.yaml" if (PATHS["ours"] / "data.yaml").exists()
                      else PATHS["sord_yolo"] / "data.yaml")
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
    path = YOLO(str(model)).export(format=a.format, imgsz=a.imgsz)
    print(f"Exported {model} -> {path}")


def st_live(a):
    args = ["live/live.py", "--model", a.model or best_model(), "--source", a.source, "--imgsz", a.imgsz]
    if a.auto:
        args.append("--auto")
    run(PY, *args)


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

    s = sub.add_parser("sord", help="download + convert SORD"); s.add_argument("--shards", type=int, default=2)
    s.set_defaults(fn=st_sord)

    s = sub.add_parser("pull", help="labelled Roboflow version -> data/ours")
    s.add_argument("--version", type=int, required=True); s.set_defaults(fn=st_pull)

    s = sub.add_parser("train", help="pretrain on SORD or fine-tune on our labels")
    s.add_argument("--stage", choices=["pretrain", "finetune"], required=True)
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
    s.set_defaults(fn=st_export)

    s = sub.add_parser("live", help="run on webcam / stream / video")
    s.add_argument("--source", default="0"); s.add_argument("--model", default=None)
    s.add_argument("--imgsz", type=int, default=640); s.add_argument("--auto", action="store_true")
    s.set_defaults(fn=st_live)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
