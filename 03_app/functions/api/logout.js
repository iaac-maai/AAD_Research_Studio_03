// POST /api/logout: clears the login cookie
export async function onRequestPost({ request }) {
  return new Response(null, {
    status: 302,
    headers: { Location: new URL("/login", request.url).toString(), "Set-Cookie": "auth=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0" },
  });
}
