"""Apex FastAPI app factory."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apex.server.db import init_db
from apex.server.routes import images, jobs, metrics, sessions, users

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="Apex", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    init_db()

    # API routers — mounted BEFORE static so they take priority.
    app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
    app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
    app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
    app.include_router(images.router, prefix="/api/images", tags=["images"])
    app.include_router(users.router, prefix="/api/users", tags=["users"])

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True}

    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app
