# Dataset catalogue: rebar faults before the pour

Researched 20 Nov 2026, updated 21 Nov 2026. Goal: find bars and ties that are **missing, shifted, wrong size, badly spaced** or have the **wrong hooks** before concrete is poured. Version 1 checks **column ties, hooks and spacing**.

**Rule: only openly licensed data goes into training.** A dataset with no licence is "all rights reserved" even when it is public, so it is listed here for reference only. No general web scraping (Google Images, YouTube frames): those photos are copyrighted.

No public dataset labels the *faults* themselves (missing bar, wrong spacing, low cover). The available sets teach the model to **find bars, ties and hooks**. The fault is then found by **measuring** those detections against the bar bending schedule and Eurocode 8 (`concrete_evidence/check.py`), plus our own mock-ups with planted errors.

## The plan without site access (21 Nov 2026)

We can't film on a real site. The labelled set for `bar · tie · hook_90 · hook_135` is built from five sources, in this order:

| # | Source | What it gives | Who | When |
|---|---|---|---|---|
| 1 | **Roboflow Universe sets with outlines** (below, "to check one by one") | Real site photos of rebar with polygons. The closest match to our task | Diego: open each page logged in, confirm CC BY 4.0 and polygons, fork into `concrete-evidence-column-cages`, map classes to ours | Sat 21 – Sun 22 Nov |
| 2 | **Box-only sets turned into outlines**: Column Tie Detection, SteelBindings, stirrup-recognition | Mostly the `tie` class. Roboflow Smart Polygon (Segment Anything) draws an outline inside each box; fix by hand | Diego | Sun 22 Nov |
| 3 | **Open-licence photos**: Wikimedia Commons and Flickr, filtered to CC0 / CC BY / CC BY-SA | Real column cages from many sites, labelled by us. Expect 50–150 | Diego, Akanksha | Sat 21 – Sun 22 Nov |
| 4 | **Fab-lab mock-up**: a small column cage with the 4 ArUco markers, correct and with planted faults (a tie removed, a hook bent to 90°, a bar shifted) | Our only real faults, the live demo, and the test photos for the depth filter | team | Sun 22 – Mon 23 Nov |
| 5 | **Renders** (optional): cages generated in Grasshopper or Blender | Perfect outlines and true depth for free. Cleaner than real photos | whoever is quick in Grasshopper | if time allows |

Keep a CSV for sources 1–3: file, source URL, author, licence. CC BY and CC BY-SA need the author credited; CC BY-SA also means a dataset we share must keep that licence.

**Target:** 300+ labelled images by Sun 22 Nov night, baseline trained Mon 23 Nov. Keep the mock-up photos of one cage out of training: that's the honest test set.

**Depth filter:** if the model will run with Depth Anything in front (`--depth-filter`), filter the labelled set the same way before training: `python pipeline.py depth data/ours --out data/ours_depth`.

## Usable (open licence)

| Dataset | What it shows | Labels | Size | Licence | Status |
|---|---|---|---|---|---|
| [Column Tie Detection v7](https://universe.roboflow.com/column-tie-detection/custom-workflow-object-detection-yhfbh) | Column cages, ties present or missing | Boxes: `Tie`, `No Tie`, `PartialTie` | 752 images | CC BY 4.0 | ❌ Checked 21 Nov: the `Tie` boxes sit on **tie-wire knots at crossings**, not stirrups. Not our `tie`: skip |
| [SteelBindings v1](https://universe.roboflow.com/steelbinding-for-rcc/steelbindings) | Beams, columns, stirrups | Boxes: `Beam`, `Column`, `Lateral-Ties`, `Stirrup` | 303 images | CC BY 4.0 | Weak (21 Nov): `Stirrup` / `Lateral-Ties` boxes cover whole zones of stirrups, not one each |
| [stirrup-recognition-dataset](https://universe.roboflow.com/jiawens-workspace/stirrup-recognition-dataset) | Stirrups | Boxes: `stirrup` | 301 images | CC BY 4.0 | ✅ Source 2 (21 Nov): one box per loose stirrup. Forked to Diego's workspace, version 1; boxes → `tie` outlines with SAM 2.1 in `team/diego/box_to_polygons.ipynb` |
| [ConRebSeg](https://github.com/DTU-PAS/ConRebSeg) | Real construction sites, exposed rebar | Segmentation: rebar, person, car, truck | 14,805 images, **22 GB** self-collected | Code GPL-3.0, data CC BY 4.0 | Concrete **repair** sites (bridge undersides, shotcrete). Labels are **patches** of exposed rebar, not single bars, and no pre-pour cages, so it isn't training data for `bar`. Converted as `exposed_rebar` by `python pipeline.py conrebseg` (self-collected only: 6,637 train, 3,454 val, 2,090 test images, 26,072 patches), for an optional warm-up. Downloaded to D: on Akshat's laptop; the Colab notebook downloads it itself. Its YouTube part is skipped: no clear licence |
| [SORD: Synthetic On-site Rebar Data](https://huggingface.co/datasets/bugwei/synthetic_on-site_rebar_data) | 25,287 Revit renders of columns, beams, slabs, walls on site | Instance masks: `intersection`, `spacing` | 120 GB total, ~480 MB per shard | CC BY-NC 4.0 (**non-commercial**) | **Not our main data**: rendered, not real, and it outlines bar *crossings* and the *gaps* between bars, not bars, ties or hooks. Optional quick test only; never in the model we publish. Shards 0–1 in `data/sord` |

### Roboflow Universe, to check one by one (source 1)

These appear on Roboflow Universe under CC BY 4.0 according to search listings, but image counts and label types vary between versions. Roboflow blocks automated page reads (21 Nov 2026), so open each page **logged in**, confirm the licence and that labels are polygons, then fork it.

| Project | Why it's useful | Checked |
|---|---|---|
| [roomsegment/rebar-seg](https://universe.roboflow.com/roomsegment/rebar-seg) | Rebar **segmentation** masks (701 or 1,399 images, depending on version) | ✅ 21 Nov: CC BY 4.0, polygons per bar, 701 images, class `rebar`. Mostly slab meshes. All 701 forked, `rebar` → `bar` |
| [ntu-ks0ac/rebar-segment-ysgc1](https://universe.roboflow.com/ntu-ks0ac/rebar-segment-ysgc1) | Classes `intersection`, `spacing`: same idea as SORD, but real photos | ❌ 21 Nov: CC BY 4.0 but **boxes**, 100 images, none of our classes. Skip |
| [new-workspace-eeam1/yolo-eio1c](https://universe.roboflow.com/new-workspace-eeam1/yolo-eio1c) | Classes `rebar-cross`, `tie-wire`: the only public **tie-wire** labels found | ❌ 21 Nov: CC BY 4.0 but **boxes**, 73 images. Tie-wire isn't our `tie` (the stirrup). Skip |
| [capstone-04lit/rebar-intersection-detect](https://universe.roboflow.com/capstone-04lit/rebar-intersection-detect) | Rebar crossings (boxes) | ❌ 21 Nov: CC BY 4.0, boxes, 99 images, class `intersection`. Skip |
| [sitevision-tnmlg/rebar-3dl2l](https://universe.roboflow.com/sitevision-tnmlg/rebar-3dl2l) | General rebar on site, 701 images | ✅ 21 Nov: CC BY 4.0, polygons per bar, **358** images, classes `rebar`, `rebars`. Column starter bars: closest to our columns. 36 forked so far, `rebar` → `bar` |

## Not usable (no open licence): reference only

| Dataset | Why it would help | Problem |
|---|---|---|
| [ROI-1555](https://huggingface.co/datasets/tsrobcvai/ROI-1555_Rebar_Detection_and_Instance_Segmentation_Dataset) | 1,555 real photos with instance masks; Mask2Former best on it (Sun, Fan & Shao 2025). **The best match that exists** | No licence on the dataset card. **Email the authors (Shao Lab) for permission now**; an answer could come by Mon 23 Nov |
| [Synthetic Stirrup Rebar Segmentation](https://huggingface.co/datasets/tsrobcvai/Synthetic_Dataset_for_Stirrup_Rebar_Segmentation) | 20,800 synthetic + 233 real stirrup images | No licence on the dataset card. Ask in the same email |
| [Rebar-MGR public subset](https://github.com/Volve-yu/Rebar-MGR) | 500 site images **with measured spacing**: the closest to a fault dataset | Its own notice says no redistribution licence is granted |
| [RebarDSC](https://github.com/Armin1337/RebarDSC) | 2,125 images of rebar bundles, for counting | No licence in the repo. Also about bundles, not placed bars |
| [whiesty/synthetic-datasets-for-rebar](https://github.com/whiesty/synthetic-datasets-for-rebar) | 2,500 synthetic images | Licence not confirmed; hosted on Baidu Netdisk |
| Google Images, YouTube, general web scraping | Many photos | Copyrighted, no licence. Not allowed |

## Pretrained models we use

| Model | Used for | Licence | Pinned |
|---|---|---|---|
| YOLOv8n-seg (Ultralytics) | the segmentation model we fine-tune | AGPL-3.0 | `ultralytics==8.4.216` |
| [Depth Anything V2 Small](https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf) | the depth filter before YOLO (`concrete_evidence/depth.py`) | Apache-2.0 (checked 21 Nov 2026). **Base and Large are CC BY-NC: not used** | revision `5426e4f0` |
| YuNet face detector (OpenCV Zoo) | blurring faces in every saved frame | MIT | SHA256 in `concrete_evidence/privacy.py` |

## Our own data (the only source of real faults)

- **Fab-lab column cage** (source 4): photos of each face with the 4 markers, correct and with planted faults. Also the test photos for the depth filter and the live demo.
- **Skewer mats**: good mat and mistake mat (one bar removed, one shifted 10 mm), 20–30 top-down photos each with 4 corner markers. Photos and a trained `skewer_best.pt` are in `~/concrete-evidence/code/skewer_yolo_notebook`.
- **Synthetic mats** from our `ce/synth.py` generator: shifted, missing, wrong-size and sagging bars, each with an answer key.

## Credits

- SORD: Huang, T.-W., Chen, Y.-H., Lin, J. J., & Chen, C.-S. (2025). *Deep learning without human labeling for on-site rebar instance segmentation using synthetic BIM data and domain adaptation.* Automation in Construction, 171, 105953.
- ConRebSeg: Schmidt, P., & Nalpantidis, L. (2025). *ConRebSeg: A segmentation dataset for reinforced concrete construction.* Automation in Construction, 171.
- Depth Anything V2: Yang, L., Kang, B., Huang, Z., Zhao, Z., Xu, X., Feng, J., & Zhao, H. (2024). *Depth Anything V2.* NeurIPS 2024.
- Roboflow sets and open-licence photos: credit each project page or author (CC BY 4.0 / CC BY-SA), listed in the sources CSV.
