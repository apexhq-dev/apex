# Apex — ML Platform · SPEC.md

> Self-hosted ML platform for small AI teams. One GPU machine, pip-installable,
> full job lifecycle management with browser-native VSCode dev sessions.
> Designed for Claude Code — follow this spec top to bottom.

---

## 1. Overview

**Product name:** Apex  
**Tagline:** Your GPU. Your team. No cloud tax.  
**Target:** Small AI/ML teams (2–8 people) with a single GPU workstation  
**Install UX:** `pip install apex` → `apex start` → browser opens at `http://localhost:7000`

Everything runs as Python threads in a single process. No Docker Compose for the
platform itself — Docker is only used to *run* dev sessions and training jobs.

---

## 2. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend framework | FastAPI + Uvicorn | Async, fast, clean OpenAPI |
| Real-time metrics | SSE via `sse-starlette` | Push GPU/CPU stats to frontend |
| Job state | SQLite via `sqlite3` (stdlib) | Zero external deps |
| GPU metrics | `nvidia-ml-py` (pynvml) | NVML bindings |
| CPU/RAM metrics | `psutil` | Cross-platform |
| Container management | `docker` Python SDK | Wraps Docker daemon |
| Frontend | Vanilla HTML + JS (served as static) | No build step, no Node.js |
| Fonts | Syne (UI) + JetBrains Mono (data) | Via Google Fonts CDN |
| Auth (Team plan) | JWT via `python-jose` + `passlib` | Simple email+password |

**`pyproject.toml` dependencies:**
```toml
[project]
name = "apex"
version = "0.1.0"
requires-python = ">=3.10"

[project.dependencies]
fastapi = ">=0.110"
uvicorn = { version = ">=0.29", extras = ["standard"] }
psutil = ">=5.9"
nvidia-ml-py = ">=12.0"
docker = ">=7.0"
sse-starlette = ">=2.0"
python-jose = { version = ">=3.3", extras = ["cryptography"] }
passlib = { version = ">=1.7", extras = ["bcrypt"] }
python-multipart = ">=0.0.9"
click = ">=8.1"

[project.scripts]
apex = "apex.cli:main"
```

---

## 3. Project Structure

```
apex/
├── cli.py                  # click CLI: start, stop, status
├── server/
│   ├── app.py              # FastAPI app factory, mounts routers + static
│   ├── db.py               # SQLite init, migrations, connection helper
│   ├── auth.py             # JWT helpers, current_user dependency
│   └── routes/
│       ├── metrics.py      # GET /api/metrics/stream  (SSE)
│       ├── jobs.py         # CRUD + submit  /api/jobs
│       ├── sessions.py     # VSCode session lifecycle  /api/sessions
│       ├── images.py       # List docker images  /api/images
│       └── users.py        # Auth: login, register, me  /api/users
├── monitor/
│   ├── gpu.py              # pynvml — util%, vram, temp, power
│   └── cpu.py              # psutil — cpu%, ram, disk
├── scheduler/
│   ├── queue.py            # SQLite-backed job queue helpers
│   └── worker.py           # Background thread: dequeue → docker run → status update
├── docker_mgr.py           # Python docker SDK wrapper (run, stop, logs, list images)
└── static/                 # Served at /  by FastAPI StaticFiles
    ├── index.html          # Single-page app shell
    ├── css/
    │   └── app.css         # All styles (see Section 6)
    └── js/
        ├── app.js          # Router, state, init
        ├── metrics.js      # SSE consumer + chart rendering
        ├── jobs.js         # Job list, submit form, polling
        ├── sessions.js     # Session list + launch
        └── logs.js         # Log drawer (WebSocket tail)
```

---

## 4. CLI (`apex/cli.py`)

```
apex start [--host 0.0.0.0] [--port 7000] [--workers 1]
apex stop
apex status
apex logs [--tail 100]
```

`apex start` must:
1. Check Docker daemon is running (`docker.from_env().ping()`) — exit with helpful message if not
2. Init SQLite DB (`server/db.py`)
3. Start the scheduler worker thread (daemon=True)
4. Start the monitor collector thread (daemon=True, samples every 2s)
5. Launch Uvicorn on `host:port`
6. Print `Apex is running at http://localhost:7000` and open browser via `webbrowser.open`

---

## 5. Database Schema (`server/db.py`)

### `jobs` table
```sql
CREATE TABLE IF NOT EXISTS jobs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT NOT NULL,
  image       TEXT NOT NULL,
  script      TEXT NOT NULL,       -- entry script + args string
  gpu_count   INTEGER DEFAULT 1,
  priority    TEXT DEFAULT 'normal', -- low | normal | high
  status      TEXT DEFAULT 'queued', -- queued | running | done | failed
  container_id TEXT,
  exit_code   INTEGER,
  error_msg   TEXT,
  submitted_by TEXT,
  submitted_at TEXT DEFAULT (datetime('now')),
  started_at  TEXT,
  finished_at TEXT,
  duration_s  INTEGER
);
```

### `sessions` table
```sql
CREATE TABLE IF NOT EXISTS sessions (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  user         TEXT NOT NULL,
  image        TEXT NOT NULL,
  container_id TEXT NOT NULL,
  port         INTEGER NOT NULL,
  status       TEXT DEFAULT 'running', -- running | stopped
  created_at   TEXT DEFAULT (datetime('now'))
);
```

### `users` table
```sql
CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  email         TEXT UNIQUE NOT NULL,
  hashed_pw     TEXT NOT NULL,
  display_name  TEXT,
  role          TEXT DEFAULT 'member', -- owner | admin | member
  created_at    TEXT DEFAULT (datetime('now'))
);
```

### `metrics_history` table
```sql
CREATE TABLE IF NOT EXISTS metrics_history (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  ts         TEXT DEFAULT (datetime('now')),
  gpu_util   REAL,
  vram_used  REAL,
  vram_total REAL,
  gpu_temp   INTEGER,
  gpu_power  INTEGER,
  cpu_util   REAL,
  ram_used   REAL,
  ram_total  REAL
);
-- Prune rows older than 24h on each insert
```

---

## 6. API Routes

### `GET /api/metrics/stream` — SSE
Streams a JSON event every 2 seconds:
```json
{
  "gpu_util": 73.2,
  "vram_used_gb": 18.4,
  "vram_total_gb": 24.0,
  "gpu_temp": 61,
  "gpu_power_w": 285,
  "cpu_util": 42.1,
  "ram_used_gb": 52.0,
  "ram_total_gb": 128.0,
  "ts": "2026-04-08T09:14:22"
}
```
Source: shared in-memory dict updated by the monitor thread.  
If no NVIDIA GPU found, `gpu_util` and related fields are `null`.

---

### `GET /api/jobs` — list jobs
Query params: `status` (filter), `limit` (default 50), `offset` (default 0)  
Returns array of job objects sorted by `submitted_at DESC`.

### `POST /api/jobs` — submit job
```json
{
  "name": "llama3-finetune-v2",
  "image": "pytorch/pytorch:2.2-cuda12",
  "script": "/workspace/train.py --lr 2e-4 --epochs 20",
  "gpu_count": 1,
  "priority": "normal"
}
```
Inserts row with `status=queued`. Returns job object.

### `GET /api/jobs/{id}` — get job detail
### `DELETE /api/jobs/{id}` — cancel/remove job (stops container if running)
### `GET /api/jobs/{id}/logs` — tail logs (WebSocket upgrade)

WebSocket at `ws://localhost:7000/api/jobs/{id}/logs`:
- Streams `container.logs(stream=True)` line by line
- Sends `{"line": "...", "ts": "..."}` JSON frames
- Closes when container exits

---

### `GET /api/sessions` — list active sessions
### `POST /api/sessions` — launch VSCode session
```json
{
  "image": "pytorch/pytorch:2.2-cuda12",
  "user": "Ajay Kumar"
}
```
Implementation:
1. Find a free port in range 8080–8200
2. Run: `docker run -d --name apex-session-{id} -p {port}:8080 -v /home/user/workspace:/workspace {image} code-server --auth none --bind-addr 0.0.0.0:8080`
3. Insert into `sessions` table
4. Return `{ "port": 8082, "url": "http://localhost:8082" }`

### `DELETE /api/sessions/{id}` — stop and remove session container

---

### `GET /api/images` — list available Docker images
Returns `docker.images.list()` formatted as:
```json
[
  { "id": "sha256:abc...", "tags": ["pytorch/pytorch:2.2-cuda12"], "size_gb": 8.2 }
]
```

---

### `POST /api/users/login` — returns JWT token
### `GET /api/users/me` — current user info
### `POST /api/users/invite` — create new user (admin only)

---

## 7. Scheduler Worker (`scheduler/worker.py`)

Single background thread that runs a loop every 3 seconds:

```python
while True:
    job = get_next_queued_job()   # priority order: high > normal > low
    if job and not is_gpu_busy():
        run_job(job)
    time.sleep(3)
```

`run_job(job)`:
1. Update status → `running`, set `started_at`
2. `docker.containers.run(image, command=job.script, detach=True, device_requests=[...], volumes={...})`
3. Store `container_id`
4. Spawn a watcher thread that blocks on `container.wait()`
5. On exit: update status → `done` or `failed`, set `finished_at`, compute `duration_s`

`is_gpu_busy()`: returns True if any job has `status=running` and `gpu_count > 0`.  
Simple single-GPU assumption for v1 — one running job at a time.

Docker run config:
```python
client.containers.run(
    image=job.image,
    command=job.script,
    detach=True,
    device_requests=[docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]])],
    volumes={"/home/user/workspace": {"bind": "/workspace", "mode": "rw"}},
    name=f"apex-job-{job.id}",
    remove=False,   # keep for log access after exit
)
```

---

## 8. Frontend Design

### Design System

**Colour palette (CSS variables — dark theme only for v1):**
```css
:root {
  --bg:     #06080B;
  --bg2:    #0C0F14;
  --bg3:    #111620;
  --bg4:    #181D27;
  --bg5:    #1E2535;

  --border:  #1C2232;
  --border2: #283042;
  --border3: #344060;

  --text:  #DDE3EF;
  --text2: #8A96B0;
  --text3: #4A5470;

  --accent:      #00D9F5;
  --accent-dim:  rgba(0,217,245,0.08);
  --accent-glow: rgba(0,217,245,0.25);

  --purple:     #8B5CF6;
  --purple-dim: rgba(139,92,246,0.1);

  --green:     #00E676;
  --green-dim: rgba(0,230,118,0.1);

  --amber:     #FFC107;
  --amber-dim: rgba(255,193,7,0.1);

  --red:     #FF4757;
  --red-dim: rgba(255,71,87,0.1);

  --orange: #FF7043;
}
```

**Typography:**
- UI labels, headings, buttons → `'Syne', sans-serif` (weights: 400, 600, 700, 800)
- All metrics, IDs, code, ports, durations → `'JetBrains Mono', monospace` (weights: 300, 400, 500)
- Load both from Google Fonts

**Status badge colours:**
| Status | Background | Text | Border |
|---|---|---|---|
| RUNNING | `var(--green-dim)` | `var(--green)` | `rgba(0,230,118,0.2)` |
| QUEUED | `var(--amber-dim)` | `var(--amber)` | `rgba(255,193,7,0.2)` |
| DONE | `var(--bg5)` | `var(--text3)` | `var(--border)` |
| FAILED | `var(--red-dim)` | `var(--red)` | `rgba(255,71,87,0.2)` |

RUNNING badge dot must pulse via `@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }`.

---

### Layout

```
┌─────────────────────────────────────────────────────┐
│  TOPBAR (50px)  logo | workspace pill | HW strip | avatar │
├──────────┬──────────────────────────────────────────┤
│          │  PAGE HEADER (title + tabs)              │
│ SIDEBAR  ├──────────────────────────────────────────┤
│ (220px)  │  SCROLL AREA                             │
│          │    stat cards (4 col)                    │
│          │    two-col grid:                         │
│          │      left: GPU chart + submit form       │
│          │      right: job list + sessions + activity│
└──────────┴──────────────────────────────────────────┘
                               LOG DRAWER (slide up from bottom-right)
```

---

### Topbar

Fixed 50px height. Contains left-to-right:
- **Logo:** cyan `▲` icon (24×24 rounded rect) + "Apex" in Syne 800
- **Workspace pill:** `team / {workspace-name}` in JetBrains Mono, muted background
- **HW strip (right-aligned):** GPU%, VRAM, CPU%, Temp — each as `key | mini-bar | value` segments separated by border-left lines. Updated live via SSE.
- **Notification bell** with red dot badge
- **Avatar** (initials, purple→cyan gradient)

---

### Sidebar (220px)

Two nav groups: **Workspace** (Overview, Jobs, Sessions, Metrics, Images) and **Team** (Members, Audit log, Secrets, Settings).

Nav items: 7px 10px padding, 7px border-radius. Active item has a 3px cyan left accent bar (position: absolute, left: -10px).

Bottom of sidebar (above footer):
- **GPU card:** dark bg, shows GPU name, VRAM spec, util%, mini progress bar, power draw, temperature
- **Plan card:** gradient border (purple→cyan), shows tier name, seat count, price, "Invite members →" CTA button in purple

---

### Stat Cards (4-column row)

Cards: Jobs today, GPU hours used, Queue depth, Success rate.  
Each: label (9px uppercase), large mono number (28px weight 300), meta line below.  
Hover: border brightens to `--border3`.

---

### GPU Chart Panel

- Legend row: two coloured dots (cyan = GPU, purple = CPU)
- `<canvas>` element, height 100px, redrawn every 2s
- Draw two series (CPU underneath, GPU on top) — filled area gradient + 1.5px line
- Below canvas: three-cell mini metric strip (GPU util, CPU util, Temp) with mini progress bars

**Chart rendering (canvas 2D API):**
```js
// Series: fill gradient from color+'33' to color+'00', then stroke
// Y scale: 0–100%, X scale: spread 60 data points across canvas width
// Redraw on every SSE tick — shift array left, push new value
```

---

### Submit Job Form

Two-column grid inside panel:
- Job name (text input)
- Docker image (select — populated from `GET /api/images`)
- Entry script + args (full-width text input)
- GPU count (select: 1 GPU / All GPUs)
- Priority (select: Normal / High / Low)
- Footer row: "Save draft" ghost button + "Queue job →" primary button

On submit: `POST /api/jobs`, then refresh job list.

---

### Job List

Each job row is a card (10px 12px padding, 8px border-radius). Clicking any row opens the log drawer.

Row layout: `[status icon] [name + meta] [badge + duration]`

- Status icon: 28×28 rounded rect with coloured background matching status
- Name: 12px bold, truncated with ellipsis
- Meta: `#id · image · elapsed` in JetBrains Mono 10px muted
- Badge: coloured status pill (see badge table above)
- Duration: mono 10px muted

Poll `GET /api/jobs` every 5 seconds to refresh list.

---

### Dev Sessions Panel

Each session row: green pulsing dot | name + image/elapsed | port pill | ↗ open button.

"+ New" button in panel header opens a modal:
- Dropdown of available Docker images
- "Launch session" button → `POST /api/sessions` → show returned URL

---

### Activity Feed

Real-time list of events (job started, job failed, session opened, job completed).  
Each item: coloured icon box | text with **bold user name** in cyan | relative timestamp.  
Backed by polling `GET /api/jobs` and diffing state for new events.

---

### Log Drawer

Slides up from bottom-right (`position: fixed, right: 0, bottom: 0`).  
Width: 540px. Max-height: 360px. Rounded top-left corner only.

Header: job title in mono | status badge | ✕ close button.  
Body: dark `#06080B` background, JetBrains Mono 10.5px, line-height 2.  
Coloured log prefixes:
- `✓` lines → `--green`
- `→` info lines → `--accent`
- `⚠` warn lines → `--amber`
- `ERROR` lines → `--red`
- Default → `--text2`

Connect to `ws://localhost:7000/api/jobs/{id}/logs` on open. Append lines. Auto-scroll to bottom.  
Close button disconnects WebSocket.

---

## 9. Monitor Threads

### GPU monitor (`monitor/gpu.py`)
```python
import pynvml

def get_gpu_metrics() -> dict:
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    util   = pynvml.nvmlDeviceGetUtilizationRates(handle)
    mem    = pynvml.nvmlDeviceGetMemoryInfo(handle)
    temp   = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
    power  = pynvml.nvmlDeviceGetPowerUsage(handle) // 1000  # mW → W
    return {
        "gpu_util":    util.gpu,
        "vram_used_gb": round(mem.used / 1024**3, 1),
        "vram_total_gb": round(mem.total / 1024**3, 1),
        "gpu_temp":    temp,
        "gpu_power_w": power,
    }
```

Wrap in `try/except pynvml.NVMLError` — return nulls if no GPU.

### CPU monitor (`monitor/cpu.py`)
```python
import psutil

def get_cpu_metrics() -> dict:
    return {
        "cpu_util":   psutil.cpu_percent(interval=None),
        "ram_used_gb": round(psutil.virtual_memory().used / 1024**3, 1),
        "ram_total_gb": round(psutil.virtual_memory().total / 1024**3, 1),
    }
```

**Collector thread:** merges GPU + CPU dicts into a shared `current_metrics` dict every 2s. SSE endpoint reads from this dict.

---

## 10. Auth (Team Plan Gate)

JWT-based. All `/api/*` routes except `/api/users/login` require `Authorization: Bearer {token}`.

First `apex start` auto-creates an owner account and prints credentials to terminal.

Frontend stores JWT in `localStorage`. On 401, redirect to `/login`.

Login page: minimal centered form — email + password + "Sign in" button. Same dark theme.

---

## 11. Static File Serving

Mount `apex/static/` at `/` using FastAPI's `StaticFiles` with `html=True`.  
`index.html` is the SPA shell — all navigation is JS-driven (no page reloads).

API routes are mounted at `/api/` prefix — they take priority over static files.

---

## 12. Frontend Routing (JS)

Simple hash-based router in `app.js`:
```
#/           → Overview (dashboard)
#/jobs       → Jobs full list + table view
#/sessions   → Sessions management
#/metrics    → Full metrics history page
#/images     → Docker image management
#/members    → Team members (admin only)
#/settings   → Platform settings
```

On hash change: hide all page sections, show active section, update sidebar active state.

---

## 13. Workspace Volume

All dev sessions and training jobs mount `/home/user/workspace` (host) → `/workspace` (container).

Create this directory on `apex start` if it doesn't exist.

The path should be configurable via `~/.apex/config.json`:
```json
{
  "workspace_path": "/home/user/workspace",
  "port": 7000,
  "session_port_range": [8080, 8200]
}
```

---

## 14. Error Handling

- Docker not running → `apex start` prints clear error: `Docker daemon not found. Please start Docker first.`
- No NVIDIA GPU → GPU metrics show as `—`, jobs can still run without `--gpus` flag
- Image not found → job immediately fails with `error_msg: "Docker image not found: {image}"`
- Port already in use → session launch picks next available port automatically
- OOM kill → container exit code 137, `error_msg: "OOM killed — try reducing batch size"`

---

## 15. Build & Package

```
apex/
├── pyproject.toml
├── README.md
├── apex/
│   └── ... (source)
└── apex/static/
    └── ... (frontend, committed to repo)
```

`pip install apex` installs the package and registers the `apex` CLI command.  
Static files are included via `[tool.setuptools.package-data] apex = ["static/**/*"]`.

No npm, no webpack, no build step. Static files are plain HTML/CSS/JS, committed as-is.

---

## 16. Implementation Order for Claude Code

Build in this exact order — each step is independently testable:

1. `cli.py` + `server/app.py` + `server/db.py` → `apex start` boots, serves 200 at `/`
2. `monitor/gpu.py` + `monitor/cpu.py` + collector thread → metrics dict populated
3. `routes/metrics.py` SSE endpoint → curl shows live JSON stream
4. `static/index.html` + `static/css/app.css` → layout renders correctly in browser
5. `static/js/metrics.js` → topbar HW strip + chart update live
6. `routes/jobs.py` CRUD → can POST and GET jobs via curl
7. `scheduler/worker.py` → submitted jobs actually run in Docker
8. `static/js/jobs.js` → job list renders, submit form works, status updates
9. `routes/sessions.py` + `docker_mgr.py` → VSCode sessions launch
10. `static/js/sessions.js` → session list + launch modal
11. WebSocket log tail → log drawer connects and streams
12. `routes/users.py` + `server/auth.py` → JWT auth, login page
13. Polish: activity feed, notifications, config file, error handling

---

## 17. Key Constraints

- **No React, no Vue, no build toolchain.** Vanilla JS only in `static/`.
- **No Redis, no Postgres, no RabbitMQ.** SQLite + Python threads only.
- **No Kubernetes, no Helm.** Docker SDK only.
- **Single GPU assumption for v1.** Scheduler runs one job at a time.
- **M1 Mac compatible** for development (pynvml will return nulls — that's fine).
- **Python 3.10+ required.**
- All times stored as ISO 8601 strings in SQLite. Frontend formats them for display.
- Workspace path defaults to `~/apex-workspace` if not configured.
