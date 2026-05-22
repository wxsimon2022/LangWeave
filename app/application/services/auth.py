"""User registration, login, and token-backed identity lookups."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.infrastructure.persistence.models import User
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

    def _build_token_response(self, user: User) -> AuthTokenResponse:
        return AuthTokenResponse(
            access_token=create_access_token(user.id),
            token_type="bearer",
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
