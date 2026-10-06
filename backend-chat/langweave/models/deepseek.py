"""DeepSeek model integration via langchain-deepseek."""

from __future__ import annotations

from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

DEEPSEEK_V4_PRO = "deepseek-v4-pro"
DEEPSEEK_V4_FLASH = "deepseek-v4-flash"

_DEFAULT_MODELS = (DEEPSEEK_V4_PRO, DEEPSEEK_V4_FLASH)


def model_id(name: str = DEEPSEEK_V4_PRO) -> str:
    """Return an `init_chat_model`-compatible model string."""
    if ":" in name:
        return name
    return f"deepseek:{name}"


def _api_key(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    from langweave.config import deepseek_api_key

    return deepseek_api_key()


def chat_model(
    model: str = DEEPSEEK_V4_PRO,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    api_key: str | None = None,
    **kwargs: Any,
) -> BaseChatModel:
    """Create a DeepSeek chat model.

    Requires `langchain-deepseek` and `DEEPSEEK_API_KEY` (or pass `api_key`).

    Common models: `deepseek-v4-pro`, `deepseek-v4-flash`.
    """
    model_kwargs: dict[str, Any] = dict(kwargs)
    if temperature is not None:
        model_kwargs["temperature"] = temperature
    if max_tokens is not None:
        model_kwargs["max_tokens"] = max_tokens
    key = _api_key(api_key)
    if key is not None:
        model_kwargs["api_key"] = key

    return init_chat_model(model_id(model), **model_kwargs)
