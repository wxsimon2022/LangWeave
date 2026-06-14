"""Aggregate business HTTP routers.

Mounted routes:
- ``app.api.v1.agents_unified`` — POST /api/v1/unified/stream
- ``app.api.v1.conversations`` — /api/v1/conversations/*
- ``app.interfaces.http.auth_routes`` — /api/v1/auth/*
- ``app.interfaces.http.heartbeat_routes`` — /api/v1/heartbeat/*
- ``app.interfaces.http.admin_routes`` — /api/v1/admin/*
- ``app.interfaces.http.session_routes`` — /api/v1/sessions/*
"""
from __future__ import annotations

from fastapi import APIRouter, FastAPI

from app.interfaces.http.agents_unified import router as agents_unified_router
from app.interfaces.http.conversations import router as conversations_router
from app.interfaces.http.admin_routes import router as admin_router
from app.interfaces.http.auth_routes import router as auth_router
from app.interfaces.http.heartbeat_routes import router as heartbeat_router
from app.interfaces.http.session_routes import router as session_router

router = APIRouter()
router.include_router(agents_unified_router)
router.include_router(conversations_router)
router.include_router(admin_router)
router.include_router(auth_router)
router.include_router(heartbeat_router)
router.include_router(session_router)


def include_business_routers(app: FastAPI) -> FastAPI:
    """Mount all business routers onto the given app."""
    app.include_router(router)
    return app

# File download router — generated documents
from app.interfaces.http.files.download import router as files_router
from app.interfaces.http.visitor_routes import router as visitor_router
router.include_router(files_router)
router.include_router(visitor_router)
