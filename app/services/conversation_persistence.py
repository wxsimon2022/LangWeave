"""Conversation persistence service — DB operations for chat messages."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import ChatMessage, Conversation
from app.schemas.emotional_chat import EmotionalMessageItem
from app.constants import DEFAULT_AGENT_NAME


class ConversationPersistence:
    """Persist and retrieve conversation data."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_conversation(self, user_id: int) -> Conversation:
        """Create a new conversation for a user."""
        conv = Conversation(user_id=user_id, agent_name=DEFAULT_AGENT_NAME)
        self._db.add(conv)
        self._db.commit()
        self._db.refresh(conv)
        return conv

    def add_messages(
        self,
        conversation_id: int,
        messages: list[dict[str, Any]],
    ) -> list[ChatMessage]:
        """Persist a batch of messages (user + assistant)."""
        models = []
        for msg in messages:
            m = ChatMessage(
                conversation_id=conversation_id,
                role=msg["role"],
                content=msg["content"],
            )
            self._db.add(m)
            models.append(m)
        self._db.commit()
        for m in models:
            self._db.refresh(m)
        return models
