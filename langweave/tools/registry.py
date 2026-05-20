"""Registry for organizing tools by group."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from langchain_core.tools import BaseTool


class ToolRegistry:
    """Group and collect tools for agent builders."""

    def __init__(self) -> None:
        self._groups: dict[str, list[BaseTool | Callable[..., object]]] = {}

    def register(
        self,
        group: str,
        *tools: BaseTool | Callable[..., object],
    ) -> None:
        self._groups.setdefault(group, []).extend(tools)

    def get(self, group: str) -> list[BaseTool | Callable[..., object]]:
        return list(self._groups.get(group, []))

    def all(self) -> list[BaseTool | Callable[..., object]]:
        out: list[BaseTool | Callable[..., object]] = []
        for tools in self._groups.values():
            out.extend(tools)
        return out

    def groups(self) -> list[str]:
        return sorted(self._groups)

    def tools_for(self, groups: Sequence[str]) -> list[BaseTool | Callable[..., object]]:
        result: list[BaseTool | Callable[..., object]] = []
        for group in groups:
            result.extend(self.get(group))
        return result
