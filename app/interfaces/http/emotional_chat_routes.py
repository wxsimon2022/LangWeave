"""Authenticated emotional chat HTTP routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.application.services.emotional_chat import EmotionalChatService
from app.interfaces.http.deps import CurrentUser, EmotionalChatServiceDep
from app.schemas.emotional_chat import (
    EmotionalChatRequest,
    EmotionalChatResponse,
    EmotionalConversationResponse,
)
from app.constants import API_V1_EMOTIONAL_CHAT
from langweave.web.response import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix=API_V1_EMOTIONAL_CHAT, tags=["emotional-chat"])


@router.get(
    "/history",
    response_model=ApiResponse[EmotionalConversationResponse],
    summary="读取当前用户的情感聊天历史（支持分页）",
)
async def get_history(
    user: CurrentUser,
    service: EmotionalChatServiceDep,
    offset: int = Query(0, ge=0, description="跳过前 N 条消息"),
    limit: int = Query(50, ge=1, le=200, description="返回消息条数上限"),
) -> ApiResponse[EmotionalConversationResponse]:
    try:
        return ApiResponse.ok(
            await service.get_history(user, offset=offset, limit=limit)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/messages",
    response_model=ApiResponse[EmotionalChatResponse],
    summary="发送情感聊天消息并持久化",
)
async def send_message(
    body: EmotionalChatRequest,
    user: CurrentUser,
    service: EmotionalChatServiceDep,
) -> ApiResponse[EmotionalChatResponse]:
    try:
        return ApiResponse.ok(await service.send_message(user, body.message))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/stream",
    summary="流式发送情感聊天消息并持久化",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "SSE stream with chunk/done events",
            "content": {"text/event-stream": {}},
        },
    },
)
async def stream_message(
    body: EmotionalChatRequest,
    user: CurrentUser,
    service: EmotionalChatServiceDep,
) -> StreamingResponse:
    stream = service.stream_message(user, body.message)
    return StreamingResponse(
        _sse_safe_iterate(stream),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _sse_safe_iterate(async_gen: AsyncIterator[str]) -> AsyncIterator[str]:
    """Wrap an SSE async generator so no exception escapes.

    Starlette's ``StreamingResponse`` wraps the generator in a ``TaskGroup``
    that bundles exceptions into an ``ExceptionGroup`` when the client
    disconnects.  This wrapper catches everything so the ASGI layer never
    sees an unhandled generator exception.
    """
    try:
        async for item in async_gen:
            try:
                yield item
            except GeneratorExit:
                return
    except GeneratorExit:
        return
    except BaseException:
        logger.exception("SSE stream iterator error")
    finally:
        # Ensure the generator is closed to release resources.
        await async_gen.aclose()


@router.delete(
    "/history",
    response_model=ApiResponse[EmotionalConversationResponse],
    summary="清空当前用户的情感聊天历史",
)
async def reset_history(
    user: CurrentUser,
    service: EmotionalChatServiceDep,
) -> ApiResponse[EmotionalConversationResponse]:
    try:
        return ApiResponse.ok(await service.reset_history(user), message="会话已重置")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
