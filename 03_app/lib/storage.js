// Where the checked photo and the full result go: R2 when the BUCKET binding exists, else the `files` table in D1.
// D1 holds up to 2 MB per value; a checked photo is about 100 kB. Switching back to R2 = add the [[r2_buckets]]
// binding in wrangler.toml again, nothing else.

const D1_LIMIT = 1_900_000;

export async function putFile(env, key, bytes, contentType) {
  if (env.BUCKET) {
    await env.BUCKET.put(key, bytes, { httpMetadata: { contentType } });
    return;
  }
  if (bytes.byteLength > D1_LIMIT) return; // too big for one D1 value: skipped (the row in `checks` still has the check)
  await env.DB.prepare("INSERT OR REPLACE INTO files (key, content_type, body, created_at) VALUES (?, ?, ?, ?)")
    .bind(key, contentType, bytes, new Date().toISOString()).run();
}

export async function getFile(env, key) {
  if (env.BUCKET) {
    const object = await env.BUCKET.get(key);
    return object ? { body: object.body, contentType: object.httpMetadata?.contentType } : null;
  }
  const row = await env.DB.prepare("SELECT content_type, body FROM files WHERE key = ?").bind(key).first();
  return row ? { body: new Uint8Array(row.body), contentType: row.content_type } : null;
}
