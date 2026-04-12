"""Metrics SSE stream and per-job GPU history."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse

from apex.monitor.collector import snapshot
from apex.server.auth import current_user
from apex.server.db import get_db

router = APIRouter()

HEARTBEAT_S = 2.0


@router.get("/stream")
async def metrics_stream() -> EventSourceResponse:
    async def generator() -> AsyncGenerator[dict, None]:
        while True:
            data = snapshot()
            if not data.get("ts"):
                data["ts"] = datetime.utcnow().isoformat(timespec="seconds")
            yield {"event": "metrics", "data": json.dumps(data)}
            await asyncio.sleep(HEARTBEAT_S)

    return EventSourceResponse(generator())


@router.get("/current")
def metrics_current() -> dict:
    data = snapshot()
    if not data.get("ts"):
        data["ts"] = datetime.utcnow().isoformat(timespec="seconds")
    return data


@router.get("/job/{job_id}")
def job_metrics(
    job_id: int,
    limit: int = Query(500, ge=1, le=5000),
    _user: dict = Depends(current_user),
) -> list[dict[str, Any]]:
    """Return GPU/CPU metrics history for a specific job."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT ts, gpu_util, vram_used AS vram_used_gb, vram_total AS vram_total_gb, "
            "gpu_temp, gpu_power AS gpu_power_w, cpu_util, ram_used AS ram_used_gb, ram_total AS ram_total_gb "
            "FROM metrics_history WHERE job_id = ? ORDER BY ts ASC LIMIT ?",
            (job_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]
