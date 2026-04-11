"""Background scheduler worker thread.

Runs a loop every 3s: pick the next queued job by priority, if the GPU is free
launch it via Docker, spawn a watcher that blocks on container.wait(), and
update status on exit.
"""
from __future__ import annotations

import threading
import time

from apex import docker_mgr
from apex.scheduler import queue

_started = False
_stop = threading.Event()
POLL_INTERVAL = 3.0


def _watch_container(job_id: int, container_id: str) -> None:
    try:
        container = docker_mgr.get_container(container_id)
        result = container.wait()
        exit_code = int(result.get("StatusCode", -1))
        err = result.get("Error") or None
        err_msg: str | None = None
        if err:
            err_msg = str(err)
        elif exit_code == 137:
            err_msg = "OOM killed — try reducing batch size"
        elif exit_code != 0:
            err_msg = f"container exited with code {exit_code}"
        queue.mark_finished(job_id, exit_code, err_msg)
    except Exception as e:
        queue.mark_failed(job_id, f"watcher error: {e}")


def _run_job(job: dict) -> None:
    job_id = int(job["id"])
    try:
        container_id = docker_mgr.run_job_container(
            job_id=job_id,
            image=job["image"],
            command=job["script"],
            gpu_count=int(job.get("gpu_count") or 1),
        )
    except Exception as e:
        # docker_mgr already returns clean messages (e.g. "Docker image not found: …"),
        # just pass them through to the user.
        queue.mark_failed(job_id, str(e))
        return

    queue.mark_running(job_id, container_id)
    watcher = threading.Thread(
        target=_watch_container,
        args=(job_id, container_id),
        daemon=True,
        name=f"apex-watch-{job_id}",
    )
    watcher.start()


def _loop() -> None:
    while not _stop.is_set():
        try:
            job = queue.get_next_queued_job()
            if job:
                needs_gpu = int(job.get("gpu_count") or 0) > 0
                if not needs_gpu or not queue.is_gpu_busy():
                    _run_job(job)
        except Exception:
            pass
        _stop.wait(POLL_INTERVAL)


def start_worker() -> None:
    global _started
    if _started:
        return
    _started = True
    t = threading.Thread(target=_loop, daemon=True, name="apex-scheduler")
    t.start()


def stop_worker() -> None:
    _stop.set()
