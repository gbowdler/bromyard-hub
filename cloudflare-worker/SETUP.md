# Depot Pipeline — Setup Guide

One-time setup to wire the PWA → Cloudflare Worker → GitHub Actions pipeline.

---

## Step 1 — GitHub Personal Access Token

1. Go to github.com → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Click "Generate new token"
3. Settings:
   - **Token name:** Bromyard depot pipeline
   - **Expiration:** 1 year (set a calendar reminder to rotate it)
   - **Repository access:** Only select repositories → `bromyard-hub`
   - **Permissions:** Repository permissions → Contents → Read and write
4. Click Generate — copy the token immediately (you won't see it again)

---

## Step 2 — Cloudflare Worker

1. Go to cloudflare.com → sign up for a free account if needed
2. Dashboard → Workers & Pages → Create → Create Worker
3. Name it `bromyard-depot-pipeline`
4. Replace the default code with the contents of `cloudflare-worker/worker.js`
5. Click Deploy
6. Copy the Worker URL (looks like `https://bromyard-depot-pipeline.<your-account>.workers.dev`)

### Set environment variables

In the Worker → Settings → Variables → Add:

| Variable name   | Value |
|---|---|
| `GITHUB_PAT`    | The token from Step 1 |
| `SHARED_SECRET` | A random string — make one up, e.g. 20+ random characters. Keep a copy. |

Tick "Encrypt" for both.

---

## Step 3 — Update the PWA

In `bale-tracker/index.html`, find these two lines near the top of the `<script>` block:

```js
const WORKER_URL    = "REPLACE_WITH_WORKER_URL";
const WORKER_SECRET = "REPLACE_WITH_SHARED_SECRET";
```

Replace with your actual values:

```js
const WORKER_URL    = "https://bromyard-depot-pipeline.<your-account>.workers.dev";
const WORKER_SECRET = "<your shared secret from Step 2>";
```

Commit and push — the app will redeploy automatically via GitHub Pages.

---

## Step 4 — GitHub Actions notification email

By default GitHub emails you when a workflow completes. To confirm:

1. github.com → Settings → Notifications
2. Under "Actions" — make sure "Email" is ticked for workflow runs

---

## How to confirm a load (after reviewing the packing sheet)

1. Open github.com on any device
2. Go to the bromyard-hub repo → Actions tab
3. Click "Confirm Load" in the left sidebar
4. Click "Run workflow"
5. Enter the load number → Run

The bale log and running total update automatically.

---

## Rotating the PAT (annually)

1. Generate a new fine-grained token in GitHub (same settings as Step 1)
2. In Cloudflare Worker → Settings → Variables → edit `GITHUB_PAT`
3. Delete the old token in GitHub

---

## Data files

Both live in the `data/` folder in the repo and are updated automatically by Actions:

- `data/bale-log.csv` — running bale log; add rows manually at start of season
- `data/packing-state.json` — load counter and running total; reset to zeros at start of season
