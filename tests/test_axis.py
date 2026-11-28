import math

import cv2
import numpy as np
import pytest

from concrete_evidence.axis import measure, tail_px
from concrete_evidence.capture import record
from concrete_evidence.check import run


def drawn(points, width=12):
    """The outline of a bar drawn along a polyline, as a mask polygon (what a segmentation model returns)."""
    img = np.zeros((1200, 1200), np.uint8)
    cv2.polylines(img, [np.array(points, np.int32)], False, 1, width)
    cs, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return max(cs, key=cv2.contourArea).reshape(-1, 2).tolist()


def hooked(angle, leg=400, tail=160, x=300, y=100):
    """A bar running down, then turning `angle` degrees into a tail."""
    t = math.radians(angle)
    return [[x, y], [x, y + leg], [x + tail * math.sin(t), y + leg + tail * math.cos(t)]]


def test_straight_bar_is_one_segment_with_its_length_and_thickness():
    m = measure([[100, 100], [116, 100], [116, 700], [100, 700]])
    assert m["bends_deg"] == [] and len(m["segments_px"]) == 1
    assert m["segments_px"][0] == pytest.approx(600, abs=3)
    assert m["thickness_px"] == pytest.approx(16, abs=2)


@pytest.mark.parametrize("angle", [90, 135])
def test_bend_angle_and_tail_are_measured(angle):
    m = measure(drawn(hooked(angle)))
    assert len(m["bends_deg"]) == 1 and m["bends_deg"][0] == pytest.approx(angle, abs=5)
    assert tail_px(m) == pytest.approx(160, abs=12)
    assert max(m["segments_px"]) == pytest.approx(400, abs=12)


def test_hook_check_uses_the_measured_tail_and_bend():
    sched = {"bar_diameter_mm": 16, "tie_diameter_mm": 8, "hook_angle": 135, "hook_tail_factor": 10}
    short = drawn(hooked(135, tail=50))
    flat = drawn(hooked(100, tail=160))
    dets = [record(1, "hook_135", 0.9, (0, 0, 1, 1), 1.0, short), record(2, "hook_135", 0.9, (0, 0, 1, 1), 1.0, flat)]
    r = run({"mm_per_px": 1.0, "detections": dets}, sched)
    fails = {(c["check"], tuple(c["track_ids"])) for c in r["checks"] if c["status"] == "fail"}
    assert ("hook_tail", (1,)) in fails  # 50 mm tail, needs 10 x 8 = 80 mm
    assert ("hook_angle", (2,)) in fails  # labelled 135 but bent about 100 degrees
    assert ("hook_tail", (2,)) not in fails


def lap_bar(tid, x, y0, y1, width=16):
    p = [[x - width / 2, y0], [x + width / 2, y0], [x + width / 2, y1], [x - width / 2, y1]]
    return record(tid, "bar", 0.9, (x - width / 2, y0, x + width / 2, y1), 1.0, p)


def test_short_lap_fails_and_long_lap_passes():
    sched = {"bar_diameter_mm": 16}  # no lap length in the schedule: Eurocode 2 floor max(15 x 16, 200) = 240 mm
    short = [lap_bar(1, 100, 100, 600), lap_bar(2, 120, 500, 1000)]   # 100 mm overlap, 20 mm apart
    long = [lap_bar(3, 400, 100, 600), lap_bar(4, 420, 300, 1000)]    # 300 mm overlap
    far = [lap_bar(5, 800, 100, 600), lap_bar(6, 950, 500, 1000)]     # 150 mm apart: not a lap
    r = run({"mm_per_px": 1.0, "detections": short + long + far}, sched)
    laps = {tuple(c["track_ids"]): (c["status"], c["measured"]) for c in r["checks"] if c["check"] == "lap_length"}
    assert laps[(1, 2)][0] == "fail" and laps[(1, 2)][1] == pytest.approx(100, abs=3)
    assert laps[(3, 4)][0] == "pass"
    assert (5, 6) not in laps
    assert any("splice bar" in f for f in r["fixes"])


def test_schedule_lap_length_wins_over_the_code_floor():
    r = run({"mm_per_px": 1.0, "detections": [lap_bar(1, 100, 100, 600), lap_bar(2, 120, 300, 1000)]},
            {"bar_diameter_mm": 16, "lap_length_mm": 640})  # 40 x diameter from the design
    lap = next(c for c in r["checks"] if c["check"] == "lap_length")
    assert lap["status"] == "fail" and lap["expected"] == 640


def test_lapped_pair_is_not_a_spacing_fault():
    dets = [lap_bar(1, 100, 100, 600), lap_bar(2, 120, 300, 1000), lap_bar(3, 270, 100, 1000)]
    r = run({"mm_per_px": 1.0, "detections": dets}, {"bar_diameter_mm": 16, "bar_spacing_mm": 150})
    assert [c["status"] for c in r["checks"] if c["check"] == "spacing"] == ["pass"]
    assert [tuple(c["track_ids"]) for c in r["checks"] if c["check"] == "lap_length"] == [(1, 2)]
