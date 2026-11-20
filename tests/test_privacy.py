import numpy as np
import pytest

from concrete_evidence import privacy
from concrete_evidence.privacy import blur_boxes, blur_faces

needs_model = pytest.mark.skipif(not privacy.model_path().exists(),
                                 reason="face model not fetched (python -m concrete_evidence.privacy --fetch)")


def noisy(seed=0, size=(200, 300, 3)):
    return np.random.default_rng(seed).integers(0, 255, size, dtype=np.uint8)


def test_blur_boxes_changes_only_the_box():
    img = noisy()
    out = blur_boxes(img, [(100, 50, 40, 40)], pad=0.0)
    assert out is not img
    assert np.array_equal(out[:50], img[:50])  # rows above the box untouched
    assert np.array_equal(out[:, :100], img[:, :100])  # columns left of the box untouched
    box_in, box_out = img[50:90, 100:140].astype(float), out[50:90, 100:140].astype(float)
    assert box_out.std() < 0.5 * box_in.std()  # noise inside is smoothed away


def test_blur_boxes_clips_at_the_edge():
    img = noisy()
    out = blur_boxes(img, [(-20, -20, 50, 50), (500, 500, 10, 10)])
    assert out.shape == img.shape


def test_missing_model_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("CE_MODELS", str(tmp_path))
    privacy._detector.cache_clear()
    try:
        with pytest.raises(FileNotFoundError, match="--fetch"):
            blur_faces(noisy())
    finally:
        privacy._detector.cache_clear()


@needs_model
def test_frame_without_faces_is_returned_as_is():
    img = np.full((240, 320, 3), 180, np.uint8)
    out, n = blur_faces(img)
    assert n == 0 and out is img
