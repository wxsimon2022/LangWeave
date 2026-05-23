"""Conversation management service.

Wraps ``app.application.services.chat.ChatService`` conversation operations.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.application.services.chat import ChatService
from app.schemas.emotional_chat import (
    ConversationListResponse,
    ConversationSummary,
    EmotionalConversationResponse,
)
from langweave.registry import AgentRegistry


class ConversationService:
    """Manage conversations across all agent types."""

    def __init__(self, db: Session, registry: AgentRegistry) -> None:
        self._chat_service = ChatService(db, registry)

    async def list_conversations(self, user: Any) -> ConversationListResponse:
        return await self._chat_service.list_conversations(user)

    async def get_history(
        self, user: Any, *, conversation_id: int, offset: int = 0, limit: int = 50
    ) -> EmotionalConversationResponse:
        return await self._chat_service.get_history(
            user, conversation_id=conversation_id, offset=offset, limit=limit
        )

    async def reset_history(
        self, user: Any, *, conversation_id: int
    ) -> EmotionalConversationResponse:
        return await self._chat_service.reset_history(
            user, conversation_id=conversation_id
        )

    async def delete_conversation(self, user: Any, *, conversation_id: int) -> None:
        await self._chat_service.delete_conversation(
            user, conversation_id=conversation_id
        )

    async def rename_conversation(
        self, user: Any, *, conversation_id: int, title: str
    ) -> ConversationSummary:
        return await self._chat_service.rename_conversation(
            user, conversation_id=conversation_id, title=title
        )
