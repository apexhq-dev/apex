"""GPU metrics via pynvml. Returns nulls when no NVIDIA GPU is present."""
from __future__ import annotations

from typing import Any

_NVML_READY: bool | None = None
_NVML_HANDLE: Any = None
_NVML_NAME: str | None = None


def _init_nvml() -> bool:
    global _NVML_READY, _NVML_HANDLE, _NVML_NAME
    if _NVML_READY is not None:
        return _NVML_READY
    try:
        import pynvml
        pynvml.nvmlInit()
        _NVML_HANDLE = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(_NVML_HANDLE)
        _NVML_NAME = name.decode() if isinstance(name, bytes) else name
        _NVML_READY = True
    except Exception:
        _NVML_READY = False
    return _NVML_READY


def get_gpu_name() -> str | None:
    _init_nvml()
    return _NVML_NAME


def get_gpu_metrics() -> dict[str, Any]:
    empty: dict[str, Any] = {
        "gpu_util": None,
        "vram_used_gb": None,
        "vram_total_gb": None,
        "gpu_temp": None,
        "gpu_power_w": None,
        "gpu_name": None,
    }
    if not _init_nvml():
        return empty
    try:
        import pynvml
        handle = _NVML_HANDLE
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        try:
            power = pynvml.nvmlDeviceGetPowerUsage(handle) // 1000  # mW -> W
        except Exception:
            power = None
        return {
            "gpu_util": float(util.gpu),
            "vram_used_gb": round(mem.used / 1024**3, 1),
            "vram_total_gb": round(mem.total / 1024**3, 1),
            "gpu_temp": int(temp),
            "gpu_power_w": int(power) if power is not None else None,
            "gpu_name": _NVML_NAME,
        }
    except Exception:
        return empty
