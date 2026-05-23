"""Tool base class — wraps LangChain tools with metadata."""
from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool


class BaseAgentTool:
    """Base wrapper for agent tools (thin wrapper around ``BaseTool``)."""

    def __init__(self, tool: BaseTool) -> None:
        self._tool = tool

    @property
    def tool(self) -> BaseTool:
        return self._tool

    @property
    def name(self) -> str:
        return self._tool.name

    @property
    def description(self) -> str:
        return self._tool.description
