"""Register business agents into the LangWeave registry.

Agent implementations live in ``app/agents/``.
"""
from __future__ import annotations

import importlib

from langweave.config import AgentSettings
from langweave.registry import AgentRegistry

from app.agents.research_agent_v2 import build_research_agent_v2
from app.agents.general_agent_v2 import build_general_agent_v2
from app.agents.intent_agent import build_intent_agent
from app.agents.fallback_agent import build_unavailable_agent
from app.constants import (
    INTENT_AGENT,
    ASSISTANT_AGENT,
    EMOTIONAL_AGENT,
    INTENT_DESCRIPTION,
    ASSISTANT_DESCRIPTION,
    EMOTIONAL_DESCRIPTION,
)


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


def _register_fallback_agents(registry: AgentRegistry, error_message: str) -> None:
    agents = [
        (INTENT_AGENT, INTENT_DESCRIPTION),
        (ASSISTANT_AGENT, ASSISTANT_DESCRIPTION),
        (EMOTIONAL_AGENT, EMOTIONAL_DESCRIPTION),
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
