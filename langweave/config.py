"""Environment-driven agent configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

_DOTENV_LOADED = False


def load_dotenv() -> None:
    """Load `.env` from the project root (idempotent)."""
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    try:
        from dotenv import load_dotenv as _load
    except ImportError:
        _DOTENV_LOADED = True
        return

    root = Path(__file__).resolve().parents[1]
    for path in (root / ".env", Path.cwd() / ".env"):
        if path.is_file():
            _load(path, override=False)
            break
    else:
        _load(override=False)
    _DOTENV_LOADED = True


def deepseek_api_key() -> str | None:
    """Resolve DeepSeek API key from settings env or standard variable."""
    load_dotenv()
    return _env("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")


def _env(key: str, default: str | None = None) -> str | None:
    value = os.environ.get(f"LANGWEAVE_{key}")
    if value is not None:
        return value
    # backward compatibility with pre-rename prefix
    return os.environ.get(f"LC_AGENT_{key}", default)


class AgentSettings(BaseModel):
    """Default model and runtime settings (overridable via LANGWEAVE_* env vars)."""

    model: str = Field(
        default="deepseek:deepseek-chat",
        description="Model for init_chat_model, e.g. deepseek:deepseek-chat",
    )
    system_prompt: str | None = Field(
        default=None,
        description="Default system prompt when builder does not set one",
    )
    temperature: float | None = Field(
        default=None,
        description="Sampling temperature passed to the chat model",
    )
    max_tokens: int | None = Field(
        default=None,
        description="Max tokens for model completion",
    )
    deepseek_api_key: str | None = Field(
        default=None,
        description="DeepSeek API key; falls back to DEEPSEEK_API_KEY env",
    )
    debug: bool = Field(default=False, description="Enable LangGraph debug mode")

    def model_kwargs(self) -> dict[str, Any]:
        """Extra kwargs for `init_chat_model` derived from settings."""
        kwargs: dict[str, Any] = {}
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens
        if self.deepseek_api_key and self.model.startswith("deepseek"):
            kwargs["api_key"] = self.deepseek_api_key
        return kwargs

    @classmethod
    def from_env(cls, **overrides: Any) -> AgentSettings:
        load_dotenv()
        data: dict[str, Any] = {}
        if model := _env("MODEL"):
            data["model"] = model
        if prompt := _env("SYSTEM_PROMPT"):
            data["system_prompt"] = prompt
        if temp := _env("TEMPERATURE"):
            data["temperature"] = float(temp)
        if max_tok := _env("MAX_TOKENS"):
            data["max_tokens"] = int(max_tok)
        if debug := _env("DEBUG"):
            data["debug"] = debug.lower() in ("1", "true", "yes")
        if key := deepseek_api_key():
            data["deepseek_api_key"] = key
        data.update(overrides)
        return cls(**data)
