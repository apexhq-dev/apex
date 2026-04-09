"""Record the Apex hero GIF.

Submits a fresh CIFAR-10 training job, waits for it to start producing log
lines, then records ~15 seconds of the log drawer streaming live training
output via Playwright's built-in video recorder. Converts the webm to an
optimized looping GIF via ffmpeg.

Output: screenshots/hero.gif  (target ~2 MB)
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:7000"
OUT = Path(os.path.dirname(os.path.abspath(__file__)))
WEBM_DIR = OUT / "_video_tmp"
WEBM_DIR.mkdir(exist_ok=True)

# Recording viewport — crop tight on the drawer so the hero asset is
# vertically compact and reads well in social feeds.
VIEWPORT = {"width": 1440, "height": 900}
RECORD_SECONDS = 15


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


def wait_for_running(job_id: int, timeout: int = 60) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = api(f"/api/jobs/{job_id}")
        if j["status"] in ("running", "done", "failed"):
            return j
        time.sleep(0.5)
    return api(f"/api/jobs/{job_id}")


def submit_marquee_job() -> dict:
    # 5 epochs on the L4 takes ~60s which outlasts the 15s recording.
    print("→ submitting fresh CIFAR-10 job …", flush=True)
    j = api("/api/jobs", "POST", {
        "name": "llama3-finetune-v2",
        "image": "apex/code-server:pytorch",
        "script": "python /workspace/cifar10_train.py --epochs 5",
        "gpu_count": 1,
        "priority": "high",
    })
    job = wait_for_running(j["id"])
    print(f"   · job #{job['id']} status={job['status']}", flush=True)
    # Give the container a head start so log lines are already flowing when
    # we click the drawer open.
    time.sleep(6)
    return job


def record(job_id: int) -> Path:
    print(f"→ recording {RECORD_SECONDS}s of log drawer …", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=2,
            record_video_dir=str(WEBM_DIR),
            record_video_size=VIEWPORT,
        )
        page = ctx.new_page()
        page.goto(BASE + "/", wait_until="domcontentloaded")
        page.wait_for_selector(".stat-row", timeout=5000)
        # Let the topbar metrics populate + the chart start drawing.
        page.wait_for_timeout(3000)

        # Find the specific running job card and click it to open the drawer.
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

        # Record window — log lines will stream in during this wait.
        page.wait_for_timeout(RECORD_SECONDS * 1000)

        # Close the page so the video file is finalised.
        video = page.video
        page.close()
        ctx.close()
        browser.close()

        webm = Path(video.path())
    print(f"   · webm saved: {webm.name} ({webm.stat().st_size // 1024} KB)", flush=True)
    return webm


def webm_to_gif(webm: Path, out: Path) -> None:
    """Two-pass ffmpeg conversion for a good looping GIF with custom palette."""
    palette = out.with_suffix(".palette.png")
    print("→ generating palette …", flush=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(webm),
            "-vf", "fps=12,scale=960:-1:flags=lanczos,palettegen=stats_mode=diff",
            str(palette),
        ],
        check=True, capture_output=True,
    )
    print("→ encoding GIF with palette …", flush=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(webm), "-i", str(palette),
            "-filter_complex",
            "fps=12,scale=960:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5",
            "-loop", "0",
            str(out),
        ],
        check=True, capture_output=True,
    )
    palette.unlink(missing_ok=True)
    print(f"   · {out.name}  ({out.stat().st_size // 1024} KB)", flush=True)


def main() -> int:
    job = submit_marquee_job()
    webm = record(int(job["id"]))
    gif = OUT / "hero.gif"
    webm_to_gif(webm, gif)
    # Keep the webm around too — useful for Twitter/Product Hunt which prefer mp4.
    mp4 = OUT / "hero.mp4"
    print("→ encoding mp4 (for Twitter/Product Hunt) …", flush=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(webm),
            "-vf", "scale=1280:-2",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-movflags", "+faststart", "-pix_fmt", "yuv420p",
            str(mp4),
        ],
        check=True, capture_output=True,
    )
    print(f"   · {mp4.name}  ({mp4.stat().st_size // 1024} KB)", flush=True)

    # Cleanup tmp webm dir
    for f in WEBM_DIR.iterdir():
        f.unlink()
    WEBM_DIR.rmdir()
    print("→ done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
