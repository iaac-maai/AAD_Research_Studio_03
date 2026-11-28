import pytest

from concrete_evidence.capture import record
from concrete_evidence.check import run, summary
from concrete_evidence.codes import column_ties
from tests.test_check import bar

COLUMN = {"element": "C1", "column_mm": [400, 400], "cover_mm": 30, "clear_height_mm": 3000, "ductility": "DCM",
          "bar_diameter_mm": 16, "bar_count": 4, "bar_spacing_mm": 150, "tie_diameter_mm": 8,
          "tie_spacing_mm": {"end": 100, "middle": 200}, "spacing_tol_mm": 10, "hook_angle": 135}


def tie(tid, y, x0=50, length=520, width=8):
    """A horizontal tie across vertical bars, at height y (px)."""
    p = [[x0, y - width / 2], [x0 + length, y - width / 2], [x0 + length, y + width / 2], [x0, y + width / 2]]
    return record(tid, "tie", 0.9, (x0, y - width / 2, x0 + length, y + width / 2), 1.0, p)


def cage(tie_ys):
    bars = [bar(i, 100 + 150 * i) for i in range(4)]  # vertical, 600 px long from y=100
    return {"mm_per_px": 1.0, "detections": bars + [tie(20 + k, y) for k, y in enumerate(tie_ys)]}


def checks(result, name):
    return [c for c in result["checks"] if c["check"] == name]


def test_ec8_dcm_limits_for_a_400_column():
    lim = column_ties([400, 400], 30, 16, 8, 3000)
    # core 400 - 2x30 - 8 = 332; end zone min(166, 175, 8x16=128); middle min(20x16=320, 400, 400)
    assert lim["core_mm"] == 332 and lim["tie_spacing_max_mm"] == {"end": 128, "middle": 320}
    assert lim["critical_length_mm"] == 500 and lim["hook_tail_min_mm"] == 80 and lim["verify"] is True


def test_dch_is_stricter_and_bad_input_is_refused():
    assert column_ties([400, 400], 30, 16, 8, ductility="DCH")["tie_spacing_max_mm"]["end"] == 96  # 6 x 16
    with pytest.raises(ValueError):
        column_ties([400, 400], 30, 16, 8, ductility="low")
    with pytest.raises(ValueError):
        column_ties([50, 50], 30, 16, 8)


def test_ties_as_scheduled_pass():
    r = run(cage([150, 250, 350, 450]), COLUMN)
    assert r["faults"] == 0, summary(r)
    assert [c["status"] for c in checks(r, "tie_spacing")] == ["pass"]
    assert r["fixes"] == [] and r["zone"] == "end"


def test_a_missing_tie_gets_a_fix_instruction():
    r = run(cage([150, 250, 480, 580]), COLUMN, face="A")  # 230 mm gap in the end zone (max 100)
    fault = checks(r, "tie_spacing")
    assert len(fault) == 1 and fault[0]["measured"] == pytest.approx(230) and fault[0]["track_ids"] == [21, 22]
    assert fault[0]["from_mm"] == pytest.approx(100) and fault[0]["to_mm"] == pytest.approx(330)
    assert r["fixes"] == ["Add 2 ties 100–330 mm below the top tie (gap 230 mm, max 100 mm here)."]


def test_same_gap_is_fine_in_the_middle_zone():
    r = run(cage([150, 250, 430]), COLUMN, zone="middle")  # 180 mm, middle allows 200
    assert [c["status"] for c in checks(r, "tie_spacing")] == ["pass"]


def test_code_caps_a_loose_schedule():
    loose = {**COLUMN, "tie_spacing_mm": {"end": 200, "middle": 200}}
    r = run(cage([150, 300]), loose)  # 150 mm gap: inside the schedule, over the code's 128
    sched = checks(r, "schedule_vs_code")
    assert len(sched) == 1 and sched[0]["expected"] == 128
    assert checks(r, "tie_spacing")[0]["status"] == "fail"
    assert "Ask the engineer: the drawing has ties every 200 mm, the code allows 128 mm max." in r["fixes"]


def test_zone_from_capture_and_bad_zone():
    cap = {**cage([150, 250]), "zone": "middle"}
    assert run(cap, COLUMN)["zone"] == "middle"
    with pytest.raises(ValueError):
        run(cap, COLUMN, zone="top")


def test_one_tie_is_unknown_not_a_pass():
    r = run(cage([150]), COLUMN)
    assert [c["status"] for c in checks(r, "tie_spacing")] == ["unknown"]


def test_hook_fixes_read_plainly():
    h = record(30, "hook_90", 0.8, (500, 50, 600, 58), 1.0, [[500, 50], [600, 50], [600, 58], [500, 58]])
    cap = cage([150, 250])
    cap["detections"].append(h)
    r = run(cap, COLUMN, face="north")
    assert "Rebend hook 30 to 135° (now 90°; 90° hooks open in earthquakes)." in r["fixes"]


def test_dch_critical_length_and_short_columns():
    dch = column_ties([400, 400], 30, 16, 8, 3000, ductility="DCH")
    assert dch["critical_length_mm"] == 600  # max(1.5 x 400, 3000 / 6, 600)
    assert dch["tie_diameter_min_mm"] == 6.4 and dch["engaged_bar_spacing_max_mm"] == 150
    short = column_ties([400, 400], 30, 16, 8, 1000)  # 1000 / 400 < 3: all of it is critical
    assert short["whole_column_critical"] and short["tie_spacing_max_mm"] == {"end": 128, "middle": 128}
    assert short["critical_length_mm"] == 1000


def test_eurocode_2_only_for_non_seismic_sites():
    lim = column_ties([400, 400], 30, 16, 8, 3000, ductility="none")
    # middle min(20 x 16, 400, 400) = 320; ends 0.6 x 320 = 192 over the larger column side
    assert lim["code"] == "EC2" and lim["tie_spacing_max_mm"] == {"end": 192, "middle": 320}
    assert lim["critical_length_mm"] == 400 and lim["hook_angle"] is None
    assert column_ties([400, 400], 30, 16, 8, ductility="DCL")["code"] == "EC2"
    plain = {**COLUMN, "ductility": "none", "hook_angle": 90, "tie_spacing_mm": {"end": 180, "middle": 300}}
    h = record(30, "hook_90", 0.8, (500, 50, 600, 58), 1.0, [[500, 50], [600, 50], [600, 58], [500, 58]])
    cap = cage([150, 330])
    cap["detections"].append(h)
    r = run(cap, plain)  # 180 mm end-zone gap and a 90 degree hook: both fine under Eurocode 2
    assert r["faults"] == 0, summary(r)


def test_too_thin_ties_are_a_design_question():
    r = run(cage([150, 250]), {**COLUMN, "bar_diameter_mm": 32, "tie_diameter_mm": 6})
    sched = [c for c in checks(r, "schedule_vs_code") if "ties" in c["detail"]]
    assert sched and sched[0]["expected"] == 8  # max(6, 32 / 4)
