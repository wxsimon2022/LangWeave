"""Aggregate business routers for application startup."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI

from app.api.intent_routes import router as intent_router
from app.api.session_routes import router as session_router

router = APIRouter()
router.include_router(intent_router)
router.include_router(session_router)


def include_business_routers(app: FastAPI) -> FastAPI:
    """Mount all business routers onto the given app."""
    app.include_router(router)
    return app
