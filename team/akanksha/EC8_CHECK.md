# Eurocode 8 check

## Scope

This check covers the values used by `concrete_evidence/codes.py` for the DCM/DCH column check:

- critical-region length;
- DCM tie spacing;
- DCH tie spacing;
- 135-degree hooks and tie tail;
- EN 1992-1-1 tie spacing outside the critical region;
- the 400 x 400 mm example.

The result is a site-assistance setting, not a design certificate. Spanish and other national annexes and the project's engineer control final dimensions.

## EN 1998-1 findings

| Item | Used in code | Finding |
|---|---:|---|
| Critical region | `max(longest side, clear height / 6, 450 mm)` | Consistent with EN 1998-1 5.4.3.2.2(4) for the implemented column-face assumption. |
| DCM tie spacing | `min(core / 2, 175 mm, 8 x smallest longitudinal bar)` | Consistent with EN 1998-1 5.4.3.2.2(11). |
| DCH tie spacing | `min(core / 3, 125 mm, 6 x smallest longitudinal bar)` | Consistent with EN 1998-1 5.5.3.2.2(12). |
| Hooks | 135 degrees | Consistent with the Eurocode 8 DCM and DCH provisions for critical regions. |
| Hook tail | 10 x tie diameter | Used in the project as the stricter QA rule. It must be checked ductility-specific against the adopted printed clause and national annex before a real pour. |

The code defines `b0` as the confined-core dimension measured to the tie centreline. The implementation therefore uses `b0 = min(column sides) - 2 x cover - tie diameter`.

## EN 1992-1-1 9.5.3

Outside the critical region, the code uses:

`min(20 x smallest longitudinal bar diameter, smallest column side, 400 mm)`

This is consistent with the spacing rule in EN 1992-1-1 9.5.3(3).

## Spanish national annex

No project-specific Spanish National Annex value has been found in the repository. This implementation does not silently replace Eurocode values: it returns `verify: true`, and final approval remains with the engineer.

Before on-site use in Spain, the engineer should confirm the adopted CTE/NA edition and whether its values or marking differ from the EN 1998-1 recommended values.

## 400 x 400 mm example

For a 400 x 400 mm column, 16 mm longitudinal bars, 8 mm ties, 30 mm cover and DCM:

- confined core: 332 mm;
- end/critical-zone tie spacing: `min(166, 175, 128) = 128 mm`;
- middle-zone tie spacing: `min(320, 400, 400) = 320 mm`;
- critical-region length for a 3000 mm clear height: `max(400, 500, 450) = 500 mm`;
- hook tail: `10 x 8 = 80 mm`.

For DCH, the end-zone spacing is `min(110.7, 125, 96) = 96 mm`.

## Code change decision

No correction to `concrete_evidence/codes.py` is required for the implemented DCM/DCH spacing formulas or example values. The 10 dbw hook-tail constant should remain a verification flag rather than an unconditional design approval. `hook_tail_min_mm` is therefore returned with `verify: true`.
