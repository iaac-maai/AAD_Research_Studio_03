"""
Turn site or mock-up videos into frames worth labelling.

    python training/extract_frames.py cage_walk.mp4 more.mov --out data/frames --every 0.5

Keeps one frame every --every seconds, drops blurry frames and near-duplicates.
Upload what's left to the Roboflow project. Site videos show workers: only label frames you may share.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from concrete_evidence.frames import extract  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("videos", nargs="+")
    p.add_argument("--out", default="data/frames")
    p.add_argument("--every", type=float, default=0.5, help="seconds between candidate frames")
    p.add_argument("--min-sharp", type=float, default=80.0, help="blur cut-off; raise it to keep fewer frames")
    p.add_argument("--min-change", type=float, default=6.0, help="duplicate cut-off (mean grey-level change)")
    p.add_argument("--max-side", type=int, default=1600, help="resize so the long side is at most this")
    a = p.parse_args()

    total = 0
    for v in a.videos:
        try:
            r = extract(v, a.out, a.every, a.min_sharp, a.min_change, a.max_side)
        except FileNotFoundError as e:
            print(f"skip {v}: {e}")
            continue
        total += r.kept
        print(f"{v}: kept {r.kept}, dropped {r.blurry} blurry and {r.duplicates} near-duplicates")
    print(f"{total} frames in {a.out}")


if __name__ == "__main__":
    main()
