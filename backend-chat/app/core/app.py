"""Application initialization and startup.

Creates the FastAPI app, registers agents, and mounts business routers.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI

from app.bootstrap import create_business_app

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and return the fully configured FastAPI application."""
    return create_business_app()
