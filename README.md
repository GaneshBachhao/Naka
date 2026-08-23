# Naka

A hyperlocal availability and routing platform for Indian talukas. First region: **Sakri, Dhule, Maharashtra**.

```
Customer asks "who has X / is the doctor sitting" (Marathi, free text)
  → routed to 3–5 verified nearby businesses
  → first business to answer wins the lead
  → customer travels with confidence instead of wasting a 20 km trip
```

See [`CLAUDE.md`](CLAUDE.md) for the full product and architecture constitution, and
[`docs/KICKOFF.md`](docs/KICKOFF.md) / [`docs/SPRINT_PLAN.md`](docs/SPRINT_PLAN.md) for how the build was sequenced.

## Stack

Python 3.13 · FastAPI · SQLAlchemy 2.x · PostgreSQL + pgvector · Redis · ARQ · Next.js 15 · React 19 · Tailwind

The first release ("Wizard of Oz") routes enquiries through a human operator using the ops console at `/ops` -
WhatsApp Business API integration comes later without touching anything above the Infrastructure layer.

## Quickstart (Docker)

```
cp .env.example .env   # defaults work as-is for local dev; add a real ANTHROPIC_API_KEY to parse enquiries
docker compose up -d
```

This brings up Postgres, Redis, the API, the ARQ worker, and the frontend. The `api` container runs
migrations and seeds the Sakri region (idempotent - safe on every restart) before it starts serving.

- Public site: http://localhost:3000/sakri
- Ops console: http://localhost:3000/ops
- API docs: http://localhost:8000/docs

The ops console has no login flow yet (see "Known gaps" below) - mint yourself a token:

```
docker compose exec api python scripts/mint_ops_token.py
```

Paste it into the console's token screen.

## Local development (without Docker)

Faster iteration loop for active development - runs Postgres/Redis in Docker, everything else on the host.

```
docker compose up -d postgres redis
cd backend && uv sync && uv run alembic upgrade head && uv run python scripts/seed_sakri.py
make api      # uvicorn --reload on :8000, from the repo root
make worker   # ARQ worker, separate terminal
cd frontend && npm install && cp .env.local.example .env.local && npm run dev   # :3000
```

`make ops-token` mints a console token the same way. `make seed` re-runs the seed script (idempotent, so
it's safe even if data's already there).

## Walking the full loop by hand

1. Open http://localhost:3000/sakri, ask a question (e.g. "कापसासाठी औषध कोणाकडे आहे?"), submit - you land
   on a live status page.
2. Open http://localhost:3000/ops (with a token), find the enquiry in the queue, open it.
3. Tap **Parse intent** - this calls the real Anthropic API, so it needs `ANTHROPIC_API_KEY` set. Without a
   key, parsing will fail; you can still exercise everything downstream by advancing an enquiry directly via
   the domain (see any `tests/enquiry/factories.py` helper for the shape, or ask the AI adapter's tests how
   it's mocked).
4. Review the ranked candidate businesses, adjust the selection if you like, tap **Route** - this shows the
   exact WhatsApp-style message for each business.
5. Open http://localhost:3000/r/{token} (the token is in the routed message, or the console's message
   queue) as if you were the dealer, tap **आहे**.
6. Back on the customer's status page (auto-refreshes), the answer appears.

## Tests

```
cd backend && uv run pytest                 # unit tests, no external services
cd backend && uv run pytest -m integration  # needs docker compose up -d postgres redis
cd frontend && npm run lint && npm run build
```

Definition of done for any change: `ruff check` clean, `black` formatted, `mypy --strict` clean (on `src`),
tests pass, no bounded-context or layer violation (`make lint` runs all of the above for the backend).

## Known gaps

- **No login for the ops console.** The identity/OTP bounded context isn't built yet - `mint_ops_token.py`
  stands in with a long-lived dev JWT. Fine for a single local operator, not for production.
- **Locality data is representative, not authoritative.** `scripts/seed_sakri.py` seeds 40 plausible Marathi
  village names for local development - Sakri and Pimpalner are real; the rest follow the region's naming
  patterns but haven't been checked against an official gazetteer. Replace before any real launch.
- **Emergency numbers page only has India-wide numbers** (112/100/101/102). Hyperlocal contacts (police
  station, primary health center) need verified real data before they can be added - a wrong number there
  is actively dangerous, so it's a deliberate gap, not an oversight.
- **The public SEO surface is deferred.** `/[region]/[category]`, `/[region]/[locality]/[category]`,
  business profile pages, JSON-LD, sitemaps, and hreflang are Sprint 4 scope (see `docs/SPRINT_PLAN.md`) -
  today the public site is just the ask box and its status page.
