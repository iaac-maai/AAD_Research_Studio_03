import numpy as np
import pytest

from concrete_evidence.markers import MARKER_IDS, MarkerDetector, marker_image, marker_sheet


def scene(side_px=100, size=(600, 800)):
    """White frame with markers 0-3 near the corners, each side_px wide."""
    h, w = size
    img = np.full((h, w), 255, np.uint8)
    pad = 40
    spots = [(pad, pad), (pad, w - pad - side_px), (h - pad - side_px, pad), (h - pad - side_px, w - pad - side_px)]
    for i, (y, x) in zip(MARKER_IDS, spots, strict=True):
        img[y:y + side_px, x:x + side_px] = marker_image(i, side_px)
    return np.dstack([img] * 3)


def test_finds_all_four_markers():
    found = MarkerDetector().find(scene())
    assert sorted(found) == list(MARKER_IDS)
    assert MarkerDetector.all_found(found)


def test_scale_matches_marker_size():
    # 100 mm marker drawn 100 px wide -> about 1 mm per px
    det = MarkerDetector(marker_mm=100)
    assert det.mm_per_px(det.find(scene(side_px=100))) == pytest.approx(1.0, rel=0.03)
    assert det.mm_per_px(det.find(scene(side_px=50))) == pytest.approx(2.0, rel=0.05)


def test_no_markers_no_scale():
    det = MarkerDetector()
    found = det.find(np.full((300, 300, 3), 255, np.uint8))
    assert found == {}
    assert det.mm_per_px(found) is None
    assert not MarkerDetector.all_found(found)


def test_sheet_is_a4_and_readable():
    page = marker_sheet(100, dpi=150)
    assert page.shape == (round(297 * 150 / 25.4), round(210 * 150 / 25.4))
    assert sorted(MarkerDetector().find(page)) == list(MARKER_IDS)


def test_sheet_rejects_markers_too_big_for_a4():
    with pytest.raises(ValueError):
        marker_sheet(120)
