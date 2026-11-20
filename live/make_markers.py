"""
Print the 4 ArUco markers the live view and the checker look for.

    python live/make_markers.py                 # live/markers_A4.png, 300 dpi
    python live/make_markers.py --mm 100

One A4 page, ids 0-3 of DICT_4X4_50, each exactly --mm wide when printed at
100 % scale (turn off "fit to page"). Measure one with a ruler after printing:
if it isn't --mm wide, pass the measured width to live.py --marker-mm.
"""

import argparse

import cv2
import numpy as np

DPI = 300
A4_MM = (210, 297)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mm", type=float, default=100.0, help="marker width in mm (2 x 2 must fit on A4)")
    p.add_argument("--out", default="live/markers_A4.png")
    a = p.parse_args()

    px_per_mm = DPI / 25.4
    W, H = (int(round(v * px_per_mm)) for v in A4_MM)
    side = int(round(a.mm * px_per_mm))
    page = np.full((H, W), 255, np.uint8)
    d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    gap_x, gap_y = (W - 2 * side) // 3, (H - 2 * side) // 3
    if gap_x < 20 or gap_y < 20:
        raise SystemExit(f"{a.mm} mm markers don't fit 2 x 2 on A4. Use --mm 100 or less.")
    for i in range(4):
        r, c = divmod(i, 2)
        x, y = gap_x + c * (side + gap_x), gap_y + r * (side + gap_y)
        page[y:y + side, x:x + side] = cv2.aruco.generateImageMarker(d, i, side)
        cv2.putText(page, f"id {i} - {a.mm:g} mm - DICT_4X4_50", (x, y + side + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, 0, 2, cv2.LINE_AA)
    cv2.imwrite(a.out, page)
    print(f"wrote {a.out}: 4 markers of {a.mm:g} mm. Print at 100 % on A4, then cut them out.")


if __name__ == "__main__":
    main()
