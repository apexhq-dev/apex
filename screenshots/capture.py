"""Marketing screenshot sweep for Apex.

Seeds realistic data through the real API (finished jobs, a failed job, a
queued job, one actually running CIFAR-10 run against the L4, a live
code-server dev session), then walks every route with Playwright and captures
retina-quality PNGs into ./screenshots/.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://localhost:7000"
OUT = os.path.dirname(os.path.abspath(__file__))
VIEWPORT = {"width": 1440, "height": 900}
DPR = 2


def api(path: str, method: str = "GET", body: dict | None = None) -> dict | list:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        raw = r.read()
    return json.loads(raw) if raw else {}


def wait_for_job_status(job_id: int, status: str, timeout: int = 60) -> dict:
    """Poll until a job reaches the target status (or any terminal state)."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        job = api(f"/api/jobs/{job_id}")
        if job["status"] == status:
            return job
        if status == "running" and job["status"] in ("done", "failed"):
            return job
        time.sleep(1)
    return api(f"/api/jobs/{job_id}")


def seed_data() -> None:
    """Populate the platform with a realistic-looking mix of jobs + a session."""
    print("→ seeding finished jobs …", flush=True)

    # Finished/fast jobs — we use the tiny python image so they finish in <3s,
    # producing "DONE" rows that populate the job list and history table.
    quick = [
        ("resnet50-imagenet-v3", "apex/code-server:python", 'python -c "import time; time.sleep(2); print(\'done\')"'),
        ("bert-eval-squad",      "apex/code-server:python", 'python -c "print(\'evaluated\')"'),
        ("whisper-small-hi",     "apex/code-server:python", 'python -c "print(\'inference ok\')"'),
        ("clip-zero-shot-v1",    "apex/code-server:python", 'python -c "print(\'clip ready\')"'),
    ]
    for name, image, script in quick:
        j = api("/api/jobs", "POST", {"name": name, "image": image, "script": script, "gpu_count": 0, "priority": "normal"})
        wait_for_job_status(j["id"], "done", timeout=30)
        print(f"   · {name} → done", flush=True)

    # A failed job (bogus image) — shows the FAILED badge + error_msg
    print("→ seeding a failed job …", flush=True)
    j = api("/api/jobs", "POST", {"name": "gpt2-custom-tokenizer", "image": "nonexistent:latest", "script": "nope", "gpu_count": 0, "priority": "high"})
    wait_for_job_status(j["id"], "failed", timeout=10)

    # Two queued jobs that will never actually run (because a real CIFAR job is
    # about to monopolise the GPU, and these are normal-priority CPU-only noops
    # blocked behind it).
    print("→ seeding queued jobs …", flush=True)
    api("/api/jobs", "POST", {"name": "llava-13b-eval", "image": "apex/code-server:pytorch", "script": "python /workspace/cifar10_train.py --epochs 1", "gpu_count": 1, "priority": "normal"})
    api("/api/jobs", "POST", {"name": "mistral-7b-lora", "image": "apex/code-server:pytorch", "script": "python /workspace/cifar10_train.py --epochs 1", "gpu_count": 1, "priority": "low"})

    # The marquee running job — real CIFAR-10 training on the L4. 5 epochs
    # runs for ~60s which comfortably outlasts the whole screenshot sweep, so
    # the "RUNNING" badge + live logs are still captured on the very last shot.
    print("→ launching real CIFAR-10 training job …", flush=True)
    j = api("/api/jobs", "POST", {
        "name": "llama3-finetune-v2",
        "image": "apex/code-server:pytorch",
        "script": "python /workspace/cifar10_train.py --epochs 5",
        "gpu_count": 1,
        "priority": "high",  # jumps ahead of the two queued normal/low
    })
    job = wait_for_job_status(j["id"], "running", timeout=60)
    print(f"   · {job['name']} → {job['status']} (id={job['id']})", flush=True)
    # Let it run a few seconds so GPU util actually ticks on the chart AND
    # a handful of training log lines have been printed inside the container.
    time.sleep(10)

    # Dev session — launch via the real code-server image
    print("→ launching dev session …", flush=True)
    try:
        s = api("/api/sessions", "POST", {"image": "apex/code-server:pytorch", "user": "Ajay Kumar"})
        print(f"   · session port={s.get('port')}", flush=True)
    except Exception as e:
        print(f"   ! session failed: {e}", flush=True)


def shot(page, name: str, *, full_page: bool = False) -> None:
    path = os.path.join(OUT, f"{name}.png")
    page.screenshot(path=path, full_page=full_page)
    size = os.path.getsize(path)
    print(f"   ✓ {name}.png  ({size // 1024} KB)", flush=True)


def goto_route(page, hash_route: str) -> None:
    page.evaluate(f"window.location.hash = {hash_route!r}")
    page.wait_for_timeout(600)  # let the router swap + lazy-load


def sweep() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=DPR)
        page = ctx.new_page()

        print("→ opening dashboard …", flush=True)
        page.goto(BASE + "/", wait_until="domcontentloaded")
        page.wait_for_selector(".stat-row", timeout=5000)

        # Let SSE populate at least 2–3 metric ticks so the chart has a visible line
        page.wait_for_timeout(4500)

        print("→ capturing routes …", flush=True)

        # 1. Overview (dashboard tab)
        shot(page, "01-overview")

        # 2. Job history tab
        page.click('.ptab[data-tab="history"]')
        page.wait_for_timeout(800)
        shot(page, "02-job-history")

        # 3. Model registry tab
        page.click('.ptab[data-tab="models"]')
        page.wait_for_timeout(400)
        shot(page, "03-model-registry")

        # 4. Team tab
        page.click('.ptab[data-tab="team"]')
        page.wait_for_timeout(400)
        shot(page, "04-team-tab")

        # Back to dashboard tab before sidebar routes
        page.click('.ptab[data-tab="dashboard"]')
        page.wait_for_timeout(300)

        # 5. Sessions route
        goto_route(page, "#/sessions")
        shot(page, "05-sessions")

        # 6. Metrics route — wait a bit for the big chart to redraw
        goto_route(page, "#/metrics")
        page.wait_for_timeout(1500)
        shot(page, "06-metrics")

        # 7. Images route
        goto_route(page, "#/images")
        shot(page, "07-images")

        # 8. Settings route
        goto_route(page, "#/settings")
        shot(page, "08-settings")

        # 9. Overview + log drawer open over the running job. Find the card
        # whose status badge text is RUNNING — don't rely on list ordering.
        goto_route(page, "#/")
        page.wait_for_timeout(500)
        running_card = page.evaluate_handle("""
          () => {
            const cards = document.querySelectorAll('.job-card');
            for (const c of cards) {
              const badge = c.querySelector('.sbadge');
              if (badge && /RUNNING/.test(badge.textContent)) return c;
            }
            return cards[0] || null;
          }
        """)
        if running_card:
            running_card.as_element().click()
            # Let the WebSocket receive several log lines from the live container.
            page.wait_for_timeout(4000)
            shot(page, "09-log-drawer")
            page.click('.log-close')
            page.wait_for_timeout(300)

        # 10. Overview full-page (entire scrollable content, vertical strip)
        goto_route(page, "#/")
        page.wait_for_timeout(500)
        shot(page, "10-overview-fullpage", full_page=True)

        # 11. Session launch modal
        goto_route(page, "#/sessions")
        page.wait_for_timeout(300)
        page.click('#btn-new-session-big')
        page.wait_for_timeout(400)
        shot(page, "11-session-modal")

        browser.close()
    print("→ done", flush=True)


if __name__ == "__main__":
    if "--skip-seed" not in sys.argv:
        seed_data()
    sweep()
