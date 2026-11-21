import json
import zipfile

import numpy as np
import pytest
from PIL import Image

from concrete_evidence import conrebseg as crs


def test_mask_round_trip():
    m = np.zeros((30, 8), np.uint8)
    m[2:28, 2:6] = 1
    assert np.array_equal(crs.decode_mask(crs.encode_mask(m)), m)


def det(label, box, mask):
    mask_doc = {"$binary": {"base64": crs.encode_mask(mask), "subType": "00"}}
    return {"label": label, "bounding_box": box, "mask": mask_doc}


def test_polygon_is_placed_in_image_pixels():
    mask = np.zeros((40, 10), np.uint8)
    mask[:, 3:7] = 1  # a 4 px wide vertical bar
    poly = crs.det_polygon(det("ExposedBars", [0.5, 0.25, 0.1, 0.4], mask), 100, 100)
    xs, ys = poly[0::2], poly[1::2]
    assert min(xs) == pytest.approx(53) and max(xs) == pytest.approx(56)
    assert min(ys) == pytest.approx(25) and max(ys) == pytest.approx(64)


def test_tiny_masks_are_skipped():
    mask = np.zeros((5, 5), np.uint8)
    mask[2, 2] = 1
    assert crs.det_polygon(det("ExposedBars", [0, 0, 0.05, 0.05], mask), 100, 100) is None


@pytest.fixture
def dataset(tmp_path):
    """A tiny ConRebSeg: 2 site images (train, val), 1 YouTube image, inside a zip."""
    root = tmp_path / "conrebseg"
    root.mkdir()
    bar = np.zeros((40, 10), np.uint8)
    bar[:, 3:7] = 1
    person = np.ones((20, 10), np.uint8)
    samples = []
    zpath = root / "ConRebSeg.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        for fp, split in [("data/langebro/run_1/a.jpg", "train"), ("data/vester_sogade/run_2/b.jpg", "val"),
                          ("data/youtube/xyz/frame_0001.jpg", "train")]:
            img = tmp_path / "img.jpg"
            Image.fromarray(np.zeros((100, 100, 3), np.uint8)).save(img)
            zf.write(img, fp.replace("data/", "ConRebSeg/", 1))  # the real zip's layout differs from the index
            samples.append({"filepath": fp, "tags": [split], "metadata": {"width": 100, "height": 100},
                            "gt_annotations": {"detections": [det("ExposedBars", [0.5, 0.25, 0.1, 0.4], bar),
                                                              det("person", [0.1, 0.1, 0.1, 0.2], person)]}})
    (root / "samples.json").write_text(json.dumps({"samples": samples}))
    return root


def test_zip_names_map_to_index_paths():
    assert crs.zip_to_filepath("ConRebSeg/langebro/run_1/a.jpg") == "data/langebro/run_1/a.jpg"
    assert crs.zip_to_filepath("ConRebSeg/vester_sogade/r/b.jpg") == "data/vester_sogade/r/b.jpg"
    assert crs.zip_to_filepath("ConRebSeg/README.txt") is None
    assert crs.zip_to_filepath("ConRebSeg/youtube/x/f.jpg") is None


def test_extract_skips_youtube(dataset):
    assert crs.extract(dataset / "ConRebSeg.zip", dataset) == 2
    assert (dataset / "data/langebro/run_1/a.jpg").exists()
    assert not (dataset / "data/youtube").exists()


def test_convert_keeps_only_rebar_patches(dataset, tmp_path):
    crs.extract(dataset / "ConRebSeg.zip", dataset)
    out = tmp_path / "yolo"
    stats = crs.convert(dataset, out)
    assert stats["images_train"] == 1 and stats["images_val"] == 1 and stats["instances"] == 2
    assert stats["dropped_person"] == 2
    label = (out / "labels/train/langebro__run_1__a.txt").read_text().splitlines()
    assert len(label) == 1 and label[0].startswith("0 ")
    assert "names:\n  0: exposed_rebar" in (out / "data.yaml").read_text()  # patches, never `bar`


def test_limit_per_split(dataset, tmp_path):
    crs.extract(dataset / "ConRebSeg.zip", dataset)
    stats = crs.convert(dataset, tmp_path / "yolo", limit=0)
    assert stats["images_train"] == 1  # limit=0 means no limit
