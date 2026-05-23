"""Error handler middleware."""
from __future__ import annotations

import logging

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def global_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "Internal server error", "data": None},
    )
