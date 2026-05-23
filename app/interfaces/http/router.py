"""Aggregate business routers for application startup."""
from __future__ import annotations

from fastapi import APIRouter, FastAPI

from app.api.v1.agents_unified import router as agents_unified_router
from app.api.v1.conversations import router as conversations_router
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
