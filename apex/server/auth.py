"""JWT auth helpers for Apex."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from apex.config import CONFIG
from apex.server.db import get_db, row_to_dict

try:
    from jose import JWTError, jwt
except ImportError:  # pragma: no cover
    jwt = None  # type: ignore
    JWTError = Exception  # type: ignore

try:
    import bcrypt as _bcrypt
except ImportError:  # pragma: no cover
    _bcrypt = None  # type: ignore


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7  # one week

_bearer = HTTPBearer(auto_error=False)


def hash_password(raw: str) -> str:
    if _bcrypt is None:
        raise RuntimeError("bcrypt not installed")
    # bcrypt has a 72-byte limit — truncate per its own guidance.
    data = raw.encode("utf-8")[:72]
    return _bcrypt.hashpw(data, _bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    if _bcrypt is None:
        return False
    try:
        return _bcrypt.checkpw(raw.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(sub: str, extra: dict[str, Any] | None = None) -> str:
    if jwt is None:
        raise RuntimeError("python-jose not installed")
    payload: dict[str, Any] = {
        "sub": sub,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, CONFIG["jwt_secret"], algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    if jwt is None:
        raise HTTPException(status_code=500, detail="auth not available")
    try:
        return jwt.decode(token, CONFIG["jwt_secret"], algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_user_by_email(email: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return row_to_dict(row)


def current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    # Auth is optional in single-user mode — if no users exist yet, allow through
    # as the first-run owner.
    with get_db() as conn:
        n = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if n == 0:
        return {"id": 0, "email": "anonymous", "display_name": "Anonymous", "role": "owner"}

    if creds is None:
        # Single-user convenience: if there is exactly one account (the auto-created
        # owner) and no login page exists yet, return that owner rather than 401.
        with get_db() as conn:
            if n == 1:
                row = conn.execute("SELECT * FROM users LIMIT 1").fetchone()
                if row:
                    return row_to_dict(row)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(creds.credentials)
    user = get_user_by_email(payload.get("sub", ""))
    if not user:
        raise HTTPException(status_code=401, detail="user not found")
    return user


def ensure_owner_account() -> tuple[str, str] | None:
    """Create an owner account if none exists. Returns (email, temp_password) if created."""
    import secrets
    with get_db() as conn:
        n = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if n > 0:
            return None
        if _bcrypt is None:
            return None
        email = "owner@apex.local"
        password = secrets.token_urlsafe(12)
        hashed = hash_password(password)
        conn.execute(
            "INSERT INTO users (email, hashed_pw, display_name, role) VALUES (?, ?, ?, ?)",
            (email, hashed, "Owner", "owner"),
        )
        return email, password
