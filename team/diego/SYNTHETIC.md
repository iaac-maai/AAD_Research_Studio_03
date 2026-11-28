# Synthetic column cages (source 5)

No public dataset labels stirrups or hooks (see `DATASET_CHECKS.md`), so we render our own. Every label is exact: it comes from the 3D model, not from a person.

**What's generated** (`synthetic/make_cages.py`, seed 22, 300 images, 960 × 720):

- A random column cage per image: section 25–50 cm, 1.2–2.4 m tall, 2–4 bars per side (Ø12–25), stirrups Ø8–10 at 6–12 cm in the end zones and 15–25 cm in the middle.
- Each stirrup closes at one corner with **two hooks**: 135° (both tails into the core) or 90° (tails along the sides). The share of 90° hooks varies per cage (15–55 %), so both classes are well represented.
- Faults on purpose: a missing stirrup in 30 % of cages, a shifted bar in 25 %.
- Camera: 40 % close-ups of the hook corner (30–80 cm), the rest 0.6–1.7 m, from −15° to 35°. Sun + ambient light, rust or grey steel.
- Backgrounds: concrete, formwork, soil, sky with ground, blurred site blocks; ArUco markers (DICT_4X4_50) in the corners of 40 % of images, like the fab-lab photos. Noise, blur, brightness and JPEG quality vary.

**Labels:** YOLO-seg polygons, classes `bar · stirrup · hook_90 · hook_135`. A piece hidden behind another is joined into one polygon along the hidden part; stirrup loops are keyholed so the inside stays unlabelled; hooks overlap their stirrup (the `LABELLING.md` rule).

**How to use:** upload the zip to Roboflow as batch `synthetic` and keep it **out of the test set**: the honest score is on the fab-lab cage. Renders are cleaner than real photos, so they help the model learn the hook shapes, but the real photos decide the score.

**Limits:** no shadows (the renderer's shadow maps fail on this Python version), smooth bars without ribs, no tie-wire, no people or clutter in front of the cage.

**Run it again:** `PYOPENGL_PLATFORM=egl python team/diego/synthetic/make_cages.py --n 300 --out synthetic --seed 22` (needs `pyrender trimesh opencv-contrib-python`; ~1–3 s per image on a laptop CPU). Change `--seed` for a new set.

## Fab-lab mock-up set (120 renders)

`make_cages.py --mockup --n 120 --start 1000 --seed 33` renders only the first fab-lab mock-up cage (`team/akanksha/MOCKUP.md`, removed 28 Nov, still in git history): 400 × 400 × 1200 mm, 4 × Ø16 corner bars, Ø8 ties at 100 mm (0–500 mm at both ends) and 200 mm in the middle, 135° hooks with 80 mm tails, on a 500 × 500 board. Faults one at a time, like the real session: none 40 %, missing tie in the lower end zone 20 %, one 90° hook 20 %, one bar shifted 30 mm 20 %. Labels: 441 `bar`, 1,112 `stirrup`, 23 `hook_90`, 1,268 `hook_135`. Upload as batch `synthetic_mockup`; like the rest of the synthetic data it stays out of the test set, so the real fab-lab cage is still a fair test. The camera is kept outside the cage in this mode (and in any new run).
