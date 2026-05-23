"""LLM provider factory — wraps langweave's model resolution."""
from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langweave.config import AgentSettings
from langweave.builder import init_chat_model


def create_llm(
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs: Any,
) -> BaseChatModel:
    """Create a chat model instance from a model string.

    Supports ``deepseek:*``, ``openai:*``, and any model supported by
    ``langchain.chat_models.init_chat_model``.
    """
    settings = AgentSettings.from_env()
    model_id = model or settings.model
    model_kwargs = settings.model_kwargs()
    if temperature is not None:
        model_kwargs["temperature"] = temperature
    if max_tokens is not None:
        model_kwargs["max_tokens"] = max_tokens
    model_kwargs.update(kwargs)
    return init_chat_model(model_id, **model_kwargs)
