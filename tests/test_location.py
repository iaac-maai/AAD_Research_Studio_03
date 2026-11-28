import pytest

from concrete_evidence.check import run
from concrete_evidence.codes import column_ties
from concrete_evidence.location import es_seismic, find_city, rules_for
from tests.test_check import capture
from tests.test_ties import COLUMN, cage


def test_city_autocomplete_ignores_accents_and_puts_spain_first():
    assert find_city("malaga")[0]["name"] == "Málaga"
    valencias = find_city("Valencia")
    assert valencias[0]["country"] == "ES" and any(v["country"] == "VE" for v in valencias)
    assert find_city("") == []


def test_spanish_seismic_value_from_the_annex_grid():
    assert es_seismic(41.4, 2.1)["agR_g"] == 0.084  # a grid point of table AN.5, read off the PDF
    bcn = rules_for("Barcelona")
    assert bcn["country"] == "ES" and 0.07 < bcn["agR_g"] < 0.1 and bcn["ductility"] == "DCM"
    assert rules_for("Bilbao")["ductility"] == "none"  # under 0.04 g: very low seismicity, Eurocode 2 only


def test_engineer_choice_wins_and_unknowns_stay_strict():
    assert rules_for("Barcelona", ductility="DCH")["ductility"] == "DCH"
    assert rules_for("Berlin")["national_annex"] is None and rules_for("Berlin")["ductility"] == "DCM"
    assert rules_for("Nowhereville123")["agR_g"] is None


def test_spanish_middle_zone_is_stricter():
    eu = column_ties([400, 400], 30, 16, 8, 3000, "DCM")
    es = column_ties([400, 400], 30, 16, 8, 3000, "DCM", country="ES")
    assert eu["tie_spacing_max_mm"]["middle"] == 320 and es["tie_spacing_max_mm"]["middle"] == 240  # 15 x 16


def test_city_in_the_schedule_picks_the_rules():
    r = run(cage([150, 250, 350, 450]), {**COLUMN, "city": "Barcelona"})
    assert r["place"]["country"] == "ES" and r["code"]["tie_spacing_max_mm"]["middle"] == 240
    r = run(cage([150, 330]), {**COLUMN, "city": "Bilbao", "ductility": None,
                               "tie_spacing_mm": {"end": 180, "middle": 200}})
    assert r["code"]["code"] == "EC2"


@pytest.mark.parametrize("cls,length,faults", [("hook_90", 60, 1), ("hook_90", 80, 0), ("hook_135", 45, 1),
                                               ("hook_135", 55, 0)])
def test_eurocode_2_hook_tails_depend_on_the_bend(cls, length, faults):
    from concrete_evidence.capture import record
    h = record(30, cls, 0.8, (500, 50, 500 + length, 58), 1.0,
               [[500, 50], [500 + length, 50], [500 + length, 58], [500, 58]])
    sched = {"element": "C1", "bar_diameter_mm": 16, "tie_diameter_mm": 6, "column_mm": [400, 400],
             "ductility": "none", "hook_angle": int(cls.split("_")[1])}
    r = run(capture([h]), sched)
    assert len([c for c in r["checks"] if c["check"] == "hook_tail" and c["status"] == "fail"]) == faults


def test_defaults_merged_by_the_caller_dont_override_eurocode_2_tails():
    from concrete_evidence.capture import record
    from concrete_evidence.check import DEFAULTS
    h = record(30, "hook_135", 0.8, (500, 50, 555, 58), 1.0, [[500, 50], [555, 50], [555, 58], [500, 58]])
    sched = {**DEFAULTS, "element": "C1", "bar_diameter_mm": 16, "tie_diameter_mm": 6, "column_mm": [400, 400],
             "ductility": "none"}  # the model server merges DEFAULTS before calling the check
    r = run(capture([h]), sched)  # 55 mm tail on a 135 degree hook: enough under Eurocode 2 (50 mm)
    assert not [c for c in r["checks"] if c["check"] == "hook_tail" and c["status"] == "fail"]
