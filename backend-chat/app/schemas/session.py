"""Conversation session (memory) schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MessageItem(BaseModel):
    role: str = Field(description="human | ai | tool | system")
    content: str = Field(description="Message text")


class SessionHistoryResponse(BaseModel):
    thread_id: str
    agent: str
    message_count: int
    messages: list[MessageItem]
