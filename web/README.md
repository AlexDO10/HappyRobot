# Carrier Sales Dashboard

React + Vite + Recharts dashboard for the Inbound Carrier Sales API. Reads
`/metrics` and `/call_results` and shows KPIs, an outcomes bar chart, a
sentiment pie, and a recent-calls table. Auto-refreshes every 15s.

This is a **static frontend** — it builds to plain HTML/JS and calls the API
over HTTPS. It does not need a server of its own (ideal for Vercel/Netlify).

## Run locally

```bash
cd web
cp .env.example .env     # set VITE_API_BASE_URL and VITE_API_KEY
npm install
npm run dev              # http://localhost:5173
```

## Environment variables

| Var | Meaning |
|-----|---------|
| `VITE_API_BASE_URL` | Base URL of the API, e.g. `https://happyrobot-carrier-sales-ado.fly.dev` (no trailing slash) |
| `VITE_API_KEY` | Must match the API's `API_KEY` |

> Note: Vite inlines `VITE_*` vars into the built JS, so the API key is visible
> to anyone who opens the dashboard. That's acceptable for an internal demo, but
> for a public dashboard you'd add a tiny auth proxy instead of shipping the key.

## Deploy to Vercel

Two ways — pick one.

### Option A — deploy this subfolder from the existing monorepo (no new repo)
1. Import the `HappyRobot` repo in Vercel.
2. Set **Root Directory** to `web`.
3. Framework preset: **Vite**. Build: `npm run build`. Output: `dist`.
4. Add env vars `VITE_API_BASE_URL` and `VITE_API_KEY` in Vercel.
5. Deploy → you get `https://<project>.vercel.app`.

### Option B — split into its own repo
```bash
# from repo root
cp -r web ../carrier-sales-dashboard
cd ../carrier-sales-dashboard
git init && git add . && git commit -m "Carrier sales dashboard"
gh repo create carrier-sales-dashboard --private --source=. --push
# then import that repo in Vercel (root = repo root)
```

## After deploying: allow the Vercel origin (CORS)

The API only accepts browser requests from origins it knows. Add your Vercel URL:

```bash
fly secrets set \
  DASHBOARD_ORIGINS="http://localhost:5173,https://<your-project>.vercel.app" \
  --app happyrobot-carrier-sales-ado
```

(Setting a secret triggers a redeploy automatically.)
