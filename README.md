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

TLS is handled by the host — the app only speaks plain HTTP on `$PORT`.

```bash
cd api
fly launch --no-deploy            # or use the included fly.toml (edit app name)
fly secrets set API_KEY=your-strong-key
# for live FMCSA: fly secrets set FMCSA_MODE=live FMCSA_WEBKEY=your-webkey
fly deploy
fly open                          # https://<app>.fly.dev/health
```

Railway: `railway up` against `api/` works identically — set `API_KEY`,
`FMCSA_MODE`, (`FMCSA_WEBKEY`) as service variables; Railway provides `$PORT`
and TLS.

## Reproducibility / portability notes

- `Dockerfile` uses a pinned base image (`python:3.12.7-slim`) and pinned uv,
  with dependency layers ordered before code so rebuilds are cached.
- All secrets are injected at runtime via env vars — nothing is baked into the
  image or hardcoded.
- Nothing in the app is host-specific, so moving to AWS later is a redeploy,
  not a rewrite.
