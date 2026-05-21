"""Intent recognition request/response models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

IntentType = Literal["general_chat", "order_query", "calculation", "unknown"]


class UserIntent(BaseModel):
    """Structured output from the intent agent."""

    intent: IntentType = Field(description="Classified user intent")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    slots: dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted entities, e.g. order_id",
    )
    target_agent: str = Field(
        default="assistant",
        description="Downstream agent name to handle the request",
    )
    reasoning: str | None = Field(
        default=None,
        description="Brief explanation of the classification",
    )


class IntentRecognizeRequest(BaseModel):
    message: str = Field(..., min_length=1)
    thread_id: str | None = None


class IntentRecognizeResponse(BaseModel):
    intent: UserIntent
    thread_id: str | None = None


class IntentChatRequest(BaseModel):
    """Recognize intent, then invoke the target agent for a reply."""

    message: str = Field(..., min_length=1)
    thread_id: str | None = None
    auto_reply: bool = Field(
        default=True,
        description="If true, call target_agent after recognition",
    )


class IntentChatResponse(BaseModel):
    intent: UserIntent
    reply: str | None = None
    agent: str | None = None
    thread_id: str | None = None
