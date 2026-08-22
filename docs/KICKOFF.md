# Naka — Claude Code Kickoff

**How to use:** put `CLAUDE.md` at the repo root. Open the folder in VS Code, start Claude Code, and paste tasks **one at a time, in order**. Do not paste the whole file at once — Claude Code produces far better work on a scoped task than on a sprint.

Run `ruff check . && mypy --strict . && pytest` after each task before moving on.

---

## Design direction (referenced by T7–T9)

Give this to Claude Code whenever it builds UI. It is deliberately specific — without it you get generic shadcn defaults.

**Subject world.** The naka is the road junction in a taluka where dealers, farmers, and workers meet. Its visual vernacular is hand-painted shop signboards: heavy Devanagari lettering, flat saturated colour on enamel and painted metal, chalk price boards outside agri shops, MSRTC bus-stand destination boards. Draw from that, not from SaaS dashboards.

**Palette** — signboard, not startup. No purple-blue gradients, no cream-and-terracotta.
```
--ink     #14261F   near-black green, all body text
--field   #0F5132   signboard green, primary
--haldi   #E8A317   turmeric amber, accent + "available" state
--paper   #FAF8F3   background
--stone   #6B7A72   muted text, borders
--stop    #B3261E   "not available", errors
```

**Type.** Body and UI: **Mukta** (Ek Type — Devanagari and Latin drawn as one harmonised family, so Marathi and English sit correctly on the same line). Display: **Anek Devanagari** at heavy weight and condensed width, echoing painted signboard lettering. Never render Devanagari in a Latin-first font with a fallback — the vertical metrics break and it looks cheap.

**Signature element.** The dealer response card. A farmer's question arrives as a card styled like a chalk price board, and the dealer taps one of three full-width answers. When answered, the card flips to a large, unmissable Devanagari **आहे** (have it) or **नाही** (don't). That single screen is the product — build it with more care than anything else.

**Hard constraints, all load-bearing:**
- Readable in direct sunlight — contrast ratio 7:1 minimum, never grey-on-grey
- Tap targets 56px minimum. Assume one thumb, possibly wet or calloused hands
- Base font 18px, not 16px. Many users are 45+ reading Marathi on a small screen
- Under 100 KB initial JS. Assume 3G and a ₹6,000 phone
- Icon plus label, never icon alone
- Empty and failure states in Marathi, plain and directive — never apologetic
- Keyboard focus visible, reduced motion respected

---

## T0 — Scaffold

```
Read CLAUDE.md fully before starting.

Scaffold the Naka monorepo:
- backend/ — FastAPI, Python 3.13, uv, src layout with the bounded contexts listed in CLAUDE.md (empty packages with __init__.py and the four-layer folders each)
- frontend/ — Next.js 15 App Router, TypeScript, Tailwind, shadcn/ui
- docker-compose.yml — postgres 17 with pgvector, redis
- pyproject.toml — ruff, black, mypy --strict, pytest with asyncio_mode=auto
- ruff config with flake8-tidy-imports banned-module-patterns preventing cross-context domain imports, and preventing fastapi/sqlalchemy imports inside any */domain/* path
- .github/workflows/ci.yml — ruff, mypy, pytest
- Makefile — up, down, test, lint, migrate
- .env.example

No business logic yet. Confirm the layer-boundary lint rules actually fail on a deliberate violation before finishing.
```

## T1 — Catalog domain

```
Implement the catalog bounded context, domain layer only. Pure Python, no framework imports.

Entities and value objects:
- Region (root): slug, names in mr/hi/en, district, state, active
- Locality: region_id, village name mr/en, transliteration variants, pincode, centroid, market day
- Category: slug, parent, names + synonyms + transliterations in mr/hi/en, tier (1-4), routable flag
- Business (root): region_id, locality_id, display name mr/en, owner name, category ids, contact numbers, WhatsApp number, landmark, coordinates, opening hours, attributes, listing status, publication state
- Value objects: BusinessId, RegionId, PhoneNumber (validates Indian mobile), Coordinates, OpeningHours, DayHours supporting a midday closure

Behaviour that belongs in the domain, not in a service:
- Business.is_open_at(datetime) accounting for weekly off and midday closure
- Business.can_receive_enquiries() — must be published, verified, routable category, has a WhatsApp number
- Publication states: DRAFT, PUBLISHED_UNVERIFIED, PUBLISHED_VERIFIED, SUSPENDED, CLOSED
- PUBLISHED_UNVERIFIED is visible on-site but must be flagged noindex and must never receive routed enquiries

Full pytest coverage of the behaviour above, including timezone edge cases at IST midnight.
```

## T2 — Verification domain

```
Implement the verification bounded context, domain layer only.

- VerificationRecord (root): business_id, tier, method, verified_at, verified_by, notes
- Tiers and decay windows: FIELD_VERIFIED 180d, OWNER_CONFIRMED 120d, CONTACT_VERIFIED 90d, SOURCED 45d
- Business-facing calculation: current confidence tier given now(), whether stale, days until decay
- A domain service that returns the re-verification queue ordered by: paying businesses first, then routable categories, then oldest verification
- Domain events: BusinessVerified, VerificationExpired

Tests covering each decay boundary exactly at the edge.
```

## T3 — Enquiry domain (the core)

```
Implement the enquiry bounded context, domain layer only. This is the heart of the product — take extra care.

- Enquiry (root): region_id, raw customer text, customer phone, parsed intent, locality, category, urgency, status, created_at, reply window
- ParsedIntent value object: category_id, item text, locality_id, urgency, confidence, is_advice_request flag
- RoutedRequest: enquiry_id, business_id, sent_at, token, expires_at, responded_at
- BusinessResponse: HAVE_IT / DONT_HAVE / CAN_ARRANGE_BY(date), optional price in paise, optional note
- Statuses: RECEIVED, PARSED, ROUTED, ANSWERED, UNANSWERED, DEFLECTED, CLOSED

Rules to enforce in the domain:
- Routing fan-out is 3 to 5 businesses, selected by category match, then locality proximity, then response rate, then verification recency
- Only businesses passing can_receive_enquiries() are eligible
- First HAVE_IT response wins and is marked winning; later responses are still recorded for analytics
- Reply window default 30 minutes; on expiry with no response the enquiry becomes UNANSWERED and must produce a customer notification event
- If ParsedIntent.is_advice_request is true, the enquiry goes straight to DEFLECTED and is never routed. This is the Insecticides Act / medical advice boundary from CLAUDE.md — enforce it here, not in a prompt

Domain events: EnquiryReceived, EnquiryRouted, ResponseReceived, EnquiryAnswered, EnquiryUnanswered, AdviceRequestDeflected

Thorough tests: fan-out selection ordering, race between two HAVE_IT responses, window expiry, advice deflection.
```

## T4 — Application layer

```
Implement the application layer for catalog, verification, and enquiry.

Ports (Protocols):
- MessagingPort — send_to_business, send_to_customer
- AIClientPort — parse_enquiry_intent returning ParsedIntent
- ObjectStoragePort, GeocodingPort, OtpPort
- Repository ports per aggregate

Use cases:
- SubmitEnquiry, ParseAndRouteEnquiry, RecordBusinessResponse, ExpireEnquiryWindow
- CreateBusiness, PublishBusiness, RecordVerification, BuildReverificationQueue

Pydantic v2 DTOs for every boundary. Transactional outbox interface for domain events.

Tests for every use case with all ports mocked. No database, no network.
```

## T5 — Infrastructure

```
Implement infrastructure for catalog, verification, enquiry.

- SQLAlchemy 2.x models, separate from domain entities, with explicit mappers both directions
- Alembic migrations
- Repository implementations
- Outbox table + ARQ worker draining it
- ManualMessagingAdapter implementing MessagingPort by writing to an operator queue table
- AnthropicAIAdapter implementing AIClientPort for intent parsing — prompt must handle Marathi, Hindi, and Latin-transliterated input, and must set is_advice_request when the user asks what to use rather than who has it
- Signed single-use expiring tokens for business response links
- ARQ jobs: expire_enquiry_windows (every minute), decay_verifications (daily)

Integration tests against a real Postgres in Docker.
```

## T6 — API

```
FastAPI routers:
- POST /api/enquiries — public submission
- GET  /r/{token} — business response page data, no auth
- POST /r/{token} — record response, single-use
- Ops endpoints behind JWT: enquiry queue, manual route, mark sent, business CRUD, verification recording, reverification queue

Rate limiting on public endpoints. OpenAPI documented. Router tests with the app factory.
```

## T7 — Dealer response page

```
Read the design direction above before writing any UI.

Build the business response page at /r/[token]. This is the single most important screen in the product.

- Server-rendered, near-zero JS, must work on 3G
- Marathi first
- Shows: what was asked, which village the customer is in, how long ago
- Three full-width buttons, 56px+ tall: आहे (have it) / नाही (don't) / नंतर मिळेल (can arrange)
- On "have it": optional price field and note, then submit
- On submit: card flips to a large confirmation. If they were first, say so plainly — that is the reward loop
- Expired or already-used token gets its own clear state, not an error page
- No login, no account, ever
```

## T8 — Ops console

```
Read the design direction above.

Internal console for the operator running Wizard-of-Oz routing:
- Live enquiry queue with age and status, auto-refreshing
- One enquiry view: raw text, parsed intent, suggested businesses ranked with the reason for each, editable
- One tap to route, showing the exact WhatsApp message to copy and send
- Response tracking as answers arrive
- Business management: create, edit, publish, record verification
- Reverification queue
- Daily counters: enquiries, answer rate, median response time

Dense and fast. This is a tool for one person working quickly, not a customer-facing surface — prioritise keyboard shortcuts and information density over polish.
```

## T9 — Public site

```
Read the design direction above.

Next.js public site, Marathi default with hreflang for hi/en:
- /[region] — region home. Hero is the ask box, not a hero image. Below it: emergency numbers, today's market day, top categories
- /[region]/[category] — listing with open-now filter
- /[region]/[locality]/[category] — the long-tail SEO workhorse
- /[region]/[category]/[business] — profile with call, WhatsApp, directions, hours, verified-on date
- Ask box submits an enquiry and shows a live status page: routed to N businesses, waiting, then the answer

SEO: LocalBusiness and ItemList JSON-LD, canonicals, hreflang, per-region sitemaps.
PUBLISHED_UNVERIFIED businesses render but emit noindex.
Category × locality pages with fewer than 3 listings emit noindex and show nearby alternatives.
Track every call tap, WhatsApp tap, and directions tap as an InteractionEvent from day one.
```

## T10 — Seed and ship

```
- Seed: Sakri region, ~40 localities with Marathi names and market days, Tier 1 category tree in mr/hi/en, 20 sample businesses
- Sakri emergency numbers page
- Docker compose up brings the whole stack live
- README with local setup
- Verify full loop end to end: submit enquiry → parse → route → dealer taps आहे → customer sees answer
```

---

## After T10

Your three familiar dealers go into the seed data, you run real enquiries through the ops console, and the notebook test becomes a real dataset. WhatsApp adapter replaces the manual one once Meta approves the templates — nothing above Infrastructure changes.
