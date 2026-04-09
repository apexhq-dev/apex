"""User/auth routes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from apex.server.auth import (
    create_access_token,
    current_user,
    get_user_by_email,
    hash_password,
    verify_password,
)
from apex.server.db import get_db

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class InviteRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6)
    display_name: str | None = None
    role: str = "member"


@router.post("/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    user = get_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user["hashed_pw"]):
        raise HTTPException(401, "invalid email or password")
    token = create_access_token(
        sub=user["email"],
        extra={"role": user.get("role"), "name": user.get("display_name")},
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "display_name": user.get("display_name"),
            "role": user.get("role"),
        },
    }


@router.get("/me")
def me(user: dict = Depends(current_user)) -> dict:
    return {
        "email": user.get("email"),
        "display_name": user.get("display_name"),
        "role": user.get("role"),
    }


@router.post("/invite")
def invite(payload: InviteRequest, user: dict = Depends(current_user)) -> dict:
    if user.get("role") not in ("owner", "admin"):
        raise HTTPException(403, "only owner/admin can invite users")
    if payload.role not in ("owner", "admin", "member"):
        raise HTTPException(400, "role must be owner/admin/member")
    if get_user_by_email(payload.email):
        raise HTTPException(409, "user already exists")
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (email, hashed_pw, display_name, role) VALUES (?, ?, ?, ?)",
            (payload.email, hash_password(payload.password), payload.display_name, payload.role),
        )
    return {"ok": True, "email": payload.email}
