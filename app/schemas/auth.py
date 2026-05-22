"""Authentication request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserProfile(BaseModel):
    """Authenticated user profile."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime


class RegisterRequest(BaseModel):
    """User registration payload."""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    """User login payload."""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class AuthTokenResponse(BaseModel):
    """Token-bearing auth response."""

    access_token: str
    token_type: str = "bearer"
    user: UserProfile
