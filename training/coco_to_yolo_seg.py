"""
Convert SORD (one LabelMe JSON per PNG; standard COCO also works) into YOLOv8-seg layout.

    python training/coco_to_yolo_seg.py --train data/sord/SORD-train-00000 data/sord/SORD-train-00001 \
                                        --val data/sord/SORD-valid-00000 --out data/sord_yolo

The logic lives in concrete_evidence/convert.py; this is the command-line entry.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run from a fresh clone, no install

from concrete_evidence.convert import build  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--train", nargs="+", required=True)
    p.add_argument("--val", nargs="+", required=True)
    p.add_argument("--out", default="data/sord_yolo")
    a = p.parse_args()
    try:
        print(f"wrote {build(a.train, a.val, a.out)}")
    except ValueError as e:
        raise SystemExit(str(e)) from e


if __name__ == "__main__":
    main()
