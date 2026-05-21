"""Register business agents into the LangWeave registry."""

from __future__ import annotations

from langweave import AgentBuilder
from langweave.config import AgentSettings
from langweave.registry import AgentRegistry

from app.agents.assistant import build_assistant_agent
from app.agents.emotional import build_emotional_agent
from app.agents.intent import build_intent_agent


def register_agents(registry: AgentRegistry) -> None:
    """Wire all application agents. Called on FastAPI startup."""
    settings = AgentSettings.from_env()
    registry.register(build_intent_agent(settings), overwrite=True)
    registry.register(build_assistant_agent(settings), overwrite=True)
    registry.register(build_emotional_agent(settings), overwrite=True)
