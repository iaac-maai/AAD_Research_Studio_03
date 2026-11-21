"""
Concrete Evidence - live rebar view.

Runs the segmentation model on a live feed (webcam, phone stream or video file),
keeps an ID on every detection between frames (tracking), finds the 4 ArUco
markers, and says when the frame is good enough to check: all 4 markers in view
and the camera held still. Press C (or use --auto) to save that frame with its
detections in mm for the checker. Faces are blurred in everything saved.

    python live/live.py                                   # laptop webcam
    python live/live.py --source http://PHONE_IP:8080/video   # phone camera app stream
    python live/live.py --source cage_walk.mp4 --model runs/.../best.pt
    python live/live.py --source test.mp4 --no-show --out live_out.mp4   # headless

Keys: C = capture this frame, Q or Esc = quit.

Markers: ArUco DICT_4X4_50, ids 0-3, printed 100 mm wide (live/make_markers.py),
placed just outside the corners of the mat or cage, as in rebar_check_ar.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from concrete_evidence.capture import Stillness, counts, records_from_result  # noqa: E402
from concrete_evidence.markers import DEFAULT_MARKER_MM, MARKER_IDS, MarkerDetector  # noqa: E402
from concrete_evidence.privacy import blur_faces  # noqa: E402


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default="yolov8n-seg.pt", help="trained weights (best.pt)")
    p.add_argument("--source", default="0", help="0 = webcam, or a video file / stream URL")
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--conf", type=float, default=0.4)
    p.add_argument("--device", default=None, help="cpu, 0 (GPU) ... default: auto")
    p.add_argument("--marker-mm", type=float, default=DEFAULT_MARKER_MM, help="printed marker width in mm")
    p.add_argument("--still-frames", type=int, default=8, help="frames the camera must be still")
    p.add_argument("--still-thresh", type=float, default=2.5, help="mean pixel change counted as still")
    p.add_argument("--auto", action="store_true", help="capture automatically when ready")
    p.add_argument("--captures", default="live/captures", help="where captured frames go")
    p.add_argument("--no-show", action="store_true", help="no window (for tests / servers)")
    p.add_argument("--out", default=None, help="also write the annotated video here (.mp4)")
    p.add_argument("--max-frames", type=int, default=0, help="stop after N frames (0 = no limit)")
    p.add_argument("--depth-filter", action="store_true",
                   help="Depth Anything before YOLO: grey out the far background (train on filtered photos too)")
    return p.parse_args()


def status_bar(frame, lines, ready):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 34), (30, 30, 30), -1)
    cv2.putText(frame, "   ".join(lines), (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (240, 240, 240), 1, cv2.LINE_AA)
    if ready:
        cv2.rectangle(frame, (0, h - 40), (w, h), (60, 160, 60), -1)
        cv2.putText(frame, "READY TO CHECK - press C", (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 255, 255), 2, cv2.LINE_AA)


def save_capture(folder, raw, annotated, dets, mm_per_px, found):
    """Save the frame (faces blurred), the annotated view and a JSON of detections."""
    folder.mkdir(parents=True, exist_ok=True)
    stem = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    raw, n_faces = blur_faces(raw)
    annotated, _ = blur_faces(annotated)
    cv2.imwrite(str(folder / f"{stem}.jpg"), raw)
    cv2.imwrite(str(folder / f"{stem}_annotated.jpg"), annotated)
    rec = {"time": datetime.now().isoformat(timespec="seconds"), "mm_per_px": mm_per_px,
           "markers_seen": sorted(found), "faces_blurred": n_faces, "counts": counts(dets), "detections": dets}
    (folder / f"{stem}.json").write_text(json.dumps(rec, indent=2))
    print(f"[capture] {stem}: {rec['counts']}, scale {mm_per_px and round(mm_per_px, 3)} mm/px")
    return stem


def main():
    a = parse_args()
    from ultralytics import YOLO  # heavy; only needed when the live view runs

    model = YOLO(a.model)
    depth = None
    if a.depth_filter:
        from concrete_evidence.depth import DepthAnything, filter_image
        depth = DepthAnything(device=a.device)
    src = int(a.source) if a.source.isdigit() else a.source
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise SystemExit(f"Could not open source {a.source!r}")

    markers, still = MarkerDetector(a.marker_mm), Stillness(a.still_frames, a.still_thresh)
    writer, n, t_prev, fps, last_auto = None, 0, time.time(), 0.0, 0.0
    captures = Path(a.captures)
    summary = {"frames": 0, "ready_frames": 0, "captures": [], "max_objects": 0}

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        n += 1
        seen = filter_image(frame, depth(frame))["image"] if depth else frame
        result = model.track(seen, persist=True, imgsz=a.imgsz, conf=a.conf, device=a.device,
                             tracker="bytetrack.yaml", verbose=False, retina_masks=False,
                             max_det=500)[0]  # dense cages: SORD frames hold up to ~430 objects
        found = markers.find(frame)
        scale = markers.mm_per_px(found)
        is_still, _ = still.update(frame)
        ready = len(found) == len(MARKER_IDS) and is_still

        view = result.plot(boxes=True, labels=True, conf=False, line_width=1)
        MarkerDetector.draw(view, found)
        now = time.time()
        fps = 0.9 * fps + 0.1 * (1.0 / max(now - t_prev, 1e-6)) if n > 1 else 0.0
        t_prev = now
        dets = records_from_result(result, scale)
        status_bar(view, [f"{fps:4.1f} fps", f"objects {len(dets)}", f"markers {len(found)}/4",
                          "still" if is_still else "moving",
                          f"{scale:.3f} mm/px" if scale else "no scale"], ready)

        summary["frames"] = n
        summary["ready_frames"] += int(ready)
        summary["max_objects"] = max(summary["max_objects"], len(dets))

        key = -1
        if not a.no_show:
            cv2.imshow("Concrete Evidence - live", view)
            key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if (key == ord("c") and ready) or (a.auto and ready and now - last_auto > 3.0):
            summary["captures"].append(save_capture(captures, frame, view, dets, scale, found))
            last_auto = now

        if a.out:
            if writer is None:
                h, w = view.shape[:2]
                fps_in = cap.get(cv2.CAP_PROP_FPS) or 15
                writer = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*"mp4v"), fps_in, (w, h))
            writer.write(view)
        if a.max_frames and n >= a.max_frames:
            break

    cap.release()
    if writer:
        writer.release()
    cv2.destroyAllWindows()
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
