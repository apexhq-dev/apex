"""Job routes — CRUD, submit, logs (WebSocket)."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from apex import docker_mgr
from apex.scheduler import queue
from apex.server.auth import current_user

router = APIRouter()


class JobSubmit(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    image: str = Field(..., min_length=1)
    script: str = Field(..., min_length=1)
    gpu_count: int = 1
    priority: str = "normal"
    max_retries: int = Field(0, ge=0, le=10)
    depends_on: list[int] | None = None


@router.get("")
def list_jobs(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _user: dict = Depends(current_user),
) -> list[dict[str, Any]]:
    return queue.list_jobs(status=status, limit=limit, offset=offset)


@router.post("")
def submit_job(payload: JobSubmit, user: dict = Depends(current_user)) -> dict[str, Any]:
    if payload.priority not in ("low", "normal", "high"):
        raise HTTPException(400, "priority must be one of: low, normal, high")
    if payload.gpu_count < 0:
        raise HTTPException(400, "gpu_count must be >= 0")
    depends_on_str = ",".join(str(d) for d in payload.depends_on) if payload.depends_on else None
    job = queue.insert_job(
        name=payload.name,
        image=payload.image,
        script=payload.script,
        gpu_count=payload.gpu_count,
        priority=payload.priority,
        submitted_by=user.get("email"),
        max_retries=payload.max_retries,
        depends_on=depends_on_str,
    )
    return job


@router.get("/{job_id}")
def get_job(job_id: int, _user: dict = Depends(current_user)) -> dict[str, Any]:
    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job


@router.delete("/{job_id}")
def cancel_job(job_id: int, _user: dict = Depends(current_user)) -> dict:
    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if job.get("container_id") and job.get("status") == "running":
        docker_mgr.stop_container(job["container_id"], remove=False)
        queue.mark_finished(job_id, exit_code=130, error_msg="cancelled by user")
    else:
        queue.delete_job(job_id)
    return {"ok": True, "id": job_id}


@router.websocket("/{job_id}/logs")
async def job_logs_ws(websocket: WebSocket, job_id: int) -> None:
    await websocket.accept()
    job = queue.get_job(job_id)
    if not job:
        await websocket.send_json({"error": "job not found"})
        await websocket.close()
        return

    container_id = job.get("container_id")
    if not container_id:
        await websocket.send_json({"line": f"[apex] job #{job_id} has no container yet (status={job.get('status')})", "ts": datetime.utcnow().isoformat()})
        await websocket.close()
        return

    try:
        container = docker_mgr.get_container(container_id)
    except Exception as e:
        await websocket.send_json({"line": f"[apex] cannot attach to container: {e}", "ts": datetime.utcnow().isoformat()})
        await websocket.close()
        return

    loop = asyncio.get_running_loop()
    queue_out: asyncio.Queue[str | None] = asyncio.Queue()

    def _reader() -> None:
        try:
            for chunk in container.logs(stream=True, follow=True, tail=200):
                text = chunk.decode(errors="replace") if isinstance(chunk, (bytes, bytearray)) else str(chunk)
                for line in text.splitlines():
                    asyncio.run_coroutine_threadsafe(queue_out.put(line), loop)
        finally:
            asyncio.run_coroutine_threadsafe(queue_out.put(None), loop)

    import threading
    t = threading.Thread(target=_reader, daemon=True)
    t.start()

    try:
        while True:
            line = await queue_out.get()
            if line is None:
                break
            await websocket.send_json({"line": line, "ts": datetime.utcnow().isoformat()})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
