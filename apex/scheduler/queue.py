"""SQLite-backed job queue helpers."""
from __future__ import annotations

from typing import Any

from apex.server.db import get_db, row_to_dict

# Priority ordering: high > normal > low
_PRIORITY_ORDER = "CASE priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 WHEN 'low' THEN 2 ELSE 3 END"


def insert_job(
    name: str,
    image: str,
    script: str,
    gpu_count: int = 1,
    priority: str = "normal",
    submitted_by: str | None = None,
    max_retries: int = 0,
    depends_on: str | None = None,
) -> dict[str, Any]:
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO jobs (name, image, script, gpu_count, priority, submitted_by, max_retries, depends_on)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, image, script, gpu_count, priority, submitted_by, max_retries, depends_on),
        )
        job_id = cur.lastrowid
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return row_to_dict(row)  # type: ignore[return-value]


def get_job(job_id: int) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return row_to_dict(row)


def list_jobs(status: str | None = None, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    sql = "SELECT * FROM jobs"
    params: list[Any] = []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    # Queued jobs are sorted by dispatch order (priority → submission time) so the
    # list reflects the actual run order.  All other statuses sort newest-first.
    if status == "queued":
        sql += f" ORDER BY {_PRIORITY_ORDER}, submitted_at ASC LIMIT ? OFFSET ?"
    else:
        sql += " ORDER BY submitted_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_next_queued_job() -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            f"SELECT * FROM jobs WHERE status = 'queued' "
            f"ORDER BY {_PRIORITY_ORDER}, submitted_at ASC LIMIT 1"
        ).fetchone()
    return row_to_dict(row)


def get_queued_jobs(limit: int = 20) -> list[dict[str, Any]]:
    """Return all queued jobs in dispatch order (priority → submission time)."""
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM jobs WHERE status = 'queued' "
            f"ORDER BY {_PRIORITY_ORDER}, submitted_at ASC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def are_dependencies_met(job: dict[str, Any]) -> bool:
    """Return True if all jobs in depends_on are status='done'."""
    deps = job.get("depends_on")
    if not deps:
        return True
    dep_ids = [int(x.strip()) for x in deps.split(",") if x.strip()]
    if not dep_ids:
        return True
    placeholders = ",".join("?" for _ in dep_ids)
    with get_db() as conn:
        row = conn.execute(
            f"SELECT COUNT(*) FROM jobs WHERE id IN ({placeholders}) AND status != 'done'",
            dep_ids,
        ).fetchone()
    return (row[0] or 0) == 0


def is_gpu_busy() -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status = 'running' AND gpu_count > 0"
        ).fetchone()
    return (row[0] or 0) > 0


def mark_running(job_id: int, container_id: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE jobs SET status='running', container_id=?, started_at=datetime('now') WHERE id=?",
            (container_id, job_id),
        )


def mark_finished(job_id: int, exit_code: int, error_msg: str | None = None) -> None:
    status = "done" if exit_code == 0 else "failed"
    with get_db() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET status=?,
                exit_code=?,
                error_msg=?,
                finished_at=datetime('now'),
                duration_s=CAST((julianday('now') - julianday(COALESCE(started_at, submitted_at))) * 86400 AS INTEGER)
            WHERE id=?
            """,
            (status, exit_code, error_msg, job_id),
        )


def mark_failed(job_id: int, error_msg: str) -> None:
    with get_db() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET status='failed',
                error_msg=?,
                finished_at=datetime('now'),
                duration_s=CAST((julianday('now') - julianday(COALESCE(started_at, submitted_at))) * 86400 AS INTEGER)
            WHERE id=?
            """,
            (error_msg, job_id),
        )


def requeue_for_retry(job_id: int) -> bool:
    """Re-queue a failed job if it has retries remaining. Returns True if re-queued."""
    with get_db() as conn:
        row = conn.execute("SELECT max_retries, retry_count FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return False
        max_r, count = row[0] or 0, row[1] or 0
        if count >= max_r:
            return False
        conn.execute(
            """
            UPDATE jobs
            SET status='queued', container_id=NULL, exit_code=NULL, error_msg=NULL,
                started_at=NULL, finished_at=NULL, duration_s=NULL,
                retry_count=?
            WHERE id=?
            """,
            (count + 1, job_id),
        )
    return True


def delete_job(job_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
