"""Apply shared conversation memory (MySQL checkpointer) to dialogue agents."""

from __future__ import annotations

from langweave import AgentBuilder
from langweave.config import AgentSettings
from langweave.memory import get_checkpointer


def with_conversation_memory(
    builder: AgentBuilder,
    settings: AgentSettings | None = None,
) -> AgentBuilder:
    """Attach MySQL-backed checkpointer when memory is enabled in settings.

    Requires ``LANGWEAVE_DATABASE_URL`` to be set. See ``langweave.memory.get_checkpointer``.
    """
    settings = settings or AgentSettings.from_env()
    if settings.memory_enabled:
        builder.with_checkpointer(get_checkpointer())
    return builder
