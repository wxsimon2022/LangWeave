"""Intent-related HTTP routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.application.services.intent import IntentService
from app.interfaces.http.deps import get_intent_service
from app.schemas.intent import (
    IntentChatRequest,
    IntentChatResponse,
    IntentRecognizeRequest,
    IntentRecognizeResponse,
)
from langweave.web.response import ApiResponse

router = APIRouter(prefix="/api/v1/intent", tags=["intent"])


@router.post(
    "/recognize",
    response_model=ApiResponse[IntentRecognizeResponse],
    summary="意图识别",
)
async def recognize_intent(
    body: IntentRecognizeRequest,
    service: Annotated[IntentService, Depends(get_intent_service)],
) -> ApiResponse[IntentRecognizeResponse]:
    """调用 intent Agent，返回结构化意图（intent、slots、target_agent 等）。"""
    try:
        intent = await service.recognize(body.message, thread_id=body.thread_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ApiResponse.ok(
        IntentRecognizeResponse(intent=intent, thread_id=body.thread_id)
    )


@router.post(
    "/chat",
    response_model=ApiResponse[IntentChatResponse],
    summary="意图识别并回复",
)
async def intent_chat(
    body: IntentChatRequest,
    service: Annotated[IntentService, Depends(get_intent_service)],
) -> ApiResponse[IntentChatResponse]:
    """先识别意图，再调用 target_agent（默认 assistant）生成业务回复。"""
    try:
        result = await service.recognize_and_chat(
            body.message,
            thread_id=body.thread_id,
            auto_reply=body.auto_reply,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ApiResponse.ok(result)
