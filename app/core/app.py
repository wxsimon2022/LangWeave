"""Application initialization and startup.

Creates the FastAPI app, registers agents, and mounts business routers.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI

from app.bootstrap import create_business_app
from app.core.database import init_database
from app.infrastructure.cache import close_redis
from langweave.web.deps import get_registry

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and return the fully configured FastAPI application."""
    return create_business_app()
