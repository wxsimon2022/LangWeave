"""Shared utility helpers for the application layer."""

from __future__ import annotations

from typing import Any, Sequence

from langchain_core.messages import AIMessage, BaseMessage


def extract_text_content(content: str | list[dict[str, Any]]) -> str:
    """Extract plain text from a LangChain message content field."""
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
    """Find the most recent AI message content in a sequence."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return extract_text_content(msg.content)
    return ""


def chunk_to_text(chunk: Any) -> str:
    """Extract text from a streaming chunk."""
    payload = chunk[0] if isinstance(chunk, tuple) else chunk
    if isinstance(payload, AIMessage):
        return extract_text_content(payload.content)
    return ""
