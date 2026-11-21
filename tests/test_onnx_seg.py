"""The ONNX runner on a tiny hand-made model: boxes, NMS, outlines, names (no torch, no weights)."""

import numpy as np
import pytest

from concrete_evidence.capture import records_from_result
from concrete_evidence.depth import dpt_size
from concrete_evidence.onnx_seg import OnnxSeg, letterbox, nms

onnx = pytest.importorskip("onnx")
pytest.importorskip("onnxruntime")
from onnx import TensorProto, helper, numpy_helper  # noqa: E402


def _model(path):
    """A 'YOLOv8-seg' whose outputs are constants: 3 candidates, 1 class, 32 prototypes.

    Candidate 0: a box x 100..300, y 180..220 (letterbox pixels), score 0.9, mask = prototype 0.
    Candidate 1: the same box 2 px lower, score 0.8 (NMS drops it). Candidate 2: score 0.1 (too low).
    Prototype 0 is +10 inside the box (in prototype pixels, 1/4 size) and -10 outside.
    """
    pred = np.zeros((1, 4 + 1 + 32, 3), np.float32)
    for k, (cy, s) in enumerate([(200, 0.9), (202, 0.8), (200, 0.1)]):
        pred[0, :5, k] = [200, cy, 200, 40, s]
        pred[0, 5, k] = 1.0
    protos = np.full((1, 32, 160, 160), 0, np.float32)
    protos[0, 0] = -10
    protos[0, 0, 45:55, 25:75] = 10
    nodes = [helper.make_node("Constant", [], ["output0"], value=numpy_helper.from_array(pred)),
             helper.make_node("Constant", [], ["output1"], value=numpy_helper.from_array(protos))]
    graph = helper.make_graph(
        nodes, "stand_in",
        [helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 640, 640])],
        [helper.make_tensor_value_info("output0", TensorProto.FLOAT, [1, 37, 3]),
         helper.make_tensor_value_info("output1", TensorProto.FLOAT, [1, 32, 160, 160])])
    m = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    m.ir_version = 9
    helper.set_model_props(m, {"names": "{0: 'bar'}", "task": "segment"})
    onnx.save(m, str(path))
    return path


def test_letterbox_pads_to_square():
    img, r, pad = letterbox(np.zeros((480, 640, 3), np.uint8))
    assert img.shape == (640, 640, 3) and r == 1.0 and pad == (0, 80)
    assert img[0, 0, 0] == 114 and img[100, 0, 0] == 0


def test_nms_keeps_the_best_of_overlapping_boxes():
    boxes = np.array([[0, 0, 10, 10], [1, 1, 11, 11], [50, 50, 60, 60]], np.float32)
    keep = nms(boxes, np.array([0.5, 0.9, 0.7]), np.array([0, 0, 0]), iou=0.5, max_det=10)
    assert keep.tolist() == [1, 2]
    other_class = nms(boxes, np.array([0.5, 0.9, 0.7]), np.array([1, 0, 0]), iou=0.5, max_det=10)
    assert sorted(other_class.tolist()) == [0, 1, 2]  # different classes never suppress each other


def test_onnx_runner_end_to_end(tmp_path):
    model = OnnxSeg(_model(tmp_path / "m.onnx"))
    result = model.predict(np.zeros((480, 640, 3), np.uint8), conf=0.25)[0]
    assert model.names == {0: "bar"}
    assert len(result.boxes) == 1  # the 0.8 duplicate is suppressed, the 0.1 one filtered
    np.testing.assert_allclose(result.boxes.xyxy.tolist()[0], [100, 100, 300, 140], atol=0.01)
    poly = result.masks.xy[0]
    assert abs(poly[:, 0].min() - 100) <= 3 and abs(poly[:, 0].max() - 300) <= 3
    assert abs(poly[:, 1].min() - 100) <= 3 and abs(poly[:, 1].max() - 140) <= 3

    recs = records_from_result(result, mm_per_px=0.5)
    assert recs[0]["class"] == "bar" and abs(recs[0]["length_px"] - 200) <= 4
    assert abs(recs[0]["length_mm"] - 100) <= 2 and recs[0]["polygon"]


def test_depth_input_size_matches_the_processor():
    assert dpt_size(1280, 960) == (686, 518)  # short side 518, both multiples of 14
    assert dpt_size(518, 518) == (518, 518)
    h, w = dpt_size(3000, 4000)
    assert h == 518 and w % 14 == 0
