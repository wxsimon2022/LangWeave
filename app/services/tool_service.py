"""Tool service — manage tools available to agents."""
from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool

from app.domain.tools import get_default_tools


class ToolService:
    """Manage and provide tools to agents."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def get_default_tools(self) -> list[BaseTool | Any]:
        return get_default_tools()

    def register_tool(self, name: str, tool: BaseTool) -> None:
        self._tools[name] = tool

    def get_tool(self, name: str) -> BaseTool | None:
        return self._tools.get(name)
