# Fix wording review

The following changes are recommended for `concrete_evidence/fixes.py`.

| Original pattern | Crew-facing wording | Why |
|---|---|---|
| `Add 2 bar(s)...` | `Add 2 longitudinal bar(s). The photo shows 2; the schedule requires 4. Stop and position...` | Explains what to count and requires a stop before retying. |
| `Check the 1 extra bar(s)...` | `Remove or recheck 1 extra longitudinal bar(s)...` | Opens with the action and avoids a purely model-facing check. |
| `Bar 3 looks 10 mm... replace it with...` | `Check bar 3... Replace it only after confirming the diameter and cut label.` | Uses an unambiguous double-check instead of implying the model can certify the bar. |
| `Rebend hook 8 to 135 degrees (now 90).` | `Rebend hook 8 to 135 degrees; it is currently 90 degrees.` | Keeps the noun and measured angle clear. |

The existing tie instruction is acceptable:

`Add 2 tie(s) between 100 and 330 mm from the first tie in view (gap 230 mm, at most 100 mm in the end zone).`

It is actionable because it gives the tie count, measured position range, gap and zone limit.

The schedule-vs-code instruction is acceptable as an engineer escalation:

`Ask the engineer before the pour: ...`
