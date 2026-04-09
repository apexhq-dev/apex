"""Docker image routes."""
from __future__ import annotations

from fastapi import APIRouter

from apex import docker_mgr

router = APIRouter()


@router.get("")
def list_images() -> list[dict]:
    return docker_mgr.list_images()
