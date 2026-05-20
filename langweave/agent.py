"""High-level wrapper around a LangChain agent graph."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph


class Agent:
    """Wraps a compiled LangGraph agent with a stable invoke/stream API."""

    def __init__(
        self,
        graph: CompiledStateGraph[Any, Any, Any, Any],
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        self._graph = graph
        self.name = name or getattr(graph, "name", None) or "agent"
        self.description = description or ""

    @property
    def graph(self) -> CompiledStateGraph[Any, Any, Any, Any]:
        return self._graph

    def _normalize_input(
        self,
        input: str | dict[str, Any] | list[AnyMessage],
        *,
        thread_id: str | None = None,
    ) -> tuple[dict[str, Any], RunnableConfig | None]:
        if isinstance(input, str):
            payload: dict[str, Any] = {"messages": [HumanMessage(content=input)]}
        elif isinstance(input, list):
            payload = {"messages": input}
        else:
            payload = input

        if thread_id is None:
            return payload, None
        return payload, {"configurable": {"thread_id": thread_id}}

    @staticmethod
    def _last_ai_content(messages: Sequence[BaseMessage]) -> str:
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                content = msg.content
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts = [
                        block.get("text", "")
                        for block in content
                        if isinstance(block, dict) and block.get("type") == "text"
                    ]
                    return "".join(parts)
        return ""

    def invoke(
        self,
        input: str | dict[str, Any] | list[AnyMessage],
        *,
        config: RunnableConfig | None = None,
        thread_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload, thread_config = self._normalize_input(input, thread_id=thread_id)
        merged = _merge_config(config, thread_config)
        return self._graph.invoke(payload, config=merged, **kwargs)

    async def ainvoke(
        self,
        input: str | dict[str, Any] | list[AnyMessage],
        *,
        config: RunnableConfig | None = None,
        thread_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload, thread_config = self._normalize_input(input, thread_id=thread_id)
        merged = _merge_config(config, thread_config)
        return await self._graph.ainvoke(payload, config=merged, **kwargs)

    def chat(
        self,
        message: str,
        *,
        config: RunnableConfig | None = None,
        thread_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        result = self.invoke(message, config=config, thread_id=thread_id, **kwargs)
        return self._last_ai_content(result.get("messages", []))

    async def achat(
        self,
        message: str,
        *,
        config: RunnableConfig | None = None,
        thread_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        result = await self.ainvoke(
            message, config=config, thread_id=thread_id, **kwargs
        )
        return self._last_ai_content(result.get("messages", []))

    def stream(
        self,
        input: str | dict[str, Any] | list[AnyMessage],
        *,
        config: RunnableConfig | None = None,
        thread_id: str | None = None,
        stream_mode: str | list[str] = "updates",
        **kwargs: Any,
    ) -> Iterator[Any]:
        payload, thread_config = self._normalize_input(input, thread_id=thread_id)
        merged = _merge_config(config, thread_config)
        yield from self._graph.stream(
            payload, config=merged, stream_mode=stream_mode, **kwargs
        )

    async def astream(
        self,
        input: str | dict[str, Any] | list[AnyMessage],
        *,
        config: RunnableConfig | None = None,
        thread_id: str | None = None,
        stream_mode: str | list[str] = "updates",
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        payload, thread_config = self._normalize_input(input, thread_id=thread_id)
        merged = _merge_config(config, thread_config)
        async for chunk in self._graph.astream(
            payload, config=merged, stream_mode=stream_mode, **kwargs
        ):
            yield chunk


def _merge_config(
    base: RunnableConfig | None,
    extra: RunnableConfig | None,
) -> RunnableConfig | None:
    if base is None:
        return extra
    if extra is None:
        return base
    merged: RunnableConfig = dict(base)
    base_cfg = base.get("configurable") or {}
    extra_cfg = extra.get("configurable") or {}
    merged["configurable"] = {**base_cfg, **extra_cfg}
    return merged
