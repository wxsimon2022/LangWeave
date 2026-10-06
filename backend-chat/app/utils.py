"""Shared utility helpers for the application layer.

Most functions here deal with the LangChain message model: streaming
chunks come as ``(AIMessage, str)`` tuples, while complete message lists
live in ``list[BaseMessage]``.
"""

from __future__ import annotations

from typing import Any, Sequence

from langchain_core.messages import AIMessage, BaseMessage


def extract_text_content(content: str | list[dict[str, Any]]) -> str:
    """Extract plain text from a LangChain message content field.

    LangGraph stores messages with either a plain string or a list of
    typed blocks (``{"type": "text", "text": "..."}``).  This function
    normalises both forms into a single string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return str(content)


def last_ai_content(messages: Sequence[BaseMessage]) -> str:
    """Find the most recent AI message content in a sequence.

    Used by the ``/api/v1/conversations/{id}`` endpoint to return
    the last reply without fetching the full message graph.
    """
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return extract_text_content(msg.content)
    return ""


def chunk_to_text(chunk: Any) -> str:
    """Extract text from a streaming chunk emitted by ``agent.astream``.

    LangGraph ``stream_mode="messages"`` yields ``(AIMessage, str)``
    tuples.  This helper pulls the text payload out regardless of the
    internal chunk format.
    """
    payload = chunk[0] if isinstance(chunk, tuple) else chunk
    if isinstance(payload, AIMessage):
        return extract_text_content(payload.content)
    return ""
