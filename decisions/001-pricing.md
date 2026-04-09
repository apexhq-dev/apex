# Decision 001 — Pricing model

**Status:** DECIDED · 2026-04-08
**Supersedes:** the temporary "$5 / mo" placeholder shown on the sidebar plan card

---

## Decision

Apex ships with **three tiers**:

| Tier | Price | Included | Target user |
|---|---|---|---|
| **Free (self-hosted)** | $0 | Full feature set · 1 seat · community support · all Docker images · unlimited jobs · unlimited dev sessions | Indie devs, students, anyone evaluating the product |
| **Team (self-hosted)** | **$29 / month** flat, billed annually ($348/yr) | Everything in Free · up to 8 seats · multi-user auth · audit log · priority email + Discord support · SSO (Google/GitHub) · license key | Small AI/ML teams (2–8 people) with their own GPU workstation |
| **Hosted** | **$99 / month** starting, + GPU pass-through | Apex managed on a rented GPU (RunPod / Lambda / our metal) · no install, no maintenance · SLA · backups | Teams who want a GPU workstation without running one physically |

All prices are in **USD**. The `$5/mo` display on the sidebar is replaced with `$29 / mo` on the same card — same position, same format, new number.

## Why this shape

### Why free includes the full feature set
- The viral-growth engine for self-hosted dev tools is *"I installed this on my workstation, it just worked"*. Gating features behind Team tier at this stage kills word-of-mouth.
- Apex's costs to serve the free tier are **zero** — users run it on their own hardware.
- The only things Team tier gates are **multi-user features** (auth, audit, seats) which are genuinely valuable to teams of 2+ and genuinely useless to solo users.

### Why $29 flat instead of $5/seat
- $5/seat sounds cheap but adds procurement friction: finance teams have to model seat counts.
- $29/mo flat is **cheaper than one Lambda H100 hour** ($2.99/hr × 10 hr/mo = $30). The comparison writes itself.
- Flat pricing eliminates the "do we buy 4 or 8 seats" decision — just $29, up to 8 seats included.
- 8 seats matches the target team size (2–8 people) from the SPEC.

### Why $99 for hosted
- Anchors the "self-host and save" story: $29 self-hosted vs $99+ hosted makes the cheaper option feel like a no-brainer.
- Gives us a high-margin upsell path for teams who don't want to run hardware.
- GPU cost is pass-through (we don't absorb it), so our marginal cost is low.

## What changes in the product

- **Sidebar plan card:** `6 of 8 seats · $5 / mo` → `6 of 8 seats · $29 / mo`
- **Settings route:** add a "Plan" row showing `Team · $29/mo · renews YYYY-MM-DD`
- **Landing page pricing section:** three columns, Team column highlighted as "Recommended"
- **README:** add a "Pricing" section with the same table
- **`/api/users/invite` gate:** enforce the 8-seat limit (currently unenforced)

All product changes other than the sidebar copy update are **deferred** — not blockers for launch. Launch can ship with pricing displayed on the landing page and the $29 label on the sidebar; enforcement + Settings integration can follow in v0.2.

## Revenue projection (rough)

Assume 90-day launch metrics from MARKETING.md §6:

- **1,000 `pip install`s** → **50 weekly active servers** (5% convert from install to real use)
- Of the WAS, **10–20 convert to Team tier** (2–4%) → **$290–$580 MRR**
- Of the WAS, **1–3 convert to Hosted** (0.1–0.5%) → **$99–$400 MRR**

**Total 90-day MRR target: $400–$1,000.**

This isn't enough to fund the project but proves willingness-to-pay. The real goal of the pricing is **validating the conversion rate**, not funding v1.

## Open questions (non-blocking)

- Annual vs monthly billing default? (Annual — saves ~15% processing fees, improves cashflow, reduces churn)
- Student discount? (Skip for now; free tier serves students fine)
- Non-profit / academic discount? (50% off Team tier — easy to honour manually via Stripe coupons)
- EU VAT? (Use Stripe Tax, don't build it)
- Crypto payments? (No, skip indefinitely)
