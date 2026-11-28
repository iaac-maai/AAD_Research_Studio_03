# Fix wording: what the crew reads

Akanksha. One line per fault, read on a phone next to the cage (`concrete_evidence/fixes.py`).
Rule: **what to do, where, and in brackets why** (what was found against what is needed). The element and face are shown once with the result, not in every line.

| Fault | Instruction |
|---|---|
| Gap where a bar is missing | *Add a bar between bars 1 and 2 (gap 200 mm, should be 100 mm).* |
| Missing bar, no gap to show where | *Add 1 bar (found 3, drawing needs 4).* |
| Extra bar | *Check the 1 extra bar before removing anything (found 5, drawing needs 4).* |
| One bar out of place | *Move bar 1 35 mm towards bar 0 (gaps 123 and 53 mm, should be 88 mm).* |
| Two bars too close or far | *Move bars 3 and 4 to 150 mm apart (now 135 mm).* |
| Bar size | *Check bar 3: it looks Ø10, the drawing says Ø16.* |
| Tie spacing | *Add 1 tie 90–270 mm below the top tie (gap 180 mm, max 90 mm here).* |
| Hook angle | *Rebend hook 8 to 135° (now 90°; 90° hooks open in earthquakes).* |
| Hook tail | *Replace the tie with hook 8 (tail 50 mm, needs 80 mm).* |
| Drawing against the code | *Ask the engineer: the drawing has ties every 200 mm, the code allows 128 mm max.* |

Bar and hook numbers match the labels on the checked photo. One shifted bar gives one line, not two. When a gap already shows where a bar is missing, the bare count line is left out.
