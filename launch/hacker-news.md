# Hacker News — Show HN draft

## Title (80 char limit)

```
Show HN: Apex – Self-hosted ML platform for a single GPU machine
```

Alternative titles to A/B test:
- `Show HN: Apex – One pip install turns your GPU box into an ML platform`
- `Show HN: Apex – Your GPU. Your team. No cloud tax.`
- `Show HN: Apex – A job queue + dev environment for your GPU workstation`

**Recommendation:** use the first one. "Self-hosted" is a magic word on HN, and
"single GPU machine" signals the scope clearly (this is not Kubernetes).

## URL

```
https://github.com/apexhq-dev/apex
```

(not the landing page — HN readers prefer going straight to the code)

## Body (1,500 char soft limit)

```
Hi HN — I built Apex because I was tired of watching small AI teams burn
$1,000–$3,000/mo on cloud GPUs when they already owned a workstation with
an L4, 4090, or A6000 sitting underutilised.

Apex is a self-hosted ML platform that you `pip install` and run on one
GPU machine. You get:

- A job queue with Docker execution + priority scheduling
- Live GPU/CPU telemetry over SSE (pynvml + psutil)
- Browser-native VS Code dev sessions (code-server in a container, workspace
  mounted, port auto-allocated)
- Full job history + WebSocket log tailing
- JWT auth for multi-user teams

The whole thing is one Python process. The stack is intentionally boring:
FastAPI, SQLite, vanilla HTML/CSS/JS, docker-py, pynvml. No React, no Redis,
no Kubernetes, no helm charts.

The hero GIF in the README is a real CIFAR-10 training run streaming over
WebSocket from inside a container — not a mockup. It hits 66% test accuracy
in 30s on an L4.

Pricing: Free forever for self-hosters (1 seat). Team tier is $29/mo flat
for up to 8 seats, which gets you auth + audit + SSO. Hosted tier for teams
who don't want to run hardware.

It's Apache 2.0. Repo, Dockerfiles, and the CIFAR training script are all
in the README. Would love feedback from anyone running small ML teams off
workstation GPUs — especially on what you'd want in the job scheduler
(DAGs? artifact passing? retry policies?).
```

## First comment (post immediately after submitting)

```
Author here. Happy to answer questions. A few things I'd love to hear
opinions on:

1. The scheduler is currently single-GPU / one-job-at-a-time. How
   important is multi-GPU scheduling for your team? (I've been assuming
   "not that important for 2–8 person teams" but I could be wrong.)

2. Would you want a DAG executor on top of the job queue (a la Airflow /
   Prefect), or is "submit a script, get logs back" enough? I've been
   resisting the DAG temptation because it adds a lot of surface area.

3. What's the most cursed thing your current MLOps setup does that you
   wish you could delete?

Tech details people sometimes ask about:
- SQLite is the only datastore. No Redis, no Postgres. WAL mode, row_factory.
- Metrics are in-memory + persisted to a rolling 24h table for the dashboard.
- Jobs run via `docker.containers.create()` + `.start()` (not `.run()`) so
  we can always clean up on failure — had a painful bug where failed container
  creates left stale state that 409'd the next retry.
- The whole frontend is ~1500 lines of vanilla JS across 5 files. No build
  step, no Node in the loop. Serving it as static files from FastAPI.
- Live demo running on an NVIDIA L4 at [URL] — state is ephemeral, feel free
  to poke.
```

## Tips for the day-of

1. **Submit between 8–11am ET on a Tuesday, Wednesday, or Thursday.** HN peaks
   then; weekend submissions get buried.
2. **Be live in the thread for at least 6 hours.** HN ranks based on early
   engagement; fast, thoughtful replies push the post up.
3. **Upvote-manipulate detection is a thing.** Don't DM friends asking for
   upvotes. Don't use fresh accounts. Don't cross-post within minutes.
4. **The title matters more than anything else.** You can't edit it after
   posting. Pick carefully.
5. **Don't respond defensively to criticism.** "Good point, I'll look into
   it" wins more than "actually you're wrong because..."
6. **Have the landing page + a live demo ready.** HN traffic is brutal; if
   your site falls over, the thread dies.
7. **Screenshot the traffic graph afterwards.** Useful for the post-launch
   Twitter thread and Medium post.

## Common HN objections + honest responses

| Objection | Response |
|---|---|
| "Isn't this just Determined / Weights & Biases / Airflow?" | "Those are all great for bigger teams. Apex is specifically for teams who own ONE GPU machine and want one pip install to get a job queue and VS Code in the browser. No distributed cluster required." |
| "Why not just use Docker Compose + tmux?" | "You can, and for a team of 1 that's often the right call. Apex starts paying off when you have 2+ people sharing a box and want a shared job queue + history." |
| "SQLite won't scale." | "Correct, and that's fine. Apex targets 2–8 people on one GPU machine. SQLite handles that load with room to spare (WAL mode, single writer)." |
| "Why Python + vanilla JS instead of Next.js?" | "Because I wanted `pip install` to be the only install step. Adding Node+npm to the requirements would roughly double the surface area and break the dev experience." |
| "Kubernetes is fine though." | "It's great for bigger teams, but the install friction is enormous. Apex is the 'rpi vs AWS' tradeoff — simpler tool for smaller scope." |
| "How do you handle multi-tenancy/isolation?" | "v0.1 trusts users on the same machine. Containers give you process/fs isolation but not GPU isolation; the assumption is that teammates don't maliciously starve each other. Enterprise multi-tenancy is on the v0.3 roadmap." |
| "What happens when the GPU is busy?" | "Jobs queue. The scheduler picks the highest-priority queued job when the GPU frees up. Single-GPU assumption for v0.1." |
| "Can I run multiple GPUs?" | "Not yet. v0.2 will add multi-GPU scheduling with per-job GPU allocation. If this is a blocker for you, please comment — it'll help me prioritise." |
| "Does it work on Mac?" | "The platform runs on macOS but GPU metrics return nulls (no CUDA). Jobs can still execute as CPU-only Docker containers. M-series GPU support (MLX/MPS) is on the roadmap." |
```
