import cv2
import numpy as np
import pytest

from concrete_evidence.capture import Stillness, counts, record
from concrete_evidence.frames import change, extract, fit_long_side, sharpness, thumb


def grid(shift=0, size=(240, 320)):
    """A sharp bar-like pattern; shift moves it sideways."""
    img = np.full(size, 200, np.uint8)
    for x in range(10 + shift, size[1], 30):
        cv2.line(img, (x, 0), (x, size[0]), 30, 3)
    return img


def test_sharp_beats_blurred():
    g = grid()
    assert sharpness(g) > 10 * sharpness(cv2.GaussianBlur(g, (21, 21), 0))


def test_change_zero_for_same_frame_and_large_for_shift():
    a = thumb(grid())
    assert change(a, a) == 0
    assert change(a, thumb(grid(shift=15))) > 6


def test_fit_long_side():
    big = np.zeros((1000, 2000, 3), np.uint8)
    assert fit_long_side(big, 800).shape[:2] == (400, 800)
    small = np.zeros((100, 200, 3), np.uint8)
    assert fit_long_side(small, 800) is small


@pytest.fixture
def video(tmp_path):
    """3 s at 10 fps: 1 s still, 1 s blurred, 1 s moving."""
    path = tmp_path / "walk.avi"
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (320, 240))
    assert w.isOpened()
    for k in range(30):
        g = grid() if k < 10 else grid(shift=(k * 7) % 30)
        if 10 <= k < 20:
            g = cv2.GaussianBlur(g, (31, 31), 0)
        w.write(cv2.cvtColor(g, cv2.COLOR_GRAY2BGR))
    w.release()
    return path


def test_extract_drops_blur_and_duplicates(video, tmp_path):
    out = tmp_path / "frames"
    r = extract(video, out, every_s=0.2)  # every 2nd frame -> 15 candidates
    assert r.kept + r.blurry + r.duplicates == 15
    assert r.blurry >= 4
    assert r.duplicates >= 3  # the still second repeats itself
    assert r.kept >= 2
    assert len(list(out.glob("*.jpg"))) == r.kept


def test_extract_missing_video(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract(tmp_path / "nope.mp4", tmp_path / "out")


def test_stillness_needs_n_still_frames():
    s = Stillness(frames=3, threshold=2.5)
    f = cv2.cvtColor(grid(), cv2.COLOR_GRAY2BGR)
    assert [s.update(f)[0] for _ in range(4)] == [False, False, False, True]
    assert s.update(cv2.cvtColor(grid(shift=15), cv2.COLOR_GRAY2BGR))[0] is False


def test_record_adds_mm_only_with_scale():
    r = record(7, "bar", 0.912, (10, 20, 30, 120), None)
    assert r["centre_px"] == [20.0, 70.0] and r["size_px"] == [20.0, 100.0]
    assert "size_mm" not in r
    r = record(7, "bar", 0.912, (10, 20, 30, 120), 2.0)
    assert r["size_mm"] == [40.0, 200.0]
    assert counts([r, r, record(1, "tie", 0.5, (0, 0, 1, 1), None)]) == {"bar": 2, "tie": 1}
