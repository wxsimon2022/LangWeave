"""Apply shared conversation memory to dialogue agents."""

from __future__ import annotations

from langweave import AgentBuilder
from langweave.config import AgentSettings
from langweave.memory import get_checkpointer


def with_conversation_memory(
    builder: AgentBuilder,
    settings: AgentSettings | None = None,
) -> AgentBuilder:
    """Attach checkpointer when memory is enabled in settings."""
    settings = settings or AgentSettings.from_env()
    if settings.memory_enabled:
        builder.with_checkpointer(get_checkpointer())
    return builder
