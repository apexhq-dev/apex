"""CPU/RAM metrics via psutil."""
from __future__ import annotations

from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore


def get_cpu_metrics() -> dict[str, Any]:
    if psutil is None:
        return {"cpu_util": None, "ram_used_gb": None, "ram_total_gb": None, "cpu_count": None}
    vm = psutil.virtual_memory()
    return {
        "cpu_util": float(psutil.cpu_percent(interval=None)),
        "ram_used_gb": round(vm.used / 1024**3, 1),
        "ram_total_gb": round(vm.total / 1024**3, 1),
        "cpu_count": psutil.cpu_count(logical=True),
    }
