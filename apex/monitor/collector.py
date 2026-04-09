"""Monitor collector thread — samples GPU + CPU every 2s into a shared dict."""
from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any

from apex.monitor.cpu import get_cpu_metrics
from apex.monitor.gpu import get_gpu_metrics
from apex.server.db import get_db

# Shared in-memory dict — mutated by the collector, read by the SSE endpoint.
current_metrics: dict[str, Any] = {
    "gpu_util": None,
    "vram_used_gb": None,
    "vram_total_gb": None,
    "gpu_temp": None,
    "gpu_power_w": None,
    "gpu_name": None,
    "cpu_util": None,
    "ram_used_gb": None,
    "ram_total_gb": None,
    "cpu_count": None,
    "ts": None,
}

_lock = threading.Lock()
_started = False
_stop = threading.Event()


def _sample_once() -> None:
    gpu = get_gpu_metrics()
    cpu = get_cpu_metrics()
    merged = {**gpu, **cpu, "ts": datetime.utcnow().isoformat(timespec="seconds")}
    with _lock:
        current_metrics.update(merged)
    # Persist sample + prune
    try:
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO metrics_history
                  (gpu_util, vram_used, vram_total, gpu_temp, gpu_power,
                   cpu_util, ram_used, ram_total)
                VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    gpu.get("gpu_util"),
                    gpu.get("vram_used_gb"),
                    gpu.get("vram_total_gb"),
                    gpu.get("gpu_temp"),
                    gpu.get("gpu_power_w"),
                    cpu.get("cpu_util"),
                    cpu.get("ram_used_gb"),
                    cpu.get("ram_total_gb"),
                ),
            )
            conn.execute("DELETE FROM metrics_history WHERE ts < datetime('now','-1 day')")
    except Exception:
        pass


def _loop(interval: float) -> None:
    while not _stop.is_set():
        try:
            _sample_once()
        except Exception:
            pass
        _stop.wait(interval)


def start_collector(interval: float = 2.0) -> None:
    global _started
    if _started:
        return
    _started = True
    t = threading.Thread(target=_loop, args=(interval,), daemon=True, name="apex-monitor")
    t.start()


def stop_collector() -> None:
    _stop.set()


def snapshot() -> dict[str, Any]:
    with _lock:
        return dict(current_metrics)
