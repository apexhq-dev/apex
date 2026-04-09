# Twitter/X launch thread

10 tweets. Post from the Apex account. Schedule 2–3 hours after the HN launch
(so the HN link in tweet 10 already has some traction).

All character counts fit in 280. Emoji count: minimal (they read as cringe
to the HN/dev crowd).

---

## Tweet 1 — the hook

```
Your AI team is renting GPUs.

You already own a workstation with an L4, 4090, or A6000.

I built Apex so you can stop paying cloud tax and start using the
hardware sitting on your desk.

pip install apex && apex start

[attach hero.mp4]
```

Why this tweet: combines the pain (cloud bill), the obvious question (why
aren't you using your own hardware?), and the solution (one install).
Hero video auto-plays in timeline.

---

## Tweet 2 — the video caption

```
That's a real CIFAR-10 training run streaming over WebSocket from inside
a Docker container.

Not a mockup. Not a demo with faked data. 141k-param CNN hitting 66%
test accuracy on an NVIDIA L4 in ~30 seconds.

Everything you see on the dashboard is live.
```

Why: proves the product is real before the thread gets deeper.

---

## Tweet 3 — the math

```
The math is silly once you run it:

• RunPod RTX 4090:      $316/mo at 24×7
• Lambda H100:          $2,150/mo at 24×7
• AWS p4d.24xlarge:     $23,594/mo at 24×7

• Your workstation + Apex: $29/mo

One of these is not like the others.

[attach screenshots/06-metrics.png]
```

Why: Twitter loves concrete numbers. Ends with a punchline.

---

## Tweet 4 — feature: job queue

```
Apex gives you a real job queue:

- Submit via UI or curl
- Priority scheduling (high > normal > low)
- Docker execution with full GPU access
- WebSocket log tailing
- Full history, sortable, filterable
- Cancel running jobs, retry failed ones

Airflow-lite for people who own one GPU.

[attach screenshots/02-job-history.png]
```

---

## Tweet 5 — feature: dev sessions

```
And browser-native VS Code. One click.

Apex spins up a code-server container with your workspace pre-mounted.
GPU attached. Full VS Code, all the extensions you know. Running at
localhost:8080.

Two clicks from pip install to coding inside your GPU.

[attach screenshots/05-sessions.png]
```

---

## Tweet 6 — the stack flex

```
The whole thing is intentionally boring:

✓ FastAPI + Uvicorn
✓ SQLite (one file)
✓ pynvml for GPU telemetry
✓ docker-py for containers
✓ Vanilla HTML/CSS/JS — no build step, no Node in the loop

Things Apex does NOT need:

✗ React
✗ Redis
✗ Postgres
✗ Kubernetes

One Python process. One pip install.
```

Why: shows technical taste. The dev-tool crowd respects restraint.

---

## Tweet 7 — the unlock

```
Here's what actually unlocks with Apex:

A 3-person team shares one workstation. Previously they were either:
(a) screaming on Slack about who gets the GPU, or
(b) paying $500/mo for RunPod to avoid the fight.

Now they have a shared job queue with priority and live logs. $29/mo.
```

Why: the customer story. Shifts from "what it is" to "what it changes."

---

## Tweet 8 — pricing

```
Pricing is deliberately simple:

• Free forever, 1 seat, full feature set — for solo devs
• $29/mo flat, 8 seats — for small teams
• $99/mo hosted — if you want us to run it on a rented GPU

All tiers run the same code. All of it is Apache 2.0.
Free tier has everything. Paid tier unlocks the multi-user bits.
```

---

## Tweet 9 — credibility

```
A few things I'm proud of in the v0.1 build:

• The scheduler uses `containers.create() + .start()` instead of `.run()`
  so it can clean up on failure. (Docker SDK leaves half-created
  containers behind if `.run()` throws mid-start.)

• The log drawer is a real WebSocket to `container.logs(stream=True)`.
  No polling, no refresh. Attach-on-click, detach-on-close.

• Metrics are SSE (not WebSocket), pushed every 2s from a background
  thread into a shared dict. The frontend has ONE EventSource for the
  whole session.

• Frontend is ~1500 LOC of vanilla JS across 5 files. The router is
  hash-based and fits in 40 lines.

The SPEC.md is 700 lines and Claude Code built the whole thing from it.
```

Why: technical credibility for the HN/dev crowd. Ends with the
#buildinpublic angle.

---

## Tweet 10 — the CTA

```
If you run a small AI/ML team and you own a GPU, give it a shot:

→ pip install apex && apex start
→ GitHub: github.com/apexhq-dev/apex
→ HN thread: [LINK]
→ Docs + install guide: tryapex.dev

Feedback welcome. I'm in the HN thread for the next ~6 hours.
```

---

## Scheduling

- Tweet 1: **T+0** (main post)
- Tweets 2–10: reply chain, 30 seconds between each (so Twitter threads them but doesn't rate-limit)
- Pin the thread to the @apexhq profile
- Tweet 1 also posts to LinkedIn separately with the same text + video

## Tags + people to @ (tweet 10)

Real accounts to tag — pick 2–3 max, don't spray:

- `@levelsio` — solo founder, #buildinpublic audience, pro-self-hosted
- `@mckaywrigley` — ML tool builder, huge dev audience
- `@swyx` — DX-focused, amplifies well-made dev tools
- `@simonw` — Simon Willison, datasette author, appreciates simple tools
- `@_philschmid` — HuggingFace, ML audience
- `@karpathy` — too big to realistically reach but worth trying ONCE

Don't tag more than 3. Twitter downranks posts with more.

## What to do after

- **Every reply gets a response within 30 minutes** for the first 4 hours
- **Screenshot the best replies** for follow-up posts ("@someone's reaction")
- **Boost the thread on LinkedIn** 6 hours later with "HN community reaction" angle
- **Day 2**: write a quote-tweet with "24 hour numbers" if things went well
- **Week 1**: write a thread about a specific feature that got the most
  questions, linking back to the original launch thread
