// Runs before EVERY request: the password gate, checked on the server.
// Without the right cookie a visitor only gets the login page and the login API.

const PUBLIC_PATHS = ["/login", "/login.html", "/api/login", "/style.css"];

export async function onRequest(context) {
  const { request, env, next } = context;
  const url = new URL(request.url);

  if (PUBLIC_PATHS.includes(url.pathname)) {
    return next();
  }

  const cookie = request.headers.get("Cookie") || "";
  const token = cookie.match(/(?:^|;\s*)auth=([a-f0-9]+)/)?.[1];
  if (env.APP_PASSWORD && token && token === (await authToken(env.APP_PASSWORD))) {
    return next();
  }

  if (url.pathname.startsWith("/api/")) {
    return Response.json({ error: "Not logged in" }, { status: 401 });
  }
  return Response.redirect(new URL("/login", url), 302);
}

// The cookie holds a hash of the password, never the password itself
export async function authToken(password) {
  const bytes = new TextEncoder().encode(`concrete-evidence:${password}`);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(hash)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
