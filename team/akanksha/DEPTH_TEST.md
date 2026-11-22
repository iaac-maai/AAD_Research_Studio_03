# Depth test status

The fab-lab mock-up photos were not available in this workspace, so a real cage depth test could not be run. This is a hand-off/physical-deliverable blocker, not a code result.

## Required command

`python pipeline.py depth <mock-up photos> --out <output directory> --preview --slices 2`

Use only:

- Apache-2.0 Depth Anything V2 Small;
- corrected and faulted cage photos from the fab-lab session;
- output files under 1 MB each;
- no full-size photos in GitHub.

## Questions to decide

1. Does the depth filter keep the complete cage, including the outer ties and longitudinal bars?
2. Are bar ends or tie edges cut off after filtering?
3. Does the grey background improve the cage view, or remove useful context?
4. Does each 135-degree hook remain visible?
5. Does filtering preserve the planted missing-tie, 90-degree-hook and shifted-bar faults?

## Before/after set

The final report must contain five before/after pairs:

1. corrected cage, face A;
2. corrected cage, face B;
3. missing tie;
4. 90-degree hook;
5. shifted bar.

Expected output is one small `(before, after)` comparison per pair, no larger than 1 MB, plus three lines: cage kept, bars cut off, decision to keep or turn depth off.
