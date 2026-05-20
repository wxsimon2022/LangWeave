"""Environment-driven agent configuration."""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field


def _env(key: str, default: str | None = None) -> str | None:
    value = os.environ.get(f"LANGWEAVE_{key}")
    if value is not None:
        return value
    # backward compatibility with pre-rename prefix
    return os.environ.get(f"LC_AGENT_{key}", default)


class AgentSettings(BaseModel):
    """Default model and runtime settings (overridable via LANGWEAVE_* env vars)."""

    model: str = Field(
        default="openai:gpt-4o-mini",
        description="Default model identifier for init_chat_model",
    )
    system_prompt: str | None = Field(
        default=None,
        description="Default system prompt when builder does not set one",
    )
    debug: bool = Field(default=False, description="Enable LangGraph debug mode")

    @classmethod
    def from_env(cls, **overrides: Any) -> AgentSettings:
        data: dict[str, Any] = {}
        if model := _env("MODEL"):
            data["model"] = model
        if prompt := _env("SYSTEM_PROMPT"):
            data["system_prompt"] = prompt
        if debug := _env("DEBUG"):
            data["debug"] = debug.lower() in ("1", "true", "yes")
        data.update(overrides)
        return cls(**data)
