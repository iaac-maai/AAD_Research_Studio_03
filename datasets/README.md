# Datasets — Step 1 (Before site)

The datasets only **teach** the AI. They are not stored in this repo (GitHub caps files at 100 MB; SORD alone is 120 GB). Run the script below to pull them into a local `data/` folder (git-ignored), then upload to Roboflow for labelling.

## Quick start

```bash
pip install huggingface_hub roboflow
export ROBOFLOW_API_KEY=your_key          # Roboflow > Settings > API Keys — never commit it
python datasets/download_datasets.py      # 2 SORD shards (~1 GB) + Roboflow sets
```

In Colab:

```python
!git clone https://github.com/iaac-maai/AAD_Research_Studio_03
%cd AAD_Research_Studio_03
!pip install -q huggingface_hub roboflow
import os; os.environ["ROBOFLOW_API_KEY"] = "your_key"
!python datasets/download_datasets.py --sord-shards 2
```

Options: `--sord-shards N` (each ≈ 480 MB, ≤100 images), `--skip-sord`, `--skip-roboflow`, `--out folder`.

## Sources

| Dataset | Images | Labels | Licence | How we get it |
|---|---|---|---|---|
| [SORD — Synthetic On-site Rebar Data](https://huggingface.co/datasets/bugwei/synthetic_on-site_rebar_data) | 25,000+ synthetic (2400×1800 PNG), 251 train + 2 valid shards | Instance segmentation, COCO JSON: rebar `intersection`, `spacing` | CC BY-NC 4.0 (**non-commercial only**) | Script (Hugging Face) |
| [Column Tie Detection](https://universe.roboflow.com/column-tie-detection/custom-workflow-object-detection-yhfbh) v7 | 752 | Boxes: `Tie`, `No Tie`, `PartialTie`, `items` | CC BY 4.0 | Script (Roboflow) |
| [SteelBindings](https://universe.roboflow.com/steelbinding-for-rcc/steelbindings) v1 | 303 | Boxes: `Beam`, `Column`, `Lateral-Ties`, `Stirrup` | CC BY 4.0 | Script (Roboflow) |
| [stirrup-recognition-dataset](https://universe.roboflow.com/jiawens-workspace/stirrup-recognition-dataset) | 301 | Boxes: `stirrup` | CC BY 4.0 | **Fork Dataset** in Roboflow (no published version, so no API download) |
| Our own photos of real column cages | 300+ target | Polygons, our classes | Ours | Shot on site, uploaded to Roboflow |

## Notes

- **Boxes → polygons.** The Roboflow sets are bounding boxes; our model is YOLOv8-seg. Re-outline each piece in Roboflow (Smart Polygon helps) with our classes: `bar · tie · hook 90° · hook 135°`.
- **SORD is synthetic and slab/wall-mesh oriented**; use it to pre-train on rebar shapes, not as the main source for column ties and hooks.
- **SORD licence is non-commercial.** Fine for the IAAC studio; do not carry SORD-trained weights into a commercial product.
- Cite SORD: Huang, T.-W., Chen, Y.-H., Lin, J. J., & Chen, C.-S. (2025). *Deep learning without human labeling for on-site rebar instance segmentation using synthetic BIM data and domain adaptation.* Automation in Construction, 171, 105953. https://doi.org/10.1016/j.autcon.2024.105953
- Roboflow datasets: credit each project page above (CC BY 4.0).
