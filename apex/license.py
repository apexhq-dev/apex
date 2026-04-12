"""License key validation via Lemon Squeezy.

Flow:
  1. User buys Team plan on tryapex.dev → Lemon Squeezy generates a license key.
  2. User runs: apex activate XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
  3. We call Lemon Squeezy's /v1/licenses/activate endpoint once.
  4. The activation response is cached in ~/.apex/license.json for offline use.
  5. On each `apex start`, we re-validate if >30 days since last check (or offline, trust cache).
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from apex.config import CONFIG_DIR

LICENSE_PATH = CONFIG_DIR / "license.json"
LEMON_SQUEEZY_ACTIVATE_URL = "https://api.lemonsqueezy.com/v1/licenses/activate"
LEMON_SQUEEZY_VALIDATE_URL = "https://api.lemonsqueezy.com/v1/licenses/validate"
REVALIDATE_INTERVAL_S = 30 * 24 * 3600  # 30 days

# Plan limits
PLAN_LIMITS = {
    "free": {"seats": 1, "name": "Free"},
    "team": {"seats": 8, "name": "Team"},
}


def _instance_id() -> str:
    """Stable machine identifier for Lemon Squeezy activation."""
    id_file = CONFIG_DIR / ".install_id"
    if id_file.exists():
        return id_file.read_text().strip()
    import secrets
    iid = secrets.token_hex(16)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    id_file.write_text(iid)
    return iid


def _ls_request(url: str, key: str) -> dict[str, Any]:
    """POST to Lemon Squeezy license API."""
    data = json.dumps({
        "license_key": key,
        "instance_name": _instance_id(),
    }).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def activate(key: str) -> dict[str, Any]:
    """Activate a license key with Lemon Squeezy. Returns cached license data."""
    try:
        result = _ls_request(LEMON_SQUEEZY_ACTIVATE_URL, key)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            detail = json.loads(body).get("error", body)
        except Exception:
            detail = body
        raise RuntimeError(f"Activation failed: {detail}")
    except Exception as e:
        raise RuntimeError(f"Could not reach Lemon Squeezy: {e}")

    if not result.get("valid") and result.get("error"):
        raise RuntimeError(f"Activation failed: {result['error']}")

    license_data = {
        "key": key,
        "valid": result.get("valid", False),
        "plan": "team",
        "seats": PLAN_LIMITS["team"]["seats"],
        "activated_at": time.time(),
        "last_validated": time.time(),
        "license_key_id": result.get("license_key", {}).get("id"),
        "customer_name": result.get("meta", {}).get("customer_name"),
        "customer_email": result.get("meta", {}).get("customer_email"),
    }

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    LICENSE_PATH.write_text(json.dumps(license_data, indent=2))
    return license_data


def validate_cached() -> dict[str, Any] | None:
    """Re-validate the cached license if stale (>30 days). Returns None if no license."""
    if not LICENSE_PATH.exists():
        return None

    try:
        data = json.loads(LICENSE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    if not data.get("valid"):
        return None

    # Re-validate if stale
    last = data.get("last_validated", 0)
    if time.time() - last > REVALIDATE_INTERVAL_S:
        try:
            result = _ls_request(LEMON_SQUEEZY_VALIDATE_URL, data["key"])
            data["valid"] = result.get("valid", False)
            data["last_validated"] = time.time()
            LICENSE_PATH.write_text(json.dumps(data, indent=2))
        except Exception:
            # Offline — trust the cache
            pass

    return data if data.get("valid") else None


def get_plan() -> dict[str, Any]:
    """Return the current plan info: name, seats, is_active."""
    cached = validate_cached()
    if cached and cached.get("valid"):
        return {
            "plan": "team",
            "name": "Team",
            "seats": PLAN_LIMITS["team"]["seats"],
            "is_active": True,
            "customer_email": cached.get("customer_email"),
        }
    return {
        "plan": "free",
        "name": "Free",
        "seats": PLAN_LIMITS["free"]["seats"],
        "is_active": True,
        "customer_email": None,
    }


def deactivate() -> None:
    """Remove the local license cache (downgrade to free)."""
    if LICENSE_PATH.exists():
        LICENSE_PATH.unlink()
