// GET /api/checks: the 30 most recent checks, newest first, read from D1
export async function onRequestGet({ env }) {
  const { results } = await env.DB.prepare(
    `SELECT id, created_at, element, face, zone, pieces, faults, scale_source, review_status, signed_off_by
     FROM checks ORDER BY created_at DESC LIMIT 30`,
  ).all();
  return Response.json(results);
}
