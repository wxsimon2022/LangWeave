"""Global exception handlers returning ``ApiResponse``."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from langweave.web.response import ApiResponse


def register_exception_handlers(app: FastAPI) -> None:
    """Register handlers so errors use ``{code, message, data}``."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        _request: Request, exc: HTTPException
    ) -> JSONResponse:
        body = ApiResponse.fail(
            exc.status_code,
            str(exc.detail) if exc.detail else "请求失败",
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=body.model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        message = errors[0].get("msg", "参数校验失败") if errors else "参数校验失败"
        body = ApiResponse.fail(422, message, data=errors)
        return JSONResponse(status_code=422, content=body.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        body = ApiResponse.fail(500, str(exc) or "服务器内部错误")
        return JSONResponse(status_code=500, content=body.model_dump())
