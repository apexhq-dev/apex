# Decision 002 — License

**Status:** DECIDED · 2026-04-08

---

## Decision

Apex ships under the **Apache License 2.0**.

## Options considered

| License | Pro | Con | Verdict |
|---|---|---|---|
| **MIT** | Shortest, most permissive, easy to explain | No explicit patent grant → scary for enterprise legal | ❌ |
| **Apache 2.0** | Explicit patent grant, OSI-approved, enterprise-friendly, compatible with most copyleft | Slightly more text than MIT | ✅ **chosen** |
| **BSD-3-Clause** | Similar to MIT, adds no-endorsement clause | No patent grant, no enterprise advantage over Apache | ❌ |
| **GPL v3** | Forces derivatives to open-source | Kills enterprise adoption dead; hostile to the self-host target market | ❌ |
| **AGPL v3** | Closes the "SaaS loophole" of GPL | Even more hostile than GPL; blocks our own future hosted tier | ❌ |
| **BSL 1.1** (Business Source License) | Delays competitive commercial use for N years, then converts to Apache | Scares devs, creates trust issues, not OSI-approved | ❌ |
| **Fair-source (SSPL)** | Allows "non-commercial-adjacent" use | MongoDB's blown reputation from this; not OSI | ❌ |
| **Elastic License 2.0** | Allows everything except "managed service" reselling | Not OSI-approved, small adoption | ❌ |
| **PolyForm Noncommercial / Shield** | Restricts commercial use | Kills enterprise path, hostile to the audience | ❌ |

## Why Apache 2.0

1. **OSI-approved and universally recognised.** Enterprise legal departments have a pre-approved list; Apache 2.0 is on every one.
2. **Explicit patent grant.** Contributors and users are protected from patent trolling by either side. MIT doesn't give you this.
3. **Compatible with our hosted tier.** Apache 2.0 doesn't force us to open-source anything we add on top (e.g. the hosted control plane, billing integration, proprietary extensions).
4. **Standard for the neighbourhood.** PyTorch, TensorFlow, Kubernetes, Docker, HuggingFace Transformers, Ray, LangChain, vLLM, llama.cpp — all Apache 2.0. Users won't even blink.
5. **No commercial use restrictions.** The "someone might resell this!" fear is overblown for a tool that runs on user hardware. If someone packages Apex into a hosted service and undercuts our hosted tier, that's a competition problem, not a license problem, and Apache lets us move fast enough to stay ahead.

## What does NOT work for us

- **Any copyleft license (GPL, AGPL).** Our target buyer is a small AI/ML team inside a company. Their legal team sees "GPL" and the procurement conversation ends. Immediate adoption death.
- **Source-available / delayed-open licenses (BSL, SSPL, Elastic).** These feel defensive and scare developers. HashiCorp, MongoDB, Elastic, Redis all learned this the hard way. The marginal protection isn't worth the signalling cost.
- **Noncommercial licenses.** Kill the path to paying Team-tier customers.

## Files to add

1. `LICENSE` — full Apache 2.0 text
2. `NOTICE` — attribution file required by Apache 2.0 §4(d)
3. `pyproject.toml` — add `license = { text = "Apache-2.0" }` + `classifiers = ["License :: OSI Approved :: Apache Software License"]`
4. README → Footer: `Apache 2.0 © 2026 Apex contributors`
5. Every source file → header comment (optional but nice):
   ```python
   # SPDX-License-Identifier: Apache-2.0
   # Copyright 2026 Apex contributors
   ```

## What we're explicitly NOT doing

- **CLA (Contributor License Agreement).** Too much friction for early contributors. DCO (sign-off in commits) is enough.
- **Dual-licensing.** Common pattern (e.g. GPL + commercial), but Apache 2.0 alone gives us everything we need without the complexity.
- **Trademark policy.** Not needed for v0.1. Add if the name starts being abused.
