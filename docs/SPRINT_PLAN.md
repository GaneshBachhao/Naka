# Naka — Sprint Plan (Phase 0: Build)

Derived from `CLAUDE.md` (repo constitution), sequenced using the task backlog in `KICKOFF.md`, scoped to the 6-week Phase 0 window from `PLAN_SHORT.md` (weeks 3–8). Repo currently contains docs only — no code — so this plan starts from T0.

---

## 1. What CLAUDE.md establishes (summary)

**Product.** Fan-out enquiry routing for Sakri taluka, Maharashtra — not a directory. Customer asks a yes/no availability question in Marathi → routed to 3–5 verified businesses → first answer wins → silence is surfaced, never left ambiguous.

**Six non-negotiable rules** that constrain every task in this plan:
1. No shopkeeper inventory/stock entry, ever.
2. Every enquiry fans out to multiple businesses, never one.
3. No response in the window → customer is told plainly, not left hanging.
4. No pesticide/medical/dosage advice — enforced in the **domain layer**, not a prompt (Insecticides Act boundary).
5. `region_id` on every aggregate; Sakri is instance #1, never hardcoded.
6. Marathi is default locale, not a bolt-on toggle.

**Stack.** Python 3.13 / FastAPI / Pydantic v2 / SQLAlchemy 2.x / Postgres+pgvector / Redis / ARQ (not Celery) · Next.js 15 / React 19 / Tailwind / shadcn. Deliberate simplifications: no CQRS split yet, no external broker (in-process events + outbox), single VM/Compose until revenue.

**Architecture.** Strict inward-only layering — Domain (pure Python) → Application (use cases, ports, DTOs) → Infrastructure (SQLAlchemy, adapters, ARQ) → API (FastAPI). Every external integration must go through a Port + Adapter pair. Six bounded contexts (`catalog`, `verification`, `enquiry`, `engagement`, `identity`, `shared`), each with its own four layers, forbidden from importing another context's domain objects (enforced via ruff `flake8-tidy-imports`).

**Build strategy.** Wizard of Oz first: a `ManualMessagingAdapter` (operator queue) stands in for `MessagingPort` until WhatsApp template approval lands; swapping to `WhatsAppMessagingAdapter` must touch **zero** Application/Domain code. Businesses never log in — signed single-use link, three buttons.

**Definition of done (every task, every sprint):** `ruff check` clean · `black` formatted · `mypy --strict` clean · tests pass · migration included if schema changed · no layer violation · no hardcoded region.

The backlog itself (T0–T10) is already scoped in `KICKOFF.md`; this plan's job is sequencing it into sprints with exit criteria, not rewriting it.

---

## 2. Sprint overview

| Sprint | Weeks | Theme | Tasks | Exit criteria |
|---|---|---|---|---|
| **1** | 3–4 | Domain foundations | T0, T1, T2, T3 | Layer-lint proven to fail on violation; full domain test suite green |
| **2** | 5–6 | Application + Infrastructure | T4, T5 | Integration tests green against dockerized Postgres; Wizard-of-Oz path technically operable end-to-end at the API-less level |
| **3** | 7–8 | Surfaces + seeded loop | T6, T7, T8, T9 (scoped), T10 | `docker compose up` → full loop works: ask → route → dealer taps → answer (Phase 0 gate from `PLAN_SHORT.md`) |
| **4 (buffer)** | 9–10 | SEO surface + hardening | Remainder of T9, polish | Category/locality/business SEO pages, JSON-LD, sitemaps, hreflang — carries into Phase 1 Coverage rather than blocking the Phase 0 gate |

Working rhythm per `KICKOFF.md`: feed one task at a time to Claude Code, run `ruff check . && mypy --strict . && pytest` after each before moving to the next. Sprints below are Claude-Code-task groupings, not calendar-fixed — a sprint ends when its tasks pass DoD, not necessarily on day 14.

---

## 3. Sprint 1 — Domain foundations (weeks 3–4)

**Goal:** Pure, framework-free domain layer for all three core contexts, fully tested, with the architectural guardrails proven to actually work before any business logic is written on top of them.

| Task | Scope | Watch for |
|---|---|---|
| **T0 — Scaffold** | Monorepo (`backend/`, `frontend/`), docker-compose (Postgres 17 + pgvector, Redis), pyproject (ruff/black/mypy --strict/pytest), CI, Makefile | Confirm the banned-import lint rule actually fails on a deliberate cross-context or domain→framework import before calling this done — it's the load-bearing guardrail for everything after |
| **T1 — Catalog domain** | `Region`, `Locality`, `Category`, `Business` + value objects; `is_open_at`, `can_receive_enquiries`, publication states | `PUBLISHED_UNVERIFIED` must be flagged noindex-eligible and excluded from `can_receive_enquiries()` — this is rule 4's precondition (unverified businesses shouldn't answer routed enquiries) |
| **T2 — Verification domain** | `VerificationRecord`, tier decay windows (180/120/90/45d), re-verification queue ordering, `BusinessVerified`/`VerificationExpired` events | Test decay boundaries exactly at the edge, not just well inside/outside the window |
| **T3 — Enquiry domain (core)** | `Enquiry`, `ParsedIntent`, `RoutedRequest`, `BusinessResponse`, fan-out rules, window expiry, advice deflection | This is where rules 2, 3, and 4 actually live in code. Give it the most test time: fan-out ordering, race between two `HAVE_IT` responses, window expiry → `EnquiryUnanswered`, `is_advice_request` → `DEFLECTED` with no routing |

**Exit check:** every test in `pytest` passes with zero I/O; `mypy --strict` clean; a manual sabotage import (e.g. `enquiry/domain` importing `catalog/domain`, or any `domain/` importing `sqlalchemy`) is confirmed to fail lint before Sprint 1 is called closed.

---

## 4. Sprint 2 — Application + Infrastructure (weeks 5–6)

**Goal:** Wire the domain to the real world behind ports, so the Wizard-of-Oz loop is technically executable even before there's an API or UI in front of it.

| Task | Scope | Watch for |
|---|---|---|
| **T4 — Application layer** | Ports (`MessagingPort`, `AIClientPort`, `ObjectStoragePort`, `GeocodingPort`, `OtpPort`, repo ports); use cases (`SubmitEnquiry`, `ParseAndRouteEnquiry`, `RecordBusinessResponse`, `ExpireEnquiryWindow`, catalog/verification use cases); Pydantic DTOs; outbox interface | Every use case test uses mocked ports only — no DB, no network. This is what keeps Sprint 2 fast and Sprint 3 safe to build on |
| **T5 — Infrastructure** | SQLAlchemy models + explicit mappers, Alembic migrations, repo implementations, outbox table + ARQ worker, `ManualMessagingAdapter`, `AnthropicAIAdapter`, signed single-use tokens, ARQ jobs (`expire_enquiry_windows` every minute, `decay_verifications` daily) | `AnthropicAIAdapter` prompt must set `is_advice_request` when the customer asks *what to use* rather than *who has it* — test this explicitly with Marathi/Hindi/transliterated samples, since it's the enforcement point for rule 4 at the I/O boundary (domain still owns the decision) |

**Exit check:** integration tests pass against a real Postgres in Docker; `ManualMessagingAdapter` write path to the operator queue table verified; confirm `WhatsAppMessagingAdapter` could later replace it without touching anything above Infrastructure (i.e. the port shape is right, don't defer this check).

---

## 5. Sprint 3 — Surfaces + seeded loop (weeks 7–8)

**Goal:** Ship exactly enough surface area to prove the core loop end-to-end, per the Phase 0 stop-gate in `PLAN_SHORT.md`: *"Full loop works: ask → route → dealer taps → answer."*

| Task | Scope | Watch for |
|---|---|---|
| **T6 — API** | `POST /api/enquiries`, `GET/POST /r/{token}`, JWT-gated ops endpoints, rate limiting, OpenAPI | Router tests via the app factory, not live server calls |
| **T7 — Dealer response page** | `/r/[token]` — the single most important screen. Server-rendered, near-zero JS, Marathi-first, 56px+ buttons, flip-to-confirmation | Read the design direction in `KICKOFF.md` before touching this — sunlight contrast, tap targets, and the "you were first" reward loop are load-bearing product decisions, not polish |
| **T8 — Ops console** | Live queue, one-tap routing with copyable WhatsApp message, response tracking, business CRUD, reverification queue, daily counters | Optimize for keyboard speed and density — this is a single-operator tool, not a customer surface |
| **T9 — Public site (scoped)** | For this sprint: `/[region]` home with the ask box, and the live enquiry status page it submits to. **Defer** the full `/category`, `/locality`, `/business` SEO surface (JSON-LD, sitemaps, hreflang, noindex thresholds) to Sprint 4 — it's not required for the Phase 0 gate and is scoped closer to Phase 1 Coverage work in `PRODUCT_PLAN.md` §6 | Don't let T9 become the sprint's critical path; the gate only needs a working ask box, not indexed pages |
| **T10 — Seed and ship** | Sakri region seed (~40 localities, Tier 1 taxonomy in mr/hi/en, 20 businesses), emergency numbers page, `docker compose up`, README, full E2E verification | This task *is* the exit criteria — run it last and don't mark Sprint 3 done until the manual E2E pass (submit → parse → route → dealer taps आहे → customer sees answer) actually happens on a fresh `docker compose up` |

**Exit check (= Phase 0 gate):** fresh clone, `docker compose up`, seeded data present, one enquiry walked through the full loop by hand and observed working.

---

## 6. Sprint 4 — SEO surface + hardening (weeks 9–10, buffer)

Not required to clear the Phase 0 gate, but needed before Phase 1 Coverage (`PLAN_SHORT.md`: 60% verified in 90 days, 200 enquiries/month) can start generating organic traffic.

- Remainder of T9: `/[region]/[category]`, `/[region]/[locality]/[category]`, `/[region]/[category]/[business]`, `LocalBusiness`/`ItemList` JSON-LD, canonicals, hreflang, per-region sitemaps
- `noindex` behavior for thin category × locality pages (<3 listings) with nearby-alternatives fallback
- `InteractionEvent` tracking on call/WhatsApp/directions taps (needed from day one per `PRODUCT_PLAN.md` §10 — don't let this slip further than this sprint)
- General hardening: load test the ARQ window-expiry job, confirm outbox draining under failure/retry, re-run the layer-lint sabotage check once more with real code present

---

## 7. Cross-cutting guardrails (check every sprint, not just at the end)

- No task ships without `ruff check` + `black` + `mypy --strict` + `pytest` green (per-task, per `KICKOFF.md`'s instruction — don't batch this to end of sprint)
- Domain and Application changes ship with tests **in the same task**, ports mocked
- Any task that seems to need an SDK call from Domain or Application: stop and flag before writing code, don't route around the port
- No hardcoded `"Sakri"` outside seed data, ever — grep for it before closing a sprint
- Full file outputs only from Claude Code, each starting with its path comment, per `CLAUDE.md` code conventions

---

## 8. Sequencing risk worth flagging now

`PLAN_SHORT.md`'s Phase 0 gate ("full loop works") is narrower than `KICKOFF.md`'s T9 (full public SEO site) and narrower still than `PRODUCT_PLAN.md`'s Phase 0 Foundation scope (150 listings live, all pages indexed) — that older v0.1 document predates the Wizard-of-Oz sequencing and is superseded by `CLAUDE.md`/`KICKOFF.md`/`PLAN_SHORT.md` v0.3. This plan follows the newer, narrower gate and pushes the SEO buildout to Sprint 4 deliberately, so a 6-week solo build stays achievable instead of silently expanding to match the older document's scope.
