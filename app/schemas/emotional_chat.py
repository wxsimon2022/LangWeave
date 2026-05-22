"""Schemas for authenticated emotional chat APIs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EmotionalMessageItem(BaseModel):
    """Single persisted chat message."""

    id: int
    role: str = Field(description="user | assistant | system")
    content: str
    created_at: datetime


class EmotionalChatRequest(BaseModel):
    """Send a new emotional chat message."""

    message: str = Field(..., min_length=1)


class EmotionalConversationResponse(BaseModel):
    """Paginated conversation history."""

    conversation_id: int
    thread_id: str
    agent: str
    messages: list[EmotionalMessageItem]
    total_count: int
    offset: int = 0
    limit: int = 50
    has_more: bool = False


class EmotionalChatResponse(BaseModel):
    """Created user/assistant message pair."""

    conversation_id: int
    thread_id: str
    agent: str
    user_message: EmotionalMessageItem
    assistant_message: EmotionalMessageItem
