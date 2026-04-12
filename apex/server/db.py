"""SQLite initialisation and connection helper for Apex."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from apex.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  name         TEXT NOT NULL,
  image        TEXT NOT NULL,
  script       TEXT NOT NULL,
  gpu_count    INTEGER DEFAULT 1,
  priority     TEXT DEFAULT 'normal',
  status       TEXT DEFAULT 'queued',
  container_id TEXT,
  exit_code    INTEGER,
  error_msg    TEXT,
  max_retries  INTEGER DEFAULT 0,
  retry_count  INTEGER DEFAULT 0,
  depends_on   TEXT,
  submitted_by TEXT,
  submitted_at TEXT DEFAULT (datetime('now')),
  started_at   TEXT,
  finished_at  TEXT,
  duration_s   INTEGER
);

CREATE TABLE IF NOT EXISTS sessions (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  user         TEXT NOT NULL,
  image        TEXT NOT NULL,
  container_id TEXT NOT NULL,
  port         INTEGER NOT NULL,
  status       TEXT DEFAULT 'running',
  created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS users (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  email        TEXT UNIQUE NOT NULL,
  hashed_pw    TEXT NOT NULL,
  display_name TEXT,
  role         TEXT DEFAULT 'member',
  created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS metrics_history (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  ts         TEXT DEFAULT (datetime('now')),
  job_id     INTEGER,
  gpu_util   REAL,
  vram_used  REAL,
  vram_total REAL,
  gpu_temp   INTEGER,
  gpu_power  INTEGER,
  cpu_util   REAL,
  ram_used   REAL,
  ram_total  REAL
);

CREATE INDEX IF NOT EXISTS idx_jobs_status      ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_submitted   ON jobs(submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_status  ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_metrics_ts       ON metrics_history(ts);
"""


_MIGRATIONS = [
    # v0.2.0: job retries
    ("max_retries", "ALTER TABLE jobs ADD COLUMN max_retries INTEGER DEFAULT 0"),
    ("retry_count", "ALTER TABLE jobs ADD COLUMN retry_count INTEGER DEFAULT 0"),
    # v0.2.0: per-job GPU history
    ("metrics_job_id", "ALTER TABLE metrics_history ADD COLUMN job_id INTEGER"),
    # v0.2.0: job dependencies
    ("depends_on", "ALTER TABLE jobs ADD COLUMN depends_on TEXT"),
]


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns that don't exist yet (idempotent)."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    existing_metrics = {row[1] for row in conn.execute("PRAGMA table_info(metrics_history)").fetchall()}
    all_existing = existing | existing_metrics
    for col_name, sql in _MIGRATIONS:
        if col_name not in all_existing:
            try:
                conn.execute(sql)
            except sqlite3.OperationalError:
                pass


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)
        conn.commit()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None
