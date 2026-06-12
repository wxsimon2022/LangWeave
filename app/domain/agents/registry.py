"""Register business agents into the LangWeave registry.

Called once during FastAPI lifespan startup (``app.bootstrap._startup``).
If the configured model provider (e.g. DeepSeek) is unavailable, every
agent is replaced with an ``UnavailableAgent`` that returns a clear
error message — the API stays alive even when the AI backend is down.
"""
from __future__ import annotations

import importlib

from langweave.config import AgentSettings
from langweave.registry import AgentRegistry

from app.domain.agents.emotional import build_research_agent_v2
from app.domain.agents.file_assistant import build_file_assistant_agent
from app.domain.agents.assistant import build_general_agent_v2
from app.domain.agents.intent import build_intent_agent
from app.domain.agents.fallback import build_unavailable_agent
from app.constants import (
    INTENT_AGENT,
    ASSISTANT_AGENT,
    EMOTIONAL_AGENT,
    INTENT_DESCRIPTION,
    ASSISTANT_DESCRIPTION,
    EMOTIONAL_DESCRIPTION,
    FILE_ASSISTANT_AGENT,
    FILE_ASSISTANT_DESCRIPTION,
)


def _missing_model_error(settings: AgentSettings) -> str | None:
    """Check whether the configured model provider is importable.

    Returns an error string if the dependency is missing, or None if OK.
    """
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


def _register_fallback_agents(registry: AgentRegistry, error_message: str) -> None:
    agents = [
        (INTENT_AGENT, INTENT_DESCRIPTION),
        (ASSISTANT_AGENT, ASSISTANT_DESCRIPTION),
        (EMOTIONAL_AGENT, EMOTIONAL_DESCRIPTION),
        (FILE_ASSISTANT_AGENT, FILE_ASSISTANT_DESCRIPTION),
    ]
    for name, description in agents:
        registry.register(
            build_unavailable_agent(name, description, error_message),
            overwrite=True,
        )


def register_agents(registry: AgentRegistry) -> None:
    """Wire all application agents. Called on FastAPI startup."""
    settings = AgentSettings.from_env()
    error_message = _missing_model_error(settings)
    if error_message:
        _register_fallback_agents(registry, error_message)
        return

    registry.register(build_intent_agent(settings), overwrite=True)
    registry.register(build_general_agent_v2(settings), overwrite=True)
    registry.register(build_research_agent_v2(settings), overwrite=True)
    registry.register(build_file_assistant_agent(settings), overwrite=True)
