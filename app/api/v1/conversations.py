"""Conversation management API — list, history, rename, delete, reset."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.services.conversation_service import ConversationService
from app.interfaces.http.deps import CurrentUser
from app.infrastructure.persistence.database import get_db_session
from app.schemas.emotional_chat import (
    ConversationListResponse,
    ConversationSummary,
    ConversationUpdateRequest,
    EmotionalConversationResponse,
)
from app.constants import API_V1_PREFIX
from langweave.web.response import ApiResponse
from langweave.registry import AgentRegistry
from langweave.web.deps import get_registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix=f"{API_V1_PREFIX}/conversations", tags=["conversations"])


# ------------------------------------------------------------------
# Dependency
# ------------------------------------------------------------------

def get_conversation_service(
    db: Session = Depends(get_db_session),
    registry: AgentRegistry = Depends(get_registry),
) -> ConversationService:
    return ConversationService(db, registry)


ConvServiceDep = Depends(get_conversation_service)


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@router.get(
    "",
    response_model=ApiResponse[ConversationListResponse],
    summary="列出当前用户的所有对话",
)
async def list_conversations(
    user: CurrentUser,
    service: ConversationService = ConvServiceDep,
) -> ApiResponse[ConversationListResponse]:
    try:
        return ApiResponse.ok(await service.list_conversations(user))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/{conversation_id}/history",
    response_model=ApiResponse[EmotionalConversationResponse],
    summary="读取指定对话的聊天历史（支持分页）",
)
async def get_history(
    conversation_id: int,
    user: CurrentUser,
    service: ConversationService = ConvServiceDep,
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


@router.delete(
    "/{conversation_id}/history",
    response_model=ApiResponse[EmotionalConversationResponse],
    summary="清空指定对话的聊天历史",
)
async def reset_history(
    conversation_id: int,
    user: CurrentUser,
    service: ConversationService = ConvServiceDep,
) -> ApiResponse[EmotionalConversationResponse]:
    try:
        return ApiResponse.ok(
            await service.reset_history(user, conversation_id=conversation_id),
            message="会话已重置",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete(
    "/{conversation_id}",
    response_model=ApiResponse[None],
    summary="删除整个对话",
)
async def delete_conversation(
    conversation_id: int,
    user: CurrentUser,
    service: ConversationService = ConvServiceDep,
) -> ApiResponse[None]:
    try:
        await service.delete_conversation(user, conversation_id=conversation_id)
        return ApiResponse.ok(None, message="对话已删除")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch(
    "/{conversation_id}",
    response_model=ApiResponse[ConversationSummary],
    summary="修改对话名称",
)
async def update_conversation(
    conversation_id: int,
    body: ConversationUpdateRequest,
    user: CurrentUser,
    service: ConversationService = ConvServiceDep,
) -> ApiResponse[ConversationSummary]:
    try:
        result = await service.rename_conversation(
            user, conversation_id=conversation_id, title=body.title
        )
        return ApiResponse.ok(result, message="对话已重命名")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
