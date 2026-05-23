"""Aggregate business routers for application startup."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI

from app.interfaces.http.admin_routes import router as admin_router
from app.interfaces.http.auth_routes import router as auth_router
from app.interfaces.http.emotional_chat_routes import router as emotional_chat_router
from app.interfaces.http.heartbeat_routes import router as heartbeat_router
from app.interfaces.http.intent_routes import router as intent_router
from app.interfaces.http.session_routes import router as session_router

router = APIRouter()
router.include_router(admin_router)
router.include_router(auth_router)
router.include_router(emotional_chat_router)
router.include_router(heartbeat_router)
router.include_router(intent_router)
router.include_router(session_router)


def include_business_routers(app: FastAPI) -> FastAPI:
    """Mount all business routers onto the given app."""
    app.include_router(router)
    return app
