import { getFile } from "../../../lib/storage.js";

// GET /api/checks/<id>: one check with its schedule, the check result, every review decision so far, and each piece
// the model found (outline, direction, length and width), so the page can colour pieces by angle and list measurements
export async function onRequestGet({ params, env }) {
  const row = await env.DB.prepare("SELECT * FROM checks WHERE id = ?").bind(params.id).first();
  if (!row) return Response.json({ error: "No check with that id." }, { status: 404 });
  const { results: reviews } = await env.DB.prepare(
    "SELECT fault_index, decision, note, reviewer, created_at FROM reviews WHERE check_id = ? ORDER BY created_at",
  ).bind(params.id).all();
  const { schedule_json, check_json, photo_key, result_key, ...rest } = row;
  return Response.json({
    ...rest, photo_url: `/api/photos/${row.id}`, schedule: JSON.parse(schedule_json), check: JSON.parse(check_json),
    reviews, ...(await pieces(env, result_key)),
  });
}

// The pieces from the stored result JSON, trimmed to what the page draws. A missing or unreadable result gives none.
async function pieces(env, key) {
  const none = { detections: [], mm_per_px: null };
  const file = key ? await getFile(env, key) : null;
  if (!file) return none;
  try {
    const text = file.body instanceof Uint8Array ? new TextDecoder().decode(file.body) : await new Response(file.body).text();
    const result = JSON.parse(text);
    const detections = (result.detections || []).map((d) => ({
      id: d.track_id, class: d.class, conf: d.conf, angle_deg: d.angle_deg ?? null,
      length_px: d.length_px ?? null, width_px: d.width_px ?? null, centre_px: d.centre_px, size_px: d.size_px,
      polygon: d.polygon || null,
      axis_px: d.axis_px || null, segments_px: d.segments_px || null, bends_deg: d.bends_deg || null,
      thickness_px: d.thickness_px ?? null, axis_length_px: d.axis_length_px ?? null,
    }));
    return { detections, mm_per_px: result.mm_per_px ?? null };
  } catch {
    return none;
  }
}
