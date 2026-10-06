"""Message ORM model — ``c_messages`` table.

A single turn in a conversation.  ``role`` is ``user`` or ``assistant``.
``agent_name`` records which specialist agent produced the reply
(``emotional`` / ``assistant``).  Messages are appended in chronological
order and loaded eagerly for history display.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .conversation import Conversation


class ChatMessage(Base):
    """A single turn (user query or assistant reply) in a conversation."""

    __tablename__ = "c_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(index=True)

    role: Mapped[str] = mapped_column(String(16))     # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    agent_name: Mapped[str | None] = mapped_column(
        String(32), nullable=True, default=None,
        comment="Specialist agent that produced this reply (emotional / assistant)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    conversation: Mapped["Conversation"] = relationship(
        back_populates="messages",
        primaryjoin="foreign(ChatMessage.conversation_id) == Conversation.id",
    )
