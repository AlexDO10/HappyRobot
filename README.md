# HappyRobot — Inbound Carrier Sales API

A small containerized HTTP API that backs a voice agent for a freight
brokerage. The agent runs on the **HappyRobot platform** and calls these
endpoints as tools mid-conversation — the agent, its prompt, and the call flow
live on the platform, not in this repo. This service is the backend only.

> A `web/` React analytics dashboard ships alongside the API and is deployed to
> Vercel. It reads the analytics endpoints but the API does not depend on it.

## What it does

Three core JSON tools (plus analytics endpoints), single shared API-key auth on
all of them, deployable to a managed host (Fly.io / Railway) that terminates TLS.
Loads come from `api/data/loads.json`, loaded into memory at startup — no database.

| Method | Path              | Purpose                                                |
|--------|-------------------|--------------------------------------------------------|
| GET    | `/health`         | Unauthenticated health check                           |
| POST   | `/get_loads`      | Find loads by lane / equipment                         |
| POST   | `/verify_mc`      | FMCSA carrier eligibility (mock or live)               |
| POST   | `/evaluate_offer` | Deterministic pricing decision (accept/counter/walk)   |
| POST   | `/call_results`   | Log one call outcome (analytics) — powers the dashboard |
| GET    | `/call_results`   | List recent call results                               |
| GET    | `/metrics`        | Aggregated KPIs (booking rate, sentiment, outcomes)    |

Live deployment: `https://happyrobot-carrier-sales-ado.fly.dev`. The
`/call_results` and `/metrics` endpoints are additive analytics (outside the
core 3-tool brief) that back the `web/` dashboard; call data persists in SQLite
on a Fly volume (single machine — see `fly.toml`). The dashboard itself lives in
`web/` and deploys to Vercel (see `web/README.md`).

All endpoints except `/health` require the header **`x-api-key: <API_KEY>`**.
A mismatched or missing key returns `401`.

### The hidden ceiling (critical invariant)

Each load has a `max_buy_rate` — the broker's walk-away ceiling. It **never
leaves the server**. `/get_loads` strips it from every response; only
`/evaluate_offer` reads it, server-side, and never echoes it back.

## Endpoints — request / response examples

Set a key first: `KEY=dev-local-key-change-me` (matches `.env`).

### POST `/get_loads`
Filter on any subset of fields. Substring (case-insensitive) match on
origin/destination; exact (case-insensitive) match on equipment_type.

```bash
curl -s localhost:8000/get_loads -H "x-api-key: $KEY" \
  -H 'content-type: application/json' \
  -d '{"origin":"Dallas","equipment_type":"Dry Van"}'
```
```json
{
  "loads": [
    {
      "load_id": "LD-1001",
      "origin": "Dallas, TX",
      "destination": "Atlanta, GA",
      "pickup_datetime": "2026-06-10T08:00:00",
      "delivery_datetime": "2026-06-11T17:00:00",
      "equipment_type": "Dry Van",
      "loadboard_rate": 1850.0,
      "notes": "No-touch freight. Drop and hook at destination.",
      "weight": 24000.0, "commodity_type": "Packaged food",
      "num_of_pieces": 18, "miles": 781.0, "dimensions": "53ft trailer"
    }
  ]
}
```
(Note: no `max_buy_rate`.)

### POST `/verify_mc`
```bash
curl -s localhost:8000/verify_mc -H "x-api-key: $KEY" \
  -H 'content-type: application/json' -d '{"mc_number":"123456"}'
```
```json
{ "status": "eligible", "legal_name": "Mock Freight Lines LLC" }
```
`status` is one of `eligible` | `not_eligible` | `not_found`.

### POST `/evaluate_offer`
The only pricing authority. Deterministic — no LLM, no randomness.
```bash
curl -s localhost:8000/evaluate_offer -H "x-api-key: $KEY" \
  -H 'content-type: application/json' \
  -d '{"load_id":"LD-1001","carrier_offer":2300,"round":1}'
```
```json
{ "decision": "counter", "counter_offer": 2000.0 }
```
Exactly one decision per response:
- `{"decision":"accept","agreed_rate": <number>}`
- `{"decision":"counter","counter_offer": <number>}`
- `{"decision":"walk"}`

**Algorithm.** `base = loadboard_rate`, `ceiling = max_buy_rate`,
`gap = ceiling - base`. By round we'll concede a growing fraction of the gap —
`{1: 0.50, 2: 0.80, 3: 1.00}` (decreasing step sizes; tunable in
`app/config.py`). `allowed = base + gap * fraction[round]`. If
`carrier_offer <= allowed` → accept at the carrier's number (cheaper for us);
else if not the final round → counter at `allowed`; else → walk. The round is
clamped to 1–3 **in code** — round 3 can only accept or walk, never counter.
The endpoint accepts no "max"/"limit" from the caller.

## Prerequisites

Match the versions this repo is built against:

- Python 3.12 (see `requires-python` in `api/pyproject.toml`)
- `uv` >= 0.5 (the Dockerfile pins `0.5.11`)
- Docker 24+ with Docker Compose v2 (for the containerized paths)
- `flyctl` (only for the Fly.io deploy)
- Node 20 + npm (only if you also run the `web/` dashboard locally)

Pick the path you need — local dev only needs Python + `uv`; a full container run only needs Docker; deploying needs `flyctl`.

## Configuration

All configuration is via environment variables. `api/.env.example` and `web/.env.example` are checked in — copy them to `.env` for local runs. In production, secrets are injected by the host (Fly secrets, Vercel env vars) — nothing is baked into images.

| Var                 | Scope | Required | Default                  | Notes                                                                                  |
|---------------------|-------|----------|--------------------------|----------------------------------------------------------------------------------------|
| `API_KEY`           | api   | yes      | —                        | Shared secret. Sent by clients in the `x-api-key` header. Mismatch → `401`.            |
| `FMCSA_MODE`        | api   | yes      | `mock`                   | `mock` (offline) or `live` (real FMCSA QCMobile API).                                  |
| `FMCSA_WEBKEY`      | api   | if live  | —                        | FMCSA QCMobile webKey. Required when `FMCSA_MODE=live`.                                |
| `DASHBOARD_ORIGINS` | api   | no       | `http://localhost:5173`  | Comma-separated list of browser origins allowed by CORS. Add your Vercel URL here.     |
| `CALLS_DB`          | api   | no       | `data/calls.db`          | Path to the SQLite analytics DB. Set to `/data/calls.db` on Fly to use the volume.     |
| `PORT`              | api   | no       | `8000`                   | The host injects this in production; the app binds `0.0.0.0:$PORT`.                    |
| `VITE_API_BASE_URL` | web   | yes      | —                        | Base URL of the API, e.g. `https://happyrobot-carrier-sales-ado.fly.dev`. No trailing slash. |
| `VITE_API_KEY`      | web   | yes      | —                        | Must match the API's `API_KEY`. Inlined into the bundle — see `web/README.md`.         |

## Run locally

```bash
cd api
cp .env.example .env          # set API_KEY (and FMCSA_MODE/FMCSA_WEBKEY for live)
uv sync --extra dev
uv run uvicorn app.main:app --reload
# OpenAPI docs: http://localhost:8000/docs
```

## Run with Docker

```bash
cd api
docker build -t carrier-sales .
docker run --rm -p 8000:8000 \
  -e API_KEY=your-strong-key \
  -e FMCSA_MODE=mock \
  carrier-sales
```

> Analytics (`/call_results`, `/metrics`) write to SQLite inside the container in this mode, so they vanish when the container exits. Use `docker compose` (below) or Fly (with the mounted volume) when you need the dashboard data to persist. To persist locally, mount a host directory and point `CALLS_DB` at it:
>
> ```bash
> docker run --rm -p 8000:8000 \
>   -e API_KEY=your-strong-key -e FMCSA_MODE=mock \
>   -e CALLS_DB=/data/calls.db \
>   -v "$(pwd)/data:/data" \
>   carrier-sales
> ```

Or the full stack (API + dashboard) from the repo root:
```bash
export API_KEY=your-strong-key
docker compose up --build      # API → :8000, web → :5173
```

## Tests

```bash
cd api && uv run pytest
```
Covers the negotiation matrix (accept below allowed, counter at allowed on
rounds 1–2, walk above ceiling on round 3, accept exactly at the ceiling on
round 3, decreasing step values per round, round clamping) and the leak
invariant (`max_buy_rate` never appears in any `/get_loads` body).

## FMCSA mode

The deployed system runs in **live** mode against the real FMCSA QCMobile API;
`mock` is a deterministic, dependency-free fallback for offline demos.

- `FMCSA_MODE=live` (production): calls
  `GET https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{mc}?webKey=$FMCSA_WEBKEY`
  and maps `allowedToOperate == "Y"` → eligible, else not_eligible, missing →
  not_found.
- `FMCSA_MODE=mock`: a small registry keyed by `mc_number` — only explicitly
  known numbers resolve (`123456`/`111111` → eligible, `222222` → not_eligible);
  everything else → not_found. No network or key required.

## Deploy (Fly.io)

TLS is handled by the host — the app only speaks plain HTTP on `$PORT`. The included `api/fly.toml` already wires up health checks, the `[mounts]` block for the SQLite analytics volume, and `force_https`.

First-time setup:

```bash
cd api

# 1. Pick a unique app name. Either edit `app = "..."` in fly.toml directly,
#    or generate a fresh one with `fly launch`:
fly launch --no-deploy --copy-config

# 2. Create the persistent volume that fly.toml's [mounts] block expects.
#    Skipping this step makes `fly deploy` fail with "volume not found".
fly volumes create carrier_data --region dfw --size 1

# 3. Inject secrets (never baked into the image).
fly secrets set API_KEY=your-strong-key
# Live FMCSA only:
fly secrets set FMCSA_MODE=live FMCSA_WEBKEY=your-webkey
# Allow the dashboard's browser origin (comma-separated; add localhost for dev):
fly secrets set DASHBOARD_ORIGINS="http://localhost:5173,https://<your-project>.vercel.app"

# 4. Deploy and smoke-test.
fly deploy
curl -s https://<app>.fly.dev/health
curl -s https://<app>.fly.dev/get_loads \
  -H "x-api-key: your-strong-key" -H 'content-type: application/json' \
  -d '{"origin":"Dallas"}'
```

Subsequent deploys are just `fly deploy` from `api/`.

Railway: `railway up` against `api/` works identically — set `API_KEY`,
`FMCSA_MODE`, (`FMCSA_WEBKEY`), and `DASHBOARD_ORIGINS` as service variables;
Railway provides `$PORT` and TLS. (No persistent volume out of the box, so
analytics will reset on redeploy unless you wire up a Railway volume.)

## Deploy the dashboard

The `web/` React dashboard is a static SPA that calls the API over HTTPS — it deploys cleanly to Vercel (or any static host). Set `VITE_API_BASE_URL` to your Fly URL and `VITE_API_KEY` to the same value as the API's `API_KEY`, then add the Vercel origin to `DASHBOARD_ORIGINS` on the API so CORS allows it. Full instructions: [`web/README.md`](web/README.md).

## Troubleshooting

- **`401 Unauthorized` on every call** → the `x-api-key` header doesn't match the API's `API_KEY`. Check the deployed value with `fly secrets list` (you'll only see digests, not values — reset with `fly secrets set` if unsure).
- **Browser console shows a CORS error from the dashboard** → the dashboard's origin isn't in `DASHBOARD_ORIGINS`. Add it (comma-separated) and redeploy: `fly secrets set DASHBOARD_ORIGINS="http://localhost:5173,https://<your-project>.vercel.app"`. Setting a secret triggers a redeploy automatically.
- **`fly deploy` fails with a missing-volume error** → run `fly volumes create carrier_data --region dfw --size 1` once, then redeploy. The `[mounts]` block in `fly.toml` requires it.
- **`FMCSA_MODE=live` returns `not_found` for every MC number** → `FMCSA_WEBKEY` is missing or invalid. Verify with `fly secrets list` and re-set it; or fall back to `FMCSA_MODE=mock` for offline demos.

## Reproducibility / portability notes

- `Dockerfile` uses a pinned base image (`python:3.12.7-slim`) and pinned uv,
  with dependency layers ordered before code so rebuilds are cached.
- All secrets are injected at runtime via env vars — nothing is baked into the
  image or hardcoded.
- Nothing in the app is host-specific, so moving to AWS later is a redeploy,
  not a rewrite.
