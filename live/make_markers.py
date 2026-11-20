"""
Print the 4 ArUco markers the live view and the checker look for.

    python live/make_markers.py                 # live/markers_A4.png, 300 dpi
    python live/make_markers.py --mm 100

One A4 page, ids 0-3 of DICT_4X4_50, each exactly --mm wide when printed at
100 % scale (turn off "fit to page"). Measure one with a ruler after printing:
if it isn't --mm wide, pass the measured width to live.py --marker-mm.
"""

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from concrete_evidence.markers import DEFAULT_MARKER_MM, marker_sheet  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mm", type=float, default=DEFAULT_MARKER_MM, help="marker width in mm (2 x 2 must fit on A4)")
    p.add_argument("--out", default="live/markers_A4.png")
    a = p.parse_args()
    try:
        page = marker_sheet(a.mm)
    except ValueError as e:
        raise SystemExit(str(e)) from e
    cv2.imwrite(a.out, page)
    print(f"wrote {a.out}: 4 markers of {a.mm:g} mm. Print at 100 % on A4, then cut them out.")


if __name__ == "__main__":
    main()
