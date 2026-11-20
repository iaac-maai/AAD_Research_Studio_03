"""
Concrete Evidence - live rebar view.

Runs the segmentation model on a live feed (webcam, phone stream or video file),
keeps an ID on every detection between frames (tracking), finds the 4 ArUco
markers, and says when the frame is good enough to check: all 4 markers in view
and the camera held still. Press C (or use --auto) to save that frame with its
detections in mm for the checker.

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
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

ARUCO_DICT = cv2.aruco.DICT_4X4_50
MARKER_IDS = (0, 1, 2, 3)


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default="yolov8n-seg.pt", help="trained weights (best.pt)")
    p.add_argument("--source", default="0", help="0 = webcam, or a video file / stream URL")
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--conf", type=float, default=0.4)
    p.add_argument("--device", default=None, help="cpu, 0 (GPU) ... default: auto")
    p.add_argument("--marker-mm", type=float, default=100.0, help="printed marker width in mm")
    p.add_argument("--still-frames", type=int, default=8, help="frames the camera must be still")
    p.add_argument("--still-thresh", type=float, default=2.5, help="mean pixel change counted as still")
    p.add_argument("--auto", action="store_true", help="capture automatically when ready")
    p.add_argument("--captures", default="live/captures", help="where captured frames go")
    p.add_argument("--no-show", action="store_true", help="no window (for tests / servers)")
    p.add_argument("--out", default=None, help="also write the annotated video here (.mp4)")
    p.add_argument("--max-frames", type=int, default=0, help="stop after N frames (0 = no limit)")
    return p.parse_args()


class Markers:
    """Finds the ArUco markers and turns their size into a mm-per-pixel scale."""

    def __init__(self, marker_mm):
        self.marker_mm = marker_mm
        params = cv2.aruco.DetectorParameters()
        self.det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(ARUCO_DICT), params)

    def find(self, frame):
        corners, ids, _ = self.det.detectMarkers(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        found = {}
        if ids is not None:
            for c, i in zip(corners, ids.flatten()):
                if int(i) in MARKER_IDS:
                    found[int(i)] = c.reshape(4, 2)
        return found

    def mm_per_px(self, found):
        """Average of the 4 side lengths of every marker seen. Good when the view is near top-down."""
        if not found:
            return None
        sides = [np.linalg.norm(c[k] - c[(k + 1) % 4]) for c in found.values() for k in range(4)]
        return self.marker_mm / float(np.mean(sides))

    @staticmethod
    def draw(frame, found):
        for i, c in found.items():
            pts = c.astype(int)
            cv2.polylines(frame, [pts], True, (0, 200, 255), 2)
            cv2.putText(frame, f"M{i}", tuple(pts[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)


class Stillness:
    """Says when the camera has been held still for a few frames."""

    def __init__(self, n, thresh):
        self.n, self.thresh, self.prev, self.count = n, thresh, None, 0

    def update(self, frame):
        g = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (160, 120))
        diff = None if self.prev is None else float(np.mean(cv2.absdiff(g, self.prev)))
        self.prev = g
        self.count = self.count + 1 if (diff is not None and diff < self.thresh) else 0
        return self.count >= self.n, diff


def detections(result, mm_per_px):
    """One dict per tracked object: id, class, confidence, centre and size (px and mm)."""
    out = []
    if result.boxes is None or len(result.boxes) == 0:
        return out
    names = result.names
    ids = result.boxes.id.int().tolist() if result.boxes.id is not None else [None] * len(result.boxes)
    for k, (box, cls, conf) in enumerate(zip(result.boxes.xyxy.tolist(), result.boxes.cls.int().tolist(),
                                             result.boxes.conf.tolist())):
        x1, y1, x2, y2 = box
        d = {"track_id": ids[k], "class": names[cls], "conf": round(conf, 3),
             "centre_px": [round((x1 + x2) / 2, 1), round((y1 + y2) / 2, 1)],
             "size_px": [round(x2 - x1, 1), round(y2 - y1, 1)]}
        if mm_per_px:
            d["centre_mm"] = [round(v * mm_per_px, 1) for v in d["centre_px"]]
            d["size_mm"] = [round(v * mm_per_px, 1) for v in d["size_px"]]
        out.append(d)
    return out


def status_bar(frame, lines, ready):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 34), (30, 30, 30), -1)
    cv2.putText(frame, "   ".join(lines), (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (240, 240, 240), 1, cv2.LINE_AA)
    if ready:
        cv2.rectangle(frame, (0, h - 40), (w, h), (60, 160, 60), -1)
        cv2.putText(frame, "READY TO CHECK - press C", (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 255, 255), 2, cv2.LINE_AA)


def capture(folder, raw, annotated, dets, mm_per_px, found):
    folder.mkdir(parents=True, exist_ok=True)
    stem = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    cv2.imwrite(str(folder / f"{stem}.jpg"), raw)
    cv2.imwrite(str(folder / f"{stem}_annotated.jpg"), annotated)
    counts = {}
    for d in dets:
        counts[d["class"]] = counts.get(d["class"], 0) + 1
    rec = {"time": datetime.now().isoformat(timespec="seconds"), "mm_per_px": mm_per_px,
           "markers_seen": sorted(found), "counts": counts, "detections": dets}
    (folder / f"{stem}.json").write_text(json.dumps(rec, indent=2))
    print(f"[capture] {stem}: {counts}, scale {mm_per_px and round(mm_per_px, 3)} mm/px")
    return stem


def main():
    a = parse_args()
    model = YOLO(a.model)
    src = int(a.source) if a.source.isdigit() else a.source
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise SystemExit(f"Could not open source {a.source!r}")

    markers, still = Markers(a.marker_mm), Stillness(a.still_frames, a.still_thresh)
    writer, n, t_prev, fps, last_auto = None, 0, time.time(), 0.0, 0.0
    captures = Path(a.captures)
    summary = {"frames": 0, "ready_frames": 0, "captures": [], "max_objects": 0}

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        n += 1
        result = model.track(frame, persist=True, imgsz=a.imgsz, conf=a.conf, device=a.device,
                             tracker="bytetrack.yaml", verbose=False, retina_masks=False,
                             max_det=500)[0]  # dense cages: SORD frames hold up to ~430 objects
        found = markers.find(frame)
        scale = markers.mm_per_px(found)
        is_still, _ = still.update(frame)
        ready = len(found) == len(MARKER_IDS) and is_still

        view = result.plot(boxes=True, labels=True, conf=False, line_width=1)
        Markers.draw(view, found)
        now = time.time()
        fps = 0.9 * fps + 0.1 * (1.0 / max(now - t_prev, 1e-6)) if n > 1 else 0.0
        t_prev = now
        dets = detections(result, scale)
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
            summary["captures"].append(capture(captures, frame, view, dets, scale, found))
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
