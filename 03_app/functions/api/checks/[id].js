// GET /api/checks/<id>: one check with its schedule, the check result and every review decision so far
export async function onRequestGet({ params, env }) {
  const row = await env.DB.prepare("SELECT * FROM checks WHERE id = ?").bind(params.id).first();
  if (!row) return Response.json({ error: "No check with that id." }, { status: 404 });
  const { results: reviews } = await env.DB.prepare(
    "SELECT fault_index, decision, note, reviewer, created_at FROM reviews WHERE check_id = ? ORDER BY created_at",
  ).bind(params.id).all();
  const { schedule_json, check_json, photo_key, result_key, ...rest } = row;
  return Response.json({
    ...rest, photo_url: `/api/photos/${row.id}`, schedule: JSON.parse(schedule_json), check: JSON.parse(check_json),
    reviews,
  });
}
