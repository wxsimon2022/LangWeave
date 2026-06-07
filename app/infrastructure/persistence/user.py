"""User ORM model — ``c_users`` table.

``password_hash`` stores the PBKDF2-HMAC-SHA256 hex digest;
``is_admin`` gates the ``/api/v1/admin/*`` endpoints.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    """Authenticated user with JWT-based auth."""

    __tablename__ = "c_users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # One-to-many: a user may have multiple conversations.
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user",
        primaryjoin="User.id == foreign(Conversation.user_id)",
    )
