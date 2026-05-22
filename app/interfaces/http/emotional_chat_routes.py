"""Authenticated emotional chat HTTP routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.application.services.emotional_chat import EmotionalChatService
from app.infrastructure.persistence.models import User
from app.interfaces.http.deps import get_current_user, get_emotional_chat_service
from app.schemas.emotional_chat import (
    EmotionalChatRequest,
    EmotionalChatResponse,
    EmotionalConversationResponse,
)
from langweave.web.response import ApiResponse

router = APIRouter(prefix="/api/v1/emotional-chat", tags=["emotional-chat"])


@router.get(
    "/history",
    response_model=ApiResponse[EmotionalConversationResponse],
    summary="读取当前用户的情感聊天历史",
)
async def get_history(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[EmotionalChatService, Depends(get_emotional_chat_service)],
) -> ApiResponse[EmotionalConversationResponse]:
    try:
        return ApiResponse.ok(await service.get_history(user))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/messages",
    response_model=ApiResponse[EmotionalChatResponse],
    summary="发送情感聊天消息并持久化",
)
async def send_message(
    body: EmotionalChatRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[EmotionalChatService, Depends(get_emotional_chat_service)],
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
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[EmotionalChatService, Depends(get_emotional_chat_service)],
) -> StreamingResponse:
    try:
        stream = service.stream_message(user, body.message)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete(
    "/history",
    response_model=ApiResponse[EmotionalConversationResponse],
    summary="清空当前用户的情感聊天历史",
)
async def reset_history(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[EmotionalChatService, Depends(get_emotional_chat_service)],
) -> ApiResponse[EmotionalConversationResponse]:
    try:
        return ApiResponse.ok(await service.reset_history(user), message="会话已重置")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
