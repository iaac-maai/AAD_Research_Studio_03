# Schedule from the engineer's PDF

Akanksha → Akshat. What the feature does, what the server returns, and how to read a column schedule. The UI (upload button, form, confirm step) is mine; the endpoint is yours.

## The flow

1. On the new-check screen the engineer uploads the drawing PDF (or skips and types).
2. The server reads it and returns the schedule values it found.
3. The values fill the schedule form. Anything not found stays empty and highlighted.
4. The engineer confirms or corrects each value. **No check runs on unconfirmed values.**
5. The confirmed schedule is sent with the photo, exactly as today (`POST /api/check`, field `schedule`).

A PDF often holds several columns (a column table). The server returns all of them; the engineer picks the one being photographed.

## The endpoint

`POST /api/schedule-from-pdf`, multipart: `pdf` (max ~10 MB), optional `element` (e.g. `"C1"`).

Response:

```json
{
  "columns": [
    {
      "values": {"element": "C1", "column_mm": [400, 400], "cover_mm": 30, "bar_diameter_mm": 16,
                 "bar_count": 3, "tie_diameter_mm": 8, "tie_spacing_mm": {"end": 100, "middle": 200},
                 "hook_angle": 135},
      "found_on_page": 2,
      "source_text": "C1  40x40  8Ø16  cØ8 c/10-20",
      "missing": ["clear_height_mm", "bar_spacing_mm"]
    }
  ],
  "note": "Read automatically. Check every value against the drawing."
}
```

- `values` must validate against **`live/schedule.schema.json`** (same file the form uses). Drop any value that doesn't, and list it in `missing`.
- `source_text` is the exact snippet each column came from, so the engineer can compare.
- Never guess a value that isn't on the drawing: leave it out and put it in `missing`.
- Not a schedule, unreadable or a scan with no text: `{"columns": [], "note": "<why>"}`. The form then opens empty.

## Values that are derived, not read

| Value | How |
|---|---|
| `bar_count` (per face) | from the total: a square column with N bars evenly round it shows N/4 + 1 per face. 4 bars → 2, 8 → 3, 12 → 4. Other layouts: leave it for the engineer |
| `bar_spacing_mm` | (side − 2 × cover − 2 × tie Ø − bar Ø) / (bars per face − 1) |
| `city`, `country`, `ductility` | from the site city the engineer picks, not from the PDF (location-based rules) |
| `hook_angle` | read it if drawn or written; if the drawing says nothing, leave it empty: the code decides (135° under Eurocode 8) |

## How column schedules are written (for the extraction prompt)

Common notations, to confirm on real PDFs:

| Written | Means |
|---|---|
| `40x40`, `40×40` (Spanish drawings, cm) | column 400 × 400 mm |
| `8Ø16`, `8φ16`, `8 Ø 16` | 8 bars of Ø16 in total |
| `4H16` (UK, BS 8666) | 4 high-yield bars of Ø16 |
| `cØ8 c/15`, `Ø8 c/15`, `cercos Ø8 a 15` | ties Ø8 every 15 **cm** (Spanish: `c/` = cada, spacing usually in cm) |
| `cØ8 c/10-20`, `Ø8 c/10 (zona crítica) c/20` | ties every 100 mm at the ends, 200 mm in the middle |
| `H8-200`, `R8 @ 200` (UK) | ties Ø8 every 200 mm |
| `r = 3 cm`, `recubrimiento 30 mm`, `cover 30` | cover 30 mm |
| `gancho 135°`, `135° hooks`, `seismic hooks` | hook angle 135° |

Units: Spanish drawings mix cm (sizes, spacing) and mm (bar Ø). Always return mm.

## Before it goes live

- **Test on real PDFs.** I'm collecting 2–3 real column schedules; no invented test files.
- **API key** as a Cloudflare secret, never in the repo.
- **Privacy:** drawings belong to the client. Don't store the PDF; keep only the confirmed values with the check, as with photos.
