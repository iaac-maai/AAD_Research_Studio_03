// Concrete Evidence page: send a photo to /api/check, show the result, save each person's decision.

const EXAMPLE_SCHEDULE = {
  element: "Column C1",
  column_mm: [400, 400],
  cover_mm: 30,
  clear_height_mm: 3000,
  ductility: "DCM",
  bar_diameter_mm: 12, // the common column bar on site; the worker picks the real size in the menu
  bar_count: 3,
  bar_spacing_mm: 155,
  tie_diameter_mm: 8,
  tie_spacing_mm: { end: 90, middle: 180 }, // EC8 DCM with Ø12 bars: end zone at most 8 × 12 = 96 mm
  spacing_tol_mm: 25,
  diameter_tol_mm: 5,
  hook_angle: 135,
  hook_tail_factor: 10,
};
const MAX_SIDE = 2048; // photos are shrunk to this before upload: faster, and enough for the model
const $ = (id) => document.getElementById(id);
let current = null; // the check on screen

$("schedule").value = JSON.stringify(EXAMPLE_SCHEDULE, null, 2);

// The bar and tie size drop-downs write into the schedule, so the JSON and the menus never disagree
function readSchedule() {
  try { return JSON.parse($("schedule").value); } catch { return null; }
}
function withSizes(s) {
  return { ...s, bar_diameter_mm: Number($("bar-size").value), tie_diameter_mm: Number($("tie-size").value) };
}
function showSchedule(s) {
  const dims = Array.isArray(s.column_mm) ? ` · ${s.column_mm.join(" × ")}` : "";
  $("schedule-summary").textContent =
    `Bar bending schedule · ${s.element || "Element"}${dims} · Ø${s.bar_diameter_mm} bars · Ø${s.tie_diameter_mm || "?"} ties`;
}
for (const id of ["bar-size", "tie-size"]) {
  $(id).addEventListener("change", () => {
    const s = readSchedule();
    if (!s) return; // invalid JSON: the menus still win when the photo is sent
    const next = withSizes(s);
    $("schedule").value = JSON.stringify(next, null, 2);
    showSchedule(next);
  });
}
$("schedule").addEventListener("change", () => {
  const s = readSchedule();
  if (!s) return;
  const pick = (sel, v) => { if ([...$(sel).options].some((o) => Number(o.value) === Number(v))) $(sel).value = String(Number(v)); };
  pick("bar-size", s.bar_diameter_mm);
  pick("tie-size", s.tie_diameter_mm);
  showSchedule(withSizes(s));
});
showSchedule(EXAMPLE_SCHEDULE);

try { $("reviewer").value = localStorage.getItem("ce-reviewer") || ""; } catch { /* private window */ }

$("photo").addEventListener("change", () => {
  const f = $("photo").files[0];
  if (!f) { $("preview").hidden = true; return; }
  $("preview").src = URL.createObjectURL(f);
  $("preview").hidden = false;
});

function say(el, text, kind = "") {
  el.textContent = text;
  el.className = `status ${kind}`;
  el.hidden = !text;
}

async function shrink(file) {
  const bmp = await createImageBitmap(file);
  const s = Math.min(1, MAX_SIDE / Math.max(bmp.width, bmp.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bmp.width * s);
  canvas.height = Math.round(bmp.height * s);
  canvas.getContext("2d").drawImage(bmp, 0, 0, canvas.width, canvas.height);
  return new Promise((ok) => canvas.toBlob(ok, "image/jpeg", 0.9));
}

// Where the photo was taken, from its EXIF GPS, rounded to about 1 km: enough to pick the town and the seismic
// rules, not to point at the site. Used only for this check (the app never stores the coordinates). null if none.
async function photoGps(file) {
  try {
    const v = new DataView(await file.slice(0, 256 * 1024).arrayBuffer());
    if (v.getUint16(0) !== 0xffd8) return null; // not a JPEG
    for (let p = 2; p + 4 < v.byteLength;) {
      const marker = v.getUint16(p), size = v.getUint16(p + 2);
      if (marker === 0xffe1 && v.getUint32(p + 4) === 0x45786966) return readGps(v, p + 10); // "Exif"
      if ((marker & 0xff00) !== 0xff00 || marker === 0xffda) return null;
      p += 2 + size;
    }
  } catch { /* unreadable EXIF: no GPS */ }
  return null;
}
function readGps(v, tiff) {
  const le = v.getUint16(tiff) === 0x4949;
  const u16 = (o) => v.getUint16(tiff + o, le), u32 = (o) => v.getUint32(tiff + o, le);
  const tags = (ifd) => {
    const out = {};
    for (let i = 0, n = u16(ifd); i < n; i++) { const e = ifd + 2 + i * 12; out[u16(e)] = e; }
    return out;
  };
  const gpsAt = tags(u32(4))[0x8825];
  if (!gpsAt) return null;
  const g = tags(u32(gpsAt + 8));
  const deg = (e) => { const o = u32(e + 8); let d = 0; for (let k = 0; k < 3; k++) d += u32(o + 8 * k) / (u32(o + 8 * k + 4) || 1) / 60 ** k; return d; };
  const ref = (e) => String.fromCharCode(v.getUint8(tiff + e + 8));
  if (!g[2] || !g[4]) return null;
  const lat = deg(g[2]) * (g[1] && ref(g[1]) === "S" ? -1 : 1), lon = deg(g[4]) * (g[3] && ref(g[3]) === "W" ? -1 : 1);
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || (lat === 0 && lon === 0) || Math.abs(lat) > 90 || Math.abs(lon) > 180) return null;
  return { lat: Math.round(lat * 100) / 100, lon: Math.round(lon * 100) / 100 };
}

$("check-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = $("photo").files[0];
  if (!file) return say($("status"), "Choose a photo first.", "error");
  const parsed = readSchedule();
  if (!parsed) return say($("status"), "The schedule isn't valid JSON. Check the brackets and commas.", "error");
  const schedule = withSizes(parsed);
  if (!schedule.city && schedule.lat == null) {
    const gps = await photoGps(file); // the shrunk upload has no EXIF, so read it from the original here
    if (gps) Object.assign(schedule, gps);
  }
  $("submit").disabled = true;
  const body = new FormData();
  body.append("photo", await shrink(file), file.name.replace(/\.\w+$/, "") + ".jpg");
  body.append("schedule", JSON.stringify(schedule));
  body.append("zone", $("zone").value);
  body.append("face", $("face").value);

  const started = Date.now();
  try {
    for (let attempt = 1; ; attempt++) {
      say($("status"), attempt === 1 ? "Checking the photo…" : "The model is waking up, about one minute. Still trying…", "busy");
      const res = await fetch("/api/check", { method: "POST", body });
      if (res.status === 401) { location.href = "/login"; return; }
      const data = await res.json();
      if (res.status === 503 && data.waking && Date.now() - started < 180000) {
        await new Promise((r) => setTimeout(r, 10000));
        continue;
      }
      if (!res.ok) { say($("status"), data.error || "Something went wrong. Try again.", "error"); return; }
      say($("status"), "");
      await openCheck(data.id);
      loadHistory();
      return;
    }
  } catch {
    say($("status"), "No connection to the app. Check your internet and try again.", "error");
  } finally {
    $("submit").disabled = false;
  }
});

const STATUS_LABEL = { pending: "Waiting for review", reviewed: "Reviewed", signed_off: "Signed off" };
const CHECK_LABEL = {
  bar_count: "Number of bars", bar_size: "Bar size", bar_spacing: "Bar spacing", tie_spacing: "Tie spacing",
  hooks: "Hooks", schedule_vs_code: "Schedule against Eurocode 8", ties: "Ties",
};
const label = (name) => CHECK_LABEL[name] || name.replace(/_/g, " ");

async function openCheck(id) {
  const res = await fetch(`/api/checks/${id}`);
  if (!res.ok) return;
  current = await res.json();
  const c = current.check;
  $("result").hidden = false;
  $("result-title").textContent = `${current.element || "Element"}, face ${current.face || "?"}, ${current.zone} zone`;
  const badge = $("result-badge");
  badge.textContent = STATUS_LABEL[current.review_status] || current.review_status;
  badge.dataset.state = current.review_status;
  const when = new Date(current.created_at).toLocaleString();
  const scale = c.scale?.source === "markers" ? "measured with the markers"
    : c.scale?.source ? "scale estimated from the bar size (no markers seen)" : "no scale";
  $("result-meta").textContent = `${when} · ${current.pieces} pieces found · ${current.faults} fault(s) · ${scale}` +
    (current.signed_off_by ? ` · signed off by ${current.signed_off_by}` : "");
  $("result-photo").src = current.photo_url;
  showPieces(current);

  // The verdict line, as in the design: NOT READY (faults left), READY (none), SIGNED OFF
  const verdict = $("verdict");
  const nFaults = Number(current.faults || 0);
  verdict.dataset.state = current.review_status === "signed_off" ? "signed_off" : nFaults ? "fail" : "pass";
  verdict.textContent = current.review_status === "signed_off" ? "Signed off" : nFaults ? "Not ready" : "Ready";
  $("headline").textContent = current.review_status === "signed_off" ? "Signed off: ready for the pour"
    : nFaults ? `${nFaults} ${nFaults === 1 ? "thing" : "things"} to fix` : "All checks pass";

  const two = (n) => String(n).padStart(2, "0");
  $("fixes").replaceChildren(...(c.fixes?.length
    ? c.fixes.map((t, i) => {
      const li = document.createElement("li");
      li.append(Object.assign(document.createElement("span"), { className: "num", textContent: two(i + 1) }),
        Object.assign(document.createElement("span"), { textContent: t }));
      return li;
    })
    : [Object.assign(document.createElement("li"), { className: "none", textContent: "No faults found. A person still confirms before the pour." })]));

  const latest = new Map(current.reviews.map((r) => [r.fault_index, r]));
  const faults = (c.checks || []).map((x, i) => ({ ...x, i })).filter((x) => x.status === "fail");
  $("faults").replaceChildren(...faults.map((f, n) => {
    const li = document.createElement("li");
    li.append(Object.assign(document.createElement("span"), { className: "num", textContent: two(n + 1) }));
    const title = document.createElement("strong"); title.textContent = label(f.check);
    const detail = document.createElement("p"); detail.textContent = f.detail;
    const choice = document.createElement("div"); choice.className = "choice";
    for (const d of ["confirm", "reject"]) {
      const id = `f${f.i}-${d}`;
      const input = Object.assign(document.createElement("input"), { type: "radio", name: `f${f.i}`, value: d, id });
      input.checked = latest.get(f.i)?.decision === d;
      const lab = Object.assign(document.createElement("label"), { htmlFor: id, textContent: d === "confirm" ? "Confirm: wrong on site" : "Reject: the app is wrong" });
      choice.append(input, lab);
    }
    const note = Object.assign(document.createElement("input"), { type: "text", placeholder: "Note (optional)", maxLength: 500 });
    note.dataset.fault = f.i; note.className = "note";
    note.value = latest.get(f.i)?.note || "";
    note.setAttribute("aria-label", `Note on ${label(f.check)}`);
    const by = latest.get(f.i);
    const meta = document.createElement("p"); meta.className = "muted";
    meta.textContent = by ? `Last decision: ${by.decision} by ${by.reviewer}` : "";
    li.append(title, detail, choice, note, meta);
    return li;
  }));
  if (!faults.length) $("faults").replaceChildren(Object.assign(document.createElement("li"), { textContent: "No faults to review.", className: "muted" }));

  $("all-checks").replaceChildren(...(c.checks || []).map((x) => {
    const li = document.createElement("li");
    li.dataset.state = x.status;
    li.append(Object.assign(document.createElement("span"), { textContent: label(x.check) }),
      Object.assign(document.createElement("span"), { className: "res", textContent: x.status }));
    if (x.detail) li.append(Object.assign(document.createElement("span"), { className: "detail", textContent: x.detail }));
    return li;
  }));
  say($("review-status"), "");
  $("result").scrollIntoView({ behavior: "smooth", block: "start" });
}

// ---- Pieces: colour by angle, and measurements ----------------------------------------------------------------
// Angles are measured against the main bar direction (the photo may be tilted), from 0 (along) to 90 (across).
const BANDS = [
  { key: "along", label: "Along the main bars", range: "0–15°", colour: "#5aa9e6" },
  { key: "across", label: "Across, like ties", range: "75–90°", colour: "#f2b134" },
  { key: "diagonal", label: "Diagonal: a bend, a hook or a tilted bar", range: "15–75°", colour: "#e0569b" },
  { key: "unknown", label: "No direction (outline too small)", range: "", colour: "#9a9a95" },
];
const BAND = Object.fromEntries(BANDS.map((b) => [b.key, b]));
const SIZES = [6, 8, 10, 12, 14, 16, 20, 25, 28, 32, 40];
const PIECE_LABEL = { bar: "Bar", tie: "Tie", stirrup: "Tie", hook_90: "Hook 90°", hook_135: "Hook 135°" };
const SVG = "http://www.w3.org/2000/svg";

// The main direction: the average of the bars' angles, on the doubled angle so 179° and 1° agree
function mainAngle(dets) {
  const bars = dets.filter((d) => d.class === "bar" && d.angle_deg != null);
  if (!bars.length) return 90; // no bars: assume an upright column photo
  let x = 0, y = 0;
  for (const b of bars) { const r = (b.angle_deg * Math.PI) / 90; x += Math.cos(r); y += Math.sin(r); }
  return ((Math.atan2(y, x) * 90) / Math.PI + 180) % 180;
}
const gap = (a, b) => { const g = Math.abs(a - b) % 180; return Math.min(g, 180 - g); };
function band(d, main) {
  // a blob about as wide as it is long has no meaningful direction
  if (d.angle_deg == null || !d.length_px || d.length_px < 1.5 * (d.width_px || 0)) return "unknown";
  const g = gap(d.angle_deg, main);
  return g <= 15 ? "along" : g >= 75 ? "across" : "diagonal";
}

function showPieces(c) {
  const dets = c.detections || [];
  const mm = c.mm_per_px || c.check?.scale?.mm_per_px || null; // without markers the scale is only in check.scale
  const main = mainAngle(dets);
  const s = c.schedule || {};
  const tol = Number(s.diameter_tol_mm || 4);
  const rows = dets.map((d) => ({ ...d, band: band(d, main), rel: d.angle_deg == null ? null : gap(d.angle_deg, main) }));

  // Overlay: one outline per piece, filled in its band's colour, drawn in the photo's own pixels
  const layer = $("angle-layer");
  const img = $("result-photo");
  const draw = () => {
    layer.setAttribute("viewBox", `0 0 ${img.naturalWidth || 1} ${img.naturalHeight || 1}`);
    layer.replaceChildren(...rows.flatMap((d) => {
      const colour = BAND[d.band].colour;
      const shapes = [];
      if (d.polygon?.length > 2) {
        const p = document.createElementNS(SVG, "polygon");
        p.setAttribute("points", d.polygon.map(([x, y]) => `${x},${y}`).join(" "));
        p.setAttribute("fill", colour); p.setAttribute("fill-opacity", "0.45");
        p.setAttribute("stroke", colour); p.setAttribute("stroke-width", "3"); p.setAttribute("vector-effect", "non-scaling-stroke");
        shapes.push(p);
        if (d.axis_px?.length > 1) { // the axis polyline, corners dotted: where the bar bends
          const l = document.createElementNS(SVG, "polyline");
          l.setAttribute("points", d.axis_px.map(([x, y]) => `${x},${y}`).join(" "));
          Object.entries({ fill: "none", stroke: "#ffffff", "stroke-width": 2, "vector-effect": "non-scaling-stroke" })
            .forEach(([k, v]) => l.setAttribute(k, v));
          shapes.push(l);
          for (const [x, y] of d.axis_px.slice(1, -1)) {
            const c = document.createElementNS(SVG, "circle");
            Object.entries({ cx: x, cy: y, r: Math.max(4, (d.thickness_px || 8) / 2), fill: "#ffffff" })
              .forEach(([k, v]) => c.setAttribute(k, v));
            shapes.push(c);
          }
        }
      } else if (d.centre_px && d.size_px) {
        const r = document.createElementNS(SVG, "rect");
        const [cx, cy] = d.centre_px, [w, h] = d.size_px;
        Object.entries({ x: cx - w / 2, y: cy - h / 2, width: w, height: h, fill: "none", stroke: colour, "stroke-width": 3, "vector-effect": "non-scaling-stroke" })
          .forEach(([k, v]) => r.setAttribute(k, v));
        shapes.push(r);
      }
      return shapes;
    }));
  };
  if (img.complete && img.naturalWidth) draw(); else img.addEventListener("load", draw, { once: true });

  const counts = Object.fromEntries(BANDS.map((b) => [b.key, rows.filter((r) => r.band === b.key).length]));
  $("angle-legend").replaceChildren(...BANDS.filter((b) => counts[b.key]).map((b) => {
    const li = document.createElement("li");
    const sw = Object.assign(document.createElement("span"), { className: "swatch" }); sw.style.background = b.colour;
    li.append(sw, Object.assign(document.createElement("span"), { textContent: `${b.label}${b.range ? ` (${b.range})` : ""}` }),
      Object.assign(document.createElement("span"), { className: "muted", textContent: ` · ${counts[b.key]}` }));
    return li;
  }));
  setView(currentView);

  // Measurements: length and width in mm, and each width against the size chosen in the menus
  const markers = c.check?.scale?.source === "markers";
  $("measure-note").textContent = !dets.length ? "No pieces found in this photo."
    : !mm ? "No scale in this photo, so lengths are in pixels."
      : markers ? `Scale from the markers: ${mm.toFixed(3)} mm per pixel. Widths are a real measurement of each bar's size.`
        : `No markers seen: the scale (${mm.toFixed(3)} mm per pixel) comes from the bar size chosen, so widths only show which bars differ from the others.`;
  const fmt = (px) => (px == null ? "—" : mm ? `${Math.round(px * mm)} mm` : `${Math.round(px)} px`);
  $("measure-rows").replaceChildren(...rows.map((d) => {
    const tr = document.createElement("tr");
    const isTie = d.class === "tie" || d.class === "stirrup";
    const isHook = String(d.class).startsWith("hook");
    const want = isTie ? Number(s.tie_diameter_mm || 8) : Number(s.bar_diameter_mm || 12);
    let verdict = "—", state = "";
    const thick = d.thickness_px ?? d.width_px; // measured across the axis when there is one
    if (mm && thick && !isHook) {
      const w = thick * mm;
      const nearest = SIZES.reduce((a, b) => (Math.abs(b - w) < Math.abs(a - w) ? b : a));
      if (Math.abs(w - want) <= tol) { verdict = `Matches Ø${want}`; state = "ok"; }
      else { verdict = `Looks like Ø${nearest}, not Ø${want}`; state = "bad"; }
    }
    const dir = document.createElement("td");
    const sw = Object.assign(document.createElement("span"), { className: "swatch" }); sw.style.background = BAND[d.band].colour;
    dir.append(sw, document.createTextNode(BAND[d.band].label.split(":")[0]));
    const v = Object.assign(document.createElement("td"), { textContent: verdict }); v.dataset.state = state;
    tr.append(
      Object.assign(document.createElement("td"), { textContent: d.id }),
      Object.assign(document.createElement("td"), { textContent: PIECE_LABEL[d.class] || d.class }),
      dir,
      Object.assign(document.createElement("td"), { className: "num", textContent: d.rel == null ? "—" : `${Math.round(d.rel)}°` }),
      Object.assign(document.createElement("td"), { className: "num", textContent: fmt(d.axis_length_px ?? d.length_px) }),
      Object.assign(document.createElement("td"), { className: "num", textContent: isHook ? "—" : fmt(d.thickness_px ?? d.width_px) }),
      Object.assign(document.createElement("td"), { textContent: d.segments_px?.length ? d.segments_px.map((p) => fmt(p).replace(" mm", "")).join(" + ") + (mm ? " mm" : " px") : "—" }),
      Object.assign(document.createElement("td"), { className: "num", textContent: d.bends_deg?.length ? d.bends_deg.map((b) => `${Math.round(b)}°`).join(", ") : "—" }),
      v,
    );
    return tr;
  }));
}

let currentView = "faults";
function setView(view) {
  currentView = view;
  const angles = view === "angles";
  $("angle-layer").toggleAttribute("hidden", !angles); // an <svg> has no .hidden property
  $("angle-legend").hidden = !angles;
  $("view-faults").setAttribute("aria-pressed", String(!angles));
  $("view-angles").setAttribute("aria-pressed", String(angles));
}
$("view-faults").addEventListener("click", () => setView("faults"));
$("view-angles").addEventListener("click", () => setView("angles"));

async function sendReview(signOff) {
  if (!current) return;
  const reviewer = $("reviewer").value.trim();
  if (!reviewer) return say($("review-status"), "Write your name first.", "error");
  try { localStorage.setItem("ce-reviewer", reviewer); } catch { /* fine */ }
  const decisions = [...document.querySelectorAll("#faults input[type=radio]:checked")].map((r) => {
    const i = Number(r.name.slice(1));
    return { fault_index: i, decision: r.value, note: document.querySelector(`#faults .note[data-fault="${i}"]`)?.value || "" };
  });
  let res, data = {};
  try {
    res = await fetch(`/api/reviews/${current.id}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reviewer, decisions, sign_off: signOff }),
    });
  } catch {
    return say($("review-status"), "Not saved: no connection. Check the signal and try again.", "error");
  }
  try { data = await res.json(); } catch { /* an error page, not JSON */ }
  if (res.status === 401) return say($("review-status"), "Not saved: you were signed out. Sign in again, then save.", "error");
  if (!res.ok) return say($("review-status"), data.error || `Not saved (error ${res.status}). Try again.`, "error");
  await openCheck(current.id);
  say($("review-status"), signOff ? `Signed off by ${reviewer}.` : `Saved. ${STATUS_LABEL[data.review_status]}.`, "ok");
  loadHistory();
}
$("save-review").addEventListener("click", () => sendReview(false));
$("sign-off").addEventListener("click", () => sendReview(true));

async function loadHistory() {
  const res = await fetch("/api/checks");
  if (!res.ok) return;
  const rows = await res.json();
  if (!rows.length) {
    $("history-list").replaceChildren(Object.assign(document.createElement("li"), { textContent: "No checks yet. Check your first photo above.", className: "muted" }));
    return;
  }
  $("history-list").replaceChildren(...rows.map((r) => {
    const li = document.createElement("li");
    const b = document.createElement("button"); b.type = "button"; b.className = "history-item";
    const t = document.createElement("span"); t.textContent = `${r.element || "Element"} · face ${r.face || "?"} · ${r.zone}`;
    const m = document.createElement("span"); m.className = "muted";
    m.textContent = `${new Date(r.created_at).toLocaleString()} · ${r.faults} fault(s)`;
    const s = document.createElement("span"); s.className = "badge"; s.dataset.state = r.review_status;
    s.textContent = STATUS_LABEL[r.review_status] || r.review_status;
    b.append(t, m, s);
    b.addEventListener("click", () => openCheck(r.id));
    li.append(b);
    return li;
  }));
}
loadHistory();
