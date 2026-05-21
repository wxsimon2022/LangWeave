"""Default assistant agent for the application."""

from __future__ import annotations

from langweave import Agent, AgentBuilder
from langweave.config import AgentSettings

from app.tools import get_default_tools


def build_assistant_agent(settings: AgentSettings | None = None) -> Agent:
    settings = settings or AgentSettings.from_env()
    return (
        AgentBuilder(settings)
        .with_name("assistant")
        .with_description("General assistant with calculator and clock tools")
        .with_system_prompt(
            settings.system_prompt
            or "You are a helpful assistant. Use tools when needed."
        )
        .with_tools(get_default_tools())
        .build()
    )
