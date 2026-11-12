"""
Concrete Evidence AI - Step 1: download the training datasets.

Pulls the public datasets listed in datasets/README.md into ./data/ so they
can be uploaded to Roboflow for labelling, or used directly in Colab.

Usage (laptop or Colab):
    pip install huggingface_hub roboflow
    python datasets/download_datasets.py                 # 2 SORD shards + Roboflow sets
    python datasets/download_datasets.py --sord-shards 5
    python datasets/download_datasets.py --skip-sord
    python datasets/download_datasets.py --skip-roboflow

Roboflow sets need your own API key (Roboflow > Settings > API Keys):
    export ROBOFLOW_API_KEY=xxxx        # Colab: os.environ["ROBOFLOW_API_KEY"] = "xxxx"
Never commit the key to this repo.
"""

import argparse
import os
import tarfile
from pathlib import Path

# ---------------------------------------------------------------- sources ---
SORD_REPO = "bugwei/synthetic_on-site_rebar_data"  # 120 GB total, ~480 MB / shard

# (workspace, project, version, folder name)
ROBOFLOW_SETS = [
    ("column-tie-detection", "custom-workflow-object-detection-yhfbh", 7, "column_tie_detection"),
    ("steelbinding-for-rcc", "steelbindings", 1, "steelbindings"),
    # stirrup-recognition-dataset (jiawens-workspace) has no published version,
    # so it can't be downloaded by API. Fork it in Roboflow instead - see README.
]
ROBOFLOW_FORMAT = "yolov8"  # boxes only; we re-outline as polygons in Roboflow


def download_sord(out_dir: Path, n_shards: int) -> None:
    from huggingface_hub import hf_hub_download

    out_dir.mkdir(parents=True, exist_ok=True)
    for i in range(n_shards):
        name = f"SORD-train-{i:05d}.tar"
        target = out_dir / name.replace(".tar", "")
        if target.exists() and any(target.iterdir()):
            print(f"[SORD] {name} already extracted, skipping")
            continue
        print(f"[SORD] downloading {name} (~480 MB)...")
        tar_path = hf_hub_download(SORD_REPO, name, repo_type="dataset",
                                   local_dir=out_dir / "_tars")
        print(f"[SORD] extracting {name}")
        # each tar already contains a folder named after the shard
        with tarfile.open(tar_path) as tf:
            tf.extractall(out_dir, filter="data")
        os.remove(tar_path)  # keep disk use down
    print(f"[SORD] done -> {out_dir}")


def download_roboflow(out_dir: Path) -> None:
    key = os.environ.get("ROBOFLOW_API_KEY")
    if not key:
        print("[Roboflow] ROBOFLOW_API_KEY not set - skipping Roboflow sets")
        return
    from roboflow import Roboflow

    rf = Roboflow(api_key=key)
    for workspace, project, version, folder in ROBOFLOW_SETS:
        dest = out_dir / folder
        if dest.exists() and any(dest.iterdir()):
            print(f"[Roboflow] {folder} already downloaded, skipping")
            continue
        print(f"[Roboflow] {workspace}/{project} v{version}")
        rf.workspace(workspace).project(project).version(version).download(
            ROBOFLOW_FORMAT, location=str(dest))
    print(f"[Roboflow] done -> {out_dir}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default="data", help="output folder (default: ./data)")
    p.add_argument("--sord-shards", type=int, default=2,
                   help="number of SORD train shards, ~100 images each (default 2)")
    p.add_argument("--skip-sord", action="store_true")
    p.add_argument("--skip-roboflow", action="store_true")
    a = p.parse_args()

    out = Path(a.out)
    if not a.skip_sord:
        download_sord(out / "sord", a.sord_shards)
    if not a.skip_roboflow:
        download_roboflow(out / "roboflow")


if __name__ == "__main__":
    main()
