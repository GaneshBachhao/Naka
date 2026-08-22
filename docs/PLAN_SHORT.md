# Naka — Short Plan
**Sakri taluka first. Built to replicate to other talukas.**
v0.3 · 22 Aug 2026 · Detail in `PRODUCT_PLAN.md` · Build instructions in `KICKOFF.md`

---

## The name

**Naka** — नाका. The road junction in a taluka where dealers, farmers, and workers meet. *"नाक्यावर जाऊन बघ"* is literally what people say when they need to find someone who does work. The metaphor is the product.

Region-neutral, two syllables, works as `naka.in/sakri`, `naka.in/shirpur`.
**Before printing anything:** confirm `.in` availability, trademark class 35, Instagram and Facebook handles. Fallbacks: `nakalocal.in`, `nakaapp.in`.

## The idea in five lines

1. A farmer, patient, or mechanic asks one question in Marathi: *who has this, is the doctor sitting, how long is the wait.*
2. Naka sends the question to 3–5 verified nearby businesses at once.
3. First to answer wins the customer. Everyone else's answer is still logged.
4. The customer travels knowing, instead of wasting a 20 km trip.
5. Businesses pay per answered enquiry. Customers never pay.

## Why this and not a directory

**This changed in v0.3.** A directory competes with Google Maps and loses — Maps knows where the shop is, has more coverage, and is already installed.

Maps does **not** know what's inside the shop or how long the line is. Nobody does. That's the gap.

The test for any feature or category: **would the customer travel and find out they wasted the trip?** If yes, it's a product. If no, it's a listing.

## Launch categories

**Tier 1 — build for these.** All four share one shape: a specific item or slot, a yes/no answer, a wasted journey if you guess wrong.

| | The question |
|---|---|
| **Agri-input dealers** | "Who has this pesticide?" — the wedge. 20–40 dealers in the taluka, crop on a clock, ₹150+ and half a day lost per failed trip |
| **Pharmacies** | "Is this medicine in stock?" — same shape, higher urgency |
| **Spare parts** — two-wheeler, tractor, pump | "Do you have this part?" — highest failed-trip cost of all |
| **Clinics** | "Is the doctor sitting? How many ahead of me?" — replaces the paper token the compounder already keeps |

Tier 2 (later): vet, hardware, repair services, tractor hire, diagnostic labs.
Tier 3 (free listings, traffic only): salon queue counter, restaurants, coaching.
Tier 4 (free forever): government offices, banks, ambulance, ST timings, market days.

**Dropped from launch:** beauty/bridal and coaching. Right for a photo-and-SEO directory; wrong for an availability product. Grocery, gym, stationery — free listings, build nothing.

## The rule that decides whether this survives

**Never build inventory management.** We never ask a shopkeeper to maintain a stock list. He taps one of three buttons on a link — आहे / नाही / नंतर मिळेल. No app, no login, no account.

Every version of this idea that requires shopkeeper data entry is abandoned within a week, and stale availability data is worse than none.

---

## Money

| | Price |
|---|---|
| Verified listing | **Free, forever** |
| **Answered enquiry** — agri, pharmacy, parts | **₹30–50 each, prepaid packs.** A pesticide sale is ₹500–3,000 |
| Clinic token system | ₹500–1,000/month |
| Done-For-You profile setup | ₹799–999 one-time |
| Featured placement — max 3 slots per category per village | ₹2,499/year prepaid |
| Category or region sponsor | ₹15,000–50,000/year |
| Salon queue counter | Free |

**Customers never pay to find anything.** Google Maps is free and already installed; any fee loses that comparison instantly. Consumer volume is what makes a listing worth paying for — gate it and there's nothing to sell.

The one consumer-side exception, phase 3 only: paid classifieds (used tractor, property, jobs at ₹49–499 per listing). Browsing stays free; posting is paid. Needs liquidity first — launch with 20 seeded listings, never zero.

**Never take a cut of the transaction.** Put yourself between customer and shop and both sides route around you by exchanging numbers. The lead is what you sell.

---

## Phases

| Phase | Weeks | Do | Stop unless |
|---|---|---|---|
| **Manual test** | 1–2 | 3 familiar dealers, one WhatsApp number, a notebook. You are the software | 30+ enquiries, someone returns unprompted, median reply under 15 min |
| **0 Build** | 3–8 | Tier 1 platform. Ops console does the routing; WhatsApp adapter comes later | Full loop works: ask → route → dealer taps → answer |
| **1 Coverage** | 9–16 | All agri dealers + pharmacies in Sakri. Verification decay. Community content live | 60% verified inside 90 days · 200 enquiries/month · 50% answered in 30 min |
| **2 Money** | 17–26 | Lead packs, clinic tokens, sponsorships | ₹40,000/month from Sakri alone |
| **3 Replicate** | 27+ | Taluka #2 — Shirpur or Sindkheda, run by a hired agent | Reaches phase-1 numbers in 8 weeks on ≤10 founder-days |

The last gate is the one that matters. If taluka #2 needs you on the ground for six weeks, this is a local services business, not a platform — worth knowing at month eight rather than month thirty.

## What makes people come back

An availability tool is used when something is needed. Between those moments, free ungated utility keeps the habit: mandi rates daily, emergency numbers, weekly market day per village, ST bus timings, government office hours, local jobs.

Farmers check mandi rates every morning. That habit is why the enquiry box gets used when it matters.

---

## Decisions made — don't reopen

- **Multi-region from day one.** `region_id` on every record. URLs `/sakri/...` on one domain — subdomains split SEO authority
- **Mobile website (PWA), not a native app.** Home screen icon, offline, installs from a QR code, no Play Store, no 30 MB download
- **Marathi first.** Mukta + Anek Devanagari, never a Latin font with Devanagari fallback
- **Businesses never log in.** Signed single-use link, three buttons, done
- **Fan out to 3–5**, never one. Reliability comes from redundancy
- **Silence is surfaced.** No answer in 30 minutes → tell the customer plainly
- **Unverified listings publish immediately** but carry `noindex` until an agent verifies, and never receive routed enquiries
- **No reviews until phase 3.** "Answers in 8 minutes, verified 12 days ago" beats anonymous stars and is harder to fake
- **Wizard of Oz first.** Real data model, real ports, human operator. WhatsApp adapter swaps in with no change above Infrastructure

## Technical calls

Full CQRS and a message broker are overkill now — domain events plus an outbox drained by ARQ does the same job far faster. Strict layers, pure domain, and ports stay; those are cheap now and expensive later. Run on one VM, containerised and Azure-ready, migrate at phase 2 rather than burning ₹10–18k/month against zero revenue.

## Legal

**Never give pesticide, dosage, or medical advice** — route availability only. Pesticide advice is licensed under the Insecticides Act. This is enforced in the domain layer, not in a prompt. Verify dealer licences at onboarding.

DPDP consent recorded at onboarding · named grievance officer published · WhatsApp opt-in before any business-initiated message, templates submitted to Meta early · never copy Google Maps data, link out instead.

---

## Next

1. Confirm `naka.in` is available and buy it
2. Run the two-week manual test with your three dealers — notebook, no code
3. If the numbers hold, `CLAUDE.md` + `KICKOFF.md` start the build
