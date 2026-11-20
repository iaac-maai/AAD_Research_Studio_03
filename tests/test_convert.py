import json

import numpy as np
import pytest
from PIL import Image

from concrete_evidence.convert import build, labelme_to_coco, polygon_line, seg_to_polygon


def test_rectangle_becomes_four_point_polygon():
    d = {"shapes": [{"label": "tie", "shape_type": "rectangle", "points": [[1, 2], [5, 8]]}],
         "imagePath": "a.png", "imageWidth": 10, "imageHeight": 10}
    coco = labelme_to_coco(d)
    assert coco["annotations"][0]["segmentation"] == [[1, 2, 5, 2, 5, 8, 1, 8]]
    assert coco["annotations"][0]["category_name"] == "tie"


def test_tiny_shapes_are_dropped():
    d = {"shapes": [{"label": "bar", "points": [[0, 0], [1, 1]]}]}
    assert labelme_to_coco(d)["annotations"] == []


def test_largest_polygon_wins():
    assert seg_to_polygon([[0, 0, 1, 0, 1, 1], [0, 0, 9, 0, 9, 9, 0, 9]], 10, 10) == [0, 0, 9, 0, 9, 9, 0, 9]
    assert seg_to_polygon([[0, 0]], 10, 10) is None


def test_polygon_line_normalises_and_clips():
    line = polygon_line(2, [0, 0, 100, 50, 150, -10], 100, 50)
    assert line == "2 0.000000 0.000000 1.000000 1.000000 1.000000 0.000000"


def labelme_folder(folder, n, label="bar"):
    folder.mkdir(parents=True)
    for k in range(n):
        Image.fromarray(np.zeros((40, 80, 3), np.uint8)).save(folder / f"img{k}.png")
        d = {"imagePath": f"img{k}.png", "imageWidth": 80, "imageHeight": 40,
             "shapes": [{"label": label, "points": [[0, 0], [40, 0], [40, 20]]},
                        {"label": "intersection", "shape_type": "rectangle", "points": [[10, 10], [20, 20]]}]}
        (folder / f"img{k}.json").write_text(json.dumps(d))
    return folder


def test_build_writes_yolo_layout(tmp_path):
    train = labelme_folder(tmp_path / "train", 3)
    val = labelme_folder(tmp_path / "val", 1)
    out = tmp_path / "yolo"
    yaml = build([train], [val], out).read_text()
    assert "names:\n  0: bar\n  1: intersection" in yaml
    labels = sorted((out / "labels" / "train").glob("*.txt"))
    assert len(labels) == 3 and len(list((out / "images" / "train").iterdir())) == 3
    lines = labels[0].read_text().splitlines()
    assert lines[0] == "0 0.000000 0.000000 0.500000 0.000000 0.500000 0.500000"
    assert lines[1].startswith("1 0.125000 0.250000")


def test_build_without_labels_fails(tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(ValueError):
        build([tmp_path / "empty"], [tmp_path / "empty"], tmp_path / "out")
