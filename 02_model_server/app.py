"""Concrete Evidence model server (Gradio): one photo in, the rebar check out.

A page for people (upload a photo, see the outlines and the fix list) and an API
for programs: `/predict` takes a base64 photo + the bar bending schedule (JSON)
+ the column zone and face, and returns the check result as JSON with the
annotated photo. The Cloudflare app calls `/predict`. Runs locally
(`python 02_model_server/app.py`) and on Render (render.yaml at the repo root).

It runs the model on ONNX Runtime, without PyTorch, so it fits Render's free
512 MB. A `.pt` file still works locally if Ultralytics is installed.

Settings, from the environment (Render: Environment tab):
  MODEL_PATH    weights to load: .onnx (ONNX Runtime) or .pt (Ultralytics); default models/best.onnx
  MODEL_REPO    a Hugging Face repo to download the weights from, e.g. iaac-maai/concrete-evidence-rebar
  MODEL_FILE    the file in that repo (default best.onnx)
  CLASS_RENAME  model class=our class, comma separated, e.g. skewer=bar for the skewer test model
  DEPTH_FILTER  1 to run Depth Anything (ONNX, 99 MB) before YOLO
"""

import base64
import json
import os
import sys
from pathlib import Path

import cv2
import gradio as gr
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from concrete_evidence import privacy  # noqa: E402
from concrete_evidence.check import DEFAULTS, summary  # noqa: E402
from concrete_evidence.infer import analyse  # noqa: E402

EXAMPLE_SCHEDULE = (ROOT / "live" / "schedule_example.json").read_text()


def load_model():
    path = os.environ.get("MODEL_PATH")
    repo = os.environ.get("MODEL_REPO")
    if not path and repo:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(repo, os.environ.get("MODEL_FILE", "best.onnx"))
    if not path:
        path = str(ROOT / "models" / "best.onnx")
    if not Path(path).exists():
        raise SystemExit(f"no model at {path}: set MODEL_PATH or MODEL_REPO")
    if path.endswith(".onnx"):
        from concrete_evidence.onnx_seg import OnnxSeg
        return OnnxSeg(path), Path(path).name
    from ultralytics import YOLO  # .pt: only where PyTorch is installed
    return YOLO(path), Path(path).name


def parse_rename(text: str) -> dict:
    return dict(kv.strip().split("=", 1) for kv in text.split(",") if "=" in kv)


privacy.fetch()  # face model (227 KB, MIT, checksum-pinned): every photo is blurred before anything else
MODEL, MODEL_NAME = load_model()
RENAME = parse_rename(os.environ.get("CLASS_RENAME", ""))
DEPTH = None
if os.environ.get("DEPTH_FILTER") == "1":
    from concrete_evidence.depth import DepthAnythingOnnx
    DEPTH = DepthAnythingOnnx()


def decode_image(image_b64: str) -> np.ndarray:
    if "," in image_b64[:100]:  # a "data:image/...;base64," prefix is allowed
        image_b64 = image_b64.split(",", 1)[1]
    img = cv2.imdecode(np.frombuffer(base64.b64decode(image_b64), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("not a JPEG or PNG image")
    return img


def run(img: np.ndarray, schedule_json: str, zone: str, face: str) -> dict:
    schedule = {**DEFAULTS, **json.loads(schedule_json or "{}")}
    if not schedule.get("bar_diameter_mm"):
        raise ValueError("the schedule needs bar_diameter_mm")
    out = analyse(img, schedule, MODEL, depth=DEPTH, zone=zone or None, face=face or None, rename=RENAME)
    ok, jpg = cv2.imencode(".jpg", out.pop("annotated"), [cv2.IMWRITE_JPEG_QUALITY, 85])
    out["annotated_jpg_base64"] = base64.b64encode(jpg.tobytes()).decode()
    out["model"] = {"weights": MODEL_NAME, "rename": RENAME, "depth_filter": DEPTH is not None}
    return out


# ---- For programs: base64 photo in, JSON out ---------------------------------
def predict(image_b64: str, schedule_json: str = "", zone: str = "end", face: str = "") -> dict:
    """Check one photo. image_b64: a base64 JPEG or PNG. schedule_json: the bar bending schedule
    (see live/schedule_example.json; empty = the example). zone: "end" or "middle". face: e.g. "A".
    Returns the check (faults, fixes, review status), detections with outlines, and the annotated photo."""
    try:
        return run(decode_image(image_b64), schedule_json or EXAMPLE_SCHEDULE, zone, face)
    except (ValueError, json.JSONDecodeError) as e:
        return {"error": str(e)}


# ---- For people: the web page --------------------------------------------------
def check_for_page(image, schedule_json, zone, face):
    if image is None:
        raise gr.Error("Upload a photo first.")
    try:
        out = run(cv2.cvtColor(image, cv2.COLOR_RGB2BGR), schedule_json, zone, face)
    except (ValueError, json.JSONDecodeError) as e:
        raise gr.Error(str(e)) from e
    jpg = cv2.imdecode(np.frombuffer(base64.b64decode(out.pop("annotated_jpg_base64")), np.uint8), cv2.IMREAD_COLOR)
    fixes = out["check"]["fixes"]
    text = "\n".join(f"- {f}" for f in fixes) or "- No faults found. A person still confirms before the pour."
    return cv2.cvtColor(jpg, cv2.COLOR_BGR2RGB), f"### To fix\n{text}", summary(out["check"]), out


with gr.Blocks(title="Concrete Evidence: rebar check") as demo:
    gr.Markdown("# Concrete Evidence: rebar check\nUpload a photo of one column face with the 4 markers in view. "
                f"Model: `{MODEL_NAME}`. Every result waits for a person to confirm it.")
    with gr.Row():
        with gr.Column():
            image_in = gr.Image(type="numpy", label="Photo")
            schedule_in = gr.Code(EXAMPLE_SCHEDULE, language="json", label="Bar bending schedule")
            with gr.Row():
                zone_in = gr.Dropdown(["end", "middle"], value="end", label="Column zone")
                face_in = gr.Textbox("A", label="Face")
            button = gr.Button("Check", variant="primary")
        with gr.Column():
            image_out = gr.Image(label="Outlines (red = named in a fault)")
            fixes_out = gr.Markdown()
            summary_out = gr.Textbox(label="All checks", lines=10)
            json_out = gr.JSON(label="Result")
    button.click(check_for_page, inputs=[image_in, schedule_in, zone_in, face_in],
                 outputs=[image_out, fixes_out, summary_out, json_out], api_visibility="private")
    gr.api(predict, api_name="predict")

if __name__ == "__main__":
    # Render sets PORT; locally it is 7860
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
