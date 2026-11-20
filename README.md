# AAD_Research_Studio_03
Concrete Evidence_AI _“Catch it before you cast it.”

## Contents

- **[PIPELINE.md](PIPELINE.md)**: start here. `pipeline.py` runs every stage, from site video to a live rebar check
- `live/`: live view (`live.py`) and ArUco marker sheet (`make_markers.py`)
- `datasets/`: download script, sources and [dataset catalogue](datasets/CATALOGUE.md)
- `training/`: SORD converter, frame extractor and Colab notebooks (YOLOv8-seg)
- `docs/rebar_process_timeline.html`: the 20 steps of the rebar process, the faults at each, and the app feature that catches them
- `concrete_evidence/`: the shared code the scripts use (markers and scale, frame picking, label conversion, face blur, live-view records)
- `tests/`: tests for that code; they run on every pull request (`.github/workflows/ci.yml`)

## Working on the code

```bash
pip install -r requirements-dev.txt     # light: no torch, enough for the tests
python -m concrete_evidence.privacy --fetch
ruff check .
python -m pytest
```

`requirements.txt` pins everything for training and the live view; Python version in `.python-version` (3.13).
Every pull request runs the same lint and tests on GitHub. Merge only when the check is green.

## Licence

AGPL-3.0 ([LICENSE](LICENSE)), the same as Ultralytics YOLOv8, which the model is trained and run with.
If the app serves the model to other people, its source has to stay open to them.
Datasets keep their own licences: see [datasets/CATALOGUE.md](datasets/CATALOGUE.md).

## Privacy

Site video shows workers. Faces are blurred before any frame is saved, labelled or uploaded
(`concrete_evidence/privacy.py`, YuNet face detector). Check frames by eye before sharing them outside the team.
