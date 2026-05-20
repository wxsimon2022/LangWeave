"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from langweave.registry import AgentRegistry
from langweave.web.routes import router


def create_app(
    registry: AgentRegistry | None = None,
    *,
    title: str = "LangWeave",
    on_startup: Callable[[AgentRegistry], None] | None = None,
    cors_origins: list[str] | None = None,
) -> FastAPI:
    """Create a FastAPI app wired to an `AgentRegistry`.

    Args:
        registry: Shared registry; created if omitted.
        title: OpenAPI title.
        on_startup: Called with the registry before serving (register agents here).
        cors_origins: If set, enable CORS for these origins.
    """
    reg = registry or AgentRegistry()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> Any:
        app.state.registry = reg
        if on_startup is not None:
            on_startup(reg)
        yield

    app = FastAPI(title=title, lifespan=lifespan)
    app.state.registry = reg

    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    return app
