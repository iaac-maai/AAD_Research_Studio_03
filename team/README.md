# Team folders

One folder each. Put **your own work** here: your plan, notes, results, scores, small screenshots and diagrams.

| Folder | Who | Holds |
|---|---|---|
| `team/diego/` | Diego | dataset checks, `sources.csv`, labelling notes, training scores |
| `team/akanksha/` | Akanksha | Eurocode 8 check, fix wording, schedule-from-PDF spec, wireframe |

**Shared code does not go here.** It goes into the shared folders, through a pull request:

| What | Where |
|---|---|
| the check, markers, all Python the pipeline uses | `concrete_evidence/` |
| the model server | `02_model_server/` |
| the Cloudflare app (incl. the result page) | `03_app/` |
| schedules (JSON) | `live/` |
| dataset list and licences | `datasets/CATALOGUE.md` |

**Never on GitHub:** photos, datasets, model weights (`*.pt`, `*.onnx` over a few MB), passwords, API keys. Photos and weights go to the team Google Drive (`MyDrive/ConcreteEvidence/`); the trained model to Hugging Face (`iaac-maai`).

## How to upload (every time)

```bash
git checkout main
git pull
git checkout -b diego-sources        # a new branch: your name + what it is
# ... add or edit files in team/<you>/ ...
git add team/diego
git commit -m "Diego: dataset checks and sources.csv"
git push -u origin diego-sources
gh pr create --fill                  # or open the pull request on github.com
```

The GitHub check (ruff + pytest) runs on every pull request. Merge when it is green. Small files only: keep each file under 5 MB.
