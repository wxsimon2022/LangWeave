"""Fallback agents used when model dependencies are unavailable."""
from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from langweave.agent import Agent


class UnavailableAgent:
    """Minimal agent facade that reports configuration/dependency issues."""

    def __init__(self, name: str, description: str, error_message: str) -> None:
        self.name = name
        self.description = description
        self.graph = None
        self._error_message = error_message

    async def achat(
        self,
        message: str,
        *,
        thread_id: str | None = None,
        **_: Any,
    ) -> tuple[str, str | None]:
        return self._error_message, thread_id

    async def ainvoke(
        self,
        input: str | dict[str, Any] | list[Any],
        *,
        thread_id: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        user_message = input if isinstance(input, str) else ""
        return {
            "messages": [
                HumanMessage(content=user_message),
                AIMessage(content=self._error_message),
            ],
            "_thread_id": thread_id,
        }

    async def aget_history(self, thread_id: str) -> list[Any]:
        return []


def build_unavailable_agent(name: str, description: str, error_message: str) -> Agent:
    """Create an agent-like placeholder for degraded startup paths."""
    return UnavailableAgent(name, description, error_message)  # type: ignore[return-value]
