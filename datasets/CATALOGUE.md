# Dataset catalogue: rebar faults before the pour

Researched 20 Nov 2026. Goal: find bars that are **missing, shifted, wrong size, badly spaced, untied or too low** before concrete is poured.

**Rule: only openly licensed data goes into training.** A dataset with no licence is "all rights reserved" even when it is public, so it is listed here for reference only.

No public dataset labels the *faults* themselves (missing bar, wrong spacing, low cover). The available sets teach the model to **find bars, ties and crossings**. The fault is then found by **measuring** those detections against the drawing (ArUco markers to mm, then EN 13670 / EC2 limits), plus our own mock-ups with planted errors.

## Usable (open licence)

| Dataset | What it shows | Labels | Size | Licence | Status |
|---|---|---|---|---|---|
| [SORD: Synthetic On-site Rebar Data](https://huggingface.co/datasets/bugwei/synthetic_on-site_rebar_data) | 25,287 Revit renders of columns, beams, slabs, walls on site | Instance masks: `intersection`, `spacing` | 120 GB total, ~480 MB per shard | CC BY-NC 4.0 (**non-commercial**) | Downloading 2 shards to `data/sord` |
| [Column Tie Detection v7](https://universe.roboflow.com/column-tie-detection/custom-workflow-object-detection-yhfbh) | Column cages, ties present or missing | Boxes: `Tie`, `No Tie`, `PartialTie` | 752 images | CC BY 4.0 | Needs `ROBOFLOW_API_KEY` |
| [SteelBindings v1](https://universe.roboflow.com/steelbinding-for-rcc/steelbindings) | Beams, columns, stirrups | Boxes: `Beam`, `Column`, `Lateral-Ties`, `Stirrup` | 303 images | CC BY 4.0 | Needs `ROBOFLOW_API_KEY` |
| [stirrup-recognition-dataset](https://universe.roboflow.com/jiawens-workspace/stirrup-recognition-dataset) | Stirrups | Boxes: `stirrup` | 301 images | CC BY 4.0 | Fork in Roboflow (no API version) |
| [ConRebSeg](https://github.com/DTU-PAS/ConRebSeg) | Real construction sites, exposed rebar | Segmentation: rebar, person, car, truck | 14,805 images, **22 GB** self-collected | Code GPL-3.0, data CC BY 4.0 | Downloaded to D: and converted by `python pipeline.py conrebseg` (self-collected only: 6,637 train, 3,454 val, 2,090 test images, about 26,000 bars). The Colab notebook downloads it itself. Its YouTube part is skipped: no clear licence |

### Roboflow Universe, to check one by one

These appear on Roboflow Universe under CC BY 4.0 according to search listings, but image counts and label types vary between versions. Open each page and confirm the licence and annotation type before adding it to `download_datasets.py`.

| Project | Why it's useful |
|---|---|
| [roomsegment/rebar-seg](https://universe.roboflow.com/roomsegment/rebar-seg) | Rebar **segmentation** masks (701 or 1,399 images, depending on version) |
| [ntu-ks0ac/rebar-segment-ysgc1](https://universe.roboflow.com/ntu-ks0ac/rebar-segment-ysgc1) | Classes `intersection`, `spacing`: same idea as SORD, but real photos |
| [new-workspace-eeam1/yolo-eio1c](https://universe.roboflow.com/new-workspace-eeam1/yolo-eio1c) | Classes `rebar-cross`, `tie-wire`: the only public **tie-wire** labels found |
| [capstone-04lit/rebar-intersection-detect](https://universe.roboflow.com/capstone-04lit/rebar-intersection-detect) | Rebar crossings (boxes) |
| [sitevision-tnmlg/rebar-3dl2l](https://universe.roboflow.com/sitevision-tnmlg/rebar-3dl2l) | General rebar on site, 701 images |

## Not usable (no open licence): reference only

| Dataset | Why it would help | Problem |
|---|---|---|
| [ROI-1555](https://huggingface.co/datasets/tsrobcvai/ROI-1555_Rebar_Detection_and_Instance_Segmentation_Dataset) | 1,555 real photos with instance masks; Mask2Former best on it (Sun, Fan & Shao 2025) | No licence on the dataset card. Ask the authors (Shao Lab) for permission |
| [Synthetic Stirrup Rebar Segmentation](https://huggingface.co/datasets/tsrobcvai/Synthetic_Dataset_for_Stirrup_Rebar_Segmentation) | 20,800 synthetic + 233 real stirrup images | No licence on the dataset card |
| [Rebar-MGR public subset](https://github.com/Volve-yu/Rebar-MGR) | 500 site images **with measured spacing**: the closest to a fault dataset | Its own notice says no redistribution licence is granted |
| [RebarDSC](https://github.com/Armin1337/RebarDSC) | 2,125 images of rebar bundles, for counting | No licence in the repo. Also about bundles, not placed bars |
| [whiesty/synthetic-datasets-for-rebar](https://github.com/whiesty/synthetic-datasets-for-rebar) | 2,500 synthetic images | Licence not confirmed; hosted on Baidu Netdisk |

## Our own data (the only source of real faults)

- **Skewer mats**: good mat and mistake mat (one bar removed, one shifted 10 mm), 20–30 top-down photos each with 4 corner markers. Photos and a trained `skewer_best.pt` are in `~/concrete-evidence/code/skewer_yolo_notebook`.
- **Synthetic mats** from our `ce/synth.py` generator: shifted, missing, wrong-size and sagging bars, each with an answer key.
- **Site photos of column cages**: target 300+, labelled as polygons: `bar · tie · hook 90° · hook 135°`.

## Credits

- SORD: Huang, T.-W., Chen, Y.-H., Lin, J. J., & Chen, C.-S. (2025). *Deep learning without human labeling for on-site rebar instance segmentation using synthetic BIM data and domain adaptation.* Automation in Construction, 171, 105953.
- ConRebSeg: Schmidt, P., & Nalpantidis, L. (2025). *ConRebSeg: A segmentation dataset for reinforced concrete construction.* Automation in Construction, 171.
- Roboflow sets: credit each project page (CC BY 4.0).
