"""Register business agents into the LangWeave registry."""

from __future__ import annotations

import importlib

from langweave.config import AgentSettings
from langweave.registry import AgentRegistry

from app.domain.agents.assistant import build_assistant_agent
from app.domain.agents.emotional import build_emotional_agent
from app.domain.agents.fallback import build_unavailable_agent
from app.domain.agents.intent import build_intent_agent


def _missing_model_error(settings: AgentSettings) -> str | None:
    model = settings.model
    if model.startswith("deepseek"):
        try:
            importlib.import_module("langchain_deepseek")
        except ImportError:
            return (
                "DeepSeek model dependency is unavailable. "
                "Install `langchain-deepseek` or switch LANGWEAVE_MODEL to an installed provider."
            )
    return None


def register_agents(registry: AgentRegistry) -> None:
    """Wire all application agents. Called on FastAPI startup."""
    settings = AgentSettings.from_env()
    error_message = _missing_model_error(settings)
    if error_message:
        registry.register(
            build_unavailable_agent(
                "intent",
                "Classifies user intent via structured output",
                error_message,
            ),
            overwrite=True,
        )
        registry.register(
            build_unavailable_agent(
                "assistant",
                "General assistant with calculator and clock tools",
                error_message,
            ),
            overwrite=True,
        )
        registry.register(
            build_unavailable_agent(
                "emotional",
                "情感陪伴与倾听，提供共情式对话支持（支持多轮记忆）",
                error_message,
            ),
            overwrite=True,
        )
        return

    registry.register(build_intent_agent(settings), overwrite=True)
    registry.register(build_assistant_agent(settings), overwrite=True)
    registry.register(build_emotional_agent(settings), overwrite=True)
