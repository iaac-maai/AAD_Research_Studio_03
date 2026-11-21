# Timeline: who waits on whom, Sat 21 – Mon 23 Nov 2026

**Goal:** the app works end to end by **Sun 22 Nov night** with a stand-in model; Diego's trained model goes in on **Mon 23 Nov by 12:00**. Freeze Wed night, presentation Thu 26 Nov.

**Bold** = someone else waits on it. Each person's full list is in their `PLAN.md`.

## The two chains

**Data chain (the model):**
Akanksha: Eurocode 8 check **Sat 18:00** → mock-up design **Sat 21:00** → fab-lab session **Sun 14:00–17:00** (everyone) → Diego: fab-lab photos labelled + test set **Sun 19:00** → Roboflow version **Sun 20:00** → training started **Sun 21:00** → `best.pt` + scores **Mon 10:00** → Akshat: model swapped in **Mon 12:00**

**App chain (the product):**
Akshat: ONNX server **Sat 20:00** → Cloudflare app locally Sat 24:00 → Render live **Sun 11:00** → Cloudflare live **Sun 13:00** → Akanksha's result page (**Sun 12:00**) wired in **Sun 21:00**

**UI chain (the look):**
Akshat: user-journey design (site worker, engineer, architect, client) **Sat** → Diego + Akanksha: review it, flow + site supervisor role **Sun 23:00** → Akshat: app restyled, site worker + engineer screens **Tue 18:00** → architect + client screens only if the core works **Wed 18:00** (else shown as design)

## By when

| When | Who | What | Who waits on it |
|---|---|---|---|
| Sat 18:00 | Akanksha | Eurocode 8 values checked | her mock-up, Akshat's check |
| Sat 18:00 | Diego | Roboflow sets checked | his fork |
| Sat 20:00 | Akshat | ONNX server under 512 MB, PR | Render deploy |
| Sat 20:00 | Akshat | ROI-1555 email sent | Diego (more data, if yes) |
| Sat 20:00 | Diego | Roboflow fork + 50 web photos | his labelling |
| **Sat 21:00** | **Akanksha** | **mock-up design + `live/schedule_mockup.json`** | **Diego, the fab-lab session** |
| Sat 23:00 | Akanksha | fix wording, wireframe, Next Steps | Akshat, her result page, her pitch |
| Sat 24:00 | Diego | 100 labelled | his version |
| Sat 24:00 | Akshat | Cloudflare app runs locally | Cloudflare deploy |
| **Sun 11:00** | **Akshat** | **Render live** (needs his Hugging Face + Render logins) | Cloudflare deploy |
| **Sun 12:00** | **Akanksha** | **result page PR into `03_app/`** | **Akshat (wiring)** |
| Sun 13:00 | Diego | 100+ box sets turned into outlines | his version |
| Sun 13:00 | Akanksha | markers printed, one checked at 100 mm | the fab-lab session |
| **Sun 13:00** | **Akshat** | **Cloudflare live** (needs his Cloudflare login) | the result-page wiring |
| **Sun 14:00–17:00** | **everyone** | **fab-lab session** | Diego's test set, Akanksha's depth test |
| Sun 19:00 | Diego | fab-lab photos labelled, test set held out | his version |
| **Sun 20:00** | **Diego** | **Roboflow version 1** | training |
| Sun 20:00 | Akanksha | depth test | the team (depth on or off) |
| **Sun 21:00** | **Diego** | **training started** (overnight) | `best.pt` |
| **Sun 21:00** | **Akshat** | **result page wired in: app end to end** | the team |
| Sun 23:00 | Akanksha / Akshat | pitch outline / board + Monday plan | the team |
| **Sun 23:00** | **Diego, Akanksha** | **user-journey design reviewed: flow, site supervisor?** | **Akshat's UI layer** |
| **Mon 10:00** | **Diego** | **`best.pt` + `RESULTS.md`** | **Akshat** |
| Mon 12:00 | Akshat | real model live in the app | Thursday demo |
| **Tue 18:00** | **Akshat** | **UI layer: app restyled, site worker + engineer screens** | freeze Wed |
| Wed 18:00 | Akshat | architect + client screens, only if the core works | Thursday demo |
