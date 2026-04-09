"""VSCode dev session routes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apex import docker_mgr
from apex.config import CONFIG
from apex.server.db import get_db, row_to_dict

router = APIRouter()


class SessionCreate(BaseModel):
    image: str = Field(..., min_length=1)
    user: str = Field(..., min_length=1)


@router.get("")
def list_sessions() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE status = 'running' ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("")
def launch_session(payload: SessionCreate) -> dict[str, Any]:
    if not docker_mgr.is_available():
        raise HTTPException(503, "docker daemon not available")

    port_lo, port_hi = CONFIG.get("session_port_range", [8080, 8200])
    port = docker_mgr.find_free_port(int(port_lo), int(port_hi))
    if port is None:
        raise HTTPException(503, f"no free port in range {port_lo}-{port_hi}")

    # Insert row first with placeholder, then update with container_id
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO sessions (user, image, container_id, port, status) VALUES (?, ?, ?, ?, 'running')",
            (payload.user, payload.image, "pending", port),
        )
        session_id = cur.lastrowid

    try:
        container_id = docker_mgr.run_session_container(session_id, payload.image, port)
    except Exception as e:
        with get_db() as conn:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        msg = str(e)
        # Trim Docker SDK's verbose HTTP error wrappers down to the useful bit.
        if "pull access denied" in msg or "repository does not exist" in msg:
            msg = f"Docker image not found: {payload.image}"
        elif "Conflict" in msg and "already in use" in msg:
            msg = f"A container named apex-session-{session_id} already exists (retry should clear it)."
        elif "Bind for" in msg and "failed: port is already allocated" in msg:
            msg = f"Port {port} is already in use on the host."
        raise HTTPException(500, f"failed to launch session: {msg}")

    with get_db() as conn:
        conn.execute(
            "UPDATE sessions SET container_id = ? WHERE id = ?",
            (container_id, session_id),
        )
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    session = row_to_dict(row) or {}
    session["url"] = f"http://localhost:{port}"
    return session


@router.delete("/{session_id}")
def stop_session(session_id: int) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(404, "session not found")
    session = dict(row)
    if session.get("container_id") and session["container_id"] != "pending":
        docker_mgr.stop_container(session["container_id"], remove=True)
    with get_db() as conn:
        conn.execute("UPDATE sessions SET status='stopped' WHERE id = ?", (session_id,))
    return {"ok": True, "id": session_id}
