# Explainers: problems we hit and how we solved them

Short notes for the professors, one per problem. The figures are in the team Google Drive (link below), not in
this repo: some are built on ROI-1555 photos, which have no licence, and this repo is public.

**Figures:** _Drive link to be added_

## 1. Pieces vs objects (two-layer cage)

Files: `01_two_layers_BEFORE_pieces.jpg`, `02_two_layers_AFTER_objects.jpg`

- **Problem:** ROI-1555 draws every *visible piece* of a bar or stirrup as its own polygon. Converted as they
  were, one cage photo counted **133 bars and 26 stirrups**. The real cage has **24 bars and 5 stirrups**.
  A model trained on pieces would count pieces too.
- **Fix:** pieces with the same ROI label (`hoop-3` twice = one stirrup) are merged into one outline, joined by
  thin bridges across the hidden parts (`team/diego/roi1555_to_yolo.py`, the same rule as our synthetic labels).
- **What the figure shows:** one photo goes into two models at the same time. YOLO says *what* each thing is and
  *where* (outlines); Depth Anything says *how near* each pixel is. Each outline then gets the depth of its own
  pixels, and the bars split into two layers (after the fix: top layer 6 bars, bottom layer 18 bars, 5 stirrups).
  With pieces, the two layers do not separate cleanly; with whole objects they do.
- **Limit:** the photo is very oblique, so one bar runs from near to far. A photo taken from above separates the
  layers better; the app can ask for that.
