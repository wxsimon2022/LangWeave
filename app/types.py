"""Shared type definitions."""

from __future__ import annotations

from typing import Any

# Common data aliases
JSONDict = dict[str, Any]
MessageContent = str | list[dict[str, Any]]

# Agent related
AgentName = str
ThreadId = str
AgentResponse = tuple[str, str | None]
