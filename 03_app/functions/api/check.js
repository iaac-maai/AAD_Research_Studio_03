// POST /api/check: one photo of one column face is checked.
// Form fields: photo (a JPEG or PNG file), schedule (the bar bending schedule as JSON text), zone ("end" or
// "middle"), face (e.g. "A").
// 1. send it to the model server, 2. store the checked photo (faces blurred) and the full result in R2,
// 3. store one row in D1, 4. answer the page. The original upload is never stored.

const MAX_BYTES = 8 * 1024 * 1024;
const ZONES = ["end", "middle"];

export async function onRequestPost({ request, env }) {
  const form = await request.formData();
  const file = form.get("photo");
  if (!file || typeof file === "string") {
    return Response.json({ error: "Choose a photo of the column face first." }, { status: 400 });
  }
  if (file.size > MAX_BYTES) {
    return Response.json({ error: "That photo is larger than 8 MB. Take it again at a lower resolution." }, { status: 413 });
  }
  const scheduleText = String(form.get("schedule") || "");
  let schedule;
  try {
    schedule = JSON.parse(scheduleText);
  } catch {
    return Response.json({ error: "The bar bending schedule isn't valid JSON. Check the brackets and commas." }, { status: 400 });
  }
  const zone = ZONES.includes(form.get("zone")) ? form.get("zone") : "end";
  const face = String(form.get("face") || "").slice(0, 20);
  const bytes = new Uint8Array(await file.arrayBuffer());

  // 1. Ask the model server
  let result;
  try {
    result = await callModel(env, [toBase64(bytes), JSON.stringify(schedule), zone, face]);
  } catch (err) {
    // Usually the free Render server is asleep and still starting: the page waits and tries again
    return Response.json({ waking: true, error: "The model is waking up. This takes about a minute.", detail: String(err) },
      { status: 503 });
  }
  if (result.error) {
    return Response.json({ error: `The model server could not check this photo: ${result.error}` }, { status: 400 });
  }

  // 2. Store the checked photo and the full result in R2
  const id = crypto.randomUUID();
  const createdAt = new Date().toISOString();
  const photoKey = `checks/${id}/checked.jpg`;
  const resultKey = `checks/${id}/result.json`;
  const annotated = fromBase64(result.annotated_jpg_base64 || "");
  delete result.annotated_jpg_base64;
  await env.BUCKET.put(photoKey, annotated, { httpMetadata: { contentType: "image/jpeg" } });
  await env.BUCKET.put(resultKey, JSON.stringify(result), { httpMetadata: { contentType: "application/json" } });

  // 3. One row in D1. The "?" placeholders keep the user's text out of the SQL
  const check = result.check || {};
  await env.DB.prepare(
    `INSERT INTO checks (id, created_at, element, face, zone, file_name, photo_key, result_key, model, pieces, faults,
       scale_source, schedule_json, check_json)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
  ).bind(
    id, createdAt, check.element || schedule.element || null, face || null, zone, file.name || null, photoKey, resultKey,
    result.model?.weights || null, (result.detections || []).length, Number(check.faults || 0),
    check.scale?.source || null, JSON.stringify(schedule), JSON.stringify(check),
  ).run();

  // 4. Answer the page
  return Response.json({
    id, created_at: createdAt, photo_url: `/api/photos/${id}`, check, counts: result.counts,
    markers_seen: result.markers_seen, mm_per_px: result.mm_per_px, faces_blurred: result.faces_blurred,
    model: result.model, review_status: "pending",
  });
}

// Gradio's HTTP API: start a job, then read its result from the event stream
async function callModel(env, data) {
  const base = `${env.MODEL_URL}/gradio_api/call/${env.MODEL_API_NAME}`;
  const started = await fetchWithTimeout(base, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ data }),
  }, 45000);
  if (!started.ok) throw new Error(`Model server answered ${started.status}`);
  const { event_id } = await started.json();

  const stream = await fetchWithTimeout(`${base}/${event_id}`, {}, 90000);
  const text = await stream.text(); // "event: complete\ndata: [ {...} ]"
  const complete = text.split("event: complete")[1];
  if (!complete) throw new Error(`No result from the model server: ${text.slice(0, 200)}`);
  return JSON.parse(complete.split("data:")[1].trim())[0];
}

async function fetchWithTimeout(url, options = {}, ms = 60000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

function toBase64(bytes) {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  }
  return btoa(binary);
}

function fromBase64(b64) {
  const binary = atob(b64);
  const out = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) out[i] = binary.charCodeAt(i);
  return out;
}
