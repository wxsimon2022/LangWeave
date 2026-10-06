"""Structured logging middleware for agent runs."""

from __future__ import annotations

import logging
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, AgentState
from langgraph.runtime import Runtime

logger = logging.getLogger("langweave")


class LoggingMiddleware(AgentMiddleware[AgentState[Any], None, Any]):
    """Log model calls and tool rounds at INFO level."""

    tools: list[Any] = []

    def __init__(self, *, log_tools: bool = True) -> None:
        self.log_tools = log_tools

    def before_model(
        self, state: AgentState[Any], runtime: Runtime[None]
    ) -> dict[str, Any] | None:
        n = len(state.get("messages", []))
        logger.info("[%s] model call (messages=%d)", self.name, n)
        return None

    def after_model(
        self, state: AgentState[Any], runtime: Runtime[None]
    ) -> dict[str, Any] | None:
        messages = state.get("messages", [])
        if not messages:
            return None
        last = messages[-1]
        tool_calls = getattr(last, "tool_calls", None) or []
        if tool_calls and self.log_tools:
            names = [tc.get("name", "?") for tc in tool_calls]
            logger.info("[%s] requested tools: %s", self.name, names)
        return None
