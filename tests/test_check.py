import json

import pytest

from concrete_evidence.capture import record, shape
from concrete_evidence.check import load_schedule, run, scale, summary
from tests.conftest import ROOT

SCHEDULE = {"element": "C1", "bar_diameter_mm": 16, "bar_count": 4, "bar_spacing_mm": 150,
            "spacing_tol_mm": 10, "diameter_tol_mm": 4, "tie_diameter_mm": 8, "hook_angle": 135, "hook_tail_factor": 10}


def bar_poly(x, width=16, length=600, y0=100):
    """A vertical bar outline at x (px), as a mask polygon."""
    return [[x - width / 2, y0], [x + width / 2, y0], [x + width / 2, y0 + length], [x - width / 2, y0 + length]]


def bar(tid, x, mm_per_px=1.0, width=16):
    p = bar_poly(x, width)
    xs, ys = [q[0] for q in p], [q[1] for q in p]
    return record(tid, "bar", 0.9, (min(xs), min(ys), max(xs), max(ys)), mm_per_px, p)


def hook(tid, cls="hook_135", length=100):
    p = [[500, 50], [500 + length, 50], [500 + length, 58], [500, 58]]
    return record(tid, cls, 0.8, (500, 50, 500 + length, 58), 1.0, p)


def capture(dets, mm_per_px=1.0):
    return {"mm_per_px": mm_per_px, "detections": dets}


def statuses(result, name):
    return [c["status"] for c in result["checks"] if c["check"] == name]


def test_shape_finds_length_width_and_direction():
    s = shape(bar_poly(100))
    assert s["length_px"] == pytest.approx(600) and s["width_px"] == pytest.approx(16)
    assert min(abs(s["angle_deg"] - 90), abs(s["angle_deg"] - 270)) < 1  # vertical bar


def test_cage_as_scheduled_has_no_faults():
    dets = [bar(i, 100 + 150 * i) for i in range(4)] + [hook(9)]
    r = run(capture(dets), SCHEDULE)
    assert r["faults"] == 0, summary(r)
    assert r["review"]["status"] == "pending"  # never approved without a person
    assert statuses(r, "spacing") == ["pass"] and statuses(r, "bar_count") == ["pass"]


def test_missing_bar_shows_in_count_and_spacing():
    dets = [bar(0, 100), bar(1, 250), bar(3, 550)]  # bar 2 at x=400 is missing
    r = run(capture(dets), SCHEDULE)
    assert statuses(r, "bar_count") == ["fail"]
    gaps = [c for c in r["checks"] if c["check"] == "spacing"]
    assert len(gaps) == 1 and gaps[0]["measured"] == pytest.approx(300) and gaps[0]["track_ids"] == [1, 3]
    assert "missing or shifted" in gaps[0]["detail"]


def test_shifted_bar_is_a_spacing_fault():
    dets = [bar(0, 100), bar(1, 280), bar(2, 400), bar(3, 550)]  # bar 1 is 30 mm off
    r = run(capture(dets), SCHEDULE)
    assert [c["track_ids"] for c in r["checks"] if c["status"] == "fail"] == [[0, 1], [1, 2]]


def test_wrong_bar_size():
    dets = [bar(0, 100), bar(1, 250, width=10), bar(2, 400), bar(3, 550)]
    r = run(capture(dets), SCHEDULE)
    fails = [c for c in r["checks"] if c["check"] == "bar_size" and c["status"] == "fail"]
    assert [c["track_ids"] for c in fails] == [[1]]


def test_90_degree_hook_and_short_tail():
    dets = [bar(i, 100 + 150 * i) for i in range(4)] + [hook(8, "hook_90"), hook(9, length=40)]
    r = run(capture(dets), SCHEDULE)
    assert {c["check"] for c in r["checks"] if c["status"] == "fail"} == {"hook_angle", "hook_tail"}
    tail = next(c for c in r["checks"] if c["check"] == "hook_tail")
    assert tail["expected"] == 80 and tail["track_ids"] == [9]  # 10 x 8 mm tie


def test_scale_from_bar_diameter_without_markers():
    dets = [bar(i, 100 + 75 * i, mm_per_px=None, width=8) for i in range(4)]  # 16 mm bars drawn 8 px wide
    mm, source = scale({"mm_per_px": None, "detections": dets}, SCHEDULE)
    assert source == "diameter" and mm == pytest.approx(2.0)
    r = run({"mm_per_px": None, "detections": dets}, SCHEDULE)
    assert statuses(r, "bar_size") == ["unknown"]  # can't check size with size as the scale
    assert statuses(r, "spacing") == ["pass"]  # 75 px x 2 mm/px = 150 mm


def test_nothing_to_measure():
    r = run({"detections": [{"class": "tie", "track_id": 1}]}, SCHEDULE)
    assert r["scale"]["source"] == "none" and r["checks"][0]["status"] == "unknown"


def test_example_schedule_loads_and_needs_diameter(tmp_path):
    s = load_schedule(ROOT / "live" / "schedule_example.json")
    assert s["bar_diameter_mm"] == 16 and s["hook_angle"] == 135
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"bar_count": 4}))
    with pytest.raises(ValueError):
        load_schedule(bad)


def test_one_shifted_bar_gives_one_fix():
    from concrete_evidence.check import run
    sched = {"element": "C1", "bar_diameter_mm": 16, "bar_count": 3, "bar_spacing_mm": 88, "spacing_tol_mm": 10}
    r = run(capture([bar(0, 100), bar(1, 223), bar(2, 276)]), sched, face="C")  # middle bar 35 mm off
    assert len([c for c in r["checks"] if c["check"] == "spacing"]) == 2
    assert r["fixes"] == ["Move bar 1 35 mm towards bar 0 (gaps 123 and 53 mm, should be 88 mm)."]


def test_a_missing_bar_is_not_read_as_shifted():
    from concrete_evidence.check import run
    sched = {"element": "C1", "bar_diameter_mm": 16, "bar_count": 4, "bar_spacing_mm": 100, "spacing_tol_mm": 10}
    r = run(capture([bar(0, 100), bar(1, 200), bar(2, 400)]), sched)  # 200 mm gap: bar missing
    assert "Add a bar between bars 1 and 2 (gap 200 mm, should be 100 mm)." in r["fixes"]


def test_small_bar_deviations_are_not_faults():
    from concrete_evidence.check import run
    sched = {"element": "C1", "bar_diameter_mm": 16, "bar_count": 3, "bar_spacing_mm": 100}  # default tolerances
    r = run(capture([bar(0, 100), bar(1, 215), bar(2, 300)]), sched)  # middle bar 15 mm off: camera noise level
    assert r["faults"] == 0
    r = run(capture([bar(0, 100), bar(1, 240), bar(2, 300)]), sched)  # 40 mm off: clearly out of place
    assert r["fixes"] == ["Move bar 1 40 mm towards bar 0 (gaps 140 and 60 mm, should be 100 mm)."]


def test_example_schedules_only_use_fields_the_schema_knows():
    root = ROOT / "live"
    known = set(json.loads((root / "schedule.schema.json").read_text())["properties"])
    for name in ("schedule_example.json", "schedule_mockup.json"):
        assert set(json.loads((root / name).read_text())) <= known, name
