"""Conversation ORM model — ``c_conversations`` table.

``agent_name`` is set to ``emotional`` on creation.  After the first
message the intent classifier may change it to ``assistant``, so that
subsequent messages in the same conversation bypass intent classification.

``thread_id`` uniquely identifies the LangGraph checkpoint thread used
for multi-turn memory.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .message import ChatMessage


class Conversation(Base):
    """Per-user persistent conversation with agent routing metadata."""

    __tablename__ = "c_conversations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(index=True)

    # The specialist agent assigned to this conversation.
    # Set by the intent router after classifying the first message.
    agent_name: Mapped[str] = mapped_column(String(32), default="emotional")

    # LangGraph checkpointer thread ID — links this SQL row to the
    # ``checkpoints`` table managed by ``langgraph-checkpoint-mysql``.
    thread_id: Mapped[str] = mapped_column(
        String(64),
        default=lambda: str(uuid.uuid4()),
        unique=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(128),
        default="新对话",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="conversations",
        primaryjoin="foreign(Conversation.user_id) == User.id",
    )
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation",
        order_by="ChatMessage.id",
        primaryjoin="Conversation.id == foreign(ChatMessage.conversation_id)",
    )
