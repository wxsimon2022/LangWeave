"""General Assistant Agent V2 — general assistant with calculator and clock tools.

This agent handles general queries, tool-based tasks (calculator,
current time), and non-emotional user requests.
"""
from __future__ import annotations

from langweave import Agent, AgentBuilder
from langweave.config import AgentSettings

from app.agents.memory import with_conversation_memory
from app.domain.tools import get_default_tools
from app.constants import ASSISTANT_AGENT


def build_general_agent_v2(settings: AgentSettings | None = None) -> Agent:
    """Build the general assistant agent V2."""
    settings = settings or AgentSettings.from_env()
    builder = (
        AgentBuilder(settings)
        .with_name(ASSISTANT_AGENT)
        .with_description("General assistant with calculator and clock tools")
        .with_system_prompt(
            settings.system_prompt
            or "You are a helpful assistant. Use tools when needed."
        )
        .with_tools(get_default_tools())
    )
    return with_conversation_memory(builder, settings).build()
