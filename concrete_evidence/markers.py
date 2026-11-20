"""ArUco markers: the scale and reference for every measurement.

Convention (same as rebar_check_ar): dictionary DICT_4X4_50, ids 0-3,
printed 100 mm wide, placed just outside the corners of the mat or cage.
"""

from __future__ import annotations

import cv2
import numpy as np

ARUCO_DICT = cv2.aruco.DICT_4X4_50
MARKER_IDS = (0, 1, 2, 3)
DEFAULT_MARKER_MM = 100.0

A4_MM = (210, 297)


def _dictionary():
    return cv2.aruco.getPredefinedDictionary(ARUCO_DICT)


class MarkerDetector:
    """Finds our four markers in a BGR frame."""

    def __init__(self, marker_mm: float = DEFAULT_MARKER_MM):
        self.marker_mm = float(marker_mm)
        self._det = cv2.aruco.ArucoDetector(_dictionary(), cv2.aruco.DetectorParameters())

    def find(self, frame: np.ndarray) -> dict[int, np.ndarray]:
        """Return {marker id: 4x2 corner array} for markers 0-3 found in the frame."""
        gray = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self._det.detectMarkers(gray)
        found: dict[int, np.ndarray] = {}
        if ids is not None:
            for c, i in zip(corners, ids.flatten(), strict=True):
                if int(i) in MARKER_IDS:
                    found[int(i)] = c.reshape(4, 2).astype(np.float32)
        return found

    def mm_per_px(self, found: dict[int, np.ndarray]) -> float | None:
        """Scale from the mean side length of every marker seen.

        Good when the view is close to top-down. Returns None with no markers.
        """
        if not found:
            return None
        sides = [np.linalg.norm(c[k] - c[(k + 1) % 4]) for c in found.values() for k in range(4)]
        return self.marker_mm / float(np.mean(sides))

    @staticmethod
    def all_found(found: dict[int, np.ndarray]) -> bool:
        return all(i in found for i in MARKER_IDS)

    @staticmethod
    def draw(frame: np.ndarray, found: dict[int, np.ndarray]) -> None:
        for i, c in found.items():
            pts = c.astype(int)
            cv2.polylines(frame, [pts], True, (0, 200, 255), 2)
            cv2.putText(frame, f"M{i}", tuple(int(v) for v in pts[0]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)


def marker_image(marker_id: int, side_px: int) -> np.ndarray:
    """One marker as a grayscale image, side_px wide, no border."""
    return cv2.aruco.generateImageMarker(_dictionary(), int(marker_id), int(side_px))


def marker_sheet(marker_mm: float = DEFAULT_MARKER_MM, dpi: int = 300) -> np.ndarray:
    """An A4 page (grayscale) with markers 0-3, 2 x 2, each marker_mm wide at 100 % print."""
    px_per_mm = dpi / 25.4
    width, height = (int(round(v * px_per_mm)) for v in A4_MM)
    side = int(round(marker_mm * px_per_mm))
    gap_x, gap_y = (width - 2 * side) // 3, (height - 2 * side) // 3
    if min(gap_x, gap_y) < 3 * px_per_mm:  # at least 3 mm of white between markers, at any dpi
        raise ValueError(f"{marker_mm} mm markers don't fit 2 x 2 on A4; use 100 mm or less")
    page = np.full((height, width), 255, np.uint8)
    for i in MARKER_IDS:
        r, c = divmod(i, 2)
        x, y = gap_x + c * (side + gap_x), gap_y + r * (side + gap_y)
        page[y:y + side, x:x + side] = marker_image(i, side)
        cv2.putText(page, f"id {i} - {marker_mm:g} mm - DICT_4X4_50", (x, y + side + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, 0, 2, cv2.LINE_AA)
    return page
