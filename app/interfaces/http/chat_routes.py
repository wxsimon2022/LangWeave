"""Unified entry-agent chat HTTP routes.

This is the primary chat endpoint — it accepts any message, classifies
intent via the intent agent, and routes to the appropriate specialist agent.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.application.services.chat import ChatService
from app.interfaces.http.deps import CurrentUser
from app.infrastructure.persistence.database import get_db_session
from app.schemas.emotional_chat import (
    ConversationListResponse,
    ConversationSummary,
    ConversationUpdateRequest,
    EmotionalConversationResponse,
    EmotionalChatRequest,
)
from app.constants import API_V1_PREFIX
from langweave.web.response import ApiResponse
from langweave.web.serialize import json_dumps
from langweave.registry import AgentRegistry
from langweave.web.deps import get_registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix=f"{API_V1_PREFIX}/chat", tags=["chat"])


# ------------------------------------------------------------------
# Dependency: ChatService
# ------------------------------------------------------------------

def get_chat_service(
    db: Session = Depends(get_db_session),
    registry: AgentRegistry = Depends(get_registry),
) -> ChatService:
    return ChatService(db, registry)


ChatServiceDep = Depends(get_chat_service)


# ------------------------------------------------------------------
# Conversation listing (unified — shows conversations from all agents)
# ------------------------------------------------------------------

@router.get(
    "/conversations",
    response_model=ApiResponse[ConversationListResponse],
    summary="列出当前用户的所有对话（入口 agent，跨智能体）",
)
async def list_conversations(
    user: CurrentUser,
    service: ChatService = ChatServiceDep,
) -> ApiResponse[ConversationListResponse]:
    try:
        return ApiResponse.ok(await service.list_conversations(user))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ------------------------------------------------------------------
# History
# ------------------------------------------------------------------

@router.get(
    "/history",
    response_model=ApiResponse[EmotionalConversationResponse],
    summary="读取指定对话的聊天历史（支持分页）",
)
async def get_history(
    user: CurrentUser,
    service: ChatService = ChatServiceDep,
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


# ------------------------------------------------------------------
# Stream message (entry agent → intent recognition → specialist agent)
# ------------------------------------------------------------------

@router.post(
    "/stream",
    summary="入口 agent：识别意图并路由到对应的 specialist agent（SSE 流式）",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "SSE stream with intent/chunk/done events",
            "content": {"text/event-stream": {}},
        },
    },
)
async def stream_message(
    body: EmotionalChatRequest,
    user: CurrentUser,
    service: ChatService = ChatServiceDep,
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


# ------------------------------------------------------------------
# Reset / rename / delete
# ------------------------------------------------------------------

@router.delete(
    "/history",
    response_model=ApiResponse[EmotionalConversationResponse],
    summary="清空指定对话的聊天历史",
)
async def reset_history(
    user: CurrentUser,
    service: ChatService = ChatServiceDep,
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
    service: ChatService = ChatServiceDep,
) -> ApiResponse[None]:
    try:
        await service.delete_conversation(user, conversation_id=conversation_id)
        return ApiResponse.ok(None, message="对话已删除")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ApiResponse[ConversationSummary],
    summary="修改对话名称",
)
async def update_conversation(
    conversation_id: int,
    body: ConversationUpdateRequest,
    user: CurrentUser,
    service: ChatService = ChatServiceDep,
) -> ApiResponse[ConversationSummary]:
    try:
        result = await service.rename_conversation(
            user, conversation_id=conversation_id, title=body.title
        )
        return ApiResponse.ok(result, message="对话已重命名")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ------------------------------------------------------------------
# SSE safety wrapper (copied from emotional_chat_routes)
# ------------------------------------------------------------------

async def _sse_safe_iterate(async_gen: AsyncIterator[str]) -> AsyncIterator[str]:
    finished = False
    try:
        async for item in async_gen:
            finished = True
            try:
                yield item
            except GeneratorExit:
                return
    except GeneratorExit:
        return
    except BaseException:
        logger.exception("SSE stream iterator error")
        if not finished:
            error_sse = (
                f"data: {json_dumps({'event': 'error', 'payload': {'message': 'Internal stream error'}})}\n\n"
            )
            yield error_sse
