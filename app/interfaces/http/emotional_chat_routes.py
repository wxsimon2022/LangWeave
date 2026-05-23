"""Authenticated emotional chat HTTP routes."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.application.services.emotional_chat import EmotionalChatService
from app.interfaces.http.deps import CurrentUser, EmotionalChatServiceDep
from app.schemas.emotional_chat import (
    ConversationListResponse,
    EmotionalChatRequest,
    EmotionalChatResponse,
    EmotionalConversationResponse,
)
from app.constants import API_V1_EMOTIONAL_CHAT
from langweave.web.response import ApiResponse
from langweave.web.serialize import json_dumps

logger = logging.getLogger(__name__)
router = APIRouter(prefix=API_V1_EMOTIONAL_CHAT, tags=["emotional-chat"])


@router.get(
    "/conversations",
    response_model=ApiResponse[ConversationListResponse],
    summary="列出当前用户的所有情感对话",
)
async def list_conversations(
    user: CurrentUser,
    service: EmotionalChatServiceDep,
) -> ApiResponse[ConversationListResponse]:
    try:
        return ApiResponse.ok(await service.list_conversations(user))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/history",
    response_model=ApiResponse[EmotionalConversationResponse],
    summary="读取指定对话的情感聊天历史（支持分页）",
)
async def get_history(
    user: CurrentUser,
    service: EmotionalChatServiceDep,
    conversation_id: int = Query(..., description="对话 ID"),
    offset: int = Query(0, ge=0, description="跳过前 N 条消息"),
    limit: int = Query(50, ge=1, le=200, description="返回消息条数上限"),
) -> ApiResponse[EmotionalConversationResponse]:
    try:
        return ApiResponse.ok(
            await service.get_history(
                user, conversation_id=conversation_id, offset=offset, limit=limit
            )
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
        return ApiResponse.ok(
            await service.send_message(
                user, body.message, conversation_id=body.conversation_id
            )
        )
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
    stream = service.stream_message(
        user, body.message, conversation_id=body.conversation_id
    )
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

    When the inner generator fails, a JSON error event is yielded so the
    client receives a meaningful message instead of a silent 200 OK.
    """
    finished = False
    try:
        async for item in async_gen:
            finished = True
            try:
                yield item
            except GeneratorExit:
                # Client disconnected — nothing more to send.
                return
        # Normal exhaustion — nothing more to yield.
    except GeneratorExit:
        return
    except BaseException:
        logger.exception("SSE stream iterator error")
        if not finished:
            error_sse = (
                f"data: {json_dumps({'event': 'error', 'payload': {'message': 'Internal stream error'}})}\n\n"
            )
            yield error_sse


@router.delete(
    "/history",
    response_model=ApiResponse[EmotionalConversationResponse],
    summary="清空指定对话的聊天历史",
)
async def reset_history(
    user: CurrentUser,
    service: EmotionalChatServiceDep,
    conversation_id: int = Query(..., description="对话 ID"),
) -> ApiResponse[EmotionalConversationResponse]:
    try:
        return ApiResponse.ok(
            await service.reset_history(user, conversation_id=conversation_id),
            message="会话已重置",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete(
    "/conversations/{conversation_id}",
    response_model=ApiResponse[None],
    summary="删除整个对话",
)
async def delete_conversation(
    conversation_id: int,
    user: CurrentUser,
    service: EmotionalChatServiceDep,
) -> ApiResponse[None]:
    try:
        await service.delete_conversation(user, conversation_id=conversation_id)
        return ApiResponse.ok(None, message="对话已删除")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
