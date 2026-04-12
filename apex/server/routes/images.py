"""Docker image routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from apex import docker_mgr
from apex.server.auth import current_user

router = APIRouter()


@router.get("")
def list_images(_user: dict = Depends(current_user)) -> list[dict]:
    return docker_mgr.list_images()
