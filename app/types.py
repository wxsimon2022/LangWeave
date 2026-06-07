"""Shared type definitions.

Centralises type aliases that appear across module boundaries so that
signatures stay readable without repeating verbose generics.
"""

from __future__ import annotations

from typing import Any

# Generic JSON-compatible dictionary — used throughout for
# unstructured metadata, tool arguments, and API response payloads.
JSONDict = dict[str, Any]

# LangChain message content can be either a plain string or a list
# of content blocks (text, image, tool-result, …).
MessageContent = str | list[dict[str, Any]]

# Agent identification — just a wrapper over ``str`` for readability.
AgentName = str
ThreadId = str

# Return type for agent.chat() — (response_text, thread_id).
AgentResponse = tuple[str, str | None]
