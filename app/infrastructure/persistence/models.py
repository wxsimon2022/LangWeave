"""SQLAlchemy ORM models for auth and chat persistence."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, foreign


class Base(DeclarativeBase):
    """Base ORM model."""


class User(Base):
    """Authenticated user."""

    __tablename__ = "c_users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user",
        primaryjoin="User.id == foreign(Conversation.user_id)",
    )


class Conversation(Base):
    """Per-user persistent conversation."""

    __tablename__ = "c_conversations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(index=True)
    agent_name: Mapped[str] = mapped_column(String(32), default="emotional")
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

    user: Mapped[User] = relationship(
        back_populates="conversations",
        primaryjoin="foreign(Conversation.user_id) == User.id",
    )
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation",
        order_by="ChatMessage.id",
        primaryjoin="Conversation.id == foreign(ChatMessage.conversation_id)",
    )


class ChatMessage(Base):
    """Persisted conversation message."""

    __tablename__ = "c_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    conversation: Mapped[Conversation] = relationship(
        back_populates="messages",
        primaryjoin="foreign(ChatMessage.conversation_id) == Conversation.id",
    )
