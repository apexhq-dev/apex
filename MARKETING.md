# Apex — Marketing Strategy

> Drafted 2026-04-08. Living document — update as launches happen and data comes back.

Short answer: **yes, you need a website**, and the core strategy should be
"dev-tool-style launch" not "SaaS-style sales funnel."

---

## 1. Positioning first (before any channel)

Everything downstream depends on nailing this. Anchor on three claims:

|        | Apex                                                                 | What it's not                              |
|--------|------------------------------------------------------------------------|--------------------------------------------|
| **Who**  | 2–8 person AI/ML teams with their own GPU box                          | Not enterprises, not solo hobbyists        |
| **What** | A full job queue + dev environment for one GPU machine, installed with `pip` | Not Kubernetes, not a cloud, not a notebook |
| **Why**  | Replace $400–$4,000/mo in cloud GPU spend with hardware you already own | Not "another MLOps platform"               |

**Tagline:** *"Your GPU. Your team. No cloud tax."* — keep it. The emotional
hook is *cloud bill guilt* — every small ML team has felt it.

**Competitive whitespace:** the market is barbelled — enterprise MLOps
(Determined, Weights & Biases, Databricks) on one end and "rent a pod"
(RunPod, Lambda, Modal) on the other. Almost nothing good exists for "we own
the hardware, we just need the software layer to be usable." SkyPilot is the
closest thing and it's still DevOps-flavoured. That's the gap.

---

## 2. Yes, you need a website

Not a sales site — a **dev-tool landing page**. These convert 5–10× better
than SaaS pages for this audience.

### Minimum viable site (one page is fine)

1. **Hero** — tagline, one sentence, install command in a big monospace box. Auto-copyable.
   ```
   pip install apex && apex start
   ```
2. **Animated hero demo** — a 10-second loop of the log drawer screenshot
   with real CIFAR training streaming. Use `09-log-drawer.png` as the first
   frame, then a looped GIF or `<video>`. This is the single most persuasive
   asset we have.
3. **The math** — a 3-line comparison:
   - RunPod RTX 4090: ~$0.44/hr = **$316/mo** at 24×7
   - Lambda H100: ~$2.99/hr = **$2,150/mo**
   - Your workstation + Apex: **$5/mo**
4. **Feature grid** — 6 tiles, each one a screenshot from `/screenshots/`:
   - Overview dashboard (`01-overview`)
   - Live training logs (`09-log-drawer`)
   - Browser VS Code in one click (`05-sessions`)
   - GPU metrics (`06-metrics`)
   - Job history (`02-job-history`)
   - Pre-built Docker images (`07-images`)
5. **"How it works" in 3 steps** — install, point at workspace, submit job. Make it feel trivially easy.
6. **Pricing box** — single tier, no "Contact sales", no enterprise ladder.
7. **GitHub star count + install count** — social proof.
8. **Footer** — Discord, Twitter, docs, GitHub.

### Tech
- Build on **Vercel + Astro** or plain HTML. It's a marketing page, not a SaaS app.
- Should take 1–2 days.

### ✅ Name decision: Apex

The project was originally called *Runway*, which collided with RunwayML
(video AI). After an availability sweep on PyPI and GitHub, **Apex** won:

- `pip install apex` — bare single-word package name is FREE on PyPI
- Aviation metaphor: an apex is the airport area where aircraft **park,
  load, fuel, and launch** — exact match for what the product does to ML jobs
- 5 letters, one syllable, memorable
- Zero collisions with existing ML/AI tools (unlike Hangar, which is taken by
  a tensor-data-versioning package in the same space)
- SEO greenfield — owning "apex ml" from day 1

**Candidates that were eliminated:**

| Name | Verdict |
|---|---|
| ~~Runway~~ | Collides with RunwayML (video AI) |
| ~~Hangar~~ | `pip install hangar` = ML tensor versioning tool — direct space collision |
| ~~Forge~~ | `forge_ml` taken on PyPI |
| ~~Dock~~ | `dock 0.0.1` = "Batch job queue for ML inference" — worst possible collision |
| ~~Berth / Kiln / Dyno / Lathe / Rig~~ | All taken bare on PyPI |

**Domain candidates to buy** (once the rename is executed):

- `apex.dev` — clean, developer-focused
- `apex.sh` — even more dev-tool native
- `apexml.com` — safe fallback
- `tryapex.com` / `getapex.com` — conversion-friendly

---

## 3. Pricing — rethink before launching

$5/mo is a suspiciously cheap number. Three problems:

1. **Self-hosted tools usually aren't subscription-priced** — they're either
   free+OSS, charge for a license, or upsell a hosted version. Charging $5/mo
   for software that runs entirely on user hardware looks strange unless we
   tie it to something they can't self-serve.
2. **It's too cheap to fund us, too expensive to convert the OSS crowd.**
   $5/mo kills the free-tier experiment that drives word-of-mouth.
3. **What exactly does the $5 unlock?** If it's nothing enforced, people won't pay.

### Recommended three-tier model

| Tier                    | Price                           | What they get                                                                 |
|-------------------------|---------------------------------|-------------------------------------------------------------------------------|
| **Free (self-hosted)**  | $0                              | Full feature set, 1 seat, community support. This is the viral engine.        |
| **Team**                | $29/mo flat *or* $5/seat/mo     | Multi-user auth, audit log, Discord-to-team support, priority issues          |
| **Hosted**              | $99/mo+                         | We host it on a rented GPU (pass-through cost + margin). Optional.            |

The dashboard can *display* "6 of 8 seats · $5/seat/mo" exactly as-is with
this model — that maps to a paying Team tier.

If we want to keep $5, make it **$5 per seat per month** (so 8 seats = $40),
which is industry standard for tools like Linear, Slack, Figma.

---

## 4. Launch channels, ranked by ROI

This is a technical product for technical buyers, so distribution is
different from a normal SaaS launch. **Order matters.**

### Week 0 — quiet prep
- Ship the website
- Open-source the repo on GitHub
- Write a README that's as good as the landing page — GitHub is often the first point of contact
- Set up a `@apex` (or renamed) Twitter account
- Create a Discord server — empty but ready

### Week 1 — warm launch
- **Post on Hacker News** (single biggest spike source for dev tools — can do 10k+ visitors in a day)
  - Title: `Show HN: Apex — self-hosted ML platform for a single GPU machine`
  - Lead with the log-drawer GIF
  - Be present in the thread for 6+ hours to answer questions (this matters a lot for HN ranking)
- **Twitter thread** — 8–10 tweets, one per feature, with screenshots. Tag @levelsio, @mckaywrigley, @_philschmid, @swyx — people who retweet good dev-tool launches
- **r/LocalLLaMA** — explicit fit, they'll love this. Post after HN.
- **r/selfhosted** — also explicit fit.

### Week 2 — content push
- **Dev.to technical post** — *"How I built a GPU job scheduler in 500 lines of Python"* (deep technical piece; attracts engineers)
- **Medium post** — *"We were spending $2,000/month on cloud GPUs. We moved to a single RTX 4090 and haven't looked back."* (story/case-study piece; attracts founders)
- **60-second YouTube demo** — Fireship style. Quick cuts, real footage. No voiceover needed.
- **Product Hunt** — launch on a Tuesday or Wednesday morning PT. Use the carousel we built.

### Week 3+ — sustained
- **Weekly LinkedIn posts** using the 11 screenshots as a rotating carousel
- **Comment on every "cloud GPU pricing is too high" thread** on X / HN / Reddit with a single honest reply
- **Reach out to 10 specific small-team AI founders** with a personal message — slow but highest-conversion
- **Sponsor one small ML newsletter** if budget allows (e.g. `The Batch`, `Last Week in AI`, ~$500–$2,000 per sponsorship)

---

## 5. Content pillars (next 3 months)

Not random posts — three recurring themes that build a narrative:

1. **"Cloud bill horror stories"** — anonymous submissions of people's GPU bills. Lightweight, viral, positions us as the antidote.
2. **"One-GPU benchmarks"** — how fast can you fine-tune Llama-3-8B / train CIFAR / run Whisper on a 4090? Concrete numbers. Engineers love this.
3. **"Build logs"** — every feature we ship, a one-paragraph post with a before/after screenshot. Builds #buildinpublic cred and gives us something to post weekly.

---

## 6. Metrics that actually matter

Don't track vanity. Track these, in order:

| Metric                 | Target (90 days) | Why                                  |
|------------------------|------------------|--------------------------------------|
| `pip install` count    | 1,000            | Proxy for real users                 |
| GitHub stars           | 500              | Social proof + HN ranking fuel       |
| Discord members        | 100              | Direct support channel               |
| Weekly active servers  | 100              | Actual retention                     |
| Paid conversions       | 10–20            | Revenue signal                       |
| Signups from HN launch | Baseline         | Channel ROI                          |

Instrument `apex start` to ping a telemetry endpoint (**opt-out**,
anonymous) so we can see install/DAU without surveying users. Respect
privacy — just send `{version, first_seen, uuid}`.

---

## 7. The 14-day action plan

| Day | Action                                                                                |
|----:|----------------------------------------------------------------------------------------|
|   1 | ✅ **Rename → Apex.** DONE — package, CLI, docs, static assets all renamed.            |
|   2 | ✅ **Landing page built** — `website/index.html`, zero dependencies, deploy-ready.      |
|   3 | ✅ **Hero GIF + MP4 recorded** — `screenshots/hero.gif` (2MB), `hero.mp4` (497KB).     |
|   4 | Push the repo to GitHub with a README that matches the landing page quality.           |
|   5 | Write the Hacker News post draft. Sleep on it.                                          |
|   6 | ✅ **Telemetry built** — opt-out via `APEX_NO_TELEMETRY=1`, sends `{v, id}` on start.  |
|   7 | Soft-launch to friends + 5 target users for feedback. Fix the top 3 issues.             |
|   8 | **Hacker News launch.** Be live in the thread.                                          |
|   9 | Twitter thread + Reddit cross-posts.                                                    |
|  10 | Write the "cloud bill" Medium post.                                                     |
|  11 | Reply to every HN comment, email every HN signup personally.                            |
|  12 | Product Hunt launch prep.                                                               |
|  13 | **Product Hunt launch.**                                                                |
|  14 | Decompress. Look at numbers. Write post-mortem.                                         |

---

## 8. One thing that'll make or break this

**The log drawer GIF.** That's our entire marketing asset in one image. If we
can get someone to look at 5 seconds of CIFAR training loss dropping in
real-time inside a dark cyberpunk UI, they will install. Lead with it
everywhere — HN, Twitter, landing page hero, Product Hunt thumbnail, every
single LinkedIn post.

Make a crop or a short screen recording (`ffmpeg` can convert a Playwright
video to a 2MB GIF) and treat it as the hero asset for the next six months.

Source file to start from: `screenshots/09-log-drawer.png`.

---

## Open decisions (blocking launch)

- [x] ✅ **Product name** — RESOLVED: **Apex**. Renamed across the codebase.
- [x] ✅ **Landing page** — built, implementation details stripped, deploy-ready.
- [x] ✅ **Hero GIF/MP4** — recorded, in `screenshots/`.
- [x] ✅ **Telemetry** — anonymous opt-out ping built into `apex start`.
- [ ] **Domain purchase** — recommend `apex.dev` or `apex.sh` (see §2 above)
- [ ] **Pricing model** — free + $29/mo Team + hosted? Or $5/seat flat? Decide before the landing page goes up
- [ ] **License** — Apache 2 in the code — confirm this is the final call
- [ ] **Hosting story** — do we offer a managed version day 1, or purely self-host for launch?
- [ ] **GitHub org name** — `apexhq`? `apex-dev`? (the bare `apex` user is an abandoned personal account)

## Assets already built (ready to use)

- `screenshots/01-overview.png` through `11-session-modal.png` — full marketing screenshot set
- `screenshots/09-log-drawer.png` — hero asset (log drawer + real CIFAR training)
- `docker/python.Dockerfile` and `docker/pytorch.Dockerfile` — reproducible demo images
- `apex-workspace/cifar10_train.py` — live training demo for GIF recording
- Live demo URL (temporary, on Lightning Studio): https://7000-01knpzs5jwa179bqf86tkd4x19.cloudspaces.litng.ai
