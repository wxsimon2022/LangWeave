"""Schemas for admin APIs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AdminUserItem(BaseModel):
    """Single user info for admin view."""

    id: int
    username: str
    created_at: datetime
    conversation_count: int


class AdminUserListResponse(BaseModel):
    """List of all registered users."""

    users: list[AdminUserItem]
    total_count: int


class AdminUserDeleteResponse(BaseModel):
    """Result of deleting a user."""

    deleted_user_id: int
    deleted_username: str


class AdminUpdatePasswordRequest(BaseModel):
    """Request to update a user's password."""

    new_password: str


class AdminUpdatePasswordResponse(BaseModel):
    """Result of updating a user's password."""

    user_id: int
    username: str


class AdminConversationItem(BaseModel):
    """Conversation summary for admin view."""

    id: int
    user_id: int
    username: str
    title: str
    agent_name: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class AdminConversationListResponse(BaseModel):
    """List of conversations for a user."""

    conversations: list[AdminConversationItem]
    total_count: int


class AdminMessageItem(BaseModel):
    """Single message for admin view."""

    id: int
    role: str
    content: str
    created_at: datetime


class AdminConversationMessagesResponse(BaseModel):
    """Messages of a conversation."""

    conversation_id: int
    title: str
    messages: list[AdminMessageItem]
    total_count: int
