"""Multi-turn conversation memory via LangGraph checkpointer."""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Any

from langchain_core.messages import BaseMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph


@lru_cache
def get_checkpointer() -> BaseCheckpointSaver:
    """Shared in-memory checkpointer for all conversational agents."""
    return MemorySaver()


def resolve_thread_id(thread_id: str | None) -> str:
    """Use provided session id or create a new one for multi-turn memory."""
    return thread_id or str(uuid.uuid4())


def thread_config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


async def aget_thread_messages(
    graph: CompiledStateGraph[Any, Any, Any, Any],
    thread_id: str,
) -> list[BaseMessage]:
    """Load message history for a conversation thread."""
    snapshot = await graph.aget_state(thread_config(thread_id))
    if snapshot is None or not snapshot.values:
        return []
    messages = snapshot.values.get("messages", [])
    return list(messages) if messages else []


def get_thread_messages(
    graph: CompiledStateGraph[Any, Any, Any, Any],
    thread_id: str,
) -> list[BaseMessage]:
    snapshot = graph.get_state(thread_config(thread_id))
    if snapshot is None or not snapshot.values:
        return []
    messages = snapshot.values.get("messages", [])
    return list(messages) if messages else []


async def aclear_thread(
    graph: CompiledStateGraph[Any, Any, Any, Any],
    thread_id: str,
) -> None:
    """Clear checkpointed state for a thread (new conversation)."""
    await graph.aupdate_state(
        thread_config(thread_id),
        {"messages": []},
    )
