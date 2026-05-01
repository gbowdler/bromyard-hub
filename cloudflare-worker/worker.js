/**
 * Bromyard Depot — manifest relay worker
 *
 * Receives a POST of manifest CSV from the PWA and commits it to
 * data/pending-manifest.csv in the bromyard-hub repo, which triggers
 * the generate-packing-sheet GitHub Actions workflow.
 *
 * Environment variables (set in Cloudflare dashboard, never in code):
 *   GITHUB_PAT     — fine-grained PAT, bromyard-hub repo, contents: read+write
 *   SHARED_SECRET  — random string also set as VITE_PIPELINE_SECRET in the PWA
 */

const REPO    = "gbowdler/bromyard-hub";
const FILE    = "data/pending-manifest.csv";
const GH_API  = `https://api.github.com/repos/${REPO}/contents/${FILE}`;

// Origins allowed to call this worker
const ALLOWED_ORIGINS = [
  "https://gbowdler.github.io",
  "http://localhost",        // local dev
  "http://127.0.0.1",
];

function corsHeaders(origin) {
  const allowed = ALLOWED_ORIGINS.some(o => origin && origin.startsWith(o))
    ? origin
    : ALLOWED_ORIGINS[0];
  return {
    "Access-Control-Allow-Origin":  allowed,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Api-Key",
  };
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";

    // Handle CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }

    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405 });
    }

    // Validate shared secret
    const key = request.headers.get("X-Api-Key");
    if (!env.SHARED_SECRET || key !== env.SHARED_SECRET) {
      return new Response("Unauthorized", { status: 401 });
    }

    // Read and validate CSV body
    const csv = await request.text();
    if (!csv || !csv.trimStart().startsWith("Bale Number")) {
      return new Response("Invalid CSV — expected Bale Number header", { status: 400 });
    }

    // Fetch current file SHA (required by GitHub API to update an existing file)
    let sha;
    const getResp = await fetch(GH_API, {
      headers: {
        "Authorization": `Bearer ${env.GITHUB_PAT}`,
        "User-Agent":    "BromyardHub-Worker/1.0",
        "Accept":        "application/vnd.github+json",
      },
    });
    if (getResp.ok) {
      const current = await getResp.json();
      sha = current.sha;
    } else if (getResp.status !== 404) {
      // 404 = file doesn't exist yet (first ever load) — that's fine
      const err = await getResp.text();
      console.error("GitHub GET error:", err);
      return new Response("GitHub API error (GET)", {
        status: 502, headers: corsHeaders(origin)
      });
    }

    // Base64-encode the CSV (GitHub Contents API requires this)
    const encoded = btoa(unescape(encodeURIComponent(csv)));

    const payload = {
      message: `Manifest upload — ${new Date().toISOString().slice(0, 10)}`,
      content: encoded,
      ...(sha ? { sha } : {}),
    };

    const putResp = await fetch(GH_API, {
      method:  "PUT",
      headers: {
        "Authorization": `Bearer ${env.GITHUB_PAT}`,
        "User-Agent":    "BromyardHub-Worker/1.0",
        "Accept":        "application/vnd.github+json",
        "Content-Type":  "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (putResp.ok) {
      return new Response("OK", { status: 200, headers: corsHeaders(origin) });
    }

    const errBody = await putResp.text();
    console.error("GitHub PUT error:", errBody);
    return new Response("GitHub API error (PUT)", {
      status: 502, headers: corsHeaders(origin)
    });
  },
};
