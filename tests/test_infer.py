"""The one-photo check with a stand-in for the YOLO model (no torch needed)."""

import numpy as np

from concrete_evidence.infer import RED, analyse
from tests.test_ties import COLUMN


class _T(list):
    """Just enough of a torch tensor: .int() and .tolist()."""

    def int(self):
        return _T(int(v) for v in self)

    def tolist(self):
        return list(self)


class _Boxes:
    def __init__(self, boxes, cls, conf):
        self.xyxy, self.cls, self.conf, self.id = _T(boxes), _T(cls), _T(conf), None

    def __len__(self):
        return len(self.xyxy)


class _Masks:
    def __init__(self, polys):
        self.xy = [np.asarray(p, dtype=np.float32) for p in polys]


class _Result:
    names = {0: "bar", 1: "tie", 2: "hook_90", 3: "hook_135"}

    def __init__(self, polys, cls):
        boxes = [[min(x for x, _ in p), min(y for _, y in p), max(x for x, _ in p), max(y for _, y in p)]
                 for p in polys]
        self.boxes, self.masks = _Boxes(boxes, cls, [0.9] * len(cls)), _Masks(polys)


class StandIn:
    """Returns a fixed column face: 4 vertical bars 150 px apart, ties at the given heights."""

    def __init__(self, tie_ys):
        self.tie_ys = tie_ys
        self.seen = None

    def predict(self, image, **kw):
        self.seen = image
        bars = [[[x - 8, 100], [x + 8, 100], [x + 8, 700], [x - 8, 700]] for x in (100, 250, 400, 550)]
        ties = [[[50, y - 4], [570, y - 4], [570, y + 4], [50, y + 4]] for y in self.tie_ys]
        return [_Result(bars + ties, [0] * 4 + [1] * len(ties))]


def photo():
    return np.full((800, 700, 3), 180, np.uint8)


def test_one_photo_end_to_end_without_markers_uses_bar_width():
    out = analyse(photo(), COLUMN, StandIn([150, 250, 480, 580]), face="A", blur=False)
    chk = out["check"]
    assert chk["scale"]["source"] == "diameter" and out["counts"] == {"bar": 4, "tie": 4}
    tie = [c for c in chk["checks"] if c["check"] == "tie_spacing"]
    assert tie[0]["status"] == "fail" and tie[0]["track_ids"] == [6, 7]  # pieces numbered 1..8
    assert chk["fixes"][0].startswith("Add")
    assert out["annotated"].shape == (800, 700, 3)
    assert (out["annotated"] == RED).all(axis=-1).any()  # the faulty ties are drawn red
    assert all(len(d["polygon"]) == 4 for d in out["detections"])


def test_depth_filter_runs_before_the_model():
    model = StandIn([150, 250])
    near = np.zeros((800, 700), np.float32)
    near[100:700, 50:600] = 1.0
    out = analyse(photo(), COLUMN, model, depth=lambda _: near, blur=False)
    assert out["depth"]["kept"] < 1
    assert (model.seen[10, 10] == 114).all()  # the model got the greyed photo
