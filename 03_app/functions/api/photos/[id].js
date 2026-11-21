// GET /api/photos/<id>: the checked photo (faces blurred, outlines drawn), read back from R2.
// Behind the password like everything else.
export async function onRequestGet({ params, env }) {
  if (!/^[0-9a-f-]{36}$/.test(params.id)) return new Response("Not found", { status: 404 });
  const object = await env.BUCKET.get(`checks/${params.id}/checked.jpg`);
  if (!object) return new Response("Not found", { status: 404 });
  return new Response(object.body, {
    headers: { "Content-Type": "image/jpeg", "Cache-Control": "private, max-age=3600" },
  });
}
