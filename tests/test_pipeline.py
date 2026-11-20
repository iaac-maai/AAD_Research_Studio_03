import argparse
import subprocess
import sys

import pytest

import pipeline
from tests.conftest import ROOT


def test_help_lists_every_stage():
    out = subprocess.run([sys.executable, "pipeline.py", "--help"], cwd=ROOT, capture_output=True, text=True,
                         check=True).stdout
    for stage in ("markers", "frames", "upload", "conrebseg", "sord", "pull", "train", "eval", "export", "live",
                  "check"):
        assert stage in out


def train_args(**kw):
    a = dict(stage="pretrain", model=None, epochs=1, imgsz=64, batch=1, patience=1, device=None, force_cpu=False,
             data="conrebseg")
    a.update(kw)
    return argparse.Namespace(**a)


def test_train_refuses_cpu_without_flag(tmp_path, monkeypatch):
    (tmp_path / "data.yaml").write_text("names: {0: bar}\n")
    monkeypatch.setitem(pipeline.PATHS, "conrebseg_yolo", tmp_path)
    monkeypatch.setattr(pipeline, "has_gpu", lambda: False)
    with pytest.raises(SystemExit, match="No CUDA GPU"):
        pipeline.st_train(train_args())


def test_train_needs_data_first(tmp_path, monkeypatch):
    monkeypatch.setitem(pipeline.PATHS, "conrebseg_yolo", tmp_path / "missing")
    with pytest.raises(SystemExit, match="not found"):
        pipeline.st_train(train_args())


def test_roboflow_key_only_from_environment(monkeypatch):
    monkeypatch.delenv("ROBOFLOW_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="ROBOFLOW_API_KEY"):
        pipeline.need_key()
    monkeypatch.setenv("ROBOFLOW_API_KEY", "test-value")
    assert pipeline.need_key() == "test-value"
