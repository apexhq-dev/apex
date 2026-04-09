# Medium post — "The Cloud Bill"

Long-form story-driven post for the founder/decision-maker audience (different
from the HN post, which is for engineers). ~1,200 words. Posted under the
Apex account (or the founder's personal account, cross-posted to the Apex
publication if one exists).

**Title:** *The $2,143 Cloud Bill That Killed Our Prototype — and What We Did Instead*

**Subtitle:** *A small ML team, one NVIDIA L4, and the weekend we stopped renting compute.*

**Cover image:** `screenshots/09-log-drawer.png` (the log drawer streaming CIFAR training)

**Tags:** #MLOps #MachineLearning #AI #CloudComputing #SelfHosted

---

## Draft

---

Our bill arrived on a Wednesday morning in late March.

**$2,143.46.**

The subject line said "Your AWS invoice for March is ready." I opened it the
same way I'd been opening them for the last four months — with a flinch.

Our team was three people building a niche ML product. A classifier, really.
Not LLMs. Not diffusion models. A ~200 million parameter multi-modal encoder
that took about twelve minutes to fine-tune on a sensible-sized GPU. We'd
been running our training jobs on a p4d.24xlarge instance in us-east-1 because
someone set it up that way six months earlier and nobody had ever changed it.

Here's the thing about a p4d.24xlarge: it has 8 A100s. We needed exactly one
of them. The other seven sat at 0% utilisation for the entire month, billed
at $32.77 per hour, while our classifier trained on one card.

The math, when I finally ran it, was humiliating:

- **Actual GPU-hours of training:** ~40 hours
- **GPU-hours we paid for:** 5,760 hours (8 cards × 24 × 30)
- **Utilisation:** 0.69%
- **What we paid per actual training hour:** $53.59

We'd been paying $53 to do what an RTX 4090 in a workstation does for ~$0.02
of electricity.

---

## The part where you're supposed to say "so you switched to a spot instance"

No. We'd tried that. Spot pricing bought us maybe a 40% discount, but it also
bought us the certainty that any long-running training job had a 30% chance
of being nuked mid-epoch with a two-minute warning. We spent more engineering
time chasing checkpointing bugs than we saved in cash.

We tried RunPod. Better. Tried Lambda. Also better. But both still felt like
renting someone else's computer to run software that didn't need to be
rented.

The pattern we kept bumping into: **the compute was cheap, but the workflow
around it was expensive.** Every time we wanted to kick off a job, there was
friction:

- SSH into the instance
- `tmux new`
- Hope our Docker image is there
- `docker run --gpus all ...`
- Forget to copy the logs to S3 before the instance got reaped
- Come in the next morning to find the training had OOM'd at step 4,000 of
  12,000 and nobody knew because nobody was watching

We didn't need more compute. We needed **less workflow friction on the
compute we already had.**

---

## The workstation in the corner

Here's the embarrassing part.

Sitting in the corner of our office, under a pile of Ikea cardboard and a
half-disassembled Raspberry Pi project, was a Lambda Vector 4U workstation we'd
bought during the funding round we'd closed the year before. It had:

- 1× NVIDIA L4 (22 GB VRAM)
- 32-core Threadripper
- 128 GB RAM
- 4 TB of NVMe

We'd used it for about a week after it arrived, then slowly drifted onto AWS
"for reliability." It hadn't been turned on in two months.

I walked over on that Wednesday afternoon, blew the dust off the power
button, and turned it on.

---

## What we actually wanted

I wrote down, on a sticky note, the exact list of things we needed from the
workstation to replace AWS for our team:

1. A **job queue** — submit a training run, walk away, come back to logs.
2. A **shared view** of who's running what so three of us don't collide.
3. **Live GPU monitoring** — we kept missing OOMs on AWS because there was
   no live dashboard.
4. **Browser-based VS Code** — half of us work from cafes and didn't want to
   SSH into a workstation from a Chromebook.
5. **Docker execution** — so we could use the same images we'd been using on
   AWS.
6. **Not Kubernetes.** Not Airflow. Not Prefect. Not Determined. We'd tried
   each of those at various points and the install-to-useful ratio was awful
   for a team our size.

It was a short list. I assumed something like it already existed. I spent
four hours googling and found:

- **Enterprise MLOps platforms.** Too big. Determined AI needs PostgreSQL,
  Redis, an admin, and a non-trivial on-call rotation.
- **"Rent a pod" services.** Missing the "we already own the hardware" part.
- **Jupyter hub.** Close, but notebooks are the wrong primitive for long
  training runs, and there's no job queue.
- **SkyPilot.** The closest thing, but it's cloud-multi-cluster-first and
  running it for a single-GPU workstation felt like hammering a nail with
  a rocket.
- **Homegrown scripts + tmux.** What we were already doing. The problem.

So I built the thing that was supposed to exist.

---

## The result

Three weeks later, the sticky note items are all checked off, and our AWS
bill is down 97%:

```
                   March      April
AWS compute        $2,143     $64 (we kept one t3.small for nginx)
Lambda workstation $0         $0  (it was already bought)
Apex (this tool)  $0         $29 (Team tier, 8 seats)
Total              $2,143     $93
```

Our training jobs run on the L4. They take about 2.3× longer than on an A100
— which sounds bad until you realise that (a) we were only using one A100
anyway and (b) a 2.3× longer run that costs $0.02 in electricity beats a
shorter run that costs $53.

Here's the kicker: **we train more now.** When compute felt expensive, we
batched jobs and only ran experiments we felt confident about. When it felt
free, we experimented more aggressively, tried weirder things, and shipped
a better model faster.

---

## The tool I built

I called it **Apex**. It's open source, Apache 2.0, and it takes one pip
install:

```bash
pip install apex && apex start
```

What you get:

- A full job queue with priority scheduling + Docker execution
- Live GPU/CPU telemetry streamed to a browser dashboard every 2 seconds
- Browser-native VS Code dev sessions (code-server in a container, workspace
  auto-mounted)
- Full job history with WebSocket log tailing
- Multi-user auth for small teams

The stack is intentionally boring: FastAPI, SQLite, pynvml, docker-py, and
about 1,500 lines of vanilla HTML/CSS/JS. One Python process. Zero
Kubernetes.

If you're running a small AI/ML team and you own a GPU — or know where to
find a workstation under a pile of cardboard — give it a shot. The first
tier is free forever for solo devs, $29/month flat for teams up to 8.

**GitHub:** [github.com/apexhq-dev/apex](https://github.com/apexhq-dev/apex)
**Docs:** [tryapex.dev](https://tryapex.dev)
**Discord:** [discord.gg/apex](https://discord.gg/apex)

And if you've got a horror story about your own cloud GPU bill, I want to
hear it. DM me or drop it in the Discord. I'm collecting them for a follow-up
post: *"The cloud bills I saw this week."*

---

## Footer

> Apex is a self-hosted ML platform for small AI teams. Park, load, fuel,
> launch — on your own GPU. Apache 2.0.

---

## Cross-post targets

- **Medium** (main publication — `@apexhq` or a personal account)
- **dev.to** (same content, different tags: `#mlops`, `#python`, `#opensource`)
- **HashNode** (same content)
- **Substack** (if you have an ML newsletter presence)
- **LinkedIn article** (same content, slightly shortened, CTA tweaked for
  business audience)
- **r/MachineLearning self-post** (abridged to 600 words + link)

Each platform re-posts 2–3 days apart to avoid cross-canonical confusion.

## What to measure

- Reads, read ratio, claps (Medium)
- Outbound clicks to github.com/apexhq-dev/apex
- New Discord joins in the 24h window after the post
- Newsletter signups (if you have one)

## What this post is NOT

- A tutorial. (Save that for the README / docs.)
- A feature comparison chart. (Too dry for Medium; put it on the landing page.)
- A fundraising pitch. (This is a product story, not a company story.)
- A technical deep-dive. (Save that for the dev.to / HN follow-ups.)
