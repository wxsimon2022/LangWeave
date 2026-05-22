"""Swagger 2.0 documentation (via fastapi-swagger2)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from langweave.web.openapi import SWAGGER_UI_PARAMETERS, TAGS_METADATA
from langweave.web.tree_docs import mount_tree_docs

try:
    from fastapi_swagger2 import FastAPISwagger2
except ImportError as exc:
    FastAPISwagger2 = None  # type: ignore[misc, assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


def swagger2_available() -> bool:
    """Return whether the optional Swagger 2 dependency is installed."""
    return FastAPISwagger2 is not None


def setup_swagger2(
    app: FastAPI,
    *,
    swagger2_url: str = "/swagger.json",
    docs_url: str = "/docs",
    docs_mode: str = "both",
    swagger_ui_url: str = "/docs/swagger",
    redoc_url: str | None = None,
    ui_parameters: dict[str, Any] | None = None,
) -> None:
    """Enable Swagger 2.0 schema + API docs on an existing FastAPI app.

    Call **after** all routers are mounted (e.g. at the end of `main.py`).

    Args:
        docs_mode: `tree` = directory-tree UI at `docs_url` (default);
            `swagger` = classic Swagger UI; `both` = tree + Swagger UI.

    Endpoints:
        - `{swagger2_url}` — Swagger 2.0 JSON spec
        - `{docs_url}` — directory-tree docs when `docs_mode` is `tree` or `both`
        - `{swagger_ui_url}` — classic Swagger UI when `docs_mode` is `swagger` or `both`
    """
    if FastAPISwagger2 is None:
        msg = (
            "Swagger 2 requires `fastapi-swagger2`. "
            "Install with: pip install fastapi-swagger2"
        )
        raise ImportError(msg) from _IMPORT_ERROR

    use_tree = docs_mode in ("tree", "both")
    use_swagger_ui = docs_mode in ("swagger", "both")

    FastAPISwagger2(
        app,  # type: ignore[arg-type]
        swagger2_url=swagger2_url,
        swagger2_docs_url=swagger_ui_url if use_swagger_ui else None,
        swagger2_redoc_url=redoc_url,
        swagger2_tags=TAGS_METADATA,
        swagger2_ui_parameters=ui_parameters or SWAGGER_UI_PARAMETERS,
    )

    if use_tree:
        mount_tree_docs(
            app,
            docs_url=docs_url,
            spec_url=swagger2_url,
            swagger_ui_url=swagger_ui_url if use_swagger_ui else None,
        )
