"""Memory management — conversation memory and memory store.

Wraps LangGraph checkpointer (volatile MemorySaver or MySQL-backed).
"""
from __future__ import annotations

from typing import Any

from langweave.memory import get_checkpointer, resolve_thread_id, aclear_thread, aget_thread_messages


async def get_conversation_history(graph: Any, thread_id: str) -> list[Any]:
    """Get message history for a thread from the checkpointer."""
    return await aget_thread_messages(graph, thread_id)


async def clear_conversation_memory(graph: Any, thread_id: str) -> None:
    """Clear the checkpointer state for a thread."""
    await aclear_thread(graph, thread_id)
