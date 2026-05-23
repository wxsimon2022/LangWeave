"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from langweave import __version__
from langweave.registry import AgentRegistry
from langweave.web.handlers import register_exception_handlers
from langweave.web.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from langweave.web.openapi import API_DESCRIPTION, SWAGGER_UI_PARAMETERS, TAGS_METADATA
from langweave.web.response import ApiResponse
from langweave.web.routes import router


def create_app(
    registry: AgentRegistry | None = None,
    *,
    title: str = "LangWeave API",
    version: str = __version__,
    description: str = API_DESCRIPTION,
    on_startup: Callable[[AgentRegistry], None] | None = None,
    cors_origins: list[str] | None = None,
    doc_mode: Literal["swagger2", "openapi3"] = "swagger2",
    docs_url: str | None = None,
    redoc_url: str | None = None,
    openapi_url: str | None = None,
) -> FastAPI:
    """Create a FastAPI app wired to an `AgentRegistry`.

    Args:
        registry: Shared registry; created if omitted.
        title: OpenAPI title.
        on_startup: Called with the registry before serving (register agents here).
        cors_origins: If set, enable CORS for these origins.
        doc_mode: `swagger2` (default) disables OpenAPI 3 docs; call
            `setup_swagger2(app)` after mounting routers. `openapi3` uses built-in `/docs`.
        docs_url: OpenAPI 3 Swagger UI path. Auto-set when `doc_mode=openapi3`.
        redoc_url: OpenAPI 3 ReDoc path. Auto-set when `doc_mode=openapi3`.
        openapi_url: OpenAPI 3 JSON path. Auto-set when `doc_mode=openapi3`.
    """
    if doc_mode == "openapi3":
        docs_url = "/docs" if docs_url is None else docs_url
        redoc_url = "/redoc" if redoc_url is None else redoc_url
        openapi_url = "/openapi.json" if openapi_url is None else openapi_url
    else:
        docs_url = None
        redoc_url = None
        openapi_url = None

    reg = registry or AgentRegistry()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> Any:
        app.state.registry = reg
        if on_startup is not None:
            on_startup(reg)
        yield

    app = FastAPI(
        title=title,
        version=version,
        description=description,
        openapi_tags=TAGS_METADATA,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
        lifespan=lifespan,
        contact={
            "name": "LangWeave",
            "url": "https://github.com/langchain-ai/langchain",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
    )
    app.state.registry = reg
    register_exception_handlers(app)

    # Security: rate limiting
    app.add_middleware(
        RateLimitMiddleware,
        exclude_paths={"/health", "/api/v1/auth/login", "/api/v1/auth/register"},
    )

    # Security: HTTP headers
    app.add_middleware(SecurityHeadersMiddleware)

    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get(
        "/health",
        tags=["meta"],
        summary="健康检查",
        response_model=ApiResponse[dict[str, str]],
    )
    def health() -> ApiResponse[dict[str, str]]:
        """检查 API 服务是否正常运行。"""
        return ApiResponse.ok({"status": "ok"})

    app.include_router(router)
    return app
