"""Global application configuration."""

from __future__ import annotations

from app.constants import (
    INTENT_AGENT,
    ASSISTANT_AGENT,
    EMOTIONAL_AGENT,
    DEFAULT_AGENT_NAME,
    API_V1_PREFIX,
    REDIS_KEY_PREFIX,
    DEFAULT_CORS_ORIGINS,
)


class AppSettings:
    """Application-level configuration."""

    # Agent names
    intent_agent: str = INTENT_AGENT
    assistant_agent: str = ASSISTANT_AGENT
    emotional_agent: str = EMOTIONAL_AGENT
    default_agent: str = DEFAULT_AGENT_NAME

    # API
    api_prefix: str = API_V1_PREFIX
    cors_origins: list[str] = DEFAULT_CORS_ORIGINS

    # Redis
    redis_key_prefix: str = REDIS_KEY_PREFIX

    # JWT
    jwt_secret: str = "change-this-in-production"
    jwt_expire_minutes: int = 120

    @classmethod
    def from_env(cls) -> AppSettings:
        return cls()
