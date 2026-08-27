const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json" },
  });

async function sign(secret, payload) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(payload),
  );
  return `sha256=${[...new Uint8Array(signature)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("")}`;
}

function equal(a, b) {
  if (!a || !b || a.length !== b.length) return false;
  let result = 0;
  for (let index = 0; index < a.length; index += 1) {
    result |= a.charCodeAt(index) ^ b.charCodeAt(index);
  }
  return result === 0;
}

async function createAppJwt(env) {
  const { KJUR } = await import("jsrsasign");
  const now = Math.floor(Date.now() / 1000);
  return KJUR.jws.JWS.sign(
    "RS256",
    JSON.stringify({ alg: "RS256", typ: "JWT" }),
    JSON.stringify({ iat: now - 60, exp: now + 540, iss: env.GITHUB_APP_ID }),
    env.GITHUB_APP_PRIVATE_KEY,
  );
}

async function dispatch(event, env) {
  const jwt = await createAppJwt(env);
  const installationResponse = await fetch(
    `https://api.github.com/repos/${env.GITHUB_ORGANIZATION}/${env.CENTRAL_REPOSITORY}/installation`,
    { headers: { Authorization: `Bearer ${jwt}`, Accept: "application/vnd.github+json", "User-Agent": "central-owasp-webhook" } },
  );
  if (!installationResponse.ok) throw new Error(`Installation lookup failed: ${installationResponse.status}`);
  const installation = await installationResponse.json();
  const tokenResponse = await fetch(
    `https://api.github.com/app/installations/${installation.id}/access_tokens`,
    { method: "POST", headers: { Authorization: `Bearer ${jwt}`, Accept: "application/vnd.github+json", "User-Agent": "central-owasp-webhook" } },
  );
  if (!tokenResponse.ok) throw new Error(`Installation token failed: ${tokenResponse.status}`);
  const token = await tokenResponse.json();
  const dispatchResponse = await fetch(
    `https://api.github.com/repos/${env.GITHUB_ORGANIZATION}/${env.CENTRAL_REPOSITORY}/dispatches`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token.token}`, Accept: "application/vnd.github+json", "User-Agent": "central-owasp-webhook", "content-type": "application/json" },
      body: JSON.stringify({
        event_type: event.event === "pull_request" ? "repository-pull-request" : "repository-push",
        client_payload: {
          repository: event.repository.full_name,
          sha: event.event === "pull_request" ? event.pull_request.head.sha : event.after,
          event: event.event,
          pull_request_number: event.pull_request?.number,
        },
      }),
    },
  );
  if (!dispatchResponse.ok) throw new Error(`Dispatch failed: ${dispatchResponse.status}`);
}

export default {
  async fetch(request, env, context) {
    if (request.method !== "POST" || new URL(request.url).pathname !== "/github/webhook") return json({ error: "not found" }, 404);
    const raw = await request.text();
    const signature = await sign(env.GITHUB_WEBHOOK_SECRET, raw);
    if (!equal(signature, request.headers.get("x-hub-signature-256"))) return json({ error: "invalid signature" }, 401);
    const eventName = request.headers.get("x-github-event");
    if (!['push', 'pull_request'].includes(eventName)) return json({ accepted: false }, 202);
    const event = { ...JSON.parse(raw), event: eventName };
    if (!event.repository?.full_name?.startsWith(`${env.GITHUB_ORGANIZATION}/`)) return json({ error: "repository outside organization" }, 403);
    context.waitUntil(
      dispatch(event, env).catch((error) => {
        console.error(`GitHub dispatch failed: ${error.message}`);
      }),
    );
    return json({ accepted: true }, 202);
  },
};