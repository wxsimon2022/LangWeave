"""Application composition helpers."""

from __future__ import annotations

from fastapi import FastAPI

from app.domain.agents import register_agents
from app.interfaces.http import include_business_routers
from langweave.web import create_app
from langweave.web.swagger2 import setup_swagger2


def create_business_app() -> FastAPI:
    """Create the project ASGI app with framework and business routes wired."""
    app = create_app(
        on_startup=register_agents,
        doc_mode="swagger2",
        cors_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
    )
    include_business_routers(app)
    setup_swagger2(
        app,
        swagger2_url="/swagger.json",
        docs_url="/docs",
        docs_mode="both",
        swagger_ui_url="/docs/swagger",
    )
    return app
