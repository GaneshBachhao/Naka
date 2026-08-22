# Naka — Repo Constitution

Read this before every task. It is the source of truth for architecture, naming, and quality.

---

## What Naka is

A hyperlocal availability and routing platform for Indian talukas. First region: **Sakri, Dhule, Maharashtra**.

The core loop, and the reason the product exists:

```
Customer asks "who has X / is the doctor sitting" (Marathi, free text)
  → we route the question to 3–5 verified nearby businesses
  → first business to answer wins the lead
  → customer travels with confidence instead of wasting a 20 km trip
```

The business directory is **not** the product. It is the substrate that makes routing possible, and the SEO surface that brings customers in.

Launch categories (Tier 1): **agri-input dealers, pharmacies, spare parts, clinics.**
All four share one shape — a specific item or slot, a yes/no answer, and a wasted journey if you guess wrong.

## Non-negotiable product rules

1. **Never build inventory management.** We never ask a shopkeeper to maintain a stock list or SKU catalog. They answer one question, one time, in one tap. Every version of this idea that requires shopkeeper data entry dies within a week.
2. **Fan out, never single-target.** An enquiry always goes to multiple businesses. Reliability comes from redundancy, not from any one shop answering.
3. **Silence must be surfaced.** If nobody answers inside the reply window, tell the customer plainly. Unanswered is a valid, visible outcome — never leave someone waiting.
4. **Never give pesticide, medical, or dosage advice.** Route availability questions only. Pesticide advice is licensed under the Insecticides Act; medical advice is obvious. If intent parsing detects an advice request, flag it and return a safe deflection. This boundary is enforced in the domain layer, not in a prompt.
5. **Multi-region from day one.** `region_id` on every aggregate. Sakri is instance #1 of many. Never hardcode "Sakri" anywhere outside seed data.
6. **Marathi is the default locale**, then Hindi, then English. Not a translation toggle bolted on later.

---

## Stack

Python 3.13+ · FastAPI · Pydantic v2 · SQLAlchemy 2.x · PostgreSQL + pgvector · Redis · ARQ
Next.js 15 (App Router) · React 19 · TailwindCSS · shadcn/ui · TanStack Query · React Hook Form + Zod
pytest · pytest-asyncio · pytest-cov · ruff · black · mypy --strict
Docker Compose · GitHub Actions

**Deliberate deviations from the standard house stack — do not "fix" these:**
- **ARQ, not Celery.** Async-native, Redis-only, lighter.
- **No CQRS read/write split yet.** Revisit when `discovery` read load justifies a projection.
- **No external message broker.** In-process domain events + a transactional outbox table drained by ARQ.
- **Single VM / Docker Compose for now, not Azure managed services.** Code stays containerised and Azure-ready; we migrate when there is revenue.

## Architecture

Strict layering. Dependencies point inward only.

```
Domain          pure Python. No FastAPI, no SQLAlchemy, no SDK imports. No I/O.
  ↑
Application     use cases, ports (Protocol/ABC), DTOs (Pydantic). Depends on Domain only.
  ↑
Infrastructure  SQLAlchemy models & repos, AI adapters, WhatsApp adapter, storage, ARQ jobs.
  ↑
API             FastAPI routers, request/response schemas, dependency wiring.
```

**Every external integration goes through a Port in Application and an Adapter in Infrastructure.** No exceptions. If a task seems to require an SDK call from a domain or application service, stop and flag it before writing code.

### Bounded contexts

```
app/
  catalog/        Business (root), Category, Locality, Region, Media, OpeningHours
  verification/   VerificationRecord (root), confidence tiers, decay, re-verification queue
  enquiry/        Enquiry (root), RoutedRequest, BusinessResponse, outcome tracking
  engagement/     InteractionEvent (append-only), rollups for monthly reports
  identity/       Owner, Agent, OTP claim flow
  shared/         value objects, domain event base, result types
```

Each context is `domain/ · application/ · infrastructure/ · api/`.
Contexts communicate through domain events or application services — **never by importing another context's domain objects**. Enforce with ruff `flake8-tidy-imports` banned-module-patterns.

### Ports required for Tier 1

`MessagingPort` (WhatsApp send/receive — manual adapter first) · `AIClientPort` (intent parsing) · `TextEmbedderPort` (search, later) · `ObjectStoragePort` · `GeocodingPort` · `OtpPort` · repository ports per aggregate.

`GeocodingPort` must stay swappable — Google Maps terms may force a move to MapmyIndia or OSM.

---

## Build strategy: Wizard of Oz first

WhatsApp Business API template approval takes weeks, so **the first release routes enquiries through a human operator using an ops console.** The data model, use cases, and ports are all real. Only the transport is manual.

`ManualMessagingAdapter` implements `MessagingPort` by writing to an operator queue. `WhatsAppMessagingAdapter` replaces it later with **zero changes above the Infrastructure layer.** If swapping it requires touching Application or Domain, the port is wrong.

**Businesses never log in.** They receive a link with a signed, single-use, expiring token and tap one of three buttons. No app, no account, no password. This constraint is what makes adoption possible — protect it.

---

## Code conventions

- Every code block and file starts with a path comment: `# app/catalog/domain/entities.py`
- Full files only. Never partial snippets requiring manual merge, unless a diff is explicitly requested.
- Type hints everywhere. `mypy --strict` clean. No unused imports.
- Domain entities are frozen dataclasses or plain classes with behaviour — never Pydantic (that's Application).
- IDs are typed value objects (`BusinessId`, `EnquiryId`), not bare `UUID`.
- Money in paise as `int`, never float.
- All timestamps timezone-aware UTC. Display converts to IST.
- Comments only where logic is non-obvious. No narration.
- Domain and Application changes ship with pytest tests in the same task, mocking ports.

## Definition of done

`ruff check` clean · `black` formatted · `mypy --strict` clean · tests pass · migration included if schema changed · no layer violation · no hardcoded region.
