# Inbound Carrier Sales — Build Description

**Author:** Alejandro Domínguez
**Challenge:** HappyRobot FDE — Inbound Carrier Sales
**Date:** June 2026

---

## 1. What this is

A freight brokerage receives inbound calls from carriers looking for loads. This
project automates that first call with a **HappyRobot voice agent** backed by a
small, purpose-built HTTP API.

The agent (built on the HappyRobot platform) handles the conversation. During
the call it calls this API as **tools** to do three things a conversation model
should *not* be trusted to do on its own:

1. **Verify** the carrier is authorized to haul (FMCSA).
2. **Find** loads matching the carrier's lane and equipment.
3. **Price** the load deterministically — accept, counter, or walk away.

The system also records each call's outcome for a live analytics **dashboard**.

### Live links

| Resource | URL |
|----------|-----|
| API (backend) | `https://happyrobot-carrier-sales-ado.fly.dev` |
| API docs (OpenAPI/Swagger) | `https://happyrobot-carrier-sales-ado.fly.dev/docs` |
| Dashboard | `https://happy-robot-swart.vercel.app` |
| Code repository | `https://github.com/AlexDO10/HappyRobot` |
| HappyRobot workflow | *(workflow editor link)* |

---

## 2. Architecture

```
                  ┌─────────────────────────┐
   Carrier  ──────▶  HappyRobot Voice Agent  │   (conversation, prompt, call flow)
   (phone)         └────────────┬────────────┘
                                │  HTTPS + x-api-key
                                │  (3 tools called mid-call)
                                ▼
                  ┌─────────────────────────┐
                  │  FastAPI backend (Fly)   │   /get_loads  /verify_mc
                  │  - plain HTTP in-container│   /evaluate_offer
                  │  - Fly terminates TLS     │   /call_results  /metrics
                  └───────┬─────────┬─────────┘
                          │         │
              loads.json  │         │  SQLite (Fly volume)
            (in-memory,   │         │  call results / analytics
             read-only)   ▼         ▼
                                ┌───────────────────────┐
   Broker  ◀──── HTTPS ─────────│  React dashboard       │
   (browser)                    │  (Vercel, static)      │  reads /metrics, /call_results
                                └───────────────────────┘
```

**Stack:** FastAPI + Uvicorn (Python 3.12), React + Vite + Recharts (dashboard),
Docker, Fly.io (API host + TLS + persistent volume), Vercel (dashboard host).

---

## 3. The three agent tools

All are JSON `POST` endpoints, authenticated with a shared `x-api-key` header.
Request/response shapes match the agent's tool definitions exactly.

### `POST /get_loads` — find loads
Filters loads by `origin` / `destination` (case-insensitive substring) and
`equipment_type` (case-insensitive match); all optional.
Returns the matching loads **without `max_buy_rate`** (see §4).

### `POST /verify_mc` — carrier eligibility
Looks up the carrier's MC docket number against the FMCSA QCMobile API and maps
the result to `eligible` / `not_eligible` / `not_found`. Runs in **mock** mode by
default (canned results, no external dependency) and **live** mode with a
server-side FMCSA webkey (see §5).

### `POST /evaluate_offer` — the pricing authority
Deterministic. Given a `load_id`, the carrier's `carrier_offer`, and the
negotiation `round`, returns exactly one of:
`{accept, agreed_rate}` · `{counter, counter_offer}` · `{walk}`.
This is the only place pricing decisions are made (see §4).

---

## 4. Key design decision: a manipulation-proof pricing core

The most important part of this system is that **the conversation model never
controls pricing**. Two concrete guarantees:

### 4.1 The hidden ceiling never leaves the server

Each load has a `max_buy_rate` — the broker's walk-away ceiling, the most they
will pay. If a carrier (or the agent) ever saw this number, the carrier would
simply ask for exactly that. So:

- `max_buy_rate` lives only on the internal `Load` model.
- The public load shape returned by `/get_loads` **does not include it**.
- Only `/evaluate_offer` reads it, server-side, and never echoes it back.

This is enforced by the data model and covered by a test that asserts
`max_buy_rate` appears in no `/get_loads` response body.

### 4.2 Deterministic concession schedule, with the round cap enforced in code

`/evaluate_offer` follows a fixed policy — no LLM, no randomness:

```
base    = loadboard_rate          # our opening (low) offer
ceiling = max_buy_rate            # hidden walk-away max
gap     = ceiling - base

# fraction of the gap we will concede to, by round (tunable config):
FRACTIONS = {1: 0.50, 2: 0.80, 3: 1.00}

allowed = base + gap * FRACTIONS[round]
if carrier_offer <= allowed:   accept at the carrier's number (cheaper for us)
elif round < 3:                counter at `allowed`
else:                          walk
```

The round is **clamped to 1–3 in the endpoint**. Round 3 can only `accept` or
`walk` — never counter. The endpoint accepts no "max" or "limit" from the
caller; it derives everything from the load. The agent is not trusted to count
rounds or hold the line — this endpoint is the source of truth.

This logic is proven with a unit-test matrix (offer below allowed → accept;
above allowed but below ceiling on rounds 1/2 → counter; above ceiling on round
3 → walk; exactly at the ceiling on round 3 → accept; the per-round step values).

---

## 5. FMCSA verification: mock vs. live

Carrier verification is behind a small client interface with an `FMCSA_MODE`
toggle:

- **`mock`** (default): a small registry of canned MC numbers. Only explicitly
  known numbers resolve; everything else is `not_found`. The demo never depends
  on an FMCSA key or FMCSA uptime, and outcomes are deterministic for a script.
- **`live`**: calls `GET /qc/services/carriers/docket-number/{mc}?webKey=...`
  with a server-side webkey and maps `allowedToOperate == "Y"` → eligible,
  otherwise not_eligible, missing/error → not_found.

Switching modes is a runtime env change (`FMCSA_MODE`, `FMCSA_WEBKEY`) — no code
change, no redeploy of a different image.

---

## 6. Security

- **Single shared API key.** Every endpoint (except `/health`) requires
  `x-api-key`, compared in constant time against the `API_KEY` env var. The
  platform is one trusted caller, so this is the right amount of auth — no
  OAuth/JWT over-engineering.
- **Secrets are injected at runtime**, never baked into the image or committed.
  On Fly they're set with `fly secrets set` and live only in the running machine.
- **TLS is terminated by the host.** The app speaks plain HTTP inside the
  container; Fly provisions and renews the certificate and fronts it with HTTPS.
- **CORS** restricts which browser origins may call the API (the dashboard
  origins), configured via `DASHBOARD_ORIGINS`. This does not replace the API
  key — it's a browser-side control layered on top.

> Note on the dashboard: it is a static frontend, so its API key is visible in
> the shipped JavaScript. That is acceptable for an internal demo. A public
> production dashboard would move the key behind a server-side proxy or use
> per-user authentication; this is documented in `web/README.md`.

---

## 7. Analytics & dashboard (beyond the core brief)

To make the system observable, the agent can POST one record per call to
`/call_results` (MC, load, outcome, sentiment, final rate, rounds, summary).
`/metrics` aggregates these into KPIs.

- **Storage:** SQLite on a **Fly persistent volume**, so data survives restarts
  and redeploys. The API runs as a single machine to keep one consistent SQLite
  writer; a future multi-instance deployment would move this to a shared DB
  (e.g. Postgres).
- **Dashboard:** a React + Recharts app on Vercel showing booking rate, average
  negotiation rounds, average final rate, an outcomes bar chart, a sentiment pie,
  and a recent-calls table. It auto-refreshes every 15 seconds.

This is additive — it does not touch the three core agent tools.

---

## 8. Deployment & reproducibility

### Backend (Fly.io)
```bash
cd api
fly launch --no-deploy                 # uses the committed fly.toml
fly volumes create carrier_data --region dfw --size 1
fly secrets set API_KEY=<strong-key> FMCSA_MODE=mock \
  DASHBOARD_ORIGINS="http://localhost:5173,https://<dashboard>.vercel.app"
fly deploy --remote-only
```
- Pinned base image (`python:3.12.7-slim`) and pinned uv; dependency layers
  ordered before code so rebuilds are cached.
- Nothing host-specific in the app code — moving to AWS later is a redeploy, not
  a rewrite.

### Dashboard (Vercel)
- Import the repo, set **Root Directory = `web`**, framework **Vite**.
- Env vars: `VITE_API_BASE_URL`, `VITE_API_KEY`.

### Local development
```bash
# API
cd api && cp .env.example .env && uv sync --extra dev
uv run uvicorn app.main:app --reload      # http://localhost:8000/docs
uv run pytest                             # test suite

# Dashboard
cd web && cp .env.example .env && npm install && npm run dev   # :5173
```

---

## 9. Testing

- **Negotiation matrix** — proves the manipulation-proof core across rounds,
  accept/counter/walk boundaries, the ceiling case, and per-round step values.
- **Leak invariant** — asserts `max_buy_rate` never appears in a `/get_loads`
  response.
- **Auth** — every endpoint rejects missing/invalid keys with 401.
- **Analytics** — log, list, and aggregate call results.

All endpoints are documented automatically via FastAPI's OpenAPI schema at
`/docs` (living documentation).

---

## 10. What I'd do next (production hardening)

- Move call-results storage to a shared DB (Postgres) to allow horizontal
  scaling of the API beyond a single machine.
- Put the dashboard behind a server-side proxy or per-user auth so the API key
  is never shipped to the browser.
- Add structured request logging and per-caller rate limiting.
- Expand the FMCSA live-mode mapping with retries/caching for resilience.
