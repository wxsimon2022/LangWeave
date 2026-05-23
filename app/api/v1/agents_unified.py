"""Unified Agent invocation API — entry-agent chat with intent routing.

This is the primary chat endpoint: it accepts any message, classifies
intent via the intent agent, and routes to the appropriate specialist agent.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.services.agent_application_service import AgentApplicationService
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
router = APIRouter(prefix=f"{API_V1_PREFIX}/agents", tags=["agents-unified"])


# ------------------------------------------------------------------
# Dependency
# ------------------------------------------------------------------

def get_agent_service(
    db: Session = Depends(get_db_session),
    registry: AgentRegistry = Depends(get_registry),
) -> AgentApplicationService:
    return AgentApplicationService(db, registry)


AgentServiceDep = Depends(get_agent_service)


# ------------------------------------------------------------------
# Stream message (entry agent → intent recognition → specialist agent)
# ------------------------------------------------------------------

@router.post(
    "/unified/stream",
    summary="入口 agent：识别意图并路由到对应的 specialist agent（SSE 流式）",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "SSE stream with intent/chunk/done events",
            "content": {"text/event-stream": {}},
        },
    },
)
async def stream_unified(
    body: EmotionalChatRequest,
    user: CurrentUser,
    service: AgentApplicationService = AgentServiceDep,
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
# SSE safety wrapper
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
