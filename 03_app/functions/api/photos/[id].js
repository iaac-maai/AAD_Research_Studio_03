import { getFile } from "../../../lib/storage.js";

// GET /api/photos/<id>: the checked photo (faces blurred, outlines drawn), from R2 or, without R2, from D1.
// Behind the password like everything else.
export async function onRequestGet({ params, env }) {
  if (!/^[0-9a-f-]{36}$/.test(params.id)) return new Response("Not found", { status: 404 });
  const file = await getFile(env, `checks/${params.id}/checked.jpg`);
  if (!file) return new Response("Not found", { status: 404 });
  return new Response(file.body, {
    headers: { "Content-Type": "image/jpeg", "Cache-Control": "private, max-age=3600" },
  });
}
