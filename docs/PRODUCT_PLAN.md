# Hyperlocal Business & Community Platform — Product Plan
**Instance 1: Sakri taluka, Dhule district, Maharashtra**
**Owner:** Pamacore Labs
**Status:** Planning — no implementation started
**Version:** 0.1 · 22 Aug 2026

---

## 0. Decisions locked in this document

| # | Decision | Value | Reversible? |
|---|---|---|---|
| D1 | Scope | Multi-taluka platform; Sakri is instance #1, not the product | No |
| D2 | Tenancy | Region is a first-class entity on every aggregate from day one | No — expensive retrofit |
| D3 | Routing | Single domain, path-based: `/{region-slug}/{category}/{business}` | Hard |
| D4 | Brand | Region-agnostic parent brand required before domain purchase | Hard |
| D5 | Client | Mobile-first PWA. No native Android app until a retention loop exists | Yes |
| D6 | Core product | Lead routing + freshness, not listings. Directory is the byproduct | No |
| D7 | Primary language | Marathi first, Hindi second, English third | Hard |
| D8 | Base listing price | Free, forever, for everyone | No |

---

## 1. Product thesis

### 1.1 The problem with "a directory for Sakri"

A directory competes with Google Maps and loses. Maps is pre-installed, already answers "salon near me," and has more coverage than a solo operator can build. A listing site also gives a consumer no reason to ever return — one visit, one phone number, done. The uploaded strategy documents solve the supply side (how to onboard businesses) thoroughly and leave the demand side to hope.

Three things Google structurally does not do for a taluka like Sakri:

1. **Route a request to a person.** Maps shows you five plumbers. It does not tell you which one will answer at 8 PM tonight.
2. **Guarantee freshness.** Dead numbers and closed shops sit on Maps and JustDial for years. Nobody re-verifies rural listings.
3. **Handle Marathi + transliteration + village-level geography.** "साक्री मध्ये ब्युटी पार्लर", "sakri madhe parlour", "parlour near Pimpalner" all need to resolve to the same result set.

### 1.2 What we actually sell

**To the consumer:** send one message, get a real answer from someone who is open and will respond.
**To the business:** enquiries you can count, and proof of them at renewal time.

Positioning line for owners — unchanged from the uploaded plan, and correct:
> "More local enquiries for your business" — never "we launched an app."

### 1.3 The three-layer product

```
Layer 3  ROUTING      Free-text enquiry → intent parse → fan-out to 3 verified
                      businesses → first responder wins → outcome tracked
                      ↑ this is the revenue engine
Layer 2  FRESHNESS    Every listing carries last_verified_at + confidence tier,
                      decays on a schedule, triggers re-verification
                      ↑ this is the moat
Layer 1  DIRECTORY    Structured listings, categories, localities, SEO pages
                      ↑ this is the SEO asset and the raw material for L2/L3
```

Build order is 1 → 2 → 3. Never pitch layer 1 as the product.

### 1.4 Why replication changes the plan

Because Sakri is instance #1, everything below is designed as a **playbook plus a region-parameterised system**, not a one-off site. The unit of expansion is a taluka (~150–250 villages, 1,000–3,000 addressable businesses). The playbook must be executable by a hired field agent with a checklist, not only by the founder. If onboarding taluka #2 requires the founder on the ground for six weeks, the model does not scale and we should know that before writing code.

---

## 2. Naming and brand (do this in week 1)

"Sakri Local" cannot be the brand — it dies at taluka #2.

Requirements:
- Region-agnostic, pronounceable in Marathi and English
- One short `.in` or `.com` domain, plus matching WhatsApp Business display name and social handles
- Works as `{brand}.in/sakri`, `{brand}.in/shirpur`, `{brand}.in/sindkheda`

Local sub-brand is fine in *marketing copy* ("Sakri वर आपले स्वागत") and in the page `<title>`, but the entity, domain, and legal name stay neutral.

**Action:** shortlist 5 names, check domain + trademark class 35/42 + Instagram/Facebook handle availability, buy before anything is printed.

---

## 3. Geography and tenancy model

### 3.1 Hierarchy

```
State (Maharashtra)
 └─ District (Dhule)
     └─ Taluka / Region  ← tenant boundary, the unit of expansion
         └─ Town or Village (Sakri, Pimpalner, Nizampur, Dahivel, …)
             └─ Area / Landmark (Main Road, Bus Stand, Market Yard, …)
```

Every business, enquiry, event, offer, and content item carries a `region_id`. Every public URL is region-scoped. Every metric is reported per region.

### 3.2 Why path-based, not subdomain

| | Path `/{region}/…` | Subdomain `{region}.brand.in` |
|---|---|---|
| SEO authority | Consolidated on one domain | Split per subdomain, each starts at zero |
| Backlinks | Every link helps every region | Only helps that region |
| SSL / DNS ops | One certificate | Wildcard + per-region config |
| Cross-region search | Trivial | Cross-origin friction |

Path-based wins decisively for a network of small, low-authority regions. Locked.

### 3.3 Locality data to prepare before launch

- Full village list for Sakri taluka with Marathi and English names, plus common transliteration variants
- Pincode mapping
- Rough centroid lat/long per village (for distance sort)
- Population / market-size tier per village (drives field-visit prioritisation)
- Weekly market (आठवडे बाजार) day per village — genuinely useful content, and nobody publishes it

Source from Census 2011 village directory, Maharashtra government village lists, and local knowledge. This is a one-time data task per taluka and belongs in the expansion playbook.

---

## 4. Content the application must maintain

This section is the answer to "what content do we keep." Split by owner and update cadence.

### 4.1 Business listing content (the core record)

**Identity**
- Legal / display name (mr + en; names are transliterated, never translated)
- Owner or contact person name
- Established year
- Business type: shop, service, professional, institution, government office, NGO

**Contact**
- Primary phone, WhatsApp number (frequently different), alternate phone
- Email (rare below a certain size — optional)
- Website / Instagram / Facebook if any
- Whether the WhatsApp number is monitored and by whom

**Location**
- Village + area + landmark ("opposite ST stand", "near Hanuman mandir") — landmarks matter more than addresses here
- Lat/long pin
- Google Maps share link (link only, never copy Maps content — see §11.3)
- Delivery / service radius, and whether they travel to the customer

**Operations**
- Opening hours per weekday, plus lunch-break closure (very common)
- Weekly off day
- Seasonal or festival closures
- Appointment required yes/no
- Home visit / home delivery available
- Payment methods: cash, UPI, card, credit-book (उधार)
- Languages spoken

**Offering**
- Service or product list with price bands, not exact prices (owners resist exact prices; bands convert better)
- Category + subcategory (from controlled taxonomy, §4.2)
- Attribute tags (from controlled set: AC, parking, female staff, wheelchair access, 24×7, emergency)
- Credentials where the category demands it: doctor degree + registration number, coaching faculty qualifications, shop licence, FSSAI number for food

**Media**
- 5–10 photos: exterior with signboard, interior, work samples, owner portrait, price card
- Optional 30-second intro video
- All images captured or explicitly licensed by us — never lifted from the owner's Instagram without written permission

**Trust**
- `last_verified_at`, verification method, verifying agent
- Confidence tier (see §5)
- Claim status: unclaimed / claimed / verified-owner
- Reviews (phase 2 — see §4.7 on why reviews are dangerous early)

**Commercial**
- Plan tier, featured placement flags, active offers with expiry
- Lead-pack balance if on pay-per-lead

**Cadence:** verified quarterly minimum. Hours and offers change more often and need a one-tap owner update path via WhatsApp.

### 4.2 Taxonomy (controlled, seeded, versioned)

Free-text categories destroy search and destroy SEO. The taxonomy is a curated tree maintained by us, not by owners.

- **Level 1** — ~12 groups: Food & Dining · Beauty & Wellness · Health & Medical · Education & Training · Home & Repair Services · Retail & Grocery · Agriculture & Farm Supply · Automotive · Construction & Hardware · Financial & Legal · Events & Photography · Government & Public Services
- **Level 2** — ~120–150 specific categories: "bridal makeup", "borewell contractor", "tractor repair", "MPSC coaching", "pathology lab", "tiffin service", "fertiliser dealer"
- **Attributes** — per-category, from a fixed vocabulary
- Each node carries mr / hi / en names, synonyms, transliteration variants, and an SEO description block

Adding a category is an editorial decision with an SEO page attached. It is not user-generated.

### 4.3 Localisation content

Three locales: `mr` (default), `hi`, `en`.

Needs translation: UI strings, category and attribute names, page templates, meta titles/descriptions, WhatsApp message templates, email templates, legal pages, help content.
Never translated: business names, person names, village names (transliterated instead, with variants stored for search).

Owner-written descriptions will be poor or absent. Generate mr/hi/en copy from the structured form using AI, then have the field agent confirm before publishing. This is one of the few genuinely load-bearing AI uses in the product.

### 4.4 SEO surfaces (the free demand channel)

Zero-competition queries. Every one of these is a maintained page template:

| Surface | URL shape | Volume | Notes |
|---|---|---|---|
| Business detail | `/sakri/beauty-parlour/sakri-beauty-studio` | 1 per business | `LocalBusiness` JSON-LD |
| Category × locality | `/sakri/pimpalner/beauty-parlour` | cat × locality | The long-tail workhorse |
| Category (region) | `/sakri/beauty-parlour` | ~150 | `ItemList` JSON-LD |
| Locality hub | `/sakri/pimpalner` | ~50 | All categories in that village |
| Curated list | `/sakri/best-beauty-parlour-in-sakri` | editorial | Human-written intro, updated quarterly |
| Region home | `/sakri` | 1 | |
| Marathi variants | `/mr/…` with hreflang | mirrors above | |

Thin-page risk is real: a category × locality page with zero listings must return a useful "nearby alternatives" page or `noindex` until it has ≥3 listings. Decide the threshold before generating pages.

Non-negotiable from commit #1: JSON-LD structured data, `hreflang`, canonical tags, XML sitemaps segmented per region, and interaction event tracking. All four are painful retrofits.

### 4.5 Community content — the retention loop

A directory has no reason for a repeat visit. This content is what makes someone open the site weekly, and it is the single biggest addition to the uploaded plan.

| Content | Cadence | Source | Why it works |
|---|---|---|---|
| Mandi / market rates for Sakri APMC | Daily | Public market-price feeds | Farmers check this daily. Highest-frequency habit in the taluka |
| Weekly market (आठवडे बाजार) calendar per village | Static + corrections | Local knowledge | Nobody publishes it |
| Emergency directory — ambulance, police, hospital, electricity fault, blood banks | Quarterly verify | Field verification | Highest-trust page on the site. Free forever |
| Government office timings and contacts — tehsil, gram panchayat, RTO, bank branches | Quarterly | Field verification | Constant search demand |
| ST bus timings from Sakri stand | Monthly | Depot | High-frequency utility |
| Admission dates for local colleges and coaching | Seasonal | Institutions | Direct feeder for the highest-value ad category |
| Local jobs board | Weekly | Employers | Strong sharing behaviour |
| Festival, jatra, and event calendar | Seasonal | Community | Seasonal traffic spikes |
| Power-cut and water-supply notices | Ad hoc | MSEDCL / panchayat | Drives WhatsApp channel subscriptions |

Rule: community content is **always free and never gated**. It buys the audience that makes the paid business listings worth paying for.

### 4.6 Sales and field collateral (maintained as product artifacts, not ad hoc)

- 3 polished demo profiles — beauty, coaching, restaurant — kept permanently current
- Owner one-pager, printed, Marathi
- QR cards and shop-window stickers ("आमचा व्यवसाय येथे आहे")
- Approved WhatsApp message templates (see §11.2 — Meta approval has lead time)
- Monthly per-business performance report template
- Field-agent onboarding checklist and photography guide
- Pricing sheet, Marathi

### 4.7 Reviews — deliberately deferred

Reviews look essential and are a trap at this scale. In a taluka everyone knows everyone: fake five-stars from relatives, and a single one-star from a rival that the owner will call you about personally. Weak review volume also looks worse than none.

Phase 1 substitute: **verification badge + last-verified date + response-rate badge**. "Responds to enquiries within 2 hours, verified 12 days ago" is more useful and more defensible than four anonymous stars. Introduce reviews only in phase 3, gated on a real enquiry having occurred through the platform.

### 4.8 Legal and policy pages

Terms of use · Privacy policy (DPDP-compliant) · Listing and content policy · Removal / correction request process · Grievance officer name and contact (DPDP requirement) · Refund policy · Advertising disclosure for featured placements.

---

## 5. Verification and freshness system

The moat. Cheap to build; expensive for an aggregator to copy because it requires local field presence.

**Confidence tiers**

| Tier | Meaning | Public label |
|---|---|---|
| Field-verified | Agent physically visited, photographed, confirmed | "Visited & verified" + date |
| Owner-confirmed | Owner confirmed details via OTP or WhatsApp reply | "Confirmed by owner" + date |
| Contact-verified | Phone answered and details confirmed by call | "Contact verified" + date |
| Sourced | Compiled from public sources, unconfirmed | "Not yet verified" |
| Stale | Past decay window | "Details may be outdated" |
| Closed | Reported or confirmed closed | Delisted from search, page retained with notice |

**Decay:** field-verified 180 days · owner-confirmed 120 days · contact-verified 90 days · sourced 45 days. On expiry the record enters a re-verification queue.

**Re-verification sweep:** automated WhatsApp ping — "still open? still this number? hours unchanged?" — with one-tap replies. No reply after two attempts escalates to an agent call, then a field visit for paying listings. Track cost per verification; it is the core unit economic of the whole business.

Public commitment worth making: **"Every listing verified within the last 90 days, or we tell you it isn't."** No competitor will match it.

---

## 6. Phased roadmap

Each phase has an exit gate. Do not start the next phase until the gate is met — the gate exists to kill the idea cheaply if it does not work.

### Phase 0 — Foundation (weeks 1–3)
Brand, domain, legal entity, region + locality data for Sakri, taxonomy seeded in 3 languages, public site with business / category / locality / region pages, internal admin for listing entry, event tracking, SEO schema, sitemaps, WhatsApp Business account, 3 demo profiles.
No login. No owner portal. No payments.
**Gate:** 150 listings live, ≥3 categories fully covered, all pages indexed.

### Phase 1 — Coverage and freshness (weeks 4–10)
Scale to 600–900 listings across 15–20 categories. Owner claim flow via phone OTP. Owner self-serve portal for hours, photos, offers. Verification decay engine and re-verification sweeps. Monthly per-business report generation and delivery. Community content live: emergency directory, mandi rates, market calendar, government timings.
**Gate:** ≥60% of listings verified inside 90 days; ≥1,500 weekly organic sessions; ≥25 businesses receiving at least one tracked interaction per month.

### Phase 2 — Routing, the actual product (weeks 11–20)
One WhatsApp number for the region. Free-text enquiry → AI intent parse (category, locality, urgency) → fan-out to 3 verified matching businesses → first responder claims → outcome logged. Response-rate and response-time badges on public profiles. Enquiry dashboard for owners. Semantic + transliteration-tolerant search across Marathi/Hindi/English.
**Gate:** ≥200 routed enquiries per month; ≥50% first-response inside 30 minutes; ≥10 owners state in writing that enquiries are commercially valuable.

### Phase 3 — Monetisation at scale (weeks 21–32)
Payments, plan management, invoicing, lead packs, featured placement auction or fixed slots, sponsorships, gated reviews, referral programme.
**Gate:** ₹40,000+ MRR-equivalent from Sakri alone, with ≥60% renewal at first renewal point.

### Phase 4 — Replication (week 33+)
Codify the playbook. Launch taluka #2 (Shirpur or Sindkheda — larger, adjacent, shares the Dhule district identity) run primarily by a hired agent.
**Gate:** taluka #2 reaches phase-1 metrics in ≤8 weeks with ≤10 founder-days invested. If it cannot, the business is a local services shop, not a platform — and that is worth knowing.

---

## 7. Pricing and monetisation

### 7.1 Principles

1. **The base listing is free forever.** Coverage is the SEO asset and the routing substrate. Charging for it caps both.
2. **Avoid small monthly subscriptions.** ₹99–₹499/month churns hard at month two when the owner cannot attribute anything, and collection overhead exceeds the revenue. The uploaded plan's monthly ladder should be restructured.
3. **Sell outcomes and services, not placement.** Owners understand "photos" and "customers." They do not understand "featured placement."
4. **Take cash up front.** One-time and annual-prepay beat monthly in this market by a wide margin.
5. **Price against the value of one customer,** not against hosting cost. A bridal package is ₹8,000–25,000; a coaching admission is ₹10,000–40,000. One converted lead pays for a year.

### 7.2 Structure

| Product | Price (test band) | Model | Notes |
|---|---|---|---|
| Verified listing | ₹0 | Free | Always. Includes verification badge |
| **Setup & Shoot** | ₹999–1,499 | One-time | Photos, copy in 3 languages, hours, map pin, WhatsApp button. **The wedge — cash on day one, and a service they already buy** |
| Featured placement | ₹2,499–3,499 | Annual prepay | Top of category × locality. Cap at 3 slots per category per village to protect scarcity |
| Lead packs | ₹25–60 per delivered enquiry, prepaid in blocks of 25 | Usage | Only in high-intent categories: clinics, coaching, bridal, contractors, automotive |
| Offer promotion | ₹499 per campaign | Per-use | Push to WhatsApp channel + social + site banner |
| Managed presence | ₹1,999–2,999/month | Monthly | Only for 5–10 anchor clients: hospitals, large coaching institutes, dealerships. Real service delivery, real margin |
| Category sponsor | ₹15,000–30,000/year | Annual | "Health section sponsored by X Hospital" |
| Region sponsor | ₹50,000+/year | Annual | Banks, credit societies, large retailers |
| Seasonal bundles | ₹2,000–5,000 | Campaign | Admission season (May–July), wedding season (Nov–Feb), festivals |

### 7.3 Revenue mix target for Sakri by month 12

Setup & Shoot 30% · Featured annual 25% · Lead packs 20% · Managed 15% · Sponsorship 10%.
Diversified deliberately — a single-product revenue line in a market of 2,000 businesses caps out fast.

### 7.4 What not to do

Do not charge for listing removal or "reputation management." Do not sell exclusivity to one business in a category — it makes the routing product worthless. Do not discount below ₹999 for Setup & Shoot; the anchor price sets the perceived value of everything else.

---

## 8. Field operations — treat this as real scope

This is a services business with software attached. The uploaded plan under-weights it.

**Roles**
- *Field agent* — visits, photographs, onboards, verifies. 8–12 listings/day achievable in a market street.
- *Tele-verifier* — part-time, works the re-verification queue by phone. Can be remote.
- *Content editor* — mandi rates, community content, category page copy. ~5 hrs/week.

**Agent economics to validate in the pilot:** cost per listing onboarded, cost per verification, listings maintained per agent, and conversion rate from onboarded → paying. These numbers decide whether replication is viable, so measure them from the first week rather than reconstructing them later.

**Internal admin tooling is not optional.** A mobile-friendly agent app for on-site entry — photo upload, hours capture, verification tick, offline draft — is required by week three. This is always forgotten in planning and always urgently needed. Budget it into phase 0/1.

**Pilot cohort:** the uploaded plan's ten free pilot businesses is right. Keep the exchange explicit — free Setup & Shoot in return for a testimonial, two referrals, and permission to publish results.

---

## 9. Go-to-market

Phase-0 and phase-1 GTM from the uploaded documents is sound. Retain: focused two-category start, personal outreach before ads, 30-day pilot, demo-first selling, offline QR presence, referral rewards. Additions and corrections:

- **SEO is the primary consumer channel, not paid ads.** Sakri-intent queries have near-zero competition. Paid ads only after phase-1 gate.
- **Lead with the emergency directory and mandi rates,** not with business listings. Utility earns the first visit; the directory monetises it.
- **Recruit two or three local "anchors"** — a photographer, a cyber café, a coaching institute owner — as referral partners. In a taluka, three well-connected people outperform any ad budget.
- **The WhatsApp channel is the retention asset.** Opt-in only, one message per day maximum, mostly utility (rates, notices, jobs) with occasional offers. The moment it becomes pure promotion, subscribers leave and never come back.
- **Case study discipline:** publish only measured numbers, exactly as the uploaded plan states.

**Category sequencing:** start with beauty/bridal and coaching (high ticket, high intent, seasonal urgency, photogenic). Add clinics and pharmacies next (trust-driven, feeds the emergency directory). Then home services (highest routing value). Retail and grocery last — lowest willingness to pay, but needed for coverage.

---

## 10. Metrics

**Coverage** — listings live · % verified <90 days · categories with ≥5 listings · villages with ≥10 listings
**Demand** — weekly organic sessions · % from Marathi queries · indexed pages · top-10 rankings for target queries
**Engagement** — call taps · WhatsApp taps · directions taps · profile views · repeat visitors · WhatsApp channel subscribers
**Routing (phase 2)** — enquiries received · % routed · first-response rate · median response time · % marked converted
**Commercial** — paying businesses · revenue by product · renewal rate · CAC per paying business · cost per verification · **businesses receiving ≥1 enquiry/month** (the only cohort that will ever pay)
**Replication** — founder-days and cost to bring taluka #2 to phase-1 metrics

Instrument engagement events from the first commit. Retrofitting analytics loses the baseline permanently.

---

## 11. Legal and compliance

### 11.1 DPDP Act 2023
Owner phone numbers and consumer enquiry data are personal data. Required: purpose-limited consent capture at onboarding (record timestamp, method, and text), a stated retention period, a deletion/correction path, a named grievance officer published on the site, and a breach-notification process. Consent records are a stored artifact, not a policy paragraph.

### 11.2 WhatsApp / Meta
Opt-in must precede any business-initiated message, and opt-out must be honoured immediately. Business-initiated template messages require Meta approval and have real lead time — submit templates in phase 0, not the week you need them. Note the session-window rules for free-form replies. TRAI's UCC framework applies to promotional messaging independently of Meta's rules.

### 11.3 Google Maps ToS
Correctly flagged in the uploaded plan. We do not extract, cache, or republish Maps business names, addresses, reviews, or ratings. We link out to Maps and we collect our own data through owner submission and field verification. Keep geocoding behind a port so the provider can be swapped if terms or pricing change.

### 11.4 Other
GST registration once revenue crosses threshold · invoicing and refund policy before taking money · takedown process for disputed or defamatory content · written media consent from owners for photographs · advertising disclosure on featured placements.

---

## 12. Cost model

**Build:** founder time, plus a part-time field agent from week 4 and a part-time tele-verifier from week 8.

**Infrastructure — a flag.** The stated Azure stack (App Service + PostgreSQL Flexible Server + Redis + Blob) runs roughly ₹10,000–18,000/month at the smallest usable tier. That is a meaningful burn against phase-0 revenue of zero. Recommendation: run phase 0 and 1 on a cheaper footprint — a single VM or a low-cost managed host with Postgres and Redis on the same box — while keeping the code Azure-ready and containerised. Move to the full Azure stack at the phase-2 gate, when there is revenue to justify it. This is a deviation from the stated infra target and is raised deliberately for a decision.

**Ongoing per region:** field agent, tele-verification calls, photography consumables, printing, small ad budget, domain and comms.

**Unit economics to prove in Sakri before replicating:** cost to onboard a listing · cost to verify a listing per year · revenue per paying business per year · % of listings that ever pay. Everything about expansion depends on these four numbers.

---

## 13. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| No repeat consumer usage | **Critical** | Community content (§4.5) as the habit loop; routing as the reason to return |
| Listings go stale, trust collapses | **Critical** | Verification decay engine + public last-verified dates |
| Businesses do not respond to routed enquiries | High | Response-rate badges, fan-out to 3, deprioritise non-responders in ranking |
| Owners will not pay after the free pilot | High | Setup & Shoot takes cash on day one, before goodwill decays |
| Field-agent dependency / single point of failure | High | Document the playbook; agent app makes the role replaceable |
| WhatsApp policy or pricing change | Medium | Keep messaging behind a port; SMS and call fallbacks |
| Google ToS exposure | Medium | Own-data-only policy, geocoding behind a port |
| Founder bandwidth across build + field + sales | **Critical** | Phase gates exist to force a stop/continue decision, not to be skipped |
| Regional competitor or JustDial attention | Low | They ignore taluka markets; that indifference is the window |

---

## 14. Architecture direction (summary only — design happens after this plan is signed off)

- Modular monolith, FastAPI, strict layer boundaries, bounded contexts as packages with enforced import rules
- Contexts: `catalog` · `verification` · `discovery` · `enquiry` · `engagement` · `identity` · `content` · `billing`
- `region_id` on every aggregate from day one
- Ports for every external integration: AI client, embeddings, WhatsApp messaging, object storage, geocoding, OTP, payments
- **Flagged deviations from the stated stack, for decision:** full CQRS read/write separation and a message broker are over-engineering at this stage. Recommend in-process domain events plus a transactional outbox drained by ARQ, and deferring the CQRS split until `discovery` read load justifies a projection. Everything else in the stated stack stands.
- AI is used for four things only: multilingual/transliteration-tolerant semantic search, enquiry intent parsing, 3-language listing copy generation, and photo moderation triage. Not a general chatbot.

---

## 15. Open decisions

| # | Question | Blocks |
|---|---|---|
| Q1 | Brand name and domain | Everything printed, SEO structure |
| Q2 | Legal entity — proprietorship now or private limited | Payments, invoicing, sponsorships |
| Q3 | Founder time available per week | Phase durations are unschedulable without it |
| Q4 | Budget for phase 0–1 field agent | Coverage rate, therefore the phase-1 gate |
| Q5 | Infra footprint for phase 0–1 (§12) | Deployment design |
| Q6 | Two launch categories confirmed | Taxonomy seed, demo profiles, outreach list |
| Q7 | Is there an existing local partner or anchor business already willing | Pilot cohort quality |

---

## 16. Immediate next steps

1. Decide Q1, Q6, and Q3 — these three unblock everything else
2. Build the Sakri locality dataset (villages, pincodes, centroids, market days)
3. Draft the 12 × ~120 taxonomy in mr/hi/en
4. Compile the 150–200 business lead list from public sources, own-data policy enforced
5. Submit WhatsApp Business templates for Meta approval (lead time)
6. Then, and only then: technical design — bounded contexts, schema, ports, API surface
