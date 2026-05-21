"""Business HTTP routes (intent recognition, etc.)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_intent_service
from app.schemas.intent import (
    IntentChatRequest,
    IntentChatResponse,
    IntentRecognizeRequest,
    IntentRecognizeResponse,
)
from app.services.intent_service import IntentService

router = APIRouter(prefix="/api/v1/intent", tags=["intent"])


@router.post("/recognize", response_model=IntentRecognizeResponse)
async def recognize_intent(
    body: IntentRecognizeRequest,
    service: Annotated[IntentService, Depends(get_intent_service)],
) -> IntentRecognizeResponse:
    """Call the intent agent and return structured classification only."""
    try:
        intent = await service.recognize(body.message, thread_id=body.thread_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return IntentRecognizeResponse(intent=intent, thread_id=body.thread_id)


@router.post("/chat", response_model=IntentChatResponse)
async def intent_chat(
    body: IntentChatRequest,
    service: Annotated[IntentService, Depends(get_intent_service)],
) -> IntentChatResponse:
    """Recognize intent, then invoke target_agent (default: assistant) for the reply."""
    try:
        return await service.recognize_and_chat(
            body.message,
            thread_id=body.thread_id,
            auto_reply=body.auto_reply,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
