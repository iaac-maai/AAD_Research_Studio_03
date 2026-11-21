// Concrete Evidence page: send a photo to /api/check, show the result, save each person's decision.

const EXAMPLE_SCHEDULE = {
  element: "Column C1",
  column_mm: [400, 400],
  cover_mm: 30,
  clear_height_mm: 3000,
  ductility: "DCM",
  bar_diameter_mm: 16,
  bar_count: 3,
  bar_spacing_mm: 155,
  tie_diameter_mm: 8,
  tie_spacing_mm: { end: 100, middle: 200 },
  spacing_tol_mm: 10,
  diameter_tol_mm: 4,
  hook_angle: 135,
  hook_tail_factor: 10,
};
const MAX_SIDE = 2048; // photos are shrunk to this before upload: faster, and enough for the model
const $ = (id) => document.getElementById(id);
let current = null; // the check on screen

$("schedule").value = JSON.stringify(EXAMPLE_SCHEDULE, null, 2);
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

$("check-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = $("photo").files[0];
  if (!file) return say($("status"), "Choose a photo first.", "error");
  try { JSON.parse($("schedule").value); } catch {
    return say($("status"), "The schedule isn't valid JSON. Check the brackets and commas.", "error");
  }
  $("submit").disabled = true;
  const body = new FormData();
  body.append("photo", await shrink(file), file.name.replace(/\.\w+$/, "") + ".jpg");
  body.append("schedule", $("schedule").value);
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

  $("fixes").replaceChildren(...(c.fixes?.length ? c.fixes : ["No faults found. A person still confirms before the pour."])
    .map((t) => Object.assign(document.createElement("li"), { textContent: t })));

  const latest = new Map(current.reviews.map((r) => [r.fault_index, r]));
  const faults = (c.checks || []).map((x, i) => ({ ...x, i })).filter((x) => x.status === "fail");
  $("faults").replaceChildren(...faults.map((f) => {
    const li = document.createElement("li");
    const title = document.createElement("strong"); title.textContent = label(f.check);
    const detail = document.createElement("p"); detail.textContent = f.detail;
    const choice = document.createElement("div"); choice.className = "choice";
    for (const d of ["confirm", "reject"]) {
      const id = `f${f.i}-${d}`;
      const input = Object.assign(document.createElement("input"), { type: "radio", name: `f${f.i}`, value: d, id });
      input.checked = latest.get(f.i)?.decision === d;
      const lab = Object.assign(document.createElement("label"), { htmlFor: id, textContent: d === "confirm" ? "Confirm: it's wrong on site" : "Reject: the app is wrong" });
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
    li.textContent = `${label(x.check)}: ${x.status}. ${x.detail || ""}`;
    return li;
  }));
  say($("review-status"), "");
  $("result").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function sendReview(signOff) {
  if (!current) return;
  const reviewer = $("reviewer").value.trim();
  if (!reviewer) return say($("review-status"), "Write your name first.", "error");
  try { localStorage.setItem("ce-reviewer", reviewer); } catch { /* fine */ }
  const decisions = [...document.querySelectorAll("#faults input[type=radio]:checked")].map((r) => {
    const i = Number(r.name.slice(1));
    return { fault_index: i, decision: r.value, note: document.querySelector(`#faults .note[data-fault="${i}"]`)?.value || "" };
  });
  const res = await fetch(`/api/reviews/${current.id}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer, decisions, sign_off: signOff }),
  });
  const data = await res.json();
  if (!res.ok) return say($("review-status"), data.error || "Not saved. Try again.", "error");
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
