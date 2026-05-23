"""User registration, login, and token-backed identity lookups."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.security import (
    create_access_token,
    create_refresh_token,
    get_auth_settings,
    hash_password,
    verify_password,
)
from app.infrastructure.persistence.models import ChatMessage, Conversation, User
from app.schemas.admin import (
    AdminConversationItem,
    AdminConversationListResponse,
    AdminConversationMessagesResponse,
    AdminMessageItem,
    AdminUserItem,
    AdminUserListResponse,
)
from app.schemas.auth import AuthTokenResponse, UserProfile


class AuthService:
    """Handle user registration and login."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def register(self, username: str, password: str) -> AuthTokenResponse:
        username = username.strip()
        password = password.strip()
        self._validate_credentials(username, password)

        existing = self._db.scalar(select(User).where(User.username == username))
        if existing is not None:
            msg = "Username already exists"
            raise ValueError(msg)

        user = User(username=username, password_hash=hash_password(password))
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return self._build_token_response(user)

    def login(self, username: str, password: str) -> AuthTokenResponse:
        username = username.strip()
        password = password.strip()
        self._validate_credentials(username, password)

        user = self._db.scalar(select(User).where(User.username == username))
        if user is None or not verify_password(password, user.password_hash):
            msg = "Invalid username or password"
            raise ValueError(msg)
        return self._build_token_response(user)

    def get_user(self, user_id: int) -> User:
        user = self._db.get(User, user_id)
        if user is None:
            msg = "User not found"
            raise ValueError(msg)
        return user

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------

    def list_users(self) -> AdminUserListResponse:
        """Return all registered users with their conversation counts."""
        # Subquery for conversation count per user
        count_subq = (
            select(
                Conversation.user_id,
                func.count(Conversation.id).label("cnt"),
            )
            .group_by(Conversation.user_id)
            .subquery()
        )

        stmt = (
            select(User.id, User.username, User.created_at, func.coalesce(count_subq.c.cnt, 0))
            .outerjoin(count_subq, User.id == count_subq.c.user_id)
            .order_by(User.created_at.desc())
        )
        rows = self._db.execute(stmt).all()

        users = [
            AdminUserItem(
                id=row.id,
                username=row.username,
                created_at=row.created_at,
                conversation_count=row[3],  # cnt from coalesce
            )
            for row in rows
        ]
        return AdminUserListResponse(users=users, total_count=len(users))

    def delete_user(self, user_id: int) -> tuple[int, str]:
        """Delete a user by ID. Returns (deleted_id, deleted_username)."""
        user = self._db.get(User, user_id)
        if user is None:
            msg = f"User {user_id} not found"
            raise ValueError(msg)
        username = user.username
        self._db.delete(user)
        self._db.commit()
        return user.id, username

    def create_user(self, username: str, password: str, is_admin: bool = False) -> User:
        """Create a new user (admin operation). Returns the created User."""
        username = username.strip()
        password = password.strip()
        self._validate_credentials(username, password)

        existing = self._db.scalar(select(User).where(User.username == username))
        if existing is not None:
            msg = "Username already exists"
            raise ValueError(msg)

        user = User(
            username=username,
            password_hash=hash_password(password),
            is_admin=is_admin,
        )
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def update_user_password(self, user_id: int, new_password: str) -> tuple[int, str]:
        """Update a user's password. Returns (user_id, username)."""
        user = self._db.get(User, user_id)
        if user is None:
            msg = f"User {user_id} not found"
            raise ValueError(msg)
        if len(new_password.strip()) < 6:
            msg = "Password must be at least 6 characters"
            raise ValueError(msg)
        user.password_hash = hash_password(new_password.strip())
        self._db.commit()
        return user.id, user.username

    def list_conversations_for_user(self, user_id: int) -> AdminConversationListResponse:
        """Return all conversations for a given user, newest first."""
        user = self._db.get(User, user_id)
        if user is None:
            msg = f"User {user_id} not found"
            raise ValueError(msg)

        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        convs = list(self._db.scalars(stmt).all())

        items = [
            AdminConversationItem(
                id=c.id,
                user_id=c.user_id,
                username=user.username,
                title=c.title,
                agent_name=c.agent_name,
                message_count=self._db.scalar(
                    select(func.count(ChatMessage.id)).where(
                        ChatMessage.conversation_id == c.id
                    )
                ) or 0,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in convs
        ]
        return AdminConversationListResponse(conversations=items, total_count=len(items))

    def get_conversation_messages(
        self, user_id: int, conversation_id: int
    ) -> AdminConversationMessagesResponse:
        """Return all messages of a conversation, ensuring it belongs to the user."""
        conv = self._db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        if conv is None:
            msg = f"Conversation {conversation_id} not found for user {user_id}"
            raise ValueError(msg)

        msgs_stmt = (
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.id)
        )
        msgs = list(self._db.scalars(msgs_stmt).all())

        items = [
            AdminMessageItem(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
            )
            for m in msgs
        ]
        return AdminConversationMessagesResponse(
            conversation_id=conv.id,
            title=conv.title,
            messages=items,
            total_count=len(items),
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_token_response(self, user: User) -> AuthTokenResponse:
        settings = get_auth_settings()
        return AuthTokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserProfile.model_validate(user),
        )

    @staticmethod
    def _validate_credentials(username: str, password: str) -> None:
        if len(username) < 3:
            msg = "Username must be at least 3 characters"
            raise ValueError(msg)
        if len(password) < 6:
            msg = "Password must be at least 6 characters"
            raise ValueError(msg)
