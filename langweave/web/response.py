"""Unified API response envelope: ``{code, message, data}``."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""

    code: int = Field(200, description="业务状态码，200 表示成功")
    message: str = Field("", description="提示信息，成功时通常为空")
    data: T | None = Field(None, description="业务数据")

    @classmethod
    def ok(cls, data: T, *, message: str = "") -> ApiResponse[T]:
        return cls(code=200, message=message, data=data)

    @classmethod
    def fail(
        cls,
        code: int,
        message: str,
        *,
        data: Any = None,
    ) -> ApiResponse[Any]:
        return cls(code=code, message=message, data=data)
