"""The depth filter without the model: a stand-in gives the nearness."""

import json

import cv2
import numpy as np

from concrete_evidence import depth as dp


def scene(h=120, w=160):
    """A far background (nearness 0.1) with a near cage block (0.9) and a middle block (0.5)."""
    near = np.full((h, w), 0.1, np.float32)
    near[20:100, 20:70] = 0.9
    near[20:100, 90:140] = 0.5
    img = np.full((h, w, 3), 200, np.uint8)
    return img, near


def test_normalise_spreads_to_0_1_and_handles_flat():
    d = dp.normalise(np.linspace(5, 10, 1000).reshape(20, 50))
    assert d.min() == 0 and d.max() == 1
    assert not dp.normalise(np.ones((4, 4))).any()


def test_near_mask_keeps_the_near_block_plus_margin():
    _, near = scene()
    mask, t = dp.near_mask(near, threshold=0.7, margin_px=5)
    assert mask[60, 45] == 1 and mask[60, 115] == 0 and mask[5, 5] == 0
    assert mask[60, 17] == 1  # 3 px outside the block: inside the margin
    assert t == 0.7


def test_automatic_threshold_drops_only_the_far_background():
    _, near = scene()
    mask, t = dp.near_mask(near, margin_px=0)
    assert 0 < t < 0.9  # Otsu sits just above the background level
    assert mask[60, 45] == 1 and mask[5, 5] == 0


def test_grey_out_and_nothing_near_keeps_the_photo():
    img, near = scene()
    res = dp.filter_image(img, near, threshold=0.7, margin_px=0)
    assert (res["image"][5, 5] == dp.GREY).all() and (res["image"][60, 45] == 200).all()
    flat = dp.filter_image(img, np.zeros_like(near))
    assert flat["kept"] == 1.0 and (flat["image"] == img).all()


def test_layers_come_nearest_first():
    img, near = scene()
    res = dp.filter_image(img, near, threshold=0.3, margin_px=0, slices=2)
    first, second = res["layers"]
    assert (first[60, 45] == 200).all() and (first[60, 115] == dp.GREY).all()
    assert (second[60, 115] == 200).all() and (second[60, 45] == dp.GREY).all()


def test_dataset_keeps_labels_and_points_yaml_at_the_copy(tmp_path):
    src, out = tmp_path / "ours", tmp_path / "ours_depth"
    img, near = scene()
    for split in ("train", "val"):
        (src / split / "images").mkdir(parents=True)
        (src / split / "labels").mkdir(parents=True)
        cv2.imwrite(str(src / split / "images" / "a.jpg"), img)
        (src / split / "labels" / "a.txt").write_text("0 0.1 0.1 0.2 0.1 0.2 0.2\n")
    (src / "data.yaml").write_text("path: old\ntrain: train/images\nval: val/images\nnames:\n  0: bar\n")
    res = dp.filter_folder(lambda _: near, src, out, threshold=0.7, margin_px=0, slices=2, previews=True)
    assert res["images"] == 2 and res["files"]["train/images/a.jpg"]["kept"] < 1
    assert (out / "train/labels/a.txt").read_text() == "0 0.1 0.1 0.2 0.1 0.2 0.2\n"
    yaml = (out / "data.yaml").read_text()
    assert f"path: {out.resolve()}" in yaml and "0: bar" in yaml
    assert (out / "_preview/train/images/a_depth.png").exists()
    assert (out / "_layers/val/images/a_layer2.jpg").exists()
    assert json.loads((out / "depth_filter.json").read_text())["revision"] == dp.REVISION


def test_single_photo(tmp_path):
    img, near = scene()
    f = tmp_path / "cage.png"
    cv2.imwrite(str(f), img)
    res = dp.filter_folder(lambda _: near, f, tmp_path / "out", threshold=0.7)
    assert res["images"] == 1 and (tmp_path / "out" / "cage.png").exists()
