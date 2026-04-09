# Product Hunt — launch kit

Launch day: pick a **Tuesday or Wednesday**, submit the product at **12:01am
PT** (Pacific midnight → beginning of "launch day" on PH). Early submissions
get ~12 hours more voting time than submissions made at noon.

## Product name

```
Apex
```

## Tagline (60 char limit, very strict)

Options (pick one):

1. **`Your GPU. Your team. No cloud tax.`** — 35 chars · the landing tagline
2. **`Self-hosted ML platform for your own GPU`** — 42 chars
3. **`Park, load, launch — on your own GPU`** — 38 chars
4. **`Airflow-lite for your workstation GPU`** — 38 chars

**Recommended: #1.** It's the most evocative and matches every other channel.

## Description (260 char limit)

```
Apex is a self-hosted ML platform for small AI teams. One pip install gives
you a full job queue, live GPU monitoring, browser-native VS Code, and
WebSocket log streaming — all running on the workstation you already own.
No Kubernetes. $29/mo flat.
```

(260 chars exactly)

## Topics / categories

Primary: **Developer Tools**
Secondary: **Artificial Intelligence**, **SaaS**, **Open Source**

Don't select "Marketing", "Productivity", or "Design" — they dilute the
feed relevance and hurt your daily ranking.

## Gallery (screenshots, in order)

PH shows **up to 8** gallery images. Use these in order:

| Slot | File | Caption |
|---|---|---|
| 1 | `01-overview.png` | **Live overview dashboard** — real-time GPU metrics, job stats, submit form, active jobs, dev sessions |
| 2 | `09-log-drawer.png` | **Live training logs** — WebSocket stream of real CIFAR-10 training output from inside a Docker container |
| 3 | `02-job-history.png` | **Full job history** — sortable, filterable table of every job you've ever run |
| 4 | `05-sessions.png` | **Browser-native VS Code** — launch a code-server container with your workspace pre-mounted |
| 5 | `06-metrics.png` | **Real GPU telemetry** — util, VRAM, temp, power, CPU, RAM — every 2s via SSE |
| 6 | `07-images.png` | **Docker integration** — reads directly from your host daemon, no registry required |
| 7 | `hero.gif` | **The whole thing in motion** — looping hero asset |
| 8 | `12-landing-hero.png` | **Landing page** — tryapex.dev |

PH also lets you embed one video prominently — use **`hero.mp4`** there.

## First comment (write this AS the maker, post the moment the listing goes live)

```
Hey Product Hunt — maker here. Apex is what I built after watching my own
team burn $2,000/month on cloud GPU bills when we had an NVIDIA L4 sitting
on a shelf gathering dust.

The short version:
• You own a workstation with a GPU (most small AI teams do)
• You want to use it like a real ML platform, not like an SSH box
• Existing tools (Kubernetes, Determined, Airflow) are built for 50-person
  teams and are painful to install
• Apex is one pip install → full job queue, live GPU metrics, browser VS
  Code, real log streaming

The hero video on the listing is a real CIFAR-10 training run on our
NVIDIA L4, captured live. Nothing staged.

Pricing is deliberately tiny:
• Free forever for solo devs (full feature set)
• $29/mo flat for teams up to 8 seats
• $99/mo hosted (we run it on a rented GPU for you)

It's Apache 2.0. Full source on GitHub. I'd love feedback — especially from
teams who tried the "rent cloud GPUs" route and want to go back to owning
their hardware.

👉 github.com/apexhq-dev/apex
👉 tryapex.dev
👉 discord.gg/apex
```

## Maker bio (reuse across the day's comments)

```
Building Apex, a self-hosted ML platform for small AI teams.
Previously: [your background]
Talk to me about: job schedulers, GPU scheduling, self-hosting, small teams
```

## Day-of strategy

### T-minus 1 week
- Make sure the GitHub repo looks polished (README, good first-issue labels, code of conduct)
- Set up a Discord server (even if empty) — you'll funnel PH traffic there
- Seed the Twitter account with 5–10 relevant posts so it's not a ghost town

### T-minus 24 hours
- Tweet a teaser: "Launching on Product Hunt tomorrow. Sign up to get notified: [PH upcoming page]"
- Message friends who are active PH hunters — ask them if they'd upvote (don't say "please upvote", say "would love your honest feedback")
- Prepare the first 10 replies to anticipated comments (template responses)

### Launch day (Tuesday)

| Time (PT) | Action |
|---|---|
| 12:01 am | Submit the listing. Post first comment immediately. |
| 12:05 am | Tweet the PH launch link with the hero video |
| 12:15 am | Post in relevant Discord servers (where allowed) |
| 1:00 am | Reply to first comments |
| 6:00 am | Morning wave — reply to everyone, cross-post to LinkedIn |
| 9:00 am | Peak voting time begins — be online, reply within 10 min |
| 12:00 pm | Mid-day push — quote-tweet momentum, post in r/LocalLLaMA / r/MachineLearning (carefully, read rules) |
| 6:00 pm | Evening wave — comment on other launches you genuinely like, reply to new Apex comments |
| 11:00 pm | Last push — thank the community publicly |
| 11:59 pm | Screenshot final rank for the post-mortem |

### Rules of engagement
- **Never ask for upvotes directly.** "If you find this useful please consider voting" is fine; "please upvote!!" gets you flagged.
- **Reply to every single comment** within 30 minutes for the first 6 hours, then every 2 hours after that.
- **Be helpful to other makers' launches** that day. They'll remember.
- **Don't respond defensively.** If someone says "this is just Airflow", the right response is "Airflow is great for teams of 50+. Apex is for teams of 2–8 who own one GPU machine. Different scope." — not "you don't understand!!"

## Realistic expectations

**Top 5 of the day** on a Tuesday is achievable if:
- You have a pre-built audience (even 500 Twitter followers helps)
- Your product fits the "developer tool" bucket cleanly (we do)
- Your launch is well-prepared (this kit is the prep)
- You're active in the thread all day

**Top 10** is achievable with just the kit and basic hustle.

**Top 20** is almost guaranteed as long as the product actually works.

Don't sweat the ranking too much — **the real goal is the traffic**.
Top-20 launches get ~5,000 unique visitors to their landing page on launch
day. That's what you're actually after.

## Post-launch

- **Day 2:** post the metrics publicly ("24 hours on PH: X installs, Y discord joins, Z emails")
- **Day 7:** email every Discord member personally asking about first-use friction
- **Day 14:** follow-up blog post: "What launching on Product Hunt actually got us"

## Link helpers

Share-friendly URLs for the thread:
- https://www.producthunt.com/posts/apex — the listing (get the real slug after submit)
- https://github.com/apexhq-dev/apex — for the engineers
- https://tryapex.dev — for the founders/skimmers
- https://discord.gg/apex — for the community builders
