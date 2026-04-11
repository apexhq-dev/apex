"""Apex runtime configuration — loads/creates ~/.apex/config.json."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

CONFIG_DIR = Path(os.path.expanduser("~/.apex"))
CONFIG_PATH = CONFIG_DIR / "config.json"
DB_PATH = CONFIG_DIR / "apex.db"

DEFAULTS: dict[str, Any] = {
    "workspace_path": os.path.expanduser("~/apex-workspace"),
    "port": 7000,
    "host": "0.0.0.0",
    "session_port_range": [8080, 8200],
    "jwt_secret": None,  # populated on first load
}


def load_config() -> dict[str, Any]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text())
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}

    changed = False
    for k, v in DEFAULTS.items():
        if k not in data:
            data[k] = v
            changed = True

    if not data.get("jwt_secret"):
        import secrets
        data["jwt_secret"] = secrets.token_urlsafe(48)
        changed = True

    if changed:
        CONFIG_PATH.write_text(json.dumps(data, indent=2))

    # Env var override — useful for NFS mounts or external SSDs configured at
    # the system level (e.g. export APEX_WORKSPACE=/mnt/bigdisk/apex-workspace)
    if os.environ.get("APEX_WORKSPACE"):
        data["workspace_path"] = os.path.expanduser(os.environ["APEX_WORKSPACE"])

    # Ensure workspace dir exists
    Path(data["workspace_path"]).mkdir(parents=True, exist_ok=True)
    return data


CONFIG = load_config()
