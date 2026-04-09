"""Metrics SSE stream."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from apex.monitor.collector import snapshot

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
