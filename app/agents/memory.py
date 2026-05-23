"""Apply shared conversation memory to dialogue agents."""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

from langweave import AgentBuilder
from langweave.config import AgentSettings
from langweave.memory import get_checkpointer


def with_conversation_memory(
    builder: AgentBuilder,
    settings: AgentSettings | None = None,
    *,
    volatile: bool = False,
) -> AgentBuilder:
    """Attach checkpointer when memory is enabled in settings.

    ``volatile=True`` uses an in-process ``MemorySaver`` instead of the
    shared MySQL checkpointer. Use for agents whose conversation history
    is persisted elsewhere (e.g. emotional chat in ``chat_messages``).
    """
    settings = settings or AgentSettings.from_env()
    if settings.memory_enabled:
        checkpointer = MemorySaver() if volatile else get_checkpointer()
        builder.with_checkpointer(checkpointer)
    return builder
